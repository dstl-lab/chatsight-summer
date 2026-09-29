"""Authored setup evidence travels through the existing tutor-only reference input."""
from copy import deepcopy
import json
import sys

import pytest

from src.agents import notebook_branch as branch, notebook_student as store, notebook_tutor as tutor
from src.eval.notebook_session import Action
from tests.test_notebook_session import ACTIVITY, TASK


def test_selected_setup_reference_is_bound_create_only_and_tutor_only(tmp_path, monkeypatch, capsys):
    from src.agents import notebook_course_context as context
    recovered = {'notebook': {'recorded_at': '2026-01-01T00:00:00Z', 'cells': [
        {'cell_type': 'code', 'source': 'import babypandas as bpd # SETUP_ONLY\nGRADER_EXCLUDED\n'},
        {'cell_type': 'markdown', 'source': 'Find distinct shades.'},
        {'cell_type': 'code', 'source': 'n_shades = 1'},
        {'cell_type': 'code', 'source': 'UNSELECTED_FUTURE'}]},
        'exchange': [{'role': 'student', 'text': 'help?'}, {'role': 'tutor', 'text': 'OLD_TUTOR'}]}
    source = tmp_path / 'source'
    branch.create(source, recovered=recovered, instruction_cells=[1], work_cell=2)
    reference = {'library': 'babypandas', 'library_version': '1.0.0',
                 'text': 'API_ONLY', 'source': 'authored reference'}
    runtime = {'python': '3.12.0', 'libraries': {'babypandas': '1.0.0', 'numpy': '1.26.4'},
               'image_id': 'sha256:' + 'a' * 64}
    inputs = {}
    for name, value in [('recovered', recovered), ('reference', reference), ('runtime', runtime)]:
        inputs[name + '_file'] = tmp_path / (name + '.json')
        store._save(inputs[name + '_file'], value, exclusive=True)
    output = tmp_path / 'course-reference.json'
    monkeypatch.setattr(sys, 'argv', ['notebook_course_context', '--output', str(output),
        '--source-branch', str(source), '--setup-cells', '0', '--line-ranges', '{"0":[1,1]}',
        *[part for name, path in inputs.items() for part in ('--' + name.replace('_', '-'), str(path))]])
    context.main()
    assert json.loads(capsys.readouterr().out)['model_calls'] == 0
    prepared = store._read(output)
    assert tutor.LibraryReference.model_validate(prepared).model_dump() == prepared
    assert 'SETUP_ONLY' in prepared['text'] and 'API_ONLY' in prepared['text']
    assert all(value not in prepared['text'] for value in ['OLD_TUTOR', 'UNSELECTED_FUTURE', 'n_shades =', 'GRADER_EXCLUDED'])
    metadata = store._read(output.with_suffix('.manifest.json'))
    assert metadata['reference_sha256'] == store.digest(prepared)
    assert metadata['runtime'] == runtime and metadata['historical_runtime_verified'] is False
    assert len(metadata['input_pins']) == 4
    assert metadata['setup_cells'] == [{'index': 0, 'lines': [1, 1]}]
    with pytest.raises(FileExistsError):
        context.prepare(output, source_branch=source, setup_cells=[0], **inputs)
    for selection in ([], [0, 0], [True], [1], [2], [3], [-1]):
        with pytest.raises(ValueError):
            context.prepare(tmp_path / 'invalid.json', source_branch=source, setup_cells=selection, **inputs)
        assert not (tmp_path / 'invalid.json').exists()
    with pytest.raises(ValueError, match='bounds'):
        context.prepare(tmp_path / 'invalid.json', source_branch=source, setup_cells=[0],
                        line_ranges={'0': [1, 3]}, **inputs)
    mismatch = deepcopy(runtime)
    mismatch['libraries']['babypandas'] = '2.0.0'
    store._save(inputs['runtime_file'], mismatch)
    with pytest.raises(ValueError, match='runtime'):
        context.prepare(tmp_path / 'invalid.json', source_branch=source, setup_cells=[0], **inputs)
    store._save(inputs['runtime_file'], runtime)
    changed = deepcopy(recovered)
    changed['notebook']['cells'][0]['source'] += '\nCHANGED'
    store._save(inputs['recovered_file'], changed)
    with pytest.raises(ValueError, match='capture'):
        context.prepare(tmp_path / 'invalid.json', source_branch=source, setup_cells=[0], **inputs)

    session = tmp_path / 'session'
    store.create(session, task=TASK, activity=ACTIVITY, branch_id='synthetic/course-context')
    store.step(session, generate=lambda *_: Action(decision='reply', text='help?', source=None), check=None, max_actions=1)
    prompts = []
    def tutor_call(prompt, schema):
        payload = json.loads(prompt.split('POLICY AND CONTEXT JSON:\n')[1])
        assert payload['library_reference'] == prepared
        return tutor.Reply(text='Consider the distinct values.')
    def student_call(prompt, schema):
        prompts.append(prompt)
        return Action(decision='no-reply', text='', source=None)
    tutor.respond(session, tmp_path / 'exchange', policy='Give one hint.', reference=prepared,
                  generate_tutor=tutor_call, generate_student=student_call, check=None, max_actions=1)
    assert len(prompts) == 1 and all(value not in prompts[0] for value in ('SETUP_ONLY', 'API_ONLY'))
