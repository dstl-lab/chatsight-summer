"""Prepare a private two-stage human review; never supply human judgments."""
from hashlib import sha256
import json
from pathlib import Path
import re

from src.agents import behavior_evidence as evidence

RUBRIC = 'requested-assistance-human-v1'
KINDS = ['hint', 'explanation', 'solution', 'checking', 'unspecified']
INSTRUCTIONS = '''Judge only the highlighted student message. In stage 1 it is the most recent student message in the prefix; later tutor replies and the next student outcome are absent. In stage 2 it is the next student message, with earlier dialogue available as context.
Hint: asks for limited guidance without a full answer. Explanation: asks what something means or why it works. Solution: asks to produce, finish or correct an answer/code. Checking: asks to assess or diagnose supplied or referred-to work. Unspecified: asks for help without a supported kind.
Select multiple kinds only when the message expresses multiple requests. If kinds are competing interpretations of one unclear request, choose Unclear and describe the ambiguity. Do not add Unspecified to a request whose kind is already clear.
No request means the message expresses no assistance request; this is not student silence. Unclear means the available message/context is insufficient. Neither means the reviewer skipped the item. Bare work, quoted task instructions, negated requests, politeness and a tutor's invitation do not automatically express a student request.
Cite numbered source lines: include the highlighted message and any earlier lines needed to resolve it. For No request, cite every nonblank highlighted-message line. For Unclear, cite the ambiguous message and explain what is unresolved. Do not infer hidden ability, motivation, progress, correctness or learning. Redactions that prevent interpretation are a reason to mark Unclear.
Use only this packet. Do not consult old judgments or a model. Report prior familiarity honestly; these are already exposed development cases, not an independent blind test. Keep downloaded responses private. No network requests are made; the page does not autosave. Save a draft before closing.'''
EXAMPLES = [
    ('Synthetic: "Just a hint, please."', 'Definite: hint.'),
    ('Synthetic: "Explain range, and check my loop."', 'Definite: explanation + checking (two expressed requests).'),
    ('Synthetic: "Can you help?"', 'Definite: unspecified.'),
    ('Synthetic: "result = 3"', 'No request, if context does not make it a question.'),
    ('Synthetic: "2?" without a task or resolving context', 'Unclear; do not guess checking versus an answer/task reference.'),
    ('Synthetic: "The assignment says: explain your answer."', 'Quoted instructions alone are not an expressed request to the tutor.'),
]


def digest(value):
    return sha256(evidence.canonical(value).encode()).hexdigest()


def redact(text, identifiers):
    counts = {'identifiers': 0, 'emails': 0, 'urls': 0}
    for ident in sorted(set(identifiers), key=len, reverse=True):
        if ident:
            counts['identifiers'] += text.count(ident)
            text = text.replace(ident, '[IDENTIFIER REDACTED]')
    text, counts['emails'] = re.subn(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[EMAIL REDACTED]', text)
    text, counts['urls'] = re.subn(r'https?://[^\s<>]+', '[URL REDACTED]', text)
    return text, counts


def prepare(packet):
    admitted = evidence.admit(packet)
    if not packet['records'] or any(r['membership'] != 'development' for r in packet['records']):
        raise ValueError('Use development records only.')
    if any(r['status'] == 'rejected' for r in admitted['records']):
        raise ValueError('Resolve rejected source records before preparing a review.')
    events = {e['id']: e for e in packet['events']}
    identifiers = [r[k] for r in packet['records'] for k in ('account_id', 'conversation_id') if r[k]]
    # Stable anonymous ordering independent of original study aliases.
    records = sorted(packet['records'], key=lambda r: digest({'review-order': r['id']}))
    stages = {phase: {'version': 1, 'rubric_id': RUBRIC, 'phase': phase,
        'synthetic': packet['synthetic'], 'instructions': INSTRUCTIONS, 'examples': EXAMPLES,
        'kinds': KINDS, 'cases': []} for phase in ('prefix', 'outcome')}
    mapping = {'source_packet_sha256': digest(packet), 'cases': []}
    for index, row in enumerate(records, 1):
        case_id = f'R{index:02}'
        prefix = [events[eid] for eid in row['prefix_event_ids'] if events[eid]['kind'] != 'execution']
        positions = [i for i, e in enumerate(prefix) if e['kind'] == 'student']
        if not positions:
            raise ValueError('A prefix judgment requires a previous student message.')
        focus = positions[-1]
        raw_stages = {'prefix': prefix[:focus+1], 'outcome': [*prefix, events[row['outcome_event_id']]]}
        private = {'case_id': case_id, 'source_record_id': row['id'], 'stages': {}}
        for phase, source_turns in raw_stages.items():
            turns = []; bindings = []
            for n, event in enumerate(source_turns, 1):
                text, redactions = redact(event['text'], identifiers)
                turn_id = f'T{n:02}'
                lines = [{'line': k, 'text': line} for k, line in enumerate(text.splitlines(), 1) if line.strip()]
                turns.append({'id': turn_id, 'role': event['kind'], 'lines': lines})
                bindings.append({'turn_id': turn_id, 'event_id': event['id'],
                    'source_sha256': event['sha256'], 'display_sha256': digest(lines), 'redactions': redactions})
            stages[phase]['cases'].append({'id': case_id, 'focus_turn_id': turns[-1]['id'], 'turns': turns})
            private['stages'][phase] = bindings
        mapping['cases'].append(private)
    stages['prefix']['packet_id'] = digest(stages['prefix'])
    stages['outcome']['prefix_packet_id'] = stages['prefix']['packet_id']
    stages['outcome']['prefix_cases'] = [
        {'id': c['id'], 'focus_turn_id': c['focus_turn_id'],
         'turns': [{'id': t['id'], 'lines': [{'line': l['line']} for l in t['lines']]} for t in c['turns']]}
        for c in stages['prefix']['cases']]
    stages['outcome']['packet_id'] = digest(stages['outcome'])
    return stages | {'mapping': mapping}


def blank(packet):
    return {'version': 1, 'rubric_id': RUBRIC, 'packet_id': packet['packet_id'], 'phase': packet['phase'],
        'reviewer_alias': None, 'prior_exposure': None, 'human_attestation': False,
        'no_prior_labels_or_model': False, 'prefix_before_outcome': False,
        'completed': False, 'completed_at': None, 'prefix_response_sha256': None,
        'judgments': [{'case_id': c['id'], 'status': None, 'labels': None, 'evidence': [], 'note': ''}
                      for c in packet['cases']]}


def write(built, folder):
    folder = Path(folder)
    if folder.exists():
        raise FileExistsError(folder)
    template = Path(__file__).with_suffix('.html').read_text()
    script = Path(__file__).with_suffix('.js').read_text()
    if template.count('__PAYLOAD__') != 1 or template.count('__SCRIPT__') != 1:
        raise ValueError('Unexpected review template.')
    folder.mkdir(parents=True, exist_ok=False)
    for number, phase in enumerate(('prefix', 'outcome'), 1):
        packet = built[phase]
        encoded = json.dumps(packet, ensure_ascii=True).replace('<', '\\u003c')
        (folder/f'{number:02}-{phase}.html').write_text(template.replace('__PAYLOAD__', encoded).replace('__SCRIPT__', script))
        (folder/f'{number:02}-{phase}-blank.json').write_text(evidence.canonical(blank(packet)))
    (folder/'private-mapping.json').write_text(evidence.canonical(built['mapping']))
    (folder/'README.txt').write_text('PRIVATE DEVELOPMENT REVIEW — do not upload or share publicly.\n\n'
        '1. Open 01-prefix.html. Read the rubric. Judge six prior student requests without opening stage 2.\n'
        '2. Download completed prefix responses and keep the file unchanged.\n'
        '3. Open 02-outcome.html. Load that completed prefix response file to unlock six next-message judgments.\n'
        '4. Download completed outcome responses. Return both response JSON files privately.\n\n'
        'Existing judgments are not displayed. private-mapping.json is for later provenance/import only; do not consult it during review.\n'
        'Blank JSON templates are supplied for inspection; use the HTML forms for review. No answers have been filled in.\n'
        'These pages make no network calls and do not autosave. Draft downloads preserve unfinished null fields.\n'
        'Known account/conversation identifiers, emails and URLs are redacted. Other identifying context may remain.\n'
        'This is not certified deidentification. Keep the packet and responses local/private.\n')
    return folder
