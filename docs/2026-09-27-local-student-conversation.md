# One bounded conversation with the saved local student

Continue from the closed training pilot without changing weights or requesting
labels. Compare the starting Qwen3-4B model and its saved student adapter in two
independent chat sessions. Reuse `chat_student`, `chat_workspace.respond` and the
read-only browser workspace; do not add another simulator or viewer.

Select one of the existing development query prefixes, without reading its
reference response or previous score: require at least two visible student turns
and at most 2,048 student-prompt tokens, then take the smallest SHA-256 of
`local-student-conversation-v1:<query-id>`. Preserve selection coverage and the
exact prefix. Later historical turns are never read into either generated branch.

Both students receive the exact training serialization with thinking disabled.
The tutor always uses the unchanged base model, the existing tutor context prompt,
and this policy: "Give concise programming help based on the conversation. Address
the current request, offer one concrete next step, and ask at most one clarifying
question when needed. Do not invent missing notebook work or claim execution."
Fresh tutor replies respond only to their own branch. Different later tutor text
is an expected consequence of different generated student messages, not a fixed
policy change.

Each arm permits three student replies and two tutor replies: at most ten local
generations total. Run the starting arm first, then the adapter arm. At matching
roles/positions use the same fixed seed: 20260928 + 10 * position, plus one for
tutors. Temperature 0.7, top-p 0.8, top-k 20, thinking disabled; limits are 256
student and 384 tutor tokens, with a 4,096-token prompt-plus-output ceiling.
No context truncation, retry, repair, replacement prefix, extra sample or training.
Use a 120-second per-call timeout, advisory 16 GiB MLX allocation limit and abort
on a reported peak over 16 GiB. Transient excess remains possible.

Only a nonblank response ending at the tokenizer's end-of-message boundary is
delivered to the chat engine. The callback wraps that message in the existing
reply schema; the model itself produces raw text. Empty output, length limits,
context limits, interruption or errors stop the affected arm and retain its raw
receipt. These outcomes do not establish student silence or abandonment. Stop
the whole pilot after both arms reach their budgets or a saved stopping condition.

Keep exact text, including blank lines, from the saved episode. Do not reconstruct
it from the legacy harness prompt, which omits blank lines. Preserve the actual
local prompt tokens, generation settings, raw output and model/adapter identities
in separate per-call receipts. Session model metadata identifies the common base;
adapter use is explicit in the local receipts and arm metadata. The historical
schema prompt remains a harness record, not a claim about model input.

Freeze sources, model hashes, selected input, adapter receipt and settings before
generation. Use exclusive output directories, preserve original evidence, and
verify the recorded chat replay and actual prompt/history joins afterward. The
browser opens the saved sessions without sending enabled. All data and results
stay local; no changes to Gemini, historical experiments or trained weights.

This is one developmental conversation, not a fidelity ranking, measured tutor
policy effect or evidence that the improved prediction score generalizes to
free conversation. Report literal observed differences and failures without
turning them into new human labels. No reviewer task is created.
