"""The privileged extraction command is separate and always read-only."""
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path

import pytest

from session_review.findings.extract import extract
from session_review.findings.web import inspect_upload

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/findings/pr100-upload.synthetic.jsonl"


class Cursor:
    def __init__(self, db, named=False): self.db, self.named = db, named
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, query, args=None): self.db.queries.append((query, args))
    def fetchall(self): return [("fictional@example.invalid", "fictional-page", "fictional-notebook")]
    def __iter__(self):
        for line in FIXTURE.read_text().splitlines():
            row = json.loads(line)
            yield row["id"], row["event_type"], "fictional@example.invalid", row["payload"], datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))


class Database:
    def __init__(self): self.queries, self.readonly, self.closed = [], False, False
    def set_session(self, *, readonly, isolation_level): self.readonly = readonly; self.isolation = isolation_level
    def cursor(self, name=None): return Cursor(self, name is not None)
    def close(self): self.closed = True


def test_export_is_readonly_pr100_only_and_preserves_exact_snapshots(tmp_path):
    db = Database()
    output = tmp_path / "operator-export"
    m = extract(output, since=datetime(2026, 10, 15, tzinfo=timezone.utc), until=datetime(2026, 10, 16, tzinfo=timezone.utc), connect=lambda: db)
    assert db.readonly and db.closed and db.isolation == "REPEATABLE READ"
    selects = [query for query, _ in db.queries if "SELECT" in query]
    assert len(selects) == 2 and all("payload->>'schema_version'='1'" in query for query in selects)
    assert all(args is not None for query, args in db.queries if "SELECT" in query)
    assert m["historical_fallback"] is False and m["event_count"] == 7
    assert inspect_upload(output / "events.jsonl.gz")["events"] == 7
    with gzip.open(output / "events.jsonl.gz", "rt") as f: exported = [json.loads(line) for line in f]
    original = [json.loads(line) for line in FIXTURE.read_text().splitlines()]
    assert all(row["user_email"].startswith("STU-") for row in exported)
    assert [row["payload"] for row in exported] == [row["payload"] for row in original]


def test_bad_range_fails_before_connecting_or_creating_an_export(tmp_path):
    with pytest.raises(ValueError, match="PR100 range"):
        extract(tmp_path / "bad", since=datetime(2026, 1, 1, tzinfo=timezone.utc), connect=lambda: pytest.fail("Unexpected database access"))
    assert not (tmp_path / "bad").exists()
