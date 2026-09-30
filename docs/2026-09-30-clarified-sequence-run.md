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

## Prepared; exact dispatch approval pending

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
there is no run receipt and **zero provider calls or local candidate executions**.
The exact-payload question is pending. Approval would dispatch only this unchanged
plan; the closed v1 trial remains unchanged.
