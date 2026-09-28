# Student evidence summarized; hybrid exchange complete

The [separation protocol](2026-09-28-student-tutor-separation.md) now has an
offline evidence summary and a completed integration check. After exact-payload
approval, one Gemini tutor request and one local trained-student reply completed.
No additional training or human labels were needed.

The private `data/conditional-student-evidence-v1/REPORT.md` keeps the earlier
recorded-response prediction results separate from first generated replies
conditioned only on recorded dialogue. It excludes the original demonstration
and later model-to-model turns. Prediction improved after training; generated
lengths moved toward the recorded distribution, with uneven case-level changes
and substantial sensitivity to one case. These diagnostics do not establish
student fidelity, whether students would reply, or instructor-policy effects.
Existing closure hashes, exact input joins and recomputed arithmetic verify.

The private `data/hybrid-student-tutor-v1/` reuses the existing chat engine and
frozen local worker. It replayed one saved trained-student message, delivered one
Gemini tutor response, and generated one new local trained-student reply.
Explicit callbacks and separate role identities prevent the mixed session label
from being used as a provider model ID. Exact transcript serialization is retained.

Authored offline checks cover history, routing, budgets, worker validation,
failure stops and refusal to resend. Independent review verifies frozen sources,
the seeded session and exact prepared/runtime tutor prompt equality. The provider
worker uses one SDK attempt rather than the repository wrapper's four attempts.
Both new calls completed at their message boundary without retries, failures or
token caps. Saved local tokenization, decoding, adapter identity and settings
verify. Independent saved-result review also verifies approval binding, the raw
provider response, exact role histories, source pins and engine replay. The
existing read-only browser displays the complete exchange and its
budget stop. No application default or browser sending mode changed.

Automatic approval review initially rejected dispatch before execution because
the earlier approval covered a different private payload. The user's subsequent
specific approval is bound to this prepared request in `approval.json`; the
earlier rejection remains in `approval-block.json`. Exact prompts, raw provider
response, per-role identities, usage and engine receipts remain private alongside
`REPORT.md`. The student continued requesting the code's result. That is an
observation of one generated reply, not a fidelity judgment or a policy effect.

The fixed decision budget is exhausted. The last student message is unanswered
because this check ended, not because the model learned silence. Whether and
when students message remains unlearned by reply-only training. This establishes
the trained student's connection to the intended tutor backend, while the
recorded-tutor evidence above remains the separate student evaluation.

Both sets of artifacts remain local and ignored. This bounded step queues no
additional experiment, labels, training or public release.
