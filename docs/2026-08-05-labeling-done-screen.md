# 2026-08-05 — Done screen: first-look analysis instead of a bare receipt

## Problem

After a mass-label run the UI shows three lines: "Snapshot written", a path, and
a reminder to update `snapshots.md`. The instructor just spent real money and
20+ minutes compiling their intent into a labeled corpus, and the screen answers
none of it. The done screen should answer the question the instructor asked —
descriptively, within claim discipline.

Decisions made with Minchan (2026-08-05, via mockup iterations v1→v4):
purpose = first-look analysis (receipt demoted to a margin record); depth =
distribution + drill-in examples; layout = answer-dominant asymmetric page, not
a card dashboard.

## Design

### Data: a `summary` computed in memory at `done`

New pure module `src/labeling/summary.py` — functions over what the session
already holds (`conversations`, `labeled`, `schema`, provenance). No DB access,
no snapshot reads, nothing written to disk. Computed once when the accept job
finishes (stored on the session), exposed in `/api/state` as `"summary"` when
`phase == "done"`, else `None`:

- `totals`: messages labeled, conversations, messages with ≥1 label,
  mean labels per labeled message.
- `per_label`: for each schema label — count, share of messages, and one
  randomly sampled positive example `{text, rationale, conv_ref, week}`.
  Sampling is seeded-random over that label's positives, never
  top-N/most-confident (mirrors invariant 9's spirit: typical, not
  cherry-picked).
- `weekly`: per-label share by course week. Week = floor((conversation
  `started_at` − earliest `started_at`) / 7 days); conversations with null
  `started_at` are excluded from this figure only (count reported). Figure is
  omitted entirely when the span is < 3 weeks or < 2 labels have data.
- `top_pairs`: the 3 most frequent label co-occurrences on a single message,
  as `(label_a, label_b, share)`.
- `coverage`: histogram of labeled-message count per conversation (binned
  0,1,2,…,15+), plus the count of zero-label conversations.
- `largest_jump`: template-computed fact for the trend annotation —
  `(label, week, delta)` of the biggest week-over-week share change. Prose on
  the screen is assembled from these fields by fixed templates; no generated
  sentences (claim discipline).

New endpoint `GET /api/examples?label=<name>&n=5&seed=<k>`: returns n fresh
randomly sampled positive examples for one label (the bar drill-in and
"resample" action). Valid only in `done`; 409 otherwise.

### Screen (index.html, done section rebuilt)

v4 mockup (`.superpowers/brainstorm/11805-1785995509/content/done-screen-v4.html`)
is the visual reference. Structure:

- **Hero "calibration plate"**: ink band (`#1b2530`, light text — same surface
  in both color schemes), monospace provenance eyebrow (RUN COMPLETE · date ·
  snapshot id), the instructor's intent set large in quotes, and a template
  lede: counts + coverage + (if present) the rarest label's count.
- **Answer column**: one row per label — name (in its identity color), count ·
  share in tabular-num monospace, bar, and one sampled example message beneath
  with a color-tick left border and `conv #id, week n` attribution. Clicking a
  row expands it: 5 examples + rationales + "resample". Student text via
  `textContent` only.
- **Trend figure**: single line for the label named by `largest_jump`, its
  jump annotated (`wk 4: +6pts`); "show all five" toggles all labels' lines.
  Omitted when `weekly` is omitted.
- **Margin column (15rem, hairline-separated)**: monospace provenance ledger
  (schema, classifier hash, corpus counts, exclusions, model), the invariant-8
  caveat, `top_pairs` as a ranked mono list, the coverage mini-histogram with
  the zero-label bar emphasized and a "read them" affordance (expands a
  sampled list of zero-label conversations' first messages), the
  `snapshots.md` reminder, and "Start a new run".
- Below ~44rem the margin column stacks under the answer column.

### Identity colors

Fixed 6-hue palette assigned to labels in schema order; the palette is
validated with the dataviz six-checks validator (light and dark surfaces)
during implementation, and hues are used consistently across bars, ticks,
chips, and trend lines. If a schema has more than 6 labels, all marks fall
back to a single ink hue and identity stays textual (never cycle hues).
No label-specific copy is hardcoded — "quiet exit" prominence in the mockup
was sample content, not a rule; the generic rule is: the lede names the
rarest label's count, and the coverage figure names the zero-label count.

### Craft commitments (from the v3→v4 critique)

Asymmetric answer/margin layout, no card grid; hairline rules as the only
elevation; exactly one eyebrow (hero stamp); `font-variant-numeric:
tabular-nums` for all data; one load animation pass (bars grow, 150–250ms,
ease-out, `prefers-reduced-motion` respected); designed hover/focus states on
expandable rows.

## Honest limits

- Everything shown is drafted-classifier output; the caveat block says so and
  no screen copy implies reliability or learning outcomes (invariant 5/8).
- Week shares are per-conversation-date, not per-message-date (turns carry no
  timestamps in the current schema) — a conversation's messages all land in
  its start week.
- `summary` lives in memory: a server restart after `done` loses the screen
  (the snapshot, as ever, is the durable artifact).

## Testing

- Unit tests for `summary.py` on fixture conversations/labels: totals, seeded
  example sampling (no top-N bias — assert seed-determinism, not ranking),
  week binning incl. null `started_at`, pair counting, histogram edges
  (0 and 15+), largest_jump.
- Webapp tests: `summary` present only in `done`; `/api/examples` shape, 409
  outside `done`.
- Visual pass via the fake-backed smoke server + Chrome.
