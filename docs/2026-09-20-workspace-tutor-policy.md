# Tutor-policy continuation and the intended workspace

Minchan clarified the end interface: a notebook-focused VS Code/Cursor-style
workspace, with notebooks on the left and the student–tutor conversation on the
right. The instructor configures support and observes the simulated student's
work and dialogue together. Keep Marimo as the current prototype and preserve
the preference for readable notebook source/diffs; the final application shell
is a later implementation decision. Defer the layout overhaul for now.

Continue with a smaller functional gap: an optional policy-driven tutor reply in
the existing workspace. When the student requests help, a researcher can edit a
tutor policy and explicitly generate one tutor reply followed by one student
decision. Manual tutor replies remain available. Quiet work, chosen silence and
the existing decision budget retain their meaning; do not force a chat response.

Reuse `notebook_tutor.respond`, its saved context/receipt, and the current runner.
The UI's displayed binding must match before any dispatch, including the context
actually prepared by the tutor helper. Use one create-only exchange directory per
displayed state so a duplicate or interrupted request cannot automatically resend.
Keep policies and generated replies in the existing exchange receipt. Opening,
refreshing and editing a policy make no model request. No new labels or changes
to either generator prompt, core engine or old frozen evidence are required.

Verify exact policy/context delivery, one tutor plus one student decision, stale
and duplicate refusal, interruption, and offline reopening with authored adapters.
This is an operational improvement, not a behavioral experiment or a claim about
policy effectiveness. Stop this increment at a working, tested control and PR.

## Use

Launch the [existing workspace](2026-09-19-saved-student-workspace.md#run-locally)
with `--send=true`. Select **Tutor policy**, edit the instructions, and generate
the tutor reply when a student message is pending. **Write a reply** retains the
manual intervention option. While the student is working quietly, the button
continues only that student; it does not generate an unsolicited tutor reply.

The two text drafts survive work/view changes and **Reload saved session** within
the page. A new browser/kernel session starts new drafts. Submitted policies and
generated replies are retained in `SESSION/tutor-exchanges/STATE_HASH/receipt.json`;
the existing saved student dialogue records the reply as a supplied intervention.
The separate tutor receipt establishes its generated origin. An interrupted or
failed exchange blocks automatic resending for the same state, even if its policy
is edited. A researcher can inspect the saved receipt before deciding what to do.

Policy mode makes one logical tutor request followed by one student decision;
the unchanged provider adapter can retry each request up to four times. A writer
can still change the session during tutor generation: the subsequent student step
then refuses the stale reply, and the tutor receipt records that failed delivery.
No reply is silently applied to a newer student state.

## Verification

The new integration checks first failed because policy continuation was missing.
They now verify exact policy/context delivery, one tutor and one student decision,
stale-screen refusal, the second-snapshot race, and interrupted-request refusal.
The full suite passes 391 tests, with two optional container checks skipped;
Marimo's app check passes. Existing generator and frozen-audit sources are unchanged.

The actual Marimo app was embedded with authored adapters for a browser check.
Editing/reloading sent nothing; one click saved the exact edited policy, tutor
reply and next student message. The conversation showed both roles. Policy text
survived switching modes/view tabs and reloading the saved state. This verification
made no Gemini or Docker requests and collected no labels. Its private fixture and
receipts are under `data/episode-pilot/workspace-tutor-policy-v1/`.
