# Assignment question insights

This prototype summarizes student messages already present in a loaded review
bundle. Open **Examples & files > Assignment insights demo** for invented data,
or choose **Assignment insights** after loading an existing PR100 review batch.
No model call is needed. Message examples link back to their original timeline.

The view groups messages by the bundle's assignment or notebook identifier.
Unknown and conflicting assignments remain unknown. It deduplicates messages
that share a source event identifier within the loaded bundle; messages without
a source identifier are counted separately by session and timeline reference.
Conflicting student identifiers for a duplicate make its student identity
unknown. Counts of known student IDs are lower bounds when identifiers are
missing, and depend on the input identifiers being consistent pseudonyms.

Topics and course concepts are overlapping, deterministic keyword matches, not
semantic clusters, validated student difficulties, or estimates of learning.
Concept phrases are seeded from the DSC 10 course profile, not confirmed against
the specific assignment's teaching materials. Function groups extract explicit
call syntax in student message text, including pasted code. Object methods with
the same name are combined (for example `df.get` and `table.get`); their library
or meaning is not inferred. Calls may be irrelevant context or quoted material,
and bare names and implicit questions are missed. Matched text and the original
conversation are available for review. Search includes all messages, including
those with no topic match.

Results cover only the currently loaded review bundle or batch. Context windows
can omit messages; batches and sampled review exports are not necessarily an
assignment-wide or class-wide population. Unknown assignment and question
attribution cannot be repaired by keyword matching. Validate identifiers, event
deduplication, attribution, and the usefulness of topic labels against approved
real data before interpreting counts as research results.
