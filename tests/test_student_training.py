"""Recorded targets and transcript roles survive local training serialization."""
from copy import deepcopy
import importlib.util
import json

import pytest


class Tokenizer:
    eos_token_id = 0

    def apply_chat_template(self, messages, **options):
        assert options == {'tokenize': True, 'add_generation_prompt': True,
                           'enable_thinking': False}
        return self.encode(json.dumps(messages, ensure_ascii=False) + '<assistant>')

    def encode(self, text, add_special_tokens=False):
        assert add_special_tokens is False
        return [ord(character) for character in text]

    def decode(self, tokens, **options):
        return ''.join(chr(token) for token in tokens)


def test_recorded_content_and_tutor_boundary_are_preserved():
    assert importlib.util.find_spec('src.eval.student_training'), 'Training helper is missing'
    from src.eval.student_training import INSTRUCTION, encode_example, messages

    prefix = [{'role': 'student', 'text': '  왜?\n', 'id': 'private-id'},
              {'role': 'tutor', 'text': 'Try x = 2.', 'response': 'hidden future'}]
    before = deepcopy(prefix)
    reply = '\n  아, 알겠어요.  \n'
    tokenizer = Tokenizer()
    prompt = messages(prefix)
    assert len(prompt) == 1 and prompt[0]['role'] == 'user'
    transcript = json.loads(prompt[0]['content'][len(INSTRUCTION):])
    assert transcript == [{'role': 'student', 'text': '  왜?\n'},
                          {'role': 'tutor', 'text': 'Try x = 2.'}]
    assert 'private-id' not in prompt[0]['content']
    assert 'hidden future' not in prompt[0]['content']
    ids, start = encode_example(tokenizer, prefix, reply)
    assert tokenizer.decode(ids[start:]) == reply
    other_ids, other_start = encode_example(tokenizer, prefix, 'different future')
    assert ids[:start] == other_ids[:other_start]
    trained, train_start = encode_example(tokenizer, prefix, reply, training=True)
    assert trained == ids + [0] and train_start == start
    assert prefix == before

    for invalid_prefix in ([], prefix[:1], [{'role': 'tutor', 'text': 'only tutor'}],
                           [{'role': 'assistant', 'text': 'wrong role'}, prefix[-1]],
                           [{'role': 'student', 'text': None}, prefix[-1]]):
        with pytest.raises(ValueError):
            encode_example(tokenizer, invalid_prefix, reply)
    for invalid_reply in ('', ' \n\t', None):
        with pytest.raises(ValueError):
            encode_example(tokenizer, prefix, invalid_reply)

    class LossyTokenizer(Tokenizer):
        def decode(self, tokens, **options):
            return super().decode(tokens).strip()

    with pytest.raises(ValueError, match='preserv'):
        encode_example(LossyTokenizer(), prefix, reply)
