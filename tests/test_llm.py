"""Retry behavior for the Gemini wrapper. A mass-label run is hundreds of
sequential calls; one transient 429/5xx must not abort the whole job."""
import pytest
from pydantic import BaseModel

from src.labeling.llm import with_retries


class Out(BaseModel):
    x: int


def test_transient_failures_are_retried_with_backoff():
    calls = {"n": 0}
    slept: list[float] = []

    def flaky(prompt, response_model):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return Out(x=7)

    generate = with_retries(flaky, attempts=4, base_delay=2.0,
                            sleep=slept.append)
    assert generate("p", Out) == Out(x=7)
    assert calls["n"] == 3
    assert slept == [2.0, 4.0]  # exponential backoff


def test_persistent_failure_raises_after_attempts_exhausted():
    calls = {"n": 0}

    def broken(prompt, response_model):
        calls["n"] += 1
        raise RuntimeError("503 UNAVAILABLE")

    generate = with_retries(broken, attempts=3, base_delay=1.0,
                            sleep=lambda _: None)
    with pytest.raises(RuntimeError, match="503"):
        generate("p", Out)
    assert calls["n"] == 3
