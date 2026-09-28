# Check the trained student through browser submissions

Use the separately prepared, zero-decision session and its existing private
launcher to verify the actual browser-to-local-worker path. Make at most two
local student requests: one initial continuation, then one continuation after
the exact authored tutor reply, “Please paste the code or output you want me to
check.” Enter both through the existing browser controls, with no API shortcut.

Use the unchanged trained adapter, serialization, seed and worker limits. A
private launch wrapper disables cloud generation and checks both expected
prefixes and the two-call ceiling before dispatch. No retries, replacement
messages, further training or behavioral labels. Stop on any failure.

Afterward verify exact saved history, local tokens, receipts and unchanged source
hashes. Reload the saved result with sending disabled; the unused decision is a
test limit, not student silence. This is a browser integration smoke check, not
a fidelity comparison or evidence about the authored tutor reply's effects.

Before opening controls, correct the generic UI notice that currently assumes
all configured backends are Gemini. The browser supports injected callbacks and
must not claim a provider that it cannot determine. No layout or action changes.
