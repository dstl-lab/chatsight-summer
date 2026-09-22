"""Saved notebook evidence reaches the browser without dispatch or file access APIs."""
from copy import deepcopy
from html.parser import HTMLParser
import importlib.util
import json

import pytest
from fastapi.testclient import TestClient

from src.agents import notebook_next_task, notebook_student as student
from src.eval import notebook_runtime as runtime
from tests.test_notebook_session import ACTIVITY, TASK, observation
from tests.test_task_evaluation import worker
from tests.test_tutor_context import choose


def client(folder):
    assert importlib.util.find_spec('src.agents.browser_workspace'), 'Browser backend is missing'
    from src.agents.browser_workspace import create_app
    return TestClient(create_app(folder), base_url='http://127.0.0.1')


def files(folder):
    return {str(path.relative_to(folder)): path.read_bytes() for path in folder.rglob('*') if path.is_file()}


def test_tutor_formatting_is_inert_and_preserves_original_evidence(tmp_path):
    from src.agents.browser_workspace import _tutor_html
    source = '''### Try this

Use **one value** and `x < 3`.

1. Read the value.
2. Check it.

```python
if x < 3:
    print("<img src=x onerror=alert(1)>")
```

```{#inspector .hidden onclick="alert(1)"}
unchanged code
```

<script>alert(1)</script>
<img src="https://example.invalid/track" onerror="alert(1)">
<svg><a href="javascript:alert(1)">bad</a></svg>
[link](javascript:alert(1)) ![image](https://example.invalid/track)
<https://example.invalid/> <user@example.invalid>
[ref][target] ![ref][target] ![target] [target]

[target]: https://example.invalid/track

&lt;iframe src=x&gt; &#60;img src=x&#62;
'''
    rendered = _tutor_html(source)
    assert '<strong>one value</strong>' in rendered
    assert '<ol>' in rendered and '<li>Check it.</li>' in rendered
    assert '<code>x &lt; 3</code>' in rendered
    assert 'if x &lt; 3:\n    print(' in rendered
    assert '<pre><code>unchanged code\n</code></pre>' in rendered
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in rendered
    assert 'https://example.invalid/track' in rendered

    class Tags(HTMLParser):
        def handle_starttag(self, tag, attrs):
            assert tag in {'p', 'h3', 'strong', 'code', 'pre', 'ol', 'li'}
            assert not attrs or (tag == 'code' and attrs == [('class', 'language-python')])

    Tags().feed(rendered)
    # Both API modes use the same presentation boundary; bindings still match the runner.
    from src.agents import chat_student
    from tests.test_chat_student import QUERY
    query = deepcopy(QUERY)
    query['prefix'][-1]['text'] = source
    chat_folder = tmp_path / 'chat'
    chat_student.create(chat_folder, query=query)
    chat_student.show(chat_folder)
    from src.agents.browser_workspace import create_app
    chat_client = TestClient(create_app(chat_folder, chat_mode=True), base_url='http://127.0.0.1')
    before = files(chat_folder)
    frame = chat_client.get('/api/workspace').json()['encounters'][0]['frames'][0]
    assert frame['binding'] == chat_student.show(chat_folder)['binding']
    assert frame['dialogue'][-1]['text'] == source
    assert frame['dialogue'][-1]['display_html'] == rendered
    assert all('display_html' not in turn for turn in frame['dialogue'] if turn['role'] == 'student')
    assert files(chat_folder) == before

    folder = tmp_path / 'notebook'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/formatting')
    choose(folder, 'reply', text='help')
    choose(folder, 'no-reply', tutor_reply=source)
    before = files(folder)
    frame = client(folder).get('/api/workspace').json()['encounters'][0]['frames'][-1]
    assert frame['dialogue'][-1]['text'] == source
    assert frame['dialogue'][-1]['display_html'] == rendered
    assert files(folder) == before


def test_saved_frames_replay_chain_and_keep_feedback_pending_chat_and_budget(tmp_path, monkeypatch):
    previous, current = tmp_path / 'private-parent', tmp_path / 'current'
    task = deepcopy(TASK)
    task['captured_at'] = 'PRIVATE_PROVENANCE'
    task['dialogue'][0]['text'] = '<script>saved student text</script>'
    student.create(previous, task=task, activity=ACTIVITY, branch_id='authored/previous',
                   evaluation={'expected':'PRIVATE_EXPECTED'}, max_decisions=5)
    worker(monkeypatch, 2)
    choose(previous, 'request-check', check=runtime.check_work)
    choose(previous, 'revise-work', source='n_shades = 2', text='check this?')
    choose(previous, 'no-reply', tutor_reply='This is an authored hint.')
    notebook_next_task.create(previous, current, task=TASK, activity=ACTIVITY, max_decisions=2)
    before = files(tmp_path)
    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw: pytest.fail('Model dispatch'))
    monkeypatch.setattr(runtime, 'check_work', lambda *a, **kw: pytest.fail('Code execution'))
    response = client(current).get('/api/workspace')
    assert response.status_code == 200
    packet = response.json()
    assert packet['version'] == 1
    assert [e['id'] for e in packet['encounters']] == ['1', '2']
    frames = packet['encounters'][0]['frames']
    assert [f['label'] for f in frames] == ['Initial state', 'Saved step 1', 'Saved step 2', 'Saved step 3']
    assert [f['decisions_remaining'] for f in frames] == [5, 4, 3, 2]
    assert [f['status'] for f in frames] == ['active', 'active', 'awaiting-tutor', 'no-reply']
    assert frames[1]['feedback']['value'] == 2 and frames[1]['feedback']['success'] is False
    assert frames[2]['feedback'] is None and frames[2]['work']['revision'] == 1
    assert frames[2]['pending_message'] == 'check this?'
    assert not any(turn['text'] == 'check this?' for turn in frames[2]['dialogue'])
    assert [turn['text'] for turn in frames[3]['dialogue']][-2:] == ['check this?', 'This is an authored hint.']
    assert frames[3]['pending_message'] is None
    assert [a['decision'] for f in frames for a in f['actions']] == ['request-check', 'revise-work', 'no-reply']
    assert frames[2]['changes']['baseline_revision'] == 0
    assert '+n_shades = 2' in frames[2]['changes']['unified_diff']
    assert frames[0]['changes']['unified_diff'] == ''
    assert frames[0]['dialogue'][0]['origin'] is None
    assert frames[3]['dialogue'][-1]['origin'] == 'supplied'
    assert packet['encounters'][1]['initialization']['previous_encounter']['work']['revision'] == 1
    assert packet['encounters'][1]['frames'][0]['feedback'] is None
    assert len(frames[3]['binding']['state_sha256']) == 64
    for secret in ('PRIVATE_EXPECTED', 'PRIVATE_PROVENANCE', str(previous), 'image_id', 'evaluation_sha256', 'engine'):
        assert secret not in response.text
    assert files(tmp_path) == before


def test_reads_are_fresh_errors_are_sanitized_and_tampering_never_falls_back(tmp_path, monkeypatch):
    folder = tmp_path / 'session'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/browser', max_decisions=2)
    student.load(folder)
    browser = client(folder)
    assert len(browser.get('/api/workspace').json()['encounters'][0]['frames']) == 1
    choose(folder, 'request-check', check=lambda *a, **kw:
           observation(*a, **kw, status='environment-error') | {'error':{'message':'PRIVATE_DOCKER_COMMAND'}})
    before = files(folder)
    payload = browser.get('/api/workspace')
    frame = payload.json()['encounters'][0]['frames'][-1]
    assert frame['status'] == 'environment-error' and frame['decisions_remaining'] == 1
    assert frame['feedback']['success'] is None and frame['feedback']['status'] == 'environment-error'
    assert 'PRIVATE_DOCKER_COMMAND' not in payload.text
    assert files(folder) == before
    receipt_path = folder / 'step-0001.json'
    receipt = json.loads(receipt_path.read_text())
    receipt['result']['state']['work']['source'] = 'tampered'
    receipt_path.write_text(json.dumps(receipt))
    tampered = files(folder)
    failed = browser.get('/api/workspace')
    assert failed.status_code == 409
    assert 'encounters' not in failed.json() and str(folder) not in failed.text
    assert files(folder) == tampered
    receipt['status'] = 'pending'
    receipt_path.write_text(json.dumps(receipt))
    assert browser.get('/api/workspace').status_code == 409


def test_saved_operation_groups_actions_and_counts_a_failed_model_decision(tmp_path):
    folder = tmp_path / 'session'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/batched', max_decisions=3)
    choices = iter([student.Action(decision='revise-work', text='', source='n_shades = 2'),
                    student.Action(decision='reply', text='check this?', source=None)])
    student.step(folder, generate=lambda *_:next(choices), check=None, max_actions=2)

    def failed(*_):
        raise RuntimeError('PRIVATE_PROVIDER_DIAGNOSTIC')

    student.step(folder, generate=failed, check=None, tutor_reply='An authored hint.', max_actions=1)
    before = files(folder)
    response = client(folder).get('/api/workspace')
    frames = response.json()['encounters'][0]['frames']
    assert [frame['decisions_remaining'] for frame in frames] == [3, 1, 0]
    assert [action['decision'] for action in frames[1]['actions']] == ['revise-work', 'reply']
    assert frames[-1]['status'] == 'error' and frames[-1]['actions'] == []
    assert frames[-1]['pending_message'] is None
    assert 'PRIVATE_PROVIDER_DIAGNOSTIC' not in response.text
    assert files(folder) == before


def test_local_server_only_serves_connected_shell_and_read_only_fixed_routes(tmp_path):
    folder = tmp_path / 'session'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/browser')
    student.load(folder)
    browser = client(folder)
    page = browser.get('/')
    assert page.status_code == 200 and '<script src="/workspace.js"></script>' in page.text
    assert 'Filtering a table' not in page.text and 'const cases' not in page.text
    assert 'Backend disconnected' not in page.text and 'Loading saved' in page.text
    assert browser.get('/student-workspace.html').text == page.text
    script = browser.get('/workspace.js')
    assert script.status_code == 200 and script.headers['content-type'].startswith('text/javascript')
    assert page.headers['cache-control'] == 'no-store'
    assert page.headers['x-content-type-options'] == 'nosniff'
    assert "connect-src 'self'" in page.headers['content-security-policy']
    assert browser.get('/api/workspace', headers={'Origin':'http://evil.example'}).status_code == 403
    assert browser.get('/api/workspace', headers={'Sec-Fetch-Site':'cross-site'}).status_code == 403
    assert browser.get('/api/workspace', headers={'Host':'evil.example'}).status_code == 400
    assert browser.get('/api/workspace', headers={'Origin':'http://127.0.0.1'}).status_code == 200
    assert browser.post('/api/workspace', json={}).status_code == 405
    for path in ('/session.json', '/data/session.json', '/api/workspace/session', '/%2e%2e/session.json', '/docs'):
        assert browser.get(path).status_code == 404
    before = files(folder)
    assert browser.get('/api/workspace?folder=/private').status_code == 400
    assert files(folder) == before
