"""Compare recorded tutor/student outcomes with proposed-policy simulations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

from src.agents import chat_workspace, notebook_student as store
from src.agents.notebook_tutor import Reply
from src.eval import student_continuation
from src.ingest.rawlog import Conversation
from src.labeling import episodes


VERSION = 1
MODEL = "gemini-2.5-pro"
MAX_CASES = 24
DEFAULT_DEVELOPMENT_CONVERSATIONS = 12
DEFAULT_SEED = 0


def _source_hashes():
    modules = (chat_workspace, student_continuation, episodes)
    return {
        Path(path).name: store.digest(Path(path).read_text())
        for path in [__file__, *(module.__file__ for module in modules)]
    }


def _turn(turn):
    return {key: turn[key] for key in ("id", "role", "text")}


def _case_from_episode(case_id, episode):
    request = [_turn(turn) for turn in episode["turns"]
               if turn["phase"] == "request" and turn["role"] == "student"]
    recorded_tutor = [_turn(turn) for turn in episode["turns"]
                      if turn["phase"] == "response" and turn["role"] == "tutor"]
    recorded_followup = [_turn(turn) for turn in episode["turns"]
                         if turn["phase"] == "followup" and turn["role"] == "student"]
    if not request or not recorded_tutor:
        raise ValueError("A policy case needs a recorded request and tutor response.")
    source = {
        "context": [_turn(turn) for turn in episode.get("context", [])],
        "request": request,
        "recorded_tutor": recorded_tutor,
        "recorded_followup": recorded_followup,
    }
    return {
        "version": VERSION,
        "case_id": case_id,
        "conversation_key": episode["conversation_key"],
        "source": source,
        "source_sha256": store.digest(source),
    }


def _selected_cases(snapshot, *, case_count, development_conversations, seed):
    if type(case_count) is not int or not 1 <= case_count <= MAX_CASES:
        raise ValueError(f"Choose between 1 and {MAX_CASES} holdout conversations.")
    if type(development_conversations) is not int or development_conversations < 1:
        raise ValueError("Reserve at least one development conversation.")
    if type(seed) is not int:
        raise ValueError("The selection seed must be an integer.")
    source = Path(snapshot) / "conversations.jsonl"
    raw = source.read_bytes()
    conversations = [
        Conversation.model_validate_json(line)
        for line in raw.splitlines() if line.strip()
    ]
    if len({conversation.conv_id for conversation in conversations}) != len(conversations):
        raise ValueError("Snapshot conversation identifiers must be unique.")
    candidates = []
    for conversation in conversations:
        options = episodes._episodes(conversation, {})
        if not options:
            continue
        conversation_rank = store.digest({
            "seed": seed,
            "conversation": conversation.conv_id,
        })
        chosen = min(options, key=lambda episode: store.digest({
            "seed": seed,
            "episode": episode["id"],
        }))
        candidates.append((conversation_rank, chosen))
    candidates.sort(key=lambda item: item[0])
    needed = development_conversations + case_count
    if len(candidates) < needed:
        raise ValueError(
            f"Need {needed} eligible conversations for the requested split; "
            f"the snapshot has {len(candidates)}."
        )
    holdout = candidates[development_conversations:needed]
    cases = [
        _case_from_episode(f"case-{index:04d}", episode)
        for index, (_, episode) in enumerate(holdout, 1)
    ]
    return raw, len(conversations), len(candidates), cases


def _tutor_context(source):
    return {
        "dialogue": [*source["context"], *source["request"][:-1]],
        "pending_message": source["request"][-1]["text"],
    }


def _tutor_prompt(source, proposed_policy):
    return chat_workspace.PROMPT + json.dumps({
        "policy": proposed_policy,
        "context": _tutor_context(source),
    }, ensure_ascii=False, sort_keys=True)


def _student_episode(source, proposed_tutor):
    return {
        "id": "proposed-policy-continuation",
        "context": [dict(turn) for turn in source["context"]],
        "turns": [
            *[dict(turn, phase="request") for turn in source["request"]],
            {
                "id": "proposed-tutor",
                "role": "tutor",
                "phase": "response",
                "text": proposed_tutor,
            },
        ],
    }


def _student_prompt(source, proposed_tutor):
    return student_continuation.make_prompt(_student_episode(source, proposed_tutor))


def prepare(snapshot, folder, *, proposed_policy, case_count=MAX_CASES,
            development_conversations=DEFAULT_DEVELOPMENT_CONVERSATIONS,
            seed=DEFAULT_SEED):
    """Freeze a conversation-held-out cohort without making provider requests."""
    if not isinstance(proposed_policy, str) or not proposed_policy.strip():
        raise ValueError("Enter a proposed tutor policy.")
    snapshot, folder = Path(snapshot), Path(folder)
    if folder.exists() or folder.is_symlink():
        raise FileExistsError(folder)
    raw, source_count, eligible_count, cases = _selected_cases(
        snapshot,
        case_count=case_count,
        development_conversations=development_conversations,
        seed=seed,
    )
    manifest = {
        "version": VERSION,
        "status": "prepared",
        "contains_private_content": True,
        "model": MODEL,
        "proposed_policy": proposed_policy,
        "logical_requests_if_fully_run": len(cases) * 2,
        "selection": {
            "seed": seed,
            "development_conversations": development_conversations,
            "holdout_conversations": len(cases),
            "unit": "conversation",
            "learner_identity_available": False,
        },
        "source": {
            "snapshot": snapshot.name,
            "conversations_sha256": sha256(raw).hexdigest(),
            "conversation_count": source_count,
            "eligible_conversations": eligible_count,
        },
        "cases": [
            {
                "case_id": case["case_id"],
                "conversation_key": case["conversation_key"],
                "source_sha256": case["source_sha256"],
            }
            for case in cases
        ],
        "sources": _source_hashes(),
    }
    manifest["sha256"] = store.digest(manifest)
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.parent, prefix=".observed-policy-") as temporary:
        staged = Path(temporary) / "cohort"
        staged.mkdir()
        store._save(staged / "manifest.json", manifest, exclusive=True)
        for case in cases:
            case_folder = staged / "cases" / case["case_id"]
            case_folder.mkdir(parents=True)
            store._save(case_folder / "source.json", case, exclusive=True)
        folder.mkdir(exist_ok=False)
        os.replace(staged, folder)
    return show(folder)


def _manifest(folder):
    manifest = store._read(Path(folder) / "manifest.json")
    unsigned = {key: value for key, value in manifest.items() if key != "sha256"}
    valid = (
        manifest.get("version") == VERSION
        and manifest.get("status") == "prepared"
        and manifest.get("contains_private_content") is True
        and manifest.get("sha256") == store.digest(unsigned)
        and manifest.get("model") == MODEL
        and isinstance(manifest.get("proposed_policy"), str)
        and bool(manifest["proposed_policy"].strip())
        and manifest.get("sources") == _source_hashes()
        and isinstance(manifest.get("cases"), list)
        and 1 <= len(manifest["cases"]) <= MAX_CASES
        and manifest.get("logical_requests_if_fully_run") == len(manifest["cases"]) * 2
    )
    if not valid:
        raise ValueError("Observed-policy cohort manifest changed or is unsupported.")
    return manifest


def _case(folder, pin):
    case = store._read(Path(folder) / "cases" / pin["case_id"] / "source.json")
    valid = (
        case.get("version") == VERSION
        and case.get("case_id") == pin["case_id"]
        and case.get("conversation_key") == pin["conversation_key"]
        and case.get("source_sha256") == pin["source_sha256"]
        and case.get("source_sha256") == store.digest(case.get("source"))
        and isinstance(case.get("source"), dict)
        and set(case["source"]) == {
            "context", "request", "recorded_tutor", "recorded_followup",
        }
        and bool(case["source"]["request"])
        and bool(case["source"]["recorded_tutor"])
    )
    if not valid:
        raise ValueError(f'{pin["case_id"]} source changed or is unsupported.')
    return case


def _receipt(folder, manifest, case):
    path = Path(folder) / "cases" / case["case_id"] / "proposed.json"
    if not path.exists():
        return None
    receipt = store._read(path)
    source = case["source"]
    tutor = receipt.get("tutor", {})
    student = receipt.get("student", {})
    expected_tutor_prompt = _tutor_prompt(source, manifest["proposed_policy"])
    valid = (
        receipt.get("version") == VERSION
        and receipt.get("case_id") == case["case_id"]
        and receipt.get("source_sha256") == case["source_sha256"]
        and tutor.get("prompt") == expected_tutor_prompt
        and tutor.get("schema") == Reply.model_json_schema()
        and tutor.get("status") in {"pending", "complete", "error"}
        and student.get("status") in {"not-started", "pending", "complete", "error"}
    )
    if tutor.get("status") == "complete":
        try:
            tutor_reply = Reply.model_validate(tutor.get("response")).text
        except Exception as exc:
            raise ValueError("Saved proposed tutor response is invalid.") from exc
        valid = valid and student.get("prompt") == _student_prompt(source, tutor_reply)
        valid = valid and student.get("schema") == student_continuation.Continuation.model_json_schema()
        if student.get("status") == "complete":
            try:
                student_continuation.Continuation.model_validate(student.get("response"))
            except Exception as exc:
                raise ValueError("Saved proposed student response is invalid.") from exc
    else:
        valid = valid and student.get("status") == "not-started"
    if not valid:
        raise ValueError(f'{case["case_id"]} proposed result changed or is unsupported.')
    return receipt


def _proposed_outcome(receipt):
    if receipt is None:
        return "ready"
    tutor_status = receipt["tutor"]["status"]
    student_status = receipt["student"]["status"]
    if tutor_status == "error" or student_status == "error":
        return "failed"
    if tutor_status == "pending" or student_status == "pending":
        return "incomplete"
    if tutor_status != "complete" or student_status != "complete":
        return "incomplete"
    response = student_continuation.Continuation.model_validate(
        receipt["student"]["response"]
    )
    return "student-replied" if response.decision == "reply" else "no-follow-up"


def _pair_outcome(recorded, proposed):
    if proposed not in {"student-replied", "no-follow-up"}:
        return "not-comparable"
    if recorded == proposed == "student-replied":
        return "both-replied"
    if recorded == proposed == "no-follow-up":
        return "both-no-follow-up"
    if recorded == "no-follow-up":
        return "proposed-gained-follow-up"
    return "proposed-lost-follow-up"


def _rate(numerator, denominator):
    return numerator / denominator if denominator else None


def show(folder):
    """Verify and summarize a saved cohort without provider calls or writes."""
    folder = Path(folder)
    manifest = _manifest(folder)
    cases = []
    proposed_counts = {status: 0 for status in (
        "ready", "student-replied", "no-follow-up", "incomplete", "failed",
    )}
    pair_counts = {status: 0 for status in (
        "both-replied", "both-no-follow-up", "proposed-gained-follow-up",
        "proposed-lost-follow-up", "not-comparable",
    )}
    recorded_replied = 0
    for pin in manifest["cases"]:
        case = _case(folder, pin)
        receipt = _receipt(folder, manifest, case)
        recorded = ("student-replied" if case["source"]["recorded_followup"]
                    else "no-follow-up")
        proposed = _proposed_outcome(receipt)
        pair = _pair_outcome(recorded, proposed)
        recorded_replied += recorded == "student-replied"
        proposed_counts[proposed] += 1
        pair_counts[pair] += 1
        cases.append({
            **case,
            "recorded_outcome": recorded,
            "proposed_outcome": proposed,
            "comparison_outcome": pair,
            "proposed": receipt,
        })
    comparable = len(cases) - pair_counts["not-comparable"]
    proposed_replied = pair_counts["both-replied"] + pair_counts["proposed-gained-follow-up"]
    recorded_replied_comparable = pair_counts["both-replied"] + pair_counts["proposed-lost-follow-up"]
    changed = pair_counts["proposed-gained-follow-up"] + pair_counts["proposed-lost-follow-up"]
    recorded_rate = _rate(recorded_replied_comparable, comparable)
    proposed_rate = _rate(proposed_replied, comparable)
    return {
        "manifest": manifest,
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "recorded": {
                "student-replied": recorded_replied,
                "no-follow-up": len(cases) - recorded_replied,
            },
            "proposed": proposed_counts,
            "comparisons": pair_counts,
            "statistics": {
                "comparable_cases": comparable,
                "coverage_rate": _rate(comparable, len(cases)),
                "recorded_reply_rate": recorded_rate,
                "proposed_reply_rate": proposed_rate,
                "reply_rate_difference": (
                    proposed_rate - recorded_rate
                    if proposed_rate is not None and recorded_rate is not None
                    else None
                ),
                "changed_cases": changed,
                "changed_rate": _rate(changed, comparable),
                "net_follow_up_change": (
                    pair_counts["proposed-gained-follow-up"]
                    - pair_counts["proposed-lost-follow-up"]
                ),
            },
        },
    }


def _run_case(folder, manifest, pin, generate_tutor, generate_student):
    case = _case(folder, pin)
    case_folder = Path(folder) / "cases" / case["case_id"]
    path = case_folder / "proposed.json"
    if path.exists():
        _receipt(folder, manifest, case)
        return
    tutor_prompt = _tutor_prompt(case["source"], manifest["proposed_policy"])
    receipt = {
        "version": VERSION,
        "case_id": case["case_id"],
        "source_sha256": case["source_sha256"],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "tutor": {
            "status": "pending",
            "prompt": tutor_prompt,
            "schema": Reply.model_json_schema(),
        },
        "student": {"status": "not-started"},
    }
    store._save(path, receipt, exclusive=True)
    try:
        tutor = Reply.model_validate(generate_tutor(tutor_prompt, Reply).model_dump())
    except Exception as error:
        receipt["tutor"].update(
            status="error",
            error={"type": type(error).__name__, "message": str(error)},
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        store._save(path, receipt)
        return
    receipt["tutor"].update(
        status="complete",
        response=tutor.model_dump(),
        finished_at=datetime.now(timezone.utc).isoformat(),
    )
    student_prompt = _student_prompt(case["source"], tutor.text)
    receipt["student"] = {
        "status": "pending",
        "prompt": student_prompt,
        "schema": student_continuation.Continuation.model_json_schema(),
    }
    store._save(path, receipt)
    try:
        student = student_continuation.Continuation.model_validate(
            generate_student(student_prompt, student_continuation.Continuation).model_dump()
        )
    except Exception as error:
        receipt["student"].update(
            status="error",
            error={"type": type(error).__name__, "message": str(error)},
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        store._save(path, receipt)
        return
    receipt["student"].update(
        status="complete",
        response=student.model_dump(),
        finished_at=datetime.now(timezone.utc).isoformat(),
    )
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    store._save(path, receipt)


def run(folder, *, send=False, generate_tutor, generate_student, workers=1):
    """Run each untouched proposed-policy branch once and preserve every result."""
    if send is not True:
        raise ValueError("Running the proposed-policy cohort requires explicit sending permission.")
    if type(workers) is not int or not 1 <= workers <= 8:
        raise ValueError("Use between one and eight concurrent cohort workers.")
    folder = Path(folder)
    manifest = _manifest(folder)
    show(folder)
    pending = [pin for pin in manifest["cases"]
               if not (folder / "cases" / pin["case_id"] / "proposed.json").exists()]
    if workers == 1:
        for pin in pending:
            _run_case(folder, manifest, pin, generate_tutor, generate_student)
    else:
        with ThreadPoolExecutor(max_workers=min(workers, len(pending) or 1)) as executor:
            futures = [executor.submit(
                _run_case, folder, manifest, pin, generate_tutor, generate_student
            ) for pin in pending]
            for future in futures:
                future.result()
    return show(folder)


def runs(workspace):
    """Return verified numbered observed-policy cohorts in creation order."""
    workspace = Path(workspace)
    if not workspace.exists():
        return {}
    if not workspace.is_dir() or workspace.is_symlink():
        raise ValueError("The observed-policy workspace must be a local directory.")
    found = {}
    for path in sorted(workspace.iterdir()):
        if not path.is_dir() or path.is_symlink():
            continue
        if not (path.name.startswith("run-") and len(path.name) == 8
                and path.name[4:].isdigit()):
            continue
        try:
            show(path)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        found[path.name] = path.resolve()
    return found


def prepare_next(workspace, snapshot, **kwargs):
    """Freeze the next numbered cohort and preserve prior runs."""
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    if workspace.is_symlink() or not workspace.is_dir():
        raise ValueError("The observed-policy workspace must be a local directory.")
    with store._locked(workspace):
        existing = runs(workspace)
        number = max((int(name[4:]) for name in existing), default=0) + 1
        destination = workspace / f"run-{number:04d}"
        saved = prepare(snapshot, destination, **kwargs)
    return destination.resolve(), saved
