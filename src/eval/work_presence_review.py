"""Build a portable work-presence-only review for the fixed 24-case test."""
import argparse
import json
from pathlib import Path

from src.eval.communication_review import validate_packet


def build(packet: Path, output: Path) -> Path:
    packet, output = Path(packet), Path(output)
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    data = json.loads(packet.read_text(encoding='utf-8'))
    validate_packet(data)
    if len(data['cases']) != 24 or any(len(case['candidates']) != 1 for case in data['cases']):
        raise ValueError('Expected exactly 24 cases with one message each.')
    template = Path(__file__).with_suffix('.html').read_text(encoding='utf-8')
    if template.count('__REVIEW_PAYLOAD__') != 1:
        raise ValueError('Expected one review payload placeholder.')
    # HTML parsers recognize </script> even inside application/json.
    encoded = json.dumps(data, ensure_ascii=True).replace('<', '\\u003c')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as target:
        target.write(template.replace('__REVIEW_PAYLOAD__', encoded))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(build(args.packet, args.output))


if __name__ == '__main__':
    main()
