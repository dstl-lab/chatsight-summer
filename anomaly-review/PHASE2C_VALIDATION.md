# Phase 2C Real-Data Integration Preparation

## Current status

The integration infrastructure is implemented and tested only with synthetic JSON.
No real AI tutor export has been inspected, mapped, or validated. A mapping remains
`provisional` until representative source records have been compared manually with
the normalized output.

This project remains isolated from ChatSight. It reads local files, performs no
database writes, makes no network calls, and does not modify its source JSON.

## Pipeline

```text
approved local JSON
  -> configurable JSON adapter
  -> canonical event validation
  -> aggregate data-quality report
  -> question-session reconstruction
  -> Phase 3A behavioral metrics
```

Source-specific field extraction is implemented in `session_review/json_adapter.py`.
Question reconstruction and metrics receive only canonical events, so connecting a
new export does not require changing either module.

Each accepted event retains:

- the input file SHA-256;
- its JSON pointer in the source export;
- a hash of the original record;
- the adapter name;
- its source event identifier in the canonical event.

Rejected and unassigned records remain in a pointer-based manifest. They are not
silently removed from the validation accounting.

## Required source documentation or sample

Before creating the real mapping, obtain schema documentation or a small approved,
deidentified sample that contains representative records for every available event
type. Confirm all of the following:

1. Whether the export is one JSON document containing an array, and where that array lives.
2. Event type names and payload shapes.
3. Student, course, cohort, assignment, assignment-version, notebook, conversation,
   question, event, request, response, cell, revision, execution, check, and grader IDs.
4. The uniqueness scope and stability of each identifier.
5. Timestamp format, units, time zone, source clock, and ordering guarantees.
6. Whether a source sequence number belongs to a documented ordering stream.
7. How explicit question attribution is recorded. If attribution is derived, obtain
   the versioned mapping and its provenance.
8. How tutor request, streaming, completion, cancellation, retry, and failure are represented.
9. Which source evidence proves that a tutor response completed.
10. Whether notebook edits are full snapshots, diffs, or periodic captures.
11. How executions bind to code revisions and how grader results bind to executions.
12. Whether an autograder attempt without a result is a distinct event and how its
    unknown outcome should be represented.
13. Which events establish question completion, reopening, or unfinished status.
14. Export coverage boundaries and whether the export claims complete or partial coverage.

Do not infer these answers from the synthetic example. Its source field names are invented.

## Mapping document

The mapping is declarative JSON. It contains:

- `records_pointer`: JSON pointer to the source record array;
- `event_type_pointer`: record-relative pointer to the source event type;
- `common_fields`: pointers for canonical event and session fields;
- `question`: explicit or versioned verified question attribution;
- `event_types`: a source type to canonical type mapping;
- per-type `fields`, `constants`, and explicit `value_maps`.

JSON pointers follow RFC 6901 escaping. Unknown source event types and unmapped enum
values are rejected with safe diagnostic codes. The adapter does not inspect message
text or code to guess event type, question, status, or identifiers.

`fixtures/phase2c_mapping.synthetic.json` demonstrates the interface only. It is not
the real source mapping and must not be reused without checking every field.

Supported canonical detail types are:

- `student_message`
- `tutor_response`
- `code_edit`
- `execution`
- `check_result`
- `question_status`
- `activity`

An attempt-only autograder record may be represented as `check_result` with an unknown
outcome only if the real source semantics confirm that interpretation.

## Local validation command

Place the approved export and its reviewed mapping under an ignored directory such as
`anomaly-review/private-data/`. Then run:

```bash
cd /Users/stevenxu/Documents/GitHub/chatsight-summer/anomaly-review
uv sync

uv run session-real-validate \
  private-data/incoming/tutor-export.json \
  --mapping private-data/mappings/tutor-export-v1.json \
  --dataset-id local-validation-001 \
  --quality-output private-data/runs/local-validation-001/quality.json \
  --artifacts-dir private-data/runs/local-validation-001/artifacts
```

Only declare coverage when the data owner confirms it:

```bash
  --coverage-start 2026-09-01T00:00:00Z \
  --coverage-end 2026-09-30T23:59:59Z \
  --coverage-completeness partial
```

All three coverage arguments must be supplied together. Outputs are create-only. The
command refuses to overwrite an existing report or artifact.

The quality report contains aggregate counts, canonical field locations, and source
JSON pointers. It does not contain raw student messages, notebook code, outputs, or
source identifier values. The optional normalization and session artifacts do retain
event content for local manual review, so keep the entire artifacts directory private.

Exit status is:

- `0`: processing completed and no blocking check failed, but manual validation is still required;
- `1`: a report was created and blocking mapping or data issues were found;
- `2`: input, mapping, configuration, or output creation failed.

## Data-quality checks

`session_review/quality.py` reports:

1. missing and duplicated event IDs;
2. missing, invalid, or inconsistent timestamps;
3. inconsistent ordering streams and unresolved timestamp ties;
4. missing or ambiguous question attribution;
5. unknown or conflicting tutor-response completion evidence;
6. unmatched or ambiguous tutor request and response links;
7. check results without reliable question attribution;
8. sessions with insufficient observed activity for common metric comparison;
9. missing or unexpected event types;
10. incomplete session scope and conflicting cross-source identifiers.

Each check states its counting unit, evaluated count, passing count, issue count, and
status. A failed check does not relabel an incomplete session as a student failure.
Missing outcomes remain unknown.

## Manual real-data validation procedure

When the export arrives:

1. Confirm approval, deidentification, date range, and storage restrictions.
2. Record the source schema version and export-generation procedure outside the raw file.
3. Copy the export into `private-data/` and do not rename or edit its contents.
4. Review representative records for every source event type and create a provisional mapping.
5. Run `session-real-validate` and inspect the aggregate quality report first.
6. Resolve mapping failures without changing reconstruction or metric semantics.
7. Select a small stratified sample of reconstructed sessions for manual source comparison.
8. Verify question attribution, tutor completion boundaries, request-response matching,
   execution and check linkage, work-bout gaps, and active-time intervals.
9. Record discrepancies and mapping revisions with versioned adapter names.
10. Only after this review, document the mapping as validated for the specific schema
    version and export range.

## Unverified assumptions

The following remain unverified until the real export is available:

- the export is standard JSON rather than JSON Lines or multiple joined files;
- records are stored in one array;
- all event types needed for reconstruction are included in one export;
- source IDs are deidentified, stable, and joinable across event sources;
- occurrence timestamps are timezone-aware and comparable across source clocks;
- source order or sequence metadata is trustworthy;
- question IDs are explicit or can be derived through an approved versioned mapping;
- tutor completion evidence distinguishes a completed response from a partial stream;
- request and response IDs define a reliable lifecycle;
- notebook revisions, executions, and checks have reliable join keys;
- grader identity and version are sufficient to identify repeated failures;
- question completion has an explicit event distinct from an intermediate passing check;
- export coverage and missing-event guarantees are documented.

No real-data findings or research conclusions should be reported until these assumptions
have been tested against the approved export.
