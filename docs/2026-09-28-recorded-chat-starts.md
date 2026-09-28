# Start the workspace from an existing recorded conversation

The local student and policy-comparison workflow currently starts from a manually
supplied Query JSON. Reuse the historical baseline's existing answer-free `queries`
so researchers can select a recorded conversation without rebuilding the dataset
or copying its next answer into the simulator.

Add an offline list/create command. Listing shows identifiers and prefix counts,
not message text. Creation selects one explicit query ID, preserves the exact
prefix and records the source-file hash, selected-query hash and session hash.
Reuse strict input schemas, split checks and the normal chat creator; initialize
its lock so the browser can immediately open it. Stage creation before publishing
the new directory, reject existing destinations, and make no model calls.
The recorded next answer and training responses stay out of the saved session.

This is a data-entry improvement, not a new experiment or a sampling scheme. These
queries are previously exposed development data. Conversation separation does not
prove learner separation when learner IDs are unknown. The imported prefix is the
existing bounded window, not full conversation history or notebook activity. A
source hash records which input was selected; it does not establish the historical
source's authenticity or validate a simulated student. Preserve closed studies and
their original environments. Do not choose a model or adopt an adapter here.

Verify exact query selection, split rejection, target exclusion, source immutability,
existing-folder protection and browser readiness with authored fixtures. Run the
command once on the existing private input into ignored data, without inference,
cloud requests or new manual labeling.

## Run it

From this checkout, use the project Python environment. Keep private input and
output under ignored `data/`. The input must have the existing strict `train` and
`queries` arrays; only a selected query is copied. `references.json` is not opened.

```sh
.venv/bin/python -m src.agents.recorded_chat list /absolute/path/to/inputs.json

.venv/bin/python -m src.agents.recorded_chat create \
  /absolute/path/to/inputs.json data/recorded-chat \
  --query-id QUERY_ID_FROM_LIST \
  --input-sha256 INPUT_SHA256_FROM_LIST \
  --model 'local-student: see local-student/backend.json' \
  --max-decisions 3

.venv/bin/python -m src.agents.browser_workspace \
  data/recorded-chat --chat --port 8443 \
  --student-model /absolute/path/to/local-mlx-model \
  --student-python /absolute/path/to/mlx-environment/bin/python
```

Creation is offline; the launch above also leaves generation disabled. The
`--model` value is the saved chat label, not a configured backend. Supply the
explicit local model/runtime paths shown above when enabling generation; add an
explicit `--student-adapter` only to use that adapter. No model, runtime or adapter
is installed or selected by the importer. See the
[local browser guide](2026-09-28-local-student-backend.md#run-it) for generation,
and the [policy comparison guide](2026-09-28-local-policy-comparison.md#run-it)
for an explicit Gemini tutor and a comparison directory.

`recorded-start.json` records the input path/byte hash, selected query/canonical
hash and created session/canonical hash. Rechecking these is an offline provenance
audit; this extra receipt is not a new browser validation gate. The normal session
engine/state checks continue to apply. Changing the input after listing requires
listing it again. Existing destinations, including concurrently created empty
directories, are not overwritten. Input errors omit private validation excerpts.

The split check deliberately reuses the existing retrieval validator, discarding
its output. It does a small unused TF-IDF calculation rather than duplicating
validation or changing the engine-pinned schema. It never adds retrieved answers
to the session, and does not alter closed studies or their environments.

## Verification and limits

All 772 Python tests pass, with three optional skips and the existing
Starlette/httpx deprecation warning. The four importer checks cover the actual
CLI, exact Unicode/whitespace preservation, hidden-reference exclusion, split and
hash failures, source-change interruption, browser readiness/read-only generation,
existing destinations and a concurrent directory-creation regression. Independent
review found no remaining blocker after the publication race was fixed.

A private start was prepared from the original input after verifying its existing
receipt's input hash. Selection used the first query by sorted ID solely to check
integration, not random sampling. The actual browser displays its unchanged
starting conversation read-only. No student decision, cloud request, new label,
training or closed-study modification occurred. The read-only launcher was given
explicit base-model/runtime paths with no adapter; it did not run inference.
This is workflow progress, not new evidence about simulator fidelity.
