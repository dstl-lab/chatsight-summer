"""Work-only review must preserve blind text and never invent a help label."""
from copy import deepcopy
import importlib.util
import json
import re
import shutil
import subprocess

import pytest


def test_work_only_packet_and_browser_draft(tmp_path):
    assert importlib.util.find_spec('src.eval.work_presence_review'), 'Work-only builder is missing'
    from src.eval.work_presence_review import build

    attack = '</script><script>alert("invented")</script>\n  student text\u2028'
    packet = {'packet_id': 'invented-packet', 'rubric_id': 'help-work-v1',
              'definitions': {'help_request': 'Asks for assistance or a check.',
                              'work_present': 'Presents an answer, code, reasoning or diagnostic evidence.'},
              'cases': [{'id': f'case-{i}', 'context_status': 'Earlier messages are context only.',
                         'prefix': {'context': [], 'turns': [
                             {'id': f'turn-{i}', 'role': 'tutor', 'text': attack}]},
                         'candidates': [{'id': f'item-{i}', 'text': attack}]}
                        for i in range(24)]}
    source, output = tmp_path / 'packet.json', tmp_path / 'review.html'
    raw = json.dumps(packet, ensure_ascii=False)
    source.write_text(raw, encoding='utf-8')
    assert build(source, output) == output
    html = output.read_text(encoding='utf-8')
    assert attack not in html
    embedded = re.search(r'<script id="review-data" type="application/json">(.*?)</script>', html, re.S)
    assert json.loads(embedded.group(1)) == packet
    assert source.read_text(encoding='utf-8') == raw
    with pytest.raises(FileExistsError):
        build(source, output)
    assert output.read_text(encoding='utf-8') == html

    for change in (
        lambda p: p.update(prediction=.7),
        lambda p: p['cases'][0].update(account_id='PRIVATE'),
        lambda p: p['cases'][0]['candidates'][0].update(cue=True),
        lambda p: p['cases'][0]['prefix']['turns'][0].update(role='system'),
        lambda p: p['cases'][0]['candidates'][0].update(id='item-1'),
        lambda p: p['cases'][0]['candidates'].append({'id': 'extra', 'text': 'extra'}),
        lambda p: p['cases'].pop(),
        lambda p: p.update(rubric_id='another-rubric'),
    ):
        invalid = deepcopy(packet)
        change(invalid)
        source.write_text(json.dumps(invalid), encoding='utf-8')
        with pytest.raises(ValueError):
            build(source, tmp_path / 'invalid.html')
        assert not (tmp_path / 'invalid.html').exists()

    # Run the page's actual state logic with Node; DOM/storage are the I/O boundary.
    node = shutil.which('node')
    assert node, 'Node is required for the browser draft regression'
    script = html.split('<script>')[1].split('</script>')[0].split('// Wire page controls.')[0]
    check = r'''
const assert = require('node:assert/strict'), vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const elements = new Map(), values = new Map(); let unavailable = false;
const context = vm.createContext({JSON,
  document:{getElementById(id) {if (!elements.has(id)) elements.set(id, {textContent:id === 'review-data' ? JSON.stringify(input.packet) : '', hidden:true}); return elements.get(id);}},
  localStorage:{getItem(key) {if (unavailable) throw Error('unavailable'); return values.get(key) ?? null;},
    setItem(key,value) {if (unavailable) throw Error('unavailable'); values.set(key,value);}}
});
const run = code => vm.runInContext(code, context);
run(input.script); run('loadDraft()');
assert.equal(values.size, 0);
const blank = JSON.parse(run('exportText(false)'));
assert.deepEqual(Object.keys(blank).sort(), ['packet_id','rubric_id','reviewer','previously_seen_cases','judgments'].sort());
assert.equal(blank.reviewer, null); assert.equal(blank.previously_seen_cases, null);
assert.deepEqual(blank.judgments[0], {id:'item-0',work_present:null,note:null});
assert.equal(blank.judgments.length,24);
assert.throws(() => run('exportText(true)'), /Complete/);
run("draft.form.reviewer='Invented reviewer'; draft.form.previously_seen_cases='no'; draft.form.judgments.forEach(a=>a.work_present='yes'); persist()");
assert.equal(run('reviewComplete()'), true);
assert.equal(JSON.parse(run('exportText(true)')).judgments.some(a=>'help_request' in a),false);
run("draft.form.judgments[0].work_present='unclear';draft.form.judgments[0].note='  '");
assert.equal(run('reviewComplete()'), false);
assert.throws(() => run('exportText(true)'), /Complete/);
run("draft.form.judgments[0].note='Ambiguous work'; persist()");
assert.equal(run('reviewComplete()'),true);
run("draft.form.judgments[0].note='Unsaved'; loadDraft()");
assert.equal(run('draft.form.judgments[0].note'), 'Ambiguous work');
const saved = values.get(run('storageKey'));
unavailable=true; run("draft.form.judgments[0].note='Current text'");
assert.equal(run('persist()'),false); assert.equal(values.get(run('storageKey')),saved);
unavailable=false; run('storageBlocked=false'); values.set(run('storageKey'),saved.replace('Ambiguous work','Another tab'));
assert.equal(run('persist()'),false); assert.match(values.get(run('storageKey')),/Another tab/);
for (const stale of ['{broken', saved.replace('help-work-v1','old-rubric'), saved.replace('invented-packet','other-packet')]) {
  values.set(run('storageKey'),stale); run('storageBlocked=false; loadDraft()');
  assert.equal(run('persist()'),false); assert.equal(values.get(run('storageKey')),stale);
}
run('draft.form.judgments[0].help_request="yes"');
assert.equal(run('validDraft(draft)'),false);
'''
    subprocess.run([node, '-e', check], input=json.dumps({'packet': packet, 'script': script}),
                   text=True, check=True, capture_output=True)
