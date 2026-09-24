# Recorded sequences panel

The question view uses a **student-question journey** as its unit, never an
isolated student message.

## What a row means

Each row groups complete journeys with the same recorded shape around tutor
use:

1. Events before the first tutor question.
2. The tutor question and reply.
3. Events after the first tutor reply.

For example:

> Error or failed autograder check → ask tutor → tutor reply → notebook edit,
> no exact tutor-code insert or paste

Membership is computed from ordered event records. Student-message wording and
LLM classifications do not determine the group.

## How message text is used

Message text is evidence inside a selected sequence group. The Overall panel
shows the messages associated with journeys in that group. The Student panel
shows one student's complete ordered trace, including the student message,
tutor reply, notebook actions, errors, and checks when those records are
available.

This prevents a message such as “is this right?” from being presented as a
standalone intent label. Its surrounding work remains visible.

## Evidence boundary

- The question ID is the notebook context recorded on the events, not semantic
  proof that every message refers only to that question.
- A sequence that starts after a passing check is not automatically a
  “verification” request.
- A sequence with no later edit does not prove the reply was ignored.
- The interface reports recorded behavior and leaves interpretation visibly
  connected to the underlying sequence.
