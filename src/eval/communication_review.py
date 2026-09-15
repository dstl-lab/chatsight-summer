"""Build one portable blind communication review from an already blinded packet."""
import argparse
import json
from pathlib import Path


def _keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        raise ValueError(f'Expected exactly these fields: {keys}')


def _text(value, *, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError('Expected text' + ('.' if empty else ' that is not blank.'))


def validate_packet(data):
    _keys(data, 'packet_id rubric_id definitions cases')
    _text(data['packet_id'])
    if data['rubric_id'] != 'help-work-v1':
        raise ValueError('Expected the help-work-v1 rubric.')
    _keys(data['definitions'], 'help_request work_present')
    for definition in data['definitions'].values():
        _text(definition)
    if not isinstance(data['cases'], list) or not data['cases']:
        raise ValueError('Expected at least one case.')
    seen = {'case': set(), 'turn': set(), 'candidate': set()}

    def identity(value, kind):
        _text(value)
        if value in seen[kind]:
            raise ValueError(f'Duplicate {kind} ID: {value}')
        seen[kind].add(value)

    for case in data['cases']:
        _keys(case, 'id context_status prefix candidates')
        identity(case['id'], 'case')
        _text(case['context_status'])
        _keys(case['prefix'], 'context turns')
        for turns in case['prefix'].values():
            if not isinstance(turns, list):
                raise ValueError('Prefix context and turns must be lists.')
            for turn in turns:
                _keys(turn, 'id role text')
                identity(turn['id'], 'turn')
                if turn['role'] not in ('student', 'tutor'):
                    raise ValueError('Turn roles must be student or tutor.')
                _text(turn['text'], empty=True)
        if not isinstance(case['candidates'], list) or not 1 <= len(case['candidates']) <= 9:
            raise ValueError('Each case must have one to nine candidates.')
        for candidate in case['candidates']:
            _keys(candidate, 'id text')
            identity(candidate['id'], 'candidate')
            _text(candidate['text'], empty=True)


def build(packet: Path, output: Path) -> Path:
    packet, output = Path(packet), Path(output)
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    data = json.loads(packet.read_text(encoding='utf-8'))
    validate_packet(data)
    template = Path(__file__).with_suffix('.html').read_text(encoding='utf-8')
    if template.count('__REVIEW_PAYLOAD__') != 1:
        raise ValueError('Expected one review payload placeholder.')
    # HTML parsers recognize </script> even inside application/json.
    encoded = json.dumps(data, ensure_ascii=True).replace('<', '\\u003c')
    html = template.replace('__REVIEW_PAYLOAD__', encoded)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as target:
        target.write(html)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(build(args.packet, args.output))


if __name__ == '__main__':
    main()
