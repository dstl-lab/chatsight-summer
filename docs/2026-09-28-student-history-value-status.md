# Earlier dialogue contributes to prediction, with limits

The [fixed history diagnostic](2026-09-28-student-history-value.md) is complete.
Earlier dialogue helped the trained model predict the recorded next reply in
15 of the 18 conversations where history could be removed. The trained model
also retained its advantage over the base model without that history. Its overall
prediction gain therefore does not, by itself, demonstrate learned individual
student habits.

## Result

These are mean target-token negative log likelihoods, equally weighted across
the 18 affected conversations; lower is better. The current exchange retains
the complete student request and tutor response blocks. Only preceding dialogue
is removed.

| Model | With earlier dialogue | Current exchange only | History benefit | Helped / hurt / tied |
| --- | ---: | ---: | ---: | ---: |
| Base | 7.17448 | 7.71353 | +0.53905 | 12 / 5 / 1 |
| Full-pass adapter | 2.72849 | 3.12299 | +0.39450 | 15 / 3 / 0 |

History benefit is current-only loss minus full-history loss. The adapter's
average benefit is **0.14455 smaller** than the base model's, although it benefits
in more cases. Pooled-token benefits also remain positive: +0.62797 for the base
and +0.32309 for the adapter. Neither weighting supports an increased average
history benefit from training in this diagnostic.

The base-to-adapter loss reduction is 4.44599 with earlier dialogue and 4.59054
without it. That persistence cannot distinguish learning student language,
current-task patterns, a generic response prior, or other training effects.
Removing history also removes earlier tutor and task information; this is not a
test isolating personal style.

The affected population contains 443 target tokens. Ten other conversations
contain no earlier dialogue: their 20 cached model scores were reused exactly,
with zero input or score differences. Across all 28 conversations and 526 target
tokens, history benefits are +0.34653 for the base and +0.25361 for the adapter.
The unchanged cases are reported separately rather than counted as new evidence
that a model ignores history. The original over-context exclusion stays excluded.

## Execution and verification

One local pass completed all 36 new example scores in 31.34 seconds, with a
reported peak MLX allocation of 3.66 GB. No generated replies, model training,
cloud calls, new labels, failures or retries occurred. Exact source prompts were
reconstructed, original target tokens retained without decoding, and cached
base/full scores bound to their completed training receipts.

Seven existing serialization, partition and retrieval tests pass. Authored checks
also cover consecutive student/tutor messages, unchanged-input reuse, mismatched
scores, changed files, report arithmetic and interrupted execution. Independent
review caught a checkpoint-counting issue before model execution; the fix writes
row checkpoints atomically and reconstructs counts from completed files. Both
the original preparation and the zero-execution amendment are preserved. The
final preparation changes no input, target, cached score, runtime or run budget.

The saved verification command reproduces the report from retained scores and
checks source hashes without loading a model. An independent audit verified
109 source and 58 output hashes, exact target tokens, cached controls, every
paired and pooled calculation, and execution limits; it found no remaining
issues. Private preparation, every paired
result, reports and execution receipts remain under ignored
`data/student-history-value-v1/`. Nothing is published.

## Decision

Keep the existing prompt, adapter status and simulator unchanged. The result
supports retaining earlier dialogue for this narrow prediction task; it does
not establish realistic generated conversations or a personalized student model.
These are exposed development conversations with unknown learner identities,
not a new holdout or a random sample of identifiable DSC 10 students.

This diagnostic is closed. No shorter-prompt candidate, further scoring pass,
training run or manual review follows automatically. The unresolved research
gap remains generated behavior, not whether the model can access prior turns.
