"""A blind review preserves text, explicit human choices, and existing drafts."""
from copy import deepcopy
import importlib.util
import json
import re
import shutil
import subprocess

import pytest


def test_blind_review_boundaries_and_browser_draft(tmp_path):
    assert importlib.util.find_spec('src.eval.communication_review'), 'Review builder is missing'
    from src.eval.communication_review import build

    attack = '</script><script>alert("invented")</script>\n  student text\u2028'
    packet = {'packet_id': 'invented-packet', 'rubric_id': 'help-work-v1',
              'definitions': {'help_request': 'Asks for assistance or a check.',
                              'work_present': 'Presents an attempted answer or code.'},
              'cases': [{'id': 'case-1', 'context_status': 'No notebook available.',
                         'prefix': {'context': [{'id': 'turn-1', 'role': 'student', 'text': attack}],
                                    'turns': [{'id': 'turn-2', 'role': 'tutor', 'text': 'Try again.'}]},
                         'candidates': [{'id': 'item-1', 'text': 'why?'},
                                        {'id': 'item-2', 'text': attack}]}]}
    source, output = tmp_path / 'packet.json', tmp_path / 'review.html'
    raw = json.dumps(packet, ensure_ascii=False)
    source.write_text(raw, encoding='utf-8')
    assert build(source, output) == output
    html = output.read_text(encoding='utf-8')
    assert attack not in html
    embedded = re.search(r'<script id="review-data" type="application/json">(.*?)</script>', html, re.S)
    assert json.loads(embedded.group(1)) == packet
    assert source.read_text(encoding='utf-8') == raw
    assert 'connect-src \'none\'' in html
    with pytest.raises(FileExistsError):
        build(source, output)
    assert output.read_text(encoding='utf-8') == html

    for change in (
        lambda p: p.update(condition='PRIVATE_SOURCE'),
        lambda p: p['definitions'].update(extra='PRIVATE_SOURCE'),
        lambda p: p['cases'][0].update(source_id='PRIVATE_SOURCE'),
        lambda p: p['cases'][0]['prefix'].update(label='PRIVATE_SOURCE'),
        lambda p: p['cases'][0]['prefix']['turns'][0].update(condition='PRIVATE_SOURCE'),
        lambda p: p['cases'][0]['candidates'][0].update(condition='PRIVATE_SOURCE'),
        lambda p: p['cases'].append(deepcopy(p['cases'][0])),
        lambda p: p['cases'][0]['candidates'][1].update(id='item-1'),
        lambda p: p['cases'][0]['prefix']['turns'][0].update(id='turn-1'),
        lambda p: p['cases'][0]['prefix']['turns'][0].update(role='system'),
        lambda p: p['cases'][0].update(candidates=[]),
        lambda p: p['cases'][0].update(candidates=[{'id': str(i), 'text': ''} for i in range(10)]),
        lambda p: p.update(rubric_id='changed-rubric'),
    ):
        invalid = deepcopy(packet)
        change(invalid)
        source.write_text(json.dumps(invalid), encoding='utf-8')
        with pytest.raises(ValueError):
            build(source, tmp_path / 'invalid.html')
        assert not (tmp_path / 'invalid.html').exists()

    # Execute the real page's state functions with Node's stdlib; no DOM framework.
    node = shutil.which('node')
    assert node, 'Node is required for the portable page state regression'
    script = html.split('<script>')[1].split('</script>')[0].split('// Wire page controls.')[0]
    check = r'''
const assert = require('node:assert/strict'), vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const elements = new Map(), values = new Map(); let unavailable = false;
const context = vm.createContext({JSON, structuredClone,
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
assert.deepEqual(blank.judgments, input.packet.cases[0].candidates.map(c => ({id:c.id,help_request:null,work_present:null,note:null})));
assert.throws(() => run('exportText(true)'), /Complete/);
run("draft.form.reviewer='Invented reviewer'; draft.form.previously_seen_cases='unsure'; draft.form.judgments.forEach(a=>{a.help_request='yes';a.work_present='yes';}); persist()");
assert.equal(run('reviewComplete()'), true, 'Both yes is allowed');
run("draft.form.judgments[0].work_present='unclear'");
assert.equal(run('reviewComplete()'), false);
assert.throws(() => run('exportText(true)'), /Complete/);
run("draft.form.judgments[0].note='Ambiguous attempted work'; persist()");
assert.equal(JSON.parse(run('exportText(true)')).judgments[0].note, 'Ambiguous attempted work');
run("draft.form.judgments[0].note='Unsaved'; loadDraft()");
assert.equal(run('draft.form.judgments[0].note'), 'Ambiguous attempted work');
const saved = values.get(run('storageKey'));
unavailable=true; run("draft.form.judgments[0].note='Current text'");
assert.equal(run('persist()'),false); assert.equal(values.get(run('storageKey')),saved);
unavailable=false; run('storageBlocked=false'); values.set(run('storageKey'),saved.replace('Ambiguous attempted work','Another tab'));
assert.equal(run('persist()'),false); assert.match(values.get(run('storageKey')),/Another tab/);
for (const stale of ['{broken', saved.replace('help-work-v1','old-rubric'), saved.replace('why?','changed question')]) {
  values.set(run('storageKey'),stale); run('storageBlocked=false; loadDraft()');
  assert.equal(run('persist()'),false); assert.equal(values.get(run('storageKey')),stale);
}
assert.equal(run('validDraft({...draft, condition:"hidden"})'),false);
assert.equal(run('validDraft({...draft, form:{...draft.form, judgments:[draft.form.judgments[0],draft.form.judgments[0]]}})'),false);
'''
    subprocess.run([node, '-e', check], input=json.dumps({'packet': packet, 'script': script}),
                   text=True, check=True, capture_output=True)
