# Cross-notebook comparison: prepared, awaiting exact-send approval

**TL;DR:** Ten cases and all 150 requests are prepared and independently verified.
Each matched card uses 12–20 earlier student queries across 2–6 notebook identities.
The ten recorded next replies remain unfetched. Automatic approval review rejected
the dispatch before process creation; **zero model requests were sent**.

## What is ready

The [frozen protocol](2026-10-01-cross-notebook-cards.md) selects ten accounts from
the 72-account richer-history pool using a fixed hash order. No case was replaced.
Read-only ingestion returned 1,774 event metadata rows across 159 conversations.
All ten selected checkpoints passed chronology and source-binding checks.

Input retrieval was restricted to 382 frozen event IDs, disjoint from all ten
reference event IDs. These yield 124 current-conversation turns and matched
history samples of 20, 20, 20, 20, 19, 20, 20, 20, 20 and 12 student queries.
Each of the ten donor samples has exactly the corresponding matched sample size.
The ten donor assignments use six accounts; two are each reused three times.
Donor histories precede recipient cutoffs, exclude both target notebook identities,
and exclude every selected target conversation.

All ten matched statistics cards differ, and each differs from its donor card.
The descriptive total-variation distances between matched/donor literal-form
distributions range from 0.05 to 0.60. This establishes finite-sample contrast,
not different personalities or evidence that history improves prediction.

Thirty prompts share the exact current conversation within each case. Only the
two history arms add aggregate statistics; no verbatim historical examples,
notebook names or account-identification fields are added. Current chat text is
private and is not asserted to be deidentified. Notebook source and future
messages are not fetched as generation inputs.

The schedule contains 150 unique slots, five per case/arm. SDK/schema options
construct successfully locally; provider acceptance has not been tested. Twelve
authored tests pass in the existing repository environment, including bounded
dispatch, donor validation, interrupted batches, missing scores and receipt replay.
Selection/preparation self-checks and independent metadata/prompt reconstruction
also pass. An unnecessary broader suite attempt encountered missing dependencies
in system Python; a repository-environment retry was stopped after 77 passing
tests. Full-suite completion is not claimed.

## Exact dispatch boundary

The attempted send used the standing project authorization. Automatic approval
review rejected it before process creation because previous approvals were judged
to cover other batches, not this exact payload, destination and scope. There is
no execution directory and no provider receipt. No workaround or retry was made.

The required approval is for **one batch of at most 150 requests to Google Gemini
2.5 Pro**, sending ten private current-conversation prefixes and aggregate
communication statistics derived from earlier histories. The recorded next
messages are excluded. No retries, replacement cases, prompt changes or further
batches are authorized by that approval. Actual provider usage remains zero.

Private preparation lives under `data/cross-notebook-cards-v1/`. Its `prepared/`
folder contains exact prompts, an input disclosure, the frozen plan, an independent
preflight audit and the saved dispatch rejection. The parent directory has a
separate, unexecuted reference request and an exposure ledger: these ten entire
accounts must be excluded from later fresh comparisons, in addition to the ten
previously exposed history-study accounts. This leaves 98 of the earlier 118
candidate accounts outside these two ten-account development cohorts.

Approved resumption must use the same hashes:

- Plan: `4928230f06bc9d23870f35f0d00a749bcddbd5b08fb72806c06151d636cefc11`
- Prompts: `6552b90ca415d6f5a5dbed775d2bae907b1134811dfdbabc9748135ed60c61c0`

After generation ends, fetch the ten frozen reference events separately, verify
their bindings, and produce the one planned report. No manual labeling pass is
needed. A result about communication form will not establish full behavioral
realism, stable personas, silence probabilities or tutor-policy effectiveness.
