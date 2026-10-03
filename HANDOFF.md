# Behavior policy handoff — 2026-10-03

This change makes the existing authored policy's probabilities inspectable,
adds a separate evidence-admission report, and prepares a private six-case human
review of requested assistance. It does **not** establish better student fidelity,
fit new probabilities, admit recorded examples to the sampler, or integrate a new
policy into the browser workbench. Human judgments are pending.

Starting revision: `3c9f4bf424fd9ea400a6ef806907e5ec1eb50efa` on
`codex/notebook-data-refresh`. The original `src/agents/behavior_policy.py` is
unchanged, including selection, seed semantics and existing source-bound receipts.
Its SHA-256 is `782b53dcb9fc58a0940e24bf3350daeded9292c45fb6e56e00ef541721101b5d`.

## Files and design

| Files | Purpose |
| --- | --- |
| `src/agents/behavior_distribution.py` | Pure `predict_distribution()` before sampling/rendering; exact account-balanced joint weights, support, exclusions and fallback. JSON/Markdown report binds input, context and sources. The small frozen calculation is duplicated to avoid invalidating the original module's pinned receipts; differential tests protect equivalence. |
| `src/agents/behavior_evidence.py` | Separate version-1 normalized evidence contract. Preserves content/annotation origins, rubric, partial labels, disagreement, account partitions and temporal isolation. Checks packet consistency, not external authenticity or annotation truth. Joint fitting stays blocked. |
| `src/eval/assistance_review.py`, `.html`, `.js` | Create-only private review exporter and offline forms. Prefix-only first pass; outcome pass requires the matching completed prefix response. Stable anonymous cases, line evidence, explicit uncertainty, reviewer attestations, drafts and local JSON downloads. No human judgment supplied by the assistant. |
| `docs/examples/behavior-evidence-synthetic.json` | Entirely invented admission fixture; not student evidence. The distribution example reuses the pre-existing `behavior-policy-authored.json`. |
| `tests/test_behavior_distribution.py`, `test_behavior_evidence.py`, `test_assistance_review.py`, `assistance_review.cjs` | Probability parity, evidence boundaries and review/export/client checks using authored data. |
| Four `docs/2026-10-02-*.md` memos listed below | Protocols, outcomes, limitations and detailed usage. |

Memos: [distribution](docs/2026-10-02-behavior-distribution.md),
[admission](docs/2026-10-02-behavior-evidence-admission.md),
[real-record validation](docs/2026-10-02-evidence-adapter-validation.md),
[human review](docs/2026-10-02-requested-assistance-review.md).
Their statements that no commit/push occurred describe those earlier bounded
steps; this handoff accompanies the later authorized commit and push.

## Run public offline reports

Run from the worktree containing `pyproject.toml`. A normal environment uses
`uv sync --locked --extra workspace`, then `.venv/bin/python`. The original Mac
has no `.venv` in this worktree; testing used the existing sibling executable
`../episode-pilot/.venv/bin/python` (Python 3.13). No installation was needed.

```sh
PYTHONPATH=. .venv/bin/python -P -m src.agents.behavior_distribution \
  docs/examples/behavior-policy-authored.json --format markdown
PYTHONPATH=. .venv/bin/python -P -m src.agents.behavior_evidence \
  docs/examples/behavior-evidence-synthetic.json --format markdown
```

Both print to stdout without creating sessions. Omit the format option for JSON.
The authored distribution gives checking/work/same-task weight 2/3 and
hint/no-material/same-task weight 1/3. These are constructed example frequencies,
not measured student probabilities. Recorded examples remain excluded.

## What the real-record validation established

A purposive check reused six already-exposed development records from six course
accounts: four fine assistant-coded pilot cases and two original human-reviewed
coarse help/work cases. Local source/event/episode, account and timestamp joins
passed; 23 earlier file pins matched, with 25 fingerprints bound overall.

- **0 fully accepted, 6 partial, 0 rejected; 0 eligible for fitting.**
- The two human observations support only their original coarse help/work rubric.
- The four fine observations remain exploratory; one task relation is unknown and
  one assistance label disputed. Agreement is not human ground truth.
- All six lack qualified preceding-assistance annotations and independently
  revision-bound execution feedback. Neither was inferred.
- A synthetic probe found that prior student assistance could cite only a tutor
  turn. The adapter now rejects that; a failed-then-passing regression covers it.
- No holdout file or unseen evaluation account was opened. Reserved-account
  non-overlap is inherited from the earlier pinned audit, not freshly rechecked.

Source consistency does not establish authentic human identity, student
eligibility, natural course use, label accuracy or a representative population.
The adapter's `empirical_reference` flag means a candidate under supplied
recorded/human provenance, not an independent validity verdict.

## Private artifacts stay on the original Mac

Checkout:
`/Users/minchan/github/chatsight-summer/notebook-data-refresh`

Ignored directories, **not included in this commit or transmitted to another person**:

- `data/evidence-adapter-validation-v2/`: normalized six-record packet, bound
  report, original labels/joins and source verification. Version 1 is preserved.
- `data/evidence-adapter-validation-code-v1/validate.py`: private bounded,
  create-only validation runner; do not rerun it to overwrite results.
- `data/requested-assistance-human-review-v1/`: two real review HTML pages, two
  blank JSON templates, README, private mapping and source/output hash manifest.
- Original audited records and some upstream dependencies also live in ignored
  sibling-worktree data. A fresh clone has code and synthetic fixtures only.

The next person may need authorized access to this original Mac and those source
artifacts. Do not transfer raw records or mappings merely to complete a handoff.
No actual student text, private review pages, account mappings or model artifacts
are tracked here. Automated display redaction is not certified deidentification.

## Review or regenerate locally

On the original Mac, use Finder's Go to Folder to open:
`/Users/minchan/github/chatsight-summer/notebook-data-refresh/data/requested-assistance-human-review-v1`

Open `01-prefix.html`, finish six judgments and download the completed JSON.
Then open `02-outcome.html` and load that unchanged prefix response to unlock the
six outcome judgments. Return both completed JSON files through the approved
private workflow. Forms do not autosave; download drafts before closing. Existing
labels are hidden, but deliberate inspection of the outcome HTML source can
break blinding. Prior familiarity must be disclosed. All 12 decisions were blank
when prepared; the assistant has not imported or evaluated human responses.

There is no review-export CLI or response-to-policy importer. The Python API can
regenerate a copy in a **new ignored directory** if authorized private inputs are
available; use the existing packet for the current review to preserve bindings:

```python
import json
from pathlib import Path
from src.agents import behavior_evidence
from src.eval import assistance_review
source = Path('data/evidence-adapter-validation-v2')
packet = json.loads((source / 'packet.json').read_text())
assert behavior_evidence.report(packet) == json.loads((source / 'report.json').read_text())
assistance_review.write(assistance_review.prepare(packet),
                        Path('data/requested-assistance-human-review-new-copy'))
```

`write()` refuses an existing destination. It creates pages, blank templates,
private mapping and README. The original packet's additional audit manifest was
recorded separately; preserve it rather than treating a new copy as the original.
Before any real-data regeneration, also recheck upstream hashes from the private
source-verification ledger. Missing files are a blocker, not permission to invent
inputs or switch to fresh accounts.

## Verification and exact browser limitation

Full Python suite: **1,131 passed, three optional local-container checks skipped**;
one existing Starlette/httpx deprecation warning. Forty focused Python checks and
16 authored Node client scenarios passed. Source/display/manifest bindings,
12 blank judgments, withheld outcomes and identifier exclusion were checked.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -P -m pytest -q -p no:cacheprovider
node tests/assistance_review.cjs
node --check src/eval/assistance_review.js
```

Actual rendered layout, browser download behavior and interactive stage gating
were **not browser-verified**. Chrome automation was unavailable. The in-app
browser explicitly rejected `file://` under its security URL policy (only HTTP
and HTTPS allowed) and prohibited workarounds, indirect execution and alternate
browser surfaces to achieve the blocked action. This was an access denial, not
merely a missing feature. No loopback server, alternate browser workaround or
security bypass was attempted. Manual opening on the Mac remains the user route.

Existing CI runs on pull requests and pushes to `main`, not this branch push.
The new Node test is a documented local command; it is not added to CI here.
No PR, merge, deployment, model/database call or empirical fitting is part of this
handoff. Pre-existing local edits to `CLAUDE.md` and `TASKLIST.md` are excluded.

## Next action

Have the human reviewer complete the two-stage packet privately. Then validate
response packet IDs, rubric/version, original evidence line bindings, reviewer
attestations and prefix-response hash before considering import. Human labels
still need a declared reliability/admission decision; do not auto-promote them to
calibrated probabilities. Preserve unresolved cases and original judgments, and
choose a bounded endpoint/baseline before any fitting or independent evaluation.
