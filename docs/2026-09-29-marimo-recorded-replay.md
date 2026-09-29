# Display recorded notebook changes in the existing Marimo harness

Minchan requested the verified recorded-event replay in the existing notebook
harness. Extend `apps/notebook_replay.py` with mutually exclusive
`--recorded-replay` and saved synthetic `--session` modes. Require an explicit
SHA-256 for the recorded projection, validate its display contract, and leave
the synthetic lineage loader unchanged. This reads the saved local projection;
it does not reconnect to Kubernetes or import/execute private Python scripts.

The recorded view opens at the first verified source difference, falling back
to its prediction cutoff. A native Marimo event picker controls notebook/code
evidence on the left and one conversation column on the right. Only observations
through the selected client sequence appear. Latest full notebook capture,
submitted execution source, metadata-only changes and recorded execution output
stay distinct. A previous capture is never represented as a continuously current
editor state. Pending execution output stays unavailable until its result event.

Display the probable-test label, cutoff/later-evidence distinction and endpoint
diff limitations. Provide read-only code editors; omit generation, editing and
execution actions. Do not embed or rehost the previously blocked static HTML.
The existing notebook app is the integration target, not a new UI framework.

Verify stale/tampered projections, malformed ordering, prefix isolation, pending
results and escaped text with authored data, then run the relevant existing
replay and Marimo checks. Launch locally on an unused localhost port using the
already installed Marimo runtime. Preserve all private source/projection bytes.
Keep implementation/documentation in the current isolated worktree and commit
locally; no provider calls, data publication or new manual labels are involved.

## Launch

From this checkout with the existing workspace extra installed:

```sh
marimo run apps/notebook_replay.py --host 127.0.0.1 --headless -- \
  --recorded-replay /path/to/verified/replay.json \
  --recorded-sha256 <verified-projection-file-sha256>
```

Use the digest retained after verifying the producer's source joins. The display
loader checks the projection's bytes and structure, not the original SQL joins;
it does not follow provenance paths, import producer scripts or reinterpret
recorded events as synthetic runner receipts. `--session` remains available for
existing saved simulations. Recorded mode rejects `--previous` and `--send`.

## Verification

The integration is running locally at `http://127.0.0.1:8446/` with the existing
verified 30-event projection pinned by file SHA-256. It opens at the source
difference (event 15): the submitted code is visible, its later execution result
is still unavailable, and the conversation contains only events 11–12. Selecting
event 12 returns to the prediction cutoff; selecting 16 reveals that execution's
recorded result. Native `app.run()` checks exercised these selections without
model/database calls or student-code execution. All 15 preexisting private probe
files retain their content hashes.

Authored tests exercised both recorded and existing synthetic app branches,
hash rejection, malformed projections, future-content exclusion, source gaps,
pending results, native disabled editors and literal hostile text. Independent
review found a valid sequence gap was passed to `mo.plain_text` as an integer;
a failing authored gap case reproduced it, and explicit gap labels fixed it.
The final full suite passes: 800 tests, three skips; the installed FastAPI test
client emits one existing Starlette/httpx deprecation warning. Marimo validation
and `git diff --check` pass. The local HTTP endpoint responds successfully.

This is a native integration into the existing Marimo app, not an iframe or a
rehost of the static HTML whose automatic browser opening was blocked. Automated
pixel inspection was not performed. Private data remains ignored by Git, and the
view exposes no generation or execution controls. This adds inspectability, not
new evidence of simulation fidelity.
