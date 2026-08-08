"""Stratified sampling for instructor review (CLAUDE.md invariant 9: never a
plain random pull).

v0 strata are structural only: conversation-length tercile x student-turn
position (early/late). Upgrade path: once a first labeled pass exists, replace
with model-uncertainty and embedding-diversity strata so boundary and rare
cases surface."""
import random
from collections import defaultdict

from pydantic import BaseModel

from src.ingest.rawlog import Conversation, Turn

# Hash-visible context parameter (2026-08-06 memo): folded into
# classifier_hash via draft.classifier_hash. Changing it is a new classifier.
WINDOW_TURNS = 6

# Latency buckets (2026-08-07 context-timing spec): elapsed time from the
# nearest preceding tutor turn to the student turn. Mechanical, computed
# from event timestamps — never an LLM judgment. Thresholds are rendered
# into the classifier prompt, so they are hash-visible via
# draft.classifier_hash: changing them is a new classifier.
RAPID_S = 120
WORKING_S = 1800
DELAYED_S = 21600
LATENCY_BUCKETS = ("conversation-opening", "rapid", "working", "delayed",
                   "returned", "unknown")


def latency_bucket(seconds: float | None, *, opening: bool) -> str:
    if opening:
        return "conversation-opening"
    if seconds is None:
        return "unknown"
    if seconds < RAPID_S:
        return "rapid"
    if seconds < WORKING_S:
        return "working"
    if seconds < DELAYED_S:
        return "delayed"
    return "returned"


class SampledMessage(BaseModel):
    chatlog_id: int
    conv_id: str
    message_index: int
    text: str
    context: list[Turn]
    context_after: str | None
    stratum: str
    latency_seconds: float | None = None
    latency_bucket: str = "unknown"


def _length_tercile(conversations: list[Conversation]) -> dict[str, str]:
    sizes = sorted((len(c.student_turns), c.conv_id) for c in conversations)
    out: dict[str, str] = {}
    third = max(1, len(sizes) // 3)
    for rank, (_, conv_id) in enumerate(sizes):
        out[conv_id] = ("short", "mid", "long")[min(rank // third, 2)]
    return out


def _context(conv: Conversation, turn_index: int) -> tuple[list[Turn], str | None]:
    """Last WINDOW_TURNS turns before the target (both roles: 71% of student
    turns are <40 chars and deictic — one adjacent tutor message is not
    enough; 2026-08-06 memo), plus the next tutor reply."""
    window = conv.turns[max(0, turn_index - WINDOW_TURNS):turn_index]
    after = next((t.text for t in conv.turns[turn_index + 1:]
                  if t.role == "tutor"), None)
    return list(window), after


def _latency(conv: Conversation, turn_index: int) -> tuple[float | None, str]:
    """Seconds from the nearest preceding tutor turn to this turn, plus its
    bucket. No preceding tutor turn ⇒ conversation-opening; missing
    timestamps ⇒ unknown."""
    prior_tutor = next((t for t in reversed(conv.turns[:turn_index])
                        if t.role == "tutor"), None)
    if prior_tutor is None:
        return None, latency_bucket(None, opening=True)
    target = conv.turns[turn_index]
    if prior_tutor.at is None or target.at is None:
        return None, latency_bucket(None, opening=False)
    seconds = (target.at - prior_tutor.at).total_seconds()
    return seconds, latency_bucket(seconds, opening=False)


def stratified_sample(conversations: list[Conversation], n: int,
                      seed: int) -> list[SampledMessage]:
    tercile = _length_tercile(conversations)
    strata: dict[str, list[SampledMessage]] = defaultdict(list)
    for conv in conversations:
        n_student = len(conv.student_turns)
        for turn in conv.student_turns:
            position = "early" if turn.student_index < n_student / 2 else "late"
            stratum = f"{tercile[conv.conv_id]}/{position}"
            window, after = _context(conv, turn.index)
            seconds, bucket = _latency(conv, turn.index)
            strata[stratum].append(SampledMessage(
                chatlog_id=conv.chatlog_id, conv_id=conv.conv_id,
                message_index=turn.index, text=turn.text,
                context=window, context_after=after, stratum=stratum,
                latency_seconds=seconds, latency_bucket=bucket,
            ))
    rng = random.Random(seed)
    for bucket in strata.values():
        rng.shuffle(bucket)
    out: list[SampledMessage] = []
    order = sorted(strata)
    while len(out) < n and any(strata[s] for s in order):
        for s in order:
            if strata[s] and len(out) < n:
                out.append(strata[s].pop())
    return out
