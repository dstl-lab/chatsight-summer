# Professor-facing lab briefing

## Purpose

The viewer starts with a direct question: “What happened in Lab 1?” It shows a
two-sentence explanation and a small set of distinct findings instead of a
matrix of every tutor-use combination.

Each finding has four parts:

1. plain-language explanation,
2. exact evidence computed from the event bundle,
3. a question the professor may want to investigate, and
4. expandable synthetic student examples.

Question-by-question bars appear only when the selected fact is a question
comparison.

## Data boundary

The current briefing accepts detailed journeys and transcripts only when the
bundle is explicitly marked `synthetic`. A future real-data implementation
must use aggregate-only input unless a separate review changes that policy.

Synthetic findings describe the generated scenario. They are not estimates of
real DSC 10 behavior.

## Generation contract

`src/viewer/briefing.py` first builds a deterministic packet containing:

- stable computed fact IDs and their display-ready evidence,
- Gemini classifications for one student's complete work on one question,
- stable synthetic journey IDs,
- compact journey measures and transcript turns, and
- explicit interpretation limits.

Gemini 2.5 Flash receives this packet in one structured-output request. It may
select fact and journey IDs and write explanations, but it does not supply the
displayed counts or percentages. The backend rejects unknown IDs, repeated
facts, unsupported causal or intent language, and invalid output structure.
Supporting examples are checked against the selected facts and replaced by
deterministic relevant examples when necessary.

If generation or validation fails, the viewer uses a deterministic fallback.

Before briefing generation, `src/viewer/classification.py` classifies every
tutor-using student-question record from all of its tutor messages and
surrounding events. API requests are batched only to stay within output limits.
The analysis unit remains one student per assignment question, so students who
send more messages are not counted more heavily. The synthetic run records
agreement with generator labels as a validation measure; model classifications
remain interpretations rather than ground truth.

## Cache and provenance

The generator writes `briefing.json` beside `events.jsonl`. The artifact
records:

- schema version,
- event bundle ID,
- source kind,
- model name,
- UTC generation time,
- evidence-packet hash, and
- prompt hash.

The API key is read from the environment or an explicitly supplied dotenv
path. It is never included in prompts, output, logs, or cache files.

The viewer accepts a cached artifact only when its bundle, packet, prompt, and
source kind still match. The existing `/api/insights` and pathway-example APIs
remain available for audits and tests, but the grid is not part of the main
interface.
