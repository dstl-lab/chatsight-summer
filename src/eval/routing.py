"""Entropy-routed audit allocation (CoAnnotating, EMNLP 2023,
arXiv:2310.15638): sample k classifier votes at temperature > 0, compute
per-message vote entropy, and route high-entropy messages into the blind
audit — +21% over random allocation at matched cost in the source study.
Verbalized confidence is never used for routing (systematically
miscalibrated, arXiv:2605.11954)."""
import math
from collections import defaultdict

from src.labeling.draft import MessageLabels

VOTE_K = 5
VOTE_TEMPERATURE = 0.7


def _binary_entropy(p: float) -> float:
    if p <= 0 or p >= 1:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def vote_entropy(vote_runs: list[list[MessageLabels]]
                 ) -> dict[tuple[int, int], dict]:
    """vote_runs: k independent labeling passes over the same messages.
    Returns per-message {mean_entropy, max_entropy, per_label} where each
    label's entropy is the binary entropy of its yes-vote fraction."""
    votes: dict[tuple[int, int], dict[str, list[bool]]] = defaultdict(
        lambda: defaultdict(list))
    for run in vote_runs:
        for r in run:
            for name, v in r.labels.items():
                votes[(r.chatlog_id, r.message_index)][name].append(bool(v))
    out = {}
    for key, by_label in votes.items():
        ent = {name: _binary_entropy(sum(vs) / len(vs))
               for name, vs in by_label.items()}
        out[key] = {"per_label": ent,
                    "mean_entropy": sum(ent.values()) / len(ent),
                    "max_entropy": max(ent.values())}
    return out


def route_audit(entropies: dict[tuple[int, int], dict], n: int,
                by: str = "max_entropy") -> list[tuple[int, int]]:
    """Top-n message keys by entropy — the audit sample's uncertainty
    stratum. Ties broken by key for determinism."""
    return [k for k, _ in sorted(entropies.items(),
                                 key=lambda kv: (-kv[1][by], kv[0]))[:n]]
