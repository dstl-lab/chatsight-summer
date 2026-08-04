"""The only module that imports google-genai. Everything else takes an injected
`generate` callable so it is testable offline."""
import time
from typing import Callable

from pydantic import BaseModel

Generate = Callable[[str, type[BaseModel]], BaseModel]

DEFAULT_MODEL = "gemini-2.5-flash"


def with_retries(generate: Generate, attempts: int = 4, base_delay: float = 2.0,
                 sleep: Callable[[float], None] = time.sleep) -> Generate:
    """A mass-label run is one call per student message, hundreds deep; a
    single transient 429/5xx must not abort it. Retries everything — a
    permanent error (bad key) just costs a few extra seconds before raising."""
    def retrying(prompt: str, response_model: type[BaseModel]) -> BaseModel:
        for attempt in range(attempts):
            try:
                return generate(prompt, response_model)
            except Exception:
                if attempt == attempts - 1:
                    raise
                sleep(base_delay * 2 ** attempt)
        raise AssertionError("unreachable")
    return retrying


def make_generate(api_key: str, model: str = DEFAULT_MODEL) -> Generate:
    from google import genai

    client = genai.Client(api_key=api_key)

    def generate(prompt: str, response_model: type[BaseModel]) -> BaseModel:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": response_model,
            },
        )
        return response_model.model_validate_json(response.text)

    return with_retries(generate)
