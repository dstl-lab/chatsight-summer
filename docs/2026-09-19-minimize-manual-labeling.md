# Continue the simulator without a standing labeling queue

Minchan approved pausing the 86-message review: “yes, do that. minimize manual
labeling unless absolutely necessary.” This is a standing workflow preference.
The prepared audit is **paused, not a prerequisite for simulator development**.
Its frozen protocol, packet, mappings, scorer and any draft answers stay intact;
this note supersedes its instruction to await coding. No semantic result is claimed.

Reuse existing judgments and mechanical diagnostics. The completed comparison
already measures length, formatting and output coverage; repeating it adds no new
evidence. Model-assigned flags are not a substitute for human behavioral ground
truth. Keep the current generator while semantic fidelity remains unresolved.

Only request human labeling when a specific consequential decision cannot be made
from existing evidence or automatic checks. Before requesting it, name the decision,
explain why the answer changes our next action, and fix the smallest useful sample
and stopping rule. Do not reopen bulk annotation or repeated plausibility rounds.

## Use the mechanism we already have

Open the existing saved three-task simulation, rather than generate another demo:
`data/episode-pilot/multi-task-history-v1/completed-replay.html`. Its 11 generated
student decisions and four actual container checks show an error, a correction,
task-specific checks and history carried across tasks. These are authored tasks;
the replay contains no generated tutor replies and establishes neither student
fidelity nor learning. Opening it makes no model calls or code executions.

The local review address (localhost:8423) now opens a pause notice and links to an
exact copy of that replay. An optional archived-review link keeps the unchanged
form available for draft access at the same origin. Browser storage is not cleared.
The private `recorded-behavior-audit-v1/pause.json` records the status change without
rewriting the frozen manifest. To serve this landing page after restarting:

```sh
python3 -m http.server 8423 --bind 127.0.0.1 \
  --directory data/episode-pilot/recorded-behavior-audit-v1/paused-ui
```

The next useful implementation increment is researcher intervention over existing
saved sessions: inspect state, supply tutor guidance, take one bounded step, and
reopen the saved result without another request. Reuse the current student/tutor
commands and coordinate with the teammate's Marimo viewer; do not rebuild the
engine or gate this work on the paused coding pass.
