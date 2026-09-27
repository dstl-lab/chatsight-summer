# Open the completed communication review directly

**TL;DR:** Make the existing mixed-reference review accessible without an
unrelated replay session, and summarize work presentation using its saved human
judgments. This continues from merged main independently of pending PR #62.

## Scope

Reuse `--comparison`, the verified evidence loader and the current browser view.
Allow a read-only launch without a session folder. Above the individual examples,
show counts of generated messages with and without work, grouped by the recorded
message's work flag. Keep unclear and unfinished judgments explicit; preserve
both occurrences of duplicate draws. Derive counts only from the verified
message judgments, never by executing archived report code.

This makes the completed diagnosis inspectable: generated work occurs in 6/10
draws whose references lack work, and is absent in 2/6 draws whose references
contain work. These are differences from observed messages, not implausibility
rates. One configuration and exposed development cases cannot establish a
grounding improvement or general student fidelity.

No generator change, new metric, model request, label or study is introduced.
The existing studies stay closed. Stop when standalone launch, explicit
denominators, source preservation and browser navigation are verified.

## Open locally

From the checkout containing this change, using the existing private bundle:

```sh
python -m src.agents.browser_workspace \
  --comparison /Users/minchan/github/chatsight-summer/episode-pilot/data/episode-pilot/cached-communication-review-v1 \
  --port 8434
```

The workspace opens on **Reviewed replies**. Choose an example on the left,
read its recorded and simulated messages in the center, and inspect the shared
conversation on the right. The summary covers the full review regardless of
which example is selected. Viewing and reloading make no requests to a model.

## Verification

689 Python tests pass with three optional skips; all three Node navigation checks
and seven Marimo checks pass. Regression coverage verifies direct launch,
disabled generation, duplicate draw weighting and unknown judgments. Independent
code review found no actionable issues. The desktop browser shows all eight
cases and the expected 6/10 and 2/6 counts; switching cases keeps the full-review
summary and changes the context and messages together. All 20 private evidence
files retain their original bytes and modification times.

This completes the increment. PR #62 remains pending and unchanged; no new
experiment, review queue or provider request follows from opening this view.
