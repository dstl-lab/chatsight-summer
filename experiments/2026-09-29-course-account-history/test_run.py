"""Authored integration check: exact schedule, failures, raw replay, no resend."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    run, protocol = load('run'), load('protocol')
    with TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / 'queries.json'
        source.write_text(json.dumps([{'id': str(i), 'conversation_id': str(i), 'student_id': str(i),
            'prefix': [{'role': 'student', 'text': 'earlier ' + str(i)},
                       {'role': 'tutor', 'text': 'earlier reply'},
                       {'role': 'student', 'text': 'help ' + str(i)},
                       {'role': 'tutor', 'text': 'current reply'}]} for i in range(10)]))
        prepared = root / 'prepared'
        pins = protocol.prepare(source, protocol.file_hash(source), prepared)
        bank = {(r['case_id'], r['condition']): r['prompt'] for r in
                json.loads((prepared / 'prompts.json').read_text())}
        schedule = json.loads((prepared / 'plan.json').read_text())['schedule']
        calls = []

        def fake(plan, prompt):
            row = schedule[len(calls)]
            assert prompt == bank[row['case_id'], row['condition']]
            assert plan['configuration']['max_output_tokens'] == 8192
            calls.append(prompt)
            if len(calls) == 1:
                raise TimeoutError('Private diagnostic must not appear in receipt')
            if len(calls) == 2:
                return {'candidates': [{'finish_reason': 'MAX_TOKENS'}]}
            value = {'decision': 'reply', 'text': ''} if len(calls) == 3 else {
                'decision': 'no-reply', 'text': ''}
            return {'candidates': [{'finish_reason': 'STOP', 'content': {'parts': [
                {'text': 'hidden thought', 'thought': True}, {'text': json.dumps(value)}]}}]}

        result = run.execute(prepared, pins['plan_sha256'], pins['prompts_sha256'], fake, progress=False)
        assert len(calls) == result['scheduled'] == 100
        assert (result['complete'], result['errors']) == (97, 3)
        _, records = run.read_receipts(prepared)
        assert records[0]['error_type'] == 'TimeoutError'
        assert 'Private diagnostic' not in (prepared / 'execution/receipts/001.json').read_text()
        assert 'raw_file' not in records[0] and 'raw_file' in records[1]
        try:
            run.execute(prepared, pins['plan_sha256'], pins['prompts_sha256'], fake, progress=False)
        except FileExistsError:
            pass
        else:
            raise AssertionError('Batch was resent')
        assert len(calls) == 100
        receipt = prepared / 'execution/receipts/100.json'
        receipt.write_text(receipt.read_text().replace('no-reply', 'reply'))
        try:
            run.read_receipts(prepared)
        except ValueError:
            pass
        else:
            raise AssertionError('Modified receipt accepted')
    print('Authored dispatch checks passed; no provider calls.')


if __name__ == '__main__':
    main()
