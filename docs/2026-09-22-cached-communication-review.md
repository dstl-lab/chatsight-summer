# One common-rubric pass over existing communication

This pass is complete and closed. See the
[result and stopping decision](2026-09-22-cached-communication-results.md).
The preparation protocol and handoff record below remain historical.

**TL;DR:** Minchan's Continue advances the completed
[inventory](2026-09-22-cached-fidelity-scope.md) to its specified review: eight
conversation cases, 23 distinct messages, two yes/no/unclear flags each. Reuse
the portable review page. Generate nothing. After one returned pass, report the
measurement coverage and observed discrepancy, then close even if inconclusive.

## Preparation and handoff

Reuse the exact `help-work-v1` definitions and the verified original prefixes,
first recorded follow-ups and sixteen cached replies. Show the shared context
once per case and each distinct message once. Both generated occurrences of the
identical case-5 reply share one judgment and retain both weights in the report.
The reviewer receives no original IDs, origins, old labels, source mapping or
duplicate weights. Private random ordering/opaque IDs are frozen before handoff;
the eight case order and the candidates within each case are shuffled once.
This cannot undo prior exposure or guarantee that origins cannot be guessed.

The existing `communication_review` builder provides browser-local drafts,
explicit previous-exposure reporting, uncertainty notes and JSON export. Serve
only the generated `ui/` directory on localhost; the source mapping, receipts and
scripts stay outside it. Nothing is submitted automatically or sent to a model.
Check draft/export behavior with the existing authored automated test, verify the
saved page's exact contents and local HTTP access, and leave real reviewer details
and judgments blank. Preserve all old studies and exports. Browser automation
blocked opening a temporary authored test file; do not rehost that test or use
another browser surface to bypass the restriction. Provide the real review link
for the user's own browser; no live browser walkthrough is claimed.

## Report rules fixed before judgments

One small private aggregation reuses the existing packet/field validators. Neither
existing scorer matches this one-condition/two-draw design, so their inputs and
historical code stay unchanged. No production simulator or UI change is needed.

- Require the exact packet/rubric, all 23 unique message IDs, reviewer identity
  and previous-exposure answer. Both flags can be yes. Null means an unfinished
  draft, not no; unclear needs a note. Preserve the original returned bytes and
  verify the frozen page, source mapping and report code before intake.
  If the reviewer stops early, preserve the partial export and mark the report
  incomplete, retaining missing counts without requiring another review. Partial
  flags do not enter comparable-case scores; missing is never inferred as no.
- Report yes/no/unclear/missing counts separately for eight reference occurrences,
  sixteen generated occurrences and 23 unique coded messages. Shared coding does
  not erase a repeated draw. Retain all case IDs and explicit exclusion reasons.
- For each flag independently, a case is comparable only when its reference and
  both generated draw flags are yes/no. Unclear help does not exclude clear work.
  For a comparable case, `p = (yes_draw_1 + yes_draw_2) / 2`; report `p`, reference
  flag, `p - reference`, and `(p - reference)^2`. Average equally across the
  comparable cases for that flag. Do not silently use a denominator of one draw.
- Report reference work-absent, work-present and unclear coverage independently
  of generated labels. Help-only requires help=yes/work=no; neither still belongs
  to work-absent. Report joint category counts only where both flags are known,
  retaining unclear counts separately. Do not force primary-action categories.
- For work, also report the mean discrepancy and Brier error separately within
  comparable work-absent and work-present reference groups. Balanced work Brier
  is half the sum of these two group means, available only if each comparable
  group is nonempty. Otherwise report unavailable and the exact missing coverage.
  An always-no-work flag rule scores 0.5 when both groups exist; include this
  diagnostic comparison without treating that rule as a message generator.
- Publish no combined success threshold, condition comparison, confidence or
  significance claim, coding-reliability estimate, or adoption decision. Two draws
  are coarse development samples. Flag agreement cannot prove contextual
  appropriateness, calibration, notebook actions or overall student realism.

## Stop

This is one human pass with a hard ceiling of **23 messages / 46 flags**, followed
by one report. No extra plausibility checks, second-reviewer dependency, replacement
cases, rerolls or model-filled labels. Missing group coverage closes the diagnostic
as inconclusive. The earlier studies remain closed; this separate pass is not
pooled into their results and cannot establish a grounding benefit.

Preparation and verification are stored in ignored
`data/episode-pilot/cached-communication-review-v1/`. Only this scope, task status
and aggregate verification enter Git. The next required input is the completed
human review export; no new generations are queued.

## Prepared handoff

The page is available at `http://127.0.0.1:8425/`; only `ui/index.html` is served.
The saved page matches its generated bytes exactly. Requests for the source
mapping and blank form, including parent-directory paths, return 404. Existing
workspace servers are untouched. No real reviewer identity or judgment was entered.

Preparation replay verifies 50 frozen files and all eight reference/sixteen draw
joins, with 23 unique messages and 46 blank flags. The existing authored review
test passes for text preservation, draft recovery, both-yes answers, required
uncertainty notes and export. A separate authored arithmetic check passes for
unequal reference groups, duplicate weighting, partial forms, per-flag exclusions,
unavailable balanced scores, malformed intake and create-only report output.
These are offline/content/connection checks, not a live browser walkthrough.
Independent audit confirms all 50 pins, 36 visible prefix turns, source texts,
shuffled opaque IDs, duplicate weights, blank form and the frozen report rules.

After entering reviewer details, code the two questions for each message. Use
**Finish review → Copy answers** and return the JSON. **Copy draft** preserves
unfinished work if the reviewer needs to stop; it does not silently fill answers.

Reproduce the preparation and authored report check from the worktree:

```sh
PYTHONPATH=. .venv/bin/python data/episode-pilot/cached-communication-review-v1/prepare.py
PYTHONPATH=. .venv/bin/python data/episode-pilot/cached-communication-review-v1/check_report.py
```

The first command replays this frozen page without changing its order or sources.
The preparation record retains the original protocol snapshot; this handoff
addendum documents verification and does not change the report rules.
