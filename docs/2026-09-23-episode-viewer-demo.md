# Ready-to-run episode viewer demo

Date: 2026-09-23. Status: implemented.

## Decision

Commit one explicitly fictional Lab 1 cohort with the episode viewer so a
reviewer can inspect the complete interface without generating data or providing
model credentials. Keep the synthetic generator as a separate tool for creating
other scenarios.

## Included bundle

`examples/episode-viewer-demo` contains 100 synthetic students, eight questions,
8,390 accepted events, 566 transcript rows, the cohort summary, and cached
analysis artifacts. Every identity, message, response, timestamp, and outcome is
generated; no real student data is present.

The committed classifications and briefing reuse the already validated synthetic
cache. The question overview is a deterministic offline artifact compatible with
the current prompt and packet hashes. This packaging update made no provider call.

## Reviewer workflow

```bash
uv run episode-viewer-demo
```

The command enables synthetic transcript drill-down and serves only on
`127.0.0.1:8342`. The ordinary `episode-viewer` command remains available for
another schema-compatible export.

## Verification

The repository test checks that the bundle is marked synthetic, contains the
declared cohort dimensions, reconstructs successfully, and loads every cached
artifact without regeneration. The documented launch command was also exercised
against the committed files and returned the expected synthetic metadata.
