"""Draft classification of sampled messages against a schema version.
classifier_hash is the provenance pin: same hash <=> same prompt template,
schema version, and model (CLAUDE.md rule 2)."""
import hashlib

from pydantic import BaseModel

from src.labeling.llm import Generate
from src.labeling.sampler import SampledMessage
from src.labeling.schema import LabelSchema


class LabelVerdicts(BaseModel):
    verdicts: dict[str, bool]
    rationales: dict[str, str]


class MessageLabels(BaseModel):
    chatlog_id: int
    message_index: int
    labels: dict[str, bool]
    rationales: dict[str, str]


CLASSIFY_PROMPT = """You label one student message from a student–AI tutor \
conversation. For EACH label below decide true/false and give a one-sentence \
rationale. Judge only the student message; context is for disambiguation.

Labels:
{labels}

Tutor message before (may be empty):
{context_before}

STUDENT MESSAGE TO LABEL:
{text}

Tutor message after (may be empty):
{context_after}

Return verdicts and rationales keyed by exact label name."""


def _labels_block(schema: LabelSchema) -> str:
    return "\n".join(
        f"- {l.name}: {l.description} | applies when: {l.positive_criteria} "
        f"| does NOT apply when: {l.negative_criteria}"
        for l in schema.labels
    )


def _validated_verdicts(v: LabelVerdicts, schema: LabelSchema
                        ) -> tuple[dict[str, bool], dict[str, str]]:
    """Drop hallucinated label names not in the schema; default any missing
    expected label to False so labels.jsonl only ever contains real names."""
    expected = [l.name for l in schema.labels]
    labels: dict[str, bool] = {}
    rationales: dict[str, str] = {}
    for name in expected:
        if name in v.verdicts:
            labels[name] = v.verdicts[name]
            rationales[name] = v.rationales.get(name, "(no verdict returned)")
        else:
            labels[name] = False
            rationales[name] = "(no verdict returned)"
    return labels, rationales


def draft_labels(messages: list[SampledMessage], schema: LabelSchema,
                 generate: Generate) -> list[MessageLabels]:
    out: list[MessageLabels] = []
    block = _labels_block(schema)
    for m in messages:
        prompt = CLASSIFY_PROMPT.format(
            labels=block, context_before=m.context_before or "",
            text=m.text, context_after=m.context_after or "",
        )
        v: LabelVerdicts = generate(prompt, LabelVerdicts)
        labels, rationales = _validated_verdicts(v, schema)
        out.append(MessageLabels(chatlog_id=m.chatlog_id,
                                 message_index=m.message_index,
                                 labels=labels, rationales=rationales))
    return out


def classifier_hash(schema: LabelSchema, model: str) -> str:
    canonical = "\x1e".join([CLASSIFY_PROMPT, schema.version_id, model])
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]
