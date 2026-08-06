"""First-look descriptive summary of a mass-label run (2026-08-05 done-screen
memo). Pure functions over in-memory session data — no DB, no snapshot reads,
nothing written to disk. Every number here is a drafted-label count: the UI
must present them as descriptive only (invariants 5/8)."""
import random
from collections import Counter
from itertools import combinations

from src.ingest.rawlog import Conversation
from src.labeling.draft import MessageLabels


def _message_lookup(conversations: list[Conversation]
                    ) -> dict[tuple[int, int], tuple[str, Conversation]]:
    out: dict[tuple[int, int], tuple[str, Conversation]] = {}
    for conv in conversations:
        for turn in conv.student_turns:
            out[(conv.chatlog_id, turn.index)] = (turn.text, conv)
    return out


def _earliest_start(conversations: list[Conversation]):
    dates = [c.started_at for c in conversations if c.started_at is not None]
    return min(dates) if dates else None


def conversation_week(conv: Conversation, earliest) -> int | None:
    if conv.started_at is None or earliest is None:
        return None
    return (conv.started_at - earliest).days // 7


def _example_dict(text: str, conv: Conversation, rationale: str,
                  earliest) -> dict:
    return {"text": text, "rationale": rationale, "conv": conv.chatlog_id,
            "week": conversation_week(conv, earliest)}


def sample_examples(conversations: list[Conversation],
                    labeled: list[MessageLabels], label: str,
                    n: int, seed: int) -> list[dict]:
    """Seeded-random sample of a label's positives — deliberately never
    top-N/most-confident (typical evidence, not cherry-picked)."""
    lookup = _message_lookup(conversations)
    earliest = _earliest_start(conversations)
    positives = [r for r in labeled if r.labels.get(label)]
    rng = random.Random(seed)
    rng.shuffle(positives)
    out = []
    for r in positives[:n]:
        hit = lookup.get((r.chatlog_id, r.message_index))
        if hit is None:
            continue
        text, conv = hit
        out.append(_example_dict(text, conv, r.rationales.get(label, ""),
                                 earliest))
    return out


def compute_summary(conversations: list[Conversation],
                    labeled: list[MessageLabels], schema,
                    seed: int) -> dict:
    with_label = [r for r in labeled if any(r.labels.values())]
    applications = sum(sum(r.labels.values()) for r in labeled)
    totals = {
        "messages": len(labeled),
        "conversations": len(conversations),
        "with_label": len(with_label),
        "labels_per_labeled": (round(applications / len(with_label), 1)
                               if with_label else 0.0),
    }
    per_label = []
    for i, l in enumerate(schema.labels):
        count = sum(1 for r in labeled if r.labels.get(l.name))
        examples = sample_examples(conversations, labeled, l.name,
                                   n=1, seed=seed + i)
        per_label.append({
            "name": l.name,
            "count": count,
            "share": (count / len(labeled)) if labeled else 0.0,
            "example": examples[0] if examples else None,
        })
    return {
        "totals": totals,
        "per_label": per_label,
        "weekly": None,        # Task 2
        "top_pairs": [],       # Task 2
        "coverage": None,      # Task 2
        "largest_jump": None,  # Task 2
    }
