# Distinguish a chat message from a notebook edit

The completed historical-context comparison preferred recorded next messages
over generated code messages in two cases, with explicit qualifications; the
third pair was equivalent. This is a development diagnostic, not an accuracy
score. A possible mechanism is ambiguity in asking for a student "contribution":
code that belongs in the notebook can instead appear as a message to the tutor.
The existing notebook-action path already separates edits from optional chat.
Test the communication prompt before changing the simulator or adding machinery.

Reuse the same three exact inputs from `evaluation-communication-v1`, cases 1,
3 and 4. Keep historical notebook cells, dialogue, unknown current work and
observation, schema and Gemini 2.5 Pro defaults unchanged. Make six fresh calls:
original/clarified for case 1, clarified/original for case 3, original/clarified
for case 4. Prior generated responses and human feedback never enter the inputs.
Case 2 remains excluded without replacement.

The clarified condition inserts only this paragraph before the unchanged JSON:

> For decision "reply", text contains only what the student would send to the tutor
> in chat. It does not represent an unsent notebook edit. Code belongs in text
> when the proposed action is sending that code to the tutor.

Code, substantive answers and no-reply remain permitted. Do not assert that the
student knows the tutor sees notebook changes, forbid repeating code, prescribe
a question number or add a brevity rule. Neither condition reconstructs silent
work, executes code or invents feedback. This remains a communication-only probe.

Use the existing continuation schema, provider adapter, atomic receipt writer
and review formatting. New private scripts and exact disclosure stay under
`data/episode-pilot/communication-channel-v1/`. Verify source hashes and identical
JSON across conditions; persist pending records before credentials or provider
creation, retain errors/retries, refuse resends and replay offline. Record the
standing grant and actual continuation instruction without fabricating exact
payload approval. Preserve any actual automatic rejection separately.

Show one case at a time with condition names hidden and exact shared context.
If the two new responses are identical, show them once while retaining both
receipts. Human review determines plausibility; reduced code length or agreement
with a recorded message is not an automatic improvement. One draw per condition
on three exposed cases cannot estimate distributions or establish a causal effect.
Keep the original production prompt unless stronger evidence warrants a change.
