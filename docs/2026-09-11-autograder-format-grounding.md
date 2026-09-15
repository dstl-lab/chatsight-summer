# Ground autograder text in the environment

Minchan's latest review redirects continuity case 1: the displayed alternatives
should be checked against the actual autograder setup and broader dataset, rather
than judged as two student writing styles. Continuity case 7's two candidates are
plausible. Preserve that feedback verbatim in the private review record; do not
infer a preferred candidate, a separate formatting judgment or reply probability.

Trace original source data and the logging/formatting path before changing another
generator instruction. Search the available immutable snapshots for actual test
output, separating student-pasted artifacts from tutor prose and generated
continuations. Deduplicate overlapping exports and retain notebook, source-turn
and snapshot provenance. Record the broader exposure; these searched data cannot
subsequently be described as untouched holdout material for this diagnostic.

If local snapshots cannot establish the format, inspect the existing raw-log
ingestion path and narrowly scoped autograder/notebook evidence where available.
Raw execution events, notebook outputs, pasted text and tutor interpretations have
different evidentiary roles. A success flag alone does not define rendered text,
and observed formatting does not establish that the generated code would pass.
Keep raw excerpts and any new source exports in ignored data, with source hashes.

The simulation distinction to resolve is between the environment's observable
output and the student's decision to transmit it. Neither should be inferred from
the other's surface form. Do not require another human preference judgment to
settle a formatter question, treat the previous comparison as demonstrated
behavioral improvement, overwrite frozen prompts/results, or launch another
model batch while investigating this correction.

## Findings

Eight unique available snapshots contain 252 unique conversations and 3,522
original turns after deduplication. Student text contains 27 occurrences of the
passing-subtest marker across 20 turns; every matching turn also contains a
failed-test marker. The aggregate all-pass phrase appears once, in tutor prose,
and never in student text in this search. This establishes mixed-result pastes,
not the complete all-pass format or a general absence of student success reports.

A bounded read-only ingestion diagnostic then checked raw event payloads. The
selected conversation's nearby grader events contain two failed question results,
each with a failed first subtest and a passing second subtest. Five successful
events for the same notebook and question, selected chronologically within the
same assignment period, all contain the aggregate all-pass text. These are five
events, not necessarily five independent students or a prevalence estimate.

With an invented question identifier, the verified logged success format is:

```text
q_example results: All test cases passed!
```

The per-subtest heading belongs to the detailed result format, for example:

```text
q_example results:
    q_example - 1 result:
        ✅ Test case passed

    q_example - 2 result:
        ❌ Test case failed
        Invented failure details
```

Local assignment sources match the original failing check. Installed Otter 6.1.6
source explains both formats, and an executable check reproduces them using
invented result objects without running student code. Its all-pass notebook HTML
instead displays the question identifier, “passed!” and a decorative emoji.
The original conversation's captured grader cell has an empty outputs list and
no relevant version metadata: logged plaintext is verified, but the deployed
package version and notebook HTML display are not. Older matching assignment
sources and a local installation alone cannot establish that deployment.

## Consequence for this comparison

Continuity case 1 candidate B combines an aggregate success phrase with a
per-subtest heading; it is not the verified full logged all-pass format.
Candidate A resembles a passing-subtest fragment, which can occur within a failed
question result; it does not establish that the whole question passed. A student
could paste only part of an output, so neither finding becomes an inferred human
plausibility verdict. Minchan's redirection is preserved without categorical
content, formatting or reply-occurrence scores.

Continuity case 7's two candidates are recorded as plausible conditional on a
reply. No preference, separate formatting score or reply probability is inferred.
Case 5's identical outputs and the eight other comparisons remain unchanged.
This feedback does not establish that the prompt variant improved behavior.

For subsequent simulation work, grader artifacts should come from a verified
environment representation; student behavior determines whether and what portion
to communicate. A formatting exemplar cannot determine whether hypothetical code
passes. Keep grader state unknown unless execution or an explicit scenario
supplies it, and do not splice a recorded future outcome into a diverged branch.
No new generator rule, formatter library or model batch is needed for this
correction. Preserve the frozen comparison as the record of the original issue.

## Evidence and verification

Private evidence is under `data/episode-pilot/autograder-format-v1/`:
`snapshot-audit.json`, `source-trace.json`, `formatter-check.json`, and three
read-only query receipts with their SQL, parameters and archived ingestion probe.
`ingestion-verification.json` pins these files and verifies the query/parameter/
probe hashes and observed result counts. PostgreSQL enforced read-only mode with
a 20-second statement timeout. The task-owned tunnels exited after the reads;
connection resets and retries are recorded. No live access was added to evaluation
or simulation, and no persistent ingestion API was introduced.

The formatter check remains runnable locally:

```sh
uv run python data/episode-pilot/autograder-format-v1/check_formatter.py
```

It requires the pinned local Otter source recorded in its receipt. Raw excerpts,
identifiers, generated messages and exact feedback remain ignored. The broader
snapshot search and new source reads are recorded as development exposure, not
untouched evaluation data. This diagnostic verifies output format, not student
reply frequency, code correctness, learning or tutor-policy effects.
