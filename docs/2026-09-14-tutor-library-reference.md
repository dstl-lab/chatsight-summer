# Give the tutor an explicit library reference

The first live tutor exchange identified a concrete failure: the tutor saw
Babypandas 1.0.0 in the activity but recommended an unavailable method. The
declaration reached the prompt correctly; a package name did not supply enough
API guidance. The saved failure and its six-decision stopping rule remain intact.

Add an optional reference to the existing tutor command. Its four required fields
are `library`, `library_version`, `text` and `source`, all nonblank strings. Match
the library and version exactly to the already snapshotted activity before creating
output or dispatching a provider. Include the exact reference in the tutor request
and its receipt. The student receives only the tutor's actual reply; the reference
does not enter student state, become feedback or change the student prompt.

Without a reference, preserve the original tutor prompt and input shape exactly.
Use the existing state-bound continuation and receipt handling. A source URL is
provenance supplied by the researcher, not an authority check or an instruction
to fetch the URL. Matching identifiers establishes declared applicability, not
truth or compliance. This adds no method blacklist, automatic document retrieval,
grader changes or claim that all tutor responses become correct.

Ship one short, task-independent Babypandas reference alongside the declared
runtime. Its statements are paraphrased from the project's
[API implementation documentation](https://babypandas.readthedocs.io/en/latest/_modules/bpd.html)
and [column-selection documentation](https://babypandas.readthedocs.io/en/latest/_autosummary/bpd.DataFrame.get.html),
then checked against the existing immutable local image. The note describes column
selection and distinct-value operations without supplying a completed assignment.
Keep the verification receipt separate from student observations.

Completion requires offline tests for exact reference delivery, unchanged input
when omitted, version/library mismatch rejection before dispatch, CLI integration
and student-input isolation; independently check the shipped API facts in the
declared runtime. No new student trajectory, model batch or human labeling review
is needed to establish this input-path change. Whether the model follows the
reference remains unmeasured by these checks.

## Use the reference

For an awaiting-tutor session using Babypandas 1.0.0:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.notebook_tutor data/my-student --policy-file policy.txt --reference-file runtime/notebook/babypandas-1.0.0-reference.json --output data/tutor-exchange-1 --send
```

The same optional format can carry a supplied API note for a different declared
library/version. No course ID or assignment-specific code is required. The current
runtime still supports only its existing declared activity; a reference does not
install a library or extend the executor. Omit `--reference-file` to retain the
original prompt. An explicitly supplied file containing JSON `null` is invalid.
The exact parsed object, including its source string and whitespace within text,
is retained in `request.library_reference`. The runner does not fetch its source.

## Completed verification

The tutor adapter now accepts the optional reference, checks exact applicability
and supplies it as API evidence while retaining the teaching policy. Two new
regressions and the extended CLI/default-prompt checks pass. The related final
offline suite reports **38 passed, 1 skipped**; the skipped case is the full
container integration test, not the separate reference verification.

One authored check ran in the existing immutable image with Babypandas 1.0.0. It
asserted that column selection uses `get()`, bracket column selection raises an
indexing error, a Series lacks `nunique()`, and `unique()` returns an array with
the expected distinct values. Counting that array returned 3. This verifies the
shipped note against that exact environment and supplied values; it is neither
a student action nor a grade on the earlier student's final revision. The plan,
reference hash and observation are retained in ignored
`data/episode-pilot/tutor-library-reference-v1/`.

The original live trace still replays exactly with unchanged files and all eight
saved artifact hashes verified. Its original tutor source was verified against
commit 851119b; the prompt used without a reference is byte-identical. No new
student trajectory or completed model generation was produced.

During development, the first JSON-null regression installed its provider stub
too late and reached the real adapter; connection failed at DNS resolution before
a model response. That failed receipt is retained with a test-attempt note. The
test now guards provider initialization before invalid-input checks, and the CLI
rejects explicitly supplied null references before creating output or dispatching.
The final regression suite uses injected providers throughout.

The input-path milestone is complete. The tutor now has an explicit, applicable
reference when supplied, but whether it follows that reference remains unmeasured.
There is no claim that this change guarantees correct hints or better learning.
