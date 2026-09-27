"""Exact recorded-message serialization and target-only loss for local MLX runs."""
import json
import math


INSTRUCTION = (
    "Write the student's next message after the final tutor turn. Continue in the "
    "student's language and style. Return only the student message. The following "
    "JSON is a transcript, with explicit student and tutor roles:\n"
)


def messages(prefix):
    if not isinstance(prefix, list) or len(prefix) < 2:
        raise ValueError('A prefix needs student and tutor turns.')
    if any(not isinstance(turn, dict)
           or turn.get('role') not in ('student', 'tutor')
           or not isinstance(turn.get('text'), str) for turn in prefix):
        raise ValueError('Every prefix turn needs a student/tutor role and text.')
    if prefix[-1]['role'] != 'tutor' or not any(t['role'] == 'student' for t in prefix):
        raise ValueError('A prefix needs a student contribution and must end at a tutor turn.')
    transcript = [{'role': turn['role'], 'text': turn['text']} for turn in prefix]
    return [{'role': 'user', 'content': INSTRUCTION + json.dumps(transcript, ensure_ascii=False)}]


def encode_example(tokenizer, prefix, response, training=False):
    if not isinstance(response, str) or not response.strip():
        raise ValueError('A recorded response must be nonblank; blanks are not stop targets.')
    prompt = tokenizer.apply_chat_template(
        messages(prefix), tokenize=True, add_generation_prompt=True, enable_thinking=False,
    )
    target = tokenizer.encode(response, add_special_tokens=False)
    if not target or tokenizer.decode(
        target, skip_special_tokens=False, clean_up_tokenization_spaces=False,
    ) != response:
        raise ValueError('Tokenization must preserve the recorded response exactly.')
    if not prompt:
        raise ValueError('The serialized prompt must contain tokens.')
    if training:
        if not isinstance(tokenizer.eos_token_id, int):
            raise ValueError('Training requires one end-of-message token.')
        target = target + [tokenizer.eos_token_id]
    return prompt + target, len(prompt)


def target_loss(model, batch, lengths):
    import mlx.core as mx
    from mlx_lm.tuner.trainer import default_loss

    # MLX-LM 0.31.3 uses an inclusive upper bound; exclude the first padding token.
    return default_loss(lambda inputs: model(inputs).astype(mx.float32),
                        batch, lengths - mx.array([0, 1]))


def score_example(model, ids, start):
    if not isinstance(start, int) or not 0 < start < len(ids):
        raise ValueError('Scoring needs a nonempty prompt and target.')
    import mlx.core as mx
    import mlx.nn as nn

    model.eval()
    logits = model(mx.array([ids[:-1]], dtype=mx.int32))
    target_logits = logits[0, start - 1:, :].astype(mx.float32)
    losses = nn.losses.cross_entropy(target_logits, mx.array(ids[start:], dtype=mx.int32))
    nll_sum = float(losses.sum().item())
    if not math.isfinite(nll_sum):
        raise ValueError('Target loss is not finite.')
    count = len(ids) - start
    return {'nll_sum': nll_sum, 'target_tokens': count, 'nll_mean': nll_sum / count}
