"""Operator-only recent PR100 export. Never imported by the upload service."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets

from .historical import timestamp, private_json, file_hash

DEPLOYED = timestamp("2026-10-13T17:30:00Z")
EVENT_TYPES = ["tutor_query", "tutor_response", "tutor_request_failed", "tutor_notebook_info",
    "notebook_execution_requested", "notebook_execution_finished", "autograder_info",
    "notebook_cell_source_changed", "notebook_cell_created", "notebook_cell_deleted",
    "notebook_cell_moved", "notebook_active_cell_changed", "notebook_cell_task_context_changed"]


def extract(destination, *, since=None, until=None, max_scopes=30, connect=None):
    until = until or datetime.now(timezone.utc)
    since = since or max(DEPLOYED, until - timedelta(hours=24))
    if any(at.utcoffset() is None for at in (since, until)) or not DEPLOYED <= since < until or until - since > timedelta(days=7):
        raise ValueError("Choose a timezone-aware PR100 range after October 13, 2026, at most seven days long.")
    if type(max_scopes) is not int or not 1 <= max_scopes <= 100:
        raise ValueError("Choose 1–100 page/notebook scopes per export.")
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    if connect is None:
        try:
            import psycopg2
        except ImportError:
            raise ValueError("Install the operator-only extraction dependency: uv sync --extra extract") from None
        connect = psycopg2.connect  # Uses the operator's standard PG* configuration.
    conn = connect()
    salt = secrets.token_bytes(32)
    def account(value):
        return "STU-" + hmac.new(salt, str(value).lower().encode(), hashlib.sha256).hexdigest()[:24]
    try:
        conn.set_session(readonly=True, isolation_level="REPEATABLE READ")
        with conn.cursor() as q:
            q.execute("SET statement_timeout='120s'")
            q.execute("""SELECT user_email,payload->>'analytics_session_id',payload->>'notebook_session_id'
                FROM events WHERE created_at >= %s AND created_at < %s AND event_type='tutor_query'
                AND payload->>'schema_version'='1' AND payload->>'mode'='tutor'
                AND payload ? 'event_id' AND payload ? 'request_id' AND user_email IS NOT NULL
                AND lower(user_email) NOT LIKE '%%test%%' ORDER BY id DESC LIMIT 5000""",
                (since, until - timedelta(minutes=30)))
            candidates = q.fetchall()
        selected, seen = [], set()
        for email, page, notebook in candidates:
            if not page or not notebook or (page, notebook) in seen:
                continue
            seen.add((page, notebook))
            selected.append({"student_id": account(email), "analytics_session_id": page, "notebook_session_id": notebook})
            if len(selected) == max_scopes:
                break
        if not selected:
            raise ValueError("No matching recent PR100 tutor sessions in that range.")
        destination.mkdir(parents=True, mode=0o700)
        counts = Counter()
        first = last = None
        source = destination / "events.jsonl.gz"
        with conn.cursor(name="pr100_operator_export") as q, gzip.open(source, "xt", encoding="utf-8", compresslevel=5) as stream:
            q.itersize = 500
            q.execute("""SELECT id,event_type,user_email,payload,created_at FROM events
                WHERE created_at >= %s AND created_at < %s AND payload->>'schema_version'='1'
                AND payload->>'analytics_session_id'=ANY(%s) AND event_type=ANY(%s)
                AND payload ? 'event_id' AND user_email IS NOT NULL
                AND lower(user_email) NOT LIKE '%%test%%' ORDER BY created_at,id""",
                (since, until, list({s["analytics_session_id"] for s in selected}), EVENT_TYPES))
            for event_id, kind, email, payload, at in q:
                if sum(counts.values()) >= 100_000:
                    raise ValueError("Export exceeds 100,000 events. Choose fewer scopes; this partial export must not be uploaded.")
                stream.write(json.dumps({"id": event_id, "event_type": kind, "user_email": account(email),
                    "payload": payload, "created_at": at.isoformat()}, ensure_ascii=False, separators=(",", ":")) + "\n")
                counts[kind] += 1
                first, last = first or at.isoformat(), at.isoformat()
        os.chmod(source, 0o600)
        manifest = {"format": "pr100.production-source.v2", "source": "Operator read-only production events export",
            "contains_private_course_content": True, "historical_fallback": False,
            "since": since.isoformat(), "until": until.isoformat(), "event_count": sum(counts.values()),
            "event_type_counts": dict(counts), "first_event_at": first, "last_event_at": last,
            "selected_scopes": selected, "events_sha256": file_hash(source),
            "selection": "Most recent tutor-bearing page/notebook scopes; requests at least 30 minutes before the export boundary. Development sample, not complete population.",
            "privacy": "Account column pseudonymized; payload text, code and notebook content remain private. Exact notebook snapshot strings retained for SHA256 verification."}
        private_json(destination / "manifest.json", manifest)
        return manifest
    except Exception:
        # An incomplete source is visibly named and cannot be mistaken for a
        # successful upload file; never delete original database records.
        source = destination / "events.jsonl.gz"
        if source.exists():
            source.rename(destination / "INCOMPLETE-events.jsonl.gz.partial")
        raise
    finally:
        conn.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--since", type=timestamp)
    parser.add_argument("--until", type=timestamp)
    parser.add_argument("--scopes", type=int, default=30)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        m = extract(args.output, since=args.since, until=args.until, max_scopes=args.scopes)
    except (ValueError, FileExistsError) as error:
        raise SystemExit(str(error)) from None
    except Exception as error:
        raise SystemExit(f"Read-only extraction failed ({type(error).__name__}). Check the operator's database connection.") from None
    print(json.dumps({"output": str(args.output / "events.jsonl.gz"), "events": m["event_count"], "scopes": len(m["selected_scopes"])}))


if __name__ == "__main__":
    main()
