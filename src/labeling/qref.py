"""Deterministic question-reference extraction from student messages.
DSC 10 reference_conventions: students cite assignment items as "3.2",
"q1_10", "question 4", "1.5.2". Normalized to grader_id shape (q3_2) so
the sequence join can narrow from notebook- to question-level. Pure text
processing — no LLM, no DB. Known false positives (version numbers) are
accepted and measured, not special-cased."""
import re

_PATTERNS = [
    re.compile(r"\bq(\d+(?:[._]\d+)*)\b", re.IGNORECASE),
    re.compile(r"\bquestion\s+(\d+(?:\.\d+)*)\b", re.IGNORECASE),
    re.compile(r"\b(\d+\.\d+(?:\.\d+)*)\b"),
]


def extract_question_ref(text: str) -> str:
    for pat in _PATTERNS:
        m = pat.search(text)
        if m:
            return "q" + m.group(1).replace(".", "_").lower()
    return ""
