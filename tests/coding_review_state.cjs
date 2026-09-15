// node tests/coding_review_state.cjs — invented answers, no browser or network.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const file = require('node:path').join(__dirname, '../src/eval/coding_review.html');
assert.ok(fs.existsSync(file), 'Portable review page is missing');
const script = fs.readFileSync(file, 'utf8').split('<script>')[1].split('</script>')[0];
const packet = {packet_id:'test-packet', reviewer_id:'reviewer-1', options:{'asked-for-help':'Help', 'other':'Other', 'revised-code':'Changed code', 'insufficient-evidence':'Unknown'},
  cases:[{case:1}], form:{reviewer:null, previously_seen_these_cases_or_labels:null, cases:[{case:1, followup:null, note:null}]}};
const elements = new Map();
const values = new Map();
let unavailable = false;
const context = vm.createContext({structuredClone, JSON, console,
  document:{getElementById(id) { if (!elements.has(id)) elements.set(id, {textContent:id === 'review-data' ? JSON.stringify(packet) : '', hidden:true}); return elements.get(id); }},
  localStorage:{getItem(key) {if (unavailable) throw Error('storage unavailable'); return values.get(key) ?? null;},
    setItem(key, value) {if (unavailable) throw Error('storage unavailable'); values.set(key, value);}},
});
const run = code => vm.runInContext(code, context);
run(script.slice(0, script.indexOf('// Wire page controls.')));
run('loadDraft()');
assert.equal(values.size, 0, 'Opening a page must not record a judgment');
assert.equal(run('answerComplete(draft.form.cases[0])'), false);
run("draft.started=true; draft.form.reviewer='Test'; draft.form.previously_seen_these_cases_or_labels=false; draft.form.cases[0].followup='other'; persist()");
assert.equal(run('answerComplete(draft.form.cases[0])'), false, 'Other requires an explanation');
run("draft.form.cases[0].note='Test explanation'; persist()");
assert.equal(run('answerComplete(draft.form.cases[0])'), true);
assert.equal(JSON.parse([...values.values()][0]).form.cases[0].note, 'Test explanation');
run('draft.index=0; loadDraft()');
assert.equal(run('draft.form.cases[0].note'), 'Test explanation', 'Resume restores human draft');
const saved = [...values.values()][0];
run("draft.form.cases[0].note='Unsaved test change'");
unavailable = true;
assert.equal(run('persist()'), false);
assert.equal([...values.values()][0], saved, 'A storage failure preserves the saved draft');
assert.equal(run('draft.form.cases[0].note'), 'Unsaved test change', 'Failed saves retain current input');
unavailable = false;
run('storageBlocked=false');
values.set(run('storageKey'), saved.replace('Test explanation', 'Another tab'));
assert.equal(run('persist()'), false, 'Stale pages must not replace another tab’s draft');
assert.match([...values.values()][0], /Another tab/);
values.set(run('storageKey'), '{broken');
run('storageBlocked=false; loadDraft()');
assert.equal(run('persist()'), false, 'Unreadable drafts must not be overwritten');
assert.equal([...values.values()][0], '{broken');
assert.equal(run('validDraft({...draft, form:{...draft.form, cases:[{case:99, followup:null, note:null}]}})'), false);
assert.equal(run('validDraft({...draft, started:true, form:{...draft.form, reviewer:null}})'), false,
  'A resumed started review requires its reviewer details');
console.log('Portable review state: completion, resume, failed saves, stale tabs and corrupt-draft preservation pass.');
