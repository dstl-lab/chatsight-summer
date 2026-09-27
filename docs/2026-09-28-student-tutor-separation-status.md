# Student evidence summarized; hybrid exchange prepared

The [separation protocol](2026-09-28-student-tutor-separation.md) now has an
offline evidence summary and a prepared integration check. No additional
training, human labels or model calls occurred in this step.

The private `data/conditional-student-evidence-v1/REPORT.md` keeps the earlier
recorded-response prediction results separate from first generated replies
conditioned only on recorded dialogue. It excludes the original demonstration
and later model-to-model turns. Prediction improved after training; generated
lengths moved toward the recorded distribution, with uneven case-level changes
and substantial sensitivity to one case. These diagnostics do not establish
student fidelity, whether students would reply, or instructor-policy effects.
Existing closure hashes, exact input joins and recomputed arithmetic verify.

The private `data/hybrid-student-tutor-v1/` reuses the existing chat engine and
frozen local worker. It replays one saved trained-student message, prepares one
Gemini tutor request, and permits at most one new local trained-student reply.
Explicit callbacks and separate role identities prevent the mixed session label
from being used as a provider model ID. Exact transcript serialization is retained.

Authored offline checks cover history, routing, budgets, worker validation,
failure stops and refusal to resend. Independent review verifies frozen sources,
the seeded session and exact prepared/runtime tutor prompt equality. The provider
worker uses one SDK attempt rather than the repository wrapper's four attempts.
No application default or browser sending mode changed.

Automatic approval review rejected dispatch before execution because it treated
the earlier approval as covering a different ten-turn private payload. The exact
eight-turn payload, destination, schema, model and limits are prepared in
`DISCLOSURE.md`, `scope.json` and `tutor-call/request.json`; the actual rejection
is preserved in `approval-block.json`. No dispatch or worker marker exists, and
no private text was sent. Specific approval of this payload is the only remaining
input for the single exchange. Success would establish connectivity and replay,
not a student-fidelity improvement or a tutor-policy result.

Both sets of artifacts remain local and ignored. This bounded step queues no
additional experiment, labels, training or public release.
