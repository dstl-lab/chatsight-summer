# Saved tutor-wording diagnostic complete

The [containment diagnostic](2026-09-28-tutor-wording-diagnostic.md) covers the
existing recorded library, saved base/adapter outputs and the separate integration
example. It adds one small inspection helper and leaves generation, model defaults
and all closed studies unchanged. No new model call or manual label was needed.

Tutor wording does recur in saved generated replies. Contextual inspection found
both a repeated tutor question and a copied tutor explanation. Other matches were
code, short task references, or text that had already appeared in student turns
and was then repeated by a synthetic tutor. The matcher exposes locations; it
cannot identify who originated the wording or classify a reply as implausible.

The shared recorded-prefix first replies contain no matches under this rule.
Later synthetic-history replies do, with fewer matches for the full adapter on
the fixed 100-step histories. Those results do not establish better realism or a
new rollout outcome. Base-model later histories differ and are kept separate. Response-length bands
also contain different cases by model, so their rates are not paired causal contrasts.
Short recorded replies also match tutor text, so filtering all matches would
remove real student behavior. Keep the full adapter experimental.

The concrete decision is to retain source-linked overlap inspection, with no
copying penalty, training-target deletion, prompt change or default-model switch.
The private report preserves response-length denominators, role overlap, casefold
sensitivity, source hashes and every location. `INTERPRETATION.md` distinguishes
contextual observations from scored human judgments. This diagnostic is closed;
it does not queue another labeling pass or generation batch.

All 773 Python tests pass, with three optional skips and the existing
Starlette/httpx warning. The authored matcher check covers blanks, casing, Unicode
expansion, internal whitespace, punctuation, multiple roles and invalid boundaries.
The private report reproduces with unchanged source pins, and its length/overlap
arithmetic verifies. An independent reconstruction reproduces every match and
aggregate directly from saved text, without importing the new matcher. Non-weight
source pins verify; existing weight hashes remain explicitly inherited. A private
completion manifest closes the diagnostic. Original artifacts remain unchanged.
