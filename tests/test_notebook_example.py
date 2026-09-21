"""The public notebook setup has explicit facts and no implicit dispatch."""
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

from src.agents import notebook_student as student, notebook_tutor as tutor, tutor_context
from src.eval import notebook_replay, notebook_session


IMAGE = 'sha256:' + 'a' * 64


def files(folder):
    return {str(p.relative_to(folder)): p.read_bytes() for p in folder.rglob('*') if p.is_file()}


def example():
    assert importlib.util.find_spec('src.agents.notebook_example'), 'Public notebook setup is missing'
    from src.agents import notebook_example
    return notebook_example


def test_create_reopen_agent_inputs_and_cli_without_dispatch(tmp_path, monkeypatch, capsys):
    setup = example()
    def forbidden(*args, **kwargs):
        pytest.fail('Example setup dispatched a provider or runtime')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.setattr(student.llm, 'make_generate', forbidden)
    monkeypatch.setattr(student.notebook_runtime, 'check_work', forbidden)
    folder = tmp_path / 'example'
    child = setup.create(folder, image_id=IMAGE)
    assert child == folder / 'session'
    initial = student.load(child)
    assert initial['status'] == 'active' and initial['history'] == [] and initial['observation'] is None
    assert initial['activity']['values'] == ['blue', 'amber', 'blue', 'green']
    assert initial['activity']['image_id'] == IMAGE and initial['activity']['library'] == 'babypandas'
    assert initial['activity']['library_version'] == '1.0.0'
    assert initial['activity']['result'] == 'fraction_blue'
    assert initial['evaluation'] == {'expected': 0.5}
    assert initial['work'] == {'cell_index': 1, 'revision': 0,
        'source': "fraction_blue = (swatches.get('shade') == 'blue').sum()"}
    manifest = student._read(child / 'session.json')
    assert manifest['model'] == 'gemini-2.5-pro' and manifest['max_decisions'] == 6
    assert set(files(folder)) == {'session/session.json', 'session/.lock', 'policy.txt'}
    assert (folder / 'policy.txt').read_text().strip()
    student_prompt = notebook_session.make_prompt(initial)
    assert 'authored' in initial['initialization'].lower()
    student.step(child, check=forbidden, max_actions=1,
        generate=lambda _, schema: schema(decision='reply', text='still stuck', source=None))
    prompts = []
    def scripted_tutor(prompt, schema):
        prompts.append(prompt)
        return schema(text='Divide the count by the number of rows.')
    tutor.respond(child, tmp_path / 'exchange', policy=(folder / 'policy.txt').read_text(),
        generate_tutor=scripted_tutor, check=forbidden, max_actions=1,
        generate_student=lambda _, schema: schema(decision='no-reply', text='', source=None))
    for prompt, marker in ((student_prompt, '\nSTATE JSON:\n'), (prompts[0], '\nPOLICY AND CONTEXT JSON:\n')):
        payload = json.loads(prompt.split(marker)[1])
        context = payload.get('context', payload)
        assert context['task'] == initial['task'] and context['work'] == initial['work']
        assert context['activity']['values'] == initial['activity']['values']
        assert all(secret not in prompt for secret in ('"evaluation"', '"expected"', '0.5'))
    cli = tmp_path / 'cli'
    monkeypatch.setattr(sys, 'argv', ['notebook_example', str(cli), '--image-id', IMAGE])
    setup.main()
    assert 'No model calls or code execution' in capsys.readouterr().out
    assert student.load(cli / 'session')['history'] == []


def test_invalid_existing_and_interrupted_preparation_preserve_destinations(tmp_path, monkeypatch):
    setup = example()
    folder = tmp_path / 'example'
    setup.create(folder, image_id=IMAGE)
    before = files(folder)
    with pytest.raises(FileExistsError):
        setup.create(folder, image_id=IMAGE)
    assert files(folder) == before
    dangling = tmp_path / 'dangling'
    dangling.symlink_to(tmp_path / 'absent')
    with pytest.raises(FileExistsError):
        setup.create(dangling, image_id=IMAGE)
    assert dangling.is_symlink() and not (tmp_path / 'absent').exists()
    with pytest.raises(ValueError):
        setup.create(tmp_path / 'invalid', image_id='latest')
    assert not (tmp_path / 'invalid').exists()
    original = Path.write_text
    def interrupt_policy(path, *args, **kwargs):
        if path.name == 'policy.txt':
            raise KeyboardInterrupt('authored preparation interruption')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'write_text', interrupt_policy)
    with pytest.raises(KeyboardInterrupt):
        setup.create(tmp_path / 'interrupted', image_id=IMAGE)
    assert not (tmp_path / 'interrupted').exists()


@pytest.mark.skipif(not os.environ.get('NOTEBOOK_RUNTIME_IMAGE'), reason='Explicit local container image required')
def test_authored_actions_get_real_feedback_and_saved_replay(tmp_path, monkeypatch):
    setup = example()
    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw: pytest.fail('Scripted test called a model'))
    child = setup.create(tmp_path / 'example', image_id=os.environ['NOTEBOOK_RUNTIME_IMAGE'])
    def scripted(decision, source=None):
        return lambda _, schema: schema(decision=decision, text='', source=source)
    checked = student.step(child, generate=scripted('request-check'),
        check=student.notebook_runtime.check_work, max_actions=1)['state']
    assert checked['observation']['status'] == 'checked'
    assert checked['observation']['success'] is False and checked['observation']['value'] == 2
    edited = student.step(child, generate=scripted('revise-work',
        "fraction_blue = (swatches.get('shade') == 'blue').sum() / len(swatches.get('shade'))"),
        check=student.notebook_runtime.check_work, max_actions=1)['state']
    assert edited['observation'] is None and edited['work']['revision'] == 1
    assert edited['status'] == 'active' and edited['message'] is None
    passed = student.step(child, generate=scripted('request-check'),
        check=student.notebook_runtime.check_work, max_actions=1)['state']
    assert passed['observation']['status'] == 'checked' and passed['observation']['success'] is True
    assert passed['observation']['value'] == 0.5
    before = files(child)
    assert student.load(child) == passed and tutor_context.snapshot(child)['feedback']['success'] is True
    notebook_replay.export(child, tmp_path / 'replay.html')
    assert files(child) == before
