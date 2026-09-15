# Can existing logs support observed notebook transitions?

The fixed help/work benchmark is closed. Minchan asked to continue. Its excess
work/evidence in simulated chat does not establish a defect in the newer notebook
student, which already separates quiet edits, chat and requested checks. Another
wording experiment would repeat a completed communication-channel probe.

The next finite step is a data-availability check: can consecutive tutoring
conversations provide two comparable captures of the same learner's notebook?
The August audit suggested this, but did not preserve verified pairs. This could
supply an observed net-work target alongside chat without reconstructing unseen
within-conversation actions. It is not yet a simulator fidelity benchmark.

## Fixed scope, before extraction

Reuse the existing read-only ingestion probe and raw-log connection. Restrict
server timestamps to [2026-02-01, 2026-08-07) UTC, the historical interval documented
in the August audit. Export aggregate metadata first, plus at most three selected
pair identifiers; learner emails stay inside the SQL join. Preserve SQL, parameters,
source hashes and receipts under ignored `data/episode-pilot/notebook-snapshot-pairs-v1/`.
No model calls, labels, reviewer work or simulator changes.

Form conversations from linked query/response events. Require one nonempty
learner and notebook identity, and order these conversations by first linked chat
time (event ID and conversation ID break ties). Consider adjacent conversations
within each learner/notebook group among identity-complete linked conversations,
including those without usable captures so missing captures are not silently
skipped. Ambiguous-identity and unlinked conversations cannot establish adjacency;
these are adjacent eligible records, not a complete interaction history. Require exactly one nonempty initial
notebook per endpoint, attached to that learner and the conversation's first
notebook-info event. Restrict candidate gaps between capture timestamps to >0 and
at most 24 hours, with the first linked chat interval ending before the second
begins. This intentionally excludes overlapping chats and distant revisits.
Report identity exclusions and capture coverage separately. Inventory counts are
within the date window. For the selected endpoints only, also count linked events
outside that window; any such endpoint is boundary-truncated and cannot support
a comparable-pair conclusion in this check.

Select using ascending MD5 of the fixed seed `notebook-snapshot-pairs-v1` plus
both conversation IDs, at most one pair per learner, then the first three.
Selection uses metadata only: no source changes, chat wording or grader outcomes.
Preserve the selection before fetching contents. Inspect those pairs once; do not
replace malformed, unchanged or incompatible examples. A timeout or connection
failure can be retried with the identical query and recorded failure.

For selected captures, parse notebook JSON without execution. Check cell types,
cell IDs and markdown/layout compatibility before aligning code. Report identical
source, changed source, added/removed cells, ambiguous alignment and timing. Cell
outputs and execution counts are stored observations, not evidence that the
captured source produced them. Do not attribute edits to tutor advice or infer the
number/order of edits between captures. Do not use a later capture as context for
an earlier prediction.

## Stopping rule and decision

Stop after one metadata inventory and at most three fixed pairs, with a report of
what can and cannot be observed. If compatible pairs exist, the next possible
benchmark is an interval-level notebook transition, with a separately fixed
protocol. If they do not, exact action-sequence evaluation needs better capture
at chat/run boundaries. Neither outcome restarts the help/work benchmark or
justifies another plausibility-review loop. Keep PR #25 draft and unmerged.

## Completed availability check

The fixed check found paired notebook observations. It does **not** recover an
attempt → error → tutor → edit → pass/fail sequence. Two selected pairs support
comparison by cell position; the third has a changed layout and remains unresolved.
No pairs were replaced and no model requests or human coding were made.

| Within-window metadata | Count |
|---|---:|
| Query, response and notebook-info events | 125,182 |
| Events without a linked conversation ID | 10,495 |
| Linked conversations | 9,442 |
| Conversations excluded for incomplete/ambiguous identity | 28 |
| Identity-complete conversations | 9,414 |
| Conversations with a usable initial capture | 8,590 |
| Adjacent pairs among identifiable linked conversations | 6,870 |
| Adjacent pairs with usable captures at both endpoints | 6,321 |
| Pairs also meeting the 24-hour and nonoverlap rules | 5,921 |
| Learner identities represented among eligible pairs | 222 |

These are availability counts under the stated filters, not numbers of validated
transitions. Adjacency is conditional on identifiable linked records; omitted or
unlinked interactions can intervene. The three inspected pairs were selected by
the frozen hash ordering, with one pair per learner. This is not a representative
sample or an estimate of the fraction that will be usable.

All six selected notebooks parse. Their captured names match their linked chat
notebooks. Each endpoint has one initial capture over its complete linked event
history, no linked events outside the frozen date window, and matching learner
attribution. None of the six captures includes stable cell IDs.

| Fixed pair | Capture gap | Observed cells | Comparison |
|---|---:|---:|---|
| 1 | 13.4 minutes | 135 → 138; code 77 → 80 | Net increase of three code cells; layout differs, so cell alignment remains unresolved. |
| 2 | 3.4 minutes | 101 → 101; code 58 → 58 | Same cell-type layout and exact non-code source; one code position has changed source. |
| 3 | 66.4 minutes | 94 → 94; code 54 → 54 | Same cell-type layout and exact non-code source; four code positions have changed source. |

The latter two comparisons align by position, not verified persistent identity.
Matching scaffold supports a conservative source comparison but cannot rule out
code-cell reordering, notebook resets or unseen assignment-version changes.
The first pair's ordered non-code contents are unchanged too, but their positions
shift. Its net increase does not establish exactly three insertions with no other
removals or moves. Its unchanged-cell mapping was deliberately not guessed.

Pair 2 also has changed stored output and execution count at the changed position.
In pair 3, six code positions have changed stored outputs, while the four positions
with changed source have unchanged outputs. These are differences between saved
fields. No output is bound to an executed source revision, and no pass/fail or
execution-order conclusion follows from them. All six captures report stripped plots, so retained outputs are incomplete.
No notebook code was executed.

## Consequence for simulated students

There is a real-data route to evaluating **net notebook change over an interval**,
in addition to the completed chat help/work measurement. This qualifies the
August memo's broad claim that across-conversation diffing works: it is feasible
for some captures, with alignment and observation-boundary limits now demonstrated.
We do not need an exhaustive label taxonomy to use these observations.

The next candidate milestone is a fixed benchmark of observed notebook-state
transitions alongside chat. Its protocol must define the observation interval,
cell alignment, available context and comparison baseline before generating
students; later work is an outcome, never input to an earlier prediction. The
three inspected pairs are exposed development evidence, not a holdout. The current
single-cell simulator will not automatically represent arbitrary whole-notebook
changes, and a model-chosen stop is not the same endpoint as a later logged visit.
Those mismatched boundaries must be resolved before scoring.

Exact intermediate action order, silent actions, reply probability and learning
remain unobserved. Better logger instrumentation is needed if those are the target.
For now, retain the working simulator and closed help/work results, and stop this
availability check here. No additional plausibility review is requested.

## Reproduction and verification

Ignored evidence is in `data/episode-pilot/notebook-snapshot-pairs-v1/`: the original
protocol, pinned SQL and parameters, metadata receipt, frozen selection, six-capture
receipt, offline comparison and verification. Both reads reused
`data/episode-pilot/notebook-context-v1/ingestion_probe.py`, which checks a read-only
transaction and applies a 20-second statement timeout. The inventory succeeded
once. The first capture request failed before connecting after the tunnel dropped;
its stderr is preserved. Restoring the tunnel and retrying the identical request
succeeded. The successful receipts and selection remain unchanged.

`inspect_pairs.py` contains an authored self-check for source changes, unchanged
outputs, layout/scaffold mismatches and malformed source; it never executes source.
Its saved output can be checked again without requerying or replacing artifacts:

```sh
python3 - <<'PY'
import json, runpy
from pathlib import Path
p = Path('data/episode-pilot/notebook-snapshot-pairs-v1')
m = runpy.run_path(str(p / 'inspect_pairs.py'))
saved = json.loads((p / 'inspection.json').read_text())
assert m['run']() == {k: v for k, v in saved.items() if k != 'source_sha256'}
PY
```

An independent audit recomputes the source differences directly from the six
captures. The final verification also checks unchanged help/work benchmark pins.
Only aggregate findings and project status enter this commit; raw captures,
identifiers, returned judgments and credentials remain outside Git.
