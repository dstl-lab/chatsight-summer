"""Expression must preserve a saved authored choice, not make another policy decision."""
import importlib.util
import json
import socket
from types import SimpleNamespace

import pytest

from src.agents import behavior_policy
from tests.test_behavior_policy import request


def test_wording_uses_compatible_api_schema_and_keeps_strict_local_validation():
    import httpx
    from google import genai
    from src.labeling.llm import gen_config

    module = expression()
    sent = []
    def capture(request):
        sent.append(json.loads(request.content)['generationConfig']['responseSchema'])
        return httpx.Response(200, json={'candidates': [{'content': {'role': 'model',
            'parts': [{'text': '{"text":"check?"}'}]}, 'finishReason': 'STOP'}]})
    with genai.Client(api_key='invented-key', http_options={
            'client_args': {'transport': httpx.MockTransport(capture)},
            'retry_options': {'attempts': 1}}) as client:
        client.models.generate_content(model='gemini-3.8-flash', contents='Invented check',
                                       config=gen_config(module.Wording))
    assert sent == [{'properties': {'text': {'title': 'Text', 'type': 'STRING'}},
                     'required': ['text'], 'title': 'Wording', 'type': 'OBJECT'}]
    for invalid in ({'text': 'check?', 'decision': 'reply'}, {'text': 'x' * 501}):
        with pytest.raises(ValueError):
            module.Wording.model_validate(invalid)


def expression():
    assert importlib.util.find_spec('src.agents.behavior_expression'), 'Behavior expression adapter is missing'
    from src.agents import behavior_expression
    return behavior_expression


def source(tmp_path, material='diagnostic'):
    value = request()
    value['query'].update(work='answer = 3', diagnostic='IndexError: authored sentinel',
                          next_task='unused-next-task-sentinel')
    for row in value['examples']:
        row['behavior'] = ({'assistance': ['hint'], 'material': [], 'task_relation': 'different'}
                          if material == 'next_task' else
                          {'assistance': ['checking'], 'material': [material] if material else [],
                           'task_relation': 'same'})
    folder = tmp_path / 'policy'
    return folder, behavior_policy.run(value, folder)


def files(folder):
    return {str(path.relative_to(folder)): path.read_bytes()
            for path in folder.rglob('*') if path.is_file()}


def test_template_is_exact_offline_and_expression_replays_without_original_source(tmp_path, monkeypatch):
    module = expression()
    monkeypatch.setattr(socket.socket, 'connect', lambda *args: pytest.fail('Template renderer used network'))
    folder, policy = source(tmp_path)
    before = files(folder)
    output = tmp_path / 'template'
    receipt = module.render(folder, output)
    assert receipt['mode'] == 'template' and receipt['model'] is None
    assert receipt['status'] == 'complete'
    assert receipt['output'] == policy['result']['rendering']['text']
    assert receipt['policy_sha256']
    assert behavior_policy.verify(output / 'policy') == policy
    assert files(folder) == before
    folder.rename(tmp_path / 'moved-policy')
    assert module.verify(output) == receipt
    saved = files(output)
    with pytest.raises(FileExistsError):
        module.render(tmp_path / 'moved-policy', output)
    assert files(output) == saved
    path = output / 'expression.json'
    changed = json.loads(path.read_text())
    changed['output'] = 'A different behavior'
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError):
        module.verify(output)


@pytest.mark.parametrize('material', ['diagnostic', 'work', 'next_task', None])
def test_wording_sees_only_choice_context_and_supplied_style_and_preserves_material(tmp_path, material):
    module = expression()
    folder, policy = source(tmp_path, material)
    template = module.render(folder, tmp_path / 'template')
    calls = []
    styles = ('can you check', 'whats wrong here')

    def generate(prompt, schema):
        calls.append(prompt)
        assert policy['result']['selection']['behavior']['assistance'][0] in prompt
        assert 'hint' in prompt
        assert all(style in prompt for style in styles)
        for hidden in ('answer = 3', 'IndexError: authored sentinel', 'unused-next-task-sentinel',
                       'authored:a1', 'authored:b1', '1/6', 'q-account'):
            assert hidden not in prompt
        return schema(text='can you check this?')

    output = tmp_path / 'wording'
    receipt = module.render(folder, output, model='invented-wording-model', generate=generate,
                            style_examples=styles)
    assert len(calls) == 1
    assert receipt['mode'] == 'wording' and receipt['model'] == 'invented-wording-model'
    assert receipt['status'] == 'complete' and receipt['semantic_status'] == 'unverified'
    assert receipt['candidate'] == {'text': 'can you check this?'}
    prefix = ('Next task: ' if material == 'next_task' else '')
    prefix += policy['result']['query'][material] + '\n' if material else ''
    assert receipt['output'] == prefix + 'can you check this?'
    assert receipt['policy_sha256'] == template['policy_sha256']
    assert behavior_policy.verify(output / 'policy') == policy
    assert receipt['request']['model'] == 'invented-wording-model'
    assert receipt['request']['prompt'] == calls[0]
    assert receipt['request']['single_attempt'] is True
    assert set(receipt['request']['schema']['properties']) == {'text'}
    assert module.verify(output) == receipt
    assert len(calls) == 1
    path = output / 'expression.json'
    changed = json.loads(path.read_text())
    changed['request']['prompt'] += '\nInvent a new behavior.'
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError):
        module.verify(output)


@pytest.mark.parametrize('problem', ['missing', 'unsupported'])
def test_unrenderable_choice_blocks_before_call_and_output_creation(tmp_path, problem):
    module = expression()
    raw = request()
    for row in raw['examples']:
        row['behavior'] = {'assistance': ['checking'] if problem == 'missing' else ['explanation'],
                           'material': ['work'] if problem == 'missing' else [], 'task_relation': 'same'}
    folder = tmp_path / 'policy'
    behavior_policy.run(raw, folder)
    output = tmp_path / 'blocked'
    with pytest.raises(ValueError):
        module.render(folder, output, model='invented-wording-model',
                      generate=lambda *args: pytest.fail('Blocked choice called backend'))
    assert not output.exists()


@pytest.mark.parametrize('failure', ['blank', 'extra-field', 'multiline', 'code-fence', 'overlong', 'exception', 'interrupted'])
def test_failed_candidate_is_saved_once_and_cannot_be_retried_or_tampered(tmp_path, failure):
    module = expression()
    folder, _ = source(tmp_path)
    calls = []

    def generate(prompt, schema):
        calls.append(prompt)
        if failure == 'exception':
            raise RuntimeError('invented backend failure')
        if failure == 'interrupted':
            raise KeyboardInterrupt('invented interruption')
        value = {'blank': {'text': '   '}, 'extra-field': {'text': 'check?', 'behavior': 'different'},
                 'multiline': {'text': 'check?\nmore'}, 'code-fence': {'text': '`check`'},
                 'overlong': {'text': 'x' * 501}}[failure]
        return SimpleNamespace(model_dump=lambda: value)

    output = tmp_path / 'failed'
    if failure == 'interrupted':
        with pytest.raises(KeyboardInterrupt):
            module.render(folder, output, model='invented-wording-model', generate=generate)
        receipt = module.verify(output)
    else:
        receipt = module.render(folder, output, model='invented-wording-model', generate=generate)
    assert len(calls) == 1
    assert receipt['status'] == ('pending' if failure == 'interrupted' else 'error')
    assert receipt['output'] is None
    assert bool(receipt['error_type']) == (failure != 'interrupted')
    assert module.verify(output) == receipt
    before = files(output)
    with pytest.raises(FileExistsError):
        module.render(folder, output, model='invented-wording-model', generate=generate)
    assert len(calls) == 1 and files(output) == before
    path = output / 'expression.json'
    changed = json.loads(path.read_text())
    changed['policy_sha256'] = '0' * 64
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError):
        module.verify(output)
