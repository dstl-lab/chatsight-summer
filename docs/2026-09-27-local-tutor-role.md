# Isolate local tutor message formatting

The closed repetition diagnosis found exact student-message echoes in generated
tutor replies. Test one candidate representation against all 52 saved tutor
requests from that cohort, preserving the student histories as fixed inputs.
This is a development diagnostic selected after inspection, not an independent
tutor-quality benchmark or a new student rollout.

Reuse the completed original tutor outputs as the baseline. For the candidate,
put the existing tutor instructions and unchanged policy in a system message,
map each supplied student turn to `user` and tutor turn to `assistant`, then append
the exact pending student message as the final `user` turn. Preserve all text,
turn order and consecutive same-role turns. Omit the old JSON wrapper and origin
metadata. This changes representation and instruction placement together; it
does not isolate a single token or prove which part causes a difference.

Run the unchanged base model without an adapter. Reuse each original request's
seed, 384-token output cap, temperature .7, top-p .8, top-k 20 and disabled
thinking. Reuse the frozen worker with only its allowed receipt root redirected.
Keep the 4,096-token prompt-plus-output and 16 GiB bounds. Freeze request mapping,
source hashes, candidate formatter and authored check before generation.

Use the cohort's case order, starting-student arm then trained-student arm, and
tutor positions one then two. At most 52 new local tutor calls, no student calls
or training. Allow 120 seconds per call within a 20-minute total deadline. No
retry, replacement, truncation or second formatting variant. Retain every failed,
capped, blank or unstarted request in the report; do not count it as an improvement.

Report coverage, all stopping reasons, and full exact equality of each tutor
output to its pending student message across the full planned set and paired
accepted outputs. Distinguish literal substring inclusion from exact echoes;
short identifiers or quotations make substring inclusion unsuitable as an error
rate. Report response lengths descriptively and inspect the previously echoed
requests in context, without inventing a semantic quality score.

Verify native prompt tokens, raw output decoding, model identity, sampling
settings and source integrity. The earlier baseline is not regenerated, so this
is a saved-run comparison with fixed recorded settings. Keep both old and new
receipts. Fewer exact echoes alone cannot establish tutor correctness, student
fidelity or a beneficial policy effect. Close after this one candidate; leave
the default simulator unchanged and do not reopen instructor labeling.
