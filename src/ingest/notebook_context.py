"""Recover dated context from saved ingestion rows, without modifying old snapshots."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json

from src.labeling.episodes import _hash
from src.labeling import tutor_moves


def _at(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('Evidence timestamps need a timezone.')
    return result


def recover_initial(capture: dict, queries: list[dict], responses: list[dict]) -> dict:
    """Bind one initial capture to query/window and response metadata from the probe.

    Query hashes identify equal text, not identity. The SQL window's subject join,
    conversation checks and unambiguous event pairing establish attribution.
    Callers must retain the input receipts and their source hashes.
    """
    cid = capture['conv_id']
    captured_at = _at(capture['created_at'])
    fingerprint = lambda text: hashlib.md5(text.encode()).hexdigest()
    matching = [r for r in queries if r['event_type'] == 'tutor_query'
                and r['case_conv_id'] == cid and r['event_conv_id'] in (None, cid)
                and r['question_md5'] == fingerprint(capture['student_message'])
                and r['id'] < capture['id'] and _at(r['created_at']) < captured_at]
    if len(matching) != 1:
        raise ValueError('Initial query is missing or ambiguous.')
    query = matching[0]
    matching = [r for r in responses if r['event_type'] == 'tutor_response'
                and r['conv_id'] == cid
                and r['response_md5'] == fingerprint(capture['tutor_response'])
                and r['id'] > query['id'] and _at(r['created_at']) > _at(query['created_at'])
                and abs((_at(r['created_at']) - captured_at).total_seconds()) < 10]
    if len(matching) != 1:
        raise ValueError('Initial response is missing or ambiguous.')
    response = matching[0]
    notebook = json.loads(capture['initial_notebook_json'])
    if not isinstance(notebook, dict) or not isinstance(notebook.get('cells'), list):
        raise ValueError('Expected a captured notebook with cells.')
    cells = []
    for index, cell in enumerate(notebook['cells']):
        if not isinstance(cell, dict) or cell.get('cell_type') not in ('code', 'markdown', 'raw'):
            raise ValueError('Invalid notebook cell.')
        source = cell.get('source')
        if isinstance(source, list) and all(isinstance(line, str) for line in source):
            source = ''.join(source)
        if not isinstance(source, str):
            raise ValueError('Cell source must be text or a list of text lines.')
        cells.append({'index':index, 'cell_type':cell['cell_type'], 'source':source})
    return {'conversation_key':_hash(cid)[:16],
            'capture_event_id':capture['id'], 'capture_sha256':_hash(capture),
            'exchange':[
                {'id':f'event-{query["id"]}', 'role':'student',
                 'text':capture['student_message'], 'at':query['created_at']},
                {'id':f'event-{response["id"]}', 'role':'tutor',
                 'text':capture['tutor_response'], 'at':response['created_at']}],
            'notebook':{'recorded_at':capture['created_at'], 'cells':cells,
                        'basis':'initial capture; not a later work state',
                        'outputs':'omitted, not evidence of no execution'}}


def context_for(episode: dict, recovered: dict) -> dict:
    """Project a later review prefix with historical work, never its reference future."""
    if episode['conversation_key'] != recovered['conversation_key']:
        raise ValueError('Recovered context belongs to another conversation.')
    visible = tutor_moves._source_turns(episode)
    current_responses = [t for t in episode['turns'] if (t['role'], t['phase']) == ('tutor','response')]
    if len(current_responses) != 1:
        raise ValueError('Choose a single response cutoff.')
    cutoff = _at(current_responses[0]['at'])
    if _at(recovered['notebook']['recorded_at']) > cutoff:
        raise ValueError('Notebook capture is after the prediction cutoff.')
    if any(_at(t['at']) > cutoff for t in visible + recovered['exchange']):
        raise ValueError('Visible context contains a future turn.')
    augmented = deepcopy(episode)
    missing = []
    for turn in recovered['exchange']:
        same_id = [t for t in visible if t['id'] == turn['id']]
        exact = [t for t in visible if (t['role'], t['text'], _at(t['at'])) ==
                 (turn['role'], turn['text'], _at(turn['at']))]
        if any(t not in exact for t in same_id):
            raise ValueError('Recovered event conflicts with an existing turn ID.')
        if not exact:
            if visible and _at(turn['at']) >= min(_at(t['at']) for t in visible):
                raise ValueError('Recovered exchange is not earlier context.')
            missing.append(deepcopy(turn))
    augmented['context'] = missing + augmented.get('context', [])
    dialogue = json.loads(tutor_moves.make_prompt(augmented, 'v5').split('\nEPISODE JSON:\n', 1)[1])
    return {'prediction_cutoff':current_responses[0]['at'], 'dialogue':dialogue,
            'initial_notebook':deepcopy(recovered['notebook']),
            'current_work':None, 'current_observation':None,
            'work_status':'unknown at this cutoff; do not apply edits to the historical capture'}
