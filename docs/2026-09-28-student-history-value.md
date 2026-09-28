# Does earlier dialogue help predict recorded student replies?

The full-pass adapter improved recorded-response likelihood, while its generated
behavior remained mixed. Before proposing another model change, measure whether
earlier dialogue contributes to that prediction result. This is a fixed local
diagnostic, not a new generator, prompt-selection round or labeling task.

## Frozen comparison

Use the same 28 eligible development conversations and their 526 saved target
tokens from the completed local training comparison. Retain the original excluded
over-context case; do not admit it because a shorter input would now fit. Use the
unchanged base model and saved full-pass adapter with the original tokenizer,
serialization, packages and target-only scoring function. Reuse their verified
full-history scores rather than recomputing them.

For each input, reuse the existing current-exchange partition: retain the entire
contiguous student request block and following tutor response block. Remove only
the preceding student/tutor turns. Preserve literal text, roles, order and prompt
instruction. Reconstruct each original prompt token sequence before preparing the
shorter input; append its original target tokens without decoding or rewriting
them. Inputs without preceding context have identical conditions: reuse both
cached scores and report them separately.

Score each changed input once per model, with no decoding, sampling, generated
conversation or training. At most 56 new example scores; 600 seconds total for
the scoring run, 4,096 tokens per example and the existing 16 GiB advisory MLX
memory limit with reported-peak checks. Freeze source/model/adapter hashes,
exact tokens, runtime and this protocol before execution. Save each completed
score immediately. Preserve failures or timeouts; no retry, replacement or
budget extension. All processing is local, with remote loading disabled.

## Report and interpretation

Report the paired change in mean target-token negative log likelihood:
`current-exchange loss - full-history loss`. Positive values mean the original
history helped predict that recorded reply. Report the equal-conversation mean,
pooled-token result, counts of positive/negative/unchanged differences and every
paired result for each model. The primary descriptive population is conversations
whose inputs actually change; include the all-28 view and unchanged-input counts.
Use a 1e-5 absolute tolerance only for numerical ties, not as an improvement margin.

Also report the difference between the full-pass and base history benefits and
the base-to-adapter gain within each input condition. These measurements can
separate overall prediction improvement from dependence on supplied history.
They cannot identify why the model uses history, distinguish student style from
task information, or rule out a learned generic response prior.

Stop after one verified report, whether history helps, hurts or has mixed effects.
Do not select a shorter production prompt from this result, adopt the adapter,
generate follow-up examples or start another tuning/labeling round. Existing
studies and the live simulator remain unchanged. Exposed development cases,
unknown learner identities and one recorded continuation per conversation do
not establish personalization, held-out generalization, dialogue realism, silence,
notebook activity or tutor-policy effects.

Implementation reuses the existing private training/scoring helpers and public
exchange partition; no new application API is needed. Authored checks must catch
lost contiguous turns, target changes, mismatched scores, altered pins and repeated
execution. Independently reproduce report arithmetic from saved scores afterward.
Private inputs, token sequences and results stay in ignored
`data/student-history-value-v1/`; only protocol/status documentation is committed
locally. The user's standing authorization and current continuation cover this
bounded local diagnostic; no external provider approval is reused.
