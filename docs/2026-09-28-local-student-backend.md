# Run a local student through the normal browser workspace

The saved adapters work, but using them currently requires private experiment
launchers. Make the existing structured-reply callback usable from the repository
with explicit local model, Python runtime and optional adapter paths. This is a
reusable simulator connection, not another fidelity experiment or a claim that
the full-pass adapter is better. No model becomes the new default.

Start with one fresh saved chat session. The browser CLI accepts local student
paths and uses typed tutor replies only. Automatic tutor generation is disabled
in both the interface and the server before any receipt or provider request.
Existing default browser and explicitly configured hybrid callbacks retain their
behavior. Notebook sessions, collections and policy workspaces are outside this
first local CLI path; their other runners do not carry its backend binding.

Reuse `student_training.messages` and the existing structured-reply engine.
Run MLX in the explicitly selected Python subprocess; keep imports and optional
runtime packages out of normal app startup. Load local files only with remote
code disabled and offline environment settings. Bound each request to 120 seconds,
256 output tokens, 4,096 total context tokens and the existing 16 GiB checks.
Keep the existing sampling settings. Record a deterministic distinct seed per
saved request, literal prefix, model/adapter identity, settings, token output and
completion/error. Decode token IDs without stripping leading whitespace.

Bind a session to its selected backend and reject later changes. Startup and
replay are read-only; model dispatch requires `--send` and an explicit browser
submission. Preserve terminal errors, incomplete/capped output and timeouts;
never retry, fall back to a provider, or interpret failure as student silence.
Local call records identify the real backend separately from the legacy session
model field. The simulator remains conditional on a reply and cannot infer
notebook work, missing learner identities or whether a student returns.

Verify backend routing, source binding and failures with authored inputs and
fake subprocesses. Check manual-only controls in Python, Node and the browser.
Then allow at most two real local student calls on a new fictional conversation,
with one authored tutor reply, solely to check the integration. Preserve both
results without rerolls. No private course text, cloud requests, new labels,
training, additional evaluation or changes to closed studies are needed.

## Run it

Use the checkout containing this change and the normal project Python environment.
The model must already be downloaded in MLX format, with its tokenizer files.
Supply a separate existing Python environment with MLX-LM installed; the verified
local setup uses MLX-LM 0.31.3 on Apple Silicon. The ordinary project environment
does not need MLX. No model or adapter is installed or selected automatically.

Create one fictional conversation using the existing session creator:

```sh
.venv/bin/python - <<'PY'
from src.agents import chat_student
folder = 'data/local-student-demo'
chat_student.create(folder, model='local-student: see local-student/backend.json',
    max_decisions=2, query={
        'id': 'authored-count', 'conversation_id': 'authored-count',
        'prefix': [
            {'role': 'student', 'text': 'values = [3, 5, 3]\nhow many 3s'},
            {'role': 'tutor', 'text': 'Count the entries equal to 3 in the list.'},
        ],
    })
chat_student.show(folder)
print('Created fictional context; no model requests.')
PY

.venv/bin/python -m src.agents.browser_workspace \
  data/local-student-demo --chat --port 8440 \
  --student-model /absolute/path/to/local-mlx-model \
  --student-python /absolute/path/to/mlx-environment/bin/python \
  --student-adapter /absolute/path/to/adapter-directory
```

Omit `--student-adapter` to use the specified base model. Open
`http://127.0.0.1:8440/` to inspect the saved start. The command above is read-only;
stop the server and add `--send` to enable explicit generation. **Continue run**
generates one student message. **Reply to student** lets you type a tutor message
and generate one continuation. No API key or automatic tutor is involved.
Stop the server with Ctrl+C. The two-decision limit is a budget, not student silence.

Reopen with the same paths to continue, or omit them and `--send` to read saved
messages without loading the model. The first call binds its backend; switching
models, adapters or code requires a fresh session. The normal Gemini entry points
will not continue a locally bound session. A failed or interrupted call is retained
and not resent. Keep the local Python environment unchanged between calls.

`SESSION/local-student/backend.json` records the selected model, adapter, runtime
path, file hashes and settings. Each `call-*` directory preserves the request,
tokens, actual runtime versions, result and process outcome. These records identify
the backend; the older session `model` string is just a label. Keep sessions,
weights, adapters and generated messages inside ignored data directories.
