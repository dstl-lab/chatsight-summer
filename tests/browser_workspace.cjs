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
    insertAdjacentHTML(){}, scrollIntoView(){}, hasAttribute(){return false}, focus(){document.activeElement=this}});
  return elements.get(id);
};
const modes = ['inspect','simulate','compare'].map(mode=>Object.assign(node(mode),{dataset:{mode}}));
let sidebarButtons=[];
const document = {activeElement:null, body:node('body'), getElementById:node,
  querySelector:selector=>node(selector),
  querySelectorAll:selector=>selector==='[data-mode]'?modes:selector==='[data-scenario]'?sidebarButtons:[]};
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
let fail=false, requests=[], finishPost, readBusy=false, pollCallbacks=[], postFailure=false;
let catalog=[], savedUrl=new URL('http://127.0.0.1/');
packet.controls={send_enabled:false,policy:'One concise hint.',reference:null,blocked_reason:null};
packet.operation={status:'idle',message:''};
const context=vm.createContext({document, window:{matchMedia:()=>({matches:true}),
  get location(){return savedUrl},history:{replaceState:(_a,_b,url)=>{savedUrl=new URL(url,savedUrl)}}},
  URL,URLSearchParams,AbortController,setTimeout:(fn,ms)=>ms===1500?(pollCallbacks.push(fn),0):setTimeout(fn,ms),clearTimeout,fetch:async(url,options)=>{
    requests.push({url,options});
    if(url==='/api/scenarios')return {ok:true,status:200,json:async()=>({version:1,scenarios:catalog})};
    if(options.method==='POST')return new Promise(resolve=>{finishPost=()=>resolve({ok:!postFailure,status:postFailure?409:200,json:async()=>postFailure?{detail:'A request is already saved.'}:packet})});
    return {ok:!fail,status:readBusy?202:fail?409:200,json:async()=>readBusy?{version:1,operation:{status:'running',message:'Request running.'}}:fail?{detail:'Cannot verify saved run.'}:packet};
  }});
const run=code=>vm.runInContext(code,context);
(async()=>{
  run(fs.readFileSync(script,'utf8'));await run('ready');
  assert.match(node('canvas').innerHTML,/Find the fraction of blue rows/);
  assert.match(node('canvas').innerHTML,/&lt;script&gt;never execute/);
  assert.doesNotMatch(node('canvas').innerHTML,/<script>|<img src=x/);
  assert.match(node('canvas').innerHTML,/&lt;img src=x/);
  assert.match(node('canvas').innerHTML,/origin unspecified/);
  finished.dialogue.push({role:'tutor',origin:'supplied',text:'**Try** `x < 3`',display_html:'<p><strong>Try</strong> <code>x &lt; 3</code></p>'});
  run('render()');
  assert.match(node('canvas').innerHTML,/<strong>Try<\/strong> <code>x &lt; 3<\/code>/);
  run("selectEvidence('turn:1')");
  assert.match(node('inspector').innerHTML,/\*\*Try\*\* `x &lt; 3`/);
  assert.doesNotMatch(node('inspector').innerHTML,/<strong>Try/);
  finished.dialogue.pop();run("selectMode('simulate')");
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
  assert.ok(requests.every(r=>['/api/workspace','/api/scenarios'].includes(r.url)&&!r.options.method));
  assert.equal(run('typeof canSubmit'),'function','Bound browser controls are missing');
  assert.equal(run('canSubmit()'),false);
  packet.controls.send_enabled=true;
  packet.encounters[0].frames=[initial];
  await run('reloadWorkspace()');
  assert.equal(run('canSubmit()'),true);
  run("selectEvidence('controls')");
  assert.match(node('inspector').innerHTML,/Continue one student decision/);
  const sent=run('submitOperation()');
  await run('submitOperation()');
  assert.equal(requests.filter(r=>r.options.method==='POST').length,1);
  assert.equal(run('canSubmit()'),false);
  assert.match(node('operation-status').textContent,/running|Generating/i);
  packet.encounters[0].frames.push({...initial,label:'Saved step 1',status:'awaiting-tutor',pending_message:'help'});
  finishPost();await sent;
  assert.equal(run('canSubmit()'),true);
  run("selectEvidence('controls')");
  node('policy').oninput({target:{value:'My edited tutor instructions.'}});
  await run('reloadWorkspace()');
  assert.equal(run('state.policyDraft'),'My edited tutor instructions.');
  run("selectEvidence('controls')");
  const response=run('submitOperation()');
  const request=JSON.parse(requests.filter(r=>r.options.method==='POST').at(-1).options.body);
  assert.equal(request.mode,'policy');assert.equal(request.text,'My edited tutor instructions.');
  finishPost();await response;
  assert.equal(run('state.showInspector'),false);
  run("selectEvidence('controls')");
  assert.equal(node('continuation-reason').textContent,'');
  node('policy').oninput({target:{value:'   '}});assert.equal(run('canSubmit()'),false);
  node('tutor-mode').onchange({target:{value:'reply'}});assert.equal(run('canSubmit()'),false);
  node('manual-reply').oninput({target:{value:'My manual hint.'}});assert.equal(run('canSubmit()'),true);
  postFailure=true;
  const rejected=run('submitOperation()');finishPost();await rejected;
  assert.equal(requests.filter(r=>r.options.method==='POST').length,3);
  assert.equal(JSON.parse(requests.filter(r=>r.options.method==='POST').at(-1).options.body).text,'My manual hint.');
  assert.match(node('operation-status').textContent,/already saved/);
  assert.equal(run('state.replyDraft'),'My manual hint.');
  run("state.clientError=''");
  run('selectFrame(0)');assert.equal(run('canSubmit()'),false);
  const count=requests.filter(r=>r.options.method==='POST').length;
  readBusy=true;await run('reloadWorkspace()');
  assert.equal(run('canSubmit()'),false);assert.equal(pollCallbacks.length,1);
  readBusy=false;await pollCallbacks.shift()();
  assert.equal(requests.filter(r=>r.options.method==='POST').length,count);
  packet.controls.blocked_reason='An earlier tutor request is saved; it will not be resent.';
  await run('reloadWorkspace()');assert.equal(run('canSubmit()'),false);
  assert.match(node('operation-status').textContent,/not be resent/);
  packet.kind='chat';packet.controls.blocked_reason=null;
  packet.encounters=[{id:'1',title:'Conversation',task:'Conversation scenario',
    initialization:'Supplied conversation prefix; notebook activity is unknown.',activity:null,
    frames:[{...initial,status:'ready',work:null,feedback:null,changes:null,
      dialogue:[{role:'student',origin:'source',text:'<b>what went wrong</b>'}]}]}];
  await run('reloadWorkspace()');
  assert.match(node('.breadcrumb').textContent,/Conversation/);
  assert.match(node('canvas').innerHTML,/Notebook activity unavailable/);
  assert.match(node('canvas').innerHTML,/&lt;b&gt;what went wrong/);
  assert.doesNotMatch(node('canvas').innerHTML,/Saved notebook work|View changes|local check|split-view/);
  assert.match(node('view-description').textContent,/student can continue/);
  assert.equal(run('canSubmit()'),true);
  postFailure=false;
  const chatAdvance=run('submitOperation()');
  assert.deepEqual(JSON.parse(requests.filter(r=>r.options.method==='POST').at(-1).options.body),{binding:{},mode:'advance'});
  finishPost();await chatAdvance;
  run("selectEvidence('controls')");
  assert.doesNotMatch(node('inspector').innerHTML,/local check|task, work/);
  run("selectEvidence('context')");
  assert.doesNotMatch(node('inspector').innerHTML,/selected cell|<h3>Activity/);
  run("selectMode('inspect')");
  assert.match(node('canvas').innerHTML,/Notebook activity unavailable/);
  assert.doesNotMatch(node('canvas').innerHTML,/recorded checks are available/);
  packet.encounters[0].frames[0].decisions_remaining=0;
  await run('reloadWorkspace()');
  assert.equal(run('canSubmit()'),false);
  assert.match(node('view-description').textContent,/budget exhausted/);
  assert.equal(run('typeof selectScenario'),'function','Scenario navigation is missing');
  catalog=[{id:'a',title:'Scenario 01'},{id:'b',title:'Scenario 02'}];
  sidebarButtons=catalog.map(s=>Object.assign(node('scenario-'+s.id),{dataset:{scenario:s.id}}));
  run('state.scenarios=null');packet.scenario_id='a';
  packet.encounters[0].frames[0].decisions_remaining=2;
  await run('reloadWorkspace()');
  assert.equal(run('state.scenarioId'),'a');
  assert.match(node('cases').innerHTML,/Scenario 01/);
  assert.match(node('cases').innerHTML,/Scenario 02/);
  run("state.policyDraft='Edited for A';state.replyDraft='Private draft A'");
  packet.scenario_id='b';
  node('scenario-b').focus();
  const switching=run("selectScenario('b')");
  document.activeElement=document.body; // Real DOM removal detaches the clicked sidebar button.
  await switching;
  assert.equal(document.activeElement,node('scenario-b'));
  assert.equal(run('state.scenarioId'),'b');
  assert.equal(savedUrl.searchParams.get('scenario'),'b');
  assert.equal(run('state.replyDraft'),'');
  assert.equal(run('state.policyDraft'),'One concise hint.');
  assert.equal(requests.at(-1).url,'/api/workspace?scenario=b');
  run('state.scenarios=null;state.scenarioId=null');
  await run('reloadWorkspace()');
  assert.equal(run('state.scenarioId'),'b','Reload must retain the URL selection');
  const loading=run('reloadWorkspace()');
  await run("selectScenario('a')");assert.equal(run('state.scenarioId'),'b');
  await loading;
  const selectedPost=run('submitOperation()');
  assert.equal(requests.at(-1).url,'/api/continue?scenario=b');
  await run("selectScenario('a')");assert.equal(run('state.scenarioId'),'b');
  finishPost();await selectedPost;
  fail=true;packet.scenario_id='a';
  await run("selectScenario('a')");
  assert.match(node('canvas').innerHTML,/Cannot verify saved run/);
  assert.match(node('cases').innerHTML,/Scenario 02/);
  assert.equal(run('canSubmit()'),false);
  fail=false;packet.scenario_id='b';
  node('scenario-b').focus();
  const recovering=run("selectScenario('b')");node('search').focus();await recovering;
  assert.equal(document.activeElement,node('search'),'Selection must not steal focus back');
  assert.equal(run('canSubmit()'),true);
  node('search').value='02';node('search').oninput();
  assert.match(node('cases').innerHTML,/Scenario 02/);
  assert.doesNotMatch(node('cases').innerHTML,/Scenario 01/);
  node('search').value='';
  readBusy=true;await run('reloadWorkspace()');
  await run("selectScenario('a')");assert.equal(run('state.scenarioId'),'b');
  readBusy=false;await pollCallbacks.shift()();
  packet.scenario_id='a';await run('reloadWorkspace()');
  assert.match(node('canvas').innerHTML,/selected scenario/i);
  assert.equal(run('canSubmit()'),false);
  console.log('Saved workspace: playback, escaping, evidence, status, and failed reload recovery pass.');
})().catch(error=>{console.error(error);process.exitCode=1});
