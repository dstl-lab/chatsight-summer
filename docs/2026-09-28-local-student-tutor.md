# Test tutor instructions with an explicitly selected local student

For independent branches from the same starting message, use the subsequent
[local policy comparison workflow](2026-09-28-local-policy-comparison.md#run-it).
This guide describes the original single-conversation path.

The normal browser command can run the trained student, but requires every tutor
reply to be typed. Add an explicit Gemini tutor model to that same single-chat
command. Reuse the existing tutor-instructions editor, saved tutor exchange and
structured local-student callback. Typed replies remain the default without the
new option; policy-pair cloning and notebook actions remain unsupported here.

`--gemini-tutor-model MODEL` selects the tutor separately from the local student.
It requires the existing local model/runtime arguments. Save the selected tutor
model and provider in each tutor receipt; local student identity stays in its
backend record. Show the tutor model and Google Gemini destination before sending.
Editing instructions or opening the page sends nothing. An explicit submission
with `--send` makes one tutor request, then one local student decision from the
exact returned tutor text. Manual replies use only the local student.

Reuse the provider helper with a single-attempt option: no application or SDK
retries, a 120-second request timeout, and preserved failure receipts. Provider
errors never invoke the local student; local errors after a successful tutor
reply never resend that tutor or fall back to a cloud student. API credentials
are loaded only at the actual tutor request and never saved in session records.

Verify routing, different model identities, exact histories, changed instructions,
read-only reopen, stale submissions and failures using fictional inputs and
injected providers. A bounded fictional live check may use two local decisions
and one Gemini tutor request, retaining failures without rerolls. No private
course dialogue, new labels, training, or changes to closed studies are needed.

This enables exploratory tutor-instruction testing. It does not establish student
realism, measure a causal policy effect, simulate notebook activity, or predict
whether a student returns. The selected adapter remains experimental. A Gemini
model alias records the requested model, not a guaranteed immutable model version.

## Run it

Create a fresh chat and configure the local model, runtime and optional adapter as
in the [local student guide](2026-09-28-local-student-backend.md#run-it). Keep its
decision budget small. Add the tutor model explicitly:

```sh
.venv/bin/python -m src.agents.browser_workspace \
  data/local-student-demo --chat --port 8441 \
  --student-model /absolute/path/to/local-mlx-model \
  --student-python /absolute/path/to/mlx-environment/bin/python \
  --student-adapter /absolute/path/to/adapter-directory \
  --gemini-tutor-model gemini-2.5-flash
```

This command opens read-only. Supply `GEMINI_API_KEY` through the environment or
the existing `.env` setup; it is read only when generating a tutor reply. Restart
with `--send` to enable submissions. **Continue run** first generates a local
student message. Then **Reply to student → Generate from instructions** lets you
edit the tutor instructions and generate one tutor reply plus one local student
continuation. **Write a reply** remains available and uses only the local student.
Optionally load starting instructions with `--policy-file /path/to/policy.txt`.

The tutor receives the visible conversation, pending student message and submitted
instructions; the local student receives that conversation with the returned tutor
reply appended. Both are saved. Tutor receipts under `tutor-exchanges/` identify
Google Gemini and the explicitly requested tutor model; local-student records
identify the local model and adapter. Changing instructions affects only the next
submitted exchange. It does not alter saved replies or create a matched comparison.

Reloading never resends an exchange. Reopen with the same backend paths, without
`--send`, for read-only playback. Omit the Gemini option to return to typed tutor
replies; changing the local backend requires a fresh session. Error receipts stay
terminal. A provider failure is not evidence about the student's behavior.

## Verification

The fictional browser check completed exactly two local student calls and one
Gemini tutor request, using the explicit full-pass adapter as an experimental
option. The student wrote `2`; the tutor answered that `values.count(3)` returns
2; the student then wrote `2 more?`. All outputs are retained without rerolls.
The final question demonstrates why a working connection is not evidence of
student realism. The completed run reopens read-only at localhost port 8441.

The saved audit verifies source hashes, local model/adapter/runtime identity,
exact tutor policy and conversation payload, exact returned tutor text in the
second student request, token decoding, EOS and the fixed call budget. The normal
CLI and actual browser controls were used. All 742 Python tests pass with three
optional skips and the existing Starlette/httpx warning; the Node workspace check,
JavaScript syntax check and independent integration review also pass. The run is
closed. No further generation, labeling or adapter change follows from this check.
