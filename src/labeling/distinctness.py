"""Post-run schema-distinctness report (2026-08-07): labels that co-fire
heavily are one construct wearing two names — the report makes rider labels
(a label that fires whenever any question-shaped label fires) visible after
every run, the way the coverage report makes abstention visible. Pure
computation over MessageLabels rows; no API calls, no snapshot mutation."""
import itertools
from pathlib import Path

from src.labeling.draft import MessageLabels

# A pair at or above this Jaccard is reported; 0.4 chosen so the known-bad
# case (Confusion x Debugging Request, J=0.71 on the 2026-08-07 smoke
# snapshot) is loud while ordinary correlated-but-distinct labels stay quiet.
OVERLAP_JACCARD = 0.4


def _rationale_overlap(rows: list[MessageLabels], a: str, b: str) -> float:
    sims = []
    for r in rows:
        if r.labels.get(a) and r.labels.get(b):
            wa = set(r.rationales.get(a, "").lower().split())
            wb = set(r.rationales.get(b, "").lower().split())
            sims.append(len(wa & wb) / max(1, len(wa | wb)))
    return sum(sims) / len(sims) if sims else 0.0


def overlapping_pairs(rows: list[MessageLabels]
                      ) -> list[tuple[str, str, float, int, float]]:
    """(label_a, label_b, jaccard, co_fire_count, rationale_overlap) for
    every pair at/above OVERLAP_JACCARD, highest jaccard first."""
    names = sorted({k for r in rows for k in r.labels})
    out = []
    for a, b in itertools.combinations(names, 2):
        both = sum(1 for r in rows
                   if r.labels.get(a) and r.labels.get(b))
        either = sum(1 for r in rows
                     if r.labels.get(a) or r.labels.get(b))
        j = both / either if either else 0.0
        if j >= OVERLAP_JACCARD:
            out.append((a, b, j, both, _rationale_overlap(rows, a, b)))
    return sorted(out, key=lambda t: -t[2])


def distinctness_report(rows: list[MessageLabels]) -> str:
    if not rows:
        return "Distinctness: no labeled rows."
    names = sorted({k for r in rows for k in r.labels},
                   key=lambda n_: -sum(1 for r in rows if r.labels.get(n_)))
    lines = [f"Distinctness ({len(rows)} rows, {len(names)} labels):"]
    for n_ in names:
        c = sum(1 for r in rows if r.labels.get(n_))
        lines.append(f"  {n_:<34}{c:>4} ({c / len(rows):.0%})")
    pairs = overlapping_pairs(rows)
    if pairs:
        lines.append(f"  OVERLAPPING PAIRS (Jaccard >= {OVERLAP_JACCARD} — "
                     "candidates for merge, tightening, or retirement):")
        for a, b, j, both, rat in pairs:
            lines.append(f"    {a} x {b}: J={j:.2f} (co-fire {both}), "
                         f"rationale overlap {rat:.2f}")
    else:
        lines.append("  no overlapping pairs — labels are behaviorally "
                     "distinct on this corpus")
    return "\n".join(lines)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="Distinctness report for a snapshot")
    parser.add_argument("snapshot_dir")
    args = parser.parse_args()
    rows = [MessageLabels.model_validate_json(l)
            for l in (Path(args.snapshot_dir) / "labels.jsonl").open()]
    print(distinctness_report(rows))


if __name__ == "__main__":
    main()
