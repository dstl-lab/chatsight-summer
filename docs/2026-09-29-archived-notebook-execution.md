# Execute the captured task on archived course data

Minchan approved checking the saved notebook's dependencies, then connecting the
captured work and simulated edit to real execution if those dependencies could
be supplied. Keep the completed source-only branch and all earlier runs unchanged.

The captured setup imports Babypandas and loads a local CSV. The selected task
counts distinct strings in one column; the table's variable name does not imply
a plotting task. Two local course archives contain byte-identical CSV files with
70,183 rows and 24 columns. The student-facing archive matches the captured loading
cell, selected question and displayed column names. The capture contains no
dataset checksum or package versions, so this is an explicitly declared archival
environment, not a recovered historical kernel or proof of historical file identity.

The current public checker accepts only 2,048 string values and its worker reads
at most 1 MiB. Do not truncate or deduplicate the real table to fit, change saved
engine implementations, or pass invented activity data. For this bounded probe,
derive a separate local image from the existing immutable runtime, with the full
CSV and a small probe worker. Reuse the existing container isolation and cleanup
helpers. No network, host mounts, host execution or implicit image pulls are used.
Record the asset, source, worker and image hashes, actual library versions, literal
value/output or error, and create a pending receipt before either code execution.

Run the captured cell and the saved simulated revision once each. These checks
occur after generation and were not available to that already-saved decision.
Keep their results separate from its original null observation and from the course
grader. Add an optional, hash-bound read-only execution attachment to the existing
browser branch: same notebook/chat layout, separate local output beneath each
revision, explicit archival provenance, no execution or provider controls.

All course assets, work and detailed results stay in ignored local data. Use an
authored check for the worker and browser binding/escaping boundaries before real
execution. Any later student reaction must be a new, explicitly recorded request
whose input includes only the earlier dialogue, saved work and actual new feedback;
the completed one-decision branch cannot be resumed or rewritten.

## Completed execution and display

The dependency inventory verifies eight original source files, seven completed
branch artifacts, and the two identical archive assets. The archived notebook's
setup has some different display, plotting and grader settings. Only the necessary
Babypandas import and CSV loading operation are reconstructed; no instructor
solutions, later messages or course grader enter either check.

The first image build treated the raw base image ID as a registry name and failed
before building. A local-only build using the verified existing tag succeeded;
its command, log, base layers and immutable output image are recorded. The first
probe then failed in its own setup because Babypandas DataFrames do not implement
`len()`. Neither selected cell executed. That failed probe remains unchanged in
`data/notebook-course-execution-v1/`.

The separate V2 probe changes the shape check to use `shape[0]`, preserving all
70,183 rows and 24 columns. Its image is
`sha256:5a4faf5e0cfc5a8bd6603cddf7b5e428c6e74eee6111b90bab483f0d0a561be4`.
Actual versions are Python 3.13.15, Babypandas 1.0.0, pandas 2.3.3 and NumPy 2.3.3.
Both selected sources execute once: captured work raises `AttributeError`, and
the saved simulated revision returns **2,850**. Neither result is a course grade.
The temporary execution containers were removed.

The read-only workspace at <http://127.0.0.1:8448/> displays these two retrospective
checks beneath the corresponding code revisions. Its original dialogue and null
student feedback remain unchanged: the already-generated decision did not see
these later results. The source-only view still works without an attachment.

```sh
python -m src.agents.browser_workspace --notebook-branch /path/to/saved-branch \
  --notebook-execution /path/to/results.json \
  --notebook-execution-sha256 <raw-file-sha256> --port 8448
```

The attachment is bound to the checkpoint, saved decision and each exact source.
Every reload verifies its hash and shape; paths inside the artifact are not used.
Values, errors and runtime details are escaped, and there are no sending or
execution routes. Independent review found no actionable issue. Verification:
832 Python tests pass, three optional tests skip, the Node controller/syntax
checks pass, and live localhost HTTP verifies both results. The existing
Starlette/httpx deprecation warning remains. Offline replay verifies both probe
versions and preserved source/branch/asset hashes. The frozen test file briefly
received additional assertions during preparation; its exact pinned bytes were
restored before execution and the extended authored check retained separately.

## Remaining student reaction

One separate reaction is prepared in the ignored V2 directory. Its 4,024-character
prompt contains the selected task, two original dialogue turns, saved simulated
edit and actual local result/runtime. It contains no CSV rows or correctness grade.
The existing action schema and provider helper are reused, with one provider
attempt at most, no tutor request and no follow-on execution. The feedback is
explicitly a researcher-triggered intervention in a declared archival environment.

Automatic approval review rejected launch because this new private payload to
Google Gemini requires specific authorization. `reaction-send-blocked.json` binds
that rejection to the exact prepared prompt; no reaction request receipt exists
and zero new provider calls occurred. The executable-work milestone is complete;
the student reaction remains pending that authorization. No labels, training,
fidelity score, remote publication or change to a closed study was made.
