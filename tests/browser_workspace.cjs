// State/render check; the browser check exercises actual DOM, layout, and HTTP.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const script = path.join(__dirname, '../apps/browser_workspace.js');
assert.ok(fs.existsSync(script), 'Saved workspace controller is missing');
const elements = new Map();
const node = id => {
  if (!elements.has(id)) elements.set(id, {innerHTML:'', textContent:'', value:'', hidden:false,
    dataset:{}, classList:{toggle(){},remove(){}}, setAttribute(){},
    hasAttribute(){return false}, focus(){document.activeElement=this}});
  return elements.get(id);
};
const modes = ['inspect','simulate','compare'].map(mode=>Object.assign(node(mode),{dataset:{mode}}));
const document = {activeElement:null, getElementById:node,
  querySelector:selector=>node(selector),
  querySelectorAll:selector=>selector==='[data-mode]'?modes:[]};
const initial = {label:'Initial state',status:'active',decisions_remaining:3,
  work:{cell_index:1,revision:0,source:'count = 0'},dialogue:[],pending_message:null,
  feedback:null,changes:{baseline_revision:0,baseline_kind:'initial-work',unified_diff:''},actions:[],binding:{}};
const finished = {...initial,label:'Saved step 1',status:'no-reply',decisions_remaining:0,
  work:{cell_index:1,revision:1,source:'<script>never execute</script>'},
  dialogue:[{role:'student',origin:null,text:'<img src=x onerror=alert(1)>'}],
  actions:[{decision:'no-reply',source:null,text:''}],
  feedback:{status:'checked',success:true,value:2},
  changes:{baseline_revision:0,baseline_kind:'previous-saved-step',unified_diff:'-count = 0\n+count = 2'}};
const packet = {version:1,encounters:[{id:'1',title:'Task 1',task:[{index:0,source:'Find the fraction of blue rows.'}],
  initialization:'Authored example',activity:{library:'babypandas'},frames:[initial,finished]}]};
let fail=false, requests=[];
const context=vm.createContext({document, window:{matchMedia:()=>({matches:true})},
  AbortController,setTimeout,clearTimeout,fetch:async(url,options)=>{
    requests.push({url,options});return {ok:!fail,json:async()=>fail?{detail:'Cannot verify saved run.'}:packet};
  }});
const run=code=>vm.runInContext(code,context);
(async()=>{
  run(fs.readFileSync(script,'utf8'));await run('ready');
  assert.match(node('canvas').innerHTML,/Find the fraction of blue rows/);
  assert.match(node('canvas').innerHTML,/&lt;script&gt;never execute/);
  assert.doesNotMatch(node('canvas').innerHTML,/<script>|<img src=x/);
  assert.match(node('canvas').innerHTML,/&lt;img src=x/);
  assert.match(node('canvas').innerHTML,/origin unspecified/);
  assert.match(node('view-description').textContent,/chose no reply/i);
  assert.equal(node('next-step').disabled,true);
  node('search').value='fraction';node('search').oninput();
  assert.match(node('cases').innerHTML,/Task 1/);
  node('search').value='';
  run('selectFrame(0)');
  assert.match(node('canvas').innerHTML,/No check feedback/);
  assert.doesNotMatch(node('canvas').innerHTML,/Passed/);
  node('next-step').onclick();
  assert.match(node('canvas').innerHTML,/Passed/);
  run("selectEvidence('work')");
  assert.match(node('inspector').innerHTML,/-count = 0/);
  run("selectMode('inspect')");
  assert.equal(node('playback').hidden,true);
  assert.equal(run('state.showInspector'),false);
  assert.match(run("statusText({...frame(),status:'active',decisions_remaining:0})"),/budget exhausted/i);
  fail=true;await run('reloadWorkspace()');
  assert.match(node('canvas').innerHTML,/Cannot verify saved run/);
  assert.doesNotMatch(node('canvas').innerHTML,/never execute/);
  assert.equal(node('cases').innerHTML,'');
  assert.equal(node('playback').hidden,true);
  fail=false;await run('reloadWorkspace()');
  assert.match(node('canvas').innerHTML,/&lt;img src=x/);
  run("selectMode('simulate')");
  assert.match(node('canvas').innerHTML,/&lt;script&gt;never execute/);
  assert.ok(requests.every(r=>r.url==='/api/workspace'&&!r.options.method));
  console.log('Saved workspace: playback, escaping, evidence, status, and failed reload recovery pass.');
})().catch(error=>{console.error(error);process.exitCode=1});
