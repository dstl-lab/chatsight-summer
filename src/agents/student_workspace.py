"""One explicit UI submission over the unchanged saved notebook runner."""
import os
from pathlib import Path
import re

from src.agents import notebook_student as student, tutor_context


def advance(folder, *, binding, tutor_reply=None, send=False, generate=None, check=None):
    if send is not True:
        raise ValueError('This workspace was opened without sending enabled.')
    if (not isinstance(binding, dict) or set(binding) != {'session_sha256', 'state_sha256'}
            or any(not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value)
                   for value in binding.values())):
        raise ValueError('Inspect the saved session to obtain a valid binding.')
    folder = Path(folder)

    def provider(prompt, schema):
        from dotenv import load_dotenv

        # The runner validates and locks the displayed state before reaching this callback.
        load_dotenv(Path.cwd() / '.env')
        load_dotenv(Path(__file__).resolve().parents[3] / 'main/.env')
        model = student._read(folder / 'session.json')['model']
        return student.llm.make_generate(os.environ['GEMINI_API_KEY'], model=model)(prompt, schema)

    student.step(folder, tutor_reply=tutor_reply, generate=generate or provider,
                 check=check or student.notebook_runtime.check_work, max_actions=1,
                 **{'expected_' + key:value for key, value in binding.items()})
    return tutor_context.snapshot(folder)
