# Evaluate notebook work in a declared runtime

The retained notebook failure probe mixed learner behavior with an incomplete
checker and an unspecified table library. Resolve that boundary with one new
standalone container checker. Keep all completed loops, inputs and results frozen;
this is a new environment, not a retrospective correction to the earlier trace.

An activity specifies an immutable Docker image ID, table library and version,
table/column/result names and authored string data. This first activity checks a
distinct count with no missing values. The container holds pinned Python-family,
NumPy, pandas and Babypandas dependencies and the worker. Record its actual Python
and library versions before evaluating the submitted cell. A version mismatch
prevents evaluation. The same method can succeed in one declared library and
raise in another; code spelling alone does not determine correctness.

Run source only inside a local Docker container, with no host mounts or injected
host environment, no network, a read-only root, an unprivileged user, dropped
capabilities, no privilege escalation and bounded memory/processes/CPU/time/output.
Only a temporary in-container scratch area is writable. The parent reads bounded
output and removes its uniquely named container on success, error or limit.
Docker availability/image failures never become student errors. Do not substitute
host execution when Docker is unavailable.

The worker evaluates the cell and returns the named scalar or an exception.
The parent checks the returned value against the authored expected count; the
expected answer and pass/fail decision do not enter the worker. Preserve separate
statuses for checked answers, runtime/result-retrieval errors, execution limits
and environment/protocol errors. Only checked answers have Boolean success.
Bind observations to branch, revision, exact source, activity/image and checker;
retain the actual runtime fingerprint. These bindings support provenance and
stale-state rejection, not proof against adversarial answer fabrication.

Expose `check_work` and `require_current` in a new module. Do not duplicate the
behavior loop or route ungraded outcomes through its older Boolean grader type.
Use one authored integration check covering alternate code forms, a wrong answer,
different library behavior, runtime error, resource limits, wrong environment and
stale bindings. Source is unrestricted Python within the container; there is no
answer-spelling allowlist or claim of general notebook/session reconstruction.
The scoped result is one cell on supplied data, not deployed-course success,
learner fidelity, mastery or a recovered student kernel.

## Implemented and verified

`src/eval/notebook_runtime.py` now exposes the checker. The container worker lives
in `runtime/notebook/worker.py`; the Dockerfile pins the public base digest and
the three selected library versions. The verified local Linux arm64 image is
`sha256:02040aecf2a21b25a5d4724db297844c0cd5d550f0209b236a92c59feb0839e5`:
Python 3.13.15, pandas 2.3.3, Babypandas 1.0.0, NumPy 2.3.3.
The immutable built image is the runtime boundary; a rebuild can resolve other
transitive package versions and must be recorded as a new environment.

The first worker build exposed a setup error: Babypandas requires the DataFrame
data argument by keyword. The shared constructor now works with both libraries.
The original image, failure log and corrected build receipts remain under ignored
`data/episode-pilot/notebook-runtime-v1/`; setup failure was never graded as a
student mistake. Nine final worker controls pass. Controller checks cover actual
execution, alternate source forms, wrong answers, runtime/setup errors, timeout,
direct output flooding, host-file isolation, read-only root and blocked network.
Malformed protocol and cleanup-error regressions pass. Timeout is part of the
observation binding. An independent review found no remaining blocking issue.

Both retained authored revisions were evaluated separately in newly declared
environments. This is four local checks with no model requests:

| Retained revision | New pandas environment | New Babypandas environment |
|---|---|---|
| 1, with trailing display expression | Count 3; pass | AttributeError; ungraded |
| 2, without trailing display expression | Count 3; pass | AttributeError; ungraded |

The original trajectory still ends at its action limit with unavailable feedback
and ungraded work. These new observations do not establish which environment the
original unspecified activity intended. All 13 new artifact/source pins verify
offline, including the original fixture and result. The full suite passes 319
tests with the existing Starlette/httpx deprecation warning. No temporary checker
containers remained after validation. Previous source modules were not changed.

## Running the checker

Build only the small runtime directory, then select the resulting immutable ID:

```sh
docker build -t chatsight-notebook-runtime:declared-v1 runtime/notebook
export NOTEBOOK_RUNTIME_IMAGE="$(docker image inspect --format '{{.Id}}' chatsight-notebook-runtime:declared-v1)"
python -m pytest tests/test_notebook_runtime.py -q
```

`check_work` accepts a work dictionary containing `source` and `revision`, a
`branch_id`, and an activity dictionary containing `image_id`, `library`,
`library_version`, `table`, `column`, `result`, and string `values`. The integration
test contains a complete authored example. `require_current` takes the same work,
activity, branch and timeout; changes invalidate old feedback. Docker must already
be running with a local Unix-socket context and the declared image present.
There is no host fallback or implicit image download.

This worker executes cooperative generated learner code. Full Python can forge
its own output protocol; source/image bindings are not an integrity-protected
grading witness. One returned integer on one supplied dataset is not a general
correctness proof. The older bounded behavior loops remain frozen. The next
behavior experiment should consume these explicit environment/error states in a
new run, with the library visible before the model chooses code.
