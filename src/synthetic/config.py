"""Transparent configuration for the synthetic Lab 1 cohort.

Only the pre-tutor sequence shares are historical aggregate anchors. All other
probabilities are explicit scenario assumptions, not claims about DSC 10.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

GENERATOR_VERSION = "1.0.1"
DEFAULT_SEED = 20260909
DEFAULT_STUDENT_COUNT = 100
NOTEBOOK_PATH = "example_notebooks/lab1/lab1.ipynb"

HISTORICAL_SEQUENCE_ANCHORS = {
    "ask-first": 0.27,
    "fail-then-ask": 0.17,
    "pass-then-ask": 0.56,
}
HISTORICAL_ANCHOR_SOURCE = (
    "docs/2026-08-09-sequence-pilot-first-numbers.md; "
    "7,782 historical tutor conversations; notebook-level join; "
    "45-minute pre-chat and 20-minute outcome windows"
)


@dataclass(frozen=True)
class QuestionSpec:
    question_id: str
    grader_id: str
    cell_index: int
    prompt: str
    answer_code: str
    difficulty: float
    runtime_error: str
    conceptual_hint: str

    def public_dict(self) -> dict:
        data = asdict(self)
        data.pop("answer_code")
        return data


QUESTIONS = (
    QuestionSpec(
        "1.1.1",
        "q1_1_1",
        12,
        "Make an array containing 2, 4, and 6 named even_numbers.",
        "even_numbers = np.array([2, 4, 6])",
        0.12,
        "NameError",
        "constructing a NumPy array from listed values",
    ),
    QuestionSpec(
        "1.1.2",
        "q1_1_2",
        15,
        "Make an array containing 0, -1, 1, pi, and e named odd_numbers.",
        "odd_numbers = np.array([0, -1, 1, np.pi, np.e])",
        0.22,
        "TypeError",
        "using NumPy constants inside an array",
    ),
    QuestionSpec(
        "1.1.4",
        "q1_1_4",
        21,
        "Use np.arange for multiples of 99 from 0 through 9999.",
        "multiples_of_99 = np.arange(0, 10000, 99)",
        0.46,
        "ValueError",
        "the exclusive stop value and step in np.arange",
    ),
    QuestionSpec(
        "1.1.5",
        "q1_1_5",
        24,
        "Create hourly collection times in seconds for all 30 days.",
        "collection_times = np.arange(0, 30 * 24 * 60 * 60, 60 * 60)",
        0.52,
        "ValueError",
        "converting days and hours into seconds",
    ),
    QuestionSpec(
        "2.2.2",
        "q2_2_2",
        90,
        "Assign the tenth movie name from top_10_movies_by_name.",
        "tenth_movie = top_10_movies_by_name.index[9]",
        0.38,
        "IndexError",
        "zero-based indexing",
    ),
    QuestionSpec(
        "3.2",
        "q3_2",
        141,
        "Sort imdb_by_name chronologically into imdb_sorted.",
        "imdb_sorted = imdb_by_name.sort_values('Year')",
        0.58,
        "KeyError",
        "sorting a DataFrame by a named column",
    ),
    QuestionSpec(
        "3.3",
        "q3_3",
        144,
        "Use code to get the earliest movie title from imdb_sorted.",
        "earliest_movie_title = imdb_sorted.index[0]",
        0.64,
        "KeyError",
        "retrieving an index label after sorting",
    ),
    QuestionSpec(
        "4.3",
        "q4_3_2",
        192,
        "Find average ratings for 20th- and 21st-century movies.",
        (
            "average_20th_century_rating = "
            "imdb[imdb.get('Year') <= 2000].get('Rating').mean()\n"
            "average_21st_century_rating = "
            "imdb[imdb.get('Year') > 2000].get('Rating').mean()"
        ),
        0.82,
        "ValueError",
        "boolean filtering around the year 2000 boundary",
    ),
)


@dataclass(frozen=True)
class CohortConfig:
    student_count: int = DEFAULT_STUDENT_COUNT
    seed: int = DEFAULT_SEED
    direct_request_share: float = 0.25
    skip_base_probability: float = 0.025
    eventual_resolution_base: float = 0.90

    def validate(self) -> None:
        if self.student_count < 1:
            raise ValueError("student_count must be positive")
        if not 0 <= self.direct_request_share <= 1:
            raise ValueError("direct_request_share must be between 0 and 1")
        if not 0 <= self.skip_base_probability <= 1:
            raise ValueError("skip_base_probability must be between 0 and 1")
        if not 0 <= self.eventual_resolution_base <= 1:
            raise ValueError("eventual_resolution_base must be between 0 and 1")

    def public_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class StudentTraits:
    pace: float
    persistence: float
    error_propensity: float
    tutor_propensity: float
    directness: float
    code_transfer_propensity: float
    self_correction: float

    def public_dict(self) -> dict:
        return {name: round(value, 4) for name, value in asdict(self).items()}
