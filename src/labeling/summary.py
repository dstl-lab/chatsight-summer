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


def _weekly(conversations, labeled, label_names):
    earliest = _earliest_start(conversations)
    week_of = {c.chatlog_id: conversation_week(c, earliest)
               for c in conversations}
    undated = sum(1 for c in conversations if c.started_at is None)
    msgs_by_week: dict[int, list[MessageLabels]] = {}
    for r in labeled:
        w = week_of.get(r.chatlog_id)
        if w is not None:
            msgs_by_week.setdefault(w, []).append(r)
    weeks = sorted(msgs_by_week)
    labels_with_data = [n for n in label_names
                        if any(r.labels.get(n) for r in labeled)]
    # Omission rule is "fewer than 3 POPULATED weeks" by choice — stricter
    # than the memo's span wording (weeks with zero labeled messages, e.g. a
    # gap in `weeks`, don't count toward the 3, since there's nothing to plot
    # or compare across the gap).
    if len(weeks) < 3 or len(labels_with_data) < 2:
        return None
    series = {}
    for name in label_names:
        series[name] = [
            sum(1 for r in msgs_by_week[w] if r.labels.get(name))
            / len(msgs_by_week[w])
            for w in weeks
        ]
    return {"weeks": weeks, "series": series, "undated": undated}


def _top_pairs(labeled, limit=3):
    counts: Counter = Counter()
    for r in labeled:
        on = sorted(k for k, v in r.labels.items() if v)
        counts.update(combinations(on, 2))
    return [{"a": a, "b": b, "share": c / len(labeled)}
            for (a, b), c in counts.most_common(limit) if c > 0]


def _coverage(conversations, labeled, seed):
    """Coverage summary, including the abstention pile: messages where the
    drafting model set `no_label_fits` (schema has no construct for this
    message). This pile feeds the instructor, not the schema — it is
    evidence for a possible future schema tweak, not itself a label
    (2026-08-06 memo)."""
    labeled_count = Counter()
    for r in labeled:
        if any(r.labels.values()):
            labeled_count[r.chatlog_id] += 1
    bins = [0] * 16
    zero_convs = []
    for c in conversations:
        n = labeled_count.get(c.chatlog_id, 0)
        bins[min(n, 15)] += 1
        if n == 0:
            zero_convs.append(c)
    rng = random.Random(seed)
    rng.shuffle(zero_convs)
    zero_examples = [{"text": c.student_turns[0].text, "conv": c.chatlog_id}
                     for c in zero_convs[:5] if c.student_turns]

    lookup = _message_lookup(conversations)
    abstained = [r for r in labeled if r.no_label_fits]
    # Separate Random instance so the zero_examples sequence above is
    # unaffected by this shuffle for a given seed.
    abstain_rng = random.Random(seed)
    abstain_rng.shuffle(abstained)
    abstained_examples = []
    for r in abstained[:5]:
        hit = lookup.get((r.chatlog_id, r.message_index))
        if hit:
            abstained_examples.append({"text": hit[0], "conv": r.chatlog_id,
                                       "note": r.coverage_note})

    return {"bins": bins, "zero_conversations": len(zero_convs),
            "zero_examples": zero_examples,
            "abstained": len(abstained),
            "abstained_examples": abstained_examples}


def _largest_jump(weekly):
    """Only ADJACENT weeks (weeks[i] - weeks[i-1] == 1) are eligible: `weeks`
    is sparse (a course week with no labeled messages is simply absent), so a
    raw index-to-index delta across a gap would compare non-adjacent weeks
    and misrepresent the "week-over-week" claim in the trend annotation."""
    if weekly is None:
        return None
    weeks = weekly["weeks"]
    best = None
    for name, values in weekly["series"].items():
        for i in range(1, len(values)):
            if weeks[i] - weeks[i - 1] != 1:
                continue
            delta = values[i] - values[i - 1]
            if best is None or abs(delta) > abs(best[2]):
                best = (name, weeks[i], delta)
    if best is None:
        return None
    return {"label": best[0], "week": best[1], "delta": round(best[2], 4)}


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
    label_names = [l.name for l in schema.labels]
    weekly = _weekly(conversations, labeled, label_names)
    return {
        "totals": totals,
        "per_label": per_label,
        "weekly": weekly,
        "top_pairs": _top_pairs(labeled),
        "coverage": _coverage(conversations, labeled, seed),
        "largest_jump": _largest_jump(weekly),
    }
