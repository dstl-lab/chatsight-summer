# One local behavior-policy step in the workbench

**TL;DR:** Connect the existing authored behavior selector to one continuing-chat
checkpoint. Show the actual output of a fixed local error example on the left,
the template reply in chat, and the saved selection rationale beside it. This
tests the mechanism, not natural student behavior or calibrated probabilities.

## Approved scope

Reuse `behavior_policy.select`, the chat reply callback, existing session bindings,
and the browser workspace. Keep the source-pinned chat engine and frozen studies
unchanged. The new adapter supplies explicit context and literal diagnostics;
there is no semantic extraction, persona inference or provider request.

Preparation executes only a fixed, repository-authored empty-list example in an
isolated Python subprocess, saves its actual error, and creates a fresh one-step
chat session. Arbitrary uploaded code execution is outside this integration.
The example library is invented, with account-balanced weights and a fixed seed.
Its probabilities describe that authored library, not DSC 10 students. Neither
the rejected prior-code cue nor the empirical 20% comparator enters the policy.

Before continuation, verify the supplied state, configuration and renderer. A
missing input or unsupported template blocks the step without consuming a chat
decision or creating a no-reply. The callback checks the exact delivered prefix,
saves a create-only policy receipt bound to the session/state and configuration,
then returns the template text to the unchanged chat runner. Replay must bind
the same selected behavior and rendered text to the saved chat outcome. Missing,
changed or interrupted receipts fail closed; reload never executes or generates.

Expose the saved authored code/error, known context, selected behavior, template,
weights, source references and seed in the existing workbench. Keep one chat view
and a compact expandable explanation; distinguish the initial preview from a
saved decision. The single-step cap means the demonstration finished, not that
a real student stopped. An explicit authored-policy launch option enables the
local callback; opening the session without it must not fall back to Gemini.

## Completion checks

- [x] Authored creation captures the actual local error; no provider is called.
- [x] The browser continuation delivers the template's exact diagnostic and saves
  a matching decision trace; stale/repeated requests cannot consume another step.
- [x] Missing/unsupported rendering leaves the session untouched; changed/missing
  policy receipts prevent unverified replay or provider fallback.
- [x] Read-only replay is stable, and relevant existing workspace checks pass.
- [x] Inspect the real page before and after its one local step, document results,
  and commit this change in the existing isolated worktree.

No new research batch, label collection, model adoption or holdout reuse follows
this mechanism milestone. The 24 closed test accounts remain reserved.

## Run locally

Use a new output directory; existing runs are never overwritten:

```sh
PYTHONPATH=. python -P -m src.agents.authored_policy_chat create data/my-authored-policy
PYTHONPATH=. python -P -m src.agents.browser_workspace data/my-authored-policy \
  --chat --authored-policy --send --port 8457
```

`--send` enables the existing explicit continuation control. In this mode it
invokes only the local selector and template; provider backends cannot be
configured alongside it. Omit `--send` for read-only inspection. Preparation
runs the fixed example once; opening, generating a reply and replaying do not
rerun the code. This is a saved authored code checkpoint, not an editable notebook
kernel or an observed student's action sequence.

Select **Generate local reply**, then expand **Why this reply?**. The fixed seed
selects diagnostic checking and emits the actual final error line followed by
`can you check this error?`. The three invented examples represent two invented
accounts: equal account weights yield 3/4 diagnostic-checking weight and 1/4
checking-without-material weight. These are demonstration settings, not estimates
or default probabilities for real students. The context fields are explicitly
authored inputs, not classifications inferred from the displayed dialogue.

The browser distinguishes the supplied context from the local template, highlights
the new message and preserves its existing chat navigation. The explanation
shows the selected behavior, template, seed, matching and example weights/source
references. Unavailable templates remain blocked rather than becoming silence.

Verify the saved decision without execution or model calls:

```sh
PYTHONPATH=. python -P -m src.agents.authored_policy_chat verify data/my-authored-policy
```

## Verification results

Four integration checks first failed on the absent adapter, then passed. They
exercise actual fixed-code execution, exact policy-to-message binding, duplicate
and stale continuation, read-only replay, missing/unsupported rendering, foreign
prefixes, and missing/tampered receipts. The focused regression set passed **86
checks**; the full Python suite passed **1,070**, with three skipped optional
checks and the existing Starlette/httpx deprecation warning. An independent
backend review found no material issue and reproduced all four integration checks.

Browser-controller checks include the authored mode, escaping, local-only
submission, selected-behavior display, preserved explanation disclosure and
completion wording. A browser-observed rewind wording issue received a failing
regression check and a correction: earlier playback now points to Next for the
already saved reply, rather than asking the user to generate again. The real
browser verified this path and generated one reply in
`data/authored-policy-workbench-v1`, and its saved policy/chat trace verified.
No private student data, LLM calls, new labels or changes to closed studies were
needed. The existing student-policy selector and source-pinned chat engine were
left unchanged.
