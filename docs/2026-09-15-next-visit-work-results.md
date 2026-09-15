# Next-capture forecast: integration failure and correction

The user explicitly authorized the two unchanged disclosed excerpts and requested
an overall project recap before dispatch. The recap was created and linked first;
`approval-response.json` binds the six relevant private artifacts and predates both
requests. The initial automatic-review rejection remains preserved.

The fixed run completed with **two logical requests, eight adapter attempts and
zero returned forecasts**. Both requests exhausted the existing adapter's four
attempts with HTTP 400: Gemini rejected `additional_properties` in the root and
nested response schema. Physical HTTP attempts below the adapter are unmeasured.
Both cases remain failures, not predictions of unchanged work or zero-quality
student forecasts. There is no behavioral result from this run.

Independent audit verified request/prompt hashes, approval ordering, all prepared
source/input pins, exact error preservation and exclusions in `scores.json`.
The unchanged baselines remain one/four missed changed positions across 58/54 code
positions. Those numbers describe the reference data, not model performance.

## Root cause and minimal correction

The new `Forecast` and nested `Edit` used plain `extra='forbid'` Pydantic config,
which exported `additionalProperties`. Existing `BeforeHelpSelection.model_config`
already removes that provider-unsupported field from exported schema while keeping
extra-field rejection local. The forecast helper omitted this existing convention.
The provider rejection matches that omission; it is an integration bug, not
student behavior or evidence against the forecasting endpoint.

Before changing code, preserve the exact failed helper source under ignored
`next-visit-work-v1/failed-notebook_forecast.py`, hash-matched to the preparation.
Extend the authored regression to reject `additionalProperties` anywhere in the
exported nested schema, observe that failure, then reuse the existing compatible
config on both forecast types while retaining strict local type/extra validation.
No adapter, prompt, source inputs, prior engine or recorded result changes.

The fixed run's budget is exhausted. Do not rerun or silently replace its failures.
Any future live validation needs a separate bounded run; first use an authored
schema smoke check before another real-data forecast. Keep the distinction between
an offline-corrected request format and verified live provider acceptance.

The earlier preparation memo is historical: it correctly describes the blocked
preparation stage. This report supersedes its pending status without rewriting
its pinned private copy. Current-source verification of that failed experiment is
expected to reject after the schema correction; its original source is preserved
and its original Git revision is `f9c44f5`. Offline scoring logic and source data
remain reproducible separately.

## Offline correction verified

The new schema regression failed on the original root/nested
`additionalProperties` fields. Reusing the existing configuration removes both
while the original strict-type, unknown-field and invalid-cell checks still pass.
All 17 related tests pass. The forecast prompt and edit/comparison behavior remain
unchanged; saved failure scoring reproduces exactly. Live acceptance of the
corrected schema has not been tested. No additional requests were made.
