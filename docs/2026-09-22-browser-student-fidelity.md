# Student fidelity comparison in the browser

**TL;DR:** Show the completed current-exchange-only versus earlier-dialogue
benchmark in the workspace before generating another batch. Its 64 saved replies
and existing human judgments already answer this first comparison. No new model
requests or labeling are needed; no untouched evaluation batch has been found.

## Reuse the completed experiment

The [fixed help/work benchmark](2026-09-15-help-work-benchmark.md) used eight
conversation cases and four draws per condition. Both conditions received the
same current student request, recorded tutor reply, model, instructions and output
schema. The earlier-dialogue condition additionally received the available
earlier student and tutor messages. The first subsequent recorded student message
was withheld from generation and used as the reference.

The browser exposes the saved conditions, outputs and human coding together.
It preserves the frozen historical experiment: no prompt rewrites, replacement
draws, relabeling, new scoring rules or generator adoption. The original stopping
rule—one frozen run, one coding pass, one report—has already been reached.

The [completed results](2026-09-15-help-work-results.md) show:

| Measure | Earlier dialogue | Current exchange only |
| --- | ---: | ---: |
| Mean combined help/work Brier error | 0.359375 | 0.29296875 |
| Generated messages with work/evidence | 26/32 | 23/32 |
| Generated messages requesting help | 32/32 | 30/32 |

Earlier dialogue has **0.06640625 higher error**, rather than an observed
improvement on this endpoint. All 64 draws produced replies; all 72 messages
(eight references plus 64 outputs) have completed human coding. Lower Brier error
means closer flag agreement here, not a percentage accuracy or a general measure
of student realism.

All eight recorded references were coded **help present, work absent**. A constant
help-only flag prediction therefore scores perfectly, so this set cannot show
whether a simulator preserves work-bearing messages appropriately. The separate
[cached communication diagnostic](2026-09-22-cached-communication-results.md)
contains five work-absent and three work-present references, but only one
historical generator condition. Keep these studies separate; their outputs cannot
be pooled into a new matched comparison.

## What this workspace answers

Tutor-policy comparisons change tutor instructions and generate a tutor reply
and student continuation per policy. This fidelity view instead holds the
**recorded tutor reply fixed** and compares the information supplied to the
student generator. Its historical outputs are read-only. It answers whether
earlier dialogue helped this particular next-message comparison, not whether a
new tutor policy changes real student behavior.

Historical case context and outcomes come from the configured benchmark directory.
The benchmark opens directly without an unrelated replay or authored conversation.
An optional session folder can accompany it; this does not replace its frozen
cases or references. Opening or reloading makes no generation request.

Launch from this worktree with the locally available private benchmark:

```sh
python -m src.agents.browser_workspace \
  --fidelity-comparison /Users/minchan/github/chatsight-summer/episode-pilot/data/episode-pilot/help-work-benchmark-v1 \
  --port 8432
```

The benchmark artifacts remain in ignored local data. The loader reuses the
existing help/work scorer and verifies the saved packet, mapping, returned
judgments and report; no raw conversation content belongs in this document or Git.

## Limits and next decision

All eight canonical course exports have previous audit or development exposure.
The saved chat schema has no learner identifier: conversations are not verified
individual students, and `student_index` is a position within a conversation.
There is no established untouched, student-separated holdout in these files.
This is same-course development evidence, not a test of randomly sampled students
or transfer to another course.

The immediate request is satisfied by making the existing baseline contrast
inspectable, rather than repeating its generation or coding. Any later study
needs a distinct intervention and an advance outcome that can detect improvement
on both work-absent and work-present messages. Surface measures such as length,
newlines or backticks can be calculated automatically, but cannot stand in for
human help/work judgments. No additional batch or review queue starts here.

## Verification

655 Python tests pass (three optional skips), including authored evidence-join,
target-exclusion, no-reply/error, changed-file and read-only endpoint checks.
All three existing Node checks and seven Marimo checks pass. Desktop browser
inspection verified direct entry, filtering, all eight draws per case, separate
reference text, source details, and one hideable conversation panel. Independent
review caught and fixed workspace identity drift that would have hidden existing
policy drafts; legacy draft identities remain stable. All 29 files in the private
benchmark archive retained their contents and modification times during verification.
