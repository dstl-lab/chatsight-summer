# Inspect tutor wording in already saved student replies

The one-decision recorded-start check produced the tutor's final question with
changed capitalization. The existing whole-turn matcher cannot detect a reply
copied from part of a longer tutor message. Inspect that narrower gap using saved
outputs before changing the generator or requesting another experiment.

Add one metadata-only matcher beside the existing repetition helpers. Match the
entire nonblank reply, with outer whitespace stripped, as a contiguous substring
of each earlier visible turn after Unicode casefolding. Preserve internal
whitespace and punctuation. Return each matching turn's role/index, whether it is
a whole-turn match, and whether matching also succeeds without casefolding. Keep
all earlier roles so student/tutor overlap remains visible. Do not change the old
whole-turn helper or any frozen study source.

Apply this rule once to the existing recorded training library, saved base and
adapter replies, and the separate one-decision integration example. The library
is descriptive context, not matched ground truth for these generated cases; do
not decode query reference targets. Show denominators, blank exclusions, and split
nonblank replies by at most 40 versus over 40 stripped characters. This is the
existing diagnostic threshold, applied here to response length; it is not tuned
on these results. Count a response once per role, even if it matches several turns.
Keep first replies on recorded prefixes separate from later synthetic histories;
the base rollout has different later contexts from the paired 100-step/full-pass
fixed-input outputs. Do not pool those groups into an adapter ranking.

Containment is lexical evidence, not a copying-intent or role-confusion label.
Short replies, copied code, quoted questions and reused task wording can match
legitimately. Casefolding can merge distinct spellings. No matches does not prove
fidelity, and partial paraphrases or copies with added text will be missed.
Inspect matching generated replies in their saved contexts, retain the cases and
source locations privately, and distinguish inspection from a scored human review.
No penalty, training filter, automatic adapter adoption or prompt change follows
from this metric alone.

Verify exact boundaries with authored examples, recheck original closure/source
hashes, and save a reproducible offline report under ignored data. Stop after the
report and its audit, preserving all source studies. No generation, notebook
execution, new labels or cloud requests are part of this diagnosis.
