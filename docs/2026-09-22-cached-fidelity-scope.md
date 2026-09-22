# Cached communication: exact scope before further review

**TL;DR:** The eight previously reviewed references link to all 16 cached replies.
One pair is identical under identical context, leaving **23 distinct messages /
46 help/work flags** for any later common-rubric pass. No compatible judgments
already cover them. This inventory is complete; no review queue, new generation,
or generator change starts here. These outputs contain only one condition, so
they cannot measure whether grounding improves realism.

## What the saved evidence actually contains

The accepted step is an inventory of existing evidence and the minimum missing
judgments. It is separate from the closed original studies, whose outcomes,
labels, stopping decisions and source files remain unchanged.

| Item | Verified scope |
| --- | --- |
| Sources | `fixed-communication-eval-v1`, linked to `fidelity-coding-readiness-v1` |
| Cases | Eight distinct conversation cases, not eight identified learners |
| Reference | First subsequent recorded student message, exactly matching the independent review |
| Generated messages | Two completed replies per case: 16 replies, zero no-replies/errors |
| Inputs | Identical saved prompt for both draws of each case; exact prefix matches the independent review |
| Conditions | One unchanged historical chat generator/configuration; two draws are not two conditions |
| Unique coding units | Eight recorded messages plus 15 distinct generated messages in their supplied contexts |
| Duplicate | Both generated draws in case 5 have identical text and context |
| Compatible judgments reusable | Zero |
| New requests / labels / executions | Zero / zero / zero |

Case 1 has eleven student messages in its recorded follow-up block. Only its first
message belongs to this scope, as in the original protocol and independent review;
the remaining ten must not silently become the reference. Each other case has one
follow-up message. Notebook activity and omitted earlier exchanges remain unknown.

All 24 occurrences already have historical plausibility and v7 primary-action/task
labels, with the categories suggested by the assistant and approved by the
instructor. Separately, one independent reviewer coded only the eight references
using primary v7 categories. Neither supplies the two independent binary flags:
work precedence can suppress an attached help request, and a pasted problem is
not necessarily submitted work. Do not convert these categories automatically.

The completed `help-work-v1` study supplies comparable definitions but concerns
different messages. Its 72 coded messages have no exact text or visible-context
matches here; its selection excluded these eight conversations. The paused
29-case audit and the joint plausibility review supply no completed flags to reuse.

## Minimum possible later pass, fixed before new judgments

If this secondary measurement diagnostic proceeds, reuse the existing
`help-work-v1` definitions and review interface. One reviewer would code help
request and work/evidence presence independently as yes/no/unclear for each of
the **23 distinct contextual messages**. Both flags may be yes. Do not add
plausibility, sentiment, personality or task-relationship questions.

Show the exact original prefix, conceal origins and old labels, record prior
exposure, and retain unclear answers with notes. Prior exposure cannot be undone;
this is development evidence, not a newly held-out benchmark. Code the duplicate
once and explicitly map that judgment to both saved draw occurrences. The analysis
still contains sixteen draws, equally weighted within eight cases. Do not discard
the duplicate, treat draws as independent learners, or choose the better reply.

The immediate question would be whether this set supplies **both work-absent and
work-present recorded messages under one rubric**, with comparable output coding.
Keep help as a separate flag and report help-only coverage explicitly; a message
with neither flag still belongs to the work-absent group. The old primary labels
do not establish binary membership. If coverage is absent or ambiguous, report that and
close; do not replace cases, resolve uncertainty through repeated review, or
fill missing answers with model judgments.

If usable coverage exists, a descriptive report may show work/help incidence and
work discrepancy separately for recorded work-absent and work-present groups.
Keep every occurrence and show missing/unclear counts and exact denominators;
any balanced work score requires both groups with comparable complete coding.
Two draws give only coarse frequencies of 0, 0.5 or 1. Coverage is a feasibility
check, not proof of reliable coding, sufficient sample size, or model calibration.

**Hard stop:** at most one pass of 23 messages / 46 flags and one report, even if
inconclusive; no replacement cases, rerolls, forced adjudication or automatic
prompt tuning. This ceiling narrows the proposed 24-message cap. That pass is
specified, not launched by this inventory.

## What this does not answer

There is no paired current-exchange-only condition in these cached outputs.
Relabeling them cannot demonstrate a grounding benefit, and the existing
two-condition scorer must not be used by renaming draws as conditions. This set
also predates the notebook simulator: it cannot validate notebook actions or the
new conversation-to-notebook initialization. Do not pool it into the closed
help/work benchmark or use it to adopt a generator. A future improvement comparison
would need its own matched conditions and a declared decision rule.

## Verification and stopping point

The private, read-only inventory at
`data/episode-pilot/cached-fidelity-scope-v1/` records exact source pointers,
prefix/text hashes, duplicate membership, old judgment provenance and the missing
flags without assigning any. Its reproducible check verifies the saved artifact
hashes and input/output/reference joins; raw messages stay in their original
ignored files. Historical source-code pins are not rewritten to match today's code.
Independent audit verifies 28 original artifact pins and 37 inventory file pins,
all 24 occurrences, 23 distinct coding units, and 46 unassigned flags.

This step ends at that verified scope. No model calls, label conversion, reviewer
handoff, packet construction or source changes are needed. Simulator behavior
stays unchanged, and the original studies remain closed.

With the existing private artifacts present, reproduce from the worktree:

```sh
PYTHONPATH=. .venv/bin/python data/episode-pilot/cached-fidelity-scope-v1/inventory.py
```

The command verifies the saved inventory exactly and refuses a changed result.
