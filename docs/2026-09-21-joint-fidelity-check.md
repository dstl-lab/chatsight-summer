# Joint student-continuation check

**TL;DR:** In six previously exposed conversation cases, Minchan preferred the
recorded continuation in four and considered both continuations possible in two.
The generator was never preferred outright. This is qualitative development
feedback, not a fidelity score or evidence that a changed simulator improves.
The pass is closed: no additional cases, model calls or automatic prompt changes.

## What we evaluated

Following Minchan's request to evaluate together, we reused six recorded next
messages and the existing generator's saved first draw for each. Selection took
all three code/work cases from the older independent primary-category review
and the first three help cases in their existing case order. The selected cases
were 1–6, ordered by case number; neither generated quality nor the new judgments
determined selection. These older categories guided sampling only. They do not
establish balanced binary work flags.

The first presentation requested two help/work flags. Minchan instead supplied a
relative likelihood judgment. After that response and before presenting case 2,
we explicitly changed the remaining questions to comparative likelihood, allowing
A, B, both, neither or uncertain. The private amendment preserves that timing.
We retained the same six cases, saved draw, messages and concealed A/B ordering.
No preferences were converted into help/work judgments; all 24 flags remain blank.

Case 1 showed the full supplied dialogue. Cases 2–6 used clearly marked assistant
summaries, visible student messages and links to the exact full dialogue. Origins
and previous labels were withheld from the review presentations until completion.
Minchan had previously encountered these cases, and the assistant facilitated the
review. This is not independent validation, and concealing origins does not
establish successful blinding.

## Result and source reveal

| Case | Instructor judgment | Recorded continuation | Generated continuation |
| --- | --- | --- | --- |
| 1 | B more likely | B | A |
| 2 | Both possible; no ranking stated | B | A |
| 3 | A more probable | A | B |
| 4 | A more probable | A | B |
| 5 | A preferred | A | B |
| 6 | Both possible; no ranking stated | A | B |

There are four preferences for the recorded message, zero for the generated
message, and two judgments that both are possible. The latter do not mean equal
probability, and a relative preference does not make the other message impossible.
No cases were excluded or replaced. Six instructor responses covered 12 existing
messages, with zero new model calls.

## What this suggests

For case 1, Minchan questioned the generated message's manner of replying to the
tutor. For cases 4 and 5, the stated reason was that the student had not previously
supplied an answer or explanation. Case 3 supplied a preference without a reason;
we do not invent one. Cases 2 and 6 show that the generated alternative can remain
possible alongside the recorded continuation.

Our working hypothesis is that the generator sometimes gives too much weight to
answering the tutor's final question relative to the student's visible pattern of
using the tutor. This is an interpretation of the messages and instructor feedback,
not a measured cause. It motivates examining conversational behavior rather than
assuming that shorter messages or fewer work submissions necessarily improve fit.
The record includes a preferred code-bearing continuation as well as preferred
brief checks; a universal ban on code, answers or acknowledgments is unsupported.

These observations are about the available conversation prefixes. They do not
establish permanent student traits, predict silent notebook activity, or prove
whether any reported work succeeded. The record also contains too little history
in some cases to infer a stable communication pattern.

## Limits and stopping decision

The six cases were selected from exposed development examples, with one cached
draw per case, one involved instructor, and a changed question after case 1.
Assistant summaries and prior recognition can influence judgments. This is not a
random student sample, a generic-versus-grounded comparison, an accuracy estimate,
a probability calibration exercise or a causal evaluation of tutor policies.

The original goal of obtaining comparable help/work coding was **not achieved**.
The [measurement gap](2026-09-20-student-fidelity-target.md) remains: this pass adds
no binary work-present reference judgments and does not clear the adoption gate.
Older reviews and closed comparisons retain their original results and scope.

Retain the current generator. Close this pass with this report, keep the bulk
audit paused, and do not request another judgment, generate another batch, or tune
against these six cases automatically. A future change must separately specify
how it would be evaluated; this qualitative finding alone cannot validate it.

## Private evidence and reproduction

Exact texts, source identities, original replies, the protocol amendment and the
source mapping remain in ignored `data/episode-pilot/joint-fidelity-check-v1/`.
`protocol.json` preserves the original preparation status; `report.json` records
completion. No private dialogue or identity is included in this commit.

Run this read-only check from the repository root with the local evidence present:

```python
import hashlib
import json
from collections import Counter
from pathlib import Path

p = Path('data/episode-pilot/joint-fidelity-check-v1')
read = lambda path: json.loads(path.read_text())
report = read(p / 'report.json')
for name, digest in report['source_hashes'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
for name, digest in report['review_artifacts'].items():
    assert hashlib.sha256((p / name).read_bytes()).hexdigest() == digest
review, mapping = read(p / 'review.json'), read(p / 'origin-key.json')
assert [r['case'] for r in review['raw_replies']] == list(range(1, 7))
counts = Counter()
for case, key in zip(review['cases'], mapping['cases'], strict=True):
    assert case['case'] == key['case']
    preference = case['relative_preference']
    choice = preference['preferred']
    if choice is None:
        assert preference['possible'] == ['A', 'B']
    counts[key['origins'][choice] if choice else 'both_possible'] += 1
    for message in case['messages']:
        assert message['help_request'] is message['work_present'] is None
assert counts == {'recorded': 4, 'both_possible': 2}
assert report['status'] == 'complete-closed' and not report['next_batch_queued']
print(dict(counts))
```
