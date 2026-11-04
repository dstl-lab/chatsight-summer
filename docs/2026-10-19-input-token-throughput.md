# Input-token accounting and project quota — October 19, 2026

The optimized runner currently throttles an estimated input plus the maximum output
allowance against TPM. Google's documented TPM is input tokens; output allowance
belongs in the separate run-budget calculation. The local 200,000 TPM setting is
not a verified project allowance. Check the actual project before raising limits.

Use Google's countTokens endpoint on the complete generateContentRequest, including
the response schema. The installed SDK's Developer API count_tokens helper cannot
include generation_config, so use the documented REST request shape for this stage.
Persist counts under the exact existing request fingerprint. Counting is a network
operation that sends evidence to the established provider, but produces no assessment.
Never count automatically in offline preparation, inspection, export or tests.

Keep input rate reservations distinct from input-plus-output run budgets. Apply a
small input margin, reconcile against reported input usage after responses, and
pause untouched analysis if required counting fails. Keep an explicitly labeled
estimate mode available. Do not change model, prompt, evidence, order, window,
thinking or output settings; accounting mode is operational, not inference identity.

Quota lookup initially hit a UCSD service restriction. Austin authorized using his
personal Google account. The personal account reached first-time onboarding; no
terms were accepted and no project was created. Austin will open the correct project.
Continue the independent code changes without restarting any existing service or
starting generation calls. Do not infer a quota from account tier or the API key.

Sources: [Google rate limits](https://ai.google.dev/gemini-api/docs/rate-limits),
[countTokens REST contract](https://ai.google.dev/api/tokens).

## Tokenizer measurement

Counted 20 frozen recent PR100 windows in original evidence JSON, without grouping
or table encoding. The generation request uses the same evidence/instructions and
settings as before this accounting change. Twenty countTokens calls took 7.26 seconds;
zero generation calls were made. Provider count: 2,201,943 input tokens, range
14,488–183,386 per window. The previous character estimate including output was
1,586,759. This data is more token-dense than the previous assumption; better counting
does not automatically mean a smaller reservation.

With a 2% input margin, rolling-minute scheduling and four workers, those counts
simulate 14.25–15 minutes at the local 200,000 input TPM for assumed 15–60 second
calls. A hypothetical 1,000,000 input TPM simulates 2.5–5 minutes. Neither is a live
generation benchmark; the larger quota remains unverified. Input evidence, models
and generation settings were not changed to produce these measurements.

Validation: 169 backend tests pass, including eight new tests for full-request
counting, unchanged generation payloads/fingerprints, input-only rate reservations,
separate output budgets, durable count reuse, fail-closed counting, reconciliation
and tokenizer-only CLI behavior. Offline tests make no provider calls. The live
checks above made 21 tokenizer calls total (one synthetic, twenty recorded windows),
zero generation calls, and no changes to the running app or project quotas.
