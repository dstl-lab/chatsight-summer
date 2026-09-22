// Lightweight state/render smoke check; browser verification covers actual DOM/layout.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../docs/prototypes/student-workspace.html'), 'utf8');
const elements = new Map();
const document = {
  activeElement: null,
  querySelectorAll: () => [],
  querySelector: () => null,
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, {value:'', textContent:'', innerHTML:'',
      classList:{toggle() {}, remove() {}}, setAttribute() {},
      focus() {document.activeElement = this;}, hasAttribute() {return false;}});
    return elements.get(id);
  },
};
let wide = true;
const context = vm.createContext({document, window:{matchMedia:()=>({matches:wide})}});
const run = code => vm.runInContext(code, context);
run(html.match(/<script>([\s\S]*?)<\/script>/)[1]);
const node = id => document.getElementById(id);
assert.match(node('canvas').innerHTML, /Generic baseline/);
assert.match(node('canvas').innerHTML, /not model outputs/);
run("selectMode('simulate')");
node('next-step').onclick(); node('next-step').onclick();
assert.equal(node('next-step').disabled, true);
assert.match(node('canvas').innerHTML, /Illustrative check output/);
run("state.step=0; render()");
assert.doesNotMatch(node('canvas').innerHTML, /Illustrative check output/);
run('openInstructions()');
node('policy').oninput({target:{value:'Temporary tutor draft'}});
node('save-draft').onclick();
run("selectMode('inspect'); openInstructions()");
assert.match(node('inspector').innerHTML, /Temporary tutor draft/);
node('policy').oninput({target:{value:'   '}});
assert.equal(node('save-draft').disabled, true);
node('restore-draft').onclick();
assert.match(node('inspector').innerHTML, /Give one focused hint/);
node('search').value='does not exist'; node('search').oninput();
assert.match(node('cases').innerHTML, /No matching cases/);
wide=false;
node('reset').onclick();
assert.equal(run('state.showInspector'), false);
run("selectEvidence('baseline')");
assert.equal(run('state.showInspector'), true);
run("selectMode('simulate')");
assert.equal(run('state.showInspector'), false);
run("state.caseIndex=1; selectMode('compare')");
assert.match(node('case-title').textContent, /Calculating an average/);
assert.equal(run("inputPrompt('baseline',current()).includes(current().history[0])"), false);
assert.equal(run("inputPrompt('grounded',current()).includes(current().history[0])"), true);
assert.doesNotMatch(html, /\bfetch\s*\(|XMLHttpRequest|WebSocket|<script[^>]+src=|<link[^>]+href=/);
console.log('Workspace prototype: playback, drafts, cases, evidence scope, and narrow-view state pass.');
