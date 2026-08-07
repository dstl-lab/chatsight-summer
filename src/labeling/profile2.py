"""CourseProfile v2: the versioned artifact the exploration pass emits and
the classify path consumes (2026-08-07 corpus-grounded-labeling memo).
Composition over v1: the six hand-profile fields stay `base`; v2 adds the
course-concept taxonomy and drafted affect/intent layers, plus exploration
provenance. Git-tracked under profiles/ — acceptance is a git review, so an
artifact must be rule-4-safe by construction: lint_profile refuses any
string sharing a verbatim run with sampled student text."""
import json
import re
from pathlib import Path

from pydantic import BaseModel, model_validator

from src.ingest.rawlog import Conversation
from src.labeling.course import CourseProfile
from src.labeling.schema import LabelDef

# Length of the verbatim word run treated as "quoting a student" by
# lint_profile. Eight words is long enough that shared course vocabulary
# ("for loop over the rows of the table") rarely trips it, short enough
# that no sentence of student prose survives.
LINT_NGRAM = 8


class ConceptDef(BaseModel):
    name: str
    description: str
    aliases: list[str] = []
    # Hybrid representation (decision 2026-08-07): a concept is a coverage
    # facet by default; promoting it makes it a real label with its own
    # single-label call, criteria, and Phase-0 admissibility.
    promoted: bool = False
    positive_criteria: str = ""
    negative_criteria: str = ""

    @model_validator(mode="after")
    def _promoted_needs_criteria(self) -> "ConceptDef":
        if self.promoted and not (self.positive_criteria
                                  and self.negative_criteria):
            raise ValueError(
                f"promoted concept {self.name!r} needs positive_criteria "
                "and negative_criteria")
        return self


class CourseProfileV2(BaseModel):
    base: CourseProfile
    concepts: list[ConceptDef]
    affect_labels: list[LabelDef]
    intent_labels: list[LabelDef]
    explored_on: str                    # ISO date of the exploration pass
    corpus_sample: dict[str, int]       # {"conversations": n, "seed": s}
    materials_provided: bool
    repo_sha: str
    accepted: bool = False              # flipped by the instructor in review

    def canonical(self) -> str:
        return json.dumps(self.model_dump(), sort_keys=True)

    @property
    def profile_id(self) -> str:
        import hashlib
        return hashlib.sha256(self.canonical().encode()).hexdigest()[:12]

    def render_context(self) -> str:
        names = ", ".join(c.name for c in self.concepts) or "(none)"
        return f"{self.base.render_context()}\nCourse concepts: {names}"


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _ngrams(words: list[str]) -> set[tuple[str, ...]]:
    return {tuple(words[i:i + LINT_NGRAM])
            for i in range(len(words) - LINT_NGRAM + 1)}


def _artifact_strings(v2: CourseProfileV2) -> list[tuple[str, str]]:
    out = [(f"base.{k}", v) for k, v in v2.base.model_dump().items()]
    for c in v2.concepts:
        out += [(f"concept.{c.name}", s) for s in
                (c.description, c.positive_criteria, c.negative_criteria,
                 *c.aliases)]
    for group, labels in (("affect", v2.affect_labels),
                          ("intent", v2.intent_labels)):
        for l in labels:
            out += [(f"{group}.{l.name}", s) for s in
                    (l.description, l.positive_criteria, l.negative_criteria)]
    return out


def lint_profile(v2: CourseProfileV2,
                 conversations: list[Conversation]) -> list[str]:
    """Return one finding per artifact string that shares a LINT_NGRAM-word
    verbatim run with any student turn in the explored sample. Empty list
    means the artifact is distilled (rule 4) and safe to write."""
    student = set()
    for conv in conversations:
        for t in conv.student_turns:
            student |= _ngrams(_words(t.text))
    findings = []
    for where, text in _artifact_strings(v2):
        if _ngrams(_words(text)) & student:
            findings.append(
                f"{where}: shares a {LINT_NGRAM}-word run with student text")
    return findings


def save_profile(v2: CourseProfileV2, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(v2.model_dump_json(indent=2))
    return path


def load_profile(path: Path) -> CourseProfileV2:
    return CourseProfileV2.model_validate_json(Path(path).read_text())
