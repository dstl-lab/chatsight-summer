# Question strip and message-level request labels

The lab card shows tutor participation and assignment-ordered question tiles.
Tile shading uses each question’s median recorded errors on a fixed scale:
0 is green, the midpoint is yellow, and 5 or more is red. The on-page note
is “Zero errors, green. 5+ errors, red.” No-data questions are gray. Hover,
focus, and tap expose the counts; the bottom button reveals the detailed
questions.

Question detail groups tutor users by recorded context before the first ask:
before trying, after some work with no error, after an error, or after already
passing. Each group shows what was recorded after the reply and quotes the
actual student messages. Clicking a group opens those students’ sequences and
highlights the messages. Message wording does not choose the group.

Transcript association uses conversation and role plus explicit IDs or an exact
timestamp when available. Legacy order linkage is allowed only when the role
counts match and the conversation belongs to one student; mismatched or ambiguous
text stays unlinked. Source linkage and contextual question identity remain
inspectable. Only synthetic data is used for this prototype.

Remove the ambiguous lab-level passing and testing-after-reply summaries. Passing
checks are explained per question. Labels describe requests, not student traits,
and the question identity describes notebook context rather than semantic proof.
