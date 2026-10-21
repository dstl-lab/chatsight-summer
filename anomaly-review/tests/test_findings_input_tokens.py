"""Token accounting changes pacing, never the model's evidence or instructions."""
from dataclasses import replace
import io
import json
import threading
import time
import urllib.error

import pytest

from session_review.findings import historical as h, optimized, provider, sweep
from test_findings_optimized import prepared, fake_result


def test_counter_sends_full_generation_request_but_never_generates(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fictional-test-key")
    sent = []
    def endpoint(request, timeout):
        sent.append(request)
        assert timeout <= 45
        return io.BytesIO(b'{"totalTokens":50}')
    monkeypatch.setattr(provider.urllib.request, "urlopen", endpoint)
    config = {"response_mime_type":"application/json", "response_json_schema":{"type":"object"},
        "temperature":0, "max_output_tokens":8192, "thinking_config":{"thinking_level":"low"}}
    assert provider.count_input_tokens("Exact text", config, "fictional", provider.Options()) == 50
    assert len(sent) == 1 and sent[0].full_url.endswith("models/fictional:countTokens")
    body = json.loads(sent[0].data)["generateContentRequest"]
    assert body["contents"] == [{"role":"user","parts":[{"text":"Exact text"}]}]
    assert body["generationConfig"] == provider.wire_config(config)
    assert body["generationConfig"]["thinkingConfig"]["thinkingLevel"] == "LOW"
    assert "fictional-test-key" not in sent[0].full_url


def test_counter_errors_cannot_echo_provider_content_or_credentials(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fictional-test-key")
    def endpoint(*_, **__):
        raise urllib.error.HTTPError("https://example.invalid", 403, "private prompt", {}, io.BytesIO(b"secret"))
    monkeypatch.setattr(provider.urllib.request, "urlopen", endpoint)
    with pytest.raises(provider.TokenCountError) as caught:
        provider.count_input_tokens("Private evidence", {}, "fictional", provider.Options())
    assert caught.value.code == 403
    assert "private" not in str(caught.value).lower() and "secret" not in str(caught.value)


def test_input_only_pacing_preserves_original_generation_payload(tmp_path):
    paths = prepared(tmp_path, 1)
    options = provider.Options(tpm=100, max_output_tokens=8192, compact=False)
    _, _, _, evidence = h.load_prepared(paths[0])
    original_text, original_config, _ = provider.payload(evidence[0], options)
    calls = []
    def counter(text, config, model, settings):
        assert text == original_text and config == original_config
        calls.append("count"); return 50
    def generate(item, model, settings):
        assert item == evidence[0]
        text, config, _ = provider.payload(item, settings)
        assert (text, config) == (original_text, original_config)
        calls.append("generate"); return fake_result(item)
    report = optimized.run_many(paths, model="fictional", options=options, send=True, generate=generate,
        token_counter=counter, cache_folder=tmp_path/"cache")
    assert calls == ["count", "generate"] and report["completed"] == 1
    receipt = json.loads(next(p for p in (paths[0]/"analysis-optimized").glob("*.json") if p.name != "plan.json").read_text())
    assert receipt["input"]["rate_limit_input_tokens"] == 82 < options.tpm
    assert receipt["input"]["run_budget_tokens"] == 82 + 8192
    assert receipt["input"]["input_token_source"] == "provider_count_full_request"
    changed = replace(options, token_counting="estimate")
    assert provider.request_key(evidence[0], "fictional", options) == provider.request_key(evidence[0], "fictional", changed)


def test_output_run_budget_still_blocks_and_saved_count_is_reused_on_resume(tmp_path):
    paths = prepared(tmp_path, 1)
    options = provider.Options(tpm=100, max_estimated_tokens=100)
    calls = []
    def counter(*_): calls.append("count"); return 50
    def generate(e,*_): calls.append("generate"); return fake_result(e)
    kwargs = dict(model="fictional", send=True, generate=generate, token_counter=counter, cache_folder=tmp_path/"cache")
    stopped = optimized.run_many(paths, options=options, **kwargs)
    assert stopped["completed"] == 0 and stopped["stopped_reason"]
    assert calls == ["count"]
    resumed = optimized.run_many(paths, options=replace(options, max_estimated_tokens=10000), **kwargs)
    assert resumed["completed"] == 1 and calls == ["count", "generate"]


def test_count_failure_leaves_analysis_untouched_and_stops_dispatch(tmp_path):
    paths = prepared(tmp_path, 3)
    def counter(*_): raise provider.TokenCountError(429)
    report = optimized.run_many(paths, model="fictional", options=provider.Options(workers=1), send=True,
        generate=lambda *_: pytest.fail("Analysis must not be sent"), token_counter=counter, cache_folder=tmp_path/"cache")
    assert report["completed"] == report["failed"] == report["pending"] == 0
    assert "counting failed" in report["stopped_reason"]


def test_explicit_estimate_mode_does_not_tokenize_or_reduce_output(tmp_path):
    paths = prepared(tmp_path, 1)
    report = optimized.run_many(paths, model="fictional", options=provider.Options(token_counting="estimate",tpm=1000000), send=True,
        generate=lambda e,*_: fake_result(e), token_counter=lambda *_: pytest.fail("Unexpected count"), cache_folder=tmp_path/"cache")
    assert report["completed"] == 1 and report["provider_counted_responses"] == 0


def test_reconciliation_releases_only_reported_input_and_keeps_rate_window():
    limiter = optimized.RateLimiter(10,100,window_seconds=.04)
    stop = threading.Event()
    first = limiter.acquire(80,stop)
    limiter.reconcile(first,30)
    start = time.monotonic()
    second = limiter.acquire(70,stop)
    assert time.monotonic()-start < .03
    assert second.input_tokens == 70
    limiter.reconcile(first,90)
    start = time.monotonic()
    assert limiter.acquire(1,stop)
    assert time.monotonic()-start >= .025


def test_count_only_workflow_requires_send_and_never_creates_analysis_receipts(tmp_path):
    paths = prepared(tmp_path, 2)
    calls = []
    def count(*_): calls.append(1); return 50
    kwargs = dict(model="fictional", cache_folder=tmp_path/"cache", measure=count)
    with pytest.raises(ValueError,match="--send"):
        sweep.count_inputs(paths,provider.Options(),**kwargs)
    report = sweep.count_inputs(paths,provider.Options(),send=True,**kwargs)
    assert report["generation_calls"] == 0 and report["count_requests"] == len(calls) == 2
    assert not (paths[0]/"analysis-optimized").exists()
    reused = sweep.count_inputs(paths,provider.Options(),send=True,**kwargs)
    assert reused["count_requests"] == 0 and len(calls) == 2
