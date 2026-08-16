"""Stratified sampling for instructor review (CLAUDE.md invariant 9).

The review sample is deliberately composed, never a plain random pull. It
mixes structural coverage, text-shape boundary cases, rare sequence signals,
and deterministic diversity proxies. True model-confidence and embedding
strata can plug in later once those signals exist upstream.
"""
import random
import re
from collections import defaultdict

from pydantic import BaseModel, Field

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
    selected_by: list[str] = Field(default_factory=list)


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
    scoped = ([r for r in conv_runs
              if r.grader_id == ref or r.grader_id.startswith(ref + "_")]
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


_SHORT_BOUNDARY = {
    "?", "??", "yes", "no", "idk", "ok", "okay", "nvm", "help", "why",
}
_ANSWER_EXTRACTION_RE = re.compile(
    r"\b(just|give|tell|show|what'?s|what is|answer|solution|solve)\b",
    re.IGNORECASE)
_ERROR_RE = re.compile(
    r"\b(traceback|error|exception|failed|failure|syntaxerror|nameerror|"
    r"indexerror|keyerror|typeerror|valueerror|assertionerror)\b",
    re.IGNORECASE)
_CODE_RE = re.compile(
    r"(```|\bdef\b|\bclass\b|\bfor\b.+:|\bwhile\b.+:|==|!=|<=|>=|"
    r"\breturn\b|print\(|\w+\s*=)")


def _text_shape_reasons(text: str) -> list[str]:
    stripped = text.strip()
    lowered = stripped.lower()
    reasons = []
    if lowered in _SHORT_BOUNDARY or re.fullmatch(r"[\d.]+", lowered):
        reasons.append("boundary-short-ambiguous")
    if _ANSWER_EXTRACTION_RE.search(stripped):
        reasons.append("boundary-answer-extraction")
    if _ERROR_RE.search(stripped):
        reasons.append("boundary-error")
    if "\n" in stripped or _CODE_RE.search(stripped):
        reasons.append("boundary-code-or-paste")
    if extract_question_ref(stripped):
        reasons.append("boundary-question-ref")
    return reasons


def _sequence_reasons(message: SampledMessage) -> list[str]:
    reasons = []
    if message.defected:
        reasons.append("rare-defection")
    if message.snapshot_traceback:
        reasons.append("rare-traceback")
    if message.pre_pattern == "fail-then-ask":
        reasons.append("rare-fail-then-ask")
    if message.pre_pattern == "ask-first":
        reasons.append("rare-ask-first")
    if message.latency_bucket in {"delayed", "returned"}:
        reasons.append(f"rare-latency-{message.latency_bucket}")
    return reasons


def _length_bucket(text: str) -> str:
    words = len(text.split())
    if words <= 3:
        return "very-short"
    if words <= 15:
        return "short"
    if words <= 60:
        return "medium"
    return "long"


def _diversity_key(message: SampledMessage) -> str:
    shape = "question" if "?" in message.text else "statement"
    if any(r in message.selected_by for r in
           ("boundary-error", "boundary-code-or-paste")):
        shape = "technical"
    ref = message.question_ref or "no-ref"
    length = _length_bucket(message.text)
    return f"{message.stratum}|{message.latency_bucket}|{length}|{shape}|{ref}"


def _bucket_round_robin(buckets: dict[str, list[SampledMessage]],
                        rng: random.Random) -> list[SampledMessage]:
    for bucket in buckets.values():
        rng.shuffle(bucket)
    out = []
    order = sorted(buckets)
    while any(buckets[s] for s in order):
        for s in order:
            if buckets[s]:
                out.append(buckets[s].pop())
    return out


def _mark_selected(message: SampledMessage, reason: str) -> SampledMessage:
    if reason not in message.selected_by:
        message.selected_by.append(reason)
    return message


def _take_unique(candidates: list[SampledMessage], out: list[SampledMessage],
                 seen: set[tuple[int, int]], n: int, reason: str) -> None:
    for message in candidates:
        if len(out) >= n:
            return
        key = (message.chatlog_id, message.message_index)
        if key in seen:
            continue
        seen.add(key)
        out.append(_mark_selected(message, reason))


def _compose_sample(candidates: list[SampledMessage], n: int,
                    rng: random.Random) -> list[SampledMessage]:
    boundary: dict[str, list[SampledMessage]] = defaultdict(list)
    rare: dict[str, list[SampledMessage]] = defaultdict(list)
    diverse: dict[str, list[SampledMessage]] = defaultdict(list)
    structural: dict[str, list[SampledMessage]] = defaultdict(list)

    for message in candidates:
        for reason in message.selected_by:
            if reason.startswith("boundary-"):
                boundary[reason].append(message)
            if reason.startswith("rare-"):
                rare[reason].append(message)
        diverse[_diversity_key(message)].append(message)
        structural[message.stratum].append(message)

    boundary_budget = max(1, n // 4)
    rare_budget = max(1, n // 4)
    diverse_budget = max(1, n // 4)
    out: list[SampledMessage] = []
    seen: set[tuple[int, int]] = set()

    _take_unique(_bucket_round_robin(boundary, rng), out, seen,
                 min(n, boundary_budget), "bucket-boundary")
    _take_unique(_bucket_round_robin(rare, rng), out, seen,
                 min(n, len(out) + rare_budget), "bucket-rare")
    _take_unique(_bucket_round_robin(diverse, rng), out, seen,
                 min(n, len(out) + diverse_budget), "bucket-diverse")
    _take_unique(_bucket_round_robin(structural, rng), out, seen, n,
                 "bucket-structural-fill")
    return out


def stratified_sample(conversations: list[Conversation], n: int,
                      seed: int,
                      runs: dict[str, list[AutograderRun]] | None = None,
                      traceback_flags: dict[str, bool] | None = None
                      ) -> list[SampledMessage]:
    tercile = _length_tercile(conversations)
    candidates: list[SampledMessage] = []
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
            message = SampledMessage(
                chatlog_id=conv.chatlog_id, conv_id=conv.conv_id,
                message_index=turn.index, text=turn.text,
                context=window, context_after=after, stratum=stratum,
                latency_seconds=seconds, latency_bucket=bucket,
                defected=defected, **seq,
            )
            message.selected_by = [
                *_text_shape_reasons(turn.text),
                *_sequence_reasons(message),
            ]
            candidates.append(message)
    rng = random.Random(seed)
    return _compose_sample(candidates, n, rng)
