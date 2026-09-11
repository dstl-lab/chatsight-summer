# Episode v6: distinguish checking work from supplying a solution

Minchan approved the proposed distinction on September 10 after reviewing the
checking-versus-repair comparison. Add `checks-work` to tutor responses; retain
`worked-solution` as the stored name for supplying a complete new answer or repair.
An explanation supporting a check remains checking. A substantial independent
instructional move can make the complete response mixed. The label describes the
tutor's assessment, not whether its assessment is correct.

Restore the earlier human request anchors in this new draft: confirmation can
check understanding as well as work and can be supported by prior dialogue;
explanation asks why/how, including why an attempt failed; debugging requests
locating or fixing a problem. Generic help, bare code, or a history of tutor
explanations alone does not establish a particular request. No case identifiers or
student quotations belong in the prompt, and old reviews are not migrated.

Keep v5's two independent input stages and existing evidence validation. Filter
blank model-visible lines after numbering so evidence IDs still address the raw
source. Preserve blank turns and reject selected blank or invented IDs. Pin the
changed input contract, prompts, and rubric as v6; v3/v4/v5 must retain their hashes.

Verify sparse evidence numbering, exact copying, rejection/retry, stage isolation,
and old-version compatibility with invented dialogue. Then generate only the same
12 development episodes under the existing Gemini disclosure authorization. Save
the comparison and returned selections under ignored data/, preserve earlier
artifacts, and keep the 35 reserved episodes unannotated. Leave the existing v3 UI
in place. This remains codebook development, not a reliability or simulation gate.

## V6 result and v7 correction

All 251 tests pass. V6 produced nine valid development annotations. Three episodes
repeatedly invented a student follow-up despite its absence and were rejected;
returned drafts remain preserved. Checking existing work is now distinguished from
supplying a repair. Remaining application errors include treating assessment and
guidance toward the same repair as mixed, and treating a brief status as a question.

V7 derives absence directly from recorded turns: if no student follow-up turn exists,
the after-help model returns only tutor_response. The application supplies
no-followup-observed and not-observable with empty evidence. A blank student turn
still counts as observed. The new strict stage schema, conditional prompt/rubric,
and deterministic rule are hash-pinned. All other stage and validation guarantees
remain intact. This removes an unnecessary model judgment, not a failed validation
check. Also clarify that assessment supporting guidance on the same repair stays
hint, and a bare status without a question stays other. These use the existing
review anchors; no repeat review of those cases is required.

Preserve v6, then rerun only the same authorized development sample as v7. Do not
claim that differences between these development runs measure accuracy.

## V7 result

All 12 drafts completed on the first pass; 24 returned stage selections and actual
prompt hashes were verified. Seven absent follow-ups are derived from recorded
turns; five observed follow-ups use the full after-help schema. All 257 Python
tests pass. Fifteen earlier artifacts, including all seven human reviews and v6's
failed drafts, retain their byte hashes. All 35 reserved episodes remain unchanged.

The central contrast holds in the generated output: episode 12 checks work,
episode 3 supplies a complete repair, and episode 8 checks then starts another
step. Mixed remains overused for single-repair guidance in episodes 5 and 7;
task links remain overconfident when the original target is missing or the new
target is only inferred (episodes 4 and 6). The saved machine outputs are unchanged;
the separate assistant audit documents these failures. No repeat human review or
additional prompt iteration was opened to make the development cases conform.

Comparison and provenance are in ignored `data/episode-pilot/pilot-v7/preview.md`
and `verification.json`. Bundle: `37743cb34354517a`; protocol:
`e1f4a23939ff68eb4dd3ba2fde303486bb93f94c6e6a70d8fc107171d63b477b`.
Category approval establishes intended meaning; these reused development cases
do not measure classifier reliability or qualify labels for simulation.
