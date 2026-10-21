"""Optimization correctness: no real API calls, no mutation of legacy inputs."""
from dataclasses import replace
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace

import pytest

from session_review.findings import analyze_sessions as analyzer, bulk, compact, grouped, historical as h, native_batch, optimized, provider
from test_findings_bulk import data


def prepared(tmp_path, count=8):
    path = tmp_path / "source.jsonl"; path.write_bytes(data(count))
    source = bulk.index_source(path, tmp_path / "events.sqlite")
    result = bulk.prepare_batches(tmp_path / "events.sqlite", tmp_path / "batches", source)
    return [tmp_path / "batches" / b["folder"] for b in result["batches"]]


def fake_result(evidence):
    return provider.CallResult(analyzer.Assessment(session_id=evidence["session_id"], decision="no_supported_finding", summary="Authored transport test."),
        {"input_tokens": 100, "output_tokens": 10, "thinking_tokens": 2, "total_tokens": 112}, .01)


def test_compaction_roundtrips_every_observation_and_preserves_original_ids(tmp_path):
    paths = prepared(tmp_path, 1)
    _, _, _, evidence = h.load_prepared(paths[0])
    item = evidence[0]
    repeated = "Exact code/output: λ = 'a\\nb'\n" * 200
    for i, event in enumerate(item["timeline"]): event["retained_test_text"] = "Different first capture" if i == 0 else repeated
    encoded = compact.pack(item)
    assert compact.unpack(encoded) == item
    assert len(compact.dumps(encoded)) < len(compact.dumps(item)) * .5
    assert {r["id"] for r in encoded["evidence"]["timeline"]} == {r["id"] for r in item["timeline"]}
    assert repeated in encoded["text_table"]


def test_concurrency_is_bounded_receipts_survive_and_resume_never_resends(tmp_path):
    paths = prepared(tmp_path, 8)
    calls, active, peak = [], 0, 0
    lock = threading.Lock()
    def generate(evidence, *_):
        nonlocal active, peak
        with lock: calls.append(evidence["session_id"]); active += 1; peak = max(peak, active)
        time.sleep(.03)
        with lock: active -= 1
        return fake_result(evidence)
    options = provider.Options(workers=4, rpm=1000, tpm=10_000_000)
    report = optimized.run_many(paths, model="fictional", options=options, send=True, generate=generate, cache_folder=tmp_path / "cache")
    assert report["completed"] == 8 and 1 < peak <= 4
    assert report["usage"]["input_tokens"] == 800
    optimized.run_many(paths, model="fictional", options=options, send=True, generate=generate, cache_folder=tmp_path / "cache")
    assert len(calls) == len(set(calls)) == 8
    assert all(r["validation_status"] == "valid" for r in optimized.saved_results(paths[0], "fictional", options).values())


def test_run_budget_pauses_untouched_work_and_can_resume_with_changed_worker_count(tmp_path):
    paths = prepared(tmp_path)
    calls = []
    def generate(evidence, *_): calls.append(evidence["session_id"]); time.sleep(.01); return fake_result(evidence)
    options = provider.Options(workers=4, rpm=1000, tpm=10_000_000, max_requests=2)
    report = optimized.run_many(paths, model="fictional", options=options, send=True, generate=generate, cache_folder=tmp_path / "cache")
    assert report["completed"] == len(calls) == 2 and report["stopped_reason"]
    report = optimized.run_many(paths, model="fictional", options=replace(options, workers=2, max_requests=0), send=True, generate=generate, cache_folder=tmp_path / "cache")
    assert report["completed"] == len(set(calls)) == 8


def test_quota_failure_stops_new_dispatch_and_diagnostics_stay_private(tmp_path):
    paths = prepared(tmp_path)
    calls = []
    class Quota(Exception): code = 429
    def generate(evidence, *_): calls.append(1); raise Quota("private credential or prompt")
    report = optimized.run_many(paths, model="fictional", options=provider.Options(workers=1, tpm=10_000_000), send=True, generate=generate, cache_folder=tmp_path / "cache")
    assert calls == [1] and report["failed"] == 1 and report["stopped_reason"]
    assert not any("private credential or prompt" in p.read_text() for p in (paths[0] / "analysis-optimized").glob("*.json"))


def test_configuration_changes_are_rejected_before_any_new_request(tmp_path):
    paths = prepared(tmp_path, 1); options = provider.Options(tpm=10_000_000)
    optimized.run_many(paths, model="fictional", options=options, send=True, generate=lambda e,*_: fake_result(e), cache_folder=tmp_path / "cache")
    with pytest.raises(ValueError, match="configuration changed"):
        optimized.run_many(paths, model="fictional", options=replace(options, thinking="low"), send=True, generate=lambda *_: pytest.fail("Unexpected call"), cache_folder=tmp_path / "cache")


def test_missing_send_and_oversized_token_setting_never_dispatch(tmp_path):
    paths = prepared(tmp_path, 1)
    with pytest.raises(ValueError, match="--send"):
        optimized.run_many(paths, model="fictional", options=provider.Options(), cache_folder=tmp_path / "cache")
    report = optimized.run_many(paths, model="fictional", options=provider.Options(tpm=1), send=True, generate=lambda *_: pytest.fail("Unexpected call"), cache_folder=tmp_path / "cache")
    assert report["completed"] == report["failed"] == 0 and report["stopped_reason"]


def test_rate_limiter_enforces_rolling_rpm_and_supports_cancellation():
    limiter = optimized.RateLimiter(1, 100, window_seconds=.03); stop = threading.Event()
    assert limiter.acquire(50, stop)
    start = time.monotonic(); assert limiter.acquire(50, stop)
    assert time.monotonic() - start >= .02
    stop.set(); assert not limiter.acquire(50, stop)


def grouped_input(tmp_path):
    rows = [json.loads(line) for line in data(1).splitlines()]
    for row in list(rows[1:]):
        if row["event_type"] not in {"tutor_query", "tutor_response"}: continue
        new = json.loads(json.dumps(row)); new["id"] += "-second"
        p = new["payload"]; p["event_id"] += "-second"; p["request_id"] += "-second"; p["client_sequence"] += 100
        if isinstance(p.get("request"), dict): p["request"]["request_id"] = p["request_id"]
        rows.append(new)
    path = tmp_path / "source.jsonl"; path.write_text("\n".join(map(json.dumps,rows)) + "\n")
    db = tmp_path / "source.sqlite"; source = bulk.index_source(path, db)
    return db, source


def test_grouping_retains_all_anchors_and_does_not_write_the_source_index(tmp_path):
    db, source = grouped_input(tmp_path); original = h.file_hash(db)
    result = grouped.prepare_batches(db, tmp_path / "grouped", source)
    assert result["coverage"]["eligible"] == 2 and result["coverage"]["analysis_units"] == 1
    ledger = [json.loads(line) for line in (tmp_path / "grouped/coverage.private.jsonl").read_text().splitlines()]
    assert len(ledger) == 2 and len({r["session_id"] for r in ledger}) == 1
    _, sessions, contexts, _ = h.load_prepared(tmp_path / "grouped/batch-0001")
    assert len(sessions[0].messages) == 4 and len(next(iter(contexts.values()))["group_anchor_event_ids"]) == 2
    assert h.file_hash(db) == original


def test_oversized_groups_fall_back_to_original_anchor_windows(tmp_path, monkeypatch):
    db, source = grouped_input(tmp_path)
    original = grouped.recent.normalize_session
    def normalized(*args, **kwargs):
        session, ctx, evidence, quality = original(*args, **kwargs)
        if len(kwargs["window"]["anchor_event_ids"]) > 1: evidence["budget_test_padding"] = "x" * 450001
        return session, ctx, evidence, quality
    monkeypatch.setattr(grouped.recent, "normalize_session", normalized)
    result = grouped.prepare_batches(db, tmp_path / "fallback", source)
    assert result["coverage"]["eligible"] == result["coverage"]["analysis_units"] == 2


class FakeAPI:
    def __init__(self, *, omit=False, uncertain=False, duplicate=False):
        self.uploads, self.creates, self.outputs = [], [], {}
        self.omit, self.uncertain, self.duplicate = omit, uncertain, duplicate
        self.files = SimpleNamespace(upload=self.upload, download=self.download)
        self.batches = SimpleNamespace(create=self.create, get=self.get)
    def upload(self, *, file, config):
        self.uploads.append(Path(file).read_text()); return SimpleNamespace(name=f"files/input-{len(self.uploads)}")
    def create(self, *, model, src, config):
        index = int(src.rsplit("-",1)[1])-1; rows = [json.loads(line) for line in self.uploads[index].splitlines()]
        outputs = []
        for row in rows:
            text = row["request"]["contents"][0]["parts"][0]["text"]
            # Session ID is present in both the raw and lossless wire encoding.
            import re
            session_id = re.search(r'"session_id":"([^"]+)"',text).group(1)
            assessment = analyzer.Assessment(session_id=session_id, decision="no_supported_finding", summary="Authored native batch test.")
            outputs.append({"key":row["key"],"response":{"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":assessment.model_dump_json()}]}}],"usageMetadata":{"promptTokenCount":100,"candidatesTokenCount":10}}})
        if self.omit: outputs = outputs[:-1]
        if self.duplicate: outputs.append(outputs[0])
        name=f"batches/test-{len(self.creates)+1}"; self.creates.append(name)
        self.outputs[name]="\n".join(json.dumps(x) for x in reversed(outputs))+"\n"
        if self.uncertain: self.uncertain=False; raise TimeoutError("private payload")
        return SimpleNamespace(name=name)
    def get(self, *, name): return SimpleNamespace(state="JOB_STATE_SUCCEEDED",dest=SimpleNamespace(file_name=name))
    def download(self, *, file, destination): destination.write(self.outputs[file].encode())
    def close(self): pass


def native_plan(tmp_path, count=2):
    paths=prepared(tmp_path,count); options=provider.Options(transport="batch")
    folder=tmp_path/"native"
    native_batch.prepare(paths,folder,model="fictional",options=options,cache_folder=tmp_path/"cache")
    return paths,options,folder


def test_native_batch_preparation_is_offline_and_result_routing_survives_restart(tmp_path, monkeypatch):
    paths,options,folder=native_plan(tmp_path); api=FakeAPI()
    assert not list((paths[0]/"analysis-optimized").glob("*.json")) == []  # Frozen local plan only.
    assert not api.creates
    native_batch.submit(folder,options=options,api=api,send=True)
    with monkeypatch.context() as patch:
        patch.setattr(native_batch, "routes_for", lambda *_: pytest.fail("Polling must not rescan submitted inputs"))
        native_batch.submit(folder,options=options,api=api,send=True)
    assert len(api.creates)==len(api.uploads)==1
    result=native_batch.collect(folder,options=options,api=api)
    assert result["completed"]==2 and result["usage"]["input_tokens"]==200
    assert len(optimized.saved_results(paths[0],"fictional",options))==2
    native_batch.collect(folder,options=options,api=api)
    assert len(api.creates)==1


def test_unknown_submission_is_not_resent_and_can_be_attached_explicitly(tmp_path):
    _,options,folder=native_plan(tmp_path); api=FakeAPI(uncertain=True)
    with pytest.raises(TimeoutError): native_batch.submit(folder,options=options,api=api,send=True)
    with pytest.raises(ValueError,match="unknown"):
        native_batch.submit(folder,options=options,api=api,send=True)
    assert len(api.creates)==1
    native_batch.attach(folder,chunk_number=1,remote_name=api.creates[0])
    assert native_batch.collect(folder,options=options,api=api)["completed"]==2


def test_missing_batch_results_remain_failures_not_negative_findings(tmp_path):
    paths,options,folder=native_plan(tmp_path); api=FakeAPI(omit=True)
    native_batch.submit(folder,options=options,api=api,send=True)
    result=native_batch.collect(folder,options=options,api=api)
    assert result["completed"]==result["failed"]==1
    failures=[r for r in optimized.saved_results(paths[0],"fictional",options).values() if r["validation_status"]!="valid"]
    assert failures[0]["decision"]=="insufficient_evidence" and not failures[0]["assessment"]["findings"]


def test_duplicate_remote_keys_are_rejected_before_accepting_any_result(tmp_path):
    paths,options,folder=native_plan(tmp_path); api=FakeAPI(duplicate=True)
    native_batch.submit(folder,options=options,api=api,send=True)
    with pytest.raises(ValueError,match="duplicate"): native_batch.collect(folder,options=options,api=api)
    assert optimized.statistics(paths)["completed"]==0


def test_native_batch_budget_is_checked_before_upload_or_dispatch(tmp_path):
    paths=prepared(tmp_path,2); options=provider.Options(transport="batch",max_requests=1)
    with pytest.raises(ValueError,match="request budget"):
        native_batch.prepare(paths,tmp_path/"native",model="fictional",options=options,cache_folder=tmp_path/"cache")
    assert optimized.statistics(paths)["pending"]==0


def test_native_batch_admits_waves_within_the_enqueued_token_allowance(tmp_path):
    paths=prepared(tmp_path,2)
    options=provider.Options(transport="batch")
    unit=next(optimized.units(paths,"fictional",options))
    _,_,metrics=provider.payload(unit.evidence,options)
    options=replace(options,batch_enqueued_tokens=metrics["estimated_tokens"]+10)
    folder=tmp_path/"native"
    state=native_batch.prepare(paths,folder,model="fictional",options=options,cache_folder=tmp_path/"cache")
    assert len(state["chunks"])==2
    api=FakeAPI();native_batch.submit(folder,options=options,api=api,send=True)
    assert len(api.creates)==1
    assert native_batch.collect(folder,options=options,api=api)["provider_status"]=="submitted"
    native_batch.submit(folder,options=options,api=api,send=True)
    assert len(api.creates)==2
    assert native_batch.collect(folder,options=options,api=api)["completed"]==2
