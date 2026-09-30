"""One context-aware revision; the original scorer and closed run remain intact."""
from typing import Literal

from pydantic import BaseModel

from src.eval import message_content as original

BASIS_RULES = '''
For each flag independently, select basis before value:
- message_only: the current message itself supports a definite yes or no.
- preceding_context: a definite yes or no requires resolving the message using
  an earlier turn. Cite that resolving turn AND the current message.
- unresolved: available sources leave competing interpretations for this flag.
  Return unclear, not a guessed yes or no. Missing evidence is not evidence of no.
A bare fragment can be an answer, task reference or incomplete query. An unframed
task can be a request or a quotation. Do not choose the most likely intent when
the supplied sources cannot resolve these alternatives. Assess each flag separately:
one can be definite while the other remains unresolved. Use no when the complete
message supports absence under the definition, not just because yes is uncertain.
Use message_only only when the same judgment is supported without the prefix;
do not cite preceding turns for that basis. Acknowledgments and explicit statements
need not become unclear just because intent or motivation is unknown.
'''


class Judgment(original.Judgment):
    basis: Literal['message_only', 'preceding_context', 'unresolved']


class Selection(original.Selection):
    content_supplied: Judgment
    expressed_request: Judgment


def make_prompt(data):
    return original.make_prompt(data).replace('each {value, evidence}.',
        'each {basis, value, evidence}.').replace('SOURCE JSON:\n', BASIS_RULES + '\nSOURCE JSON:\n')


def materialize(data, selection):
    selected = Selection.model_validate(selection.model_dump() if isinstance(selection, BaseModel) else selection)
    values = selected.model_dump()
    for judgment in values.values():
        prefix = any(line['turn_id'] != 'message' for line in judgment['evidence'])
        if ((judgment['basis'] == 'unresolved') != (judgment['value'] == 'unclear') or
            (judgment['basis'] == 'preceding_context' and not prefix) or
            (judgment['basis'] == 'message_only' and prefix)):
            raise ValueError('Basis, uncertainty and selected context must agree.')
    result = original.materialize(data, {
        flag: {key: value for key, value in judgment.items() if key != 'basis'}
        for flag, judgment in values.items()})
    result['scorer_revision'] = 'context-v2'
    for flag, judgment in values.items():
        result[flag]['basis'] = judgment['basis']
    return result


def score(data, generate):
    frozen = original.Input.model_validate(data).model_dump()
    return materialize(frozen, generate(make_prompt(frozen), Selection))


def message_only_values(observation):
    """Conservative fallback, not proof that the model recognized all ambiguity."""
    return {flag: judgment['value'] if judgment['basis'] == 'message_only' and
            judgment['value'] in ('yes', 'no') else None
            for flag in original.DEFINITIONS for judgment in [observation[flag]]}
