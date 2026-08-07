"""Exploration pass: read a corpus sample (plus optional course materials)
once, emit a CourseProfileV2 draft for instructor review (2026-08-07 memo).
Never invoked at labeling time (rule 2): the CLI here is the only caller,
and the artifact it writes is the only thing the classify path ever sees.
Student excerpts go INTO the prompt and never into the artifact; lint_profile
gates every write (rule 4)."""
import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from pydantic import BaseModel

from src.ingest.rawlog import Conversation
from src.labeling.course import CourseProfile
from src.labeling.llm import Generate
from src.labeling.profile2 import (ConceptDef, CourseProfileV2, lint_profile,
                                   save_profile)
from src.labeling.schema import LabelDef

# Excerpt budget per conversation: enough to show register and shape,
# bounded so a 150-conversation digest stays well under context limits.
EXCERPTS_PER_CONV = 4
EXCERPT_CHARS = 160
MATERIALS_CHARS = 20_000   # per uploaded file


# Wire format for Gemini structured output: v2 minus provenance, v1 fields
# flattened. No dict[...] fields (Gemini rejects additionalProperties).
class ExplorationDraft(BaseModel):
    course_name: str
    domain_description: str
    tooling: str
    paste_conventions: str
    reference_conventions: str
    message_shape_notes: str
    concepts: list[ConceptDef]
    affect_labels: list[LabelDef]
    intent_labels: list[LabelDef]


EXPLORE_PROMPT = """You are profiling a course from its AI-tutor chat logs \
so a labeling system can be grounded in what the course actually is.

{materials_block}Corpus digest (per conversation: notebook, student-turn \
count, excerpted student turns — tutor text omitted):
{digest}

Produce:
1. The course profile fields: course_name, domain_description, tooling, \
paste_conventions (what students paste and how), reference_conventions (how \
students reference assignment items), message_shape_notes (typical length, \
terseness, languages).
2. concepts: a taxonomy of what the course demonstrably teaches — seed from \
the course materials when provided, otherwise from curricular artifacts \
visible in the chats, and refine by what students actually discuss. One \
entry per concept: short name, one-sentence description, common aliases. \
Leave promoted=false and criteria empty.
3. affect_labels: student sentiment/emotion labels, and 4. intent_labels: \
generic help-seeking intent labels — each with description, \
positive_criteria, negative_criteria. Labels must be judgeable on messages \
as they actually occur in these logs (see the digest: mostly terse, often \
pasted or deictic), not only on articulate prose. Prefer fewer, sharper \
labels.

Rules: distill, never quote — no phrase copied from a student turn may \
appear in any output field. Do not invent concepts the data or materials \
cannot support."""


def build_digest(conversations: list[Conversation]) -> str:
    lines = []
    for c in conversations:
        turns = c.student_turns
        lines.append(f"[{c.notebook or 'unknown'} · {len(turns)} student "
                     "turns]")
        for t in turns[:EXCERPTS_PER_CONV]:
            lines.append(f"  student: {t.text[:EXCERPT_CHARS]}")
    return "\n".join(lines)


def _materials_block(materials_texts: list[str]) -> str:
    if not materials_texts:
        return ""
    joined = "\n---\n".join(m[:MATERIALS_CHARS] for m in materials_texts)
    return f"Course materials provided by the instructor:\n{joined}\n\n"


def explore(conversations: list[Conversation], materials_texts: list[str],
            generate: Generate, *, sample_meta: dict[str, int],
            repo_sha: str, explored_on: str) -> CourseProfileV2:
    prompt = EXPLORE_PROMPT.format(
        materials_block=_materials_block(materials_texts),
        digest=build_digest(conversations))
    draft: ExplorationDraft = generate(prompt, ExplorationDraft)
    return CourseProfileV2(
        base=CourseProfile(
            course_name=draft.course_name,
            domain_description=draft.domain_description,
            tooling=draft.tooling,
            paste_conventions=draft.paste_conventions,
            reference_conventions=draft.reference_conventions,
            message_shape_notes=draft.message_shape_notes),
        concepts=draft.concepts, affect_labels=draft.affect_labels,
        intent_labels=draft.intent_labels, explored_on=explored_on,
        corpus_sample=sample_meta,
        materials_provided=bool(materials_texts), repo_sha=repo_sha)


def write_draft(v2: CourseProfileV2, conversations: list[Conversation],
                path: Path) -> Path:
    findings = lint_profile(v2, conversations)
    if findings:
        raise ValueError("lint: artifact quotes student text — refusing to "
                         "write:\n" + "\n".join(findings))
    return save_profile(v2, path)


def main() -> None:
    from src.config import Settings
    from src.ingest.rawlog import fetch_conversations
    from src.labeling.llm import make_generate

    parser = argparse.ArgumentParser(
        description="Corpus exploration -> CourseProfile v2 draft")
    parser.add_argument("--course-slug", required=True)
    parser.add_argument("--sample", type=int, default=150)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--materials", nargs="*", default=[],
                        help="optional course-material text files")
    args = parser.parse_args()

    settings = Settings.load()
    if not settings.gemini_api_key:
        sys.exit("GEMINI_API_KEY missing from .env")
    generate = make_generate(settings.gemini_api_key)
    conversations = fetch_conversations(settings.ext_db_url,
                                        limit=args.sample)
    materials = [Path(p).read_text() for p in args.materials]
    try:
        repo_sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                  capture_output=True, text=True,
                                  cwd=settings.repo_root).stdout.strip()
    except OSError:
        repo_sha = ""
    v2 = explore(conversations, materials, generate,
                 sample_meta={"conversations": len(conversations),
                              "seed": args.seed},
                 repo_sha=repo_sha or "unknown",
                 explored_on=date.today().isoformat())
    out = Path(settings.repo_root) / "profiles" / \
        f"{args.course_slug}-draft.json"
    write_draft(v2, conversations, out)
    print(f"Draft written: {out}")
    print(f"  profile_id {v2.profile_id} · {len(v2.concepts)} concepts · "
          f"{len(v2.affect_labels)} affect · {len(v2.intent_labels)} intent")
    print("Review the draft, edit as needed, set accepted:true, rename to "
          f"profiles/{args.course_slug}.json, and commit (the accept gate "
          "is git review — 2026-08-07 memo).")


if __name__ == "__main__":
    main()
