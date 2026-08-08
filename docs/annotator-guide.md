# Blind-audit annotator guide

You've been asked to blind-label a sample of student–AI-tutor messages so we
can measure our classifier against human judgment (and measure two humans
against each other — the agreement ceiling). Total time: **about 10–15
minutes.** Thank you!

## What you need from Minchan first

1. This repository (branch `main`), with Python + [uv](https://docs.astral.sh/uv/) installed
   (`uv sync` from the repo root sets up the environment).
2. **A snapshot directory** — e.g. `20260807-d67ba530d3ee-dda99f/`. It
   contains real student conversations (IRB-covered), which is why it is
   **never in git**. Minchan hands it to you directly (AirDrop/USB/secure
   share — not email attachments, not Slack, not cloud links). Put it at
   `data/snapshots/<snapshot_id>/` inside the repo. You must be covered by
   the course's IRB protocol to handle it — if you're not sure, ask before
   accepting the folder.
3. The exact command to run (Minchan copies it from the run he wants
   audited; a typical one looks like this):

```bash
uv run python -m src.eval.audit_server \
    data/snapshots/20260807-d67ba530d3ee-dda99f \
    --n-per-label 8 --seed 0 \
    --annotator YOURNAME \
    --exclude-review-sample 6 \
    --profile profiles/dsc10.json
```

Replace `YOURNAME` with your first name (it names your answer file). Then
open **http://127.0.0.1:8399** in your browser. Everything stays on your
machine — the server binds localhost only and makes no network calls.

## How the labeling works

- You go through **one label at a time** ("pass 1/13"), with that label's
  definition and criteria pinned at the top in its layer color. Keep only
  that one criterion in mind.
- For each message, press **`y`** (the label applies) or **`n`** (it
  doesn't). The page auto-advances. Arrow keys go back if you want to
  change an answer; the card shows your current answer for this message.
- Judge the **highlighted student message** using the surrounding
  conversation shown above/below it and the "time since the tutor's last
  message" — the act, not just the surface words. A bare "1.6" can be an
  answer request; a pasted error can be a help request.
- The final pass is **"no label fits"**: press `y` only if the message
  shows a student act that none of the labels captured.
- There are no model answers on this page by design — do not ask what "the
  AI said" for a message, and don't discuss messages with anyone who has
  seen model labels until after you submit. Independent judgment is the
  entire value of this exercise.
- Don't overthink: your first considered read is what we want. There are no
  trick questions and no grade.

When you finish the last pass, click **Submit all passes** once. You'll see
"Saved."

## Sending results back

Your answers are written to:

```
data/audit/<snapshot_id>/human-labels-YOURNAME.json
```

**This file is safe to send through normal channels** (email/Slack): it
contains only message ID numbers and your yes/no answers — no student text.
Send it to Minchan. Do **not** send the snapshot
directory itself anywhere, and delete it when you're done
(`rm -r data/snapshots/<snapshot_id>` — your answers file is all we need).

## What happens with your labels

They become ground truth: per-label precision/recall for the classifier,
and — combined with a second annotator's file on the same sample — the
human-agreement ceiling every reported number is judged against
(CLAUDE.md invariant 2). Your labels are never shown to the model and never
used for training; they only ever judge.
