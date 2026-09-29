"""Evidence uses only the supplied prefix and optional guidance stays auditable."""
import json

from fastapi.testclient import TestClient
import pytest

from src.agents import browser_workspace as browser, chat_student as chat


PREFIX = [{'role': 'student', 'text': 'help'}, {'role': 'tutor', 'text': 'TUTOR_ONLY'},
          {'role': 'student', 'text': 'x' * 41}, {'role': 'tutor', 'text': 'Another hint'},
          {'role': 'student', 'text': '学' * 301 + '\n`'}, {'role': 'tutor', 'text': 'Try this'}]


def make_session(tmp_path):
    folder = tmp_path / 'chat'
    chat.create(folder, query={'id': 'PRIVATE_CASE', 'student_id': 'PRIVATE_ACCOUNT',
                              'conversation_id': 'PRIVATE_CONVERSATION', 'prefix': PREFIX})
    chat.show(folder)
    return folder


def test_card_literal_counts_unicode_examples_and_empty_input():
    from src.agents import student_evidence as evidence
    card = evidence.card(PREFIX)
    assert card['student_messages'] == 3 and card['supplied_turns'] == 6
    assert card['statistics'] == {'median_characters': 41, 'short_messages': 1,
        'medium_messages': 1, 'long_messages': 1, 'newline_messages': 1,
        'backtick_messages': 1, 'blank_messages': 0}
    assert [r['turn_index'] for r in card['examples']] == [1, 3, 5]
    assert len(card['examples'][-1]['text']) == 240 and card['examples'][-1]['truncated']
    assert 'TUTOR_ONLY' not in json.dumps(card)
    assert evidence.card([])['statistics']['median_characters'] is None
    even = evidence.card([{'role': 'student', 'text': 'x' * n} for n in (4, 40)])
    assert even['statistics']['median_characters'] == 22
    with pytest.raises(ValueError):
        evidence.card([{'role': 'student', 'text': 'synthetic', 'origin': 'generated'}])


@pytest.mark.parametrize('enabled', [False, True])
def test_browser_guidance_is_opt_in_and_never_learns_from_generated_messages(tmp_path, enabled):
    folder = make_session(tmp_path)
    sent = []

    def generate(prompt, schema):
        sent.append(prompt)
        return schema(decision='reply', text='SYNTHETIC_FOLLOWUP')

    viewer = TestClient(browser.create_app(folder, chat_mode=True, send=True, generate=generate),
                        base_url='http://127.0.0.1')
    packet = viewer.get('/api/workspace').json()
    card = packet['encounters'][0]['evidence_card']
    assert packet['controls']['evidence_guidance_enabled'] is True
    assert not sent and not (folder / 'student-evidence').exists()
    before = chat.show(folder)['binding']
    response = viewer.post('/api/continue', json={'binding': before, 'mode': 'advance',
                                                  'use_evidence': enabled})
    assert response.status_code == 200, response.text
    assert response.json()['encounters'][0]['evidence_card'] == card
    assert response.json()['encounters'][0]['frames'][-1]['evidence_guidance_used'] is enabled
    assert len(sent) == 1 and ('STUDENT COMMUNICATION EVIDENCE JSON' in sent[0]) is enabled
    assert 'PRIVATE_' not in sent[0] and 'SYNTHETIC_FOLLOWUP' not in json.dumps(card)
    if enabled:
        audit_path = folder / 'student-evidence' / (before['state_sha256'] + '.json')
        audit = json.loads(audit_path.read_text())
        assert audit['request']['prompt'] == sent[0] and audit['request']['card'] == card
        assert audit['response']['text'] == 'SYNTHETIC_FOLLOWUP'
        assert viewer.post('/api/continue', json={'binding': before, 'mode': 'advance',
                                                 'use_evidence': True}).status_code == 409
        audit['request']['card']['student_messages'] = 99
        audit_path.write_text(json.dumps(audit))
        assert viewer.get('/api/workspace').status_code == 409
    else:
        assert not (folder / 'student-evidence').exists()


def test_guidance_error_preserves_request_and_stops_without_resend(tmp_path):
    folder = make_session(tmp_path)
    sent = []

    def fail(prompt, schema):
        sent.append(prompt)
        raise RuntimeError('PRIVATE_PROVIDER_ERROR')

    viewer = TestClient(browser.create_app(folder, chat_mode=True, send=True, generate=fail),
                        base_url='http://127.0.0.1')
    binding = chat.show(folder)['binding']
    body = {'binding': binding, 'mode': 'advance', 'use_evidence': True}
    response = viewer.post('/api/continue', json=body)
    assert response.status_code == 200 and response.json()['operation']['status'] == 'error'
    assert 'PRIVATE_PROVIDER_ERROR' not in response.text
    assert viewer.post('/api/continue', json=body).status_code == 409
    assert len(sent) == 1
    audit = json.loads(next((folder / 'student-evidence').glob('*.json')).read_text())
    assert audit['status'] == 'error' and audit['error_type'] == 'RuntimeError'


@pytest.mark.parametrize('mode', ['reply', 'policy'])
def test_guidance_reaches_student_after_tutor_without_changing_the_tutor_prompt(tmp_path, mode):
    folder = make_session(tmp_path)
    chat.step(folder, binding=chat.show(folder)['binding'],
              generate=lambda _, schema: schema(decision='reply', text='SYNTHETIC_QUESTION'))
    student_prompts, tutor_prompts = [], []

    def tutor(prompt, schema):
        tutor_prompts.append(prompt)
        return schema(text='NEW_TUTOR_REPLY')

    def student(prompt, schema):
        student_prompts.append(prompt)
        return schema(decision='no-reply', text='')

    viewer = TestClient(browser.create_app(folder, chat_mode=True, send=True,
        generate=student, generate_tutor=tutor), base_url='http://127.0.0.1')
    card = viewer.get('/api/workspace').json()['encounters'][0]['evidence_card']
    response = viewer.post('/api/continue', json={'binding': chat.show(folder)['binding'],
        'mode': mode, 'text': 'NEW_TUTOR_REPLY' if mode == 'reply' else 'Give a hint.', 'use_evidence': True})
    assert response.status_code == 200, response.text
    assert response.json()['encounters'][0]['evidence_card'] == card
    assert len(student_prompts) == 1 and 'NEW_TUTOR_REPLY' in student_prompts[0]
    assert all('STUDENT COMMUNICATION EVIDENCE JSON' not in p for p in tutor_prompts)
    assert viewer.get('/api/workspace').status_code == 200


def test_local_backend_rejects_guidance_before_any_dispatch(tmp_path):
    folder = make_session(tmp_path)
    viewer = TestClient(browser.create_app(folder, chat_mode=True, send=True, manual_tutor=True,
        generate_reply=lambda _: pytest.fail('Unsupported local dispatch')), base_url='http://127.0.0.1')
    assert viewer.get('/api/workspace').json()['controls']['evidence_guidance_enabled'] is False
    response = viewer.post('/api/continue', json={'binding': chat.show(folder)['binding'],
                                                  'mode': 'advance', 'use_evidence': True})
    assert response.status_code == 400 and not list(folder.glob('step-*.json'))
