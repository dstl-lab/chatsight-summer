# One full training pass over existing recorded replies

The browser's repeated reply received the correct new tutor context. The saved
training-target check finds no exact match for that output or the cohort's
repeated outputs among eligible training answers. Removing duplicates or
penalizing all repeated requests is therefore not supported by this diagnosis.

The existing adapter used only a small hash-selected training subset. Test the
remaining obvious coverage limitation once: start from the same frozen base
weights and train one pass over **every eligible example** in the already
separated training partition. This changes data coverage and total updates
together; it does not isolate their effects or establish the cause of repetition.

Reuse the original local runner, tokenizer, response-only loss, sequence limit,
seed, optimizer, adapter settings and batch size. Preserve legitimate repeated
targets. Keep the original hash ordering before the trainer's seeded shuffle.
Use the same fixed development references and exclusions, with no new split,
labels or examples. The final adapter is the only candidate; there is no
development evaluation during training or intermediate checkpoint selection.

Freeze tokens, counts, packages, source hashes and settings before execution.
Stop after one epoch or 90 minutes of model execution, whichever occurs first,
with the original 16 GiB advisory memory limit and reported-peak checks. Retain
any failure or timeout as incomplete; do not retry or extend it. Existing model
files are read locally; there are no downloads, uploads or cloud calls.

Before and after training, score the unchanged recorded development replies.
Report equal-conversation mean negative log likelihood, pooled token loss and
every paired difference. Compare the final candidate with both the base model
and the saved small-subset adapter; verify matching tokens and reference IDs.
Call this a development prediction improvement only if its conversation mean
is lower than the small-subset adapter and more conversations improve than
worsen. Report all results regardless of that descriptive decision.

This closes after the saved adapter, score comparison and integrity checks.
No additional generated conversations, human review, automatic model adoption
or further training follows within this scope. Development cases are already
exposed, examples are conversation-dependent, learner identities are unavailable,
and the model predicts text conditional on a reply. Prediction improvement
cannot establish realistic silence, repetition rates, notebook actions,
generalization, or effects of tutor policies on real students.
