"""Prepare one blind account-held-out test; never fit on or score new targets here."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys

from src.eval import work_presence_review

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/context-work-holdout-v1'
RECOVERY = ROOT / 'data/learner-linkage-recovery-v1'
EXPOSURE = ROOT / 'data/context-work-holdout-v1-exposure.json'
SEED = 'context-work-holdout-v1-20261001'
META_SQL = ROOT / 'data/course-account-checkpoints-v1/checkpoints.sql'
TEXT_SQL = ROOT / 'experiments/2026-10-01-cross-notebook-content.sql'
INGEST = ROOT.parent / 'episode-pilot/data/episode-pilot/notebook-context-v1/ingestion_probe.py'
spec = importlib.util.spec_from_file_location('context_probe', ROOT / 'experiments/2026-10-01-context-work-probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
cal = probe.calibration
helpers = cal.module(ROOT / 'experiments/2026-10-01-cross-notebook-select.py')
read, digest, save = cal.read, cal.digest, helpers.save


def rank(kind, value):
    return sha256(f'{SEED}:{kind}:{value}'.encode()).hexdigest()


def stamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp must include a timezone.')
    return result


def choose(rows, excluded, count=24):
    rows = [r for r in rows if len(r['account_ids']) == 1 and r['account_ids'][0] not in excluded]
    accounts = sorted({r['account_ids'][0] for r in rows}, key=lambda a: (rank('account', a), a))
    if len(accounts) < count:
        raise ValueError('Insufficient unexposed accounts; do not weaken exclusions.')
    result = []
    for i, account in enumerate(accounts[:count], 1):
        row = min((r for r in rows if r['account_ids'] == [account]),
                  key=lambda r: (rank('conversation', r['conv_id']), r['conv_id']))
        result.append({'id': f'holdout-{i:02}', 'account_id': account, 'conv_id': row['conv_id'],
                       'expected_checkpoints': row['eligible_checkpoints']})
    return result


def model():
    probe.run(ROOT / 'data/context-work-probe-v1', verify=True)
    old = read(ROOT / 'data/context-work-probe-v1/inputs.json')
    estimates = {str(cue): probe.forecast(old['observations'], old['features'], cue) for cue in (True, False, None)}
    if [estimates[str(c)]['fraction'] for c in (True, False, None)] != ['11/15', '3/35', '1/5']:
        raise ValueError('Frozen training rule changed.')
    paths = [Path(__file__), Path(probe.__file__), Path(helpers.__file__),
             ROOT / 'docs/2026-10-01-context-work-holdout.md',
             ROOT / 'data/context-work-probe-v1/inputs.json', ROOT / 'data/context-work-probe-v1/report.json']
    return {'estimates': estimates, 'baseline': {'frequency': .2, 'constant_half': .5, 'always_no': 0.},
            'training_accounts': sorted({r['account_id'] for r in old['observations']}),
            'source_sha256': helpers.pins(paths)}


def select():
    if OUT.exists():
        raise FileExistsError('Preserve the original selection.')
    fitted = model()
    exposure = read(EXPOSURE)
    if exposure.get('selection_ready') is not True:
        raise ValueError('Exposure inventory has unresolved selection blockers.')
    helpers.checked_pins(exposure['source_sha256'])
    old = read(ROOT / 'data/course-account-checkpoints-v1/selection.json')
    helpers.checked_pins(old['source_sha256'])
    pool = read(RECOVERY / 'candidate-accounts.json')['conversations']
    excluded = set(exposure['excluded_account_ids']) | set(fitted['training_accounts'])
    cases = choose(pool, excluded)
    params = read(RECOVERY / 'linkage-params.json')
    paths = [EXPOSURE, RECOVERY / 'candidate-accounts.json', RECOVERY / 'linkage.json',
             RECOVERY / 'linkage-params.json', META_SQL, TEXT_SQL, INGEST]
    selection = {'seed': SEED, 'cases': cases, 'excluded_accounts': sorted(excluded),
        'window': {k: params[k] for k in ('start_at', 'end_at', 'until')},
        'source_sha256': helpers.pins(paths), 'model_sha256': sha256(cal.encoded(fitted).encode()).hexdigest()}
    OUT.mkdir()
    save(OUT / 'model.json', fitted)
    save(OUT / 'selection.json', selection)
    save(OUT / 'checkpoints-params.json', {k: params[k] for k in ('start_at', 'end_at', 'until', 'salt')} |
         {'conversation_ids': json.dumps([c['conv_id'] for c in cases])})
    return {'selected_accounts': len(cases), 'text_retrieved': False}


def checked_selection():
    selection, fitted = read(OUT / 'selection.json'), read(OUT / 'model.json')
    helpers.checked_pins(selection['source_sha256'])
    if fitted != model() or sha256(cal.encoded(fitted).encode()).hexdigest() != selection['model_sha256']:
        raise ValueError('Frozen training model changed.')
    exposure = read(EXPOSURE)
    if selection['cases'] != choose(read(RECOVERY / 'candidate-accounts.json')['conversations'], set(selection['excluded_accounts'])):
        raise ValueError('Selected account sample changed.')
    if set(selection['excluded_accounts']) != set(exposure['excluded_account_ids']) | set(fitted['training_accounts']):
        raise ValueError('Whole-account exclusions changed.')
    return selection, fitted


def expected_params(stem):
    original = read(RECOVERY / 'linkage-params.json')
    if stem == 'checkpoints':
        selection, _ = checked_selection()
        return {k: original[k] for k in ('start_at', 'end_at', 'until', 'salt')} | {
            'conversation_ids': json.dumps([c['conv_id'] for c in selection['cases']])}
    frozen = boundaries()
    if read(OUT / 'boundaries.json') != frozen:
        raise ValueError('Saved checkpoint boundaries changed.')
    if stem == 'prefix':
        ids = sorted(i for c in frozen['cases'] for i in c['prefix_event_ids'])
    elif stem == 'targets':
        ids = sorted(c['target_event_id'] for c in frozen['cases'])
    else:
        raise ValueError('Unknown export stage.')
    return {k: original[k] for k in ('salt', 'until')} | {'event_ids': json.dumps(ids)}


def check_params(stem):
    if read(OUT / (stem + '-params.json')) != expected_params(stem):
        raise ValueError('Query parameters differ from the frozen selection/window.')


def receipt(stem, sql):
    check_params(stem)
    value = read(OUT / (stem + '.json'))
    if value['read_only'] is not True or any(value[k] != digest(p) for k, p in (
        ('query_sha256', sql), ('params_sha256', OUT / (stem + '-params.json')), ('probe_sha256', INGEST))):
        raise ValueError('Export must bind to the exact read-only query and parameters.')
    return value['rows']


def fetch(stem):
    """Validate, record launch, then invoke the existing read-only ingestion probe once."""
    check_params(stem)
    if (OUT / (stem + '.json')).exists():
        raise FileExistsError('Do not repeat a completed export.')
    sql = META_SQL if stem == 'checkpoints' else TEXT_SQL
    launch = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'query_sha256': digest(sql), 'params_sha256': digest(OUT / (stem + '-params.json'))}
    if stem == 'targets':
        saved = read(OUT / 'predictions.json')
        if {k: v for k, v in saved.items() if k != 'sealed_at_utc'} != predictions():
            raise ValueError('Predictions must be sealed before target retrieval.')
        launch['predictions_sha256'] = digest(OUT / 'predictions.json')
    save(OUT / (stem + '-dispatch.json'), launch)
    from dotenv import load_dotenv
    from sqlalchemy.engine import make_url
    from src.config import Settings
    load_dotenv(ROOT.parent / 'main/.env')
    url = make_url(Settings.load().ext_db_url).set(host='127.0.0.1', port=15432)
    os.environ['EXT_DB_URL'] = url.render_as_string(hide_password=False)
    sys.argv = [str(INGEST), str(sql), str(OUT / (stem + '-params.json')), str(OUT / (stem + '.json'))]
    runpy.run_path(str(INGEST), run_name='__main__')
    return {'export': stem, 'read_only': True}


def boundaries():
    selection, _ = checked_selection()
    rows = receipt('checkpoints', META_SQL)
    if {r['conv_id'] for r in rows} != {c['conv_id'] for c in selection['cases']}:
        raise ValueError('Missing or extra conversation; do not replace it.')
    cases = []
    for chosen in selection['cases']:
        candidates = [r for r in rows if r['conv_id'] == chosen['conv_id']]
        if len(candidates) != chosen['expected_checkpoints'] or len({r['target_event_id'] for r in candidates}) != len(candidates):
            raise ValueError('Checkpoint availability changed.')
        if any(r['account_ids'] != [chosen['account_id']] or r['missing_identity_events'] for r in candidates):
            raise ValueError('Account linkage changed.')
        boundary = min(candidates, key=lambda r: (rank('checkpoint', f"{r['conv_id']}:{r['target_event_id']}"), r['target_event_id']))
        ids = boundary['prefix_event_ids'] + [boundary['target_event_id']]
        if (ids != sorted(set(ids)) or boundary['prefix_event_ids'][-1] != boundary['tutor_event_id']
                or boundary['prior_queries'] < 2 or not stamp(selection['window']['start_at']) <= stamp(boundary['target_at']) < stamp(selection['window']['end_at'])):
            raise ValueError('Invalid selected checkpoint; do not rerank.')
        cases.append(chosen | {k: boundary[k] for k in ('prefix_event_ids', 'target_event_id', 'tutor_event_id', 'prior_queries', 'target_at')})
    return {'cases': cases, 'source_sha256': helpers.pins([OUT / n for n in ('selection.json', 'checkpoints.json', 'checkpoints-params.json')])}


def freeze():
    value = boundaries()
    params = read(RECOVERY / 'linkage-params.json')
    save(OUT / 'boundaries.json', value)
    save(OUT / 'prefix-params.json', {k: params[k] for k in ('salt', 'until')} |
         {'event_ids': json.dumps(sorted(i for c in value['cases'] for i in c['prefix_event_ids']))})
    return {'frozen_cases': len(value['cases']), 'target_content_retrieved': False}


def prefix(case, rows):
    rows = sorted(rows, key=lambda r: r['id'])
    if [r['id'] for r in rows] != case['prefix_event_ids'] or any(
            r['conv_id'] != case['conv_id'] or r['account_id'] != case['account_id']
            or r['event_type'] not in ('tutor_query', 'tutor_response') or not isinstance(r['text'], str) or r['text'] == '' for r in rows):
        raise ValueError('Prefix identity, membership or text changed.')
    times = [stamp(r['created_at']) for r in rows] + [stamp(case['target_at'])]
    if (times != sorted(times) or rows[-1]['id'] != case['tutor_event_id'] or rows[-1]['event_type'] != 'tutor_response'
            or sum(r['event_type'] == 'tutor_query' for r in rows) != case['prior_queries']):
        raise ValueError('Prefix boundary or temporal order changed; no repair/truncation.')
    return [{'role': 'student' if r['event_type'] == 'tutor_query' else 'tutor', 'text': r['text']} for r in rows]


def predictions():
    frozen = boundaries()
    if read(OUT / 'boundaries.json') != frozen:
        raise ValueError('Saved checkpoint boundaries changed.')
    rows = receipt('prefix', TEXT_SQL)
    expected = sorted(i for c in frozen['cases'] for i in c['prefix_event_ids'])
    if sorted(r['id'] for r in rows) != expected:
        raise ValueError('Prefix export contains missing, duplicate or future events.')
    fitted = read(OUT / 'model.json')
    cases = []
    for case in frozen['cases']:
        context = prefix(case, [r for r in rows if r['conv_id'] == case['conv_id']])
        cue = probe.feature(context)
        cases.append(case | {'prefix': context, 'cue': cue, 'p': fitted['estimates'][str(cue)]['p'],
                             'baselines': fitted['baseline'], 'prefix_sha256': probe.value_digest(context)})
    return {'cases': cases, 'source_sha256': helpers.pins([OUT / n for n in ('model.json', 'boundaries.json', 'prefix.json', 'prefix-params.json')])}


def seal():
    if (OUT / 'targets.json').exists() or (OUT / 'targets-params.json').exists():
        raise ValueError('Targets must not be retrieved before forecasts are sealed.')
    result = predictions()
    save(OUT / 'predictions.json', result | {'sealed_at_utc': datetime.now(timezone.utc).isoformat()})
    params = read(RECOVERY / 'linkage-params.json')
    save(OUT / 'targets-params.json', {k: params[k] for k in ('salt', 'until')} |
         {'event_ids': json.dumps(sorted(c['target_event_id'] for c in result['cases']))})
    return {'sealed_predictions': len(result['cases']), 'targets_retrieved': False}


def packet():
    saved = read(OUT / 'predictions.json')
    if {k: v for k, v in saved.items() if k != 'sealed_at_utc'} != predictions():
        raise ValueError('Saved forecasts or their inputs changed.')
    raw = read(OUT / 'targets.json')
    launch = read(OUT / 'targets-dispatch.json')
    if (not stamp(saved['sealed_at_utc']) < stamp(launch['started_at_utc']) <= stamp(raw['queried_at_utc'])
            or launch['predictions_sha256'] != digest(OUT / 'predictions.json')
            or launch['query_sha256'] != digest(TEXT_SQL)
            or launch['params_sha256'] != digest(OUT / 'targets-params.json')):
        raise ValueError('Targets were fetched before forecasts were sealed.')
    rows = receipt('targets', TEXT_SQL)
    if sorted(r['id'] for r in rows) != sorted(c['target_event_id'] for c in saved['cases']):
        raise ValueError('Recorded targets do not match the fixed selection.')
    cases = []
    for c in sorted(saved['cases'], key=lambda c: rank('review', c['id'])):
        r = next(r for r in rows if r['id'] == c['target_event_id'])
        if (r['account_id'] != c['account_id'] or r['conv_id'] != c['conv_id'] or r['event_type'] != 'tutor_query'
                or stamp(r['created_at']) != stamp(c['target_at']) or not isinstance(r['text'], str) or not r['text']):
            raise ValueError('Recorded target identity or content is unavailable.')
        cases.append({'id': c['id'], 'context_status': 'Complete available conversation before the next recorded message.',
            'prefix': {'context': [], 'turns': [t | {'id': f"{c['id']}-turn-{i}"} for i, t in enumerate(c['prefix'], 1)]},
            'candidates': [{'id': c['id'] + '-message', 'text': r['text']}]})
    # Reuse the exact original human rubric; no predictor-derived outcome definition.
    source = cal.BASE / 'help-work-benchmark-v1/review-packet.json'
    definitions = read(source)['definitions']
    body = {'rubric_id': 'help-work-v1', 'definitions': definitions, 'cases': cases}
    result = {'packet_id': 'packet_' + probe.value_digest(body), **body}
    save(OUT / 'review-packet.json', result)
    work_presence_review.build(OUT / 'review-packet.json', OUT / 'review.html')
    save(OUT / 'preparation.json', {'status': 'awaiting-blind-human-review', 'cases': 24,
        'predictions_before_targets': True, 'provider_calls': 0,
        'source_sha256': helpers.pins([source, Path(work_presence_review.__file__), Path(work_presence_review.__file__).with_suffix('.html'),
            *[OUT / n for n in ('predictions.json', 'targets.json', 'targets-params.json', 'targets-dispatch.json', 'review-packet.json', 'review.html')]])})
    return {'review_cases': 24, 'status': 'awaiting-blind-human-review'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('select', 'freeze', 'seal', 'packet', 'fetch-checkpoints', 'fetch-prefix', 'fetch-targets'))
    args = parser.parse_args()
    result = fetch(args.stage.removeprefix('fetch-')) if args.stage.startswith('fetch-') else globals()[args.stage]()
    print(json.dumps({'stage': args.stage, **result}, indent=2))
