# Recording work at help and execution boundaries

Minchan approved implementation after the comparison with coding assistants:
"Let's do it." Prepare the change in the generalized
`dstl-lab/jupyterlab-ai-tutor` repository, in an isolated worktree on
`codex/request-work-logging`, starting at `7ffe89e8577f920a62caa27eb20e4aee59233b2d`.
This authorization covers implementation, local invented-data verification and a
reviewable PR. It does not deploy the extension or collect new student records.

Save the exact serialized work and effective request context on every normal
tutor request, preserving the original question separately. Generate a request ID
before dispatch and retain it on the response, failure or cancellation. Move
response logging out of React state updaters. Preserve native notebook cell IDs;
missing task/version identity remains unknown. Compute diffs from retained source
when needed; do not add a new diff store or event framework.

For code execution, use the actual outgoing kernel execute request and matching
reply/output message IDs. Completion-time cell text can differ from submitted
code. Log execution evidence separately from tutor requests: temporal proximity
does not establish causation. Existing grader text heuristics cannot establish
correctness of an entire notebook or hidden kernel state.

The finite engineering check is an invented two-request sequence with an edit
during streaming, distinct request IDs, source integrity, correct response joins,
and visible interruption handling. Execution controls must retain submitted code
when the editor changes, distinguish runs with repeated counts, and avoid binding
unrelated output. Reopening emitted records must work without a model call.

No historical benchmark is rerun. No new labels, ratings, database queries, model
requests or teammate-task changes are needed. Existing evidence stays unchanged.
This supplies future observations for a later fixed simulator comparison; passing
these controls demonstrates recording mechanics, not student fidelity or learning.

## Implementation and verification

Implemented in [generalized tutor PR #11](https://github.com/dstl-lab/jupyterlab-ai-tutor/pull/11),
commit `3843d12d98efad67113b366af3b5908b7f7d2d37`. The persistent isolated worktree is
`../tutor-request-logging`, with its separate Git store at `../.tutor-source.git`.
The PR is draft and has not been deployed or merged. The repository requires one
approving GitHub review before merge; no rule was bypassed.

The exact request object, raw typed question, SHA-256 of serialized notebook JSON,
native cell IDs, live notebook/kernel/session identities and explicit unknown
task/version fields are recorded per streamed request. Responses and failed or
cancelled streams join by request ID. Legacy summaries use the captured request
source. Logging side effects have left React state updaters. Native cell IDs also
reach the existing notebook prompt context; prompt templates/work are unchanged.

Execution observations use actual submitted kernel messages and matching reply
plus idle messages. They cover all tracked notebook views, retain submitted code
through editor changes, and mark lost observations incomplete. Grader command
detection and text verdicts remain explicitly qualified heuristics, with unknown
outcomes represented as null. A shared-view close bug found during independent
review was reproduced and fixed before commit. Retained output is a bounded text
transcript, not complete rich output or kernel state. Submitted messages can be
queued; submission alone does not prove execution.

All 20 frontend tests pass (19 new authored checks and the existing placeholder).
TypeScript compilation and alias build, changed-production ESLint, changed-file
Prettier and diff checks pass. Two independent reviews found no remaining issues.
Controls reopen serialized request records and verify source hashes and joins
without model calls. These are module/protocol checks, not a deployed collector or
live-kernel integration test. Existing package versions and lockfile are unchanged;
local Yarn 3.8.7 substituted its TypeScript compatibility patch for installation
only, then the original lockfile was restored.

Main already fails its browser-startup check with static-asset HTTP 500 errors and
a page timeout: [baseline CI](https://github.com/dstl-lab/jupyterlab-ai-tutor/actions/runs/34929387647).
The logging PR's CI must be assessed separately. Delivery is still best effort:
HTTP/network failures are reported to the browser console, without durable retry.
Received records must be inspected before treating a deployed session as usable
research evidence. No data/model requests, new human ratings or deployments ran.

The next human review is the concrete tutor PR, followed by a deliberate deployment
decision. After installation in an approved test environment, verify one invented
two-request/execution example in the actual collector before collecting a new
fixed simulator comparison. Earlier exposed examples remain closed and unchanged.
