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
from contextlib import contextmanager
import socket
import subprocess
import time

from .historical import timestamp, private_json, file_hash
from . import production

DEPLOYED = timestamp("2026-10-13T17:30:00Z")
EVENT_TYPES = ["tutor_query", "tutor_response", "tutor_request_failed", "tutor_notebook_info",
    "notebook_execution_requested", "notebook_execution_finished", "autograder_info",
    "notebook_cell_source_changed", "notebook_cell_created", "notebook_cell_deleted",
    "notebook_cell_moved", "notebook_active_cell_changed", "notebook_cell_task_context_changed"]


def export_all(destination, *, since=None, until=None, key_file=None, connect=None):
    """Stream a fixed production snapshot; no sampling or tutor-scope limit."""
    until = until or datetime.now(timezone.utc)
    since = since or production.DEPLOYED
    if any(at.utcoffset() is None for at in (since, until)) or not production.DEPLOYED <= since < until:
        raise ValueError("Choose a range after the observed PR100 production start, October 13 at 10:30:59 Pacific.")
    destination = Path(destination)
    if destination.exists() or destination.is_symlink(): raise FileExistsError(destination)
    key_file = Path(key_file or destination.parent / ".pr100-pseudonym.key")
    key_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if key_file.is_symlink(): raise ValueError("The private pseudonym key cannot be a symlink.")
    if not key_file.exists():
        with key_file.open("xb") as f:
            os.chmod(key_file, 0o600)
            f.write(secrets.token_bytes(32))
    salt = key_file.read_bytes()
    if len(salt) != 32: raise ValueError("Invalid private pseudonym key; preserve the original 32-byte file.")
    if connect is None:
        import psycopg2
        connect = psycopg2.connect
    conn = connect()
    source = destination / "events.jsonl.gz"
    try:
        conn.set_session(readonly=True, isolation_level="REPEATABLE READ")
        with conn.cursor() as q: q.execute("SET statement_timeout='120s'")
        destination.mkdir(parents=True, mode=0o700)
        counts = Counter()
        first = last = None
        header = {"format": production.EXPORT_FORMAT, "since": since.isoformat(), "until": until.isoformat(),
            "production_boundary": production.DEPLOYED.isoformat(),
            "boundary_basis": "First verified schema-v1 production receipt, not Git merge time; clients can upgrade at different times.",
            "selection": "All received schema-v1 events in [since,until); no scope sampling or account-name exclusion.",
            "pseudonym_key_id": hashlib.sha256(salt).hexdigest()[:16]}
        with conn.cursor(name="pr100_full_export") as q, source.open("xb") as raw:
            os.chmod(source, 0o600)
            with gzip.open(raw, "wt", encoding="utf-8", compresslevel=5) as stream:
                stream.write(json.dumps(header) + "\n")
                q.itersize = 2000
                q.execute("""SELECT id,event_type,user_email,payload,created_at FROM events
                    WHERE created_at >= %s AND created_at < %s AND payload->>'schema_version'='1'
                    ORDER BY created_at,id""", (since, until))
                for event_id, kind, email, payload, at in q:
                    account = "STU-" + hmac.new(salt, str(email).strip().lower().encode(), hashlib.sha256).hexdigest()[:24] if email else None
                    stream.write(json.dumps({"id": event_id, "event_type": kind, "user_email": account,
                        "payload": payload, "created_at": at.isoformat()}, ensure_ascii=False, separators=(",", ":")) + "\n")
                    counts[kind] += 1
                    first, last = first or at.isoformat(), at.isoformat()
        manifest = {**header, "event_count": sum(counts.values()), "event_type_counts": dict(counts),
            "first_event_at": first, "last_event_at": last, "events_sha256": file_hash(source),
            "compressed_bytes": source.stat().st_size, "contains_private_course_content": True,
            "privacy": "Account column pseudonymized consistently using the operator's private key. Payload code/text remains private."}
        private_json(destination / "manifest.json", manifest)
        return manifest
    except Exception:
        if source.exists(): source.rename(destination / "INCOMPLETE-events.jsonl.gz.partial")
        raise
    finally:
        conn.close()


def load_database_env(path):
    """Explicit file only; load database fields, never provider keys or arbitrary env."""
    from dotenv import dotenv_values
    values = dotenv_values(path)
    for name, alias in {"PGHOST": "PG_HOST", "PGPORT": "PG_PORT", "PGDATABASE": "PG_DATABASE", "PGUSER": "PG_USER", "PGPASSWORD": "PG_PASSWORD"}.items():
        value = values.get(name) or values.get(alias)
        if value: os.environ[name] = value


@contextmanager
def production_tunnel(enabled):
    if not enabled:
        yield
        return
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    proc = subprocess.Popen(["kubectl", "port-forward", "pod/dsc10-tutor-logs-prod-0", f"{port}:5432", "--address=127.0.0.1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            if proc.poll() is not None: raise ValueError("Production tunnel failed. Check kubectl context, namespace and cluster permissions.")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.2): break
            except OSError: time.sleep(.1)
        else: raise ValueError("Production tunnel did not become ready.")
        os.environ.update(PGHOST="127.0.0.1", PGPORT=str(port))
        os.environ.setdefault("PGDATABASE", "dsc10_tutor_logs")
        os.environ.setdefault("PGUSER", "dsc10_tutor")
        yield
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait()


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
    parser.add_argument("--all", action="store_true", help="Export every schema-v1 event in the range; defaults to the observed production start.")
    parser.add_argument("--env-file", type=Path, help="Operator-only explicit file containing PostgreSQL credentials.")
    parser.add_argument("--port-forward", action="store_true", help="Open and close a local tunnel to the production log pod using your kubectl permissions.")
    parser.add_argument("--pseudonym-key", type=Path, help="Persistent private key for consistent account pseudonyms across full exports.")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.env_file: load_database_env(args.env_file)
        with production_tunnel(args.port_forward):
            if args.all:
                m = export_all(args.output, since=args.since, until=args.until, key_file=args.pseudonym_key)
            else:
                m = extract(args.output, since=args.since, until=args.until, max_scopes=args.scopes)
    except (ValueError, FileExistsError) as error:
        raise SystemExit(str(error)) from None
    except Exception as error:
        raise SystemExit(f"Read-only extraction failed ({type(error).__name__}). Check the operator's database connection.") from None
    print(json.dumps({"output": str(args.output / "events.jsonl.gz"), "events": m["event_count"], "selection": "all schema-v1 events in range" if args.all else "sampled scopes", "until": m["until"]}))


if __name__ == "__main__":
    main()
