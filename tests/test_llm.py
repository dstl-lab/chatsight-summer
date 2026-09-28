"""Retry behavior for the Gemini wrapper. A mass-label run is hundreds of
sequential calls; one transient 429/5xx must not abort the whole job."""
import pytest
from pydantic import BaseModel
from types import SimpleNamespace

from src.labeling.llm import with_retries


class Out(BaseModel):
    x: int


def test_transient_failures_are_retried_with_backoff():
    calls = {"n": 0}
    slept: list[float] = []

    def flaky(prompt, response_model):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return Out(x=7)

    generate = with_retries(flaky, attempts=4, base_delay=2.0,
                            sleep=slept.append)
    assert generate("p", Out) == Out(x=7)
    assert calls["n"] == 3
    assert slept == [2.0, 4.0]  # exponential backoff


def test_persistent_failure_raises_after_attempts_exhausted():
    calls = {"n": 0}

    def broken(prompt, response_model):
        calls["n"] += 1
        raise RuntimeError("503 UNAVAILABLE")

    generate = with_retries(broken, attempts=3, base_delay=1.0,
                            sleep=lambda _: None)
    with pytest.raises(RuntimeError, match="503"):
        generate("p", Out)
    assert calls["n"] == 3


def test_with_retries_reports_and_clears_retry():
    calls: list[int] = []
    events: list[dict | None] = []

    def flaky(prompt, response_model):
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("429")
        return "ok"

    g = with_retries(flaky, sleep=lambda s: None, on_retry=events.append)
    assert g("p", None) == "ok"
    assert events == [
        {"attempt": 2, "max": 4, "wait_s": 2.0},
        {"attempt": 3, "max": 4, "wait_s": 4.0},
        None,
    ]


def test_with_retries_without_callback_still_works():
    g = with_retries(lambda p, m: "ok", sleep=lambda s: None)
    assert g("p", None) == "ok"


@pytest.mark.parametrize('outcome', ['success', 'transport-error', 'invalid-json',
                                     'capped', 'missing-candidate', 'multiple-candidates'])
def test_single_attempt_bounds_sdk_and_never_wraps_or_sleeps(monkeypatch, outcome):
    from google import genai
    from src.labeling import llm

    constructors, calls, retries = [], [], []

    def generate_content(**kwargs):
        calls.append(kwargs)
        if outcome == 'transport-error':
            raise RuntimeError('Authored failed request')
        candidate = SimpleNamespace(finish_reason='MAX_TOKENS' if outcome == 'capped' else 'STOP')
        candidates = ([] if outcome == 'missing-candidate' else
                      [candidate, candidate] if outcome == 'multiple-candidates' else [candidate])
        return SimpleNamespace(text='not JSON' if outcome == 'invalid-json' else '{"x":7}',
                               candidates=candidates)

    def client(**kwargs):
        constructors.append(kwargs)
        return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

    monkeypatch.setattr(genai, 'Client', client)
    monkeypatch.setattr(llm, 'with_retries', lambda *a, **kw: pytest.fail('Application retry wrapper attached'))
    monkeypatch.setattr(llm.time, 'sleep', lambda _: pytest.fail('Single attempt slept'))
    generate = llm.make_generate('authored-key', model='gemini-authored-tutor',
                                temperature=0.4, on_retry=retries.append, single_attempt=True)
    assert calls == []
    if outcome == 'success':
        assert generate('authored prompt', Out) == Out(x=7)
    else:
        with pytest.raises((RuntimeError, ValueError)):
            generate('authored prompt', Out)
    assert len(calls) == 1 and retries == []
    assert calls[0] == {'model': 'gemini-authored-tutor', 'contents': 'authored prompt',
                       'config': {'response_mime_type': 'application/json', 'response_schema': Out,
                                  'temperature': 0.4}}
    assert len(constructors) == 1
    options = constructors[0]['http_options']
    assert options.timeout == 120000 and options.retry_options.attempts == 1


def test_make_generate_default_keeps_existing_retry_behavior(monkeypatch):
    from google import genai
    from src.labeling import llm

    constructors, calls, sleeps, events = [], [], [], []

    def generate_content(**kwargs):
        calls.append(kwargs)
        raise RuntimeError('Authored persistent failure')

    def client(**kwargs):
        constructors.append(kwargs)
        return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

    original = llm.with_retries
    monkeypatch.setattr(genai, 'Client', client)
    monkeypatch.setattr(llm, 'with_retries', lambda generate, **kw:
                        original(generate, sleep=sleeps.append, **kw))
    generate = llm.make_generate('authored-key', on_retry=events.append)
    with pytest.raises(RuntimeError, match='persistent failure'):
        generate('authored prompt', Out)
    assert constructors == [{'api_key': 'authored-key'}]
    assert len(calls) == 4 and sleeps == [2.0, 4.0, 8.0]
    assert events == [{'attempt': 2, 'max': 4, 'wait_s': 2.0},
                      {'attempt': 3, 'max': 4, 'wait_s': 4.0},
                      {'attempt': 4, 'max': 4, 'wait_s': 8.0}]


@pytest.mark.parametrize('value', [None, 0, 1, 'false'])
def test_single_attempt_rejects_non_boolean_before_client_construction(monkeypatch, value):
    from google import genai
    from src.labeling import llm

    monkeypatch.setattr(genai, 'Client', lambda **kw: pytest.fail('Invalid setting created a client'))
    with pytest.raises(ValueError, match='single_attempt'):
        llm.make_generate('authored-key', single_attempt=value)
