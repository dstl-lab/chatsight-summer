"""The only module that imports google-genai. Everything else takes an injected
`generate` callable so it is testable offline."""
import time
from typing import Callable

from pydantic import BaseModel

Generate = Callable[[str, type[BaseModel]], BaseModel]

DEFAULT_MODEL = "gemini-2.5-flash"


def with_retries(generate: Generate, attempts: int = 4, base_delay: float = 2.0,
                 sleep: Callable[[float], None] = time.sleep,
                 on_retry: Callable[[dict | None], None] | None = None
                 ) -> Generate:
    """A mass-label run is one call per student message, hundreds deep; a
    single transient 429/5xx must not abort it. Retries everything — a
    permanent error (bad key) just costs a few extra seconds before raising.
    on_retry gets {"attempt", "max", "wait_s"} before each backoff and None
    after any success, so a UI can show and clear a retry banner."""
    def retrying(prompt: str, response_model: type[BaseModel]) -> BaseModel:
        for attempt in range(attempts):
            try:
                result = generate(prompt, response_model)
                if on_retry:
                    on_retry(None)
                return result
            except Exception:
                if attempt == attempts - 1:
                    raise
                delay = base_delay * 2 ** attempt
                if on_retry:
                    on_retry({"attempt": attempt + 2, "max": attempts,
                              "wait_s": delay})
                sleep(delay)
        raise AssertionError("unreachable")
    return retrying


def gen_config(response_model: type[BaseModel],
               temperature: float | None = None) -> dict:
    """Generation config. temperature is only ever set for vote-sampling
    diagnostics (Phase 0 entropy routing) — labeling runs stay at the API
    default; a temperature would be a provenance input if it touched
    snapshot verdicts."""
    config: dict = {
        "response_mime_type": "application/json",
        "response_schema": response_model,
    }
    if temperature is not None:
        config["temperature"] = temperature
    return config


def make_generate(api_key: str, model: str = DEFAULT_MODEL,
                  on_retry: Callable[[dict | None], None] | None = None,
                  temperature: float | None = None, *,
                  single_attempt: bool = False) -> Generate:
    """Use single_attempt for saved operations that must never resend a request."""
    if type(single_attempt) is not bool:
        raise ValueError('single_attempt must be a boolean.')
    from google import genai

    if single_attempt:
        client = genai.Client(api_key=api_key, http_options=genai.types.HttpOptions(
            timeout=120000, retry_options={'attempts': 1}))
    else:
        client = genai.Client(api_key=api_key)

    def generate(prompt: str, response_model: type[BaseModel]) -> BaseModel:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=gen_config(response_model, temperature),
        )
        if single_attempt and (not response.candidates or len(response.candidates) != 1
                or response.candidates[0].finish_reason != genai.types.FinishReason.STOP):
            raise ValueError('Single-attempt generation requires exactly one completed STOP candidate.')
        return response_model.model_validate_json(response.text)

    return generate if single_attempt else with_retries(generate, on_retry=on_retry)
