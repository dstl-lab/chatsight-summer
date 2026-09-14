# Work completed while independent coding is pending

Minchan approved an offline evaluation tool and a readable replay of the existing
two-task simulation. This increment ends at checked artifacts. It makes no new
model calls, assigns no human labels and does not run a student-fidelity benchmark.
The eight-case coding readiness set stays separate and unchanged.

## Offline scoring

`src/eval/behavior_scoring.py` compares externally supplied action probabilities
with a baseline computed only from labeled training records. The action vocabulary
is supplied with the input; this does not finalize the reviewers' codebook.

One input JSON contains:

- `description`: what the dataset represents, shown on the report.
- `classes`: unique observable action names.
- `train` and `evaluation`: records with unique `id`, `conversation_id`, optional
  `student_id`, and `label`. Unknown references use a null label and nonblank
  `exclusion_reason`; they are excluded explicitly.
- `predictions`: evaluation IDs with status `ok` and a complete probability map,
  or status `error`, `no-reply` or `unlabeled` with a reason. Missing IDs are
  counted as missing forecasts. Supplied probabilities are not verified samples
  of the continuation generator, and this command does not label generated text.

The command rejects duplicate IDs, unknown classes, malformed probabilities,
conflicting declared identities, and training/evaluation overlap in conversation
or known student IDs. Excluded records still participate in overlap checks.
Unknown student identities cannot rule out a learner appearing in different
conversations; the report discloses conversation-only grouping.

The score is the multiclass Brier sum of squared probability errors, without
dividing by the number of classes or by two. Its range is 0–2, with lower better.
The report compares the same scoreable rows for both methods. It shows equal
encounter weighting and equal represented-group weighting, plus breakdowns by
reference action. It separately reports baseline performance on all labelable
evaluation rows, coverage, failures and every excluded record. Empty paired sets
produce null scores, never zero error.

Selective failures can bias the paired comparison. Group weighting is not a
confidence interval. The command does not declare a winner, infer significance,
choose a practical improvement margin or launch another experiment. A real
benchmark still needs agreed data, exposure/split rules, forecast sampling/output
coding, uncertainty analysis and a fixed budget.

### Reproduce the invented check

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.eval.behavior_scoring tests/fixtures/behavior_scoring_toy.json --output data/offline-scoring-example
```

The output directory must be new. It contains `report.md` and `report.json`, with
input and source hashes. The committed fixture contains only invented records,
including an ambiguous reference, a forecast error, a model stop and a missing
forecast. The training frequencies are help 3/4 and code 1/4. Three paired
forecasts have hand-calculated errors 0.08, 0.32 and 0.50; the corresponding
baseline errors are 1.125, 0.125 and 0.125. The first two encounters share one
student, illustrating why encounter and group weighting differ.

| Weighting | Baseline | Supplied toy forecasts |
| --- | ---: | ---: |
| Each encounter equally | 0.458333 | 0.300000 |
| Each represented group equally | 0.375000 | 0.350000 |

Only 3/7 evaluation records enter the paired comparison; 6/7 have a known
reference label. These numbers verify arithmetic, not simulator quality. The
completed report is in ignored `data/episode-pilot/offline-evaluation-tools-v1/`.

## Saved simulation replay

`src/eval/notebook_replay.py` exports one static HTML page from a saved session and
its predecessor. It reuses the existing offline replay loader, holds existing
session locks read-only, and verifies the predecessor manifest/state hashes and
exact shared observed history before describing a linked continuation. It does
not modify any engine, source receipt, reviewer form or session file.

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.eval.notebook_replay data/episode-pilot/next-task-history-v1/session --output data/replay.html
```

The destination parent must exist; the file must be new and outside the input
sessions. `--previous PATH` can locate a moved predecessor, but the recorded
ancestry must still match. Missing locks or conflicting evidence cause refusal.

The page shows the supplied initial task/dialogue, recorded action order, work
after each action, requested check results, final state/budget and the shared
predecessor record. Context and action details expand with native HTML controls.
Private expected answers and runtime/provenance fields stay out of the display.
Text is escaped and scripts/external resources are disabled. The student-session
receipt identifies received tutor turns as supplied interventions; the exporter
does not infer a separate tutor-generation provenance.

The displayed existing example has five student decisions in Task 1 (edit,
runtime error, edit, pass at 0.5, stop) and three in Task 2 (edit, pass at 2, stop).
Both initial tutor turns were researcher supplied; no tutor reply was generated
in these two encounters. This is recorded generated behavior on authored tasks,
not a real student trace or evidence of learning. Old task feedback stays in its
own task/history section. No new generation or execution was needed to export it.

## Verification and stopping point

The related suite passes 27 tests, including the new hand-calculated scoring
checks and replay boundary regression. They cover invalid forecasts, identity
overlap (including excluded records), zero usable forecasts, input preservation,
ancestry mismatch, hostile display text, private-field exclusion and no-clobber
output. Independent scoring review found no concrete issue and confirmed the
hand arithmetic. Existing replay/next-task/tutor-context/student tests also pass.

The final HTML was inspected through a localhost preview: the action overview,
recorded TypeError, task navigation and Task 2 check value match the saved events.
Both original sessions and the eight-case packet/form artifact hashes verify
unchanged. The first expanded-context HTML is retained separately; the final
page folds initial context so recorded actions are easier to see.

This increment is complete. The next human input remains the two independent
reviews. Do not score those eight exposed readiness cases as a benchmark or
resume the paused history-ablation/plausibility loop automatically.
