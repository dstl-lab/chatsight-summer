# Inspect delivered tutor instructions in the browser

Continue the accepted browser workflow by exposing the existing Saved results
renderer for the selected notebook encounter or conversation. It distinguishes
confirmed policy delivery, supplied replies without a confirmed policy link,
configured but unused lesson policies, and incomplete/failed exchanges. Keep
the current editable draft separate. Reuse existing receipt interpretation;
do not introduce a second policy-attribution implementation.

Show results in center details with chat alongside. Bind results to the selected
saved encounter, clear on failed loads, escape active markup and omit raw runtime
diagnostics. Browser reads must stay within known receipt paths and must not
follow symlinks. No provider calls, code execution, new labels, or evidence edits.
Verify authored policy/manual/unused/failure cases, selection and source safety,
then inspect the actual desktop browser and run existing contributor checks.

The user also requested a subagent improve the chat interface. Limit this to
readability, role hierarchy, spacing and useful existing-content navigation in
the right sidebar. Keep exact source access, independent scrolling, comparison
context boundaries, draft preservation and keyboard access. No new chat framework,
engine controls, synthetic conversation or mobile design work.

## Result

Saved results is now available in Replay for each verified encounter. It reuses
workspace_history under the existing shared read lock and keeps its established
policy/reply/result matching. The browser adds restricted HTML presentation,
diagnostic redaction, and guards for symlinks in receipt folders/files. The
Marimo reader's default output remains unchanged. Missing tutor metadata warns
without hiding valid student steps or falsely attributing a policy; interrupted
student replay still fails closed instead of offering partial continuation.

The center details explicitly label the full task/conversation history, including
exchanges after the selected playback state. Chat continues to show that state;
closing details restores focus to Saved results. Compare keeps its separate
review workflow. Drafts remain independent from recorded instructions.

The requested UI subagent used craft and cognitive-load guidance to refine role
hierarchy, student message backgrounds, source access and spacing. Message counts
and First/Last buttons navigate only the sidebar; source inspection highlights
its message and restores focus/scroll on close. Existing origin labels and
comparison prefix boundaries are retained. No new dependencies were added.

Validation: 544 Python tests pass with three optional container skips; both
Marimo checks and all three Node checks pass. Coverage includes saved versus
draft policies, unused lesson policy, errors without raw diagnostics, known-path
symlinks, encounter isolation, source escaping, navigation and disabled states.
Independent backend review found no blockers. Desktop browser checks verified
chat navigation/source focus, comparisons, saved policy history and notebook
edit/check/no-reply history with chat visible and no page overflow.

All 29 private conversation scenarios reopen (two have confirmed policy links,
none have receipt warnings), and the notebook preview shows its three saved
steps. All 20 comparison, 105 chat and five notebook evidence files are unchanged;
local audit: ignored `data/browser-saved-results-verification/`. Both previews
remain read-only. No provider calls, execution, labels or new fidelity evidence.

## Teammate handoff

The quickstart now leads with the existing fictional chat_demo and dedicated
browser collection command. Both authored policy branches reopen with their saved
instructions: A exhausts its budget and B chooses no reply. The walkthrough needs
no credentials, private inputs, Docker or model calls. Direct endpoint checks
verified both outcomes, disabled sending, unknown notebook work and unchanged
files. The separate Marimo policy-pair comparison remains optional; its folder
is not compatible with the browser's cached-research-review option.

Consolidate browser PRs #49–56 into #48 under the user's standing merge approval,
preserving all source commits and independent review requirements for main.
The UI increment is complete; integration and teammate reproduction take priority
over adding another screen or reopening closed labeling/generation studies.
