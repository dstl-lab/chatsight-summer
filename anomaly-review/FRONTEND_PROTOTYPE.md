# Instructor Frontend Prototype

On the integration branch, [FINDINGS_INTEGRATION.md](FINDINGS_INTEGRATION.md)
supersedes the synthetic-only data/loading limitations below. This original
design describes Steven’s preserved demo; new review bundles are imported locally.

## Purpose

This frontend demonstrates an instructor workflow for reviewing potentially concerning AI tutor sessions. It is an HCI prototype, not an anomaly detector. It does not make causal claims about the tutor.

All displayed students, conversations, priorities, reference ranges, and metrics are synthetic. The prototype never reads a database or calls an LLM.

## Stack

- React for component structure and local interaction state.
- TypeScript for the versioned UI data contract.
- Vite for a small local development server and production build.
- Lucide React for interface icons.
- Vitest and Testing Library for data and interaction tests.

This stack adds no application backend. The built output is a static site.

## Data flow

1. `fixtures/frontend_demo_sessions.json` contains canonical synthetic events.
2. The existing normalizer reconstructs question-level episodes.
3. The Phase 3A calculator produces evidence-linked behavioral metrics.
4. `session_review.demo_export` converts those reports into the versioned frontend contract.
5. `frontend/src/data/demo-data.json` is the generated static dataset consumed by React.

The exporter test verifies that the committed frontend data exactly matches the pipeline output. Every displayed metric reason links to normalized event references, and every timeline item displays its canonical source event ID and normalized reference.

## Interface structure

### Dashboard

The top summary shows total sessions, illustratively flagged sessions, high-priority sessions, and locally reviewed sessions. The queue supports text search and priority filtering. Selecting a row opens the investigation view and writes the selection to the page URL.

### Investigation

The investigation view includes:

- observed active time and an illustrative reference band;
- failed checks after help, repeated failures, tutor requests, and explicit outcome;
- clickable flag reasons that scroll to and highlight supporting events;
- timeline filters for conversation, notebook, and check events;
- pre-help, help-boundary, post-help, and ambiguous ordering labels;
- student messages, tutor responses, code edits, executions, checks, statuses, and inactivity gaps;
- before-and-after code views where source is available;
- canonical event IDs and normalized evidence references.

### Instructor review

An instructor can classify a session as a potential tutor issue, student struggle without apparent tutor issue, or insufficient evidence. Notes and labels are stored in browser local storage only. There is no shared persistence or export in this prototype.

## Synthetic scenarios

- Quick recovery after one tutor response.
- Repeated failed checks and resumed work after tutor assistance.
- Multiple tutor interactions before recovery.
- Missing outcome and ambiguous timestamp ordering.

Unknown metrics remain unknown instead of being displayed as zero.

## Placeholders

The following are manually configured solely to demonstrate the workflow:

- queue ranking;
- high, medium, and routine priority;
- flagged status;
- question-level reference time bands;
- short human-readable reason titles and descriptions.

They are not research findings, baseline statistics, anomaly scores, or model diagnoses.

## Future integration boundary

Phase 3B can later produce records matching `frontend/src/types.ts`. A real data source would replace the imported static JSON while preserving the dashboard and investigation components. The future adapter must supply:

- session identity and question scope;
- ranking and eligibility provenance;
- metric values with explicit known or unknown status;
- reason descriptions with supporting event references;
- chronological source events;
- any approved pseudonymous identifiers.

The UI should not calculate anomaly rankings. It should display ranked results and evidence produced by a separately tested analysis layer.
