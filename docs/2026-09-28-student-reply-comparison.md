# Inspect saved student models in the workspace

## Bounded design

The existing Compare workspace will show the saved base model and full-pass
adapter replies side by side, with one shared recorded conversation in the chat
sidebar. This makes the model evidence usable without another experiment or
labeling pass. Use all 13 first replies with shared recorded prefixes; later
synthetic histories differ between runs and do not belong in this comparison.

Reuse the current route, case navigator, source inspector, literal student-text
display and two-column styles. Add one read-only comparison kind and explicit
`--student-comparison` launch option. The page identifies these as saved outputs
and the trained model as experimental. It has no scores, winner, reference-answer
column, labels or generation controls. Context appears once in the chat sidebar;
model details stay in the inspector.

An offline-prepared private bundle copies exact requests/results/invocations and
the original cohort/adapter manifests and completion records. The reader accepts
only known local filenames, verifies their closure hashes and original source
pins, joins every first reply by case/query identity, and checks equal prefixes,
serialized messages, seeds, sampling settings and base-model identity. Adapter
identity remains explicit. Archived absolute paths are metadata, never paths for
the browser to open. Pin the bundle at launch; changed or invalid evidence fails
closed instead of displaying stale data. Preserve original closed artifacts.

Success means the existing desktop workspace can navigate all 13 cases, display
both exact saved replies and their shared context, and reject writes or changed
evidence. Verify the reader/API with authored fixtures, the existing JavaScript
controller checks, and an actual browser check. No model loading, provider calls,
training, additional human review or default-model adoption is part of this work.

These conversation IDs do not identify individual learners. One draw per model
on exposed development prefixes does not establish student fidelity, notebook
behavior or policy effects. The full adapter's likelihood improvement and mixed
generation results remain as previously reported; this view adds no new evidence.

Standing authorization to continue through implementation applies. Work remains
in a separate worktree and local commit; private copies stay under ignored data.

## Implemented

Launch the existing browser server with the closed local bundle:

```sh
python -m src.agents.browser_workspace \
  --student-comparison data/student-reply-comparison-v1/bundle --port 8445
```

Open `http://127.0.0.1:8445/?view=compare`. Student models has searchable
conversation navigation, two literal saved replies, one shared chat sidebar, and
the existing source inspector. Model details include the base revision and
training receipt hashes. This is a standalone read-only view; session, sending,
generation callback and tutor options are rejected.

The private bundle contains byte-for-byte copies of the selected closed files,
both original manifests/completions, and a closure listing the exact allowed
inventory. Its preparation record preserves original and copied file hashes.
The reader verifies complete model identity across every case in each arm and
joins model/adapter file hashes to the original manifest pins. It never opens
archived model or source paths. No new dependencies or styles were needed.

## Verification and stopping point

- 787 Python tests pass; three optional skips and the existing Starlette/httpx
  deprecation warning remain. The browser controller checks pass.
- Authored cases cover exact text/context, changed or incomparable evidence,
  mixed model identities, original manifest pins, read-only API/CLI behavior and
  escaped UI text. Independent review reproduced and confirmed the identity fix.
- Desktop checks cover the two columns, shared current exchange, search,
  multilingual case switching, source inspection, model details and reload.
- All 26 projected replies and all 13 shared prefixes match their saved sources
  exactly. All 1,497 original files and 83 bundle files retain their recorded
  hashes after inspection.

This work makes existing evidence inspectable; it does not add a result or adopt
the adapter. No model calls, training, labels or further experiment are queued.
Implementation and documentation are saved locally; private artifacts remain
ignored and nothing is published.
