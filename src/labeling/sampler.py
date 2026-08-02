"""Stratified sampling for instructor review (CLAUDE.md invariant 9: never a
plain random pull).

v0 strata are structural only: conversation-length tercile x student-turn
position (early/late). Upgrade path: once a first labeled pass exists, replace
with model-uncertainty and embedding-diversity strata so boundary and rare
cases surface."""
import random
from collections import defaultdict

from pydantic import BaseModel

from src.ingest.rawlog import Conversation


class SampledMessage(BaseModel):
    chatlog_id: int
    conv_id: str
    message_index: int
    text: str
    context_before: str | None
    context_after: str | None
    stratum: str


def _length_tercile(conversations: list[Conversation]) -> dict[str, str]:
    sizes = sorted((len(c.student_turns), c.conv_id) for c in conversations)
    out: dict[str, str] = {}
    third = max(1, len(sizes) // 3)
    for rank, (_, conv_id) in enumerate(sizes):
        out[conv_id] = ("short", "mid", "long")[min(rank // third, 2)]
    return out


def _neighbors(conv: Conversation, turn_index: int) -> tuple[str | None, str | None]:
    before = next((t.text for t in reversed(conv.turns[:turn_index])
                   if t.role == "tutor"), None)
    after = next((t.text for t in conv.turns[turn_index + 1:]
                  if t.role == "tutor"), None)
    return before, after


def stratified_sample(conversations: list[Conversation], n: int,
                      seed: int) -> list[SampledMessage]:
    tercile = _length_tercile(conversations)
    strata: dict[str, list[SampledMessage]] = defaultdict(list)
    for conv in conversations:
        n_student = len(conv.student_turns)
        for turn in conv.student_turns:
            position = "early" if turn.student_index < n_student / 2 else "late"
            stratum = f"{tercile[conv.conv_id]}/{position}"
            before, after = _neighbors(conv, turn.index)
            strata[stratum].append(SampledMessage(
                chatlog_id=conv.chatlog_id, conv_id=conv.conv_id,
                message_index=turn.index, text=turn.text,
                context_before=before, context_after=after, stratum=stratum,
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
