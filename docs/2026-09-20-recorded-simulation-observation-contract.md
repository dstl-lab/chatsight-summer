# Common observation contract for recorded and simulated sessions

## Decision before implementation

The replay viewer now opens a genuine saved notebook simulation, while the chat
workspace separately opens recorded student conversations. The next engineering
question is not yet how to condition Gemini on private history. First establish
which fields the two sources can honestly place at the same observation boundary.

Implement one local, private packet shape for:

1. a recorded conversation prefix ending at a tutor turn; and
2. a verified saved notebook simulation state.

The common fields are dialogue, the associated tutor boundary, task identity,
selected-cell identity and revision, and a check bound to that revision. Preserve
source and record digests without exposing raw conversation identifiers. Historical
fields absent from the current snapshots stay explicitly unavailable. Do not infer
notebook work from code pasted in chat, derive a course task version from a notebook
name, or turn grader-like text into a source-bound check.

Packet preparation and inspection are offline. This increment makes no Gemini,
database or Docker request and adds no generation command. Private packet output is
create-only and remains under ignored `data/`. A later private-data generation run
must define its exact payload and evidence question separately.

## Contract

Every packet contains:

- `origin`: recorded conversation or saved notebook simulation;
- source, record and opaque-record digests for provenance;
- exact visible dialogue through one tutor boundary;
- task identity status and content digests when the task was supplied;
- selected-cell status, identity kind, source and revision when saved;
- current-check status and revision binding when a verified check exists;
- explicit limitations and a packet content hash.

For a recorded chat snapshot, the available evidence is exact dialogue, source turn
positions, timestamps when present, and the selected tutor boundary. Task/version,
work, cell identity, revision and source-bound checks are unavailable.

For a saved simulation, task identity is a digest of researcher-supplied content,
not a recovered course identifier. The selected cell is stable only inside the
saved synthetic branch and is identified by branch plus cell index. Check feedback
is included only after the existing loader verifies its source/revision/activity
binding. These fields describe a simulation receipt, not observed student behavior.

## Safety and stopping rule

Recorded preparation must accept an explicit tutor-turn boundary and omit all later
turns. Mutating omitted future turns must not change the packet. Raw chatlog,
conversation and notebook identifiers must not appear in the packet. Output files
must not be replaced.

Simulation preparation must use the existing offline loader, make no provider or
execution call, and leave every session file byte-for-byte unchanged. Environment
diagnostics are sanitized through the existing tutor-context projection.

This milestone is complete when authored tests cover future isolation, identifier
redaction, unavailable historical fields, verified simulation work/check bindings,
create-only output and offline immutability, and one local real-snapshot packet can
be compared with the saved live simulation packet. It does not establish fidelity,
same-task historical actions, learning, or permission to send these packets.

## Local use

Create one private packet from an explicit recorded conversation and tutor-turn
boundary:

```sh
uv run python -m src.eval.observation_contract recorded \
  data/snapshots/SNAPSHOT_ID data/workspace/observation/recorded.json \
  --conversation-index 1 --through-turn 3
```

Create the same packet shape from a verified saved notebook simulation:

```sh
uv run python -m src.eval.observation_contract simulation \
  data/workspace/sessions/SESSION data/workspace/observation/simulation.json
```

Both commands create rather than replace their output and print only an availability
summary plus hashes. The JSON contains conversation text or code and remains private.
There is deliberately no generation option in this command.
