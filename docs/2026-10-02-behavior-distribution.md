# Inspect behavior probabilities before sampling

The approved first step exposes the existing authored policy's deterministic
probability calculation independently of sampling and rendering. It does not
admit recorded examples, calibrate weights, add an evidence adapter or change
simulator defaults. Stop after focused verification and an authored report.

Saved policy receipts pin the entire original module. Preserve that module and
its clients byte-for-byte. Add a separate distribution interface using the same
schemas and matching/account-weighting arithmetic. This intentionally duplicates
the small frozen calculation; differential tests guard equivalence. Refactoring
the original would invalidate existing source-bound evidence.

The pure operation returns joint probabilities, exact fractional weights, declared
supporting examples, exclusions, known/unknown context and fallback reasons. It
never samples or renders. A separate report wrapper binds normalized input,
context and both source files. Its CLI prints JSON or Markdown to stdout and
creates no session or evidence files. The seed remains validated in the existing
input contract and bound in the report, but cannot affect the distribution.

## API and offline example

`src.agents.behavior_distribution.predict_distribution(request)` is pure: no
filesystem reads, random draws, rendering, or provider access. `report(request)`
adds source/input/context SHA-256 bindings by reading the two Python modules.
The report is a view, not a new policy receipt; retain the original input to
reproduce it. Existing policy `run` and `verify` remain unchanged.

Using the existing local environment from this worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ../episode-pilot/.venv/bin/python -P \
  -m src.agents.behavior_distribution docs/examples/behavior-policy-authored.json \
  --format markdown
```

A normal installation can substitute `.venv/bin/python`. Omit `--format markdown`
for machine-readable JSON. Both modes only print to stdout; they do not create a
session. The original input's seed is validated and hashed, but changing it does
not change probabilities. Input ordering is retained in the input hash, while
sorted evidence and probability output remain order-independent.

| Joint behavior | Probability | Matching examples | Matching accounts |
| --- | ---: | ---: | ---: |
| Checking / work / same task | 2/3 | 2 | 2 |
| Hint / no material / same task | 1/3 | 2 | 1 |

The query supplies last assistance = hint; feedback remains unknown. Four rows
from two accounts match. Account A's three rows each contribute 1/6; account B's
single row contributes 1/2. Hence raw example counts are equal between the two
behaviors but account-balanced probabilities differ. Remaining rows and their
exclusion or context-mismatch information appear in the full report. No behavior
is selected, no sentence is rendered and no missing literal work changes these
probabilities. These are invented examples, not estimated student frequencies.

If fewer than two accounts match, the report explicitly identifies broader
fallback and preserves mismatch details. If fewer than two eligible accounts
exist at all, the distribution is empty with insufficient-evidence status, never
a fabricated uniform distribution or an observed student stop.

## Verification

The 11 new checks initially failed because the interface was absent. After
implementation, all 50 focused distribution/policy/template/expression/workbench
and coverage checks passed. One existing Starlette/httpx deprecation warning
remains. Tests cover exact fractions, normalization, seed/order independence,
no sampling/rendering/file access in the pure API, joint-label preservation,
matching/fallback/insufficient evidence, excluded origins and query accounts,
invalid inputs, source/context/input bindings and the read-only CLI. Differential
checks compare the new calculation with the unchanged selector across six cases
and three seeds, including preserved receipt output.

The original policy source SHA-256 remains
`782b53dcb9fc58a0940e24bf3350daeded9292c45fb6e56e00ef541721101b5d`.
Pre-existing CLAUDE.md and TASKLIST.md edits remain untouched. No evidence adapter,
new empirical weights, recorded-example admission, model/DB call, UI integration,
commit, push or PR is included. Stop here for review of this bounded step.

The full existing Python suite also passed: **1,102 passed, three skipped**, with
one existing dependency warning, in 50.34 seconds. Run used the installed sibling
Python environment, disabled bytecode and pytest cache writes, and performed no
dependency installation. The authored Markdown CLI example reproduced the table
above. No browser/Node/Marimo UI verification was run because this additive module
does not alter UI paths. `git diff --check` passed for tracked changes; original
policy and unrelated documentation hashes still match the pre-edit values.
