"""Freeze and run a bounded cohort of independent tutor-policy comparisons."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import tempfile
from uuid import uuid4

from src.agents import chat_policy_pair, notebook_student as store


MAX_CASES = 24


def _source(path):
    """Validate one eligible source and return its pinned identity."""
    manifest, state, first = chat_policy_pair._source(Path(path))
    return {
        "session_sha256": store.digest(manifest),
        "state_sha256": store.digest(state),
        "first_step_sha256": store.digest(first),
    }


def _prepared_sources(sources):
    if not isinstance(sources, (list, tuple)) or not 1 <= len(sources) <= MAX_CASES:
        raise ValueError(f"Choose between 1 and {MAX_CASES} eligible conversation scenarios.")
    prepared = [(_source(path), Path(path).resolve()) for path in sources]
    hashes = [item[0]["session_sha256"] for item in prepared]
    if len(set(hashes)) != len(hashes):
        raise ValueError("A cohort cannot contain the same conversation scenario twice.")
    manifests = [store._read(path / "session.json") for _, path in prepared]
    if len({manifest["query"]["conversation_id"] for manifest in manifests}) != len(manifests):
        raise ValueError("Use distinct source conversations in a cohort.")
    if len({manifest["model"] for manifest in manifests}) != 1:
        raise ValueError("All cohort sources must use the same model.")
    return sorted(prepared, key=lambda item: item[0]["session_sha256"])


def create(folder, *, sources, current_policy, proposed_policy):
    """Freeze one independent A/B comparison per source without provider calls."""
    policies = {"a": current_policy, "b": proposed_policy}
    if any(not isinstance(value, str) or not value.strip() for value in policies.values()):
        raise ValueError("Enter both the confirmed current policy and the proposed policy.")
    if current_policy.strip() == proposed_policy.strip():
        raise ValueError("The proposed policy must differ from the current policy.")
    prepared = _prepared_sources(sources)
    folder = Path(folder)
    if folder.exists() or folder.is_symlink():
        raise FileExistsError(folder)
    if any(folder.resolve().is_relative_to(path) for _, path in prepared):
        raise ValueError("Keep the cohort outside its frozen sources.")

    plan = {
        "version": 1,
        "cohort_id": uuid4().hex,
        "policies": policies,
        "max_new_decisions": 1,
        "cases": [],
    }
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.parent, prefix=".policy-cohort-") as temporary:
        staged = Path(temporary) / "cohort"
        for index, (source, path) in enumerate(prepared, 1):
            case_id = f"case-{index:04d}"
            pair_path = staged / "cases" / case_id
            from src.agents import policy_comparison_setup
            policy_comparison_setup.freeze(
                pair_path,
                source=path,
                current_policy=current_policy,
                proposed_policy=proposed_policy,
            )
            pair_receipt = store._read(pair_path / "comparison.json")
            plan["cases"].append({
                "case_id": case_id,
                "source": source,
                "pair_plan_sha256": pair_receipt["plan_sha256"],
            })

        for source, path in prepared:
            if _source(path) != source:
                raise ValueError("A source conversation changed while the cohort was being frozen.")
        receipt = {"plan": plan, "plan_sha256": store.digest(plan)}
        store._save(staged / "cohort.json", receipt, exclusive=True)
        folder.mkdir(exist_ok=False)
        os.replace(staged, folder)
    return show(folder)


def _plan(folder):
    folder = Path(folder)
    if folder.is_symlink() or any(path.is_symlink() for path in folder.rglob("*")):
        raise ValueError("Cohort files and directories must not be symbolic links.")
    receipt = store._read(folder / "cohort.json")
    try:
        plan = receipt["plan"]
        cases = plan["cases"]
        valid = (
            set(receipt) == {"plan", "plan_sha256"}
            and receipt["plan_sha256"] == store.digest(plan)
            and set(plan) == {
                "version", "cohort_id", "policies", "max_new_decisions", "cases",
            }
            and plan["version"] == 1
            and isinstance(plan["cohort_id"], str) and bool(plan["cohort_id"])
            and set(plan["policies"]) == {"a", "b"}
            and all(isinstance(value, str) and value.strip()
                    for value in plan["policies"].values())
            and plan["policies"]["a"].strip() != plan["policies"]["b"].strip()
            and plan["max_new_decisions"] == 1
            and isinstance(cases, list) and 1 <= len(cases) <= MAX_CASES
            and [case.get("case_id") for case in cases]
                == [f"case-{index:04d}" for index in range(1, len(cases) + 1)]
            and all(
                isinstance(case.get("source"), dict)
                and set(case["source"]) == {
                    "session_sha256", "state_sha256", "first_step_sha256",
                }
                and all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                        for value in case["source"].values())
                and isinstance(case.get("pair_plan_sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", case["pair_plan_sha256"])
                for case in cases
            )
        )
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("The cohort plan is incomplete or invalid.") from exc
    if not valid:
        raise ValueError("The fixed cohort plan changed or is invalid.")
    return plan


def _outcome(condition):
    return condition["lifecycle"]


def _comparison_outcome(a, b):
    terminal = {"student-replied", "no-follow-up"}
    if a not in terminal or b not in terminal:
        return "not-comparable"
    if a == b == "student-replied":
        return "both-replied"
    if a == b == "no-follow-up":
        return "both-no-follow-up"
    if a == "no-follow-up":
        return "proposed-gained-follow-up"
    return "proposed-lost-follow-up"


def show(folder):
    """Reopen the fixed cohort and compute objective lifecycle counts offline."""
    folder = Path(folder)
    plan = _plan(folder)
    from src.agents import policy_comparison_setup

    cases = []
    counts = {
        name: {status: 0 for status in (
            "ready", "student-replied", "no-follow-up", "incomplete", "failed",
        )}
        for name in ("a", "b")
    }
    comparison_counts = {status: 0 for status in (
        "both-replied", "both-no-follow-up", "proposed-gained-follow-up",
        "proposed-lost-follow-up", "not-comparable",
    )}
    conversations, models = set(), set()
    for case in plan["cases"]:
        pair_path = folder / "cases" / case["case_id"]
        pair_receipt = store._read(pair_path / "comparison.json")
        if pair_receipt.get("plan_sha256") != case["pair_plan_sha256"]:
            raise ValueError(f'{case["case_id"]} no longer matches the frozen cohort plan.')
        comparison = policy_comparison_setup.reopen(pair_path)
        for name in ("a", "b"):
            try:
                _, manifest, _ = chat_policy_pair._startup(pair_path, pair_receipt, name)
            except (OSError, ValueError, KeyError, TypeError):
                continue
            conversation = manifest["query"]["conversation_id"]
            if conversation in conversations:
                raise ValueError("Use distinct source conversations in a cohort.")
            conversations.add(conversation)
            models.add(manifest["model"])
            if len(models) > 1:
                raise ValueError("All cohort sources must use the same model.")
            break
        if ({key: comparison["source"].get(key) for key in case["source"]} != case["source"]
                or {name: comparison["conditions"][name]["policy"] for name in ("a", "b")}
                != plan["policies"]):
            raise ValueError(f'{case["case_id"]} changed from the frozen cohort plan.')
        outcomes = {name: _outcome(comparison["conditions"][name]) for name in ("a", "b")}
        for name, outcome in outcomes.items():
            counts[name][outcome] += 1
        comparison_outcome = _comparison_outcome(outcomes["a"], outcomes["b"])
        comparison_counts[comparison_outcome] += 1
        cases.append({
            "case_id": case["case_id"],
            "source": case["source"],
            "outcomes": outcomes,
            "comparison_outcome": comparison_outcome,
            "comparison": comparison,
        })
    return {
        "cohort_id": plan["cohort_id"],
        "policies": plan["policies"],
        "max_new_decisions": plan["max_new_decisions"],
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "logical_requests_if_fully_run": len(cases) * 4,
            "conditions": counts,
            "comparisons": comparison_counts,
            "different_reply_status": (
                comparison_counts["proposed-gained-follow-up"]
                + comparison_counts["proposed-lost-follow-up"]
            ),
        },
    }


def run(folder, *, send=False, generate_tutor=None, generate_student=None, workers=1):
    """Run every untouched case once; saved failures and completions are not resent."""
    if send is not True:
        raise ValueError("Running the cohort requires explicit sending permission.")
    if type(workers) is not int or not 1 <= workers <= 8:
        raise ValueError("Use between one and eight concurrent cohort workers.")
    folder = Path(folder)
    plan = _plan(folder)
    from src.agents import policy_comparison_setup

    show(folder)

    def run_case(case):
        policy_comparison_setup.run_both(
            folder / "cases" / case["case_id"],
            send=True,
            generate_tutor=generate_tutor,
            generate_student=generate_student,
        )
    if workers == 1:
        for case in plan["cases"]:
            run_case(case)
    else:
        with ThreadPoolExecutor(max_workers=min(workers, len(plan["cases"]))) as executor:
            futures = [executor.submit(run_case, case) for case in plan["cases"]]
            for future in futures:
                future.result()
    return show(folder)


def runs(workspace):
    """Return verified numbered cohort runs in creation order."""
    workspace = Path(workspace)
    if not workspace.exists():
        return {}
    if not workspace.is_dir() or workspace.is_symlink():
        raise ValueError("The cohort workspace must be a local directory.")
    found = {}
    for path in sorted(workspace.iterdir()):
        if not path.is_dir() or path.is_symlink():
            continue
        name = path.name
        if not (name.startswith("cohort-") and len(name) == 11 and name[7:].isdigit()):
            continue
        try:
            show(path)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        found[name] = path.resolve()
    return found


def freeze_next(workspace, *, sources, current_policy, proposed_policy):
    """Freeze the next numbered cohort while refusing an exact rerun."""
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    if workspace.is_symlink() or not workspace.is_dir():
        raise ValueError("The cohort workspace must be a local directory.")
    prepared = _prepared_sources(sources)
    source_hashes = [source["session_sha256"] for source, _ in prepared]
    policies = {"a": current_policy, "b": proposed_policy}
    with store._locked(workspace):
        existing = runs(workspace)
        for path in existing.values():
            plan = _plan(path)
            if ([case["source"]["session_sha256"] for case in plan["cases"]] == source_hashes
                    and plan["policies"] == policies):
                raise ValueError(f"This exact cohort and policy pair already exists as {path.name}.")
        number = max((int(name[7:]) for name in existing), default=0) + 1
        destination = workspace / f"cohort-{number:04d}"
        saved = create(
            destination,
            sources=[path for _, path in prepared],
            current_policy=current_policy,
            proposed_policy=proposed_policy,
        )
    return destination.resolve(), saved
