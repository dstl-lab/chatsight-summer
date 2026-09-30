"""Compare student-only earlier context with the same complete current exchange."""
from collections import Counter
from copy import deepcopy

from src.agents import chat_student
from src.eval import student_continuation

CONDITIONS = ('current-exchange', 'student-history')


def prompts(query):
    episode = deepcopy(chat_student._initial(query)['episode'])
    counts = Counter()
    for turn in episode['turns']:
        counts[turn['phase']] += 1
        turn['id'] = f"{turn['phase']}-{counts[turn['phase']]}"
    students = [turn for turn in episode['context'] if turn['role'] == 'student']
    for number, turn in enumerate(students, 1):
        turn['id'] = f'context-{number}'
    return {condition: student_continuation.make_prompt(episode | {'context': context})
            for condition, context in zip(CONDITIONS, ([], students), strict=True)}
