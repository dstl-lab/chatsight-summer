# Review certainty and compact evidence — October 19, 2026

The lab2 profit-division example exposed a presentation limit. Linked source and
execution output establish a string/numeric division failure, but do not establish
that the tutor caused it. Earlier syntax mistakes are separate observations. The
flag is useful even when attribution remains uncertain; the instructor decides
the interpretation. Absence of recovery in a fixed window does not establish that
the session ended without recovery.

Keep flag eligibility and existing evidence references. Present each flag as a
possible interpretation with a visible uncertainty and access to the exact cited
records. Do not show a confidence percentage or call structural evidence checks
semantic verification. Human reviews stay separate and are not inferred from a
model flag. New assessments should distinguish recorded observations, plausible
interpretation and missing context concisely, without automatically blaming the
tutor or suppressing plausible review cases.

Replace tall timeline cards with compact, collapsed rows: time, small event icon,
action label and a literal excerpt. Full text, code, outputs, provenance and ordering
warnings remain expandable. Evidence jumps highlight rows without opening a wall
of text. Preserve event order and filters. Test interactions and inspect desktop
and narrow layouts with synthetic data. Existing app processes, saved results,
private datasets and instructor labels remain untouched; activation still requires
Austin's go-ahead.

The new prompt is pinned by the existing configuration hashes. Existing assessments
are not silently regenerated or rewritten; changed prompts require a new prepared
analysis. Saved review bundles can still be opened with the new presentation, and
their existing instructor reviews keep the same dataset identity and storage key.

Validation: 161 backend and 24 frontend tests pass; TypeScript and the production
build pass. Synthetic desktop and 390-pixel previews confirm compact 34-pixel rows,
single-record expansion and citation highlighting without bulk expansion. The
original checkout remains clean at `5fbd1de`. No Gemini calls or app restart occurred.
