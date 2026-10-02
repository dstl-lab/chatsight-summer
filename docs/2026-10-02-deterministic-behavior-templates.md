# Deterministic wording for the observed expression gaps

**TL;DR:** Add three authored wording patterns: general help on the current task,
a solution request on an explicitly supplied next task, and that request with
explicitly supplied work. Express an existing saved choice without changing its
distribution, seed, behavior, labels or provenance. No model calls are needed.

The user approved this bounded extension after the recorded-pattern coverage
comparison. It implements clear expression gaps; it does not fit a behavior
distribution or validate student realism.

## Implementation boundary

Existing policy, expression and workbench runs pin their source files. Keep those
modules unchanged so their verification still works. Add one small deterministic
renderer over a verified saved choice, reusing the policy schemas and old
renderer for the six existing patterns. Save a separate rendering receipt and
copy the original policy files into the new output for replay. Do not revise the
old trace, relabel recorded cases as authored or select another behavior.

| Behavior | Required literal inputs | Authored wording |
| --- | --- | --- |
| General help / no material / same task | None | `can you help me with this?` |
| Solution / no material / different task | `next_task` | Supplied next task, then `can you show me the solution?` |
| Solution / work / different task | `work`, `next_task` | Supplied work, then next task, then `can you show me the solution?` |

Insert literal task/work content once, unchanged. Do not claim that supplied work
is unfinished or belongs to the next task; that association is not established by
the existing fields. Do not extract literal content from recorded
future messages, invent code or claim progress. A missing required field returns
`missing-input` with no text. Unresolved or unsupported selections remain so;
neither becomes silence or a guessed greeting. The single disputed general-help
versus solution case remains disputed. No extra template is justified by choosing
one coder as the authority.

The new renderer is explicit and local. The current workbench and optional model
wording path keep their saved behavior; no UI or production default is changed.
Use authored examples for functional checks and documentation, with no new student
labels, provider requests, database access or reserved test content.

## Implemented and verified

`src/agents/behavior_templates.py` implements the three additional patterns over
the unchanged policy. `express()` is a pure operation on a verified policy result;
`run()` verifies a saved policy, copies its three original files byte-for-byte,
reverifies the copy, and saves a separate rendering receipt. The receipt binds the
original policy and new renderer source hashes. `verify()` reproduces the output
from the copied policy without the original directory or any provider call.

The original trace can correctly say `unsupported` while the new rendering
receipt says `rendered`: they describe the old and extended renderer respectively.
The original choice and distribution are identical. Missing-input receipts keep
the choice and list every required absent field; they contain no reply text.

Authored examples are saved locally in `data/deterministic-template-examples-v1/`:
three successful replies and one missing-next-task case. The summary is in that
directory's `report.md`. All four receipts replay, and their original source files
are unchanged. This is a local saved-decision renderer; the current browser
workbench and optional Gemini wording module do not automatically use it.

```sh
PYTHONPATH=. python -P -m src.agents.behavior_templates render \
  data/my-saved-policy data/my-deterministic-wording
PYTHONPATH=. python -P -m src.agents.behavior_templates verify \
  data/my-deterministic-wording
```

An independent read-only comparison of existing labels against the nine combined
template keys found 7 covered / 2 missing / 1 unresolved under coder A, and
8 / 1 / 1 under coder B. For the eight complete, agreed cases, coverage rises from
3 to 7. The difference between coders is the unchanged disputed assistance label.
The remaining agreed gap is a message requesting neither assistance nor supplying
material; its communicative meaning cannot be guessed from that tuple. Four
covered cases need no literal slots; the others require task/work inputs whose
availability is not established by this comparison. No label or probability was
changed to obtain these counts.

**39 focused checks passed**, including five new authored checks. They cover
literal insertion (including braces and newlines), every missing slot, unchanged
selection/distribution, original-template behavior, unsupported/not-selected
states, offline replay, source preservation, overwrite rejection and tampering.
The new tests first failed because the extension was absent. Independent code
review found no material issues. The existing FastAPI test client emits one
dependency deprecation warning; no test failed. The saved workbench example and
previous coverage report both still verify with their original source bindings.

```sh
PYTHONPATH=. python -P -m pytest -q tests/test_behavior_templates.py \
  tests/test_behavior_policy.py tests/test_behavior_expression.py \
  tests/test_authored_policy_chat.py tests/test_policy_template_coverage.py
```

The next integration can expose this renderer for new workbench sessions while
keeping old session receipts intact. No human labeling round is needed for that
engineering step; empirical probability calibration remains a separate question.
