# Local tutor-format comparison closed

The [fixed tutor-format test](2026-09-27-local-tutor-role.md) is complete.
Every saved tutor request was evaluated once with native chat messages while
preserving exact dialogue, policy, model, seeds and output budgets. The original
JSON-format outputs supplied the baseline; candidate outputs never entered
other requests. All planned calls completed without retries or failures.

The private report records a partial reduction in literal student-message
echoes, alongside a persistent echo and contextual counterexamples involving
missing assignment content, unsupported work-success claims and invalid code.
Lower echo frequency does not establish better tutor correctness. The candidate
is not adopted as a validated tutor, and no second formatting variant is queued.
See `data/local-tutor-role-v1/REPORT.md` for private evidence and exact metrics.

Exact text equality also needs careful interpretation: a copied acknowledgment
may speak in the student's voice, while a copied answer can be nonresponsive
restatement. Neither equality nor substring inclusion is a general role-quality
classifier. Inspection observations remain distinct from human gold labels.

The authored formatter check, independent failure/deadline dryruns and tokenizer
preflight passed. The final audit verified frozen sources, native message mapping,
actual tokens, raw output decoding, settings, identity, coverage and arithmetic.
The historical cohort and diagnosis remain unchanged. No student generation,
training updates, instructor labels or default-simulator changes were added.

Continue student next-message evaluation after recorded tutor turns. For later
interactive policy work, use the intended tutor backend and check its grounding
separately; stand-in tutor failures otherwise confound student behavior. Whether
and when students send messages remains unlearned by reply-only training. This
bounded test is closed, with no further model calls or labeling queued.
