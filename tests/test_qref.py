import pytest

from src.labeling.qref import extract_question_ref


@pytest.mark.parametrize("text,ref", [
    ("how do I do 3.2?", "q3_2"),
    ("stuck on question 4", "q4"),
    ("q1_10 keeps failing", "q1_10"),
    ("Q2.4.1 hint please", "q2_4_1"),
    ("is there a way to do 1.5.2 without a loop", "q1_5_2"),
    ("my groupby is broken", ""),
    ("version 3.2 of pandas", "q3_2"),   # known false positive, accepted
])
def test_extract_question_ref(text, ref):
    assert extract_question_ref(text) == ref
