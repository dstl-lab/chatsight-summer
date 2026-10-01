# Gemini 3.8 Flash for new runs

The user requested trying Gemini 3.8 Flash. The configured API key successfully
retrieved `models/gemini-3.8-flash` on 2026-10-01. Three invented-text requests
passed our existing chat-continuation, notebook-action and tutor-reply schemas
through `generate_content`, with one completed STOP candidate each and no retries.
Returned model version: `gemini-3.8-flash`. Observed request times were 2.838,
2.095 and 4.483 seconds respectively; this is a compatibility check, not a latency
benchmark or evidence of improved student realism. No student data was sent.

Receipts are in ignored `data/gemini-38-upgrade-v1/`. An initial sandboxed metadata
request failed to connect; the network-enabled metadata request succeeded.

## Scoped configuration change

Fresh `src.agents.notebook_example` sessions default to `gemini-3.8-flash`.
An optional `--model` records an explicit alternative in the new session manifest.
With `--previous`, the predecessor's model is inherited; a conflicting override
is rejected. Existing chat preparation already supports
`src.agents.recorded_chat create ... --model gemini-3.8-flash`.

Normal browser generation reads the saved session model. Historical sessions,
frozen experiment settings, labeling defaults and source-pinned engines retain
their original versions. Do not rewrite a historical manifest to upgrade it.
The authored behavior-policy demo at port 8457 uses local selection and templates,
so it has no Gemini dependency and is unaffected.

This changes the model used for new exploratory notebook examples at the user's
request. It does not adopt a new fidelity baseline, reopen closed experiments,
or transfer behavior selection from the local policy to an LLM.

Google's [model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
lists structured-output support; access and the existing SDK protocol were
also checked directly above.

Verification: 52 focused tests passed (one skipped); the full Python suite passed
1,070 tests (three skipped, one existing Starlette/httpx warning). The saved
authored-policy demo verified offline, and an independent caller/source-pin review
found no blocking issues.
