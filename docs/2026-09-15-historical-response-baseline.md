# A response baseline using existing conversations

Minchan redirected work to the existing dataset, then asked to continue. Build
one offline comparison baseline before another model experiment: retrieve the
most similar recorded dialogue prefix and return its next student message
verbatim. Reuse the existing episode extraction and installed scikit-learn.
This is a lexical reference baseline, not a new persona model or a replacement
for the current generator. Existing model prompts and completed batches stay intact.

The input separates reference-library examples (visible turns plus the first
recorded next message) from query prefixes (no target field). Fit word/unigram
and bigram TF-IDF only on library prefixes; choose highest cosine similarity,
breaking ties by example ID. No overlap yields an explicit no-match. A retrieved
blank message remains a recorded blank, never a chosen stop. Keep the selected
source and similarity visible; similarity is not a behavioral probability.

Validate IDs and conversation separation before retrieval, including known
student identities when supplied. Return exactly the selected recorded text;
do not rewrite variable names, infer actions or assign help/work labels. This
can yield contextually wrong responses and cannot estimate silent actions or
whether a student replies. A longer tutor reply may dominate lexical matching.

For the local development run, reuse the eight canonical exports already audited,
verify their hashes, deduplicate dialogue and reject conflicting versions. Split
whole conversations deterministically before inspecting target content. Use SHA-256
of `historical-response-baseline-v1:<conversation_key>`, with integer remainder
zero modulo five assigned to queries and all other conversations to the library.
Keep all 55 minimum known continuation-exposed conversations in the library;
the exposure count includes the eight closed help/work cases. Select at most one
query window per conversation by the smallest hash of
`historical-response-baseline-v1:<episode_id>`. Include every library window with
a recorded followup. Use source order and the existing six-turn context limit;
there is no claim of a fixed time horizon. Stop on conflicting or identical full
dialogue across different conversation IDs instead of changing the split. This
is previously audited same-course development evidence, not a pristine or
student-separated holdout. Save query references separately from retrieval input.

Finish after one reproducible offline run with all retrieved responses and source
joins, explicit no-match/blank coverage, and descriptive character-count error
against the recorded query messages. Include a constant training-median length
baseline for that narrow diagnostic. Length does not measure help/work content,
contextual appropriateness, reduced over-explaining or student fidelity. Do not
change retrieval settings in response to its result or automatically generate a
new comparison batch. A later candidate/model comparison needs a frozen protocol.

The runnable control must catch target/response leakage into retrieval, overlapping
conversations/known learners, ambiguous ties, blank versus absent results, and
overwritten artifacts. No model, DB, notebook execution or human review is needed
to build and run this baseline.
