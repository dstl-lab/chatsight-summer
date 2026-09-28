# Student-role reminder: closed without adoption

One final instruction after the unchanged transcript corrected the observed
copied-tutor-question example, but failed the [predeclared criteria](2026-09-28-student-role-reminder.md).
Keep the live simulator unchanged. No second reminder, training run or manual
labeling pass is queued.

## What ran

Forty local base-model student generations used the same saved prefixes, seeds,
sampling settings and output caps as their cached baselines. All completed at
end-of-message within the fixed limits. There were no new tutor calls, rollouts,
cloud requests, retries or adapter changes. A separate local scoring pass used
the same 28 exposed development targets and all 526 original target tokens.

| Population | Replies | Tutor containment, baseline → candidate | Long tutor containment (>40 characters) | Whole earlier-student repeats |
| --- | ---: | ---: | ---: | ---: |
| Recorded-prefix first replies | 13 | 0 → 1 | 0 → 0 | 1 → 1 |
| Fixed later synthetic histories | 26 | 7 → 4 | 6 → 3 | 10 → 4 |
| Separate recorded smoke example | 1 | 1 → 0 | 1 → 0 | 0 → 0 |

Containment means the entire stripped reply occurs within an earlier tutor turn
after casefolding; it does not itself establish role confusion. Long-match counts
decreased in three cohort conversations, with no increases. The new first-reply
match was a short question identifier, illustrating the measure's ambiguity.
Median stripped lengths changed from 156 to 116 characters for first replies,
129 to 103 for later replies, and 73 to 229 for the separate smoke example.

Conversation-weighted mean negative log loss **worsened from 7.52277 to 8.11010**
(+0.58733; lower is better). Seven conversations improved and 21 worsened.
The candidate therefore failed both the no-new-first-match criterion and the
recorded-response likelihood guard. Even treating the short identifier as
ambiguous would not change the likelihood failure. The successful smoke example
does not override the fixed decision rule.

## What the saved examples clarify

Agent inspection covered all 13 first replies, the smoke example and every later
reply with a tutor-containment match in either condition. This is contextual
diagnosis, not a new human-coded evaluation. The smoke response now speaks from
the student's position, but narrates planned work at length. Other responses
still claim execution or test success without observed notebook activity.

The three reduced long overlaps occurred where earlier synthetic student and
tutor wording already overlapped. Their replacements include generic thanks,
extended explanations and an explicit description of what the student would
say. A lower overlap count can therefore hide continuing communication problems.
Unchanged overlaps also include code supplied by the tutor, which may be valid
student reuse. These findings do not justify a blanket copying filter.

## Verification and limits

Preparation independently verified 1,542 distinct frozen source hashes, all 40
suffix-only request transformations and exact tokenized prompts. Saved output
checks verified tokens, decoding, chunks, end markers, identities and budgets.
The loss check reconstructed both prompt formats, preserved every target token,
and reproduced the saved aggregate and per-conversation differences. Four focused
existing tests passed, along with authored request/failure checks. An independent
stdlib audit reproduced the final counts, loss differences and failed decision;
all 332 private artifacts were then bound into the closed completion record.

These are exposed development cases with unknown learner identities. The later
histories are fixed baseline-generated conversations; candidate replies were
never fed forward. The smoke conversation is also among the previously scored
development targets. A single seeded draw and conditional text likelihood do
not establish realistic personalities, notebook actions or real policy effects.

The private, reproducible artifacts are in ignored
`data/student-role-reminder-v1/`: frozen preparations, requests, results, token
audit, per-conversation losses, report and contextual interpretation. The protocol
and this outcome are committed locally only. This attempt is closed: the useful
result is that fixing a visible role error did not improve this candidate's
recorded-response prediction, so it should not become the default.
