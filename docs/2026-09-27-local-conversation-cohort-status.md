# Fixed local conversation evaluation complete

The [frozen conversation evaluation](2026-09-27-local-conversation-cohort.md)
is closed. All remaining eligible starts from the earlier selection were used,
with no replacements, further training, prompt changes or human labeling.
The existing chat engine ran the starting local model and saved student adapter
against the same base tutor and policy, preserving separate histories.

Every planned arm reached its decision budget. Every call ended at EOS; none
required a retry or was lost to a cap, failure or deadline. These budget stops
are not observed student decisions to stop communicating.

The private report preserves coverage, exact repetition, whitespace sensitivity,
length strata, pooled and conversation-weighted lengths, paired first-reply
length errors, missing-slot bounds and every planned case. It distinguishes
aggregate changes from their per-case concentration. The earlier prediction
score remains separate; no composite fidelity score or model winner is claimed.
Results, actual prompts, tokens and replayable sessions remain under
`data/local-conversation-cohort-v1/`; start with its `REPORT.md`.

The authored offline check and nine focused existing tests passed before the
source freeze. An independent post-run audit verified source/model/adapter
hashes, fixed selection, settings and paired seeds, raw token decoding, exact
branch histories, tutor bindings, bounds and report arithmetic. Earlier closed
artifacts remain unchanged. The existing read-only browser can open either
saved branch of any case without generating another reply.

The cases remain development-exposed conversation scenarios, not a sample of
identifiable learners. This response-only model does not establish message
timing, silence, notebook activity, learning or real tutor-policy effects.
The default simulator remains unchanged. Next, diagnose the saved repeated
sequences and limits of response-only training before proposing another model
change; no new labeling or generation round is queued.
