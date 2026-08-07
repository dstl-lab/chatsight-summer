"""Draft classification of sampled messages against a schema version.
classifier_hash is the provenance pin: same hash <=> same prompt template,
schema version, model, course profile, and context window (CLAUDE.md rule 2)."""
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
class LabelVerdict(BaseModel):
    label: str
    applies: bool
    rationale: str


class LabelVerdicts(BaseModel):
    verdicts: list[LabelVerdict]
    # Detection channel, not a labeling one (2026-08-06 memo): the model may
    # say "no label fits" but may never name a new label. Feeds the
    # instructor's coverage pile; round-trips through the tweak loop.
    no_label_fits: bool = False


class MessageLabels(BaseModel):
    chatlog_id: int
    message_index: int
    labels: dict[str, bool]
    rationales: dict[str, str]
    no_label_fits: bool = False   # default: old snapshots still parse


CLASSIFY_PROMPT = """You label one student message from a student–AI tutor \
conversation.

Course context:
{course_context}

For EACH label below decide true/false and give a one-sentence rationale. \
Judge the student's act in THIS message — what the student is doing at this \
point in the conversation — using the preceding turns to resolve short or \
deictic messages (a bare "?", a question number, a pasted error).

Rules:
- Distinguish student-authored words from pasted material. A pasted \
assignment prompt or bare error output expresses no affect by itself; label \
it by what the student is using it to do.
- Very short messages inherit their meaning from the immediately preceding \
turns, including the student's own previous message.
- If a label cannot be judged from this message even with context, mark it \
false and say why in the rationale.

Labels:
{labels}

Conversation so far (most recent last; may be empty):
{context}

STUDENT MESSAGE TO LABEL:
{text}

Tutor reply after (may be empty):
{context_after}

Return one verdict entry per label: label (exact name), applies \
(true/false), rationale (one sentence). Also set no_label_fits=true if this \
message shows a student act that none of the labels capture; otherwise \
false. Do not invent label names."""


def _labels_block(schema: LabelSchema) -> str:
    return "\n".join(
        f"- {l.name}: {l.description} | applies when: {l.positive_criteria} "
        f"| does NOT apply when: {l.negative_criteria}"
        for l in schema.labels
    )


def _render_window(turns: list[Turn]) -> str:
    if not turns:
        return "(conversation start)"
    return "\n".join(f"{t.role}: {t.text}" for t in turns)


def _validated_verdicts(v: LabelVerdicts, schema: LabelSchema
                        ) -> tuple[dict[str, bool], dict[str, str]]:
    """Drop hallucinated label names not in the schema; default any missing
    expected label to False so labels.jsonl only ever contains real names."""
    expected = [l.name for l in schema.labels]
    by_name = {item.label: item for item in v.verdicts}
    labels: dict[str, bool] = {}
    rationales: dict[str, str] = {}
    for name in expected:
        if name in by_name:
            labels[name] = by_name[name].applies
            rationales[name] = by_name[name].rationale or "(no verdict returned)"
        else:
            labels[name] = False
            rationales[name] = "(no verdict returned)"
    return labels, rationales


def draft_labels(messages: list[SampledMessage], schema: LabelSchema,
                 profile: CourseProfile, generate: Generate,
                 on_progress: Callable[[int, int], None] | None = None,
                 on_result: Callable[[SampledMessage, MessageLabels], None]
                 | None = None) -> list[MessageLabels]:
    out: list[MessageLabels] = []
    block = _labels_block(schema)
    for i, m in enumerate(messages):
        prompt = CLASSIFY_PROMPT.format(
            course_context=profile.render_context(), labels=block,
            context=_render_window(m.context), text=m.text,
            context_after=m.context_after or "",
        )
        v: LabelVerdicts = generate(prompt, LabelVerdicts)
        labels, rationales = _validated_verdicts(v, schema)
        out.append(MessageLabels(chatlog_id=m.chatlog_id,
                                 message_index=m.message_index,
                                 labels=labels, rationales=rationales,
                                 no_label_fits=v.no_label_fits))
        if on_result:
            on_result(m, out[-1])
        if on_progress:
            on_progress(i + 1, len(messages))
    return out


def classifier_hash(schema: LabelSchema, model: str,
                    profile: CourseProfile) -> str:
    canonical = "\x1e".join([CLASSIFY_PROMPT, schema.version_id, model,
                             profile.canonical(), f"window={WINDOW_TURNS}"])
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]
