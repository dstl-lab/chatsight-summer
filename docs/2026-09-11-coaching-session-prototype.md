# Coaching session prototype

Minchan selected the coaching direction, deferred the adventure and support-placement
alternatives, and requested Animal Crossing as a stylistic reference. Use an original
cozy village, animal characters, rounded forms and warm natural materials. The first
deliverable is an interactive storyboard for review, not a validated agent world.

**Paused:** Minchan subsequently said, "But before we design the end product,
let’s work on actually making the simulated students work." Preserve this
exploration and resume work on the simulator; no interface review is requested.

## Design and implementation plan

Build one static page, following the existing self-contained HTML convention in
src/eval/. Serve only that directory with Python's standard-library HTTP server.
No framework, backend route, model call, database access or production agent change.

The page pairs a village illustration with a coaching notebook. Two fictional
learners independently compare tomatoes per plant in two garden beds. The educator
inspects work and an earlier interaction, chooses one of three supplied coaching
approaches, sees an explicitly scripted contribution, and can revisit every branch
in a playbook. Retrying starts from the same original situation; it does not extend
the previous answer. A sample with no further message leaves later work unknown.
No choice earns learning points or claims an intervention effect.

Palette: forest #294E43, grass #66815A, mint #CEE1D4, paper #FFFBEF,
honey #E8CE8F, ink #303D35. Rounded system display type and Avenir Next body text;
left-aligned readable copy. The illustrated studio is the main visual feature.
Use keyboard-operable native controls, visible focus, reduced-motion support,
responsive layout, and a persistent "Scripted sample" explanation.

- [x] Create src/eval/coaching_session.html and one original illustration asset.
- [x] Add one Node regression covering retained alternatives, learner separation,
      revisiting a branch and the no-reply boundary. Exercise the actual page code.
- [x] Inspect the page in a browser at desktop and narrow widths; verify the whole
      choose → response → retry → playbook flow and keyboard/dialog behavior.
- [x] Verify frozen experiment pins and document the result. Preserve the work in
      the existing isolated branch; interface feedback is deferred.

Both Node checks (`tests/coaching_session.cjs` and the existing review-navigation
check) pass. Browser checks at 1280×720 and 390×844 covered retained alternatives,
learner separation, no-reply, modal focus containment and Escape/focus restoration;
neither width overflows horizontally. Console warnings/errors were empty. The
offline experiment verifier passed all 370 current pins, including 358 archive
pins and 350 unchanged live parent pins. No model calls were made for the page.
The playbook lasts only for the open page. To inspect this deferred artifact,
serve `src/eval` with Python's standard-library HTTP server and open
`coaching_session.html`.

The storyboard introduces no human labels and uses no student dialogue. The
reviewed real/generated behavior packets remain a separate pending calibration
task. The final game still needs model-backed encounters and evidence of fidelity.

## Illustration provenance

coaching-village.png was produced with the built-in image-generation tool for this
prototype. No model/version selector was exposed. The original 1536×1024 PNG is
copied unmodified. Prompt: an original elevated village diorama with a wooden
outdoor learning pavilion, exactly two original animal learners (fox and rabbit)
using small laptops, blank chalkboard, green terrain, round trees, flowers, mint
river and bridge; warm afternoon light, matte tactile forms, honey wood, cream and
sage palette; no text, UI, branding or existing franchise characters/assets.
