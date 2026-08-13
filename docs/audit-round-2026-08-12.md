# Audit round 2 — support-targeted (August 2026, sunset vintage)

Round 2 targets the three labels that round 1 put on the admission path:
**Seeking Validation, bare-assignment-reference, Conceptual
Clarification**. Goal: enough blind positive-support per label to make an
admit/deny call under the threshold proposal. **Time: about 25 minutes**
(3 passes, 144 quick judgments). Same harness as round 1; only the
snapshot and command changed.

## Setup

1. Pull this repo on `main`; `uv sync` if you haven't since last time.
2. Get the new snapshot folder **`20260811-1d1e79d39fda-7bc759/`** from
   Minchan via wormhole (same as last round: he runs
   `uvx --from magic-wormhole wormhole send <folder>` and tells you the
   code; you run `uvx --from magic-wormhole wormhole receive` and enter
   it). Put it at `data/snapshots/20260811-1d1e79d39fda-7bc759/` and
   delete it when done.
3. You still need your round-1 answers file at
   `data/audit/20260810-b975dcfde38c-927c22/human-labels-YOURNAME.json`
   — the command below uses it to keep messages you've already seen (with
   the model's answers revealed) out of this round. If you deleted it,
   ask Minchan to wormhole it back.

## Run it

```bash
uv run python -m src.eval.audit_server data/snapshots/20260811-1d1e79d39fda-7bc759 \
    --n-per-label 48 --seed 1 --pos-fraction 0.85 --annotator YOURNAME \
    --labels "Seeking Validation,bare-assignment-reference,Conceptual Clarification" \
    --exclude-audit data/audit/20260810-b975dcfde38c-927c22/human-labels-YOURNAME.json \
    --profile profiles/dsc10.json
```

Replace `YOURNAME` (first name, lowercase) in **both** places. Open
**http://127.0.0.1:8399**. Everything else works exactly like round 1:
one label per pass, `y`/`n` keys, autosave on every answer, derived
no-label-fits, submit once at the end, reveal after.

## Rules (same as round 1)

- Work alone; no discussing messages or labels until everyone submits.
- First considered read is the right read.
- Judge the act using the surrounding conversation and the autograder
  lines — a bare "1.6" can be an answer request.

## Send back

Email/Slack `data/audit/20260811-1d1e79d39fda-7bc759/human-labels-YOURNAME.json`
to Minchan (IDs and yes/no only — safe to send), then delete the
snapshot folder.

## Why this composition (for the record, not for annotators)

Support-targeted rounds spend 85% of each label's budget on
model-positive messages because the admission threshold needs ≥25 blind
human positives per label and precision evidence is what positives buy;
the remaining 15% goes to abstained/random negatives as recall probes.
Round-1 messages are excluded (the post-submit reveal anchored them —
invariant 8); both annotators judged the same round-1 keys, so
per-annotator exclusion files yield identical round-2 samples. Known
limit going in: bare-assignment-reference has only 16 unanchored
model-positives in this 235-row snapshot, so its support will land
around 12–16 — provisional either way; admitting it needs a larger
mass-labeled corpus, not more annotator time on this one.
