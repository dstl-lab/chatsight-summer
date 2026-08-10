"""Intent elicitation: instructor's stated trends -> drafted label schema, and
free-text feedback -> revised schema. Drafting is anchored by design; reliability
measurement is blind and lives elsewhere (invariant 8)."""
from pydantic import BaseModel

from src.labeling.course import CourseProfile
from src.labeling.llm import Generate
from src.labeling.schema import (CRITERIA_WORD_CAP, DESC_WORD_CAP, LabelDef,
                                 LabelSchema, oversized_fields)


class DraftedLabels(BaseModel):
    labels: list[LabelDef]


def _capped_generate(prompt: str, generate: Generate) -> DraftedLabels:
    """Generate labels, re-prompting once on cap violations, then hard-fail:
    oversized criteria never enter a schema (2026-08-10 audit finding)."""
    drafted = generate(prompt, DraftedLabels)
    findings = oversized_fields(drafted.labels)
    if findings:
        drafted = generate(
            prompt + _RETRY_ADDENDUM.format(findings=", ".join(findings)),
            DraftedLabels)
        findings = oversized_fields(drafted.labels)
    if findings:
        raise ValueError("label criteria exceed brevity caps after retry: "
                         + ", ".join(findings))
    return drafted


ELICIT_PROMPT = """You are helping a course instructor turn the trends they want \
to see in student–AI tutor chat logs into a precise label schema.

Course context:
{course_context}

Instructor's stated interest:
{intent}

{covered_block}Draft 3-8 binary message-level labels. Each label must have: a kebab-case name; \
kind ("conceptual" for topic/content labels, "behavioral" for help-seeking or \
affect, "other" otherwise); a one-sentence description; positive_criteria (when \
it applies); negative_criteria (nearby cases where it must NOT apply). Labels \
must be checkable from a single student message with surrounding conversation \
context. Prefer fewer, sharper labels over many vague ones. Labels must be judgeable on messages as they actually occur in this course's logs (see message shape above), not only on articulate prose. \
Labels must be mutually distinct: no two labels' criteria may be written so \
that one message satisfies both by design — overlap between labels is a \
defect, not richness. Do not draft a label whose evidence is merely "the \
student asked a question".

BREVITY IS A HARD REQUIREMENT: a human annotator must hold the criterion \
in mind while judging in seconds. description <= {desc_cap} words; each \
criteria field <= {crit_cap} words. Plain words, no nested clauses."""

_COVERED_TEMPLATE = """Constructs ALREADY COVERED by standing label layers — \
do NOT draft duplicates or near-duplicates of these; spend the instructor's \
label budget only on constructs this list misses:
{covered}

"""

REVISE_PROMPT = """You are revising a label schema for student–AI tutor chat \
logs based on instructor feedback.

Course context:
{course_context}

Instructor's original interest:
{intent}

Current labels:
{labels}

Instructor's feedback on the drafted labels as seen on a sample:
{feedback}

Return the full revised label set (same format, 3-8 binary message-level \
labels), applying the feedback. Keep labels the feedback did not touch.

BREVITY IS A HARD REQUIREMENT: description <= {desc_cap} words; each \
criteria field <= {crit_cap} words. Plain words, no nested clauses."""

_RETRY_ADDENDUM = """

Your previous draft broke the brevity caps on: {findings}. Rewrite those \
fields within the caps, preserving meaning. Return the full label set."""


def _covered_block(profile2) -> str:
    """Standing layers the composed schema will already carry (2026-08-07
    distinctness memo): promoted concepts + affect + intent labels. The
    elicitation must see them so the instructor's budget compiles into what
    is MISSING, not into rediscovering the intent layer under new names."""
    if profile2 is None:
        return ""
    lines = [f"- {c.name}: {c.description} | applies: {c.positive_criteria}"
             for c in profile2.concepts if c.promoted]
    lines += [f"- {l.name}: {l.description} | applies: {l.positive_criteria}"
              for l in (*profile2.affect_labels, *profile2.intent_labels)]
    if not lines:
        return ""
    return _COVERED_TEMPLATE.format(covered="\n".join(lines))


def draft_schema(intent_text: str, profile: CourseProfile,
                 generate: Generate, profile2=None) -> LabelSchema:
    drafted = _capped_generate(
        ELICIT_PROMPT.format(intent=intent_text,
                             course_context=profile.render_context(),
                             covered_block=_covered_block(profile2),
                             desc_cap=DESC_WORD_CAP,
                             crit_cap=CRITERIA_WORD_CAP),
        generate)
    return LabelSchema(instructor_intent=intent_text, labels=drafted.labels)


def revise_schema(current: LabelSchema, feedback: str, profile: CourseProfile, generate: Generate) -> LabelSchema:
    prompt = REVISE_PROMPT.format(
        intent=current.instructor_intent,
        course_context=profile.render_context(),
        labels="\n".join(
            f"- {l.name} ({l.kind}): {l.description} | applies: {l.positive_criteria} "
            f"| does not apply: {l.negative_criteria}"
            for l in current.labels
        ),
        feedback=feedback,
        desc_cap=DESC_WORD_CAP,
        crit_cap=CRITERIA_WORD_CAP,
    )
    drafted = _capped_generate(prompt, generate)
    return LabelSchema(
        instructor_intent=current.instructor_intent,
        labels=drafted.labels,
        parent_version=current.version_id,
        feedback_applied=feedback,
    )
