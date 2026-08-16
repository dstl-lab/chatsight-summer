"""Build empirical transition matrices from label trajectories.

Transition matrices are downstream artifacts: they consume the text-free
trajectory output from src.trajectories.extract and preserve its provenance.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

END_STATE = "__END__"
NO_LABEL_STATE = "__NO_LABEL__"
NO_LABEL_FITS_STATE = "__NO_LABEL_FITS__"


def _ordered_labels(active_labels: list[str], label_names: list[str]) -> list[str]:
    order = {name: i for i, name in enumerate(label_names)}
    return sorted(active_labels, key=lambda name: (order.get(name, len(order)), name))


def state_id(step: dict, label_names: list[str]) -> str:
    parts = _ordered_labels(list(step.get("active_labels", [])), label_names)
    if step.get("no_label_fits"):
        parts.append(NO_LABEL_FITS_STATE)
    if not parts:
        return NO_LABEL_STATE
    return "+".join(parts)


def _state_record(state: str) -> dict:
    return {
        "active_labels": [] if state in {END_STATE, NO_LABEL_STATE}
        else [part for part in state.split("+") if part != NO_LABEL_FITS_STATE],
        "no_label_fits": NO_LABEL_FITS_STATE in state.split("+"),
        "terminal": state == END_STATE,
    }


def _sorted_nested_counts(counts: dict[str, Counter]) -> dict[str, dict[str, int]]:
    return {
        source: dict(sorted(targets.items()))
        for source, targets in sorted(counts.items())
    }


def _probabilities(counts: dict[str, Counter]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for source, targets in sorted(counts.items()):
        total = sum(targets.values())
        out[source] = {
            target: count / total
            for target, count in sorted(targets.items())
        }
    return out


def build_transition_matrix(trajectory_report: dict) -> dict:
    metadata = dict(trajectory_report.get("metadata", {}))
    label_names = list(metadata.get("label_names", []))
    trajectories = list(trajectory_report.get("trajectories", []))

    transition_counts: dict[str, Counter] = defaultdict(Counter)
    state_counts: Counter[str] = Counter()
    sequences = []

    for trajectory in trajectories:
        states = [
            state_id(step, label_names)
            for step in trajectory.get("steps", [])
        ]
        states_with_end = [*states, END_STATE]
        for state in states_with_end:
            state_counts[state] += 1
        for source, target in zip(states_with_end, states_with_end[1:]):
            transition_counts[source][target] += 1
        sequences.append({
            "conv_id": trajectory.get("conv_id"),
            "chatlog_id": trajectory.get("chatlog_id"),
            "states": states_with_end,
        })

    row_counts = {
        "trajectories": len(trajectories),
        "steps": sum(len(t.get("steps", [])) for t in trajectories),
        "states": len(state_counts),
        "transitions": sum(sum(c.values()) for c in transition_counts.values()),
    }
    states = {
        state: {**_state_record(state), "count": count}
        for state, count in sorted(state_counts.items())
    }
    return {
        "metadata": {
            **metadata,
            "artifact_type": "empirical_transition_matrix",
            "source_row_counts": metadata.get("row_counts", {}),
            "state_encoding": "active labels joined by '+', with reserved "
            f"{NO_LABEL_STATE}, {NO_LABEL_FITS_STATE}, and {END_STATE}",
            "terminal_state": END_STATE,
            "row_counts": row_counts,
        },
        "states": states,
        "transition_counts": _sorted_nested_counts(transition_counts),
        "transition_probabilities": _probabilities(transition_counts),
        "sequences": sequences,
    }


def load_trajectory_report(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def default_output_path(trajectory_path: Path) -> Path:
    trajectory_path = Path(trajectory_path)
    parent = trajectory_path.parent
    if parent.name:
        return parent / "transition-matrix.json"
    return Path("transition-matrix.json")


def write_transition_matrix(report: dict, out: Path) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build an empirical transition matrix from trajectories")
    parser.add_argument("trajectory_json")
    parser.add_argument("--out", default=None,
                        help="output JSON path; defaults next to trajectories")
    args = parser.parse_args()
    trajectory_path = Path(args.trajectory_json)
    report = build_transition_matrix(load_trajectory_report(trajectory_path))
    out = Path(args.out) if args.out else default_output_path(trajectory_path)
    write_transition_matrix(report, out)
    counts = report["metadata"]["row_counts"]
    print(f"wrote {out} ({counts['states']} states, "
          f"{counts['transitions']} transitions)")


if __name__ == "__main__":
    main()
