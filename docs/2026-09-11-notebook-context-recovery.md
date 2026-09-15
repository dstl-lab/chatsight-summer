# Recover work context before tuning student replies

Minchan's four-case review identified an omitted channel: notebooks and diffs are
sent to the tutor, so a repeated short query can accompany changed work. In case 4,
the repeated query was the recorded continuation. This does not prove that a
particular edit occurred; it demonstrates why a chat-only review cannot assume
the work stayed unchanged. Keep the human reservations and actual source assignment
separate rather than treating either as a fidelity score.

The omission is verified in this repository. `rawlog._TURNS_SQL` reads question,
response, timestamp and mode; `Turn` has no notebook-state/diff field. `_episodes`
and the continuation projection preserve dialogue only. The existing snapshots
and four generated prefixes therefore omit that work channel. Prior probes found
an initial notebook capture; null later initial-capture fields do not by themselves
establish absence of a separate diff representation.

First inspect existing source/probe evidence for a recoverable, time-aligned work
history. If necessary, use a bounded read-only ingestion query for these same four
conversations, beginning with event types, payload keys, counts and timestamps.
Keep identifiers and any recovered content in a new ignored artifact, with query
and source hashes. Do not alter old snapshots, prompts or completed experiments.
No new model request or generic notebook adapter is required for this check.

If work history is available, distinguish two boundaries. At the prediction cutoff,
only work visible by the current request/tutor response may enter the simulator.
At the observed next request, its notebook change may describe the reference
student action for review; it is future evidence and must not enter the generator.
After synthetic divergence the simulator owns its work state; historical future
diffs cannot supply its edits, execution results or hidden progress.

The useful observation becomes the work change plus whatever the student chose
to say. Work in a notebook need not be narrated or pasted into chat. Missing work
data must remain unknown, with affected comparisons qualified or excluded from
claims that depend on it. Code edits, syntax validity, execution success, copying
and understanding remain separate questions.

## Bounded recovery results

The enforced read-only ingestion probe inspected 98 conversation-linked events
for these four cases, then retained their 26 notebook-info records. An additional
145-row metadata inventory joined the same subjects inside SQL over each
conversation's event window, beginning five minutes before its first linked
event. This also checked events without a conversation ID. Student account
identifiers stayed inside the join; results are grouped by conversation. All three queries stayed below their row caps;
20-second statement and 10-second connection timeouts bounded each query.

Each conversation has one initial notebook capture. The other 22 notebook-info
messages equal ordinary query text; no later notebook/diff field was found in
these inspected payloads. Other observed event types have keys for grader results,
session metadata or suggested/sent follow-up text, with no explicit work-diff
field; arbitrary string payloads were not exhaustively decoded. This is
bounded evidence, not proof that no other store, deployment or logging version
retains diffs. Available local source did not include the tutor/logger itself.

There is a second ingestion omission: all four initial query events lack a
conversation ID. Each initial notebook-info message uniquely matches that
subject's preceding unlinked query, and its embedded response matches the linked
tutor response. The importer therefore misses the first student/tutor exchange.
The earlier check that all available prefix turns were retained applies only to
the already incomplete snapshot. A future snapshot can recover these exchanges
from aligned notebook-info evidence; old snapshots must remain unchanged.

Notebook-info records arrive near the tutor response, sometimes after it. The
offline audit pairs query text, event order and embedded response hashes rather
than treating record time alone as the question-time capture boundary. Initial
captures precede these four selected requests, but are not their current code.

| Case | Recovered evidence | Interpretation limit |
|---|---|---|
| 1 | A same-notebook check of the relevant question failed 4.98 seconds before the recorded complaint, after the current tutor response | Supports the condition in Minchan's judgment; does not establish the exact submitted code or cause of failure |
| 2 | The initial assignment requires percentage tiers applied to the remaining balance; B implements this rule, A uses a fixed discount | A fails the stated assignment example; that alone does not make it implausible student behavior or show copying |
| 3 | Four relevant failed checks occurred between the tutor response and the recorded work-check request | Repeated requests can accompany continued checking; whether code changed remains unknown |
| 4 | Initial notebook exists; no later work diff or intervening grader record was recovered in the inspected window | Neither unchanged work nor silent progress is established |

The recovered artifacts and exact review response remain ignored under
`data/episode-pilot/notebook-context-v1/` and the existing comparison directory.
`verify.py` checks query/probe/source hashes, row caps, capture alignment, temporal
separation and original presentation bindings; `verification.json` pins 19 files.
Run it offline from this worktree with
`../main/.venv/bin/python data/episode-pilot/notebook-context-v1/verify.py`.
No student code was executed, no old result was relabeled, and no new model call
was made. A dropped tunnel was reopened; the failed connection produced no data
artifact before the unchanged read-only query succeeded.

Verification also reopened the four saved draws and rerendered the original
review identically, checking all 18 preparation pins. All 370 older experiment
pins still verify, and both authored worksheet traces reproduce offline. This
change adds documentation and ignored evidence only; no production code changed.

The next simulator comparison needs assignment context, an explicitly dated work
state and optional chat. Use an initial capture only as an initial state, and
represent later unknown work as unknown. Recover the omitted first exchange in a
new ingestion artifact before creating another prefix. Current-time evidence may
ground a simulated action; reference-only checks can explain the recorded action.
Neither makes historical future edits available to a synthetic branch. Do not
train away mistakes, terse requests or uncertainty to make generated students
appear more correct or cooperative.
