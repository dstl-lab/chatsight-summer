# Student communication evidence card

The approved first feature is implemented in the existing browser workbench.
Expand **Student evidence** above the conversation to inspect the supplied
student-message count, median length, length bins, newline/backtick counts and
source excerpts. The card starts collapsed and retains its open state while
viewing steps from the same source. It adds no separate navigation tab.

The local preview is <http://127.0.0.1:8451/>. It contains fresh session copies
of the ten existing course-account prefixes, in their original order, with
three decisions available per session. Opening it makes no model request.
These are development examples, not a fresh evaluation set.

## Evidence boundary

Chat cards use only the verified session manifest's initial query prefix.
Notebook cards use initial supplied dialogue, excluding explicitly generated
turns. The saved policy preview uses its shared starting dialogue for both
conditions and every sample. Generated follow-ups, target messages, notebook
outputs and unrelated imported conversation examples cannot grow the card.

Counts describe raw Unicode characters, including pasted work and whitespace.
Length bins remain 0–40, 41–300 and over 300. Median uses the conventional average
of the middle two values for even counts; an empty card has no median. This
display statistic does not change any closed experiment's scoring definitions.
Examples are the first, middle and latest student messages, deduplicated by
position, with a marked 240-character excerpt ceiling. They are illustrations,
not a semantic or representative sample. No personality, skill, sentiment,
learning or silence probability is inferred. Supplied context may be recorded
or authored; the UI says so.

## Optional generation guidance

**Use as student guidance** is off by default. It is available for chat sessions
using the provider callback, and is reset when changing source/scenario. Enable
it, open **Continue run**, then explicitly submit the next decision to use it.
Viewing, expanding and toggling the card send nothing. Existing notebook and
local-model sessions can display evidence but do not accept this option.

The selected student request receives a soft-guidance preamble and the exact
card alongside the ordinary current dialogue. Tutor requests remain unchanged.
The guidance explicitly avoids hard length limits, copied answers, damaged code,
invented typos and inferred traits. Its default provider callback uses one
attempt. The option does not schedule a batch or retry an interrupted request.

The unchanged chat engine retains its canonical input receipt. A separate
create-only `student-evidence/<state-hash>.json` records the **actual augmented
provider prompt**, card, schema, model, source hash, binding and response/error.
It is written pending before dispatch under the existing session lock. Browser
replay verifies it against the canonical operation and result. A verified saved
decision shows **Evidence guidance recorded for this decision**. Absence of an
extension means no guidance receipt is available, not proof about all historical
provider inputs. All receipts and source messages remain in ignored private data.

## Validation and stopping point

Seventy focused Python checks and two Node controller checks pass. Browser
inspection confirms the compact collapsed view, corrected even-count median,
visible guidance control and default-off behavior. Viewing and toggling the
preview produced zero generation receipts. Existing Starlette/httpx deprecation
warning remains. Independent review covered binding, error handling, no resend,
unsupported backends and separation from tutor prompts.

All 100 receipts from the closed history comparison still verify with unchanged
inputs and pinned engine files. No real generation, new labels or experiment ran
for this feature. It establishes an inspectable input mechanism; improved
student realism remains untested. Separate action selection is not part of this
increment.

## One-pair illustration prepared

Following the user's request for a concrete example, the first conversation was
selected in its original order before seeing outputs. Two fresh one-decision
sessions share the exact five-message prefix, Gemini 2.5 Pro, temperature 1.0 and
an 8,192-token output limit. One uses the existing prompt; one adds the evidence
card through the actual workbench adapter. Recorded next messages are excluded.
This is one sample per condition, not an improvement test or another labeling pass.

Private inputs, a single-use runner, and a side-by-side HTML view are prepared
under `data/student-evidence-example-v1/`. The frozen plan SHA-256 is
`f09d28cbd34a921cc76498db5e6b44cdd0fd18709cae903d2b20c5190889a856`.
The runner reuses the existing raw Gemini callback and parser, saves raw responses
before parsing, preserves errors and blocks reruns. Its authored pair/no-resend
check and seven evidence-adapter tests pass; independent pre-dispatch review passes.

Automatic approval review rejected dispatch because it required explicit
authorization for this private conversation's export to Google Gemini despite
the standing authorization and accepted comparison. A specific two-request
permission question is pending. **Zero provider requests have been sent for this
example; no comparison result exists yet.** Original workbench sessions and the
closed 100-call study remain untouched.

Offline check (no provider request):

```sh
PYTHONPATH=. python -P data/student-evidence-example-v1/run_pair.py check
```

```sh
PYTHONPATH=. python -P -m src.agents.browser_workspace \
  data/student-evidence-v1/sessions --chat-sessions --send --port 8451
```
