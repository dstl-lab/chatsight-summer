# Audit the evidence available to the behavior policy

**TL;DR:** Audit already-exposed development records for source traceability,
label meaning, available context and permitted use. Reuse original annotations;
do not generate new labels or convert a source-linked example into a validated
student probability. The source checks support **26 recorded development
messages from 25 course accounts**. Their labels support different, limited uses;
they do not yet validate the full behavior policy or its probabilities.

## Fixed scope

The user authorized this audit after the discussion of what makes an example
real and defensible. Check the sixteen recorded human-reviewed references from
`real-policy-calibration-v2` and the ten recorded follow-ups from
`behavior-pilot-v1`, using the saved 134-event recheck in `behavior-examples-v1`
as supporting provenance for the latter. Report overlap before combining counts.
Generated and authored pilot items remain separate from recorded evidence.

Reproduce existing source validators and original labels. Use only the reserved
holdout's account-selection metadata to verify non-overlap; do not read its
messages, targets or judgments. No database queries, model calls, relabeling,
student eligibility verification or fresh sampling is part of this audit.
Private record identifiers, joins and row-level findings stay under ignored
`data/policy-evidence-audit-v1/`. Public results contain only aggregates and
methodological findings.

## Admission criteria

- **Source:** the original message, preceding context, role and account linkage
  must reproduce. Check known source hashes and any available original-event join.
  Byte identity establishes faithful capture, not human identity or natural use.
- **Observation:** retain the exact original rubric, coder origin, uncertainty
  and disagreements. A coarse work label cannot be split into work/diagnostic;
  assistant agreement does not establish validity. Missing is never absence.
- **Context:** the policy needs preceding requested-assistance and revision-bound
  execution feedback when used for matching. Next-message labels are not earlier
  context. Pasted errors cannot become independently observed execution feedback.
- **Permitted use:** source-verified rows can support scoped descriptions; original
  human labels can support their existing coarse development measurement. Fine
  assistant labels remain exploratory. Account-separated evaluation is a distinct
  requirement from source authenticity. None of these exposed cases is a fresh
  validation set, and known testing traces cannot estimate natural action rates.

Stop after one reproducible inventory, the admission summary and a concrete next
step. Keep the current policy's authored-only admission rule and old studies intact.

## Findings

| Evidence | Source check | Label support | Defensible use |
| --- | --- | --- | --- |
| 16 human-reviewed messages / 15 accounts | Original packets, preceding context, recorded follow-ups and account joins reproduce | Original `help-work-v1` judgments: 16 help=yes; 3 work=yes, 13 work=no | Coarse development measurements under that exact rubric |
| 10 recorded pilot messages / 10 accounts | Every target and full prefix joins exactly to saved database events | Two assistant passes; 8/10 have complete, mutually agreed labels across all three dimensions | Exploratory examples of requested assistance, supplied material and task movement; keep both judgments |
| 134 supporting events / 10 accounts | Saved recheck matches the earlier event exports; 29 illustration references verify | Nine qualitative illustrations, not another independently labeled sample | Traceable examples and source context, not population frequencies |

The two message cohorts share **zero accounts and zero conversations**. The
supporting events belong to the pilot cohort; they are not additional independent
examples. There is **zero account overlap with the 24 reserved test accounts**.
Only their selection metadata was inspected, not their messages or judgments.
Ten generated pilot replies and eight authored boundary items were kept outside
the recorded-evidence count. Existing validators reproduce the original human
observations and the pilot report without changing their labels or results.

Recorded-only assistant agreement is **9/10 for assistance**, **10/10 for
material**, and **10/10 for task relationship**. Task agreement includes one
jointly unclear case. A different case has a general-help versus solution-request
disagreement, leaving eight jointly resolved and agreed bundles. Agreement is a
description of these two assistant outputs, not an accuracy estimate or human
validation. The sixteen human judgments also come from one reviewer, so their
annotation error remains unknown.

## What the audit does not establish

**Capture is verifiable; interpretation and generalization remain separate.**
Source hashes and joins establish that we retained the recorded messages and
their context faithfully. They do not establish who operated an account, a stable
student persona, or representative sampling of DSC 10. Eligibility verification
was explicitly outside scope.

The older human rubric combines code, answers, reasoning and diagnostic evidence
under `work_present`. A yes cannot be split into the policy's separate work and
diagnostic fields, and help=yes cannot reveal hint versus solution versus
checking. Those sixteen annotations are useful without converting their meaning.

The pilot labels describe the **next student message**. They cannot be reused as
the policy's **preceding** requested-assistance state; doing so would leak the
outcome into its predictor. The preceding conversations exist, but that context
field has not been coded by this audit. Neither collection supplies a verified
execution outcome tied to the relevant code revision. Missing feedback stays
unknown; it is not `not-checked`, and a pasted error is not independent proof of
an execution. These gaps prevent claims about matched execution contexts, not
descriptions of the messages themselves.

This audit concerns communication conditional on another recorded message. It
does not validate notebook editing, running code, passing tests, stopping, or the
probability of sending another message. The earlier
[notebook observability audit](2026-09-29-notebook-data-refresh.md) also separates
test/diagnostic traces from evidence of natural course behavior.

## Decision and next build

Keep all 26 messages as source-backed development references, with their original
rubric and human/assistant provenance. Retain disagreements and unknowns per field;
do not discard an entire example merely because one dimension is unresolved.
The sixteen coarse labels remain usable for their existing baseline, and the ten
pilot messages remain useful for diagnosing behaviors the simulator overlooks.
Do not pool their differently defined work counts.

**No recorded example enters the current sampler through this audit.** Its
authored-only contract is a deliberate implementation boundary, not a finding
that recorded data is worthless. Converting recorded examples to `authored` would
hide their origin. An empirical extension needs to retain recorded origin and
label provenance explicitly, expose support and uncertainty, and distinguish
unconditional descriptive frequencies from validated context-dependent predictions.
All audited cases were already exposed during development; none becomes a fresh
validation set because its provenance checks pass.

The next small build should compare the existing policy behaviors and templates
with these source-backed references: show which recorded patterns have a matching
template, which lack one, and which context fields remain unknown. Display the
observed message, original labels and source alongside the authored choice, with
an explicit note that the references did not determine its probability. Reuse
these records; no blanket relabeling round is needed. This makes gaps in the
implemented behavior coverage inspectable without presenting a similar example
as validation. The failed prior-code predictor stays rejected; this audit supplies
no reason to tune it on reserved test accounts.

## Reproduction

The dated offline runner reuses the original source validators and adds cohort
overlap, event joins and per-record permitted uses. The private result lives at
`data/policy-evidence-audit-v1/audit.json`; source messages, record identifiers,
judgments and mappings remain ignored. Verification recomputes the audit without
rewriting evidence or issuing database/model requests.

Verification passed: the saved audit reproduces exactly, **171 source hashes**
match, and the small self-check rejects both a changed evidence file and a reserved
account overlap. No simulator code, label, probability or default changed.

```sh
PYTHONPATH=. python -P experiments/2026-10-02-policy-evidence-audit.py verify
PYTHONPATH=. python -P experiments/2026-10-02-policy-evidence-audit.py self-check
```
