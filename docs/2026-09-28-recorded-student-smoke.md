# Run one local reply from an imported recorded start

The recorded-query importer has passed offline checks. Complete one bounded
integration check through the actual browser: import the same selected query into
a new one-decision session, configure the existing local base model and runtime,
and submit one student continuation. This checks the recorded input → browser →
local worker → saved replay path. It is not a new fidelity experiment.

Use the existing model without an adapter; the full-pass adapter remains
experimental. Preserve the source query and its original input-receipt hash.
Before dispatch, tokenize the exact existing student serialization and confirm
that the prompt plus the fixed 256-token output allowance fits the 4,096-token
limit. Do not trim the prefix, choose another case or open the withheld answer.
The selected query was already chosen by sorted ID for integration, not sampled
as a representative student.

The budget is exactly one local student decision, with the normal seed and
120-second limit. No tutor model, cloud request, new label, training or notebook
execution is included. Preserve incomplete output and failures; no retries or
rerolls. After completion, reopen with generation disabled and verify source
immutability, exact input history, saved output tokens, model identity and replay.
Keep private messages, call receipts and checks under ignored data. Record the
outcome here without quoting course content. Commit locally; do not publish.

## Result

The actual browser submission completed one local base-model reply at an EOS
boundary: 751 input tokens, 18 generated tokens including EOS, and approximately
3.32 seconds in the worker. The original importer source and all 92 pinned source
files are unchanged. The prompt tokens match the preflight exactly. The saved
session has one decision and no remaining budget, no adapter and no tutor exchange.

The output repeats the final question in the recorded tutor response with changed
capitalization. This is a concrete role-confusion example, not a successful
plausibility result. It confirms that a successful generation/replay transaction
is separate from a believable simulated student. One selected base-model reply
cannot estimate failure frequency, compare adapters, establish student separation,
or show whether any real student would have replied. The withheld next answer
was not opened or used for selection or generation.

The replay is available on the loopback browser server at port 8444. It was
reopened without sending enabled; both browser display and API checks confirm
read-only access and an exhausted decision budget. Inspecting/reloading preserves
the saved files. No further call, retry, label or training run is queued.
The next behavior work should use existing saved outputs to characterize this
failure before changing a prompt or running another batch.

Private preparation, preflight, receipts and checks live under
`data/recorded-student-smoke-v1`. Preserve that directory and this checkout.
Independent audit reproduced the 751 input tokens and the 17 content tokens plus
EOS, verified the model/runtime hashes and preserved a private audit receipt.
The run is closed with a hashed completion manifest.

No application code changed, so the verification for this increment is the actual
bounded run, saved-token/source audits and read-only replay checks; the prior
772-test result belongs to the unchanged importer implementation.
