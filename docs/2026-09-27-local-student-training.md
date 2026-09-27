# One local student-response training pilot

Continue the recorded-target plan with one local, compute-bounded comparison.
Use `mlx-community/Qwen3-4B-4bit` at revision
`4dcb3d101c2a062e5c1d4bb173588c54ea6c4d25`, MLX LM 0.31.3, and the existing
conversation partition. This is a compact instruction model with local adapters,
compared with its own unchanged quantized weights, not a Gemini comparison.
Public weights may be downloaded; student data, adapters and results stay local.

Use one explicitly labeled transcript as the model's user input; output is the
recorded student message. Apply the tokenizer's generation template with thinking
disabled, then encode the target independently without special tokens. Check that
decoding restores the exact target, including leading newlines. Identifiers never
enter model input. Training includes one message-end token; evaluation excludes
that token and measures recorded content only. An observed message end does not
label a conversation stop.

Reject whole examples longer than 4,096 tokens, with separate training/development
exclusion records. Never truncate a target. From eligible training examples select
100 by smallest SHA-256 of `20260927:<example-id>`, before any model scores. Stop if
fewer than 100 qualify. Train one pass over those 100 examples, batch size one,
with seed 20260927 in NumPy and MLX. This is a small pilot, not training on every
available example. Preserve selected conversation counts and dependence.

Use Adam at constant learning rate 0.00001; LoRA in the last four layers, rank 8,
scale 20, dropout zero; gradient checkpointing, no accumulation, an advisory MLX
memory limit of 16 GiB, and abort if reported peak memory exceeds 16 GiB after
any scored example or training update. This cannot prevent a transient allocation
above that limit. Stop after 100 updates or 45 minutes of model execution, whichever comes
first. An interrupted or failed run stays incomplete; no automatic retry,
checkpoint extension, alternative model or parameter sweep follows. Use only the
final adapter, with no development validation or checkpoint selection during
training. The existing MLX trainer handles optimization and weight saving.

MLX LM 0.31.3's default loss includes one padded position when a sequence is padded.
Correct its upper bound by subtracting one from the supplied sequence length;
cast logits to float32 before cross entropy. An authored check must verify exact
target counts and independence from masked prompt labels and padding. Do not use
the stock full-assistant chat serialization: it may alter leading newlines and
include template text as target content.

Before training, score all eligible development references against starting
weights. After training, score the identical fixed examples against the final
adapter. Save each content-token count, summed negative log likelihood and mean
negative log likelihood. Report the mean of conversation means and paired
differences (trained minus starting); lower is better. Report coverage and every
exclusion; a negative average is a descriptive prediction improvement on this
exposed development set, not an adoption gate or statistical generalization claim.

Freeze source/model hashes, package versions, serialization, selected examples and settings
before scoring. Create run directories exclusively, retain failures, and verify
saved artifacts and source preservation afterward. No generation, human labeling,
remote reporting, simulator replacement or GitHub publication is part of this
run. Full conversations, no-reply behavior and instructor-policy effects remain
unvalidated even if prediction loss falls.

References: [Qwen model](https://huggingface.co/Qwen/Qwen3-4B),
[MLX trainer](https://github.com/ml-explore/mlx-lm/blob/v0.31.3/mlx_lm/tuner/trainer.py),
[MLX dataset serialization](https://github.com/ml-explore/mlx-lm/blob/v0.31.3/mlx_lm/tuner/datasets.py).
