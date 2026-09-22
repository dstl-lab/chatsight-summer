"""One explicit UI submission over the unchanged saved notebook runner."""
import os
from functools import partial
from pathlib import Path
import re

from src.agents import notebook_student as student, notebook_tutor, tutor_context


def _require_binding(binding, send):
    if send is not True:
        raise ValueError('This workspace was opened without sending enabled.')
    if (not isinstance(binding, dict) or set(binding) != {'session_sha256', 'state_sha256'}
            or any(not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value)
                   for value in binding.values())):
        raise ValueError('Inspect the saved session to obtain a valid binding.')


def _generate(folder, prompt, schema):
    from dotenv import load_dotenv

    # Both submission paths validate the displayed state before reaching this callback.
    load_dotenv(Path.cwd() / '.env')
    load_dotenv(Path(__file__).resolve().parents[3] / 'main/.env')
    model = student._read(folder / 'session.json')['model']
    return student.llm.make_generate(os.environ['GEMINI_API_KEY'], model=model)(prompt, schema)


def advance(folder, *, binding, tutor_reply=None, send=False, generate=None, check=None):
    _require_binding(binding, send)
    folder = Path(folder)
    student.step(folder, tutor_reply=tutor_reply, generate=generate or partial(_generate, folder),
                 check=check or student.notebook_runtime.check_work, max_actions=1,
                 **{'expected_' + key:value for key, value in binding.items()})
    return tutor_context.snapshot(folder)


def respond(folder, *, binding, policy, send=False, generate_tutor=None, generate_student=None, check=None,
            reference=None):
    """Generate one bound tutor reply and one student decision; never retry a saved exchange."""
    _require_binding(binding, send)
    if not isinstance(policy, str) or not policy.strip():
        raise ValueError('Write a tutor policy first.')
    folder = Path(folder)
    if tutor_context.snapshot(folder)['binding'] != binding:
        raise ValueError('Stale tutor context: reload the saved session before replying.')
    output = folder / 'tutor-exchanges' / binding['state_sha256']
    if output.exists():
        raise FileExistsError('A tutor exchange is already saved for this state. Reload or inspect that exchange; it will not be resent.')

    def bound_tutor(prompt, schema):
        # respond takes its own snapshot: check that exact saved input before sending it.
        if tutor_context.read_handoff(output / 'context.json')['binding'] != binding:
            raise ValueError('Stale tutor context: the student changed before tutor generation.')
        return (generate_tutor or partial(_generate, folder))(prompt, schema)

    notebook_tutor.respond(folder, output, policy=policy, reference=reference,
        model=student._read(folder / 'session.json')['model'], max_actions=1,
        generate_tutor=bound_tutor, generate_student=generate_student or partial(_generate, folder),
        check=check or student.notebook_runtime.check_work)
    return tutor_context.snapshot(folder)
