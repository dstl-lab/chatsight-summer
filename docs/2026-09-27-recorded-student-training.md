# Prepare recorded student replies for training

Use recorded replies as supervised targets, without another semantic-label pass.
The historical response baseline already contains the required examples: each
library row has a dialogue prefix and its actual first next student message.
Reuse those rows and the existing conversation partition. Do not build another
extractor, rewrite replies, or substitute generated messages as targets.

Use the existing private `inputs.json` (`train` and answer-free `queries`) and
separate `references.json` directly. Verify the old receipts and canonical
sources, exact reference joins, conversation separation, and byte-for-byte source
preservation. Keep a private readiness manifest pointing to those files; do not
duplicate the dataset or add an exporter before a training consumer needs one.
Blank recorded targets cannot be treated as a stop decision.
No model call, fine-tuning job, notebook execution or new judgment is part of this
preparation. The current simulator stays unchanged.

The inherited prefix contains up to six earlier turns plus the current student
request and tutor response. It is not the full conversation. Preserve that
definition for the first comparison; increasing context is a separate change.
Multiple examples from one conversation are dependent. The query split is
previously exposed development data, not a pristine holdout. Learner identities
are unavailable, so conversation separation does not establish student separation.

The next milestone is one base-versus-trained comparison using the same model,
tokenizer, prompt serialization and context policy. Fix the model, compute budget,
training settings and checkpoint before examining its development results. Score
only the recorded student target tokens, masking all context/tutor tokens; report
per-conversation average negative log likelihood and paired differences. A lower
loss is evidence of improved conditional prediction of these observed messages,
not proof that alternatives are implausible. Tokenizer and context policy affect
likelihood, so this is not a cross-model leaderboard
([Transformers documentation](https://huggingface.co/docs/transformers/en/perplexity)).

The eventual training adapter must make the model produce the student's reply.
Keep student/tutor names explicit inside the input transcript and put the recorded
student target in the model's output slot. Simply mapping tutors to the model's
assistant role would train the wrong task. Identifiers remain join metadata,
outside model inputs.

Stop after that fixed comparison, including failures and context exclusions. Do
not tune repeatedly on the development split or automatically replace the deployed
generator. Full-conversation realism, whether a student replies, unseen-student
generalization and real tutor-policy effects remain unmeasured. No training run is
configured yet; model and available compute must be settled first.

For local execution, MLX LM already provides LoRA and completion-only loss
masking; use its existing trainer instead of building one
([official guide](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md)).
A small locally trainable model must be compared with its own unchanged weights,
not with the current Gemini results: changing both model and training would
confound the comparison. Neither the trainer nor model weights are installed by
this preparation.

Local preparation is complete. The ignored
`data/recorded-student-training-v1/verify.py` and `manifest.json` reference the
existing baseline without copying messages. The checker revalidates source pins,
strict input schemas, split separation, reference joins and source-turn ordering;
its normal invocation also verifies the saved manifest. Existing corpus/retrieval
checks pass (five tests). Private artifacts remain outside Git, and the simulator
and frozen experiments are unchanged.
