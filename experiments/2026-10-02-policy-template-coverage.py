"""Compare existing recorded labels to templates; no recoding, sampling or dispatch."""
import argparse
from collections import Counter
from html import escape
import importlib.util
import json
from pathlib import Path
from textwrap import indent

from src.agents import behavior_policy as policy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/policy-template-coverage-v1'
FIELDS = ('assistance', 'material', 'task_relation')
CODERS = ('coder-a', 'coder-b')
STATUSES = ('template-present', 'template-missing', 'unresolved-labels')


def classify(judgments):
    values = {field: judgments[field]['value'] for field in FIELDS}
    values = {field: sorted(value) if isinstance(value, list) else value for field, value in values.items()}
    unknown = [field for field, value in values.items() if value is None or value == 'unclear']
    result = {'behavior': values, 'unknown_fields': unknown, 'template': None}
    if unknown:
        return result | {'status': 'unresolved-labels'}
    template = policy.TEMPLATES.get(policy._key(policy.Behavior.model_validate(values)))
    if template is None:
        return result | {'status': 'template-missing'}
    name, slots, pattern = template
    return result | {'status': 'template-present', 'template': {
        'id': name, 'required_inputs': list(slots), 'authored_pattern': pattern}}


def compare(rows):
    compared = []
    for row in rows:
        coders = {name: classify(row['judgments'][name]) for name in CODERS}
        compared.append({'case_alias': row['case_alias'], 'coders': coders,
            'labels_agree': coders['coder-a']['behavior'] == coders['coder-b']['behavior']})
    counts = {name: Counter(row['coders'][name]['status'] for row in compared) for name in CODERS}
    agreed = [row for row in compared if row['labels_agree']
              and not row['coders']['coder-a']['unknown_fields']]
    return {'rows': compared, 'by_coder': {
        name: {status: counts[name][status] for status in STATUSES} for name in CODERS},
        'agreed_resolved': {'messages': len(agreed), **{
            status: sum(row['coders']['coder-a']['status'] == status for row in agreed)
            for status in STATUSES[:2]}}}


def collect():
    path = ROOT / 'experiments/2026-10-02-policy-evidence-audit.py'
    spec = importlib.util.spec_from_file_location(path.stem, path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    saved = audit.read(audit.OUT)
    audit.pins_checked(saved['source_sha256'])
    audit.require(audit.collect() == saved, 'The preceding evidence audit does not reproduce.')
    result = compare(saved['assistant_rows'])
    mapping_path = ROOT / 'data/behavior-pilot-v1/mapping.json'
    mapping = {row['id']: row for row in audit.read(mapping_path) if row['origin'] == 'recorded'}
    sources = {row['case_alias']: row for row in saved['assistant_rows']}
    for row in result['rows']:
        source = sources[row['case_alias']]
        item = mapping[source['id']]
        audit.require(item['case'] == row['case_alias'], 'A recorded example changed identity.')
        row['source'] = {'audit_id': source['id'], 'event_id': source['event_id'],
                         'origin': 'recorded', 'label_origin': 'assistant', **item['data']}
    result['templates'] = [{'id': name, 'behavior': dict(zip(FIELDS, (list(key[0]), list(key[1]), key[2]))),
        'required_inputs': list(slots), 'authored_pattern': pattern,
        'recorded_cases': {coder: [row['case_alias'] for row in result['rows']
            if row['coders'][coder]['template'] is not None
            and row['coders'][coder]['template']['id'] == name] for coder in CODERS}}
        for key, (name, slots, pattern) in policy.TEMPLATES.items()]
    result['coarse_references'] = {'status': 'rubric-not-comparable', 'messages': len(saved['human_rows']),
        'reason': 'Human help/work labels do not determine assistance/material/task bundles.'}
    paths = (Path(__file__), Path(policy.__file__), audit.OUT, mapping_path,
             ROOT / 'src/agents/behavior_expression.py', ROOT / 'docs/2026-10-02-policy-template-coverage.md')
    pins = saved['source_sha256'] | {str(path.resolve()): audit.digest(path) for path in paths}
    audit.pins_checked(pins)
    return {'version': 1, 'result': result, 'source_sha256': pins,
        'limits': ['Template availability is not behavioral fidelity, semantic wording accuracy or policy admission.',
            'Both original assistant judgments are retained; no consensus or new labels were created.',
            'Preceding assistance and revision-bound execution feedback remain unknown.',
            'Required literal inputs are listed, not inferred from the recorded future.',
            'No sampling, probability change, model call, database query or new holdout target read.']}


def literal(text):
    """Keep private source text literal in Markdown, including any embedded markup."""
    return indent(text, '    ')


def bundle(values):
    def label(value):
        if value is None or value == 'unclear':
            return 'unknown'
        return ', '.join(value) or 'none' if isinstance(value, list) else value
    return ' / '.join(label(values[field]) for field in FIELDS)


def markdown(saved):
    result = saved['result']
    lines = ['# Recorded behavior and template coverage', '',
        'Existing assistant labels on ten recorded development messages. No new labels or model calls.', '',
        '**A matching template only establishes implementation coverage. These references did not determine '
        'the authored policy’s probabilities.**', '',
        '| Original coder | Template exists | Missing template | Unresolved labels |',
        '| --- | ---: | ---: | ---: |']
    for name, counts in result['by_coder'].items():
        lines.append(f"| {name} | " + ' | '.join(str(counts[key]) for key in STATUSES) + ' |')
    agreed = result['agreed_resolved']
    lines += ['', f"Of {agreed['messages']} complete, agreed label bundles: "
        f"{agreed['template-present']} have templates and {agreed['template-missing']} do not.", '',
        'The 16 human-reviewed help/work references are not comparable to these finer bundles. '
        'A missing template never means student silence.', '', '## Existing templates', '',
        '| Template | Assistance / material / task | Required literal inputs | Recorded cases (A / B) |',
        '| --- | --- | --- | --- |']
    for template in result['templates']:
        cases = [' '.join(map(str, template['recorded_cases'][name])) or 'none in this set' for name in CODERS]
        lines.append(f"| {template['id']} | {bundle(template['behavior'])} | "
                     f"{', '.join(template['required_inputs']) or 'none'} | {' / '.join(cases)} |")
    lines += ['', '## Recorded examples', '',
        'Matching context is unknown for all ten: preceding requested assistance has not been coded, '
        'and revision-bound execution feedback is unavailable. Required literal inputs were not extracted '
        'from the recorded target. Even templates without slots have unvalidated wording suitability.', '']
    for row in result['rows']:
        source = row['source']
        lines += [f"### Case {row['case_alias']}", '', 'Recorded message:', '', literal(source['message']), '',
            '| Coder | Assistance / material / task | Coverage |', '| --- | --- | --- |']
        for name, checked in row['coders'].items():
            lines.append(f"| {name} | {bundle(checked['behavior'])} | {checked['status']} |")
        templates = {checked['template']['id']: checked['template'] for checked in row['coders'].values()
                     if checked['template'] is not None}
        for template in templates.values():
            lines += ['', f"Matching authored pattern ({template['id']}; unfilled):", '',
                literal(template['authored_pattern']), '',
                'Required literal inputs: ' + (', '.join(template['required_inputs']) or 'none') + '.']
        context = (f"Original audit item: {source['audit_id']}; database event: {source['event_id']}.\n\n"
                   + '\n\n'.join(turn['role'].capitalize() + ':\n' + turn['text'] for turn in source['prefix']))
        lines += ['', '<details><summary>Recorded preceding context and source</summary>',
                  '<pre>' + escape(context) + '</pre></details>', '']
    lines += ['## Limits', '', *('- ' + limit for limit in saved['limits']), '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'verify'))
    args = parser.parse_args()
    if args.command == 'run' and OUT.exists():
        raise FileExistsError('Keep the saved comparison; use verify.')
    saved = collect()
    documents = {'coverage.json': json.dumps(saved, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
                 'report.md': markdown(saved)}
    if args.command == 'run':
        OUT.mkdir(parents=True, exist_ok=False)
        for name, text in documents.items():
            with (OUT / name).open('x', encoding='utf-8') as stream:
                stream.write(text)
    else:
        for name, text in documents.items():
            if (OUT / name).read_text(encoding='utf-8') != text:
                raise ValueError('The saved comparison, source pins or readable report changed.')
    print(json.dumps({'status': args.command, 'by_coder': saved['result']['by_coder'],
                     'agreed_resolved': saved['result']['agreed_resolved']}))


if __name__ == '__main__':
    main()
