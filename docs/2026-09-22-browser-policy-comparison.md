# Saved policy comparisons in the browser

The user approved fixing PR #47 and beginning integration after the assessment.
First slice: open a saved tutor-policy pair in the existing Compare area, show
its common starting conversation once, and show each arm's fixed instructions,
tutor response, and student result. Ready, failed, interrupted, reply and no-reply
are distinct states. This uses the existing browser shell and pair engine.

Keep the completed communication-review format supported. A new explicit
policy-pair launch option must not reinterpret that format. Load local evidence
through verified read-only snapshots, restrict symlinks and paths, pin the
comparison manifest at startup, and escape displayed content. No additional
replay panel, new provider calls, or new scoring/labeling. Live pair creation and
batch controls follow after this saved-pair view is verified.

Validate with authored saved pairs: ready, completed, no-reply, saved failure,
tampering and unchanged input files, plus existing browser navigation checks.
Implemented via explicit `--policy-comparison`. `--comparison` still accepts only
the completed communication-review format; the options are mutually exclusive.
The shared question retains simulated origin. Fixed instructions are expandable
inside each comparison column; tutor text uses the existing safe Markdown display
and student text remains literal. No live pair creation or batch controls yet.

Combined validation: 618 Python tests passed, three optional tests skipped; all
seven Marimo checks and three Node checks passed. HTTP regressions cover ready,
reply, no-follow-up, saved tutor error, interrupted tutor/student requests, busy
locks, missing locks, tampering and symlinks, with unchanged input evidence.
Independent review and desktop browser inspection passed. An entirely authored
offline example is served read-only on localhost:8429; the existing private-data
preview on 8428 remains unchanged. No provider or notebook execution occurred.

Next slice: browser creation of a frozen pair and explicit generation through the
existing bound runner. Do not infer improved simulator fidelity from this UI work.
