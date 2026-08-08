"""Phase 0: per-label validation of the classifier against a blind audit.
Reports per-label positive-class recall/precision, Cohen's kappa, and
Rogan-Gladen prevalence correction — never a single pooled accuracy
(invariant 2; research report 2026-08-07: accuracy alone hides
majority-class collapse on rare labels, and raw LLM prevalences mislead).
Pure computation; the blind audit itself is produced elsewhere and must
never have shown the auditor a model label (invariant 8)."""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from src.labeling.draft import MessageLabels
from src.labeling.schema import LabelSchema

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


def _load_audit_doc(path: Path) -> tuple[list[AuditRow], dict]:
    data = json.loads(Path(path).read_text())
    rows = data["rows"] if isinstance(data, dict) else data
    metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
    return ([AuditRow(key=tuple(r["key"]), labels=r["labels"],
                      no_label_fits=r.get("no_label_fits", False))
             for r in rows], metadata)


def _load_model(snapshot_dir: Path) -> list[MessageLabels]:
    return [MessageLabels.model_validate_json(l)
            for l in (snapshot_dir / "labels.jsonl").open()]


def _snapshot_metadata(snapshot_dir: Path) -> dict:
    schema = LabelSchema.model_validate_json(
        (snapshot_dir / "schema.json").read_text())
    manifest_path = snapshot_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) \
        if manifest_path.exists() else {}
    return {
        "snapshot_id": manifest.get("snapshot_id", snapshot_dir.name),
        "schema_version": manifest.get("schema_version", schema.version_id),
        "classifier_hash": manifest.get("classifier_hash"),
        "repo_sha": manifest.get("repo_sha"),
    }


def _verify_audit_metadata(snapshot_meta: dict, audit_meta: dict) -> None:
    """Reject audit files that declare a different snapshot/schema/hash.
    Legacy audit files without metadata can still be scored, but they are
    marked as unverified in the report."""
    if not audit_meta:
        return
    for field in ("snapshot_id", "schema_version"):
        if audit_meta.get(field) and audit_meta[field] != snapshot_meta[field]:
            raise ValueError(
                f"audit {field} {audit_meta[field]!r} does not match "
                f"snapshot {snapshot_meta[field]!r}")
    audit_hash = audit_meta.get("classifier_hash")
    snapshot_hash = snapshot_meta.get("classifier_hash")
    if audit_hash and snapshot_hash and audit_hash != snapshot_hash:
        raise ValueError(
            f"audit classifier_hash {audit_hash!r} does not match "
            f"snapshot {snapshot_hash!r}")


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
        if a.key not in by_key:
            raise ValueError(f"audit key {a.key!r} missing from model labels")
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


def _label_metrics(label: str, c: Confusion,
                   ceiling: float | None = None) -> dict:
    kk = kappa(c)
    return {
        "label": label,
        "tp": c.tp,
        "fp": c.fp,
        "fn": c.fn,
        "tn": c.tn,
        "n": c.n,
        "support": c.support,
        "precision": c.precision,
        "recall": c.recall,
        "specificity": c.specificity,
        "agreement": c.agreement,
        "kappa": kk,
        "ceiling": ceiling,
        "raw_prevalence": ((c.tp + c.fp) / c.n if c.n else None),
        "corrected_prevalence": corrected_prevalence(c),
        "chance_flag": kk is not None and kk < CHANCE_KAPPA,
    }


def build_validation_report(snapshot_dir: Path, audit_json: Path,
                            ceilings: dict[str, float] | None = None
                            ) -> dict:
    """Durable Phase 0 report: model labels vs one blind human audit.
    The report carries snapshot/schema/classifier provenance so numbers
    cannot become orphaned from the run that produced them."""
    snapshot_dir = Path(snapshot_dir)
    audit_json = Path(audit_json)
    snapshot_meta = _snapshot_metadata(snapshot_dir)
    audit, audit_meta = _load_audit_doc(audit_json)
    _verify_audit_metadata(snapshot_meta, audit_meta)

    keys = {a.key for a in audit}
    model = [r for r in _load_model(snapshot_dir)
             if (r.chatlog_id, r.message_index) in keys]
    names = sorted({k for a in audit for k in a.labels},
                   key=lambda n_: -confusion(audit, model, n_).support)
    metrics = [_label_metrics(n_, confusion(audit, model, n_),
                              (ceilings or {}).get(n_))
               for n_ in names]
    generated_at = datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z")
    return {
        "metadata": {
            **snapshot_meta,
            "snapshot_dir": str(snapshot_dir),
            "audit_json": str(audit_json),
            "audit_metadata_present": bool(audit_meta),
            "audit_metadata": audit_meta,
            "audited_messages": len(audit),
            "audited_labels": names,
            "generated_at": generated_at,
        },
        "labels": metrics,
    }


def validation_report_table(report: dict) -> str:
    """Human-readable view of `build_validation_report`."""
    m = report["metadata"]
    lines = [
        f"Snapshot: {m['snapshot_id']}",
        f"Schema version: {m['schema_version']}",
        f"Classifier hash: {m['classifier_hash'] or '—'}",
        f"Audit: {m['audit_json']}",
        f"Per-label validation (n={m['audited_messages']} blind-audited "
        "messages):",
        f"{'label':<34}{'P':>6}{'recall':>8}{'kappa':>7}"
        f"{'ceiling':>9}{'support':>9}{'raw prev':>10}"
        f"{'corrected prev':>16}",
    ]
    for row in report["labels"]:
        def fmt(v, pct=False):
            if v is None:
                return "—"
            return f"{v:.0%}" if pct else f"{v:.2f}"
        flag = "  ≈ chance — keep human-only" if row["chance_flag"] else ""
        lines.append(
            f"{row['label']:<34}{fmt(row['precision']):>6}"
            f"{fmt(row['recall']):>8}{fmt(row['kappa']):>7}"
            f"{fmt(row['ceiling']):>9}{row['support']:>9}"
            f"{fmt(row['raw_prevalence'], pct=True):>10}"
            f"{fmt(row['corrected_prevalence'], pct=True):>16}{flag}")
    lines.append("(recall/precision are positive-class; corrected prev = "
                 "Rogan-Gladen from this audit's confusion matrix)")
    return "\n".join(lines)


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


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="Per-label validation report: snapshot vs blind audit")
    parser.add_argument("snapshot_dir")
    parser.add_argument("audit_json")
    parser.add_argument("--out", default=None,
                        help="optional JSON report path")
    args = parser.parse_args()
    report = build_validation_report(Path(args.snapshot_dir),
                                     Path(args.audit_json))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
    print(validation_report_table(report))


if __name__ == "__main__":
    main()
