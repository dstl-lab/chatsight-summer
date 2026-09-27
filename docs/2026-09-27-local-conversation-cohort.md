# Fixed local conversation evaluation

Evaluate the unchanged starting Qwen3-4B model and saved student adapter across
all thirteen remaining eligible prefixes in the closed local conversation pilot's
selection. That selection already required at least two visible student messages
and at most 2,048 student-prompt tokens. Exclude the sole previously generated
case; retain the existing hash order. No replacement, new selection threshold,
reference-dependent selection, further training or instructor labeling.

Reuse the pinned prior runner's `run_arm` and local worker's `generate`, imported
without editing their files. A thin worker entry point redirects only the allowed
receipt root. Each case has separate starting/trained session directories. The
unchanged base model tutors both arms with the exact prior policy; fresh replies
follow each arm's own history. Alternate which model runs first by case ordinal
(starting first for odd ordinals). The default simulator remains unchanged.

Each arm permits three student decisions and two tutor replies: at most 130 local
generations total. Fixed seeds are `20261001 + 100 * case + 10 * position`, plus
one for tutors, with cases numbered 1–13, student positions 1–3 and tutor positions
1–2. Reset seeds immediately before sampling after loading weights. Retain prior
temperature .7, top-p .8, top-k 20, thinking disabled, exact training serialization,
256 student / 384 tutor output tokens, and a 4,096-token prompt-plus-budget ceiling.
Retain the advisory 16 GiB limit and stop on reported excess; no context truncation.

Keep the 120-second per-call timeout and a 30-minute overall generation deadline;
each call receives at most the remaining overall time. A blank, non-EOS, capped,
failed or interrupted call stops its arm. Retain partial receipts. Continue other
untouched arms while time remains, without retrying any started operation. Stop
after the fixed plan or deadline; unstarted and unavailable planned slots remain
explicit. EOS does not establish student silence. All processing is local.

Freeze the plan, source/model/adapter hashes, driver, worker and authored checks
before generation. No future historical turns or reference targets enter model
input. Read references only after generation closes, for the first-reply length
comparison. Preserve exact token/text receipts, model identity, attempted calls,
delivery status, branch-local histories and original source bytes.

Report these declared diagnostics without selecting a winner:

- Coverage: each arm's completed conversations, delivered student turns, tutor
  calls and every stopping reason, with all 13 planned cases retained.
- Exact repetition using `student_repetition.summarize`, including the first
  recorded-to-generated transition: up to 39 pairs per arm. Show pooled and
  conversation-mean rates, outer-whitespace sensitivity and existing length strata.
  Also show the paired fully completed subset, and conservative all-planned-slot
  repetition bounds assigning unavailable slots either no repeat or repeat.
- Unicode-character lengths using the existing distribution helper, both pooled
  and conversation-weighted across delivered turns. For first replies only,
  report absolute character-length error versus the actual recorded next message,
  with paired means/medians on cases where both first replies were delivered.
  Later simulated turns have no matched real future target and receive no error score.
- Reference the already completed prediction-loss pilot separately; do not combine
  its different case set or metric into a new composite score.

These are developmental conversation scenarios, not randomly sampled identifiable
students. The selection excludes short-history and longer-context cases; the
development cases are already exposed. Missingness can change delivered-only
rates, later tutor text can differ by branch, and repeated text can be legitimate
student behavior. Character-length similarity is not semantic fidelity. No labels,
silent-action rates, notebook execution, learning or real tutor-policy effect are
inferred. Close this evaluation before considering another model change.
