"""Inspect a saved notebook or chat session; continue only through explicit submissions."""
import argparse
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from datetime import datetime
import difflib
import fcntl
from hashlib import sha256
from functools import partial
import json
from pathlib import Path
import re
from threading import Lock
from typing import Literal

from markdown import Markdown
from markdown.extensions.fenced_code import FencedBlockPreprocessor
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.agents import chat_policy_pair, chat_student, chat_workspace, notebook_example, notebook_next_task, notebook_student as student, notebook_teaching_pair, notebook_tutor, policy_comparison_setup, student_workspace, workspace_history
from src.eval import fidelity_comparison as fidelity, notebook_replay, student_reply_comparison as student_replies
from src.eval.saved_comparison import load_comparison
from src.agents import notebook_branch as source_branch
from src.agents import student_evidence

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = "Respond concisely to the student's current request using the visible work and check feedback."


class _PlainFences(FencedBlockPreprocessor):
    def handle_attrs(self, attrs):
        # Saved text must not assign app IDs, classes or other HTML attributes.
        return '', [], {}


def _tutor_html(text):
    """Display-only Markdown: raw HTML, links, images and fence attributes stay inert."""
    md = Markdown(extensions=['fenced_code', 'sane_lists'])
    md.preprocessors.deregister('html_block')
    md.parser.blockprocessors.deregister('reference')
    for name in ('html', 'reference', 'link', 'image_link', 'image_reference',
                 'short_reference', 'short_image_ref', 'autolink', 'automail'):
        md.inlinePatterns.deregister(name)
    md.preprocessors.register(_PlainFences(md, md.preprocessors['fenced_code_block'].config),
                              'fenced_code_block', 25)
    return md.convert(text)


def _saved_results(folder):
    """Reuse receipt interpretation without following links or exposing diagnostics."""
    folder = Path(folder)
    paths = [folder / 'session.json', *folder.glob('step-*.json')]
    for name, pattern in (('tutor-exchanges', '*'), ('lesson', 'tutor-*')):
        directory = folder / name
        if directory.is_symlink():
            raise ValueError('Saved exchange folders must not be symlinks.')
        paths.append(directory / 'receipt.json')
        for exchange in directory.glob(pattern):
            if exchange.is_symlink():
                raise ValueError('Saved exchanges must not be symlinks.')
            if exchange.is_dir():
                paths.extend(exchange / name for name in ('receipt.json', 'context.json'))
    if any(path.is_symlink() for path in paths):
        raise ValueError('Saved exchange files must not be symlinks.')
    return _tutor_html(workspace_history.render(folder, diagnostics=False))


class Binding(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    session_sha256: str = Field(min_length=64, max_length=64, pattern=r'^[0-9a-f]{64}$')
    state_sha256: str = Field(min_length=64, max_length=64, pattern=r'^[0-9a-f]{64}$')


class Submission(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    binding: Binding
    mode: Literal['advance', 'reply', 'policy']
    text: str | None = Field(default=None, max_length=64000)
    use_evidence: bool = False

    @model_validator(mode='after')
    def mode_text(self):
        if self.mode == 'advance' and 'text' in self.model_fields_set:
            raise ValueError('Quiet continuation does not accept tutor text.')
        if self.mode != 'advance' and (self.text is None or not self.text.strip()):
            raise ValueError('Supply nonblank tutor instructions or a reply.')
        return self


class PolicyCreation(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    source_id: str = Field(min_length=64, max_length=64, pattern=r'^[0-9a-f]{64}$')
    binding: Binding
    current_policy: str = Field(min_length=1, max_length=64000)
    proposed_policy: str = Field(min_length=1, max_length=64000)

    @model_validator(mode='after')
    def distinct_policies(self):
        if not self.current_policy.strip() or not self.proposed_policy.strip():
            raise ValueError('Enter both tutor policies.')
        if self.current_policy.strip() == self.proposed_policy.strip():
            raise ValueError('Policy B must differ from Policy A.')
        return self


class PolicyRun(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    comparison_id: str = Field(min_length=1, max_length=128)
    comparison_sha256: str = Field(min_length=64, max_length=64, pattern=r'^[0-9a-f]{64}$')


class NextExercise(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    binding: Binding
    exercise_sha256: str = Field(min_length=64, max_length=64, pattern=r'^[0-9a-f]{64}$')


def _exercise_path(path):
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('Exercise paths must not contain symlinks.')
    return path.resolve()


def _policy_prefix(state):
    episode = state['episode']
    return {'context':[{key:turn[key] for key in ('role', 'text', 'origin')}
                       for turn in [*episode['context'], *episode['turns']]],
            'turns':[{'role':'student', 'text':state['message'], 'origin':'generated'}]}


def _question_summary(state):
    episode = state['episode']
    text = state['message'] or next((turn['text'] for turn in
        reversed([*episode['context'], *episode['turns']])
        if turn['role'] == 'student' and turn['text'].strip()), '')
    text = ' '.join(text.split())
    return text[:160] + ('…' if len(text) > 160 else '')


def _chat_summary(folder):
    if folder.is_symlink() or any(path.is_symlink() for path in folder.rglob('*')):
        raise ValueError('Saved conversation paths must not be symlinks.')
    with (folder / '.lock').open('rb') as stream:
        fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
        _, state, _ = chat_student._load(folder)
        return _question_summary(state)


def _frame(manifest, state, previous, decisions, index):
    before = previous['work'] if previous is not None else state['work']
    lines = difflib.unified_diff(before['source'].splitlines(keepends=True),
        state['work']['source'].splitlines(keepends=True), fromfile='previous saved work', tofile='saved work')
    diff = ''.join(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n' for line in lines)
    feedback = student.notebook_session._feedback(state['observation'])
    if feedback is not None and feedback['status'] == 'environment-error':
        feedback['error'] = {'message':'Local execution was unavailable; this work is ungraded.'}
    history = state['history'][len(previous['history']):] if previous is not None else []
    return {'label':f'Saved step {index}' if index else 'Initial state',
        'binding':{'session_sha256':student.digest(manifest), 'state_sha256':student.digest(state)},
        'status':state['status'], 'decisions_remaining':manifest['max_decisions'] - decisions,
        'work':{key:state['work'][key] for key in ('cell_index', 'revision', 'source')},
        'dialogue':[{'role':turn['role'], 'text':turn['text'], 'origin':turn.get('origin')}
                    for turn in state['dialogue']],
        'pending_message':state['message'] if state['status'] == 'awaiting-tutor' else None,
        'feedback':feedback,
        'changes':{'baseline_revision':before['revision'],
                   'baseline_kind':'previous-saved-step' if previous is not None else 'initial-work',
                   'unified_diff':diff},
        'actions':[{key:event['action'][key] for key in ('decision', 'text', 'source')} for event in history]}


def _chat_snapshot(folder):
    with (Path(folder) / '.lock').open('rb') as stream:
        fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
        manifest, _, _ = chat_student._load(Path(folder))
        receipts = [student._read(path) for path in sorted(Path(folder).glob('step-*.json'))]
        evidence, guided_states = student_evidence.verify(folder, manifest, receipts)
        states = [chat_student._initial(manifest['query']), *(receipt['result'] for receipt in receipts)]
        frames = []
        for index, state in enumerate(states):
            episode = state['episode']
            receipt = receipts[index - 1] if index else None
            frames.append({'label':(f'Student decision {index}' if receipt['status'] == 'complete' else f'Failed attempt {index}') if index else 'Starting conversation',
                'evidence_guidance_used': bool(receipt and receipt['request']['binding']['state_sha256'] in guided_states),
                'binding':{'session_sha256':student.digest(manifest), 'state_sha256':student.digest(state)},
                'status':state['status'], 'decisions_remaining':manifest['max_decisions'] - index,
                'dialogue':[{key:turn[key] for key in ('role', 'text', 'origin')}
                            for turn in [*episode['context'], *episode['turns']]],
                'pending_message':state['message'] if state['status'] == 'awaiting-tutor' else None,
                'work':None, 'feedback':None, 'changes':None,
                'actions':[{key:receipt['response'][key] for key in ('decision', 'text')} | {'source':None}]
                    if receipt is not None and receipt['status'] == 'complete' else []})
        saved_results = _saved_results(folder)
    return {'version':1, 'kind':'chat', 'encounters':[{
        'id':'1', 'title':'Conversation', 'task':'Conversation scenario',
        'evidence_card': evidence,
        'initialization':'Supplied conversation prefix followed by saved simulated continuation. '
            'The prefix may be recorded or authored; its saved origin alone does not establish this. '
            'Notebook activity and outcomes are unknown. Code in a message is text only.',
        'activity':None, 'frames':frames, 'saved_results_html':saved_results}]}


def snapshot(folder, *, chat_mode=False):
    """Project only display evidence after verifying every saved predecessor and receipt."""
    if chat_mode:
        return _chat_snapshot(folder)
    encounters = []
    with ExitStack() as stack:
        for number, (encounter_folder, manifest, _, receipts, _) in enumerate(notebook_next_task.lineage(folder, stack), 1):
            initial = manifest['initial']
            frames = [_frame(manifest, initial, None, 0, 0)]
            previous, decisions = initial, 0
            for index, receipt in enumerate(receipts, 1):
                state = receipt['result']['state']
                decisions += sum(call['kind'] == 'model' for call in receipt['calls'])
                frames.append(_frame(manifest, state, previous, decisions, index))
                previous = state
            encounters.append({'id':str(number), 'title':f'Task {number}', 'task':initial['task'],
                'evidence_card':student_evidence.supplied_card(initial['dialogue']),
                'initialization':initial['initialization'],
                'activity':{key:value for key,value in initial['activity'].items() if key != 'image_id'},
                'frames':frames, 'saved_results_html':_saved_results(encounter_folder)})
    return {'version':1, 'kind':'notebook', 'encounters':encounters}


def _page():
    # ponytail: reuse the single preview shell; extract a template if the layouts diverge.
    page = (ROOT / 'docs/prototypes/student-workspace.html').read_text(encoding='utf-8')
    page, count = re.subn(r'<script>.*?</script>', '<script src="/workspace.js"></script>', page, flags=re.S)
    if count != 1:
        raise ValueError('The workspace shell must have exactly one replaceable script.')
    for before, after in (
        ('Student simulation workspace · Design prototype', 'Saved student workspace'),
        ('Authored demo · Backend disconnected', 'Saved session · Read only'),
        ('<div class="breadcrumb">DSC 10</div>', '<div class="breadcrumb">Notebook session</div>'),
        ('Reset all demo changes', 'Reload saved session'), ('Reset demo', 'Reload saved session'),
        ('Filter sample cases', 'Filter saved tasks'),
        ('class="body-grid"', 'class="body-grid no-inspector"'),
        ('<h1 id="case-title"></h1>', '<h1 id="case-title">Loading saved workspace…</h1>'),
        ('<div class="canvas" id="canvas"></div>',
         '<div class="canvas" id="canvas"><p>Loading saved evidence. No simulation will run.</p>'
         '<noscript>Enable JavaScript to inspect this saved session.</noscript></div>'),
        ('id="playback"', 'id="playback" hidden'),
    ):
        page = page.replace(before, after)
    return page


def _policy_comparison(folder, expected_pin, *, sources=None):
    """Project a fixed one-decision pair under read-only locks, with shared context once."""
    if folder.is_symlink() or any(path.is_symlink() for path in folder.rglob('*')):
        raise ValueError('Policy comparison paths must not be symlinks.')
    manifest_path = folder / 'comparison.json'
    if sha256(manifest_path.read_bytes()).hexdigest() != expected_pin:
        raise ValueError('The policy comparison changed after opening this workspace.')
    receipt = chat_policy_pair._comparison(folder)
    plan = receipt['plan']
    if plan['max_new_decisions'] != 1:
        raise ValueError('This view requires one student decision per policy.')
    conditions, prefix = [], None
    with ExitStack() as stack:
        for name in ('a', 'b'):
            stream = stack.enter_context((folder / 'sessions' / name / '.lock').open('rb'))
            fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
        for name in ('a', 'b'):
            child, _, first = chat_policy_pair._startup(folder, receipt, name)
            # Validate every path component read by the pair's receipt-link checks.
            for path in child.glob('step-*.json'):
                Binding.model_validate(student._read(path)['request']['binding'])
            for path in (child / 'tutor-exchanges').iterdir() if (child / 'tutor-exchanges').exists() else []:
                if not re.fullmatch(r'[0-9a-f]{64}', path.name) or not path.is_dir():
                    raise ValueError('Invalid saved tutor exchange path.')
            status = chat_policy_pair._condition_lifecycle(folder, receipt, name)
            if prefix is None:
                prefix = _policy_prefix(first['result'])
            exchanges = list((child / 'tutor-exchanges').glob('*/receipt.json'))
            if len(exchanges) > 1:
                raise ValueError('A one-decision policy arm has multiple tutor exchanges.')
            tutor = student._read(exchanges[0]) if exchanges else None
            tutor_reply = tutor['response']['text'] if tutor and tutor['status'] == 'complete' else None
            student_reply = None
            if status == 'student-replied':
                _, state, _ = chat_student._load(child)
                student_reply = state['message']
            conditions.append({'id':name, 'title':f'Policy {name.upper()}',
                               'policy':plan['policies'][name], 'status':status,
                               'tutor_reply':tutor_reply, 'student_reply':student_reply})
    if sha256(manifest_path.read_bytes()).hexdigest() != expected_pin:
        raise ValueError('The policy comparison changed during inspection.')
    binding = {key:plan['source'][key] for key in ('session_sha256', 'state_sha256')}
    matches = [source for source in sources or [] if source['binding'] == binding]
    source = ({key:matches[0][key] for key in ('id', 'title', 'summary', 'binding')}
              if len(matches) == 1 else None)
    reason = (None if source else
              'Open a configurable policy workspace to reuse this setup.' if sources is None else
              'Several saved starts share this identity; select a source in a new comparison.' if matches else
              'The original saved start is unavailable or no longer eligible in this workspace.')
    return {'version':1, 'kind':'saved-policy-comparison', 'cases':[{
        'id':plan['comparison_id'], 'title':'Tutor policy comparison', 'model':plan['model'],
        **({'gemini_tutor_model':plan['gemini_tutor_model']} if plan['version'] == 2 else {}),
        'summary':_question_summary(first['result']),
        'source':source, 'reuse_unavailable_reason':reason,
        'context_status':'Both policies start from this supplied conversation and the same cached simulated question. '
                         'The earlier conversation may be recorded or authored; notebook activity is unknown.',
        'prefix':prefix, 'conditions':conditions}]}


def _teaching_comparison(folder, expected_pin):
    """Join a pinned notebook preparation with each arm's verified current replay."""
    if _exercise_path(folder) != folder or any(path.is_symlink() for path in folder.rglob('*')):
        raise ValueError('Teaching comparison paths must not be symlinks.')
    path = folder / 'comparison.json'
    if sha256(path.read_bytes()).hexdigest() != expected_pin:
        raise ValueError('The teaching comparison changed after opening this workspace.')
    receipt = student._read(path)
    if (receipt.get('version') != 1 or receipt.get('status') != 'prepared'
            or receipt.get('source_sha256') != student.digest(Path(notebook_teaching_pair.__file__).read_text())
            or not re.fullmatch(r'[0-9a-f]{32}', receipt.get('comparison_id', ''))
            or not re.fullmatch(r'[0-9a-f]{64}', receipt.get('common_input_sha256', ''))
            or set(receipt.get('sessions', {})) != {'a', 'b'}):
        raise ValueError('The saved teaching-pair preparation is unsupported.')
    conditions, starts, branches = [], [], []
    with ExitStack() as stack:
        for name in ('a', 'b'):
            child = folder / name
            manifest = student._read(child / 'session.json')
            if 'previous_encounter' in manifest['provenance']:
                raise ValueError('Teaching comparisons require fresh initial encounters.')
            lineage = notebook_next_task.lineage(child, stack)
            if len(lineage) != 1 or lineage[0][1] != manifest:
                raise ValueError('The teaching-pair session changed or contains linked tasks.')
            initial = manifest['initial']
            dialogue = initial['dialogue']
            if (len(dialogue) < 2 or [turn['role'] for turn in dialogue[-2:]] != ['student', 'tutor']
                    or any(turn['role'] not in ('student', 'tutor') or not isinstance(turn['text'], str)
                           or not turn['text'].strip() for turn in dialogue)
                    or dialogue[-1] != {'role':'tutor', 'text':dialogue[-1]['text'], 'origin':'supplied'}):
                raise ValueError('The teaching-pair initial dialogue is invalid.')
            recreated = student.notebook_session.initial_state(
                {key:initial[key] for key in ('initialization', 'task', 'work', 'dialogue')},
                activity=initial['activity'], branch_id=initial['branch_id'], timeout=initial['timeout'],
                evaluation=initial.get('evaluation'))
            saved = receipt['sessions'][name]
            if (initial != recreated or student.digest(manifest) != saved['manifest_sha256']
                    or student.digest(dialogue[-1]['text']) != saved['tutor_reply_sha256']
                    or manifest['provenance']['teaching_pair'] != {
                        'comparison_id':receipt['comparison_id'], 'condition':name,
                        'common_input_sha256':receipt['common_input_sha256']}
                    or receipt['max_student_decisions_total'] != 2 * manifest['max_decisions']):
                raise ValueError('The teaching-pair session does not match its preparation.')
            # The original replaced tutor text is not retained, so compare actual shared inputs.
            starts.append({key:manifest[key] for key in ('model', 'max_decisions', 'engine')} | {
                'initial':{key:value for key, value in initial.items() if key not in ('branch_id', 'dialogue')}
                          | {'dialogue':dialogue[:-1]},
                'provenance':{key:value for key, value in manifest['provenance'].items() if key != 'teaching_pair'}})
            branches.append(initial['branch_id'])
            conditions.append({'id':name, 'tutor_reply':dialogue[-1]['text'],
                               'encounter':snapshot(child)['encounters'][0]})
        if starts[0] != starts[1] or branches[0] == branches[1]:
            raise ValueError('Teaching conditions must share initial inputs and have separate execution identities.')
        if sha256(path.read_bytes()).hexdigest() != expected_pin:
            raise ValueError('The teaching comparison changed during inspection.')
    shared = starts[0]['initial']
    return {'version':1, 'kind':'saved-notebook-teaching-comparison', 'cases':[{
        'id':receipt['comparison_id'], 'title':'Notebook teaching comparison',
        'context_status':'Both conditions share this initial task and work, with different supplied tutor replies. '
                         'Saved simulated outcomes do not establish learning or tutor effects.',
        'task':shared['task'], 'initial_work':shared['work'],
        'prefix':{'context':[], 'turns':[{key:turn[key] for key in ('role', 'text', 'origin') if key in turn}
                                       for turn in shared['dialogue']]},
        'conditions':conditions}]}


def _recorded_snapshot(replay):
    frames = []
    for index, event in enumerate(replay['events']):
        recorded = notebook_replay.recorded_frame(replay, index)
        if recorded['notebook_capture']:
            for cell in recorded['notebook_capture']['cells']:
                if cell['cell_type'] == 'markdown':
                    cell['display_html'] = _tutor_html(cell['source'])
        dialogue = [{**turn, 'origin':'source',
                     **({'display_html':_tutor_html(turn['text'])} if turn['role'] == 'tutor' else {})}
                    for turn in recorded['dialogue']]
        frames.append({'label':f"Event {event['sequence']} · {event['title']}",
                       'status':'recorded', 'dialogue':dialogue, 'pending_message':None,
                       'actions':[], 'recorded':recorded})
    boundary_index = next(i for i, event in enumerate(replay['events'])
                          if event['sequence'] == replay['boundary_sequence'])
    return {'version':1, 'kind':'recorded-notebook',
            'encounters':[{'id':'1', 'title':'Recorded notebook activity',
                           'task':'Recorded notebook observations',
                           'initialization':'Recorded probable instrumentation test; not validated learner behavior.',
                           'frames':frames}],
            'default_step':next((i for i, event in enumerate(replay['events']) if event.get('diff')), boundary_index),
            'provenance':'Recorded events · probable instrumentation test. Observations are not a complete editor history.',
            'recorded_summary':{key:replay[key] for key in ('boundary_sequence', 'summary', 'limitations')},
            'controls':{'send_enabled':False, 'tutor_generation_enabled':False,
                        'blocked_reason':'Recorded evidence is read-only.'},
            'operation':{'status':'idle', 'message':''}}


def _branch_artifact(path, expected_sha256):
    """Read bounded, pinned JSON without following artifact-supplied paths."""
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)) or not path.is_file():
        raise ValueError('Notebook attachment must be a regular file without symlinks.')
    with path.open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if (len(raw) > 1024 * 1024 or not isinstance(expected_sha256, str)
            or re.fullmatch(r'[0-9a-f]{64}', expected_sha256) is None
            or sha256(raw).hexdigest() != expected_sha256):
        raise ValueError('The notebook attachment changed or exceeds the supported size.')
    result = json.loads(raw)
    json.dumps(result, allow_nan=False)
    return result


def _branch_execution(path, expected_sha256, folder, manifest, receipt):
    """Verify the separately saved checks; never follow artifact paths or execute code."""
    result = _branch_artifact(path, expected_sha256)
    if (not isinstance(result, dict) or set(result) != {'version', 'checkpoint_sha256',
            'decision_sha256', 'dataset', 'image_id', 'checks', 'model_calls'}
            or type(result['version']) is not int or result['version'] != 1
            or type(result['model_calls']) is not int or result['model_calls'] != 0
            or receipt is None or receipt['status'] != 'complete'
            or receipt['response']['decision'] != 'revise-work'):
        raise ValueError('Notebook execution requires one completed source revision.')
    decision_raw = (folder / 'decision.json').read_bytes()
    if (result['checkpoint_sha256'] != student.digest(manifest)
            or result['decision_sha256'] != sha256(decision_raw).hexdigest()
            or json.loads(decision_raw) != receipt):
        raise ValueError('Notebook execution does not match the saved branch.')
    dataset = result['dataset']
    if (not isinstance(dataset, dict) or set(dataset) != {'sha256', 'rows', 'columns', 'provenance'}
            or type(dataset['rows']) is not int or not 0 < dataset['rows'] <= 1_000_000_000
            or type(dataset['columns']) is not int or not 0 < dataset['columns'] <= 100_000
            or dataset['provenance'] != 'archived-course-asset; historical bytes/version unverified'
            or not isinstance(dataset['sha256'], str) or re.fullmatch(r'[0-9a-f]{64}', dataset['sha256']) is None
            or not isinstance(result['image_id'], str) or re.fullmatch(r'sha256:[0-9a-f]{64}', result['image_id']) is None
            or not isinstance(result['checks'], list) or len(result['checks']) != 2):
        raise ValueError('Notebook execution metadata is unsupported.')
    sources = {0:manifest['task']['work'], 1:receipt['applied']['work']}
    executions = {'ok':('completed',), 'cell-error':('completed',), 'setup-error':('not-started',),
                  'execution-limit':('attempted',), 'environment-error':('not-started', 'attempted')}
    revisions = set()
    for check in result['checks']:
        if (not isinstance(check, dict) or set(check) != {'revision', 'source_sha256', 'status',
                'execution', 'value', 'error', 'output', 'runtime'}
                or type(check['revision']) is not int or check['revision'] not in sources
                or check['revision'] in revisions or not isinstance(check['status'], str)
                or check['execution'] not in executions.get(check['status'], ())
                or not isinstance(check['output'], str) or len(check['output']) > 8192):
            raise ValueError('Notebook execution checks are unsupported.')
        revision = check['revision']
        revisions.add(revision)
        if (sources[revision]['revision'] != revision
                or check['source_sha256'] != sha256(sources[revision]['source'].encode('utf-8')).hexdigest()):
            raise ValueError('Notebook execution source changed.')
        error, runtime = check['error'], check['runtime']
        if check['status'] == 'ok':
            if type(check['value']) not in (str, int, float, bool, type(None)) or error is not None:
                raise ValueError('Successful notebook execution must report a scalar value.')
        elif (check['value'] is not None or not isinstance(error, dict) or set(error) != {'type', 'message'}
                or not all(isinstance(value, str) for value in error.values())):
            raise ValueError('Failed notebook execution must report an error.')
        if runtime is None:
            if check['status'] in ('ok', 'cell-error'):
                raise ValueError('Completed notebook execution requires runtime metadata.')
        elif (not isinstance(runtime, dict) or set(runtime) != {'python', 'libraries', 'image_id'}
                or not isinstance(runtime['python'], str) or not runtime['python'].strip()
                or runtime['image_id'] != result['image_id']
                or not isinstance(runtime['libraries'], dict) or not runtime['libraries']
                or not all(isinstance(value, str) and value.strip() for pair in runtime['libraries'].items()
                           for value in pair)):
            raise ValueError('Notebook execution runtime is unsupported.')
    return result


def _branch_reaction(path, expected_sha256, execution_sha256, manifest, first, execution):
    receipt = _branch_artifact(path, expected_sha256)
    if (not isinstance(receipt, dict) or set(receipt) != {'status', 'preparation_sha256', 'started_at',
            'finished_at', 'response', 'applied'} or receipt['status'] != 'complete'):
        raise ValueError('A completed saved reaction is required.')
    prepared = _branch_artifact(Path(path).with_name('reaction-preparation.json'), receipt['preparation_sha256'])
    if (not isinstance(prepared, dict) or set(prepared) != {'version', 'model', 'maximum_provider_attempts',
            'results_sha256', 'checkpoint_sha256', 'decision_sha256', 'script_sha256', 'schema', 'task',
            'prompt', 'prompt_sha256', 'authorization'}
            or type(prepared['version']) is not int or prepared['version'] != 1
            or type(prepared['maximum_provider_attempts']) is not int or prepared['maximum_provider_attempts'] != 1
            or not isinstance(prepared['model'], str) or not prepared['model'].strip()
            or prepared['results_sha256'] != execution_sha256
            or prepared['checkpoint_sha256'] != execution['checkpoint_sha256']
            or prepared['decision_sha256'] != execution['decision_sha256']
            or prepared['schema'] != source_branch.action.Action.model_json_schema()
            or not isinstance(prepared['script_sha256'], str)
            or re.fullmatch(r'[0-9a-f]{64}', prepared['script_sha256']) is None
            or not isinstance(prepared['authorization'], str)):
        raise ValueError('The saved reaction is not bound to this branch and execution.')
    times = [first.get('finished_at'), receipt['started_at'], receipt['finished_at']]
    if not all(isinstance(value, str) for value in times):
        raise ValueError('Saved reaction timestamps are required.')
    times = [datetime.fromisoformat(value) for value in times]
    if not all(value.utcoffset() is not None for value in times) or not times[0] <= times[1] <= times[2]:
        raise ValueError('Saved reaction timestamps must follow the original decision.')
    observed = next(check for check in execution['checks'] if check['revision'] == first['applied']['work']['revision'])
    if observed['status'] not in ('ok', 'cell-error') or observed['execution'] != 'completed':
        raise ValueError('The reaction requires a completed execution of the saved edit.')
    task = deepcopy(manifest['task'])
    task['work'] = deepcopy(first['applied']['work'])
    task['history'] = [{'origin':'model', 'action':first['response']}]
    task['observation'] = {key:observed[key] for key in ('status', 'value', 'error', 'output', 'runtime')}
    task['observation']['basis'] = 'Researcher-triggered local execution after the saved edit, using archived course data in a new declared environment. No course grader ran.'
    task['omitted'] = 'Other cells, full table values and the historical kernel are not supplied. The actual local result above belongs to the displayed work.'
    old = 'A revision is only a source edit. No code is executed and no grader result is\navailable. Do not invent checks, outputs, unseen edits or outcomes.'
    new = 'The displayed work was executed locally after the previous simulated edit.\nIts actual result is supplied as observation; no correctness grade is available.\nAny new revision is only a source edit and has not been executed. Do not invent\nchecks, outputs, unseen edits or outcomes. Choose one next action after seeing\nthis feedback; the earlier run was a researcher intervention, not a student choice.'
    prompt = source_branch.action.PROMPT.replace(old, new) + json.dumps(task, ensure_ascii=False, sort_keys=True)
    if (source_branch.action.PROMPT.count(old) != 1 or student.digest(prepared['task']) != student.digest(task) or prepared['prompt'] != prompt
            or prepared['prompt_sha256'] != sha256(prompt.encode('utf-8')).hexdigest()):
        raise ValueError('The saved reaction task or prompt changed.')
    response = source_branch.action.Action.model_validate(receipt['response'])
    if student.digest(receipt['applied']) != student.digest(source_branch.action.apply_action(task, response)):
        raise ValueError('The saved reaction action does not reproduce.')
    return prepared, receipt, observed


def _source_branch_snapshot(folder, expected_pin, execution_path=None, execution_sha256=None,
                            reaction_path=None, reaction_sha256=None):
    manifest, receipt = source_branch.load(folder)
    if student.digest(manifest) != expected_pin:
        raise ValueError('The source checkpoint changed.')
    execution = (_branch_execution(execution_path, execution_sha256, folder, manifest, receipt)
                 if execution_path is not None else None)
    reaction = (_branch_reaction(reaction_path, reaction_sha256, execution_sha256, manifest, receipt, execution)
                if reaction_path is not None else None)
    task = manifest['task']
    initial = {'label':'Captured starting work', 'status':'active', 'decisions_remaining':1,
               'work':task['work'], 'dialogue':[{**turn, 'origin':'source'} for turn in task['dialogue']],
               'pending_message':None, 'feedback':None, 'actions':[],
               'binding':{'session_sha256':expected_pin, 'state_sha256':student.digest(task)},
               'changes':{'baseline_revision':0, 'baseline_kind':'initial-work', 'unified_diff':''}}
    frames = [initial]
    if receipt:
        result = {**initial, 'decisions_remaining':0,
                  'label':'Request pending · no result' if receipt['status'] == 'pending' else 'Failed request',
                  'status':receipt['status']}
        if receipt['status'] == 'complete':
            applied, choice = receipt['applied'], receipt['response']
            result.update(label='Simulated student decision', status='no-reply' if choice['decision'] == 'no-reply'
                          else 'awaiting-tutor' if applied['message'] else 'active',
                          work=applied['work'], actions=[choice],
                          binding={'session_sha256':expected_pin, 'state_sha256':student.digest(applied)},
                          dialogue=initial['dialogue'] + ([{'role':'student', 'text':applied['message'], 'origin':'generated'}]
                                                         if applied['message'] else []),
                          changes={'baseline_revision':0, 'baseline_kind':'previous-saved-step',
                                   'unified_diff':notebook_replay._code_diff(task['work'], applied['work'])})
        frames.append(result)
    for frame in frames:
        if execution is not None:
            check = next(check for check in execution['checks'] if check['revision'] == frame['work']['revision'])
            frame['external_execution'] = {**check, 'dataset':execution['dataset'], 'image_id':execution['image_id']}
            frame['label'] = 'Captured revision 0' if frame['work']['revision'] == 0 else 'Generated revision 1'
        frame['dialogue'] = [{**turn, **({'display_html':_tutor_html(turn['text'])} if turn['role'] == 'tutor' else {})}
                            for turn in frame['dialogue']]
    if reaction is not None:
        prepared, saved, observed = reaction
        applied, choice, previous = saved['applied'], saved['response'], frames[-1]
        frames.append({**{key:value for key,value in previous.items() if key != 'external_execution'},
            'label':'After execution', 'status':'no-reply' if choice['decision'] == 'no-reply'
                else 'awaiting-tutor' if applied['message'] else 'active',
            'work':applied['work'], 'actions':[choice], 'feedback':None,
            'dialogue':previous['dialogue'] + ([{'role':'student', 'text':applied['message'], 'origin':'generated'}]
                                               if applied['message'] else []),
            'binding':{'session_sha256':expected_pin, 'state_sha256':student.digest(applied)},
            'changes':{'baseline_revision':previous['work']['revision'], 'baseline_kind':'previous-saved-step',
                       'unified_diff':notebook_replay._code_diff(previous['work'], applied['work'])},
            'reaction':{'model':prepared['model'], 'status':saved['status'], 'action':choice,
                        'observed_revision':observed['revision'],
                        'observation':{**observed, 'dataset':execution['dataset'], 'image_id':execution['image_id']},
                        'started_at':saved['started_at'], 'finished_at':saved['finished_at']}})
    summary = ('One student decision saved.' if receipt and receipt['status'] == 'complete' else
               'No decision requested.' if receipt is None else 'Request '+receipt['status']+'; no action established. It cannot be resent.')
    return {'version':1, 'kind':'notebook', 'source_only':True, 'encounters':[{
        'id':'1', 'title':'Student continuation from captured work', 'task':task['task'],
        'task_html':_tutor_html('\n\n'.join(cell['source'] for cell in task['task'])),
        'initialization':task['initialization'], 'activity':None, 'frames':frames,
        'saved_results_html':_tutor_html(summary+'\n\n'+('One additional simulated reaction was saved after seeing the local execution result of revision 1. '
            'The original edit was generated before these results; any new edit is unexecuted. '
            'No course grade or learning outcome is established.' if reaction is not None else
            'Local execution attempts for both revisions were saved after generation on archived data. '
            'The simulated student did not see these results; they do not reconstruct historical execution. '
            'No course grade or learning outcome is established.' if execution is not None else
            'Code execution is unavailable. No grade or learning outcome is established.'))}],
        'controls':{'send_enabled':False, 'tutor_generation_enabled':False,
                    'blocked_reason':('Saved retrospective execution checks. This branch is read only.' if execution is not None else
                                      'Source-only branch. Code execution is unavailable.')},
        'operation':{'status':'idle', 'message':''}}


def create_app(folder=None, *, chat_sessions=False, chat_mode=False, comparison=None, policy_comparison=None, policy_workspace=None, fidelity_comparison=None, student_comparison=None, teaching_comparison=None, recorded_replay=None, recorded_sha256=None, notebook_branch=None, notebook_execution=None, notebook_execution_sha256=None, notebook_reaction=None, notebook_reaction_sha256=None, next_exercise_file=None, next_exercise_output=None, send=False, policy=None, reference=None, generate=None, generate_tutor=None, check=None, generate_reply=None, manual_tutor=False, gemini_tutor_model=None, make_student_reply=None):
    if (notebook_execution is None) != (notebook_execution_sha256 is None):
        raise ValueError('Configure both the notebook execution file and its expected SHA-256.')
    if notebook_execution is not None and notebook_branch is None:
        raise ValueError('Notebook execution requires a read-only notebook branch.')
    if (notebook_reaction is None) != (notebook_reaction_sha256 is None):
        raise ValueError('Configure both the notebook reaction file and its expected SHA-256.')
    if notebook_reaction is not None and notebook_execution is None:
        raise ValueError('Notebook reaction requires bound notebook execution results.')
    if notebook_branch is not None:
        if chat_mode or chat_sessions or send or manual_tutor or any(value is not None for value in
                (folder, comparison, policy_comparison, policy_workspace, fidelity_comparison,
                 student_comparison, teaching_comparison, recorded_replay, recorded_sha256, policy, reference,
                 next_exercise_file, next_exercise_output, generate, generate_tutor, generate_reply, check,
                 gemini_tutor_model, make_student_reply)):
            raise ValueError('A source-only notebook branch is read-only and requires no session or tutor configuration.')
        notebook_branch = Path(notebook_branch).absolute()
        branch_pin = student.digest(source_branch.load(notebook_branch)[0])
        if notebook_execution is not None:
            notebook_execution = Path(notebook_execution).absolute()
            notebook_reaction = Path(notebook_reaction).absolute() if notebook_reaction is not None else None
            _source_branch_snapshot(notebook_branch, branch_pin, notebook_execution, notebook_execution_sha256,
                                    notebook_reaction, notebook_reaction_sha256)
    if (recorded_replay is None) != (recorded_sha256 is None):
        raise ValueError('Configure both the recorded replay and its expected SHA-256.')
    if recorded_replay is not None:
        if chat_mode or chat_sessions or send or manual_tutor or any(value is not None for value in
                (folder, comparison, policy_comparison, policy_workspace, fidelity_comparison,
                 student_comparison, teaching_comparison, policy, reference, next_exercise_file,
                 next_exercise_output, generate, generate_tutor, generate_reply, check,
                 gemini_tutor_model, make_student_reply)):
            raise ValueError('Recorded replay is read-only and requires no session or tutor configuration.')
        recorded_replay = Path(recorded_replay).absolute()
        notebook_replay.load_recorded(recorded_replay, recorded_sha256)
    if student_comparison is not None and (folder is not None or chat_mode or chat_sessions or send
            or manual_tutor or any(value is not None for value in (comparison, policy_comparison,
                policy_workspace, fidelity_comparison, teaching_comparison, policy, reference,
                next_exercise_file, next_exercise_output, generate_reply, generate_tutor,
                generate, check, gemini_tutor_model, make_student_reply))):
        raise ValueError('Student reply comparison is read-only and requires no session or tutor configuration.')
    if make_student_reply is not None and (not callable(make_student_reply) or policy_workspace is None
            or gemini_tutor_model is None or not callable(generate_reply)):
        raise ValueError('A local comparison factory requires an explicit tutor model and policy workspace.')
    if gemini_tutor_model is not None and (not isinstance(gemini_tutor_model, str)
            or not gemini_tutor_model.strip() or not chat_mode or chat_sessions
            or not callable(generate_reply) or not callable(generate_tutor) or manual_tutor
            or (policy_workspace is not None and make_student_reply is None)
            or any(value is not None for value in (comparison, policy_comparison,
                fidelity_comparison, teaching_comparison, next_exercise_file, next_exercise_output))):
        raise ValueError('An explicit Gemini tutor requires one chat with student and tutor callbacks.')
    if type(manual_tutor) is not bool or (manual_tutor and (
            not (chat_mode or chat_sessions) or generate_tutor is not None or policy_workspace is not None)):
        raise ValueError('Manual tutor mode requires chat without a tutor callback or policy workspace.')
    if generate_reply is not None:
        if not (chat_mode or chat_sessions) or (policy_workspace is not None and make_student_reply is None):
            raise ValueError('A reply backend requires chat mode without a policy workspace.')
        if generate is not None or not callable(generate_reply) or (not manual_tutor and not callable(generate_tutor)):
            raise ValueError('Supply one callable reply backend and an explicit tutor callback or manual tutor mode.')
    if (next_exercise_file is None) != (next_exercise_output is None):
        raise ValueError('Configure both the next exercise file and its output directory.')
    exercise = None
    if next_exercise_file is not None:
        if folder is None or chat_mode or chat_sessions or any(value is not None for value in
                (comparison, policy_comparison, policy_workspace, fidelity_comparison, teaching_comparison)):
            raise ValueError('A next exercise requires one standalone notebook session.')
        folder = _exercise_path(folder)
        next_exercise_file = _exercise_path(next_exercise_file)
        next_exercise_output = _exercise_path(next_exercise_output)
        raw_exercise = next_exercise_file.read_bytes()
        exercise_sha256 = sha256(raw_exercise).hexdigest()
        exercise = json.loads(raw_exercise)
        if (not isinstance(exercise, dict) or set(exercise) != {'task', 'activity', 'evaluation', 'policy'}
                or not isinstance(exercise['task'], dict)
                or not isinstance(exercise['task'].get('task'), str) or not exercise['task']['task'].strip()
                or not isinstance(exercise['policy'], str) or not exercise['policy'].strip()):
            raise ValueError('Supply a supported exercise with task text and tutor policy.')
        with ExitStack() as stack:
            ancestors = notebook_next_task.lineage(folder, stack)
            if any(next_exercise_output.is_relative_to(entry[0]) or entry[0].is_relative_to(next_exercise_output)
                   for entry in ancestors):
                raise ValueError('Keep the next exercise outside every source session and its parent directories.')
            source_manifest_pin = student.digest(ancestors[-1][1])
    if sum(value is not None for value in (comparison, policy_comparison, policy_workspace, fidelity_comparison, teaching_comparison)) > 1:
        raise ValueError('Choose one comparison: communication review, tutor policies, student fidelity or notebook teaching.')
    if folder is None and ((comparison is None and fidelity_comparison is None and student_comparison is None and teaching_comparison is None and recorded_replay is None and notebook_branch is None) or chat_sessions or chat_mode or send
                           or policy is not None or reference is not None):
        raise ValueError('A session folder is required unless only a read-only comparison is configured.')
    folder = Path(folder).resolve() if folder is not None else None
    if policy_workspace is not None:
        if not (chat_mode or chat_sessions):
            raise ValueError('A policy workspace requires a chat session or collection.')
        policy_workspace = Path(policy_workspace).absolute()
        if policy_workspace.is_symlink():
            raise ValueError('The policy workspace must not be a symlink.')
        policy_workspace = policy_workspace.resolve()
        if policy_workspace == folder or policy_workspace.is_relative_to(folder):
            raise ValueError('Keep the policy workspace outside the source session or collection.')
    if policy_comparison is not None:
        policy_comparison = Path(policy_comparison).absolute()
        if policy_comparison.is_symlink() or (policy_comparison / 'comparison.json').is_symlink():
            raise ValueError('The policy comparison must not be a symlink.')
    policy_comparison_pin = sha256((policy_comparison / 'comparison.json').read_bytes()).hexdigest() if policy_comparison else None
    if comparison is not None and Path(comparison).is_symlink():
        raise ValueError('The comparison folder must not be a symlink.')
    comparison = Path(comparison).resolve() if comparison is not None else None
    comparison_pin = sha256((comparison / 'closure.json').read_bytes()).hexdigest() if comparison else None
    fidelity_comparison = Path(fidelity_comparison).absolute() if fidelity_comparison is not None else None
    fidelity_pins = fidelity.evidence_hashes(fidelity_comparison) if fidelity_comparison is not None else None
    student_comparison = Path(student_comparison).absolute() if student_comparison is not None else None
    student_reply_pins = student_replies.evidence_hashes(student_comparison) if student_comparison is not None else None
    teaching_comparison = _exercise_path(teaching_comparison) if teaching_comparison is not None else None
    teaching_pin = sha256((teaching_comparison / 'comparison.json').read_bytes()).hexdigest() if teaching_comparison is not None else None
    workspace_paths = (folder, comparison, policy_comparison, policy_workspace)
    if notebook_branch is not None:
        workspace_paths += (notebook_branch,)
    if recorded_replay is not None:
        workspace_paths += (recorded_replay,)
    if fidelity_comparison is not None:
        workspace_paths += (fidelity_comparison,)
    if student_comparison is not None:
        workspace_paths += (student_comparison,)
    if teaching_comparison is not None:
        workspace_paths += (teaching_comparison,)
    if exercise is not None:
        workspace_paths += (next_exercise_file, next_exercise_output)
    workspace_id = student.digest([str(path.resolve()) if path is not None else None
        for path in workspace_paths])
    if chat_sessions and chat_mode:
        raise ValueError('Choose one chat session or a chat collection, not both.')
    scenarios = {}
    if chat_sessions:
        scenarios = {student.digest(path.name):path for path in sorted(folder.iterdir())
            if path.is_dir() and not path.is_symlink()
            and (path / 'session.json').is_file() and not (path / 'session.json').is_symlink()}
        if not scenarios:
            raise ValueError('No saved conversation scenarios were found.')
        chat_mode = True
    if policy_workspace is not None and make_student_reply is None and any((path / 'local-student').exists()
                                            for path in (scenarios.values() if scenarios else [folder])):
        raise ValueError('Local student sessions do not support automatic policy-comparison runs.')
    titles = {key:f'Conversation {index:02d}' for index, key in enumerate(scenarios, 1)}
    if policy is not None and (not isinstance(policy, str) or not policy.strip()):
        raise ValueError('The tutor policy must contain nonblank text.')
    if chat_mode and reference is not None:
        raise ValueError('A library reference is only available for notebook sessions.')
    policy = ("Respond concisely to the student's current request using the visible conversation."
              if chat_mode else DEFAULT_POLICY) if policy is None else policy
    reference = notebook_tutor.LibraryReference.model_validate(reference).model_dump() if reference is not None else None
    runner = chat_workspace if chat_mode else student_workspace
    # ponytail: one serving process; use a shared job store if multiple writers are needed.
    running = Lock()
    operations = {key:{'status':'idle', 'message':''} for key in [None, *scenarios]}
    if exercise is not None:
        operations['next'] = {'status':'idle', 'message':''}
    comparison_operation = {'status':'idle', 'message':'', 'comparison_id':None}
    policy_sources, policy_runs = {}, {}
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    def exercise_source(stack):
        for path in (folder, next_exercise_file, next_exercise_output):
            if _exercise_path(path) != path:
                raise ValueError('The configured exercise path changed.')
        if sha256(next_exercise_file.read_bytes()).hexdigest() != exercise_sha256:
            raise ValueError('The configured exercise changed.')
        entries = notebook_next_task.lineage(folder, stack)
        if student.digest(entries[-1][1]) != source_manifest_pin:
            raise ValueError('The source session changed.')
        for source, *_ in entries:
            _exercise_path(source)
            if any(path.is_symlink() for path in source.rglob('*')):
                raise ValueError('Source files must not be symlinks.')
        return entries

    def verify_next(entries, stack):
        if not next_exercise_output.is_dir() or any(path.is_symlink() for path in next_exercise_output.rglob('*')):
            raise ValueError('The saved next exercise is unavailable or changed.')
        child = next_exercise_output / 'session'
        lineage = notebook_next_task.lineage(child, stack)
        receipt = student._read(next_exercise_output / 'next-exercise.json')
        expected = {'version':1, 'exercise_sha256':exercise_sha256,
                    'binding':{'session_sha256':student.digest(entries[-1][1]),
                               'state_sha256':student.digest(entries[-1][2])},
                    'session_sha256':student.digest(lineage[-1][1])}
        if (receipt != expected or lineage[:-1] != entries
                or (next_exercise_output / 'policy.txt').read_text(encoding='utf-8') != exercise['policy']):
            raise ValueError('The saved next exercise does not match its source and configuration.')
        return child

    def next_control():
        control = {'title':'Next exercise', 'task':exercise['task']['task'],
                   'exercise_sha256':exercise_sha256, 'status':'blocked', 'reason':None}
        try:
            with ExitStack() as stack:
                entries = exercise_source(stack)
                if next_exercise_output.exists():
                    verify_next(entries, stack)
                    control['status'] = 'saved'
                elif notebook_next_task._ended(entries[-1][2]):
                    control['status'] = 'ready'
                else:
                    control['reason'] = 'The current task must end with a saved student no-reply before assigning another.'
        except (OSError, ValueError, KeyError, TypeError):
            control['reason'] = 'The next exercise could not be verified. Inspect its saved files before continuing.'
        return control

    @contextmanager
    def policy_source(source_id):
        selected = policy_sources[source_id]['path']
        if selected.is_symlink() or selected.resolve() != selected:
            raise ValueError('The source path changed.')
        if any(path.is_symlink() for path in selected.rglob('*')):
            raise ValueError('The source files changed.')
        with (selected / '.lock').open('rb') as stream:
            fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
            manifest, state, _ = chat_policy_pair._source(selected, local=make_student_reply is not None)
            binding = {'session_sha256':student.digest(manifest), 'state_sha256':student.digest(state)}
            pinned = policy_sources[source_id].get('binding')
            if pinned is not None and binding != pinned:
                raise ValueError('The source changed after this workspace opened.')
            policy_sources[source_id].setdefault('binding', binding)
            yield {'id':source_id, 'title':policy_sources[source_id]['title'], 'binding':binding,
                   'summary':_question_summary(state),
                   'prefix':_policy_prefix(state),
                   'context_status':'This supplied conversation and cached simulated question will start both policies. '
                                    'The conversation may be recorded or authored; notebook activity is unknown.'}

    def run_paths():
        if (policy_workspace.is_symlink() or policy_workspace.resolve() != policy_workspace
                or (policy_workspace / '.lock').is_symlink()):
            raise ValueError('The policy workspace path changed.')
        if not policy_workspace.exists():
            return []
        return sorted(path for path in policy_workspace.iterdir() if re.fullmatch(r'run-\d{4}', path.name))

    def register_run(path):
        if path.is_symlink() or (path / 'comparison.json').is_symlink():
            raise ValueError('Saved comparisons must not be symlinks.')
        pin = sha256((path / 'comparison.json').read_bytes()).hexdigest()
        plan = chat_policy_pair._comparison(path)['plan']
        if ((plan['version'] == 2) != (make_student_reply is not None)
                or plan.get('gemini_tutor_model') != gemini_tutor_model):
            raise ValueError('The saved comparison requires its original tutor and student configuration.')
        case = _policy_comparison(path, pin)['cases'][0]
        if case['id'] in policy_runs:
            raise ValueError('Saved comparison identifiers must be unique.')
        policy_runs[case['id']] = {'path':path, 'pin':pin}
        return case['id']

    def policy_packet():
        if set(run_paths()) != {item['path'] for item in policy_runs.values()}:
            raise ValueError('The saved comparison list changed. Reopen the workspace.')
        cases, sources = [], []
        for source_id in policy_sources:
            try:
                with policy_source(source_id) as source:
                    sources.append(source)
            except (OSError, ValueError, KeyError, TypeError):
                # A continued source cannot seed another pair; its frozen comparisons remain usable.
                continue
        for index, item in enumerate(policy_runs.values(), 1):
            case = _policy_comparison(item['path'], item['pin'], sources=sources)['cases'][0]
            cases.append(case | {'title':f'Policy comparison {index:02d}', 'comparison_sha256':item['pin']})
        return {'version':1, 'kind':'saved-policy-comparison', 'cases':cases,
                'controls':{'create_enabled':True, 'send_enabled':send is True, 'sources':sources,
                    **({'gemini_tutor_model':gemini_tutor_model} if make_student_reply is not None else {})},
                'operation':dict(comparison_operation)}

    if policy_workspace is not None:
        candidates = scenarios if chat_sessions else {student.digest('single-chat-session'):folder}
        for source_id, selected in candidates.items():
            policy_sources[source_id] = {'path':selected, 'title':titles.get(source_id, 'Conversation')}
            try:
                with policy_source(source_id) as source:
                    policy_sources[source_id]['binding'] = source['binding']
            except (OSError, ValueError, KeyError, TypeError):
                pass  # A fresh chat can become eligible after its first saved reply.
        for path in run_paths():
            register_run(path)

    def selection(request):
        if folder is None:
            raise HTTPException(404, 'No replay session is configured for this saved benchmark.')
        params = list(request.query_params.multi_items())
        if not chat_sessions:
            if exercise is not None and params == [('exercise', 'next')]:
                try:
                    child = next_exercise_output / 'session'
                    if _exercise_path(child) != child:
                        raise ValueError('The saved next exercise path changed.')
                    return None, child
                except (OSError, ValueError) as exc:
                    raise HTTPException(409, 'The saved next exercise could not be verified. Reload the original task.') from exc
            if params:
                raise HTTPException(400, 'This workspace uses only the session selected at launch.')
            return None, folder
        if len(params) != 1 or params[0][0] != 'scenario' or params[0][1] not in scenarios:
            raise HTTPException(400, 'Choose one scenario from the workspace catalog.')
        scenario_id = params[0][1]
        selected = scenarios[scenario_id]
        try:
            if (selected.is_symlink() or not selected.is_dir() or selected.resolve().parent != folder
                    or any(path.is_symlink() for path in
                           [selected / 'session.json', selected / '.lock', selected / 'tutor-exchanges',
                            *selected.glob('step-*.json')])):
                raise ValueError('The saved scenario path changed.')
        except (OSError, ValueError) as exc:
            raise HTTPException(409, 'The selected scenario could not be verified; continuation is disabled.') from exc
        return scenario_id, selected

    def blocked(selected, frame):
        if chat_mode and generate_reply is None and (selected / 'local-student').exists():
            return 'Configure the saved local student model and runtime paths to continue this session.'
        if (selected / 'tutor-exchanges' / frame['binding']['state_sha256']).exists():
            return ('A tutor exchange already exists for this saved state. It will not be resent; '
                    'inspect its saved receipt before continuing.')
        return None

    def packet(scenario_id, selected):
        is_next = exercise is not None and selected == next_exercise_output / 'session'
        if is_next:
            with ExitStack() as stack:
                verify_next(exercise_source(stack), stack)
        result = snapshot(selected, chat_mode=chat_mode)
        for encounter in result['encounters']:
            for saved_frame in encounter['frames']:
                for turn in saved_frame['dialogue']:
                    if turn['role'] == 'tutor':
                        turn['display_html'] = _tutor_html(turn['text'])
        if scenario_id is not None:
            result['encounters'][0]['title'] = titles[scenario_id]
        frame = result['encounters'][-1]['frames'][-1]
        result = result | {'scenario_id':scenario_id, 'controls':{'send_enabled':send is True,
            'evidence_guidance_enabled':chat_mode and generate_reply is None and not (selected / 'local-student').exists(),
            'tutor_generation_enabled':not manual_tutor,
            **({'gemini_tutor_model':gemini_tutor_model} if gemini_tutor_model is not None else {}),
            'policy':exercise['policy'] if is_next else policy,
            'reference':{key:reference[key] for key in ('library', 'library_version', 'source')}
                        if reference is not None else None,
            'blocked_reason':blocked(selected, frame)}, 'operation':dict(operations['next' if is_next else scenario_id])}
        if not chat_mode:
            result['exercise'] = 'next' if is_next else 'current'
        if exercise is not None and not is_next:
            result['controls']['next_exercise'] = next_control()
        return result

    def comparison_html(result):
        for case in [*result['cases'], *result.get('controls', {}).get('sources', [])]:
            for turns in case['prefix'].values():
                for turn in turns:
                    if turn['role'] == 'tutor':
                        turn['display_html'] = _tutor_html(turn['text'])
            for condition in case.get('conditions', []):
                if condition.get('tutor_reply') is not None:
                    condition['tutor_html'] = _tutor_html(condition['tutor_reply'])
                for frame in condition.get('encounter', {}).get('frames', []):
                    for turn in frame['dialogue']:
                        if turn['role'] == 'tutor':
                            turn['display_html'] = _tutor_html(turn['text'])
        return result

    @app.middleware('http')
    async def local_requests(request: Request, call_next):
        origin = request.headers.get('origin')
        expected = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if origin is not None and origin != expected or request.headers.get('sec-fetch-site') == 'cross-site':
            response = JSONResponse({'detail':'Open this workspace directly on localhost.'}, status_code=403)
        else:
            response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = (
            "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        return response

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]'])

    @app.get('/', response_class=HTMLResponse)
    @app.get('/student-workspace.html', response_class=HTMLResponse)
    def page():
        return _page()

    @app.get('/workspace.js')
    def script():
        return Response((ROOT / 'apps/browser_workspace.js').read_text(encoding='utf-8'),
                        media_type='text/javascript')

    @app.get('/api/scenarios')
    def catalog(request: Request):
        if request.query_params:
            raise HTTPException(400, 'The scenario catalog does not accept query parameters.')
        entries = []
        for key, selected in scenarios.items():
            try:
                summary = _chat_summary(selected)
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                summary = None
            entries.append({'id':key, 'title':titles[key], 'summary':summary})
        return {'version':1, 'workspace_id':workspace_id, 'scenarios':entries,
                **({'comparison_available':True} if any(value is not None for value in
                   (comparison, policy_comparison, policy_workspace, fidelity_comparison, student_comparison, teaching_comparison)) else {}),
                **({'replay_available':False} if comparison is not None and folder is None else {}),
                **({'fidelity_comparison_available':True, 'replay_available':folder is not None}
                   if fidelity_comparison is not None else {}),
                **({'student_comparison_available':True, 'replay_available':False}
                   if student_comparison is not None else {}),
                **({'teaching_comparison_available':True, 'replay_available':folder is not None}
                   if teaching_comparison is not None else {}),
                **({'policy_workspace_available':True} if policy_workspace is not None else {})}

    @app.get('/api/comparison')
    def comparison_view(request: Request):
        if request.query_params:
            raise HTTPException(400, 'The comparison uses only the saved evidence selected at launch.')
        if all(value is None for value in (comparison, policy_comparison, policy_workspace, fidelity_comparison, student_comparison, teaching_comparison)):
            raise HTTPException(404, 'No saved comparison is configured.')
        if policy_workspace is not None and not running.acquire(blocking=False):
            operation = (dict(comparison_operation) if comparison_operation['status'] == 'running' else
                         {'status':'running', 'message':'The workspace is handling another request. '
                          'Checking progress does not resend it.', 'comparison_id':None})
            return JSONResponse({'version':1, 'kind':'saved-policy-comparison',
                'operation':operation}, status_code=202)
        try:
            result = (policy_packet() if policy_workspace is not None else
                      _policy_comparison(policy_comparison, policy_comparison_pin) if policy_comparison is not None
                      else fidelity.load_comparison(fidelity_comparison, expected_files=fidelity_pins) if fidelity_comparison is not None
                      else student_replies.load_comparison(student_comparison, expected_files=student_reply_pins) if student_comparison is not None
                      else _teaching_comparison(teaching_comparison, teaching_pin) if teaching_comparison is not None
                      else load_comparison(comparison, expected_closure=comparison_pin))
            return comparison_html(result)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise HTTPException(409, 'The saved comparison could not be verified. Its evidence is not displayed.') from exc
        finally:
            if policy_workspace is not None:
                running.release()

    if policy_workspace is not None:
        @app.post('/api/comparison')
        def create_comparison(body: PolicyCreation, request: Request):
            if request.query_params:
                raise HTTPException(400, 'Choose a source from the workspace catalog.')
            if body.source_id not in policy_sources:
                raise HTTPException(400, 'Choose a source from the workspace catalog.')
            if not running.acquire(blocking=False):
                raise HTTPException(409, 'The workspace is busy. Check progress without resending.')
            try:
                policy_packet()  # Verify all registered evidence before the setup helper reads it.
                with policy_source(body.source_id) as source:
                    if source['binding'] != body.binding.model_dump():
                        raise HTTPException(409, 'The displayed source is stale. Reload before saving.')
                    comparison_operation.update(status='running', message='Saving this policy comparison.', comparison_id=None)
                    path, _ = policy_comparison_setup.freeze_next(policy_workspace,
                        source=policy_sources[body.source_id]['path'], current_policy=body.current_policy,
                        proposed_policy=body.proposed_policy, gemini_tutor_model=gemini_tutor_model)
                selected_id = register_run(path)
                comparison_operation.update(status='complete', message='The policy comparison is saved. No requests were sent.',
                                            comparison_id=selected_id)
                return comparison_html(policy_packet()) | {'selected_id':selected_id}
            except HTTPException:
                raise
            except Exception as exc:
                duplicate = isinstance(exc, ValueError) and re.fullmatch(
                    r'This exact scenario and policy pair already exists as run-\d{4}\.', str(exc))
                comparison_operation.update(status='error', message=(
                    'This conversation and policy pair is already saved. Open its existing comparison.' if duplicate else
                    'The comparison could not be saved or verified. '
                    'Check saved comparisons before trying again; identical setups are not recreated.'))
                raise HTTPException(409, comparison_operation['message']) from exc
            finally:
                running.release()

        @app.post('/api/comparison/run')
        def run_comparison(body: PolicyRun, request: Request):
            if request.query_params:
                raise HTTPException(400, 'Choose a saved comparison from the workspace.')
            if send is not True:
                raise HTTPException(403, 'This workspace was opened without sending enabled.')
            if body.comparison_id not in policy_runs:
                raise HTTPException(400, 'Choose a saved comparison from the workspace.')
            if not running.acquire(blocking=False):
                raise HTTPException(409, 'The workspace is busy. Check progress without resending.')
            try:
                item = policy_runs[body.comparison_id]
                if body.comparison_sha256 != item['pin']:
                    raise HTTPException(409, 'The displayed comparison is stale. Reload before running.')
                saved = policy_packet()
                case = next(case for case in saved['cases'] if case['id'] == body.comparison_id)
                if not any(condition['status'] == 'ready' for condition in case['conditions']):
                    raise HTTPException(409, 'This comparison has no untouched conditions to run. Saved attempts are never resent.')
                comparison_operation.update(status='running', message='Running the saved tutor policies and student responses.',
                                            comparison_id=body.comparison_id)
                policy_comparison_setup.run_both(item['path'], send=True,
                    generate_tutor=generate_tutor, generate_student=generate,
                    make_student_reply=make_student_reply, gemini_tutor_model=gemini_tutor_model)
                result = policy_packet()
                case = next(case for case in result['cases'] if case['id'] == body.comparison_id)
                failed = any(condition['status'] in ('failed', 'incomplete') for condition in case['conditions'])
                comparison_operation.update(status='error' if failed else 'complete', message=(
                    'Some requests failed or remain incomplete. Their saved attempts will not be resent.' if failed else
                    'Both policy outcomes are saved.'))
                result['operation'] = dict(comparison_operation)
                return comparison_html(result) | {'selected_id':body.comparison_id}
            except HTTPException:
                raise
            except Exception as exc:
                comparison_operation.update(status='error', message='The run could not complete or be verified. '
                    'Inspect saved outcomes before trying again; saved attempts are never resent.', comparison_id=body.comparison_id)
                raise HTTPException(409, comparison_operation['message']) from exc
            finally:
                running.release()

    if exercise is not None:
        @app.post('/api/next-exercise')
        def create_next_exercise(body: NextExercise, request: Request):
            if request.query_params:
                raise HTTPException(400, 'Assign the configured exercise from the original task.')
            if not running.acquire(blocking=False):
                raise HTTPException(409, 'The workspace is busy. Reload to inspect saved progress.')
            try:
                with ExitStack() as stack:
                    entries = exercise_source(stack)
                    manifest, state = entries[-1][1:3]
                    binding = {'session_sha256':student.digest(manifest), 'state_sha256':student.digest(state)}
                    if body.binding.model_dump() != binding or body.exercise_sha256 != exercise_sha256:
                        raise HTTPException(409, 'The displayed task or exercise is stale. Reload before saving.')
                    if next_exercise_output.exists():
                        raise HTTPException(409, 'A next exercise already exists. Open its saved result; it will not be recreated.')
                    if not notebook_next_task._ended(state):
                        raise HTTPException(409, 'The current task must end with a saved student no-reply.')
                    child = notebook_example.create(next_exercise_output, previous=folder,
                        image_id=state['activity']['image_id'], exercise=exercise)
                    student._save(next_exercise_output / 'next-exercise.json', {
                        'version':1, 'exercise_sha256':exercise_sha256, 'binding':binding,
                        'session_sha256':student.digest(student._read(child / 'session.json'))}, exclusive=True)
                    verify_next(entries, stack)
                return packet(None, child)
            except HTTPException:
                raise
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise HTTPException(409, 'The next exercise could not be saved or verified. Reload to inspect saved progress; '
                                    'an existing exercise will not be recreated.') from exc
            finally:
                running.release()

    @app.get('/api/workspace')
    def workspace(request: Request):
        if notebook_branch is not None:
            if request.query_params:
                raise HTTPException(400, 'The notebook branch uses only the checkpoint selected at launch.')
            try:
                return _source_branch_snapshot(notebook_branch, branch_pin, notebook_execution, notebook_execution_sha256,
                                                notebook_reaction, notebook_reaction_sha256)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise HTTPException(409, 'The notebook branch could not be verified. Its contents are not displayed.') from exc
        if recorded_replay is not None:
            if request.query_params:
                raise HTTPException(400, 'Recorded replay uses only the evidence selected at launch.')
            try:
                return _recorded_snapshot(notebook_replay.load_recorded(recorded_replay, recorded_sha256))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise HTTPException(409, 'Recorded evidence could not be verified. Its contents are not displayed.') from exc
        scenario_id, selected = selection(request)
        if not running.acquire(blocking=False):
            return JSONResponse({'version':1, 'scenario_id':scenario_id, 'operation':{'status':'running',
                'message':'The workspace is handling a request. Reloading checks progress without resending.'}}, status_code=202)
        try:
            return packet(scenario_id, selected)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise HTTPException(409, 'Saved evidence could not be verified. Check the configured session '
                                'and its original environment; continuation is disabled.') from exc
        finally:
            running.release()

    def continue_session(body: Submission, request: Request):
        scenario_id, selected = selection(request)
        if send is not True:
            raise HTTPException(403, 'This workspace was opened without sending enabled.')
        if manual_tutor and body.mode == 'policy':
            raise HTTPException(403, 'Automatic tutor generation is disabled. Write a tutor reply instead.')
        if not running.acquire(blocking=False):
            raise HTTPException(409, 'The workspace is busy. Reload to inspect its current state; do not resend.')
        is_next = exercise is not None and selected == next_exercise_output / 'session'
        operation = operations['next' if is_next else scenario_id]
        try:
            if is_next:
                with ExitStack() as stack:
                    verify_next(exercise_source(stack), stack)
            current = snapshot(selected, chat_mode=chat_mode)['encounters'][-1]['frames'][-1]
            binding = body.binding.model_dump()
            if binding != current['binding']:
                raise HTTPException(409, 'The displayed state is stale. Reload before continuing.')
            if reason := blocked(selected, current):
                raise HTTPException(409, reason)
            ready = 'ready' if chat_mode else 'active'
            if current['status'] not in (ready, 'awaiting-tutor') or current['decisions_remaining'] <= 0:
                raise HTTPException(409, 'This encounter has stopped or used its decision budget.')
            if (body.mode == 'advance') != (current['status'] == ready):
                raise HTTPException(409, 'Tutor guidance requires a pending student message; continuation does not accept it.')
            student_generator = generate
            if body.use_evidence:
                if not chat_mode or generate_reply is not None or (selected / 'local-student').exists():
                    raise HTTPException(400, 'Evidence guidance is available for the chat provider backend only.')
                backend = generate or partial(student_workspace._generate_model,
                    student._read(selected / 'session.json')['model'], single_attempt=True)
                student_generator = student_evidence.guided(selected, binding, backend)
            if body.mode == 'policy':
                runner.respond(selected, binding=binding, policy=body.text, send=True,
                    generate_tutor=generate_tutor, generate_student=student_generator,
                    **({'generate_reply':generate_reply, 'gemini_tutor_model':gemini_tutor_model}
                       if chat_mode else {'check':check, 'reference':reference}))
            else:
                runner.advance(selected, binding=binding,
                    tutor_reply=body.text if body.mode == 'reply' else None,
                    send=True, generate=student_generator,
                    **({'generate_reply':generate_reply} if chat_mode else {'check':check}))
            result = packet(scenario_id, selected)
            failed = result['encounters'][-1]['frames'][-1]['status'] in ('error', 'environment-error', 'execution-limit')
            operation.update(status='error' if failed else 'complete', message=(
                ('The simulation stopped after a generation error. Inspect the saved result.' if chat_mode else
                 'The simulation stopped after an error or unavailable local check. Inspect the saved result.')
                if failed else 'One student decision was saved.'))
            result['operation'] = dict(operation)
            return result
        except HTTPException:
            raise
        except Exception as exc:
            operation.update(status='error', message=(
                'The request could not complete. Reload to inspect saved evidence; it will not be automatically resent.'))
            raise HTTPException(409, operation['message']) from exc
        finally:
            running.release()

    if recorded_replay is None and notebook_branch is None:
        app.post('/api/continue')(continue_session)
    return app


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, nargs='?', help='Saved session or conversation collection; omit for a read-only communication, fidelity or teaching comparison.')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--chat', action='store_true', help='Open a chat-only session; notebook state remains unknown.')
    mode.add_argument('--chat-sessions', action='store_true', help='Choose among saved chat sessions directly inside the folder.')
    parser.add_argument('--port', type=int, default=8427)
    compare = parser.add_mutually_exclusive_group()
    compare.add_argument('--comparison', type=Path, help='Completed cached communication review folder for read-only Compare.')
    compare.add_argument('--policy-comparison', type=Path, help='Saved one-decision tutor-policy pair for read-only Compare.')
    compare.add_argument('--policy-workspace', type=Path, help='Directory for creating saved policy pairs from eligible chat starts.')
    compare.add_argument('--fidelity-comparison', type=Path, help='Completed fixed help/work benchmark for read-only student fidelity comparison.')
    compare.add_argument('--student-comparison', type=Path, help='Saved base and trained student replies; read-only, without a session folder.')
    compare.add_argument('--teaching-comparison', type=Path, help='Saved notebook teaching-pair sessions directory containing a, b and comparison.json.')
    compare.add_argument('--recorded-replay', type=Path, help='Verified recorded notebook projection; exclusive read-only playback.')
    compare.add_argument('--notebook-branch', type=Path, help='Saved source-only notebook checkpoint and one student choice; read-only.')
    parser.add_argument('--recorded-sha256', help='Expected SHA-256 of the recorded replay projection; required with --recorded-replay.')
    parser.add_argument('--notebook-execution', type=Path, help='Saved retrospective execution results for both notebook branch revisions; read-only.')
    parser.add_argument('--notebook-execution-sha256', help='Expected raw file SHA-256; required with --notebook-execution.')
    parser.add_argument('--notebook-reaction', type=Path, help='Saved student reaction to the attached execution; read-only.')
    parser.add_argument('--notebook-reaction-sha256', help='Expected raw file SHA-256; required with --notebook-reaction.')
    parser.add_argument('--send', action='store_true', help='Enable explicit tutor/student generation and requested local checks.')
    parser.add_argument('--policy-file', type=Path, help='UTF-8 starting tutor instructions, loaded once.')
    parser.add_argument('--reference-file', type=Path, help='Tutor-only library reference JSON, loaded once.')
    parser.add_argument('--next-exercise-file', type=Path, help='One supported exercise JSON to assign after this notebook task ends.')
    parser.add_argument('--next-exercise-output', type=Path, help='Separate directory for that one saved next exercise and policy.')
    parser.add_argument('--student-model', type=Path, help='Existing local MLX model directory for one --chat; tutor replies are typed unless --gemini-tutor-model is supplied.')
    parser.add_argument('--student-python', type=Path, help='Existing Python executable with MLX-LM installed; required with --student-model.')
    parser.add_argument('--student-adapter', type=Path, help='Optional local adapter directory for --student-model.')
    parser.add_argument('--gemini-tutor-model', help='Explicit Gemini tutor model for a local student. Generated tutor replies send conversation and instructions to Google Gemini.')
    args = parser.parse_args()
    try:
        if args.folder is None and (args.chat or args.chat_sessions or args.send or args.policy_file or args.reference_file):
            raise ValueError('Chat, sending and tutor configuration options require a session folder.')
        if (args.chat or args.chat_sessions) and args.reference_file:
            raise ValueError('A library reference is only available for notebook sessions.')
        reply = None
        tutor = None
        reply_factory = None
        if args.gemini_tutor_model is not None and (not args.gemini_tutor_model.strip()
                or not args.student_model or not args.student_python):
            raise ValueError('--gemini-tutor-model requires a nonblank model and local student model/runtime paths.')
        if any((args.student_model, args.student_python, args.student_adapter)):
            if not (args.folder and args.chat and args.student_model and args.student_python) or any((
                    args.comparison, args.policy_comparison, args.fidelity_comparison, args.student_comparison,
                    args.teaching_comparison, args.recorded_replay, args.notebook_branch, args.next_exercise_file, args.next_exercise_output)):
                raise ValueError('Local students require one --chat, --student-model and --student-python, without comparison or exercise options.')
            if args.policy_file and args.gemini_tutor_model is None:
                raise ValueError('A local student policy file requires --gemini-tutor-model.')
            if args.policy_workspace and args.gemini_tutor_model is None:
                raise ValueError('Local policy comparisons require --gemini-tutor-model.')
            from src.agents.local_student import make_reply
            configured_reply = partial(make_reply, model=args.student_model, python=args.student_python, adapter=args.student_adapter)
            reply = configured_reply(args.folder)
            reply_factory = configured_reply if args.policy_workspace else None
            if args.gemini_tutor_model is not None:
                tutor = partial(student_workspace._generate_model, args.gemini_tutor_model, single_attempt=True)
        policy = args.policy_file.read_text(encoding='utf-8') if args.policy_file else None
        reference = notebook_tutor.LibraryReference.model_validate_json(
            args.reference_file.read_text(encoding='utf-8')).model_dump() if args.reference_file else None
        app = create_app(args.folder, chat_sessions=args.chat_sessions, chat_mode=args.chat, comparison=args.comparison,
                         policy_comparison=args.policy_comparison, policy_workspace=args.policy_workspace,
                         fidelity_comparison=args.fidelity_comparison, student_comparison=args.student_comparison,
                         teaching_comparison=args.teaching_comparison,
                         recorded_replay=args.recorded_replay, recorded_sha256=args.recorded_sha256,
                         notebook_branch=args.notebook_branch,
                         notebook_execution=args.notebook_execution, notebook_execution_sha256=args.notebook_execution_sha256,
                         notebook_reaction=args.notebook_reaction, notebook_reaction_sha256=args.notebook_reaction_sha256,
                         next_exercise_file=args.next_exercise_file, next_exercise_output=args.next_exercise_output,
                         send=args.send, policy=policy, reference=reference,
                         generate_reply=reply, generate_tutor=tutor,
                         manual_tutor=reply is not None and tutor is None, gemini_tutor_model=args.gemini_tutor_model,
                         make_student_reply=reply_factory)
    except (OSError, ValueError) as exc:
        parser.error(f'Workspace configuration could not be loaded: {exc}')
    uvicorn.run(app, host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
