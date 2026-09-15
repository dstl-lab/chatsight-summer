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
initial commit `3843d12d98efad67113b366af3b5908b7f7d2d37`, with browser integration
and CI follow-up at `adff528fad664f1c8fd93a64b2e64a97a774a20a`.
The persistent isolated worktree is
`../tutor-request-logging`, with its separate Git store at `../.tutor-source.git`.
The PR is ready for review and has not been deployed or merged. The repository requires one
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

All 20 frontend unit tests pass (19 new authored checks and the existing
placeholder), along with both local browser tests. TypeScript compilation and
alias build, the full development extension build, changed-production ESLint,
changed TypeScript/JavaScript/Markdown Prettier and diff checks pass. Independent
request, execution and integration reviews found no remaining issues after fixes.
Existing package versions and lockfiles are unchanged;
local Yarn 3.8.7 substituted its TypeScript compatibility patch for installation
only, then the original lockfile was restored.

The new browser control runs the built plugin and a real local Python kernel.
It holds a cell running `x = 1` while changing the editor to `x = 2`; the emitted
result retains the submitted source and output `1`. A first help request captures
`x = 2`, then an edit during the scripted tutor response makes the next request
capture `x = 3`. Both snapshots retain output `1`. The check verifies nonempty
native execution/kernel/cell identities, exact request bodies, SHA-256 hashes,
response joins and the legacy initial snapshot. A review found a test route-lifetime
gap; context-level interception now persists through Galata cleanup.

This is an actual local browser/kernel integration check with invented work,
scripted tutor responses and intercepted logging uploads. It does not contact the
model or deployed collector. The ignored evidence directory
`data/episode-pilot/tutor-logging-integration-v1/` retains `observations.json`,
unit/browser/build logs, local configuration and `receipt.json` with source pins,
artifact hashes and installed versions: JupyterLab 4.6.3, Jupyter Server 2.21.0,
Tornado 6.5.8, ipykernel 7.3.0, Galata 5.6.3 and Playwright 1.63.0.

Main and the initial logging PR failed static-asset loading:
[baseline CI](https://github.com/dstl-lab/jupyterlab-ai-tutor/actions/runs/34929387647),
[initial PR CI](https://github.com/dstl-lab/jupyterlab-ai-tutor/actions/runs/34933300477).
Direct local reproduction identified Jupyter Server 2.21.0's static handler lacking
the `allowed_symlink_directory` attribute required by Tornado 6.5.9. A temporary
CI-only `tornado<6.5.9` bound restores local startup while leaving shipped runtime
requirements unchanged. It is not a production downgrade recommendation; remove
it when compatible upstream versions pass the browser check. The updated
[PR CI](https://github.com/dstl-lab/jupyterlab-ai-tutor/actions/runs/34934925819)
passes build, isolated installation, browser integration and link checks at
`adff528`; the release and PR-title checks also pass. All six GitHub checks are
green. CI result receipts are saved beside the local evidence. The PR is ready for
the required approving GitHub review; no branch protection was bypassed.

Minchan asked whether this adds reply latency. The current request path serializes
and copies the request and awaits a notebook checksum before tutor dispatch.
Logging uploads run asynchronously, but CPU and network overhead remain possible.
No latency benchmark has run. Measure request-to-first-token delay with
representative notebook sizes and connections before deployment.

Delivery is still best effort:
HTTP/network failures are reported to the browser console, without durable retry.
Received records must be inspected before treating a deployed session as usable
research evidence. No data/model requests, new human ratings or deployments ran.

The next human review for this logging work is the concrete tutor PR, followed by
a deliberate deployment decision. After installation in an approved test
environment, verify one invented two-request/execution example in the actual
collector before using newly collected observations in a simulator comparison.
Minchan subsequently clarified that main-flow simulator development must use the
existing data now, independently of this PR and the next quarter. Earlier exposed
examples remain closed and unchanged.
