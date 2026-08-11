# Audit round — August 2026 snapshot (for team annotators)

You're blind-labeling a small sample of student–AI-tutor messages so we
can measure our classifier against human judgment. **Time: about 10
minutes.** Full background lives in `docs/annotator-guide.md`; this page
is everything you need for this round.

## Setup (5 minutes, once)

1. Clone/pull this repo on branch `main`; run `uv sync` in the repo root
   (needs [uv](https://docs.astral.sh/uv/) and Python installed).
2. Get the snapshot folder **`20260810-b975dcfde38c-927c22/`** from
   Minchan **in person — AirDrop or USB, never email/Slack/cloud**. It
   contains real student conversations (IRB-covered); you must be on the
   course's IRB protocol to handle it. Put it at
   `data/snapshots/20260810-b975dcfde38c-927c22/` inside the repo.

## Run it

```bash
uv run python -m src.eval.audit_server data/snapshots/20260810-b975dcfde38c-927c22 \
    --n-per-label 8 --seed 0 --annotator YOURNAME \
    --exclude-review-sample 25 --profile profiles/dsc10.json
```

Replace `YOURNAME` with your first name (lowercase). Open
**http://127.0.0.1:8399**. Everything stays on your machine.

## How it works

- One label at a time (12 short passes, 96 quick judgments). The label's
  definition sits at the top in its layer color — keep only that one
  criterion in mind.
- Press **`y`** (applies) or **`n`** (doesn't) for the highlighted
  student message; the page auto-advances. Arrow keys go back.
- Judge the act, not just the words: use the conversation around the
  message and the "time since tutor's last message" / autograder lines.
  A bare "1.6" can be an answer request; a pasted error can be a help
  request.
- There's no "no label fits" question — answering `n` on everything for
  a message records that automatically.
- **Every answer autosaves.** Close the tab, come back later, nothing is
  lost.
- Click **Submit all passes** once at the end. After submitting you'll
  see a reveal comparing your answers to the model's, with its evidence
  in bold — that's for your curiosity; your answers are already locked.

## Rules that make the data valid

- Work alone. Don't discuss messages or labels with anyone (including
  other annotators) until everyone has submitted — especially not after
  you've seen the reveal.
- First considered read is the right read. No trick questions, no grade.

## Send back

Your answers land in
`data/audit/20260810-b975dcfde38c-927c22/human-labels-YOURNAME.json`.
That file contains only message IDs and your yes/no answers — **safe to
send by email/Slack** to Minchan. Then delete the snapshot folder
(`rm -r data/snapshots/20260810-b975dcfde38c-927c22`).

Your labels become ground truth: they judge the classifier and set the
human-agreement ceiling. They are never shown to the model and never
used for training.
