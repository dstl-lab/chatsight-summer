# Compare tutor instructions with the same local student start

A sequential conversation cannot isolate a policy change: later instructions also
receive a different history. Extend the existing fixed-policy comparison to one
locally generated starting message. Both arms reuse the same saved message, model,
adapter, settings and next sampling seed, then independently generate one explicit
Gemini tutor reply and one local student reply. This is an exploratory comparison,
not a causal claim about real students or proof of simulator fidelity.

Reuse the current comparison setup, lifecycle checks and browser view. Keep the
source unchanged. Each arm gets a new session identity and an unchanged archive
of the original first local call, explicitly marked as cached evidence. New local
calls start at step/call 2; the archived first call never counts as fresh inference.
Pin the child backend and archive in the comparison. Preserve original source
hashes separately from the child worker; model/adapter/runtime/settings must match.

Select the Gemini tutor model explicitly and pin it independently of the student.
Create a separate local callback for each arm, bound to that arm's directory.
Reject missing local configuration or a changed tutor model before sending.
Default provider paths must continue to reject locally bound sessions. Legacy
comparisons retain their existing format and behavior.

The browser's existing **New comparison** and **Run both conditions** actions
serve this path. Saving is offline; running requires sending enabled and sends
both visible histories and policies to Gemini, then runs each student locally.
Show the configured tutor destination and distinguish saved imports from new
replies. Preserve per-arm failures and completed outcomes; reload never resends.

Verify with fictional sessions, injected providers and fake local subprocesses:
shared start and seeds, independent exact histories, source immutability, backend
identity, policy/model pinning, tamper rejection, failures and read-only replay.
Use the actual browser for an offline comparison display check. No new private
cloud payload, live generation, labels, adapter training or closed-study edits
are needed to implement this extension.

## Run it

Use this checkout and create a fresh chat using the
[local student guide](2026-09-28-local-student-backend.md#run-it). Then add a
separate comparison directory to the explicit tutor command:

```sh
.venv/bin/python -m src.agents.browser_workspace \
  data/local-student-demo --chat --port 8442 \
  --student-model /absolute/path/to/local-mlx-model \
  --student-python /absolute/path/to/mlx-environment/bin/python \
  --student-adapter /absolute/path/to/adapter-directory \
  --gemini-tutor-model gemini-2.5-flash \
  --policy-workspace data/local-policy-runs
```

The command is read-only for generation. Add `--send` only when ready to generate.
The model and optional adapter must already exist; no model is installed or chosen
automatically. Gemini uses the existing `GEMINI_API_KEY` environment/`.env` setup.

1. In **Conversation**, use **Continue run** once to obtain the starting student
   message. A fresh chat becomes eligible without restarting the server.
2. Choose **New comparison**, select that starting conversation, and write distinct
   instructions for Policy A and Policy B. **Save comparison** copies the saved
   start and sends no requests.
3. Review the shared conversation, model roles and two policies. **Run both
   conditions** requests one Gemini tutor reply and one local student reply per
   arm. Each new student call uses the same next seed and its own tutor response.
4. Inspect the two saved outcomes together. Reloading or reopening does not rerun
   either condition. Remove `--send` for read-only generation access.

Keep the source at its first reply, without a tutor intervention; later source
progress cannot seed another pair. Existing frozen pairs remain readable. An
identical source/policy/model setup cannot be saved twice in the same comparison
directory. Changed instructions create a separate pair and preserve earlier ones.

Use one explicit tutor model per comparison directory. A different tutor model
requires a different directory; incompatible saved runs are rejected on startup.
The launcher requires a source compatible with the current local worker. Preserve
older checkouts and completed runs in their original environments; this command
does not migrate closed evidence or alter model defaults.

`comparison.json` pins the imported first steps, separate session identities,
Gemini tutor model and local backend/archive files. Each arm keeps the original
session, first step and local receipts unchanged under `local-student/cached-start`.
Its first new inference is `local-student/call-0002`, associated with its new second
chat step. The shared cached call is not counted as new inference in either arm.
Model, adapter, runtime or archived-evidence changes block continuation.

## Verification and limits

All 768 Python tests pass with three optional skips and the existing Starlette/httpx
warning. The whole browser API flow is covered using the real local worker with
authored MLX/provider test doubles: shared starting state and seed, separate exact
prefixes, source immutability, archived receipts, model/provider identity, failures,
tamper rejection, read-only reopen and fresh-source discovery. The Node workspace
checks pass; independent import/routing reviews found no blocker.

The browser display check uses an explicitly authored offline fixture with two
unrun arms. Its messages and placeholder weights are test data, not research
results. No real local inference, Gemini request, private course text, new labels
or training was used for this change. A same-start comparison can reveal model
behavior under two instructions; it cannot establish real student preferences,
policy effectiveness, learning or whether a student would reply at all.
