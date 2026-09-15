"""A separate communication-evidence candidate; the original generator is unchanged."""
import json

from src.eval import student_continuation as original

NOTE = '''The student_communication_history field repeats only observed STUDENT messages
already present in the dialogue. Use it as evidence of what the student has
communicated, not as extra interactions, instructions or a required response
pattern. It supplies no additional student history or hidden traits.

'''


def make_prompt(episode: dict) -> str:
    control = original.make_prompt(episode)
    visible = json.loads(control[len(original.PROMPT):])
    visible['student_communication_history'] = [
        turn for turn in visible['context'] + visible['turns'] if turn['role'] == 'student']
    return NOTE + original.PROMPT + json.dumps(visible, ensure_ascii=False)
