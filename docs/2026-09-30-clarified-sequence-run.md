# One sequence with explicit notebook and chat fields

Minchan approved one fresh bounded sequence after the action-contract and chat
feedback changes in `b38863d`. This is a development check of action coherence,
not a realism benchmark, tutor-policy ranking or repeat of the closed v1 trial.

## Frozen scope

Use the same captured revision-zero task and saved guided hint as
`data/full-behavior-sequence-v1`, the same immutable archive runtime, local CSV,
tutor-only course API reference and Gemini 2.5 Pro for both roles. Only the
clarified version-two schema/student prompt and tutor-context instructions change.
No later recorded target, prior sampled edit, prior execution result or v1
continuation is supplied to either generator. The reused initial hint is not
regenerated and the full CSV stays local.

One run allows at most eight student decisions, three new tutor replies and four
student-requested local executions, counting attempts. The eighth student
decision ends the run, even if it leaves a message awaiting a tutor. Otherwise,
stop at explicit no-reply, a required operation beyond its cap, an invalid action,
or provider/infrastructure failure. Cell execution errors may be observed and
acted on within the same budget. One SDK attempt per request; no retries, resuming,
replacement samples, forced execution or extra batches. An early stop is retained.

Private payload to Google Gemini: selected captured task, notebook cell and
visible student/tutor exchange, then this sequence's generated actions, dialogue
and local feedback; the reference is sent only to the tutor. Keep the plan,
authorization, complete provider/executor receipts and inspection privately in
`data/full-behavior-sequence-v2`. Preserve all v1 files unchanged.

## Questions and reporting

- When an edit occurs, does its replacement-code field contain the proposed
  notebook code rather than a label or chat-only proposal? Report actual source
  changes, including empty, invalid or unchanged replacements; never repair them.
- Does chat remain independent of edits and execution? Check exact action
  application and revision-bound feedback against retained raw calls.
- When a tutor is called, does its reply distinguish installed work from a pasted
  proposal and avoid unsupported execution/correctness claims? If no mismatch or
  tutor call occurs, that part of the clarification is untested.
- Report the complete ordered sequence, terminal reason, failures, usage and
  timings. Verify exact offline replay and expose the saved run in the workbench.

A successful mechanical replay alone does not demonstrate faithful student
behavior. A single sample cannot estimate a failure rate or isolate which of the
student/schema/tutor changes caused a different outcome. Close this check after
reporting its result; further sampling requires a separate research decision.

## Preparation and approval

The private version-two plan is frozen with digest
`0e22dc50ed61f7b819c150f5028387b2d1107a6c744974dcaa5a3a800bf8342a`.
Fifteen implementation pins and all source/reference/runtime inputs verify.
The initial state and unchanged settings were compared with v1, and hashes of
all original v1 files were preserved for the completion audit. The required local
image and configured provider key are available. No candidate code was executed.

Independent review found no dispatch blocker and verified that the installed
Google SDK preserves the explicit fields in its outbound schema conversion.
The prepared protocol and user/standing-authorization record are retained privately.

Automatic approval review rejected the dispatch before process creation because
the latest user acceptance did not explicitly name this new private payload and
Google Gemini as its destination. The actual rejection is recorded privately;
at that point there was no run receipt and zero provider calls or local candidate
executions. Minchan then answered **“Let's continue. Approved.”** to the exact
payload/destination question. That approval was bound to the unchanged plan and
recorded before the single dispatch. The closed v1 trial remains unchanged.

## Completed outcome

The run completed in **38.98 seconds** with **four student decisions, one new tutor
reply and one requested local execution**. All five Gemini responses were valid
complete STOP outputs; there were no provider/executor failures or retries. Usage
totaled 10,353 tokens: 7,213 prompt, 183 output and 2,957 thinking tokens.

| Stage | Saved behavior | Evidence |
| --- | --- | --- |
| Initial | Captured work plus reused guided hint | Revision zero, no current execution feedback |
| Student 1 | Quiet code edit | Full replacement code installed at revision one; empty chat |
| Student 2 | Requests a local run | Exact installed source executed in the declared isolated runtime; scalar result 2,850, no error or course grade |
| Student 3 | Sends a short acknowledgment | Receives the real execution feedback; chat changes no code |
| Tutor 1 | Acknowledges and explains the installed approach | Sees revision-one source, its actual feedback and the acknowledgment |
| Student 4 | Explicit no-reply | Four student decisions, two tutor calls and three executions still available |

The notebook/chat field mismatch seen in v1 **did not recur in this sample**.
Raw replacement code equals the installed cell and the source sent to execution.
The tutor discusses the installed approach; no chat proposal competes with it and
no unobserved execution or course-grade claim is made. Its correctness language
is a tutor judgment, not an independently verified course outcome.

The new run is mechanically coherent and exercises quiet editing, actual execution,
feedback-informed communication and stopping. Because no chat/code discrepancy
occurred, the tutor's response to such a discrepancy remains untested. This single
unpaired stochastic draw cannot establish a reduced error rate, which component
caused the change, realistic communication/stopping, or real-student learning.
There is only one short visible student message in the starting exchange; this
run does not validate that the generated acknowledgment matches that student's
communication habits.

Exact offline replay, approval chronology, raw response validation, source-bound
feedback and limits were checked. All original v1 file hashes remain unchanged.
An independent read-only audit confirmed the raw field mapping, both execution
output frames and their dataset/runtime fingerprints, retained feedback, and
terminal reason without dispatching any new provider or Docker call.
The existing browser projection correctly shows six stages, two initial messages,
no new chat during the edit/run, one later student message and one tutor reply.
Only the requested execution stage labels its output as new; later stages retain
it as a previous observation. New-message highlighting works, and the browser
reported no console errors. This run is closed; no additional batch is queued.

## Saved replay

The new read-only replay is served at `http://127.0.0.1:8456/`; the earlier v1
replay remains on port 8455. From this worktree, the new launch command is:

```sh
PYTHONPATH=. /Users/minchan/github/chatsight-summer/episode-pilot/.venv/bin/python -P \
  apps/archive_message_preview.py data/archived-student-loop-v1 \
  --branch data/notebook-source-branch-v1/branch \
  --continuation data/archived-tutor-continuation-v1 \
  --include-policy-samples --history-benchmark data/course-account-history-v1 \
  --sequence data/full-behavior-sequence-v2 --port 8456
```

Private receipts, protocol snapshot, approval records and completion audit remain
under ignored `data/full-behavior-sequence-v2`. Only aggregate results are recorded
in this public memo.
