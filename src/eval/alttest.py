"""Alt-test (Calderon, Reichart & Dror, ACL 2025, arXiv:2501.10970): can the
LLM annotator statistically replace a human annotator on this task? For each
human annotator j, compare the LLM's instance-level agreement with the
OTHER annotators against annotator j's agreement with them; the LLM "wins"
an annotator when its advantage probability exceeds 0.5 - epsilon. Passing
means the LLM is at least as aligned with the annotator pool as a typical
human is. Requires >= 2 annotators — with one, there is no pool to agree
with, so the test is undefined (we surface that rather than fake it)."""
from src.eval.validation import AuditRow
from src.labeling.draft import MessageLabels

# Calderon et al.'s recommended cost-benefit slack: the LLM may be up to
# epsilon worse than a human annotator and still "pass" (their paper's
# default 0.1 reflects annotation cost asymmetry).
EPSILON = 0.1


def _agreement(a: dict[str, bool], b: dict[str, bool],
               names: list[str]) -> float:
    return sum(bool(a.get(n)) == bool(b.get(n)) for n in names) / len(names)


def alt_test(annotators: list[list[AuditRow]], model: list[MessageLabels],
             epsilon: float = EPSILON) -> dict:
    """annotators: one blind-audit row list per human, same keys. Returns
    per-annotator advantage probabilities and the pass verdict (LLM must
    win a majority of annotators, Calderon's decision rule)."""
    if len(annotators) < 2:
        raise ValueError(
            "alt-test needs >= 2 independent annotators; with one there is "
            "no annotator pool to measure alignment against (run the "
            "second blind audit first)")
    model_by_key = {(r.chatlog_id, r.message_index): r.labels for r in model}
    by_ann = [{r.key: r.labels for r in rows} for rows in annotators]
    # The audit is per-label sampled: each key carries judgments for only the
    # labels whose passes drew it. Score agreement over the labels every
    # annotator actually judged on that key — scoring the full schema would
    # let the humans' unjudged-default-False slots agree trivially while the
    # model is graded on labels nobody audited.
    judged = {key: sorted(set.intersection(*(set(m[key]) for m in by_ann)))
              for key in set.intersection(*(set(m) for m in by_ann))}
    keys = {k for k, names in judged.items() if names} & set(model_by_key)
    if not keys:
        raise ValueError("no commonly judged audited keys across annotators "
                         "+ model")

    wins = []
    per_annotator = []
    for j, ann_j in enumerate(by_ann):
        others = [m for i, m in enumerate(by_ann) if i != j]
        advantage = 0
        for key in keys:
            pool = [o[key] for o in others]
            llm_score = sum(_agreement(model_by_key[key], p, judged[key])
                            for p in pool) / len(pool)
            human_score = sum(_agreement(ann_j[key], p, judged[key])
                              for p in pool) / len(pool)
            advantage += (llm_score >= human_score)
        rho = advantage / len(keys)
        won = rho >= 0.5 - epsilon
        per_annotator.append({"annotator": j, "advantage_prob": rho,
                              "wins": won})
        wins.append(won)
    return {"n_items": len(keys), "epsilon": epsilon,
            "per_annotator": per_annotator,
            "passes": sum(wins) > len(wins) / 2}
