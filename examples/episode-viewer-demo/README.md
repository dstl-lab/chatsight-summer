# Episode viewer demo data

This ready-to-view bundle contains 100 fictional students working across eight
Lab 1 questions. Every identity, message, tutor response, timestamp, and outcome
is synthetic; no real student record is included.

Run it from the repository root:

```bash
uv run episode-viewer-demo
```

Then open `http://127.0.0.1:8342`.

`events.jsonl` is the input event table. The other JSON files contain the
reproducible cohort summary and cached analysis shown by the dashboard, so the
demo does not require Gemini credentials. See `validation_report.md` for the
generated counts and the boundary on interpreting them.
