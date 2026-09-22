"""Discover eligible starts and freeze one offline tutor-policy comparison."""
from pathlib import Path

from src.agents import chat_policy_pair, notebook_student as store


PACKAGED_POLICY_COMMIT = "d899879c3e7537b021d16bb901da341945606891"
PACKAGED_POLICY_URL = (
    "https://github.com/dstl-lab/jupyterlab-ai-tutor/blob/"
    + PACKAGED_POLICY_COMMIT
    + "/jupyterlab_ai_tutor_backend/config/default.yaml"
)
DEFAULT_CURRENT_POLICY = """Use the DSC 10 tutor's Socratic teaching approach:

- First understand what the student is trying to accomplish and what they have tried.
- Ask clarifying questions to assess the student's understanding.
- Give scaffolded hints, starting conceptually and becoming more specific only when needed.
- Prioritize why an approach works instead of immediately giving a complete solution.
- Help students interpret errors and identify the responsible line before explaining it.
- Encourage readable code, incremental testing, and checking data types and shapes.
- Use only evidence visible in the conversation; do not claim to inspect unavailable notebook work.
- Be encouraging, concise, and student-friendly.
- Do not provide complete solutions immediately or assume untaught knowledge.
- Ask a relevant follow-up question that supports independent problem solving.
"""


def sources(root):
    """Return verified direct-child source sessions without changing them."""
    root = Path(root)
    found = {}
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.is_symlink() or not (path / "session.json").is_file():
            continue
        try:
            chat_policy_pair._source(path)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        found[path.name] = path.resolve()
    return found


def freeze(destination, *, source, current_policy, proposed_policy):
    """Create a fixed one-decision pair; this function never dispatches a provider."""
    policies = {"a": current_policy, "b": proposed_policy}
    if any(not isinstance(value, str) or not value.strip() for value in policies.values()):
        raise ValueError("Enter both the confirmed current policy and the proposed policy.")
    if current_policy.strip() == proposed_policy.strip():
        raise ValueError("The proposed policy must differ from the current policy.")
    return chat_policy_pair.create(
        destination, source=source, policies=policies, max_new_decisions=1
    )


def reopen(destination):
    """Read a frozen setup without sending or modifying either condition."""
    return chat_policy_pair.show(destination)


def run_both(destination, *, send=False, generate_tutor=None, generate_student=None):
    """Run each untouched condition once; completed or failed conditions are never resent."""
    if send is not True:
        raise ValueError("Running the comparison requires explicit sending permission.")
    destination = Path(destination)
    for name in ("a", "b"):
        saved = reopen(destination)
        condition = saved["conditions"][name]
        snapshot = condition["snapshot"]
        if condition["error"] or snapshot is None:
            continue
        if not (snapshot["status"] == "awaiting-tutor"
                and snapshot["decisions_remaining"] > 0):
            continue
        try:
            chat_policy_pair.respond(
                destination, name, binding=snapshot["binding"], send=True,
                generate_tutor=generate_tutor, generate_student=generate_student,
            )
        except Exception:
            # Continue only if an actual saved failure explains this exception.
            receipt = chat_policy_pair._comparison(destination)
            if chat_policy_pair._condition_lifecycle(destination, receipt, name) not in ('failed', 'incomplete'):
                raise
    return reopen(destination)


def runs(workspace):
    """Return verified numbered comparisons in creation order."""
    workspace = Path(workspace)
    if not workspace.exists():
        return {}
    if not workspace.is_dir() or workspace.is_symlink():
        raise ValueError("The policy workspace must be a local directory.")
    found = {}
    for path in sorted(workspace.iterdir()):
        if not path.is_dir() or path.is_symlink():
            continue
        name = path.name
        if not (name.startswith("run-") and len(name) == 8 and name[4:].isdigit()):
            continue
        try:
            reopen(path)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        found[name] = path.resolve()
    return found


def freeze_next(workspace, *, source, current_policy, proposed_policy):
    """Freeze the next numbered run while refusing an exact policy/source reroll."""
    workspace, source = Path(workspace), Path(source)
    workspace.mkdir(parents=True, exist_ok=True)
    if workspace.is_symlink() or not workspace.is_dir():
        raise ValueError("The policy workspace must be a local directory.")
    source_manifest, _, _ = chat_policy_pair._source(source)
    source_sha256 = store.digest(source_manifest)
    with store._locked(workspace):
        existing = runs(workspace)
        for path in existing.values():
            plan = store._read(path / "comparison.json")["plan"]
            if (plan["source"]["session_sha256"] == source_sha256
                    and plan["policies"] == {"a": current_policy, "b": proposed_policy}):
                raise ValueError(
                    f"This exact scenario and policy pair already exists as {path.name}."
                )
        number = max((int(name[4:]) for name in existing), default=0) + 1
        destination = workspace / f"run-{number:04d}"
        saved = freeze(
            destination, source=source,
            current_policy=current_policy, proposed_policy=proposed_policy,
        )
    return destination.resolve(), saved
