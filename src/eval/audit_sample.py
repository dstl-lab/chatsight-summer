"""Blind-audit sample composition (invariant 9: never a plain random pull).
Strata, in priority order: (1) every abstained message — the abstention
call is itself a classifier and abstentions are where ambiguous items
silently vanish (research report §5.3); (2) high-entropy messages when
vote-entropy routing ran (CoAnnotating); (3) random fill from the rest,
seeded. Anchored keys (messages the instructor saw with model labels —
review samples, prior audits) are excluded up front (invariant 8)."""
import random

from src.labeling.draft import MessageLabels

Key = tuple[int, int]


def build_audit_sample(rows: list[MessageLabels], n: int, seed: int,
                       exclude: set[Key] = frozenset(),
                       entropies: dict[Key, dict] | None = None,
                       max_abstained_fraction: float = 0.4) -> dict:
    """Returns {"keys": [...], "strata": {key: stratum}} with n keys.
    Abstained messages are capped at max_abstained_fraction of the sample
    so the audit never becomes purely an abstention review."""
    pool = {(r.chatlog_id, r.message_index): r for r in rows
            if (r.chatlog_id, r.message_index) not in exclude}
    rng = random.Random(seed)

    strata: dict[Key, str] = {}
    abstained = sorted(k for k, r in pool.items() if r.no_label_fits)
    rng.shuffle(abstained)
    for k in abstained[:max(1, int(n * max_abstained_fraction))
                       if abstained else 0]:
        if len(strata) < n:
            strata[k] = "abstained"

    if entropies:
        ranked = sorted(((k, e) for k, e in entropies.items()
                         if k in pool and k not in strata),
                        key=lambda kv: (-kv[1]["max_entropy"], kv[0]))
        for k, e in ranked:
            if len(strata) >= n * 0.8:      # leave room for random fill
                break
            if e["max_entropy"] > 0:
                strata[k] = "high-entropy"

    rest = sorted(k for k in pool if k not in strata)
    rng.shuffle(rest)
    for k in rest:
        if len(strata) >= n:
            break
        strata[k] = "random"
    return {"keys": sorted(strata), "strata": strata}


def build_label_audit_samples(rows: list[MessageLabels], labels: list[str],
                              n_per_label: int, seed: int,
                              exclude: set[Key] = frozenset(),
                              pos_fraction: float = 0.5) -> dict:
    """Per-label audit samples (verification-budget design): for each label,
    pos_fraction of the budget goes to model-POSITIVE messages (precision
    evidence; 0.5 default — raise it for support-targeted rounds where the
    admission threshold needs positive support >= 25), the rest to
    model-negatives with abstained messages first (recall probes —
    abstentions are where missed positives hide), then random negatives.
    When a label has fewer positives than its share, negatives fill the
    remainder. Strata are for SCORING ONLY and must never reach the
    annotator's page (showing 'model-positive' would anchor, invariant 8);
    each label's key list is independently shuffled so order leaks nothing.
    Returns {label: {"keys": [...], "strata": {key: stratum}}}."""
    if not 0 < pos_fraction < 1:
        raise ValueError(f"pos_fraction must be in (0, 1), got "
                         f"{pos_fraction}: an all-positive audit measures "
                         "no recall and an all-negative one no precision")
    pool = {(r.chatlog_id, r.message_index): r for r in rows
            if (r.chatlog_id, r.message_index) not in exclude}
    out = {}
    for label in labels:
        rng = random.Random(f"{seed}:{label}")
        strata: dict[Key, str] = {}
        pos = sorted(k for k, r in pool.items() if r.labels.get(label))
        rng.shuffle(pos)
        for k in pos[:max(1, int(n_per_label * pos_fraction))
                     if pos else 0]:
            strata[k] = "model-positive"
        neg_abst = sorted(k for k, r in pool.items()
                          if not r.labels.get(label) and r.no_label_fits
                          and k not in strata)
        neg_rest = sorted(k for k, r in pool.items()
                          if not r.labels.get(label) and not r.no_label_fits
                          and k not in strata)
        rng.shuffle(neg_abst)
        rng.shuffle(neg_rest)
        for k in neg_abst + neg_rest:
            if len(strata) >= n_per_label:
                break
            strata[k] = ("abstained-negative" if k in neg_abst
                         else "random-negative")
        keys = list(strata)
        rng.shuffle(keys)              # annotator must not infer strata
        out[label] = {"keys": keys, "strata": strata}
    return out
