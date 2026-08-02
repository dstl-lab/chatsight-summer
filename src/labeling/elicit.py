"""Intent elicitation: instructor's stated trends -> drafted label schema, and
free-text feedback -> revised schema. Drafting is anchored by design; reliability
measurement is blind and lives elsewhere (invariant 8)."""
from pydantic import BaseModel

from src.labeling.llm import Generate
from src.labeling.schema import LabelDef, LabelSchema


class DraftedLabels(BaseModel):
    labels: list[LabelDef]


ELICIT_PROMPT = """You are helping a course instructor turn the trends they want \
to see in student–AI tutor chat logs into a precise label schema.

Instructor's stated interest:
{intent}

Draft 3-8 binary message-level labels. Each label must have: a kebab-case name; \
kind ("conceptual" for topic/content labels, "behavioral" for help-seeking or \
affect, "other" otherwise); a one-sentence description; positive_criteria (when \
it applies); negative_criteria (nearby cases where it must NOT apply). Labels \
must be checkable from a single student message with surrounding conversation \
context. Prefer fewer, sharper labels over many vague ones."""

REVISE_PROMPT = """You are revising a label schema for student–AI tutor chat \
logs based on instructor feedback.

Instructor's original interest:
{intent}

Current labels:
{labels}

Instructor's feedback on the drafted labels as seen on a sample:
{feedback}

Return the full revised label set (same format, 3-8 binary message-level \
labels), applying the feedback. Keep labels the feedback did not touch."""


def draft_schema(intent_text: str, generate: Generate) -> LabelSchema:
    drafted = generate(ELICIT_PROMPT.format(intent=intent_text), DraftedLabels)
    return LabelSchema(instructor_intent=intent_text, labels=drafted.labels)


def revise_schema(current: LabelSchema, feedback: str, generate: Generate) -> LabelSchema:
    prompt = REVISE_PROMPT.format(
        intent=current.instructor_intent,
        labels="\n".join(
            f"- {l.name} ({l.kind}): {l.description} | applies: {l.positive_criteria} "
            f"| does not apply: {l.negative_criteria}"
            for l in current.labels
        ),
        feedback=feedback,
    )
    drafted = generate(prompt, DraftedLabels)
    return LabelSchema(
        instructor_intent=current.instructor_intent,
        labels=drafted.labels,
        parent_version=current.version_id,
        feedback_applied=feedback,
    )
