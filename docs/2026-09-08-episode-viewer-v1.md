# Question-scoped episode viewer V1

Date: 2026-09-08. Status: approved direction for implementation.

## Decision

Build a third localhost-only instructor surface in this repository for
inspecting question-scoped notebook/tutor episodes. The JupyterLab extension
remains the telemetry producer. This repository owns validation,
reconstruction, derived measures, and visualization.

The new episode model is canonical. Existing `conversation_id` values are
optional source references for transcript linkage; they do not define episode
identity or boundaries. This avoids adapting the new behavioral model to the
older conversation-centered solution.

## V1 question

For one assignment question, what observable paths did students take before
and after using the tutor, and which raw events support each displayed
measure?

## Input boundary

V1 imports a schema-versioned JSONL event stream produced by
`dsc10-tutor-jlab`. The importer:

- accepts episode envelope schema `1.0.0`;
- skips separately marked legacy rows during reconstruction;
- validates required fields and privacy-forbidden payload keys;
- deduplicates by `event_id`;
- preserves `unknown` question identity and provenance;
- optionally indexes local legacy tutor text by `conversation_id` for
  localhost-only drill-down.

No viewer code opens the live Postgres. Imported data and derived artifacts
remain under gitignored `data/`.

## Canonical identifiers

- `episode_id`: opaque deterministic ID derived from the reconstruction
  version and episode event boundaries.
- `student_key`: opaque deterministic display key; raw student identity is
  never returned by the viewer API.
- `event_id`: source event identity and deduplication key.
- `correlation_id`: source execution-chain linkage.
- `turn_id` and `response_id`: source tutor-turn linkage.
- `conversation_id`: nullable legacy transcript reference only.

## Episode boundaries

Events are ordered by client occurrence time, sequence, and event ID, then
grouped by student, notebook, and question. A new episode is created after:

- successful autograder completion;
- thirty minutes of inactivity;
- end of available data.

Question changes naturally enter a different question stream. V1 does not
claim a question-change or notebook-close boundary until those event types are
actually emitted.

## V1 screens

1. **Question overview.** Student denominator, ask-before-attempt rate, median
   errors before asking, exact tutor-code-use rate, test-after-tutor rate,
   pass-after-tutor rate, and unresolved rate.
2. **Observed pattern breakdown.** Deterministic rules such as
   ask-before-attempt, struggle-then-ask, tutor-code transfer,
   revised-after-response, and unresolved.
3. **Episode timeline.** Ordered notebook, tutor, provenance, and autograder
   events with relative timing and measure provenance.
4. **Data quality.** Rejected rows, duplicate rows, legacy rows, unknown
   question IDs, schema version, reconstruction version, and source kind.
5. **Optional transcript.** Local tutor query/response text joined only through
   a source `conversation_id`.

## Claim discipline

The UI describes recorded behavior only:

- “asked before a recorded attempt,” not “was answer-seeking”;
- “pasted tutor code then passed,” not “the tutor caused success”;
- “no later recorded pass,” not “gave up”;
- `unknown` remains `unknown`.

V1 has no LLM summaries, inferred personas, causal recommendations, learning
claims, clustering, or composite risk score.

## Reuse and separation

Reuse FastAPI, Pydantic, gitignored data conventions, localhost binding,
manifest-style provenance, and existing test patterns. Do not add episode
state to `LoopSession` or the blind-audit server; their workflows and
measurement constraints remain separate.

## Deferred

- shared or production deployment, authentication, and instructor roles;
- direct ingestion from the shared logging API or Postgres;
- live streaming;
- cross-quarter comparisons;
- archetype generation and policy replay;
- semantic or LLM-generated episode interpretation.

## Success criterion

An instructor can select a question, understand the distribution of observable
help-seeking paths, open every contributing episode, and trace every measure
to ordered source events without exposing raw student identity.
