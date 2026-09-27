# Local student training pilot completed

The [fixed pilot](2026-09-27-local-student-training.md) completed its training
budget and saved a candidate adapter. The final adapter was reloaded and scored
against the same development references as its unchanged starting model. No
parameters, examples or checkpoint choices were changed after model scoring
started. Private metrics, exclusions, receipts and the model artifact remain in
ignored `data/local-student-training-v1/`; `REPORT.md` summarizes the result.

The new `src.eval.student_training` helper preserves exact student target text,
keeps tutor replies in the input transcript, and corrects the installed MLX loss
mask's padding boundary. Six focused tests pass; an actual MLX synthetic check
confirms target counts, gradients and mask invariance. Authored receipt checks
reject contradictory failures and changed preparation. Saved calculation and
source-preservation checks pass.

Before model scoring, independent review identified the advisory nature of MLX's
memory setting and a receipt-binding gap. The initial preparation was preserved;
the corrected preparation retains identical examples and tokens, adds memory
checks after updates/scored examples, and binds completion to its initial hash.
The private amendment records this correction. The frozen plan is unchanged
since execution began.

This produces a locally trained candidate and a conditional prediction comparison.
It does not validate generated conversations or replace the Gemini simulator.
The next distinct milestone is a bounded conversation using the saved candidate;
that requires its own fixed generation settings, not further training or another
labeling queue. No such run is started or queued here.
