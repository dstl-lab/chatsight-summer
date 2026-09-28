# Inspect repeated replies against visible history

The fixed-input comparison exposed a gap in the latest-message repetition
diagnostic: a generated reply can match an older student message. Add a small
whole-message matcher alongside the existing repetition summary. Preserve the
old summary and completed comparisons exactly; this work uses a separate
worktree because their source files are pinned.

For one validated response window, return every matching prefix turn's zero-based
index, student/tutor role, whether it is the latest student turn, and whether the
match is literal or requires stripping outer whitespace. Return no matches for a
blank reply. Do not normalize capitalization, internal whitespace or punctuation.
Include all matching locations, but count a response only once in each aggregate;
student and tutor matches can overlap. Do not return student text from the helper.

Apply the matcher offline to all saved full-adapter requests and cached outputs.
Keep recorded-history first replies and later fixed synthetic histories separate.
Use the original recorded first-reply references only for the former. Describe
the existing training library separately to show that repetition also occurs in
recorded messages. Keep private counts, source links and generated text in ignored
data. Verify the original closure/source hashes and leave every input unchanged.

This is lexical source inspection, not evidence of why the model copied, a
plausibility classifier, or a measured improvement to the simulator. Whole-turn
equality misses partial copies such as an error traceback with a changed header.
Repeated questions and copied code can be legitimate. Do not filter training
targets, penalize generation, replace the browser model, or request labels on
this basis. Stop after the authored regression check and saved-data report;
no model call, tuning run or new review queue is part of this change.
