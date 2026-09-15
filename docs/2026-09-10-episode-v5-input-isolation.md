# Episode v5: isolate pre-help intent from future dialogue

Minchan authorized continuing after the v4 findings. The immediate change addresses the observed hindsight failure: episode 5's first draft cited a future tutor reply as request evidence, and its retry removed that citation while retaining the future reply in its rationale. V4 validates citations but still supplies future text to the model. Its instruction cannot enforce an information boundary.

## Smallest testable change

Keep all five v4 fields and their category definitions unchanged. Version 5 makes two stateless calls through the existing Gemini adapter:

| Stage | Model input | Output |
| --- | --- | --- |
| Before help | Earlier context and current student request, with source-line numbers | student_action, request |
| After help | Existing full episode context and turns | tutor_response, followup, task_relation |

The before-help input excludes the current tutor reply, follow-up, later metadata, legacy labels, human judgments, and any earlier model judgments. The after-help call receives no before-help predictions and cannot return or overwrite those fields. The stored annotation remains the same five-field shape.

Version the new prompts, stage schemas, and input contract. Preserve v3/v4 hashes and bundles. Reuse v4's category, exact-quote, phase, paired-evidence, and absence checks. Save an episode only after both stages succeed and the merged output validates. A failed episode retries both calls; per-stage persistence is unnecessary for this 12-episode pilot. Do not weaken validation to get a complete run.

The new regression must compare actual before-help prompts while varying all future text and future metadata. Those prompts must remain identical. It must also exercise merged outputs, cross-stage overwrite rejection, failed-stage recovery, untouched reserved episodes, and saved v3/v4 loading. Tests use invented dialogue only.

## Development check

Prepare the same 12 development and 35 reserved episodes with unchanged source and sampling pins. Send only the same 12 development episodes covered by Minchan's explicit Gemini disclosure approval. Save new v5 outputs and a v4/v5 preview under ignored `data/`; leave v3, v4, and the seven human reviews intact. The active v3 review page is unchanged.

Inspect whether episode 5 still invents help intent without earlier context, whether episode 7 continues to infer intent from bare code, and whether other request interpretations become clearer or remain ambiguous. Keep task-link and tutor-response problems visible; this change does not resolve them by definition. Do not tailor the prompt to particular student quotations or expected episode labels.

## Interpretation limits

This prevents access to observed future dialogue; it cannot prevent a model from inventing context or making an unsupported pragmatic inference from the student request itself. The staged output schema and prompt framing also change, so a difference from one previous model run is not a controlled estimate of the benefit of removing future context. These are development cases used to diagnose failure, not a blind evaluation. No classifier reliability, learning, or simulation admission claim follows.

## Implementation and development result

The input boundary is implemented. All 246 Python tests pass, including actual prompt invariance under changed future dialogue/metadata, strict stage separation, failure recovery, and v3/v4 compatibility. Live before-help prompt hashes also match reconstructed context/request-only inputs. An initial Gemini wire-schema rejection was resolved by omitting its unsupported extra-properties keyword while retaining strict local rejection of unexpected fields. Wire schemas and local validation policies are both hash-pinned; the empty rejected run is archived separately.

All 12 v5 development drafts were generated under the same disclosure approval. Three initially selected blank evidence lines and were retried with unchanged prompts; all saved annotations pass structural validation. The v3 bundle, seven human reviews, and v4 artifacts retain their prior byte hashes. All 35 reserved episodes remain identical and unannotated.

Episode 5 now leaves intent unclear instead of drawing on the later tutor diagnosis. Episode 6's after-help judgment leaves task relationship uncertain in this run. Episode 7 retains the observable code-submission/hint/revision sequence but still infers a correctness-check request from prior context. Episode 10 infers explanation intent from earlier tutoring patterns. Those last two judgments remain uncertain under the strict codebook; removing future input does not resolve pragmatic inference.

The comparison and separate assistant audit are in ignored `data/episode-pilot/pilot-v5/preview.md`. Machine outputs remain unchanged. V5 bundle ID is `b7d9a17e02eed875`, protocol hash `bee5e3fdb5f3b7fa602bf2b637f1ea009d6c3638d59f27342373a4f4308fc09c`, model `gemini-2.5-flash`, source snapshot `20260811-1d1e79d39fda-7bc759`. This completes the input-isolation change; it does not admit the labels to simulation or validate their semantics.

## September 10 continuation: category review point

The remaining tutor-response decision is whether evaluating existing work merits a
separate **checks-work** category from supplying a complete new answer or repair.
Recommend the distinction: explanation supporting an assessment remains checking;
a separate instructional move can make the whole response mixed. Episode 12 provides
the checking example, episode 3 the already-reviewed repair contrast, and episode 8
the checking-plus-next-question boundary. A short review packet, including exact
excerpts, is at ignored `data/episode-pilot/review-checking-work.md`. This proposal has
not changed the codebook or any annotation.

The seven saved reviews remain development anchors. In particular, the human request
judgments on episodes 1, 4, and 7 should not be treated as errors because later
assistant-written rules narrow confirmation or recategorize requests for explanation
as debugging. A next draft should retain checks of understanding under confirmation,
distinguish asking why from asking to locate or fix a problem, and represent episode
7's contextual confirmation interpretation. These anchors do not establish reliability.

Keep task linkage scoped to the question target, consistent with the original
one-question sequence proposal. A changed question reference does not establish
disengagement or that the activity is unrelated; episode 11 illustrates that limit.

Defer another model run until the category decision. In that next version, omit blank
entries from model-visible evidence arrays after numbering, retaining original line
IDs, raw text, and rejection of invalid evidence. Do not alter v3/v4/v5 rendering or
hashes. All 12 v5 drafts already validate, so this does not require a separate run now.
The continuation preserved ten existing artifacts byte-for-byte, including all seven
reviews; hashes are in ignored `data/episode-pilot/review-checking-work-preservation.json`.
