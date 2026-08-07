"""CourseProfile: the course-specific vocabulary the classifier prompt
operates over, kept out of the template so the template stays
course-agnostic (2026-08-06 memo). A profile is a pinned provenance input:
its content is hashed into classifier_hash, so two courses sharing a
template are still different classifiers."""
import hashlib
import json

from pydantic import BaseModel


class CourseProfile(BaseModel):
    course_name: str
    domain_description: str
    tooling: str
    paste_conventions: str
    reference_conventions: str
    message_shape_notes: str

    def canonical(self) -> str:
        return json.dumps(self.model_dump(), sort_keys=True)

    @property
    def profile_id(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()[:12]

    def render_context(self) -> str:
        return (
            f"{self.course_name}: {self.domain_description}\n"
            f"Tooling: {self.tooling}\n"
            f"Pasted material: {self.paste_conventions}\n"
            f"Assignment references: {self.reference_conventions}\n"
            f"Message shape: {self.message_shape_notes}"
        )


# Filled from the corpus-profiling pass behind the 2026-08-06 memo.
DSC10_PROFILE = CourseProfile(
    course_name="DSC 10",
    domain_description=(
        "an introductory data science course (UC San Diego) taught in "
        "Python with the babypandas library, inside Jupyter notebooks; "
        "an AI tutor is embedded in the notebook"),
    tooling="Python, babypandas, numpy, Jupyter notebooks",
    paste_conventions=(
        "students often paste assignment prompt text, code cells, or full "
        "error tracebacks as their message, sometimes with no words of "
        "their own"),
    reference_conventions=(
        "students reference assignment items by number (e.g. 'question "
        "1.6', 'help with 4.1', or a bare number like '3.2')"),
    message_shape_notes=(
        "most messages are under 40 characters; many are terse follow-ups "
        "that only make sense given the preceding turns; messages may be "
        "in languages other than English"),
)
