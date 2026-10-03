# Inspect recorded evidence before fitting

The approved second step adds a separate versioned admission adapter and report.
Preserve the original authored policy, its receipts, and the distribution-only
module. Do not estimate probabilities, feed recorded rows into the sampler,
relabel old studies or inspect closed holdouts.

Validate an explicitly supplied packet of source-bound events and observations.
Keep prefix context separate from next-message outcomes and content origin
separate from coder origin and rubric. Retain partial labels, disagreements and
unknowns. Check timestamps, target isolation, declared account partitions and
exposure. Checks establish packet consistency, not source authenticity, annotation
accuracy, natural use or student eligibility.

Report candidate support per evaluation target under its original rubric. A
complete contextual joint record may be ready for protocol review; actual joint
fitting stays blocked pending a separate admission/evaluation decision. Synthetic
packets can demonstrate structural acceptance but never become empirical evidence.
Use authored examples only in this step; no private records or holdouts are read.

## Interface and definitions

`src.agents.behavior_evidence.admit(packet)` is a pure operation over a version-1
packet. It does not read files, perform semantic extraction or emit policy inputs.
The packet supplies events, cutoff/prefix/outcome references, separate context
observations and outcome annotations, and explicit development/test/reserved/
previously-exposed account inventories. Timestamp strings require a timezone.

Every event includes content origin, account/conversation, role, source reference
and SHA-256 of the exact supplied event object excluding its `sha256` key. Optional
field presence is part of that digest. Recompute from the original object, not a
schema-expanded copy. Each label independently retains coder origin, rubric,
value/unknown and supporting event IDs. An empty set means absence; null means
unknown; disagreeing judgments stay separate. No coarse work/help label is split
into a fine behavior bundle. The supported original rubrics are `help-work-v1`
and `behavior-pilot-v1-20261001`. Revision-bound feedback has a separate structural
`execution-feedback-v1` contract; this does not certify historical execution.

Validation rejects duplicate identities and malformed schema. Per-record rejection
covers source-hash mismatch, missing sources, nonrecorded content, account or
conversation mismatch, partition overlap, reserved accounts, exposed test
accounts, unordered/late prefix events, invalid target ordering/role, duplicate
targets, target-in-prefix, context citing nonprefix evidence, outcome evidence
without the target, and feedback lacking matching revision-bound execution
metadata. Temporal checks use supplied timestamps; ambiguous historical ordering
must be resolved upstream, never silently repaired here.

Per-field statuses include missing, unknown, disputed, incompatible-rubric and
exploratory-only. A compatible resolved observation with a human judgment can be
a **candidate reference under its original rubric** if packet checks pass.
Assistant-only labels never acquire that status; agreement does not manufacture
a human judgment. For feedback the required origin is instrumentation, with a
matching execution/revision field. A disagreement or rubric conflict blocks that
field while unrelated usable observations remain visible. Test records can be
candidate evaluation references but cannot be ready for joint fitting.

`accepted` means complete qualified context and fine outcome fields in the
supplied development record pass structural checks. `partial` means the record
passes integrity checks but is incomplete, exploratory or restricted to evaluation.
`rejected` means integrity/isolation checks failed. All records keep
`joint_fit.eligible = false`, with a protocol-not-established reason. Readiness
for protocol review is distinct from scientific admission. The report never
constructs a `behavior_policy.Example` or calls the sampler.

For nonsynthetic packets, `empirical_reference` identifies a candidate using
supplied recorded/human provenance; it is **not authentication, human ground truth,
independent validation, natural-use verification or permission to run a study**.
Source hashes bind supplied bytes, and cannot certify the external source or
truth of the supplied coder identity. The adapter cannot prove that the account
inventories are exhaustive, or that no undeclared exposure occurred. Student
eligibility always stays `not-assessed`. These limitations are also in the report.
A future real-data integration must verify upstream audit bindings before relying
on the normalized packet. No such integration is performed in this step.

## Synthetic example

`docs/examples/behavior-evidence-synthetic.json` is entirely invented. Its event
origin and human/instrumentation annotation fields simulate prospective records;
they do not describe actual student data or an actual human review. The enclosing
`synthetic: true` flag and `synthetic:` source references make that explicit.
Changing only that flag is rejected. All empirical-reference flags are false.

| Fixture | Result | Meaning |
| --- | --- | --- |
| complete | accepted | Assistance/material/task observations and prefix context pass structural checks; fitting is still blocked. |
| partial | partial | Material and task relation remain candidate targets; assistance is unknown and prefix context is missing. No complete bundle is fabricated. |
| leaked | rejected | The target is included in the prefix and falls after its cutoff. No target is eligible. |

Run from the worktree, using its existing sibling environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ../episode-pilot/.venv/bin/python -P \
  -m src.agents.behavior_evidence docs/examples/behavior-evidence-synthetic.json \
  --format markdown
```

Substitute `.venv/bin/python` in a normally installed checkout. Omit the format
option for JSON. Both forms print to stdout only. `report(packet)` adds input and
adapter-source SHA-256 bindings. Source references/timestamps and all annotations
remain inspectable in the output; raw event text is not reproduced. Retain the
input separately for replay. No session or saved policy receipt is created.

## Verification and boundary

The first 15 tests failed on the missing adapter, then passed. Additional tests
exposed missing visible source references and the need to reject a synthetic
packet relabeled as recorded; both were fixed. The final focused run passed
**73 tests**, including 23 adapter checks and the existing distribution, policy,
template, expression, authored-workbench and coverage regressions. One existing
Starlette/httpx deprecation warning remains. The synthetic CLI produced the three
statuses above. Hash comparison confirms that all three step-one files, the
original policy, CLAUDE.md and TASKLIST.md are byte-for-byte unchanged.

No existing private records, historical labels or closed holdout contents were
read. No database/provider calls, empirical estimation, fitting, new annotations,
UI integration, commit, push or PR occurred. Stop here for review; any fitting or
real-data normalization/admission decision is a later step.

Full Python verification passed: **1,125 passed, three skipped**, one existing
dependency warning, in 54.06 seconds. The three skipped checks require an explicit
local container image. No UI/browser/Node checks were run because no UI path
changed. Tests used the existing Python environment with bytecode/cache writes
disabled. No dependency install or network pipeline was needed.
