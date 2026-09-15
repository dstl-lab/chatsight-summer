"""Build two independent, portable review pages from a frozen coding packet."""
import argparse
from hashlib import sha256
import json
from pathlib import Path


OPTIONS = {'revised-code', 'submitted-code', 'submitted-work', 'asked-for-help',
           'acknowledgment', 'other', 'insufficient-evidence'}


def _turn(turn):
    if (not isinstance(turn, dict) or turn.get('role') not in ('student', 'tutor')
            or not isinstance(turn.get('id'), str) or not turn['id']
            or not isinstance(turn.get('lines'), list)):
        raise ValueError('Every source turn needs an ID, student/tutor role and numbered lines.')
    text = []
    for row in turn['lines']:
        if (not isinstance(row, dict) or type(row.get('line')) is not int
                or row['line'] <= len(text) or not isinstance(row.get('text'), str)):
            raise ValueError('Source line numbers must be positive and strictly increasing.')
        text.extend([''] * (row['line'] - len(text)))
        text[-1] = row['text']
    return {key: turn[key] for key in ('id', 'role')} | {'text': '\n'.join(text)}


def build(packet_dir: Path, output_dir: Path) -> Path:
    packet_dir, output_dir = Path(packet_dir), Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f'Output already exists: {output_dir}')
    manifest_raw = (packet_dir / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    if (not isinstance(manifest, dict) or type(manifest.get('cases')) is not int
            or manifest['cases'] != 8 or not isinstance(manifest.get('options'), dict)
            or set(manifest['options']) != OPTIONS
            or any(not isinstance(v, str) or not v.strip() for v in manifest['options'].values())
            or not isinstance(manifest.get('artifacts'), dict)):
        raise ValueError('Expected the fixed eight-case packet and its seven action definitions.')

    files = {}
    for name in ('source-records.json', 'reviewer-1.json', 'reviewer-2.json'):
        files[name] = (packet_dir / name).read_bytes()
        if sha256(files[name]).hexdigest() != manifest['artifacts'].get(name):
            raise ValueError(f'Source hash does not match the frozen packet: {name}')
    records = json.loads(files['source-records.json'])
    if (not isinstance(records, list) or len(records) != 8
            or any(not isinstance(row, dict) or type(row.get('case')) is not int
                   or row['case'] != n for n, row in enumerate(records, 1))):
        raise ValueError('Source cases must be numbered 1 through 8 in order.')
    cases = []
    for row in records:
        prefix = row.get('prefix')
        if (not isinstance(prefix, dict) or not isinstance(prefix.get('context_status'), str)
                or not isinstance(prefix.get('context'), list)
                or not isinstance(prefix.get('turns'), list)
                or not isinstance(row.get('recorded_message'), str)):
            raise ValueError('Each case needs its frozen context and recorded message.')
        cases.append({'case': row['case'], 'context_status': prefix['context_status'],
                      'context': [_turn(t) for t in prefix['context']],
                      'turns': [_turn(t) for t in prefix['turns']],
                      'recorded_message': row['recorded_message']})
    blank = {'reviewer': None, 'previously_seen_these_cases_or_labels': None,
             'cases': [{'case': n, 'followup': None, 'note': None} for n in range(1, 9)]}
    template = Path(__file__).with_suffix('.html').read_text(encoding='utf-8')
    if template.count('__REVIEW_PAYLOAD__') != 1:
        raise ValueError('Review template needs exactly one payload placeholder.')
    packet_id = sha256(files['source-records.json'] + manifest_raw).hexdigest()
    pages = {}
    for reviewer in ('reviewer-1', 'reviewer-2'):
        form = json.loads(files[f'{reviewer}.json'])
        if form != blank or any(type(row['case']) is not int for row in form['cases']):
            raise ValueError('Reviewer source forms must remain completely blank.')
        payload = {'packet_id': packet_id, 'reviewer_id': reviewer,
                   'options': manifest['options'], 'cases': cases, 'form': form}
        # Escape '<' even in application/json: HTML parsers still recognize </script>.
        encoded = json.dumps(payload, ensure_ascii=True).replace('<', '\\u003c')
        pages[f'{reviewer}.html'] = template.replace('__REVIEW_PAYLOAD__', encoded)
    pages['index.html'] = '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Student message review</title>
<style>html{background:#f5f8fa;color:#18384d}body{font:17px/1.6 "Avenir Next","Segoe UI",sans-serif;max-width:760px;margin:4rem auto;padding:0 1.5rem}h1{letter-spacing:-.7px;line-height:1.2}ul{padding:0;list-style:none}li{margin:1rem 0;padding:24px;background:white;border:1px solid #c7d5dd;border-radius:8px}a{color:#006c70;text-underline-offset:4px;display:inline-block;padding:6px 0;min-height:44px}li a:first-child{font-weight:650;margin-right:16px}:focus-visible{outline:3px solid #087bba;outline-offset:4px}</style>
<h1>Student message review</h1>
<p>Give each reviewer only their assigned file. They can open it in a browser, work independently, and copy or download their answers to return.</p>
<ul><li><a href="reviewer-1.html">Open Reviewer 1</a> · <a href="reviewer-1.html" download>Download Reviewer 1 page</a></li>
<li><a href="reviewer-2.html">Open Reviewer 2</a> · <a href="reviewer-2.html" download>Download Reviewer 2 page</a></li></ul>
<p>Both reviewers see the same eight messages. Finish separately before discussing the cases.</p>
</html>'''
    # Validate and render everything before reserving the create-only output directory.
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, html in pages.items():
        with (output_dir / name).open('x', encoding='utf-8') as target:
            target.write(html)
    return output_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(build(args.packet, args.output or args.packet / 'ui'))


if __name__ == '__main__':
    main()
