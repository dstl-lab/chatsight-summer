"""The opt-in app uses isolated jobs and the same review contract."""
import io
import json
import threading
import time

from session_review.findings import provider, web
from session_review.findings.contract import ReviewBundle
from test_findings_bulk import data
from test_findings_optimized import FakeAPI, fake_result


def ready(store, payload):
    state = store.upload_collection(io.BytesIO(payload), len(payload), "fictional.jsonl")
    store.futures[-1].result(timeout=10)
    assert store.summary(state["id"])["status"] == "ready"
    return state["id"]


def test_app_parallelizes_across_review_batches_and_reports_measured_usage(tmp_path):
    active, peak, calls = 0, 0, []
    lock = threading.Lock()
    def generate(evidence,*_):
        nonlocal active,peak
        with lock: active+=1; peak=max(active,peak); calls.append(evidence["session_id"])
        time.sleep(.01)
        with lock: active-=1
        return fake_result(evidence)
    store=web.Jobs(tmp_path/"private",optimization=provider.Options(workers=3,tpm=10_000_000,rpm=1000),optimized_generate=generate)
    try:
        job=ready(store,data(21)); assert not calls
        store.start(job); store.futures[-1].result(timeout=10)
        state=store.summary(job)
        assert state["status"]=="completed" and state["progress"]["completed"]==21
        assert 1<peak<=3 and len(calls)==21
        assert state["runtime"]["usage"]["input_tokens"]==2100
        for batch in state["batches"]:
            view=ReviewBundle.model_validate_json(store.get_bundle(batch["id"]))
            assert all(s.analysis.state=="completed" for s in view.sessions)
    finally: store.executor.shutdown(wait=True)


def test_app_native_batch_submits_one_job_for_multiple_ui_batches(tmp_path):
    api=FakeAPI()
    store=web.Jobs(tmp_path/"private",optimization=provider.Options(transport="batch",batch_enqueued_tokens=10_000_000),batch_api_factory=lambda _:api)
    try:
        job=ready(store,data(21)); assert not api.creates
        store.start(job); store.futures[-1].result(timeout=10)
        state=store.summary(job)
        assert state["status"]=="completed" and state["progress"]["completed"]==21
        assert len(api.creates)==1 and len(state["batches"])==2
        assert state["runtime"]["transport"]=="batch" and state["runtime"]["mean_call_seconds"] is None
    finally: store.executor.shutdown(wait=True)


def test_app_stops_on_budget_and_exports_unanalyzed_units_honestly(tmp_path):
    store=web.Jobs(tmp_path/"private",optimization=provider.Options(workers=2,max_requests=2,tpm=10_000_000),optimized_generate=lambda e,*_:fake_result(e))
    try:
        job=ready(store,data(4)); store.start(job); store.futures[-1].result(timeout=10)
        state=store.summary(job)
        assert state["status"]=="stopped" and state["progress"]["completed"]==2
        view=ReviewBundle.model_validate_json(store.get_bundle(state["batches"][0]["id"]))
        assert sum(s.analysis.state=="not_analyzed" for s in view.sessions)==2
    finally: store.executor.shutdown(wait=True)


def test_app_grouped_profile_counts_units_separately_from_requests(tmp_path):
    rows=[json.loads(line) for line in data(1).splitlines()]
    for row in list(rows[1:]):
        if row["event_type"] not in {"tutor_query","tutor_response"}: continue
        new=json.loads(json.dumps(row));new["id"]+="-next"
        p=new["payload"];p["event_id"]+="-next";p["request_id"]+="-next";p["client_sequence"]+=100
        if isinstance(p.get("request"),dict):p["request"]["request_id"]=p["request_id"]
        rows.append(new)
    store=web.Jobs(tmp_path/"private",optimization=provider.Options(),group_overlap=True)
    try:
        job=ready(store,("\n".join(map(json.dumps,rows))+"\n").encode())
        state=store.summary(job)
        assert state["grouped"] and state["count"]==1 and state["coverage"]["eligible"]==2
        assert state["runtime"]["completed"]==0
    finally:store.executor.shutdown(wait=True)
