# Marimo direction and the next observation check

PR #25 merged into main as `35ae189` on September 15. Work continues on
`codex/observation-contract` in the existing isolated worktree, preserving the
private evidence and historical source paths.

## UI direction

Minchan selected **Marimo for the eventual simulation workspace**, with readable
Python source and diffs as the motivation. Its notebooks are stored as Python
files, can run as scripts or apps, and use reactive execution. The runtime can
also mark dependent cells stale instead of automatically running them.
[Official documentation](https://docs.marimo.io/).

This choice concerns the future educator/researcher workspace. A source-file diff
does not itself record when a student edited, asked for help, or requested a check.
The interface needs to preserve those distinctions, including user-requested
execution versus reactive execution. Existing saved runner operations already
provide bounded requests and replay; reuse them when building the UI, so an
interface refresh cannot silently become another model request or student action.
This is an integration requirement, not a claim that a Marimo adapter exists.

The cozy visual direction remains a later product decision. This step installs
no dependency, builds no interface and converts no historical dataset.

## Existing bindings and unresolved evidence

| Observation | Existing simulator | Retained historical evidence |
|---|---|---|
| Session/task context | Manifest and state hashes bind supplied task/activity and branch | Learner/notebook grouping and event IDs; same-question/version identity unverified |
| Work change | Selected cell source, revision, before/after work in action history | Initial captures and later eligible captures; no persistent cell IDs in inspected notebooks |
| Tutor context | Supplied/generated reply bound to saved state; existing text diff export | Matched first exchange plus some later event metadata; incomplete work state at later turns |
| Check result | Source/revision, activity, runtime and evaluator bindings | Observed grader fields without a verified executed-source binding in the inspected records |
| Ordering | Ordered operation receipts, call timestamps and replay | Server event order/time; incomplete links and unknown intervening actions |

Implementation references: `src/agents/notebook_student.py` (`create`, `step`),
`src/eval/notebook_session.py` (`advance`), `src/eval/notebook_runtime.py`
(`_binding`, `require_current`), and `src/agents/tutor_context.py` (`snapshot`).
These mechanisms support the current selected-cell runner; they are not a
complete multi-cell identity or real-session observation contract.

## Bounded source-discovery result

A read-only search of six plausible local project folders found readers and
transcript parsers, but not the tutor event emitter or its deployed version:

- The sibling ChatSight `server/python/main.py` (lines 90–134, 341–368) queries
  tutor query/response events. `queue_service.py` (874–917) reconstructs turns.
  Their derived message indices are not emitted notebook/cell revision IDs.
- ChatSight MVP's `src/App.tsx` (49–87) extracts code from imported transcript
  sections. That parser is not evidence of a live notebook logger.
- The inspected analysis project parses transcripts; the generic chat project
  models conversations/messages. The remaining candidates concern a Sheets
  downloader and unrelated car telemetry.

These are local source findings, not a verified deployment audit. No sibling
source was edited, no credentials were opened, and no database or model request
was made. The emitter may exist elsewhere; its bindings remain unverified.
Source locations and hashes are retained privately under
`data/episode-pilot/observation-contract-v1/`.

The next useful evidence is one recorded example with task/version, work revision,
tutor boundary and execution bindings, checked against the actual logger version.
If that cannot be reconstructed, identify the specific missing event or field
before proposing instrumentation. A new label taxonomy would not supply it.

## Team explorations and verification

The [two informal teammate briefs](2026-09-15-teammate-explorations.md) split this
into independent questions: recoverable real student activity, and a useful
Marimo simulation workspace. They are drafts to share, not assignments sent to
anyone or new automated coding tasks.

The new branch starts from the exact merged tree. Its baseline passed 371 Python
tests with two optional container tests skipped and one upstream deprecation
warning. This change adds documentation only; no simulator behavior, receipt
format, classifier or completed benchmark changed.
