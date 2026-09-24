"""Deterministic, internally consistent synthetic Lab 1 class generator."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.episodes.models import EpisodeEvent
from src.ingest.episode_events import build_dataset
from src.synthetic.config import (
    DEFAULT_SEED,
    DEFAULT_STUDENT_COUNT,
    GENERATOR_VERSION,
    HISTORICAL_ANCHOR_SOURCE,
    HISTORICAL_SEQUENCE_ANCHORS,
    NOTEBOOK_PATH,
    QUESTIONS,
    CohortConfig,
    QuestionSpec,
    StudentTraits,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "data" / "synthetic" / "lab1-100"
BASE_TIME = datetime(2026, 9, 14, 15, 0, tzinfo=timezone.utc)
INTERACTION_ACTS = (
    "direct-request",
    "debugging-request",
    "syntax-help",
    "conceptual-clarification",
    "assignment-reference",
    "validation",
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _short_hash(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _student_id(seed: int, index: int) -> str:
    return f"syn_{_short_hash(f'{seed}:{index}', 10)}"


def _student_traits(rng: random.Random) -> StudentTraits:
    persistence = rng.betavariate(2.4, 1.9)
    self_correction = _clamp(
        0.62 * persistence + 0.38 * rng.betavariate(2.2, 2.0)
    )
    directness = rng.betavariate(1.8, 2.5)
    return StudentTraits(
        pace=_clamp(math.exp(rng.gauss(0, 0.32)), 0.52, 2.25),
        persistence=persistence,
        error_propensity=rng.betavariate(2.1, 2.2),
        tutor_propensity=rng.betavariate(2.0, 2.1),
        directness=directness,
        code_transfer_propensity=_clamp(
            0.55 * directness + 0.45 * rng.betavariate(1.7, 2.6)
        ),
        self_correction=self_correction,
    )


@dataclass
class PathPlan:
    student_id: str
    student_index: int
    traits: StudentTraits
    question: QuestionSpec
    seed: int
    skipped: bool
    uses_tutor: bool
    eventual_resolution_base: float
    pre_pattern: str = ""
    interaction_act: str = ""
    code_transfer: bool = False


@dataclass
class PathResult:
    student_id: str
    question_id: str
    skipped: bool
    used_tutor: bool
    pre_pattern: str
    interaction_act: str
    code_transfer: bool
    immediate_outcome: str
    eventually_passed: bool
    event_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "student_id": self.student_id,
            "question_id": self.question_id,
            "skipped": self.skipped,
            "used_tutor": self.used_tutor,
            "pre_pattern": self.pre_pattern,
            "interaction_act": self.interaction_act,
            "code_transfer": self.code_transfer,
            "immediate_outcome": self.immediate_outcome,
            "eventually_passed": self.eventually_passed,
            "event_count": self.event_count,
        }


def _make_plans(
    config: CohortConfig,
) -> tuple[list[PathPlan], dict[str, StudentTraits]]:
    plans: list[PathPlan] = []
    traits_by_student: dict[str, StudentTraits] = {}
    for student_index in range(config.student_count):
        student_seed = config.seed * 1009 + student_index
        rng = random.Random(student_seed)
        student_id = _student_id(config.seed, student_index)
        traits = _student_traits(rng)
        traits_by_student[student_id] = traits
        for question_index, question in enumerate(QUESTIONS):
            path_seed = student_seed * 101 + question_index
            path_rng = random.Random(path_seed)
            skip_probability = _clamp(
                config.skip_base_probability
                + (1 - traits.persistence) * 0.045
                + question.difficulty * 0.015,
                high=0.14,
            )
            skipped = path_rng.random() < skip_probability
            tutor_probability = _clamp(
                0.08
                + 0.46 * traits.tutor_propensity
                + 0.27 * question.difficulty
                - 0.10 * traits.self_correction,
                0.06,
                0.82,
            )
            uses_tutor = not skipped and path_rng.random() < tutor_probability
            plans.append(
                PathPlan(
                    student_id=student_id,
                    student_index=student_index,
                    traits=traits,
                    question=question,
                    seed=path_seed,
                    skipped=skipped,
                    uses_tutor=uses_tutor,
                    eventual_resolution_base=config.eventual_resolution_base,
                )
            )

    tutor_plans = [plan for plan in plans if plan.uses_tutor]
    allocation_rng = random.Random(config.seed + 7001)
    jitter = {id(plan): allocation_rng.random() for plan in tutor_plans}
    ask_count = round(len(tutor_plans) * HISTORICAL_SEQUENCE_ANCHORS["ask-first"])
    fail_count = round(
        len(tutor_plans) * HISTORICAL_SEQUENCE_ANCHORS["fail-then-ask"]
    )

    ask_ranked = sorted(
        tutor_plans,
        key=lambda plan: (
            plan.traits.directness
            + (1 - plan.traits.persistence) * 0.5
            + jitter[id(plan)] * 0.3
        ),
        reverse=True,
    )
    ask = ask_ranked[:ask_count]
    ask_ids = {id(plan) for plan in ask}
    remaining = [plan for plan in tutor_plans if id(plan) not in ask_ids]
    fail_ranked = sorted(
        remaining,
        key=lambda plan: (
            plan.traits.error_propensity
            + plan.question.difficulty * 0.65
            + plan.traits.persistence * 0.25
            + jitter[id(plan)] * 0.25
        ),
        reverse=True,
    )
    fail = fail_ranked[:fail_count]
    fail_ids = {id(plan) for plan in fail}
    for plan in tutor_plans:
        if id(plan) in ask_ids:
            plan.pre_pattern = "ask-first"
        elif id(plan) in fail_ids:
            plan.pre_pattern = "fail-then-ask"
        else:
            plan.pre_pattern = "pass-then-ask"

    direct_count = round(len(tutor_plans) * config.direct_request_share)
    direct_ranked = sorted(
        tutor_plans,
        key=lambda plan: (
            (0.9 if plan.pre_pattern != "pass-then-ask" else 0)
            + plan.traits.directness
            + plan.question.difficulty * 0.25
            + jitter[id(plan)] * 0.15
        ),
        reverse=True,
    )
    direct_ids = {id(plan) for plan in direct_ranked[:direct_count]}
    for plan in tutor_plans:
        rng = random.Random(plan.seed + 17)
        if id(plan) in direct_ids:
            plan.interaction_act = "direct-request"
        elif plan.pre_pattern == "pass-then-ask":
            roll = rng.random()
            if roll < 0.55:
                plan.interaction_act = "validation"
            elif roll < 0.80:
                plan.interaction_act = "conceptual-clarification"
            elif roll < 0.90:
                plan.interaction_act = "syntax-help"
            else:
                plan.interaction_act = "assignment-reference"
        elif plan.pre_pattern == "fail-then-ask":
            plan.interaction_act = (
                "debugging-request" if rng.random() < 0.72 else "syntax-help"
            )
        else:
            plan.interaction_act = (
                "assignment-reference"
                if rng.random() < 0.44
                else "conceptual-clarification"
            )

        transfer_probability = {
            "direct-request": 0.74,
            "assignment-reference": 0.40,
            "debugging-request": 0.18,
            "syntax-help": 0.16,
            "conceptual-clarification": 0.05,
            "validation": 0.025,
        }[plan.interaction_act]
        transfer_probability = _clamp(
            transfer_probability * 0.65
            + plan.traits.code_transfer_propensity * 0.42
        )
        plan.code_transfer = rng.random() < transfer_probability

    return plans, traits_by_student


class Timeline:
    def __init__(
        self,
        student_id: str,
        traits: StudentTraits,
        start: datetime,
        seed: int,
    ):
        self.student_id = student_id
        self.traits = traits
        self.now = start
        self.rng = random.Random(seed)
        self.sequence = 0
        self.execution = 0
        self.turn = 0
        self.records: list[dict[str, Any]] = []

    def wait(self, low_seconds: int, high_seconds: int | None = None) -> None:
        high = high_seconds if high_seconds is not None else low_seconds
        seconds = self.rng.randint(low_seconds, high)
        self.now += timedelta(seconds=max(1, round(seconds * self.traits.pace)))

    def wait_past_inactivity(self) -> None:
        self.wait(31 * 60, 95 * 60)

    def _event(
        self,
        event_type: str,
        question: QuestionSpec,
        payload: dict[str, Any],
        *,
        cell_index: int | None = None,
        correlation_id: str | None = None,
        conversation_id: str | None = None,
        turn_id: str | None = None,
        response_id: str | None = None,
    ) -> dict[str, Any]:
        self.sequence += 1
        index = question.cell_index if cell_index is None else cell_index
        record = {
            "schema_version": "1.0.0",
            "event_id": f"{self.student_id}-{self.sequence:05d}",
            "event_type": event_type,
            "occurred_at": self.now.isoformat(timespec="milliseconds").replace(
                "+00:00", "Z"
            ),
            "client_sequence": self.sequence,
            "analytics_session_id": f"session-{self.student_id}",
            "user_id": self.student_id,
            "notebook_path": NOTEBOOK_PATH,
            "notebook_name": "lab1.ipynb",
            "cell_id": f"lab1-cell-{index}",
            "cell_index": index,
            "question_id": question.question_id,
            "question_source": "grader_id",
            "conversation_id": conversation_id,
            "turn_id": turn_id,
            "response_id": response_id,
            "correlation_id": correlation_id,
            "payload": payload,
        }
        EpisodeEvent.model_validate(record)
        self.records.append(record)
        return record

    def _legacy(
        self,
        event_type: str,
        conversation_id: str,
        payload: dict[str, Any],
        *,
        event_id: str | None = None,
        turn_id: str | None = None,
        response_id: str | None = None,
    ) -> None:
        self.records.append(
            {
                "record_kind": "legacy",
                "event_type": event_type,
                "occurred_at": self.now.isoformat(timespec="milliseconds").replace(
                    "+00:00", "Z"
                ),
                "user_id": self.student_id,
                "event_id": event_id,
                "turn_id": turn_id,
                "response_id": response_id,
                "payload": {"conversation_id": conversation_id, **payload},
            }
        )

    def edit(self, question: QuestionSpec, source: str, previous: str = "...") -> None:
        self._event(
            "cell_edit",
            question,
            {
                "previous_source_hash": _short_hash(previous),
                "source_hash": _short_hash(source),
                "characters_inserted": max(1, len(source) - len(previous)),
                "characters_deleted": max(0, len(previous) - len(source)),
            },
        )

    def execute(
        self,
        question: QuestionSpec,
        source: str,
        *,
        error_name: str | None = None,
    ) -> None:
        self.execution += 1
        correlation = f"{self.student_id}-run-{self.execution}"
        self._event(
            "cell_execution_started",
            question,
            {
                "source_hash": _short_hash(source),
                "execution_count": self.execution,
                "is_autograder": False,
                "paste_to_execution_ms": None,
            },
            correlation_id=correlation,
        )
        duration = self.rng.randint(1, 4)
        self.now += timedelta(seconds=duration)
        self._event(
            "cell_execution_completed",
            question,
            {
                "success": error_name is None,
                "duration_ms": duration * 1000,
                "output_types": ["error"] if error_name else ["execute_result"],
                "is_autograder": False,
            },
            correlation_id=correlation,
        )
        if error_name:
            self._event(
                "cell_error",
                question,
                {"error_name": error_name, "output_types": ["error"]},
                correlation_id=correlation,
            )

    def grade(self, question: QuestionSpec, success: bool) -> None:
        self.execution += 1
        correlation = f"{self.student_id}-run-{self.execution}"
        grader_cell = question.cell_index + 1
        self._event(
            "cell_execution_started",
            question,
            {
                "source_hash": _short_hash(
                    f'grader.check("{question.grader_id}")'
                ),
                "execution_count": self.execution,
                "is_autograder": True,
                "paste_to_execution_ms": None,
            },
            cell_index=grader_cell,
            correlation_id=correlation,
        )
        duration = self.rng.randint(1, 3)
        self.now += timedelta(seconds=duration)
        self._event(
            "cell_execution_completed",
            question,
            {
                "success": True,
                "duration_ms": duration * 1000,
                "output_types": ["execute_result"],
                "is_autograder": True,
            },
            cell_index=grader_cell,
            correlation_id=correlation,
        )
        self._event(
            "autograder_completed",
            question,
            {
                "grader_id": question.grader_id,
                "success": success,
                "output_length": 34 if success else self.rng.randint(180, 520),
            },
            cell_index=grader_cell,
            correlation_id=correlation,
        )

    def ask(
        self,
        question: QuestionSpec,
        act: str,
        *,
        include_code: bool,
    ) -> tuple[str, str | None]:
        self.turn += 1
        conversation_id = (
            f"syn-conv-{self.student_id}-{question.question_id}-{self.turn}"
        )
        turn_id = f"syn-turn-{self.student_id}-{self.turn}"
        response_id = f"syn-response-{self.student_id}-{self.turn}"
        block_id = f"{response_id}-code-1" if include_code else None
        message = self._message(question, act)
        response = self._response(question, act, include_code)
        query = self._event(
            "tutor_query",
            question,
            {
                "message_length": len(message),
                "synthetic_message_act": act,
                "synthetic_ground_truth": True,
            },
            conversation_id=conversation_id,
            turn_id=turn_id,
        )
        self._legacy(
            "tutor_query",
            conversation_id,
            {
                "question": message,
                "mode": "tutor",
                "notebook": "lab1.ipynb",
            },
            event_id=query["event_id"],
            turn_id=turn_id,
        )
        self.wait(5, 24)
        reply = self._event(
            "tutor_response",
            question,
            {
                "response_length": len(response),
                "code_block_count": 1 if block_id else 0,
                "code_block_ids": [block_id] if block_id else [],
                "synthetic_ground_truth": True,
            },
            conversation_id=conversation_id,
            turn_id=turn_id,
            response_id=response_id,
        )
        self._legacy(
            "tutor_response",
            conversation_id,
            {
                "response": response,
                "mode": "tutor",
                "notebook": "lab1.ipynb",
            },
            event_id=reply["event_id"],
            turn_id=turn_id,
            response_id=response_id,
        )
        return response_id, block_id

    def transfer_code(
        self,
        question: QuestionSpec,
        response_id: str,
        block_id: str,
    ) -> None:
        code_hash = _short_hash(question.answer_code)
        if self.rng.random() < 0.35:
            self._event(
                "tutor_code_inserted",
                question,
                {
                    "code_block_id": block_id,
                    "destination_cell_id": f"lab1-cell-{question.cell_index}",
                    "destination_cell_index": question.cell_index,
                    "source_hash": code_hash,
                    "provenance": "inserted_from_tutor",
                },
                response_id=response_id,
            )
            return
        self._event(
            "tutor_code_copied",
            question,
            {
                "code_block_id": block_id,
                "code_hash": code_hash,
                "provenance": "tutor_copy_only",
                "response_to_copy_ms": self.rng.randint(800, 9000),
            },
            response_id=response_id,
        )
        self.wait(1, 8)
        self._event(
            "notebook_paste",
            question,
            {
                "pasted_hash": code_hash,
                "matched_code_block_id": block_id,
                "matched_response_id": response_id,
                "provenance": "copied_then_pasted",
                "response_to_paste_ms": self.rng.randint(1800, 15000),
            },
            response_id=response_id,
        )

    def _message(self, question: QuestionSpec, act: str) -> str:
        variants = {
            "direct-request": [
                f"Give me the exact code for Question {question.question_id}.",
                f"Question {question.question_id}: I need the executable answer.",
                f"Can you write the complete answer for {question.question_id}?",
                f"Just provide the code that passes {question.question_id}.",
            ],
            "debugging-request": [
                f"My attempt for {question.question_id} still fails. What should I check?",
                f"I ran Question {question.question_id} and got an error. Help me debug it.",
                f"Why is my code for {question.question_id} not working?",
            ],
            "syntax-help": [
                f"What syntax should I use for {question.conceptual_hint}?",
                f"I know the approach for {question.question_id}, but not the Python syntax.",
                f"Can you remind me of the method syntax for {question.question_id}?",
            ],
            "conceptual-clarification": [
                f"Can you explain {question.conceptual_hint} for Question {question.question_id}?",
                f"What does the prompt mean by {question.conceptual_hint}?",
                f"I need a conceptual explanation for {question.question_id}, not the answer.",
            ],
            "assignment-reference": [
                f"Question {question.question_id}",
                f"Can you help with {question.question_id}?",
                f"I am on Question {question.question_id}. What is it asking me to do?",
            ],
            "validation": [
                f"I passed {question.question_id}. Is my approach reasonable?",
                f"Question {question.question_id} passes, but can you check my reasoning?",
                f"Is there a cleaner way to solve {question.question_id} after it passes?",
            ],
        }
        return self.rng.choice(variants[act])

    def _response(
        self,
        question: QuestionSpec,
        act: str,
        include_code: bool,
    ) -> str:
        if include_code:
            return (
                f"Here is a complete synthetic example for {question.question_id}:\n"
                f"```python\n{question.answer_code}\n```"
            )
        if act == "validation":
            return (
                "A passing check confirms the recorded output for this question. "
                f"Review whether your code clearly expresses {question.conceptual_hint}."
            )
        if act == "direct-request":
            return (
                "I will not provide the complete answer here. Start by identifying "
                f"the operation for {question.conceptual_hint}, then test one step."
            )
        return (
            f"Focus on {question.conceptual_hint}. Inspect the current values, "
            "change one part, and run the relevant check again."
        )


def _wrong_source(question: QuestionSpec, attempt: int) -> str:
    return (
        f"synthetic_incomplete_{attempt} = None\n"
        f"# target {question.grader_id} is not assigned yet"
    )


def _runtime_error_source(question: QuestionSpec, attempt: int) -> str:
    trigger = {
        "NameError": "synthetic_missing_name",
        "TypeError": "1 + 'synthetic'",
        "ValueError": "int('synthetic')",
        "IndexError": "[0][9]",
        "KeyError": "{}['synthetic']",
    }[question.runtime_error]
    return f"# synthetic runtime attempt {attempt}\n{trigger}"


def _eventual_pass(plan: PathPlan, rng: random.Random) -> bool:
    probability = _clamp(
        plan.eventual_resolution_base
        - 0.16
        + plan.traits.persistence * 0.16
        + plan.traits.self_correction * 0.09
        - plan.question.difficulty * 0.12,
        0.58,
        0.99,
    )
    return rng.random() < probability


def _independent_work(
    timeline: Timeline,
    plan: PathPlan,
    *,
    force_failure: bool = False,
    eventual_pass: bool,
) -> None:
    rng = random.Random(plan.seed + timeline.sequence + 311)
    failure_probability = _clamp(
        0.10
        + plan.traits.error_propensity * 0.50
        + plan.question.difficulty * 0.36
        - plan.traits.self_correction * 0.16,
        0.08,
        0.88,
    )
    failures = 0
    minimum_failures = 1 if force_failure else 0
    while failures < 3 and (
        failures < minimum_failures or rng.random() < failure_probability
    ):
        failures += 1
        if rng.random() < 0.48:
            wrong = _runtime_error_source(plan.question, failures)
            timeline.edit(plan.question, wrong)
            timeline.wait(8, 70)
            timeline.execute(
                plan.question,
                wrong,
                error_name=plan.question.runtime_error,
            )
        else:
            wrong = _wrong_source(plan.question, failures)
            timeline.edit(plan.question, wrong)
            timeline.wait(8, 70)
            timeline.execute(plan.question, wrong)
            timeline.wait(4, 28)
            timeline.grade(plan.question, False)
        timeline.wait(12, 110)
    if eventual_pass:
        timeline.edit(
            plan.question,
            plan.question.answer_code,
            previous=_wrong_source(plan.question, max(1, failures)),
        )
        timeline.wait(8, 75)
        timeline.execute(plan.question, plan.question.answer_code)
        timeline.wait(3, 30)
        timeline.grade(plan.question, True)
    elif failures == 0:
        wrong = _wrong_source(plan.question, 1)
        timeline.edit(plan.question, wrong)
        timeline.execute(plan.question, wrong)
        timeline.grade(plan.question, False)


def _outcome_for(plan: PathPlan, rng: random.Random) -> str:
    roll = rng.random()
    if plan.pre_pattern == "ask-first":
        if roll < 0.15:
            return "quick-pass"
        if roll < 0.995:
            return "no-run-after"
        return "fail-after"
    if plan.pre_pattern == "fail-then-ask":
        if roll < 0.87:
            return "quick-pass"
        if roll < 0.98:
            return "no-run-after"
        return "fail-after"
    if roll < 0.85:
        return "quick-pass"
    if roll < 0.99:
        return "no-run-after"
    return "fail-after"


def _generate_path(timeline: Timeline, plan: PathPlan) -> PathResult:
    start_count = sum(
        record.get("record_kind") != "legacy" for record in timeline.records
    )
    if plan.skipped:
        return PathResult(
            plan.student_id,
            plan.question.question_id,
            True,
            False,
            "",
            "",
            False,
            "skipped",
            False,
            0,
        )

    rng = random.Random(plan.seed + 991)
    timeline.wait(20, 8 * 60)
    eventual_pass = _eventual_pass(plan, rng)
    immediate_outcome = "no-tutor"

    if not plan.uses_tutor:
        _independent_work(
            timeline,
            plan,
            eventual_pass=eventual_pass,
        )
    elif plan.pre_pattern == "pass-then-ask":
        _independent_work(timeline, plan, eventual_pass=True)
        timeline.wait(8, 180)
        response_id, block_id = timeline.ask(
            plan.question,
            plan.interaction_act,
            include_code=plan.code_transfer,
        )
        immediate_outcome = _outcome_for(plan, rng)
        if plan.code_transfer and block_id:
            timeline.wait(1, 12)
            timeline.transfer_code(plan.question, response_id, block_id)
        if immediate_outcome == "quick-pass":
            timeline.wait(3, 90)
            timeline.execute(plan.question, plan.question.answer_code)
            timeline.grade(plan.question, True)
        elif immediate_outcome == "fail-after":
            changed = _wrong_source(plan.question, 9)
            timeline.edit(plan.question, changed)
            timeline.execute(plan.question, changed)
            timeline.grade(plan.question, False)
        eventual_pass = True
    else:
        if plan.pre_pattern == "fail-then-ask":
            _independent_work(
                timeline,
                plan,
                force_failure=True,
                eventual_pass=False,
            )
        response_id, block_id = timeline.ask(
            plan.question,
            plan.interaction_act,
            include_code=plan.code_transfer,
        )
        immediate_outcome = _outcome_for(plan, rng)
        if plan.code_transfer and block_id:
            timeline.wait(1, 12)
            timeline.transfer_code(plan.question, response_id, block_id)
        if immediate_outcome == "quick-pass":
            timeline.wait(4, 105)
            if not plan.code_transfer:
                timeline.edit(
                    plan.question,
                    plan.question.answer_code,
                    previous=_wrong_source(plan.question, 4),
                )
            timeline.execute(plan.question, plan.question.answer_code)
            timeline.grade(plan.question, True)
            eventual_pass = True
        elif immediate_outcome == "fail-after":
            wrong = _wrong_source(plan.question, 7)
            timeline.edit(plan.question, wrong)
            timeline.execute(plan.question, wrong)
            timeline.grade(plan.question, False)
            if eventual_pass:
                timeline.wait_past_inactivity()
                _independent_work(timeline, plan, eventual_pass=True)
        elif eventual_pass:
            timeline.wait_past_inactivity()
            _independent_work(timeline, plan, eventual_pass=True)

    end_count = sum(
        record.get("record_kind") != "legacy" for record in timeline.records
    )
    return PathResult(
        student_id=plan.student_id,
        question_id=plan.question.question_id,
        skipped=False,
        used_tutor=plan.uses_tutor,
        pre_pattern=plan.pre_pattern,
        interaction_act=plan.interaction_act,
        code_transfer=plan.code_transfer,
        immediate_outcome=immediate_outcome,
        eventually_passed=eventual_pass,
        event_count=end_count - start_count,
    )


def _share(counter: Counter, key: str) -> float | None:
    total = sum(counter.values())
    return counter[key] / total if total else None


def _aggregate_results(
    results: list[PathResult],
    event_count: int,
    transcript_row_count: int,
) -> dict[str, Any]:
    represented = [result for result in results if not result.skipped]
    tutor = [result for result in represented if result.used_tutor]
    pre = Counter(result.pre_pattern for result in tutor)
    acts = Counter(result.interaction_act for result in tutor)
    outcomes = Counter(result.immediate_outcome for result in tutor)
    return {
        "potential_question_paths": len(results),
        "represented_question_paths": len(represented),
        "skipped_question_paths": sum(result.skipped for result in results),
        "tutor_using_question_paths": len(tutor),
        "event_count": event_count,
        "transcript_row_count": transcript_row_count,
        "total_jsonl_rows": event_count + transcript_row_count,
        "eventual_pass_paths": sum(result.eventually_passed for result in represented),
        "unresolved_paths": sum(
            not result.eventually_passed for result in represented
        ),
        "code_transfer_paths": sum(result.code_transfer for result in tutor),
        "pre_pattern": {
            name: {"count": pre[name], "share": round(_share(pre, name) or 0, 4)}
            for name in HISTORICAL_SEQUENCE_ANCHORS
        },
        "interaction_acts": {
            name: {"count": acts[name], "share": round(_share(acts, name) or 0, 4)}
            for name in INTERACTION_ACTS
        },
        "immediate_outcomes": {
            name: {"count": count, "share": round(count / len(tutor), 4)}
            for name, count in sorted(outcomes.items())
        },
    }


def _run_id(config: CohortConfig) -> str:
    encoded = json.dumps(
        {
            "generator_version": GENERATOR_VERSION,
            "config": config.public_dict(),
            "questions": [question.public_dict() for question in QUESTIONS],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"cohort_{_short_hash(encoded, 14)}"


def _write_report(
    path: Path,
    config: CohortConfig,
    observed: dict[str, Any],
    dataset,
) -> None:
    lines = [
        "# Synthetic Lab 1 cohort validation",
        "",
        "All students, messages, tutor responses, timings, and outcomes are synthetic.",
        "No real student text or student-level trajectory was used.",
        "",
        "## Run",
        "",
        f"- Students: {config.student_count}",
        f"- Potential student-question paths: {observed['potential_question_paths']}",
        f"- Represented paths: {observed['represented_question_paths']}",
        f"- Raw episode events: {observed['event_count']}",
        f"- Synthetic transcript rows: {observed['transcript_row_count']}",
        f"- Reconstructed episodes: {dataset.meta.episode_count}",
        f"- Questions: {dataset.meta.question_count}",
        f"- Direct-request scenario assumption: {config.direct_request_share:.0%} of tutor-using paths",
        "",
        "## Historical sequence calibration",
        "",
        "These targets apply only among generated tutor-using paths.",
        "",
        "| Pre-chat state | Historical target | Generated share | Generated count |",
        "|---|---:|---:|---:|",
    ]
    for name, target in HISTORICAL_SEQUENCE_ANCHORS.items():
        actual = observed["pre_pattern"][name]
        lines.append(
            f"| {name} | {target:.0%} | {actual['share']:.1%} | {actual['count']} |"
        )
    lines.extend(
        [
            "",
            f"Source and limitation: {HISTORICAL_ANCHOR_SOURCE}.",
            "",
            "## Scenario-generated interaction acts",
            "",
            "These are synthetic ground-truth choices, not measured historical rates.",
            "",
            "| Interaction act | Share of tutor-using paths | Count |",
            "|---|---:|---:|",
        ]
    )
    for name, value in observed["interaction_acts"].items():
        lines.append(f"| {name} | {value['share']:.1%} | {value['count']} |")
    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            "This cohort tests analytics and interface behavior. It does not estimate",
            "real DSC 10 prevalence, learning, student intent, or tutor causality.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def generate_cohort(
    config: CohortConfig,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    config.validate()
    plans, traits = _make_plans(config)
    plans_by_student: dict[str, list[PathPlan]] = defaultdict(list)
    for plan in plans:
        plans_by_student[plan.student_id].append(plan)

    records: list[dict[str, Any]] = []
    results: list[PathResult] = []
    for student_id, student_plans in plans_by_student.items():
        index = student_plans[0].student_index
        start_rng = random.Random(config.seed + index * 43)
        start = BASE_TIME + timedelta(
            days=start_rng.randint(0, 5),
            minutes=start_rng.randint(0, 8 * 60),
        )
        timeline = Timeline(
            student_id,
            traits[student_id],
            start,
            config.seed * 997 + index,
        )
        for plan in sorted(
            student_plans, key=lambda item: item.question.cell_index
        ):
            results.append(_generate_path(timeline, plan))
        records.extend(timeline.records)

    records.sort(
        key=lambda row: (
            row.get("occurred_at", ""),
            row.get("user_id", ""),
            row.get("client_sequence", 0),
            1 if row.get("record_kind") == "legacy" else 0,
        )
    )
    event_count = sum(row.get("record_kind") != "legacy" for row in records)
    transcript_row_count = len(records) - event_count
    observed = _aggregate_results(results, event_count, transcript_row_count)
    run_id = _run_id(config)
    outdir = output_root / run_id
    outdir.mkdir(parents=True, exist_ok=True)
    event_path = outdir / "events.jsonl"
    event_path.write_text(
        "\n".join(
            json.dumps(record, separators=(",", ":"), ensure_ascii=False)
            for record in records
        )
        + "\n",
        encoding="utf-8",
    )

    generation = {
        "generator": "src.synthetic.cohort",
        "generator_version": GENERATOR_VERSION,
        "seed": config.seed,
        "student_count": config.student_count,
        "question_count": len(QUESTIONS),
        "historical_aggregate_anchors": {
            "status": "evidence_anchor_with_documented_limits",
            "source": HISTORICAL_ANCHOR_SOURCE,
            "pre_pattern_shares": HISTORICAL_SEQUENCE_ANCHORS,
        },
        "scenario_assumptions": {
            "direct_request_share": config.direct_request_share,
            "direct_request_sensitivity_targets": [0.10, 0.40],
            "skip_base_probability": config.skip_base_probability,
            "eventual_resolution_base": config.eventual_resolution_base,
        },
        "observed": observed,
    }
    manifest = {
        "bundle_id": run_id,
        "synthetic": True,
        "event_schema_version": "1.0.0",
        "generation": generation,
        "questions": [question.public_dict() for question in QUESTIONS],
        "files": {
            "events": "events.jsonl",
            "cohort_summary": "cohort_summary.json",
            "validation_report": "validation_report.md",
        },
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    dataset = build_dataset(event_path, source_kind="synthetic")
    student_summaries = []
    for student_id, student_traits in traits.items():
        student_results = [
            result.as_dict() for result in results if result.student_id == student_id
        ]
        student_summaries.append(
            {
                "student_id": student_id,
                "traits": student_traits.public_dict(),
                "question_paths": student_results,
            }
        )
    summary = {
        "run_id": run_id,
        "observed": observed,
        "students": student_summaries,
        "viewer_question_summaries": [
            question.model_dump(mode="json") for question in dataset.questions
        ],
    }
    (outdir / "cohort_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    _write_report(
        outdir / "validation_report.md",
        config,
        observed,
        dataset,
    )
    return {
        "run_id": run_id,
        "output_dir": str(outdir),
        "event_path": str(event_path),
        "student_count": config.student_count,
        "event_count": event_count,
        "episode_count": dataset.meta.episode_count,
        "question_count": dataset.meta.question_count,
        "observed": observed,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic synthetic Lab 1 class."
    )
    parser.add_argument("--students", type=int, default=DEFAULT_STUDENT_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--direct-request-share", type=float, default=0.25)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    result = generate_cohort(
        CohortConfig(
            student_count=args.students,
            seed=args.seed,
            direct_request_share=args.direct_request_share,
        ),
        output_root=args.output_root,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
