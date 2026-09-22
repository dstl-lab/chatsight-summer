# PR #47 integration assessment

## Decision

Reuse the policy-comparison backend in the existing browser workspace after the
findings below are fixed. Keep Marimo apps as optional research utilities; do not
replace the accepted browser shell or add another copy of conversation replay.
This assessment does not merge PR #47 or run a new experiment.

Reviewed [PR #47](https://github.com/dstl-lab/chatsight-summer/pull/47), whose actual
head is `codex/marimo-replay-viewer` at
`4d7c2a8abfd352cf01c06fecfeb909424addb18c`, against browser PR #48 at
`27a20f319679375a477dbd335e193d27821c9794`.
The review and temporary merge used the separate `policy-labs-integration`
worktree on `codex/policy-labs-integration`.

## What it contributes

| Capability | Relationship to our workflow |
|---|---|
| Discover eligible saved starts and freeze numbered A/B runs | Reuse `policy_comparison_setup`; both arms receive the same cached student question and fixed, distinct tutor policies. |
| Run each untouched arm once and reopen its outcome | Reuses our existing `chat_policy_pair` engine; preserve failed/interrupted runs and duplicate-run protection. |
| Run 1–24 independent cases with bounded concurrency | `policy_cohort` generalizes the existing three-case coordinator. Defer browser batch controls until single-pair inspection is sound. |
| Inspect one recorded/generated continuation | Useful research diagnostic after receipt verification is fixed; a new saved format requiring its own browser projection. |
| Inspect notebook actions and observation packets | Reuse verified projection where needed; keep browser locking, provenance, and path restrictions. No second replay panel. |

The new cohort runner overlaps with `chat_cohort`: both build on
`chat_policy_pair`. Keep the old runner unchanged for its frozen three-case
protocol. Avoid adding a third orchestration layer. Before exposing larger
cohorts, decide and document conversation deduplication, model consistency,
receipt pinning, and dispatch order; the old coordinator enforced constraints
that the new one does not all preserve.

## Findings to resolve before adoption

All references below describe the pinned PR head, not the current browser branch.

1. **Saved continuation validation can be bypassed.**
   `src/eval/heldout_continuation.py:139–147,191–203` reads a completed response
   and hashes the receipt without replaying its request. In an authored
   reproduction, changing `receipt.request.prompt` before finalization made
   `chat.show()` reject the session, but both `finalize()` and `load()` accepted
   it. Reuse the existing verified chat loader under a read-only lock.
2. **Cohort failure classification depends on message content.**
   `src/agents/policy_cohort.py:124–126` searches rendered history for
   `incomplete`. A saved tutor failure under the policy “Ask questions when the
   work is incomplete.” is counted as incomplete instead of failed. Derive
   lifecycle status from receipts, not policies or message text.
3. **An unrun starting question is displayed as a new follow-up.**
   `apps/policy_simulation_lab.py:183–215` looks for the starting student question
   only in dialogue, then treats every pending message as a generated follow-up.
   A freshly frozen arm has its cached starting question in `pending_message`,
   one decision remaining, and no generated student turn in dialogue. The app
   therefore reports the starting question missing and mislabels it as a result.
   Reuse the ready-state distinction already present in the setup/cohort apps.
4. **Request counts describe logical calls as provider attempts.**
   `src/eval/heldout_continuation.py:157` and
   `src/agents/policy_cohort.py:198` count one or four logical calls, respectively.
   The default retry wrapper allows four adapter attempts per logical call.
   An authored three-attempt retry still reports one provider request.
   Name logical requests accurately and record attempts separately or mark them
   unmeasured. The cohort UI must not promise four total provider attempts/case.
5. **Read-only observation inspection can write to the input session.**
   `src/eval/observation_contract.py:107` uses the append/create lock helper.
   Inspecting a freshly created notebook session creates `.lock`. Apply the
   browser's read-only locking convention and handle missing locks explicitly.

Additional integration concerns: `run_both()` catches every ordinary exception,
including errors without a saved failure receipt; preserve or surface those
errors as the existing three-case runner does. The cohort UI reads shared
context only from arm A, losing the displayed context if A fails while B remains
valid. Source-origin content may be authored; it should not automatically be
called recorded student evidence.

## Smallest browser integration

1. Fix and regression-check the findings in the affected shared helpers/apps.
2. Add saved policy-pair inspection to the existing Compare area using an
   explicitly typed projection. The current `--comparison` option accepts a
   closed communication-review bundle, not a policy-pair directory.
3. Reuse `freeze_next` and the existing bound pair runner for an explicit
   “Compare tutor policies” action: choose a saved eligible start, enter the
   current and proposed instructions, and save one new paired run.
4. Show the common starting context once. Compare each policy's tutor response
   and subsequent simulated student outcome; distinguish ready, failed,
   interrupted, replied, and no-follow-up. Keep the single chat view.
5. Add batch execution only when a fixed multi-case comparison is needed.

Browser adapters must preserve startup-pinned evidence, safe file selection,
symlink refusal, read-only snapshots, and escaped rendering. The Python helpers
accept local paths and are not themselves an HTTP trust boundary.

## Research meaning

This is progress toward instructors trying alternative tutor instructions. It
does not by itself improve or validate simulated-student fidelity. Eligible starts
contain supplied conversation context plus a cached **simulated** question;
these are not a random sample of real pending student requests. The packaged
current-policy text is a summary of a pinned tutor configuration, not verified
deployment instructions. A reply/no-follow-up difference is a simulated outcome,
not evidence of learning, real policy effects, or a response probability.

The one-case continuation keeps its reference out of the ordinary generation
path, but remains an exposed development case conditioned on an observed reply.
It is not a new representative holdout or an accuracy estimate. No new manual
labeling, closed-study rerun, or provider run is needed for this integration.

## Compatibility checks

- Temporary local merge: only `.github/workflows/tests.yml` conflicted. Resolve
  by retaining all seven Marimo app checks and all three browser/review Node
  checks. The teammate quickstart auto-merges but needs final workflow wording.
- Combined tree: **573 Python tests passed, three optional tests skipped**;
  all seven Marimo checks and all three Node checks passed.
- Independent backend/evaluation reviews and authored local reproductions found
  the gaps above despite the passing suite. Concurrent submissions to one pair
  produced exactly one tutor and one student call per arm with mocked callbacks.
- No private data, live provider calls, notebook execution, or new labels were
  used. Existing browser previews and saved runs were not changed.
- The temporary merge was aborted after validation. This branch commits the
  assessment only; PR #47 and PR #48 remain unchanged by this review. Passing
  compatibility checks are not approval to merge the identified bugs.
