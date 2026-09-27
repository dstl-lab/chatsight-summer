# Separate student evidence from tutor integration

Keep conditional student evaluation tied to recorded tutor turns. Summarize the
already completed prediction comparison and the fixed cohort's first generated
replies separately from its later model-to-model exchanges. Reuse the original
cases and references; do not create new labels, sampling, training or scores that
combine the different populations. This is a read-only synthesis of saved evidence.

For the next integration check, reuse the first trained-student message from the
original local demonstration, selected by the earlier frozen hash order. Create
a separate session from its exact recorded prefix and replay that single saved
student output. Leave every original session and experiment unchanged.

Allow one new tutor request through the repository's configured interactive
Gemini model, `gemini-2.5-pro`, using the unchanged chat tutor prompt and policy.
After an accepted tutor reply, allow one new local trained-student message using
the original exact transcript serialization, adapter and worker. This is a
functional integration check, not evidence of tutor quality, student fidelity,
silence, notebook execution or instructor-policy effects.

Use explicit callbacks for both roles. The legacy session model field will be a
descriptive mixed-routing label, never an API model ID; save authoritative tutor
and student provider/model identities separately. Capture raw state before the
engine call and the actual tutor reply in its callback. Never reconstruct student
history from the line-oriented harness prompt or read the session while its
student callback holds the lock. The existing read-only viewer may open the result;
do not enable generic browser sending for this mixed session.

Prepare the exact Gemini prompt, schema, policy, destination, model and bounds
before any external call. Only dialogue text, origins, the pending saved student
message and tutor policy enter that payload; no future recorded target, dataset
identifier, notebook contents or training weights are included. Preserve any
required external-send approval separately from behavior judgments.

Reuse the provider's structured-response configuration with an explicit single
SDK attempt, 120-second request timeout and 8,192-token output ceiling. Do not use
the repository's four-attempt wrapper. Preserve the raw provider response and
require one complete STOP candidate with a nonblank schema-valid tutor message.
Cap the whole dispatch at six minutes; interruptions or uncertainty are not
retried. A failed tutor stops before local student generation.

The local student uses the saved adapter, seed 20260928, temperature .7, top-p .8,
top-k 20, disabled thinking, 256 output tokens and the existing 4,096-token context
and 16 GiB limits. No truncation, fallback or retry. The session has two decisions:
one replayed saved message and at most one new local message. Preserve separate
call counts for replay, external tutor and new local student. Stop after that
exchange; no additional conversation, experiment or training run is queued.

Before dispatch, run an authored callback/routing/failure check with fake providers
and verify frozen source/model hashes. After a successful run, verify exact engine
replay, the tutor-to-student history join, actual model identities and local token
decoding. New local code and documentation stay on the isolated worktree; private
inputs and outputs remain ignored, and publication is not part of this step.
