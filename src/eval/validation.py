"""Phase 0: per-label validation of the classifier against a blind audit.
Reports per-label positive-class recall/precision, Cohen's kappa, and
Rogan-Gladen prevalence correction — never a single pooled accuracy
(invariant 2; research report 2026-08-07: accuracy alone hides
majority-class collapse on rare labels, and raw LLM prevalences mislead).
Pure computation; the blind audit itself is produced elsewhere and must
never have shown the auditor a model label (invariant 8)."""
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from src.labeling.draft import MessageLabels

# Kappa below which a label is flagged as "model ≈ chance" (LACA's move:
# per-code agreement identifies codes where the LLM is guessing; those stay
# human-only until criteria improve).
CHANCE_KAPPA = 0.2


class AuditRow(BaseModel):
    key: tuple[int, int]              # (chatlog_id, message_index)
    labels: dict[str, bool]
    no_label_fits: bool = False


def load_audit(path: Path) -> list[AuditRow]:
    data = json.loads(Path(path).read_text())
    rows = data["rows"] if isinstance(data, dict) else data
    return [AuditRow(key=tuple(r["key"]), labels=r["labels"],
                     no_label_fits=r.get("no_label_fits", False))
            for r in rows]


@dataclass
class Confusion:
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def n(self) -> int:
        return self.tp + self.fp + self.fn + self.tn

    @property
    def support(self) -> int:
        return self.tp + self.fn

    @property
    def precision(self) -> float | None:
        d = self.tp + self.fp
        return self.tp / d if d else None

    @property
    def recall(self) -> float | None:
        d = self.tp + self.fn
        return self.tp / d if d else None

    @property
    def specificity(self) -> float | None:
        d = self.tn + self.fp
        return self.tn / d if d else None

    @property
    def agreement(self) -> float:
        return (self.tp + self.tn) / self.n if self.n else 0.0


def confusion(audit: list[AuditRow], model: list[MessageLabels],
              label: str) -> Confusion:
    by_key = {(r.chatlog_id, r.message_index): r for r in model}
    tp = fp = fn = tn = 0
    for a in audit:
        if label not in a.labels:
            continue        # per-label sampled audit: label not audited here
        m = by_key[a.key]
        hv, mv = bool(a.labels.get(label)), bool(m.labels.get(label))
        tp += hv and mv
        fp += mv and not hv
        fn += hv and not mv
        tn += not hv and not mv
    return Confusion(tp, fp, fn, tn)


def kappa(c: Confusion) -> float | None:
    if not c.n:
        return None
    po = c.agreement
    p_model_yes = (c.tp + c.fp) / c.n
    p_human_yes = (c.tp + c.fn) / c.n
    pe = (p_model_yes * p_human_yes
          + (1 - p_model_yes) * (1 - p_human_yes))
    return None if pe == 1 else (po - pe) / (1 - pe)


def corrected_prevalence(c: Confusion) -> float | None:
    """Rogan-Gladen: true prevalence estimated from apparent (model)
    prevalence and the audit-derived sensitivity/specificity. None when the
    classifier is uninformative (sens + spec <= 1) — a corrected number
    from a chance-level classifier would be noise wearing a decimal."""
    sens, spec = c.recall, c.specificity
    if sens is None or spec is None or (sens + spec) <= 1:
        return None
    raw = (c.tp + c.fp) / c.n
    return min(1.0, max(0.0, (raw + spec - 1) / (sens + spec - 1)))


def validation_table(audit: list[AuditRow], model: list[MessageLabels],
                     ceilings: dict[str, float] | None = None) -> str:
    """Per-label table. `ceilings` maps label -> human-human agreement when
    a second annotator exists; '—' otherwise (invariant 2: a number without
    its ceiling is not reportable)."""
    names = sorted({k for a in audit for k in a.labels},
                   key=lambda n_: -confusion(audit, model, n_).support)
    lines = [f"Per-label validation (n={len(audit)} blind-audited "
             "messages):",
             f"{'label':<34}{'P':>6}{'recall':>8}{'kappa':>7}"
             f"{'ceiling':>9}{'support':>9}{'raw prev':>10}"
             f"{'corrected prev':>16}"]
    for n_ in names:
        c = confusion(audit, model, n_)
        k = kappa(c)
        cp = corrected_prevalence(c)
        ceiling = (ceilings or {}).get(n_)
        def fmt(v, pct=False):
            if v is None:
                return "—"
            return f"{v:.0%}" if pct else f"{v:.2f}"
        flag = "  ≈ chance — keep human-only" \
            if (k is not None and k < CHANCE_KAPPA) else ""
        lines.append(
            f"{n_:<34}{fmt(c.precision):>6}{fmt(c.recall):>8}"
            f"{fmt(k):>7}{fmt(ceiling):>9}{c.support:>9}"
            f"{fmt((c.tp + c.fp) / c.n if c.n else None, pct=True):>10}"
            f"{fmt(cp, pct=True):>16}{flag}")
    lines.append("(recall/precision are positive-class; corrected prev = "
                 "Rogan-Gladen from this audit's confusion matrix)")
    return "\n".join(lines)


def outcome_anchor(rows: list[MessageLabels], label: str,
                   expected_pattern: str = "fail-then-ask") -> dict:
    """Directional sanity check (2026-08-09 spec): a label like
    answer-extraction should concentrate in fail->ask conversations more
    than that pattern's base rate in the corpus. Violations FLAG the label
    for human audit — never auto-relabeled (invariant 1)."""
    positives = [r for r in rows if r.labels.get(label)]
    in_pattern = sum(1 for r in positives
                     if r.pre_pattern == expected_pattern)
    baseline = (sum(1 for r in rows if r.pre_pattern == expected_pattern)
                / len(rows)) if rows else 0.0
    concentration = in_pattern / len(positives) if positives else 0.0
    return {"label": label, "expected_pattern": expected_pattern,
            "in_pattern": in_pattern, "total_positives": len(positives),
            "concentration": concentration, "baseline": baseline}


def anchor_report(rows: list[MessageLabels],
                  anchors: dict[str, str]) -> str:
    """One line per (label, expected_pattern) anchor. FLAG marks labels
    whose positives concentrate below the pattern's corpus baseline — an
    audit candidate, never an auto-relabel (invariant 1)."""
    lines = ["== outcome anchors =="]
    for label, pattern in sorted(anchors.items()):
        a = outcome_anchor(rows, label, pattern)
        flag = " FLAG: below baseline — audit candidate" \
            if a["total_positives"] and a["concentration"] < a["baseline"] \
            else ""
        lines.append(
            f"  {label}: {a['in_pattern']}/{a['total_positives']} positives "
            f"in {pattern} ({a['concentration']:.0%} vs baseline "
            f"{a['baseline']:.0%}){flag}")
    return "\n".join(lines)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="Per-label validation table: snapshot vs blind audit")
    parser.add_argument("snapshot_dir")
    parser.add_argument("audit_json")
    args = parser.parse_args()
    model = [MessageLabels.model_validate_json(l)
             for l in (Path(args.snapshot_dir) / "labels.jsonl").open()]
    audit = load_audit(Path(args.audit_json))
    keys = {a.key for a in audit}
    model = [r for r in model if (r.chatlog_id, r.message_index) in keys]
    print(validation_table(audit, model))


if __name__ == "__main__":
    main()
