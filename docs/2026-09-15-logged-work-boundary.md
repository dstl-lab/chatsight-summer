# What the tutor sees versus what the logger saves

## Scope before source inspection

Minchan asked to continue the main flow while teammates independently explore new
exercises and a Marimo replay viewer. The lab repository inventory now identifies
`dsc10-tutor-jlab`, `dsc10-tutor-logger`, and `jupyterlab-ai-tutor` as concrete source
candidates. This check follows their request, notebook and logging paths at pinned
commits. Where history permits, inspect the latest source before August 7, 2026,
the end of the previously audited data window, separately from current code.
A historical commit is not automatically a verified deployed version.

Use read-only GitHub/source access. Keep retrieved source and metadata under
ignored `data/episode-pilot/observation-contract-v2/`; import no sibling code into
the simulator. Do not fetch secrets or student records, modify the deployed tutor,
query the database, call a model, or add a UI dependency. The output is a concrete
field/path map and an observation-boundary decision, not another forecast batch.
Stop after these bounded source traces and document any deployment evidence that
still needs to be supplied. The Marimo and exercise explorations do not gate this.

## Findings

The source identifies a concrete mismatch: **notebook content sent to the tutor
is not the same record as notebook content persisted for research**. The old DSC
10 client sends a sanitized notebook on each normal tutor request, but emits
notebook source only for the first completed turn of a conversation. It obtains
that logged source again after streaming finishes. A student can therefore edit
while waiting and produce a logged capture different from the request's source.
This is a possibility supported by the code, not a claim that it happened in a
particular inspected example.

| Path | What the pinned source does | Research consequence |
|---|---|---|
| Tutor request | Serializes current sanitized notebook plus structured context before dispatch | The tutor can see updated work even when student chat is terse |
| Query log | Emits raw question, mode, notebook name and existing conversation ID | Does not preserve the notebook or complete effective request context |
| Notebook-info log | Emits source on the first completed turn only, by reading the notebook again | Later per-turn work is absent from this emission path; first capture is not proven to equal the request snapshot |
| Sanitizer | Copies cell type, source, execution count and selected outputs, omitting native cell IDs | Positional alignment cannot become persistent identity by relabeling |
| Grader log | Emits grader ID, output, success flag, timestamp and notebook name | No execution/request ID or submitted-source revision connects the result to exact work |
| Event collector | Stores the supplied payload dictionary in JSONB without a nested whitelist | Fields could be retained if emitted; the collector cannot reconstruct missing client data |

Old-client evidence at `3eab46cd094c4bd2a74fe49d69b6832b8e1d583e`:
[request and logging](https://github.com/dstl-lab/dsc10-tutor-jlab/blob/3eab46cd094c4bd2a74fe49d69b6832b8e1d583e/src/components/Chat.tsx#L330),
[cell sanitization](https://github.com/dstl-lab/dsc10-tutor-jlab/blob/3eab46cd094c4bd2a74fe49d69b6832b8e1d583e/src/utils/notebookSanitizer.ts#L165),
[grader payload](https://github.com/dstl-lab/dsc10-tutor-jlab/blob/3eab46cd094c4bd2a74fe49d69b6832b8e1d583e/src/utils/autograderLogger.ts#L3).
Collector evidence at `078e54cd651b0dc7c734a34f9d2056148733664d`:
[event model](https://github.com/dstl-lab/dsc10-tutor-logger/blob/078e54cd651b0dc7c734a34f9d2056148733664d/api/models.py#L4) and
[insert path](https://github.com/dstl-lab/dsc10-tutor-logger/blob/078e54cd651b0dc7c734a34f9d2056148733664d/api/main.py#L40).

The first query can be emitted before the backend assigns a conversation ID.
Its eventual response and notebook-info record receive the resolved ID. This is
consistent with the earlier unlinked-query recovery finding, without proving a
particular source version was deployed for each record.

The old backend consumes the notebook in its current prompt. Its conversation
store keeps student/tutor text in a process-local dictionary, and the inspected
agent creates an in-memory ADK session. No durable per-turn notebook archive was
found in this request path. An external store or platform trace remains possible;
these source reads do not establish global absence.

## History and deployment limits

The old client's default head is dated June 11, 2026. A separate source snapshot
available before the April example (`8f8957f0f10716fb5c364a553716ff1bf956db6c`,
April 12) has the same first-turn-only, response-time capture pattern. The source
available before the July example is the June head. These are available revisions,
not an installation or deployment record for the students in the dataset.

The newer `jupyterlab-ai-tutor` repository began July 23 as a generalization of the
DSC 10 extension. Its inspected September 15 head,
`7ffe89e8577f920a62caa27eb20e4aee59233b2d`, retains the same capture and grader
binding limits. It is relevant to a future change, but cannot stand in for the
February–July deployed client. See its
[logging path](https://github.com/dstl-lab/jupyterlab-ai-tutor/blob/7ffe89e8577f920a62caa27eb20e4aee59233b2d/src/components/Chat.tsx#L367).

The collector's reachable history begins February 9. Its request model and table
schema retain the same payload mechanism; receiver changes switch database
connection handling, not payload retention. Deployment source uses a mutable
`latest` image, and no per-event deployment identifier or historical deployed
image digest was established. GitHub's empty deployment list is not proof that
GitLab/Kubernetes deployment records do not exist.

## Consequence for the existing simulations

The saved net-change counts remain reproducible, but the initial capture must be
described as **response-time recorded work**, not a verified copy of the notebook
the tutor originally saw. The old recovery routine establishes an exchange match;
it does not establish request/capture source equality. Keep all original receipts
and completed scores. No historical target is replaced or relabeled here.

The next-action validation gap is upstream of labeling. The preserved data can
still support its stated chat and conditional net-state comparisons. A complete
edit/check trajectory or exact tutor-input replay needs additional evidence;
new labels or more generations cannot supply missing observations.

## Smallest useful future logging change — proposed, not implemented

Start with **work at each help request**, reusing the existing event collector:

1. Serialize the notebook once before dispatch, and retain that exact request-time
   string with the effective question/context. Log it on every request, with a
   shared request ID and explicit capture time. Do not re-read the notebook after
   the tutor finishes to represent that earlier state.
2. Link the returned response and resolved conversation ID to the same request ID.
   Record event schema/client version and preserve native cell IDs where available.
   Represent missing task/version identity explicitly rather than deriving it from
   notebook name alone. A source hash must verify the retained source bytes.
3. Test an invented two-turn example: edit during streaming, then submit another
   request. The first retained snapshot must stay unchanged, the second must show
   the edit, and both responses must join their original requests. Reopening the
   emitted records must reproduce that sequence without calling a model.

This would support work change plus chat between help requests. It would not
recover every silent edit, establish student effort, or make existing grader logs
source-bound. Execution-request/result binding is a separate step; reactive
Marimo reruns must also remain distinguishable from explicit student checks.
No collector schema rewrite or general event framework is justified by this pass.

The remaining scope decision is whether the project can prepare a change for
future tutor sessions or must continue solely with existing data. No deployed
service, source repository or student collection behavior has been changed.

## Verification and stopping point

Separate source audits covered the client, successor and collector; retrieved files and immutable
commit metadata are retained under `data/episode-pilot/observation-contract-v2/`.
The old client was checked at two historical source checkpoints, separately from
the newer client and collector histories. No imported upstream code was executed.
This turn changes research documentation only. No database/model calls, new
ratings, source-format migration or teammate-task duplication occurred.
