"""The only module that imports google-genai. Everything else takes an injected
`generate` callable so it is testable offline."""
from typing import Callable

from pydantic import BaseModel

Generate = Callable[[str, type[BaseModel]], BaseModel]

DEFAULT_MODEL = "gemini-2.5-flash"


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

    return generate
