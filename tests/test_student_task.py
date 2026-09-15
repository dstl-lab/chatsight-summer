"""One authored task: checks must follow the learner's actual current work."""
import importlib.util
import json
from copy import deepcopy

import pytest


def test_work_revision_invalidates_feedback_and_never_leaks_future():
    assert importlib.util.find_spec('src.eval.student_task'), 'The student work loop is not implemented'
    from src.eval.student_task import EXAMPLE, run

    episode = deepcopy(EXAMPLE)
    episode['turns'].append(dict(id='future', role='student', phase='followup', text='HIDDEN_FUTURE'))
    sequence = [
        dict(decision='request-check', text='', work=None),
        dict(decision='revise-work', text='', work=dict(north=8.0, south=10.0, choice='south')),
        dict(decision='request-check', text='', work=None),
        dict(decision='reply', text='which unit?', work=None),
        dict(decision='no-reply', text='', work=None),
    ]
    packets = []

    def generate(prompt, model):
        assert 'HIDDEN_FUTURE' not in prompt
        packet = json.loads(prompt.split('\nSTATE JSON:\n')[1])
        packets.append(packet)
        return model.model_validate(sequence[len(packets) - 1])

    result = run(episode, generate=generate, tutor_bridges=['Use tomatoes per plant.'])
    assert result['status'] == 'no-reply'
    assert packets[0]['observation'] is None
    assert packets[1]['observation']['success'] is False
    assert packets[2]['revision'] == 1 and packets[2]['observation'] is None
    assert packets[2]['history'][0]['observation']['revision'] == 0
    assert packets[3]['observation']['success'] is True
    assert packets[3]['observation']['revision'] == 1
    assert result['work'] == {'north': 8.0, 'south': 10.0, 'choice': 'south'}
    assert len(result['events']) == 5
    assert 'which unit?' in json.dumps(packets[4]['dialogue'])
    assert 'Use tomatoes per plant.' in json.dumps(packets[4]['dialogue'])
    assert episode['turns'][-1]['text'] == 'HIDDEN_FUTURE'


def test_termination_validation_and_untrusted_chat_do_not_change_work():
    from src.eval.student_task import Action, EXAMPLE, run

    assert 'additionalProperties' not in json.dumps(Action.model_json_schema())
    for invalid in [
        dict(decision='reply', text='', work=None),
        dict(decision='request-check', text='it passed', work=None),
        dict(decision='revise-work', text='', work=None),
        dict(decision='no-reply', text='', work={'north': 8, 'south': 10, 'choice': 'south'}),
        dict(decision='revise-work', text='', work={'north': float('nan'), 'south': 10, 'choice': 'south'}),
        dict(decision='request-check', text='', work=None, success=True),
    ]:
        with pytest.raises(ValueError):
            Action.model_validate(invalid)
    claims = run(EXAMPLE, generate=lambda _, model: model(decision='reply', text='all passed', work=None),
                 tutor_bridges=[])
    assert claims['status'] == 'awaiting-tutor'
    assert claims['observation'] is None and claims['revision'] == 0
    assert claims['events'][0]['action']['text'] == 'all passed'
    capped = run(EXAMPLE, generate=lambda _, model: model(decision='request-check', text='', work=None),
                 tutor_bridges=[], max_actions=2)
    assert capped['status'] == 'action-limit' and len(capped['events']) == 2
    invalid = run(EXAMPLE, generate=lambda _, model: model.model_construct(decision='no-reply', text='bad', work=None),
                  tutor_bridges=[])
    assert invalid['status'] == 'error' and invalid['events'][0]['action']['text'] == 'bad'
    assert invalid['observation'] is None
    with pytest.raises(ValueError):
        run(EXAMPLE, generate=lambda *_: None, tutor_bridges=[], max_actions=0)


def test_trace_replays_without_dispatch_and_preserves_incomplete_receipts(tmp_path, monkeypatch):
    import sys
    from src.eval.student_task import main
    from src.labeling import llm

    calls = []

    def generate(prompt, model):
        calls.append(prompt)
        return model(decision='no-reply', text='', work=None)

    monkeypatch.setenv('GEMINI_API_KEY', 'invented-offline-test-key')
    monkeypatch.setattr(llm, 'make_generate', lambda *args, **kwargs: generate)
    folder = tmp_path / 'trace'
    monkeypatch.setattr(sys, 'argv', ['student_task', '--send', '--output', str(folder)])
    main()
    assert len(calls) == 1
    before = {path.name: path.read_bytes() for path in folder.iterdir()}
    with pytest.raises(FileExistsError):
        main()
    monkeypatch.setattr(sys, 'argv', ['student_task', '--replay', '--output', str(folder)])
    main()
    assert len(calls) == 1 and before == {path.name: path.read_bytes() for path in folder.iterdir()}
    receipt_file = folder / 'call-01.json'
    receipt = json.loads(receipt_file.read_text())
    receipt['status'] = 'pending'
    receipt_file.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='does not reproduce'):
        main()
    assert len(calls) == 1 and json.loads(receipt_file.read_text())['status'] == 'pending'


def test_provider_failure_replays_as_the_same_failure_without_resubmission(tmp_path, monkeypatch):
    import sys
    from src.eval.student_task import main
    from src.labeling import llm

    calls = []

    def fail(*args):
        calls.append(True)
        raise RuntimeError('invented provider failure')

    monkeypatch.setenv('GEMINI_API_KEY', 'invented-offline-test-key')
    monkeypatch.setattr(llm, 'make_generate', lambda *args, **kwargs: fail)
    folder = tmp_path / 'failed'
    monkeypatch.setattr(sys, 'argv', ['student_task', '--send', '--output', str(folder)])
    with pytest.raises(SystemExit) as sent:
        main()
    assert sent.value.code == 1
    before = {path.name: path.read_bytes() for path in folder.iterdir()}
    monkeypatch.setattr(sys, 'argv', ['student_task', '--replay', '--output', str(folder)])
    with pytest.raises(SystemExit) as replayed:
        main()
    assert replayed.value.code == 1 and len(calls) == 1
    assert before == {path.name: path.read_bytes() for path in folder.iterdir()}
