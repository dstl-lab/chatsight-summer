# Communication choice and student formatting comparison

Minchan approved the next comparison after the reporting audit. Reuse the existing
student-continuation runner and preserve the public generator, all prior prompts,
results and human feedback. This is one new generic prompt variant, not a new
student model or a held-out evaluation.

Use all eight exposed interaction-comparison contexts with two new draws each,
plus the three previously reviewed continuity branches with one new draw each:
19 new logical requests to the established Gemini 2.5 Pro endpoint. Hold the
dialogue projection, schema, generation settings and scripted bridges fixed.
Retain the corresponding 19 earlier draws as a historical baseline; do not rerun
or cherry-pick it. Branches retain their original generated student seed, rather
than introducing a second changing input. The three branches derive from three
of the eight contexts and are not independent conversations.
Draw numbers identify retained replicates, not matched random seeds. The baseline
was generated earlier, so provider changes over time are also uncontrolled.

Append two generic instructions to the frozen prompt:

> Separate a possible outcome of working on the task from a reason to send a
> message. Do not add a completion announcement, successful test output, or claim
> that an error was fixed just because the tutor's suggestion could lead there.
> An outcome report can be plausible when the visible interaction supports sharing
> it, including a pasted problem report or an outcome attached to another request.
> Do not force either a status update or no-reply to close the exchange. Whether
> work succeeds and whether the student reports it are different possibilities.

> Distinguish code syntax from Markdown used to present code. Follow the visible
> student's use of plain text, inline backticks, code fences, and lists; do not add
> Markdown wrappers merely to polish a message or imitate the tutor. Preserve
> necessary code syntax and identifiers. Sparse style evidence is not a reason to
> invent formatting habits or ban a form that the content requires.

These are combined development constraints. Any improvement cannot be attributed
separately to one instruction. Fewer backticks or more no-reply outputs are not
success metrics. No recorded future turn, human case verdict, audit count or prior
generated target enters a new prompt. Retained generated seeds and scripted
bridges are visible only in their existing branch inputs.
Those frozen inputs omit origin metadata; the review identifies the generated
seed and scripted tutor explicitly. Branch style evidence therefore includes its
retained generated student contribution as well as the recorded student history.

Before sending, freeze the exact inputs, new instruction, baseline mappings,
runner, source pins and authorization basis under ignored
`data/episode-pilot/communication-format-v1/`. Save a readable disclosure of the
19 planned requests. The standing model-run approval and this turn's instruction
authorize this continuation; record them as standing authorization and direction
approval, without misrepresenting either as review of the eventual outputs.
Verify authorization before loading credentials. Use the existing durable cache;
preserve failures and do not reroll candidates for semantic quality.

Prepare an exact-text comparison with earlier context expandable. Show the three
continuity cases first because they motivated this change, followed by all eight
original-context checks. Compare baseline and variant without revealing prompt
identity in the candidate headings; preserve the mapping privately. Earlier
exposure means this is not a blind study. Identical outputs may share one display
but must retain every draw and condition in their provenance. Mark generated
seeds, scripted tutor bridges, no-reply and failed draws explicitly.

Human review asks whether a message fits conditional on sending it, whether its
formatting fits, and whether a reply would occur; each can remain unknown. A short
combined note is sufficient. Do not convert stylistic reservations or preferences
into categorical rejection, or copy previous feedback onto new candidates. Keep
all new judgments blank until Minchan supplies them. Mechanical checks establish
input/output integrity and presentation only; they are not a plausibility score.
Stop at the prepared human comparison before further prompt tuning.

Only the generic method, verification and execution status enter Git. Raw dialogue,
generated outputs and review records remain ignored. No live notebook, grader,
database, inferred persona, admitted label or tutor-policy change is introduced.

## Frozen preparation

Experiment `2745d2eba517a31dd705dcc10320d8cdc680aa7ddc85bb8bad4a5cb650bcee87`
pins 339 files, including all 327 continuity-parent pins. All 11 revised inputs
retain the exact baseline dialogue suffix. The new manifest separates API
settings from the explicit schedule: 16 original-context draws and three branch
draws. The older continuity manifest's inherited two-draw description remains
untouched; its actual one-draw branch inputs and results define this baseline.

The runner reuses the existing model adapter, strict response validation and
durable call cache. Offline checks pass for prefix isolation and missing
authorization. Independent review found no blocking runner issue. The new
Markdown renderer reuses the existing text restoration and safe-fence helpers;
invented checks cover duplicate provenance, failed/no-reply outputs, request and
output mismatches, incomplete batches, and preserved human answers. All 11 real
prefixes also passed an in-memory presentation check using invented failed
variant calls, without writing review results or calling a model.

The exact disclosure and truthful authorization basis are saved privately.
Automatic approval review allowed this batch under the recorded authorization,
and generation has started. No human judgments of these outputs exist yet.
