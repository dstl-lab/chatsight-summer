"""Draft classification of sampled messages against a schema version.
One Gemini call per (message, label) plus one per-message coverage call —
replacing the earlier all-labels-in-one-call design so a single label's
verdict can't be corrupted by cross-label prompt interference, and so
"no label fits" is judged on a dedicated channel that can never invent a
label name (Task 1 of the 2026-08-06 parallelize-labeling change).
classifier_hash is the provenance pin: same hash <=> same prompt templates
(single-label + coverage), schema version, model, course profile (both
field-level canonical() and rendered render_context() wording), and context
window (window size, the empty-window sentinel, and the per-turn line
format), per CLAUDE.md rule 2."""
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from pydantic import BaseModel

from src.ingest.rawlog import Turn
from src.ingest.sequences import BEFORE_MIN
from src.labeling.course import CourseProfile
from src.labeling import qref
from src.labeling.llm import Generate
from src.labeling.sampler import (DELAYED_S, RAPID_S, WINDOW_TURNS,
                                  WORKING_S, SampledMessage)
from src.labeling.schema import LabelDef, LabelSchema


# Wire format for Gemini structured output. Must stay free of dict[...] fields:
# pydantic renders those as JSON-schema additionalProperties, which the Gemini
# Developer API rejects. Lists of typed items only.
class SingleLabelVerdict(BaseModel):
    applies: bool
    rationale: str


# Surface form of the message (2026-08-06 prompt-redesign memo, Option B):
# a mechanical facet like message length, repo-authored rather than
# instructor-compiled, so it does not violate the top-down principle.
# List-valued because hybrids (pasted prompt + authored question in one
# message) are common. Hash-visible: folded into classifier_hash.
# Discourse position of the student message (2026-08-07 context-timing
# spec): judged by the coverage call with the turn window and the rendered
# latency line in view. Single-valued; hash-pinned.
MOVE_TAXONOMY = ("responds-to-tutor", "initiates-new-topic",
                 "continues-own-thread")

FORM_TAXONOMY = ("authored-question", "pasted-assignment", "pasted-error",
                 "code-share", "nudge", "answer-reply", "other")


class CoverageVerdict(BaseModel):
    # `forms` is declared first so the model commits to the surface reading
    # of the message before judging coverage.
    forms: list[str] = []
    # Course-concept facet (2026-08-07 memo): non-promoted concepts are
    # analytics-grade coverage data, not labels.
    concepts: list[str] = []
    # Discourse position, one MOVE_TAXONOMY value (context-timing spec).
    move: str = ""
    # Detection channel, not a labeling one (2026-08-06 memos): the model may
    # flag "no label fits" and describe the act, but never name a label.
    no_label_fits: bool
    note: str = ""


class MessageLabels(BaseModel):
    chatlog_id: int
    message_index: int
    labels: dict[str, bool]
    rationales: dict[str, str]
    no_label_fits: bool = False   # default: old snapshots still parse
    coverage_note: str = ""       # ditto
    forms: list[str] = []         # ditto
    concepts: list[str] = []      # ditto
    move: str = ""                # ditto
    latency_seconds: float | None = None   # mechanical, from event times
    latency_bucket: str = ""      # "" in old snapshots; else LATENCY_BUCKETS
    mode: str = ""                 # "" in old snapshots; else chatgpt/tutor
    defected: bool = False
    attempted: bool | None = None  # None: no sequence data for this message
    error_verified: bool | None = None  # None: ditto
    question_ref: str = ""
    pre_pattern: str = ""
    seq_granularity: str = ""


_SHARED_RULES = """\
Rules:
- Distinguish student-authored words from pasted material. A pasted \
assignment prompt or bare error output expresses no affect by itself; label \
it by what the student is using it to do.
- Very short messages inherit their meaning from the immediately preceding \
turns, including the student's own previous message.
- Judge the student's act in THIS message — what the student is doing at \
this point in the conversation — using the preceding turns to resolve short \
or deictic messages (a bare "?", a question number, a pasted error)."""

_SHARED_CONTEXT = """\
Conversation so far (most recent last; may be empty):
{context}

Time since the tutor's last message: {latency}

Autograder state when the student asked: {sequence}
Assistant mode: {mode}

STUDENT MESSAGE TO LABEL:
{text}

Tutor reply after (may be empty):
{context_after}"""

SINGLE_LABEL_PROMPT = f"""You judge ONE label against one student message \
from a student–AI tutor conversation.

Course context:
{{course_context}}

{_SHARED_RULES}
- If the label cannot be judged from this message even with context, answer \
false and say why in the rationale.

Label:
- {{label_name}}: {{label_description}} | applies when: {{positive_criteria}} \
| does NOT apply when: {{negative_criteria}}

{_SHARED_CONTEXT}

Does the label apply to the student message? Return applies (true/false) \
and a one-sentence rationale."""

COVERAGE_PROMPT = f"""You check label coverage for one student message from \
a student–AI tutor conversation.

Course context:
{{course_context}}

{_SHARED_RULES}

The label set:
{{labels}}

{_SHARED_CONTEXT}

First declare the message's surface form(s) in forms — every value that \
applies, from exactly this list: {{form_taxonomy}}. A message can be a \
hybrid (e.g. a pasted assignment prompt plus an authored question).

In move, give the message's discourse position — exactly one of: \
responds-to-tutor (engages what the tutor just said), initiates-new-topic \
(opens a new question or task regardless of how recently the tutor spoke), \
continues-own-thread (extends the student's own previous message). Use the \
elapsed-time line to disambiguate.

{{concept_section}}Then set no_label_fits=true only if this message shows a student act that NONE \
of the labels capture (a message can be partially captured: some act \
labeled, another not — that still counts). If true, describe the uncaptured \
act in one sentence in note; do not propose or name any label. Otherwise \
no_label_fits=false and note empty."""


def _coverage_labels_block(schema: LabelSchema) -> str:
    return "\n".join(f"- {l.name}: {l.description}" for l in schema.labels)


# Rendered into COVERAGE_PROMPT's {concept_section} slot only when a v2
# profile is in use; the v1 path renders the slot empty, keeping the
# rendered prompt — and therefore the v1 classifier_hash — byte-identical
# to the pre-concepts vintage (2026-08-07 memo: no retroactive re-vintage).
CONCEPTS_SECTION = """Course concepts taught in this course:
{concept_block}

In concepts, list every course concept from that list this message engages \
— exact names only; empty list if none apply.

"""


def _concepts_block(profile2) -> str:
    """Non-promoted concepts only: promoted ones are real labels with their
    own single-label calls, not coverage facets (2026-08-07 memo, hybrid)."""
    if profile2 is None:
        return "(none)"
    lines = [f"- {c.name}: {c.description}"
             for c in profile2.concepts if not c.promoted]
    return "\n".join(lines) or "(none)"


def _render_latency(m: SampledMessage) -> str:
    if m.latency_bucket == "conversation-opening":
        return "(conversation opening)"
    if m.latency_seconds is None:
        return "(unknown)"
    s = m.latency_seconds
    if s < 120:
        human = f"{s:.0f} seconds"
    elif s < 7200:
        human = f"{s / 60:.0f} minutes"
    elif s < 172800:
        human = f"{s / 3600:.0f} hours"
    else:
        human = f"{s / 86400:.0f} days"
    return f"{human} ({m.latency_bucket})"


def _render_sequence(m: SampledMessage) -> str:
    # "No autograder data" (no sequence facts at all for this conversation)
    # is deliberately distinct from the ask-first windowed claim below (no
    # sequence facts vs. a checked-and-empty window) — do not merge them.
    if not m.pre_pattern:
        return "No autograder data for this conversation."
    gran = ("question-level" if m.seq_granularity == "question"
            else "notebook-level")
    if m.pre_pattern == "ask-first":
        # Honest windowed claim, not "no run ever": we only checked the
        # BEFORE_MIN-minute window (src.ingest.sequences), so this reports
        # absence within that window, not absence overall.
        s = (f"No autograder activity in the {BEFORE_MIN} min before this "
             f"message ({gran})")
    else:
        verdict = "PASSED" if m.last_run_success else "FAILED"
        mins = (f"{m.last_run_minutes:.0f}m"
                if m.last_run_minutes is not None else "?")
        s = (f"last run {mins} before this message: {verdict} "
             f"({m.last_run_grader or 'unknown check'}, {gran})")
    if m.snapshot_traceback:
        # snapshot_traceback is a conversation-start flag (one notebook
        # snapshot per conversation, on turn 1 — see the 2026-08-09 pilot
        # memo appendix), not a live/current-state signal.
        s += ("; notebook snapshot at conversation start showed a "
              "traceback")
    return s


def _render_mode(m: SampledMessage) -> str:
    if m.mode == "chatgpt":
        return ("plain-ChatGPT mode — the student toggled the tutor "
                "persona off for this message")
    if m.mode == "tutor":
        return "tutor mode"
    return "unknown (older log)"


def _render_window(turns: list[Turn]) -> str:
    if not turns:
        return "(conversation start)"
    return "\n".join(f"{t.role}: {t.text}" for t in turns)


def draft_labels(messages: list[SampledMessage], schema: LabelSchema,
                 profile: CourseProfile, generate: Generate,
                 on_progress: Callable[[int, int], None] | None = None,
                 on_result: Callable[[SampledMessage, MessageLabels], None]
                 | None = None, workers: int = 8,
                 profile2=None) -> list[MessageLabels]:
    """Call-level fan-out: (message x label) verdict calls plus one coverage
    call per message on a bounded pool. A message's record assembles when all
    its calls land; callbacks fire under the internal lock (serialized,
    progress strictly increasing, per completed message). First failure stops
    further work; already-completed messages were delivered via on_result, so
    a resuming caller (webapp done-set) re-runs only the rest. Concurrency is
    not a provenance input (classifier_hash unchanged by `workers`)."""
    n = len(messages)
    concept_names = ({c.name for c in profile2.concepts if not c.promoted}
                     if profile2 is not None else set())
    concept_section = ("" if profile2 is None else CONCEPTS_SECTION.format(
        concept_block=_concepts_block(profile2)))
    results: list[MessageLabels | None] = [None] * n
    calls_per_msg = len(schema.labels) + 1
    slots = [{"labels": {}, "rationales": {}, "coverage": None,
              "remaining": calls_per_msg} for _ in messages]
    lock = threading.Lock()
    state = {"done": 0, "failure": None}

    def run_call(idx: int, label) -> None:
        with lock:
            if state["failure"] is not None:
                return
        m = messages[idx]
        common = dict(course_context=profile.render_context(),
                      context=_render_window(m.context), text=m.text,
                      context_after=m.context_after or "",
                      latency=_render_latency(m),
                      sequence=_render_sequence(m), mode=_render_mode(m))
        try:
            if label is None:
                verdict = generate(
                    COVERAGE_PROMPT.format(
                        labels=_coverage_labels_block(schema),
                        form_taxonomy=", ".join(FORM_TAXONOMY),
                        concept_section=concept_section, **common),
                    CoverageVerdict)
            else:
                verdict = generate(
                    SINGLE_LABEL_PROMPT.format(
                        label_name=label.name,
                        label_description=label.description,
                        positive_criteria=label.positive_criteria,
                        negative_criteria=label.negative_criteria, **common),
                    SingleLabelVerdict)
        except BaseException as e:
            with lock:
                if state["failure"] is None:
                    state["failure"] = e
            return
        # Assembly and callbacks run under the same lock/failure protocol as
        # generate() itself: on_result/on_progress are caller-supplied and
        # can raise (bad callback, assertion in a test, etc.) — that must
        # abort the run and propagate, not vanish into a discarded Future.
        try:
            with lock:
                if state["failure"] is not None:
                    return
                slot = slots[idx]
                if label is None:
                    slot["coverage"] = verdict
                else:
                    slot["labels"][label.name] = verdict.applies
                    slot["rationales"][label.name] = (
                        verdict.rationale or "(no rationale returned)")
                slot["remaining"] -= 1
                if slot["remaining"] == 0:
                    cov = slot["coverage"]
                    r = MessageLabels(
                        chatlog_id=m.chatlog_id,
                        message_index=m.message_index,
                        labels=slot["labels"], rationales=slot["rationales"],
                        no_label_fits=cov.no_label_fits,
                        coverage_note=cov.note if cov.no_label_fits else "",
                        forms=[f for f in cov.forms if f in FORM_TAXONOMY],
                        concepts=[c for c in cov.concepts
                                  if c in concept_names],
                        move=(cov.move if cov.move in MOVE_TAXONOMY
                              else ""),
                        latency_seconds=m.latency_seconds,
                        latency_bucket=m.latency_bucket,
                        mode=m.mode, defected=m.defected,
                        question_ref=m.question_ref,
                        pre_pattern=m.pre_pattern,
                        seq_granularity=m.seq_granularity,
                        attempted=(None if not m.pre_pattern
                                   else m.pre_pattern != "ask-first"),
                        error_verified=(None if not m.pre_pattern
                                        else m.snapshot_traceback
                                        or m.last_run_success is False))
                    results[idx] = r
                    state["done"] += 1
                    if on_result:
                        on_result(m, r)
                    if on_progress:
                        on_progress(state["done"], n)
        except BaseException as e:
            with lock:
                if state["failure"] is None:
                    state["failure"] = e

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for idx in range(n):
            for label in [*schema.labels, None]:
                pool.submit(run_call, idx, label)
    if state["failure"] is not None:
        raise state["failure"]
    return [r for r in results if r is not None]


def classifier_hash(schema: LabelSchema, model: str,
                    profile: CourseProfile, profile2=None) -> str:
    # \x1e-joined provenance components: none of them may themselves contain
    # \x1e, or the join stops being unambiguous. A v1-only run (profile2
    # None) hashes exactly as before the 2026-08-07 concepts facet — no
    # retroactive re-vintage; a v2 run appends the artifact canonical and
    # the rendered concept block.
    # Fixture SampledMessages (fixed values, not schema/data-dependent) so
    # classifier_hash pins the actual rendered wording of _render_sequence
    # and _render_mode, not just a static tag naming the fields involved —
    # a wording-only change (e.g. the 2026-08-09 ask-first/traceback fix)
    # must move the hash.
    _base = dict(chatlog_id=0, conv_id="x", message_index=0, text="x",
                context=[], context_after=None, stratum="x")
    _fail_msg = SampledMessage(
        **_base, pre_pattern="fail-then-ask", last_run_minutes=4.0,
        last_run_grader="q1_1", last_run_success=False,
        snapshot_traceback=True, seq_granularity="question")
    _ask_msg = SampledMessage(**_base, pre_pattern="ask-first",
                              seq_granularity="notebook")
    _nodata_msg = SampledMessage(**_base)
    canonical = "\x1e".join([
        SINGLE_LABEL_PROMPT,
        COVERAGE_PROMPT.replace("{concept_section}", ""),
        schema.version_id, model,
        profile.canonical(), profile.render_context(),
        f"window={WINDOW_TURNS}",
        "forms=" + ",".join(FORM_TAXONOMY),
        "move=" + ",".join(MOVE_TAXONOMY),
        f"latency=rapid<{RAPID_S},working<{WORKING_S},delayed<{DELAYED_S}",
        _render_sequence(_fail_msg),
        _render_sequence(_ask_msg),
        _render_sequence(_nodata_msg),
        _render_mode(SampledMessage(**_base, mode="tutor")),
        _render_mode(SampledMessage(**_base, mode="chatgpt")),
        _render_mode(SampledMessage(**_base, mode="")),
        "|".join(p.pattern for p in qref._PATTERNS),
        _render_window([]),
        _render_window([Turn(index=0, role="student", text="x",
                             student_index=0)]),
        _coverage_labels_block(LabelSchema(
            instructor_intent="x", labels=[
                LabelDef(name="x", kind="other", description="x",
                        positive_criteria="x", negative_criteria="x")])),
    ])
    if profile2 is not None:
        canonical = "\x1e".join([canonical, profile2.canonical(),
                                 CONCEPTS_SECTION,
                                 _concepts_block(profile2)])
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]
