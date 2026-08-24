"""Repeatable corpus measurements for CourseProfile drafting.

This module does not write CourseProfile prose. It reports deterministic
measurements and message IDs that a human can use to distill the profile.
"""
import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from src.ingest.rawlog import Conversation
from src.labeling.qref import extract_question_ref

_ERROR_RE = re.compile(
    r"\b(traceback|error|exception|failed|failure|syntaxerror|nameerror|"
    r"indexerror|keyerror|typeerror|valueerror|assertionerror)\b",
    re.IGNORECASE)
_CODE_RE = re.compile(
    r"(```|\bdef\b|\bclass\b|\bfor\b.+:|\bwhile\b.+:|==|!=|<=|>=|"
    r"\breturn\b|print\(|\w+\s*=)")
_SHORT_AMBIGUOUS = {"?", "??", "yes", "no", "idk", "ok", "okay",
                    "nvm", "help", "why"}
_REFERENCE_PATTERNS = {
    "q_slug": re.compile(r"\bq\d+(?:[._]\d+)*\b", re.IGNORECASE),
    "question_word": re.compile(
        r"\bquestion\s+\d+(?:\.\d+)*\b", re.IGNORECASE),
    "decimal_question": re.compile(r"\b\d+\.\d+(?:\.\d+)*\b"),
    "lab_reference": re.compile(r"\blab\s*\d+\b", re.IGNORECASE),
    "homework_reference": re.compile(
        r"\b(?:hw|homework)\s*\d+\b", re.IGNORECASE),
    "problem_reference": re.compile(
        r"\b(?:problem|prob)\s*\d+\b", re.IGNORECASE),
    "pa_reference": re.compile(r"\bpa\s*\d+\b", re.IGNORECASE),
}
_CLOSE_READ_REASON_ORDER = [
    "traceback_or_error",
    "code_bearing",
    "question_reference",
    "contains_non_ascii",
    "long_message",
    "short_ambiguous",
    "paste_like",
]


def load_snapshot_conversations(snapshot_dir: Path) -> list[Conversation]:
    return [
        Conversation.model_validate_json(line)
        for line in (Path(snapshot_dir) / "conversations.jsonl").open()
    ]


def _percentile(values: list[int], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = pct * (len(ordered) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    frac = rank - lo
    return ordered[lo] + (ordered[hi] - ordered[lo]) * frac


def _length_summary(values: list[int]) -> dict:
    return {
        "min": min(values) if values else None,
        "median": _percentile(values, 0.5),
        "p90": _percentile(values, 0.9),
        "max": max(values) if values else None,
    }


def _rate(count: int, total: int) -> float:
    return count / total if total else 0.0


def _reference_pattern_counts(text: str) -> list[str]:
    return [name for name, pat in _REFERENCE_PATTERNS.items()
            if pat.search(text)]


def _message_flags(text: str) -> dict[str, bool | str | list[str]]:
    stripped = text.strip()
    words = stripped.split()
    char_len = len(stripped)
    line_count = stripped.count("\n") + (1 if stripped else 0)
    code = bool(_CODE_RE.search(stripped))
    error = bool(_ERROR_RE.search(stripped))
    qref = extract_question_ref(stripped)
    non_ascii = any(ord(ch) > 127 for ch in stripped)
    paste_like = line_count >= 3 or char_len >= 300 or code or error
    short_ambiguous = (
        stripped.lower() in _SHORT_AMBIGUOUS
        or re.fullmatch(r"[\d.]+", stripped.lower()) is not None
        or (len(words) <= 1 and char_len <= 20)
    )
    return {
        "code_bearing": code,
        "traceback_or_error": error,
        "question_reference": bool(qref),
        "normalized_question_ref": qref,
        "reference_patterns": _reference_pattern_counts(stripped),
        "contains_non_ascii": non_ascii,
        "paste_like": paste_like,
        "short_ambiguous": short_ambiguous,
        "long_message": char_len >= 300,
    }


def _close_read_reasons(flags: dict[str, bool | str | list[str]]) -> list[str]:
    reasons = []
    for name in ("traceback_or_error", "code_bearing", "paste_like",
                 "question_reference", "contains_non_ascii",
                 "long_message", "short_ambiguous"):
        if flags.get(name):
            reasons.append(name)
    return reasons


def _close_reading_sample(candidates: dict[str, list[dict]], *,
                          seed: int, per_stratum: int) -> list[dict]:
    rng = random.Random(seed)
    out = []
    seen: set[tuple[int, int]] = set()
    ordered = sorted(
        candidates,
        key=lambda r: (_CLOSE_READ_REASON_ORDER.index(r)
                       if r in _CLOSE_READ_REASON_ORDER
                       else len(_CLOSE_READ_REASON_ORDER), r))
    for reason in ordered:
        bucket = list(candidates[reason])
        rng.shuffle(bucket)
        picked = 0
        for item in bucket:
            key = (item["chatlog_id"], item["message_index"])
            if key in seen:
                continue
            seen.add(key)
            out.append({**item, "reason": reason})
            picked += 1
            if picked >= per_stratum:
                break
    return out


def profile_conversations(conversations: list[Conversation], *, seed: int = 0,
                          close_read_per_stratum: int = 3) -> dict:
    char_lengths: list[int] = []
    word_lengths: list[int] = []
    flags_count: Counter[str] = Counter()
    pattern_count: Counter[str] = Counter()
    refs: Counter[str] = Counter()
    close_read: dict[str, list[dict]] = defaultdict(list)
    student_messages = 0

    for conv in conversations:
        for turn in conv.student_turns:
            student_messages += 1
            text = turn.text.strip()
            char_lengths.append(len(text))
            word_lengths.append(len(text.split()))
            flags = _message_flags(text)
            for name in ("code_bearing", "traceback_or_error",
                         "question_reference", "contains_non_ascii",
                         "paste_like", "short_ambiguous", "long_message"):
                if flags[name]:
                    flags_count[name] += 1
            for pattern in flags["reference_patterns"]:
                pattern_count[pattern] += 1
            qref = str(flags["normalized_question_ref"])
            if qref:
                refs[qref] += 1
            item = {
                "conv_id": conv.conv_id,
                "chatlog_id": conv.chatlog_id,
                "message_index": turn.index,
                "student_index": turn.student_index,
            }
            for reason in _close_read_reasons(flags):
                close_read[reason].append(item)

    top_refs = [
        {"ref": ref, "count": count}
        for ref, count in sorted(refs.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return {
        "metadata": {
            "artifact_type": "course_profile_corpus_report",
            "seed": seed,
            "close_read_per_stratum": close_read_per_stratum,
            "student_text_included": False,
        },
        "counts": {
            "conversations": len(conversations),
            "student_messages": student_messages,
        },
        "message_lengths": {
            "chars": _length_summary(char_lengths),
            "words": _length_summary(word_lengths),
            "short_under_40_chars_rate": _rate(
                sum(1 for n in char_lengths if n < 40), student_messages),
        },
        "rates": {
            name: _rate(flags_count[name], student_messages)
            for name in ("code_bearing", "traceback_or_error",
                         "question_reference", "paste_like",
                         "short_ambiguous", "long_message")
        },
        "language_mix": {
            "ascii_only_messages": student_messages
            - flags_count["contains_non_ascii"],
            "contains_non_ascii_messages": flags_count["contains_non_ascii"],
            "contains_non_ascii_rate": _rate(
                flags_count["contains_non_ascii"], student_messages),
        },
        "reference_patterns": {
            "pattern_counts": dict(sorted(pattern_count.items())),
            "normalized_question_refs": top_refs,
        },
        "close_reading_sample": _close_reading_sample(
            close_read, seed=seed, per_stratum=close_read_per_stratum),
    }


def default_output_path(snapshot_dir: Path) -> Path:
    snapshot_dir = Path(snapshot_dir)
    return snapshot_dir.parent.parent / "profile-reports" / snapshot_dir.name / \
        "profile-report.json"


def write_profile_report(report: dict, out: Path) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure corpus facts for human CourseProfile drafting")
    parser.add_argument("snapshot_dir")
    parser.add_argument("--out", default=None,
                        help="output JSON path; defaults under "
                             "data/profile-reports")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--close-read-per-stratum", type=int, default=3)
    args = parser.parse_args()

    snapshot_dir = Path(args.snapshot_dir)
    report = profile_conversations(
        load_snapshot_conversations(snapshot_dir),
        seed=args.seed,
        close_read_per_stratum=args.close_read_per_stratum)
    out = Path(args.out) if args.out else default_output_path(snapshot_dir)
    write_profile_report(report, out)
    counts = report["counts"]
    print(f"wrote {out} ({counts['conversations']} conversations, "
          f"{counts['student_messages']} student messages)")


if __name__ == "__main__":
    main()
