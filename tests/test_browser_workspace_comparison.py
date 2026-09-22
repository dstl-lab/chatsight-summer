"""Saved comparisons share the browser, never the simulator submission path."""
import sys

from fastapi.testclient import TestClient
import pytest

from src.agents import browser_workspace as browser, chat_student
from tests.test_chat_student import QUERY, files
from tests.test_saved_comparison import write_bundle


def test_fixed_comparison_endpoint_is_read_only_pinned_and_separate_from_replay(tmp_path):
    review = write_bundle(tmp_path)
    session = tmp_path / 'session'
    chat_student.create(session, query=QUERY)
    chat_student.show(session)
    before = files(tmp_path)
    app = browser.create_app(session, chat_mode=True, comparison=review,
        generate=lambda *_: pytest.fail('Compare dispatched a model'))
    viewer = TestClient(app, base_url='http://127.0.0.1')
    assert viewer.get('/api/scenarios').json() == {
        'version':1, 'scenarios':[], 'comparison_available':True}
    replay = viewer.get('/api/workspace').json()
    response = viewer.get('/api/comparison')
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    assert len(response.json()['cases']) == 2
    assert 'PRIVATE REVIEWER' not in response.text and str(review) not in response.text
    assert response.json()['cases'][1]['draws'][0]['shared_review_with'] == 2
    assert viewer.get('/api/workspace').json() == replay
    assert viewer.post('/api/comparison', json={}).status_code == 405
    assert viewer.get('/api/comparison?folder=elsewhere').status_code == 400
    assert viewer.get('/api/comparison', headers={'Origin':'http://evil.example'}).status_code == 403
    assert files(tmp_path) == before
    closure = review / 'closure.json'
    original = closure.read_bytes()
    closure.write_bytes(original + b' ')
    failed = viewer.get('/api/comparison')
    assert failed.status_code == 409 and 'cases' not in failed.json()
    assert str(tmp_path) not in failed.text
    assert viewer.get('/api/workspace').json() == replay
    closure.write_bytes(original)
    assert viewer.get('/api/comparison').json() == response.json()
    unconfigured = TestClient(browser.create_app(session, chat_mode=True), base_url='http://127.0.0.1')
    assert unconfigured.get('/api/comparison').status_code == 404
    assert 'comparison_available' not in unconfigured.get('/api/scenarios').json()
    alias = tmp_path / 'linked-review'
    alias.symlink_to(review, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        browser.create_app(session, chat_mode=True, comparison=alias)


def test_cli_companion_review_keeps_sending_disabled(tmp_path, monkeypatch):
    import uvicorn

    review = write_bundle(tmp_path)
    session = tmp_path / 'session'
    chat_student.create(session, query=QUERY)
    chat_student.show(session)
    apps = []
    monkeypatch.setattr(uvicorn, 'run', lambda app, **options: apps.append(app))
    monkeypatch.setattr(sys, 'argv', ['browser_workspace', str(session), '--chat', '--comparison', str(review)])
    browser.main()
    viewer = TestClient(apps[0], base_url='http://127.0.0.1')
    assert viewer.get('/api/comparison').status_code == 200
    assert viewer.get('/api/workspace').json()['controls']['send_enabled'] is False
