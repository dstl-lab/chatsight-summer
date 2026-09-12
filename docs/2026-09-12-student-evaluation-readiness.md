# Establish what the available data can evaluate

The partial-work continuation is accepted as plausible. Close that example and
retain the original generator. Further similar reviews cannot establish how often
the simulator reproduces real behavior. Before another model batch, inventory
the available real observations and freeze a small candidate slice for context
recovery. This is a development evaluation preparation, not a pristine holdout or
a new labeling taxonomy.

Reuse the saved canonical snapshot inventory, the existing episode extractor,
continuation exposure ledgers and recovered initial-context manifest. Verify
their source hashes. Count each snapshot separately and distinguish overlapping
conversations from independent observations. Read no live database and make no
model requests during this inventory. All identifiers and row-level metadata
stay in a new ignored `data/episode-pilot/evaluation-readiness-v1/` directory.

For the established sequence snapshot, enumerate eligible request/response
windows and their prefix sizes, timestamps, presence of a recorded next student
contribution, and availability of recovered initial work. Exclude known prior
continuation cases using the two existing selection ledgers. This exclusion is
a minimum known exposure list; older label audits and corpus searches mean all
local snapshots have prior exposure. Do not call the remaining conversations
unseen or held out.

Freeze four distinct candidate conversations, using the existing prefix strata
(two code/error cues, one concise request and one earlier-context request), a
6,000-character visible-prefix limit and a deterministic hash ordering. Eligibility
requires an observed next student contribution; this conditions the sample on a
logged reply and cannot measure reply probability. Selection may use the existence
of that contribution, never its wording, apparent success or model outputs.
Preserve a shortfall instead of relaxing criteria after looking at candidates.

A code-looking chat excerpt is not a notebook capture, a check record does not
reveal the code that ran, and an initial capture is not current work at a later
cutoff. Inventory these channels separately. The new candidate list is for
context recovery, not authorization to feed historical work into a later state
or to equate one generated silent edit with the next logged chat message.

The immediate measurement question is which subsequent help requests and work
submissions are observable with enough preceding context to support a comparison.
Do not assign semantic labels or claim a behavioral score from this inventory.
Missing silent edits, exposure duration and observation boundaries continue to
prevent calibration of action frequencies or pacing. No new runtime checker,
memory framework, review interface or prompt change is required.

## Completed inventory

The eight saved snapshots contain 455 conversation records covering 252 distinct
conversation IDs. Six conversations have differing metadata across exports; none
has differing dialogue or conflicting role/text at the same turn index. Snapshot
memberships remain separate, and distinct conversations do not imply distinct
students. All source conversation and manifest hashes and row counts verify.

The primary sequence snapshot contains 147 request/response opportunities: 110
have a subsequent student contribution and 37 do not. These are observations in
the export, not reply/no-reply probabilities. The two exposure ledgers identify
35 previously used conversation keys across the available sources. Applying
those exclusions and the prefix limit leaves 55 eligible windows across 24
conversations. Their retrieval strata contain six code/error windows, 38 concise
requests and 13 earlier-context windows; the latter two overlap.

All four requested candidate slots are filled, with distinct conversations and
complete visible/next-contribution timestamps. None has an already recovered
initial notebook capture. Current work and execution remain unknown. This is a
context-recovery list, not four ready-to-run notebook simulations.

The final ranking uses the existing continuation helper's raw-string SHA256
convention and the recorded seed. An initial JSON-string ranking preparation is
preserved privately as superseded; no target text was reviewed to choose between
them and no model call occurred. The final inventory reproduces exactly. Its
invented check covers target-text isolation, exclusions, distinct conversations
and quota shortfalls; replacing future text in every primary opportunity also
leaves its metadata unchanged. An independent comparison against the earlier
saved candidate metadata confirms the same 55 eligible windows and four selected
IDs. All 32 direct source/script/output hashes verify.

No production code, earlier experiment, model prompt or raw source changed. No
database, model or network calls were made for this inventory. The latest full
production-code suite remains the previously recorded 321-test run; only the
new offline check was run here.

Next, recover and align notebook context for these fixed candidates using the
existing read-only ingestion path. Preserve missing or ambiguous cases; do not
replace them after seeing the reference behavior. A starting capture may support
a new initial encounter, but a later comparison still needs current work or an
explicitly narrower communication-only question. Keep reference next messages
and intervening checks out of generator context. No additional plausibility
review is needed for this metadata inventory.
