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
from src.ingest.sequences import AutograderRun
from src.labeling.qref import extract_question_ref

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
    mode: str = ""
    defected: bool = False
    question_ref: str = ""
    pre_pattern: str = ""
    last_run_minutes: float | None = None
    last_run_grader: str = ""
    last_run_success: bool | None = None
    snapshot_traceback: bool = False
    seq_granularity: str = ""


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


def _sequence_fields(conv: Conversation, turn: Turn,
                     runs: dict[str, list[AutograderRun]] | None,
                     traceback_flags: dict[str, bool] | None) -> dict:
    """Mechanical per-message sequence facts (2026-08-09 spec). Facts,
    not LLM judgments; absent data leaves defaults ("", None, False)."""
    if runs is None:
        return {}
    fields: dict = {"snapshot_traceback":
                    bool((traceback_flags or {}).get(conv.conv_id))}
    fields["mode"] = turn.mode
    ref = extract_question_ref(turn.text)
    fields["question_ref"] = ref
    conv_runs = runs.get(conv.conv_id, [])
    scoped = ([r for r in conv_runs if r.grader_id.startswith(ref)]
              if ref else conv_runs)
    fields["seq_granularity"] = ("question" if ref and scoped
                                 else "notebook")
    if turn.at is None:
        # Timing unknown, not "no prior run" — leave pre_pattern/last_run_*
        # at their defaults ("" / None) rather than asserting ask-first.
        return fields
    pool = scoped if ref and scoped else conv_runs
    prior = [r for r in pool if r.at <= turn.at]
    if not prior:
        fields["pre_pattern"] = "ask-first"
    else:
        last = prior[-1]
        fields["pre_pattern"] = ("pass-then-ask" if last.success
                                 else "fail-then-ask")
        fields["last_run_minutes"] = (turn.at - last.at).total_seconds() / 60
        fields["last_run_grader"] = last.grader_id
        fields["last_run_success"] = last.success
    return fields


def _defection_indexes(conv: Conversation) -> set[int]:
    """Turn indexes where the student first switches tutor->chatgpt."""
    out, prev = set(), ""
    for t in conv.student_turns:
        if t.mode == "chatgpt" and prev == "tutor":
            out.add(t.index)
        if t.mode:
            prev = t.mode
    return out


def stratified_sample(conversations: list[Conversation], n: int,
                      seed: int,
                      runs: dict[str, list[AutograderRun]] | None = None,
                      traceback_flags: dict[str, bool] | None = None
                      ) -> list[SampledMessage]:
    tercile = _length_tercile(conversations)
    strata: dict[str, list[SampledMessage]] = defaultdict(list)
    for conv in conversations:
        n_student = len(conv.student_turns)
        defection_idx = _defection_indexes(conv) if runs is not None else set()
        for turn in conv.student_turns:
            position = "early" if turn.student_index < n_student / 2 else "late"
            base_stratum = f"{tercile[conv.conv_id]}/{position}"
            window, after = _context(conv, turn.index)
            seconds, bucket = _latency(conv, turn.index)
            seq = _sequence_fields(conv, turn, runs, traceback_flags)
            defected = runs is not None and turn.index in defection_idx
            suffix = ""
            if seq.get("pre_pattern") == "fail-then-ask":
                suffix = "/seq-fail"
            elif seq.get("pre_pattern") == "ask-first":
                suffix = "/seq-askfirst"
            elif defected:
                suffix = "/seq-defect"
            stratum = base_stratum + suffix
            strata[stratum].append(SampledMessage(
                chatlog_id=conv.chatlog_id, conv_id=conv.conv_id,
                message_index=turn.index, text=turn.text,
                context=window, context_after=after, stratum=stratum,
                latency_seconds=seconds, latency_bucket=bucket,
                defected=defected, **seq,
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
