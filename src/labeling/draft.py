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
from typing import Callable

from pydantic import BaseModel

from src.ingest.rawlog import Turn
from src.labeling.course import CourseProfile
from src.labeling.llm import Generate
from src.labeling.sampler import WINDOW_TURNS, SampledMessage
from src.labeling.schema import LabelSchema


# Wire format for Gemini structured output. Must stay free of dict[...] fields:
# pydantic renders those as JSON-schema additionalProperties, which the Gemini
# Developer API rejects. Lists of typed items only.
class SingleLabelVerdict(BaseModel):
    applies: bool
    rationale: str


class CoverageVerdict(BaseModel):
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

Set no_label_fits=true only if this message shows a student act that NONE \
of the labels capture (a message can be partially captured: some act \
labeled, another not — that still counts). If true, describe the uncaptured \
act in one sentence in note; do not propose or name any label. Otherwise \
no_label_fits=false and note empty."""


def _coverage_labels_block(schema: LabelSchema) -> str:
    return "\n".join(f"- {l.name}: {l.description}" for l in schema.labels)


def _render_window(turns: list[Turn]) -> str:
    if not turns:
        return "(conversation start)"
    return "\n".join(f"{t.role}: {t.text}" for t in turns)


def _classify_message(m: SampledMessage, schema: LabelSchema,
                      profile: CourseProfile,
                      generate: Generate) -> MessageLabels:
    common = dict(course_context=profile.render_context(),
                  context=_render_window(m.context), text=m.text,
                  context_after=m.context_after or "")
    labels: dict[str, bool] = {}
    rationales: dict[str, str] = {}
    for l in schema.labels:
        v: SingleLabelVerdict = generate(
            SINGLE_LABEL_PROMPT.format(
                label_name=l.name, label_description=l.description,
                positive_criteria=l.positive_criteria,
                negative_criteria=l.negative_criteria, **common),
            SingleLabelVerdict)
        labels[l.name] = v.applies
        rationales[l.name] = v.rationale or "(no rationale returned)"
    c: CoverageVerdict = generate(
        COVERAGE_PROMPT.format(labels=_coverage_labels_block(schema),
                               **common),
        CoverageVerdict)
    return MessageLabels(chatlog_id=m.chatlog_id,
                         message_index=m.message_index, labels=labels,
                         rationales=rationales,
                         no_label_fits=c.no_label_fits,
                         coverage_note=c.note if c.no_label_fits else "")


def draft_labels(messages: list[SampledMessage], schema: LabelSchema,
                 profile: CourseProfile, generate: Generate,
                 on_progress: Callable[[int, int], None] | None = None,
                 on_result: Callable[[SampledMessage, MessageLabels], None]
                 | None = None) -> list[MessageLabels]:
    out: list[MessageLabels] = []
    for i, m in enumerate(messages):
        out.append(_classify_message(m, schema, profile, generate))
        if on_result:
            on_result(m, out[-1])
        if on_progress:
            on_progress(i + 1, len(messages))
    return out


def classifier_hash(schema: LabelSchema, model: str,
                    profile: CourseProfile) -> str:
    # \x1e-joined provenance components: none of them may themselves contain
    # \x1e, or the join stops being unambiguous.
    canonical = "\x1e".join([
        SINGLE_LABEL_PROMPT, COVERAGE_PROMPT, schema.version_id, model,
        profile.canonical(), profile.render_context(),
        f"window={WINDOW_TURNS}",
        _render_window([]),
        _render_window([Turn(index=0, role="student", text="x",
                             student_index=0)]),
    ])
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]
