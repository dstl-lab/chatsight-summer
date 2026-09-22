# One-case held-out continuation walkthrough

## Decision before implementation

The common observation contract shows that current historical exports provide
conversation turns but not revision-bound notebook work or checks. The next
milestone therefore tests only the behavior those exports actually observe: one
student message after a tutor response.

Select one eligible tutor boundary deterministically from the local snapshot,
without ranking target meaning. Keep at most the last eight visible turns ending
at that tutor response. Save the immediate recorded student follow-up separately
as the reference. Reuse the unchanged `student_continuation` prompt and schema,
the saved chat runner, Gemini 2.5 Pro, and its durable pending/completed receipt.
Make one request.

The user approved this exact next-milestone flow after it was described as choosing
a real tutor boundary, hiding the actual next response, sending only the approved
prefix to Gemini, generating once, and comparing with the hidden response. The
repository also records standing Gemini approval. Preserve the scoped request,
source hashes and result under ignored `data/`.

This is an exposed development walkthrough, not a new baseline. Earlier work
already contains larger historical continuation comparisons. Do not call this
case pristine, student-separated, representative, an accuracy estimate, or an
improvement over the existing generator.

## Isolation and persistence

Preparation creates three separate artifacts:

- a saved chat session containing only the visible prefix;
- a reference file containing the immediate recorded next student message; and
- a manifest binding the selector, source, prompt and reference hashes.

Changing the hidden target must not change case selection, the visible query or
the model prompt. The session is initialized before generation. Its existing step
runner writes a pending receipt before the provider call and refuses automatic
resend after interruption.

After one successful response, build the existing recorded/generated behavior
review structure with blank human judgments. The comparison page reveals origins
because this walkthrough explains the mechanism; it does not collect a blind
rating. A recorded response is one observed outcome, not the only valid response.

## Interface and stopping rule

Add a read-only Marimo comparison page showing the shared prefix, recorded next
message, simulated next message or no-reply disposition, and saved provenance.
Opening or reloading it must make no provider call and change no files.

Stop after one request, one saved comparison and offline verification. Do not tune
the prompt, reroll the case, add notebook claims, assign labels, or calculate an
accuracy score from this example. The next research decision must use the already
available larger evidence rather than treating this walkthrough as validation.
