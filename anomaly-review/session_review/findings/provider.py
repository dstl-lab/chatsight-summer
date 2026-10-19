"""Measured Gemini transport with one SDK attempt and explicit inference settings."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
import threading
import urllib.error
import urllib.request

from . import analyze_sessions as analyzer, compact
from .historical import digest, private_json


@dataclass(frozen=True)
class Options:
    workers: int = 4
    rpm: int = 30
    tpm: int = 200_000
    compact: bool = True
    thinking: str = "default"
    max_output_tokens: int = 8192
    timeout_seconds: int = 180
    max_requests: int = 0
    max_estimated_tokens: int = 0
    transport: str = "concurrent"
    batch_enqueued_tokens: int = 0
    token_counting: str = "provider"

    def __post_init__(self):
        if type(self.workers) is not int or not 1 <= self.workers <= 16: raise ValueError("Choose 1–16 workers")
        if type(self.rpm) is not int or not 1 <= self.rpm <= 10000: raise ValueError("Set a positive RPM limit")
        if type(self.tpm) is not int or self.tpm < 1: raise ValueError("Set a positive TPM limit")
        if self.thinking not in {"default", "low", "medium", "high"}: raise ValueError("Unknown thinking level")
        if self.transport not in {"concurrent", "batch"}: raise ValueError("Unknown provider transport")
        if self.token_counting not in {"provider", "estimate"}: raise ValueError("Unknown input-token accounting mode")
        if not 256 <= self.max_output_tokens <= 32768 or not 5 <= self.timeout_seconds <= 600: raise ValueError("Invalid output/timeout budget")
        if min(self.max_requests, self.max_estimated_tokens, self.batch_enqueued_tokens) < 0: raise ValueError("Budgets cannot be negative")

    def inference(self):
        return {"compact": self.compact, "thinking": self.thinking, "max_output_tokens": self.max_output_tokens,
                "wire_version": compact.VERSION if self.compact else "original-evidence-json-v1",
                "encoder_sha256": hashlib.sha256(__import__("pathlib").Path(compact.__file__).read_bytes()).hexdigest()}


def compatible(value):
    if isinstance(value, dict): return {k: compatible(v) for k, v in value.items() if k != "additionalProperties"}
    if isinstance(value, list): return [compatible(v) for v in value]
    return value


def payload(evidence, options):
    raw = compact.dumps(evidence)
    if options.compact:
        encoded = compact.dumps(compact.pack(evidence))
        # Tiny inputs can grow under table encoding. Keep the original when smaller.
        if len(encoded) + len(compact.INSTRUCTIONS) < len(raw):
            text = analyzer.PROMPT + compact.INSTRUCTIONS + encoded
        else: text = analyzer.PROMPT + raw
    else: text = analyzer.PROMPT + raw
    config = {"temperature": 0, "response_mime_type": "application/json",
        "response_json_schema": compatible(analyzer.Assessment.model_json_schema()), "max_output_tokens": options.max_output_tokens}
    if options.thinking != "default": config["thinking_config"] = {"thinking_level": options.thinking}
    schema_allowance = (len(compact.dumps(config["response_json_schema"])) + 2) // 3 + 32
    input_estimate = (len(text) + 2) // 3 + schema_allowance
    return text, config, {"original_characters": len(analyzer.PROMPT) + len(raw), "sent_characters": len(text),
                          "estimated_input_tokens": input_estimate,
                          "output_token_allowance": options.max_output_tokens,
                          "estimated_tokens": input_estimate + options.max_output_tokens,
                          "token_estimate_basis": "characters/3 including schema overhead, plus reserved output; not provider usage"}


def wire_config(config):
    names = {"temperature": "temperature", "response_mime_type": "responseMimeType", "response_json_schema": "responseJsonSchema", "max_output_tokens": "maxOutputTokens"}
    result = {names[k]: v for k, v in config.items() if k in names}
    if "thinking_config" in config: result["thinkingConfig"] = {"thinkingLevel": config["thinking_config"]["thinking_level"].upper()}
    return result


class TokenCountError(RuntimeError):
    def __init__(self, code=None):
        self.code = code
        super().__init__("Provider input token counting failed; no assessment was requested")


def count_input_tokens(text, config, model, options):
    """Tokenize the full request without generating. No prompt/key in diagnostics."""
    name = model.removeprefix("models/")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name): raise ValueError("Invalid model resource")
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key: raise TokenCountError()
    request = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{name}:countTokens",
        data=json.dumps({"generateContentRequest": {"model": "models/" + name,
            "contents": [{"role": "user", "parts": [{"text": text}]}], "generationConfig": wire_config(config)}}).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=min(options.timeout_seconds, 45)) as response:
            value = json.loads(response.read(1024**2))
    except urllib.error.HTTPError as error:
        raise TokenCountError(error.code) from None
    except Exception:
        raise TokenCountError() from None
    count = value.get("totalTokens")
    if type(count) is not int or count <= 0: raise TokenCountError()
    return count


def input_accounting(metrics, options, *, counted=None):
    """TPM covers input; the separate run budget still reserves maximum output."""
    tokens = metrics["estimated_input_tokens"] if counted is None else counted
    if type(tokens) is not int or tokens <= 0: raise TokenCountError()
    # CountTokens can differ slightly from generation usage; keep a small margin.
    reserved = max(tokens + 32, (tokens * 102 + 99) // 100) if counted is not None else tokens
    return {**metrics, "input_tokens_before_send": tokens,
        "input_token_source": "provider_count_full_request" if counted is not None else "character_estimate",
        "rate_limit_input_tokens": reserved, "run_budget_tokens": reserved + options.max_output_tokens}


class InputTokenCache:
    """Persist tokenizer results, independently of assessment receipts and identity."""
    FORMAT = "gemini-input-token-count-v1"

    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True, mode=0o700)

    def count(self, text, config, model, options, *, measure=None):
        key = fingerprint(text, config, model, options)
        path = self.folder / (key + ".json")
        def saved():
            if path.is_symlink(): raise ValueError("Refusing a symlink token count")
            doc = json.loads(path.read_text())
            count = doc.get("input_tokens")
            if doc.get("format") != self.FORMAT or doc.get("request_key") != key or type(count) is not int or count <= 0:
                raise ValueError("Invalid saved input-token count")
            return count
        if path.exists(): return saved(), True
        count = (measure or count_input_tokens)(text, config, model, options)
        if type(count) is not int or count <= 0: raise TokenCountError()
        try:
            private_json(path, {"format": self.FORMAT, "request_key": key, "input_tokens": count,
                "counted_at": datetime.now(timezone.utc).isoformat()})
        except FileExistsError:
            return saved(), True
        return count, False


def request_key(evidence, model, options):
    text, config, _ = payload(evidence, options)
    return fingerprint(text, config, model, options)


def fingerprint(text, config, model, options):
    return digest({"model": model, "text": text, "config": config, "inference": options.inference()})


def client(options):
    from google import genai
    from google.genai import types
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key: raise ValueError("Configure the Gemini key in the new service")
    return genai.Client(api_key=key, http_options=types.HttpOptions(timeout=options.timeout_seconds * 1000,
        retry_options=types.HttpRetryOptions(attempts=1)))


def usage(value):
    if hasattr(value, "model_dump"): value = value.model_dump(exclude_none=True)
    value = value or {}
    names = {"input_tokens": ("prompt_token_count", "promptTokenCount"), "output_tokens": ("candidates_token_count", "candidatesTokenCount"),
             "thinking_tokens": ("thoughts_token_count", "thoughtsTokenCount"), "total_tokens": ("total_token_count", "totalTokenCount"),
             "cached_input_tokens": ("cached_content_token_count", "cachedContentTokenCount")}
    return {key: next((value[n] for n in aliases if type(value.get(n)) is int), None) for key, aliases in names.items()}


@dataclass
class CallResult:
    assessment: analyzer.Assessment
    usage: dict
    duration_seconds: float


def call(api, text, config, model):
    start = time.monotonic()
    response = api.models.generate_content(model=model, contents=text, config=config)
    finish = response.candidates[0].finish_reason if response.candidates else None
    if getattr(finish, "value", finish) != "STOP": raise ValueError("Incomplete provider response")
    return CallResult(analyzer.Assessment.model_validate_json(response.text), usage(response.usage_metadata), time.monotonic() - start)


def generate(evidence, model, options):
    text, config, _ = payload(evidence, options)
    api = client(options)
    try:
        return call(api, text, config, model)
    finally:
        api.close()


class ClientPool:
    """One reusable HTTP client per worker, never shared concurrently between threads."""
    def __init__(self, options):
        self.options, self.local, self.clients, self.lock = options, threading.local(), [], threading.Lock()

    def call(self, text, config, model):
        if not hasattr(self.local, "client"):
            self.local.client = client(self.options)
            with self.lock: self.clients.append(self.local.client)
        return call(self.local.client, text, config, model)

    def close(self):
        for api in self.clients: api.close()
