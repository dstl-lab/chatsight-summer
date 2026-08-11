# Sunsetting the inferential layer — schema cut to 8 act-based labels

Date: 2026-08-11. Decision: Minchan, on the two-annotator audit round
(docs/2026-08-10-two-annotator-audit-round.md); flag for Sam review
alongside the behavioral-sequences memo. This is a label-set change:
new profile vintage `e8778096364e` (parent `821784c1258d`), new schema
vintage chained from `bc3739645004`, fresh mass-label required.

## The rule the audit round taught

Across both audit rounds, labels that name an **observable act** ("asked
for confirmation", "pasted an error", "referenced an item number")
survive human measurement; labels that infer an **internal state**
("frustrated", "confused", "wants completion") collapse exactly at the
human-human ceiling — no classifier number on them can mean anything
(invariant 2). The collaborator's sequences memo predicted this from the
armchair; our own numbers now show it.

## Sunset (4 labels)

| label | evidence for retirement |
|---|---|
| Frustration | ceiling 38%, human κ = −0.25 — annotators marked different messages entirely |
| Confusion | ceiling 50%, pooled κ = 0.00; S+5 vs A+1 — construct not shared |
| code-completion-request | infers intent behind pasted code; human κ = −0.14, model P = 0.17 |
| Code Implementation Query | the "asked a question" catch-all; distinctness-flagged twice (J = 0.53 / 0.49), human κ = −0.20; retiring it resolves both standing flags without a merge |

The affective *signal* is not lost — it re-enters as mechanical facets
already logged per message: repeated re-asks, mid-conversation defection
to ChatGPT, fail-then-ask spirals, quiet exit. Those are admitted to the
state space by construction (2026-08-10 proposal) and cost zero
annotator judgments.

## Kept (8)

Admission candidates: Seeking Validation (κ 0.75), bare-assignment-
reference (κ 0.62), Conceptual Clarification (κ 0.62). Act-anchored
keepers on watch: Debugging Request (κ 0.38 — boundary should sharpen
with Code Implementation Query gone), Alternative Method Query (human
κ = 1.00; model side is the laggard), Direct Solution Request (κ 0.33
but load-bearing for the answer-extraction framing — one more round),
assignment-prompt-paste and explicit-concept-mention (high-ceiling
observable acts; candidates to become mechanical detectors later).

## Deliberately NOT changed this vintage

No criteria rewording on the 8 keepers — including the planned
behavioral rewrite of Direct Solution Request — so next round's
per-label deltas are attributable to the cut alone, not to wording
drift. One change per vintage.

## Relabel result (same March–July draw, snapshot 20260811-1d1e79d39fda-7bc759)

Schema `1d1e79d39fda` (8 labels), classifier `7bc759295852`, 235 rows —
corpus-controlled against b975 (identical 52-conversation draw):

- **Zero distinctness flags** — first vintage with none. Retiring the
  catch-all resolved both standing overlaps without a merge.
- **Abstention 3% → 10%**, as predicted. Label prevalences barely moved
  (Conceptual Clarification 48→44%, Debugging 45→43%, Seeking Validation
  37→37%): Code Implementation Query's 56% mass was almost entirely
  co-fire redundancy, not unique coverage. The 10% no-fit is the honest
  residual the catch-all had been absorbing.
- Debugging Request outcome anchor holds (35% of positives in
  fail-then-ask vs 21% baseline); Direct Solution Request sits at
  baseline (no flag, but nothing earned either — consistent with its
  watch status).

## Honest limits

- The cut is argued from n=8 joint pairs per label; the per-label
  ceilings are noisy. The *direction* (act vs. inference) is consistent
  across two rounds and two annotator pools, which is what we're acting
  on — not any single κ.
- Retiring Code Implementation Query (56% prevalence, the corpus's most
  common label) will raise the abstention rate; that is expected and
  informative, not a regression. Watch whether Debugging Request /
  Conceptual Clarification absorb its mass or no-label-fits does.
- If the affect constructs matter to an instructor question later, the
  path back is conversation-segment-level behavioral definitions, not
  reinstating per-message mind-reading.
