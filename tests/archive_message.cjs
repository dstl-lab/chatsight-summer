// Authored three-frame adapter check; no model or execution requests.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const nodes=new Map();
const document={activeElement:null,querySelector:selector=>node(selector)};
let runButtons=[],runNodeId=0;
function node(id){
  if(!nodes.has(id))nodes.set(id,{textContent:'',html:'',hidden:false,dataset:{},attributes:{},style:{},
    get innerHTML(){return this.html},set innerHTML(html){
      this.html=html;if(id!=='simulation-run')return;
      if(runButtons.includes(document.activeElement))document.activeElement=null;
      runButtons=[...html.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)].map(([,attrs,content])=>{
        const button=node('run-button-'+(++runNodeId));button.innerHTML=content;
        button.attributes=Object.fromEntries([...attrs.matchAll(/([\w-]+)="([^"]*)"/g)].map(([,key,value])=>[key,value]));
        button.dataset.run=button.attributes['data-run'];return button;
      });
    },
    before(child){this.beforeNode=child},insertAdjacentHTML(position,html){this.inserted={position,html}},
    setAttribute(name,value){this.attributes[name]=value},
    querySelectorAll(){return id==='simulation-run'?runButtons:buttons},
    querySelector(selector){return runButtons.find(button=>selector===`[data-run="${button.dataset.run}"]`||selector===`button[data-run="${button.dataset.run}"]`)},
    contains(element){return id==='simulation-run'&&runButtons.includes(element)},
    closest(selector){return selector==='button[data-run]'&&this.dataset.run?this:null},
    focus(){document.activeElement=this}});
  return nodes.get(id);
}
const stages=['captured','tutor','message'];
const saved={archive_message:true,authored_demo:false,model_decisions:1,execution_calls:0,
  initialization:'Captured context <not markup>',frames:stages.map((archive_stage,i)=>({archive_stage,
    label:['Captured start','Saved tutor reply','Student edit + message'][i],
    status:i===2?'awaiting-tutor':'active',actions:i===2?[{decision:'revise-work'}]:[],
    changes:{baseline_kind:i===0?'initial-work':'previous-saved-step',baseline_revision:0,unified_diff:i===2?'+new source':''}}))};
const state={encounters:[saved],caseIndex:0,step:2,selected:'step'};
let renders=0;
const buttons=stages.map((_,i)=>{const button=node('button-'+i);button.dataset.trail=String(i);
  button.onclick=()=>{state.step=i;context.render()};return button});
const handlers=buttons.map(button=>button.onclick);
const context=vm.createContext({state,document,$:node,current:()=>state.encounters[state.caseIndex],
  frame:()=>state.encounters[state.caseIndex].frames[state.step],glyph:()=>'<svg aria-hidden="true"></svg>',
  esc:value=>String(value).replaceAll('<','&lt;').replaceAll('>','&gt;'),block:value=>'<pre>'+String(value).replaceAll('<','&lt;').replaceAll('>','&gt;')+'</pre>',
  statusText:()=> 'Generic status',pendingReplyNote:()=> 'Generic pending note',continuationReason:()=> 'Generic control reason',
  sourceOnlyNotebook:()=>'<section><pre class="notebook-input"><code>saved code</code></pre><p>caption</p></section>',
  externalExecution:(result,title)=>`<section class="notebook-result">${title}: ${result.output}</section>`,
  renderInspector(){node('inspector').innerHTML='Generic inspector'},
  notify(){},
  render(){renders++;const active=state.encounters[state.caseIndex];
    while(buttons.length<active.frames.length){const i=buttons.length,button=node('button-'+i);button.dataset.trail=String(i);
      button.onclick=()=>{state.step=i;context.render()};buttons.push(button)}
    buttons.splice(active.frames.length);
    node('#canvas .notebook-document > .notebook-caption').textContent='Code execution is unavailable';
    node('#canvas .notebook-prompt').attributes={title:'Code execution unavailable'};
    node('#conversation-messages > p.quiet:last-child').textContent='This saved decision ends the branch.';
    node('view-description').textContent=context.statusText(active.frames[state.step]);
    buttons.forEach((button,i)=>button.setAttribute('aria-pressed',String(i===state.step)));
    if(state.showInspector)context.renderInspector();context.renderOperationStatus()},
  renderOperationStatus(){node('.prototype-note').textContent='Source-only branch · Read only'},
  fetch(){throw Error('The adapter must send no requests')}});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../apps/archive-message.js'),'utf8'),context);
assert.equal(state.step,2,'The newly saved message remains selected initially');
assert.equal(node('canvas').beforeNode,node('playback'));
assert.equal(node('trail').style.gridTemplateColumns,'repeat(3, minmax(0, 1fr))');
assert.equal(node('.prototype-note').textContent,'Saved student-controlled loop');
assert.equal(context.statusText(saved.frames[2]),'Awaiting tutor · No reply is running');
assert.match(context.pendingReplyNote(),/No reply is running/);
assert.doesNotMatch(context.continuationReason(),/unavailable|retrospective/);
assert.equal(buttons[2].attributes['aria-label'],'3. Edit + message · Student');
assert.equal(buttons[2].attributes['aria-pressed'],'true');
assert.deepEqual(buttons.map(button=>button.onclick),handlers,'Base click handlers are retained');
assert.match(node('#canvas .notebook-document > .notebook-caption').textContent,/has not been executed in this run/);
assert.doesNotMatch(node('#canvas .notebook-document > .notebook-caption').textContent,/Later stages|researcher|unavailable/);
assert.match(node('#conversation-messages > p.quiet:last-child').textContent,/stopped after the student/);
buttons[2].focus();context.renderOperationStatus();
assert.equal(document.activeElement,buttons[2],'Repeated decoration does not replace the focused event button');
buttons[0].onclick();
assert.equal(state.step,0);
assert.equal(buttons[0].attributes['aria-pressed'],'true');
assert.equal(node('#canvas .notebook-prompt').attributes.title,'No execution result at this stage');
assert.equal(node('view-description').textContent,'Read only');
buttons[1].onclick();assert.match(node('view-description').textContent,/Student has not acted/);
state.selected='context';state.showInspector=true;context.render();
assert.match(node('inspector').innerHTML,/No local execution was requested/);
assert.match(node('inspector').innerHTML,/&lt;not markup&gt;/);
assert.doesNotMatch(node('inspector').innerHTML,/unavailable|researcher-triggered|checked after/);
state.selected='work';context.render();assert.match(node('inspector').innerHTML,/No source change/);
saved.authored_demo=true;context.renderOperationStatus();
assert.equal(node('.prototype-note').textContent,'Authored test data · Saved student-controlled loop');
assert.equal(buttons[0].attributes['aria-label'],'1. Captured · Authored');
saved.frames[2].actions=[{decision:'reply'}];buttons[2].onclick();
assert.equal(buttons[2].attributes['aria-label'],'3. Student message · Student');
saved.archive_continuation=true;saved.execution_results=1;saved.model_decisions=4;
saved.frames.push({archive_stage:'tutor',status:'active',actions:[]},
  {archive_stage:'request-check',status:'active',actions:[{decision:'request-check'}],
    archive_observation:{revision:1,output:'AUTHORED OUTPUT'},archive_observation_new:true},
  {archive_stage:'revise-work',status:'active',actions:[{decision:'revise-work',text:''}]},
  {archive_stage:'no-reply',status:'no-reply',actions:[{decision:'no-reply'}]});
for(let i=3;i<saved.frames.length;i++){const button=node('button-'+i);button.dataset.trail=String(i);button.onclick=()=>{state.step=i;context.render()};buttons.push(button)}
state.showInspector=false;state.step=4;context.render();
assert.equal(node('trail').style.gridTemplateColumns,'repeat(7, minmax(76px, 1fr))');
assert.equal(node('trail').style.overflowX,'auto','Longer timelines keep their native buttons readable');
assert.equal(buttons[4].attributes['aria-label'],'5. Local run · Student');
assert.match(context.sourceOnlyNotebook(),/saved code<\/code><\/pre><section class="notebook-result">Student-requested local execution · revision 1: AUTHORED OUTPUT/);
assert.match(node('#canvas .notebook-document > .notebook-caption').textContent,/student requested this local run/);
assert.doesNotMatch(node('#canvas .notebook-prompt').attributes.title,/retrospective|researcher/i);
state.step=2;context.render();assert.match(context.pendingReplyNote(),/later saved tutor reply/);
assert.match(node('#conversation-messages > p.quiet:last-child').textContent,/following stage/);
state.step=5;context.render();
assert.equal(buttons[5].attributes['aria-label'],'6. Code edit · Student');
assert.doesNotMatch(context.sourceOnlyNotebook(),/AUTHORED OUTPUT/,'An edit does not inherit earlier execution output');
assert.match(node('#canvas .notebook-document > .notebook-caption').textContent,/No execution result for this revision/);
state.step=6;context.render();assert.equal(context.statusText(saved.frames[6]),'Student chose no further action');
saved.frames[6].archive_observation=saved.frames[4].archive_observation;saved.frames[6].archive_observation_new=false;
context.render();assert.match(context.sourceOnlyNotebook(),/Previously observed local result/);
assert.match(node('#canvas .notebook-document > .notebook-caption').textContent,/unchanged revision/);
for(const [status,label] of [['action-limit',/Action limit/],['check-limit',/Local run limit/],
  ['error',/action failed/],['environment-error',/environment unavailable/],['execution-limit',/Execution limit/],
  ['setup-error',/setup failed/],['tutor-error',/Tutor reply failed/]]){
  saved.frames[6].status=status;assert.match(context.statusText(saved.frames[6]),label);
}
saved.frames[6].archive_stage='request-check';saved.frames[6].status='check-limit';context.render();
assert.equal(buttons[6].attributes['aria-label'],'7. Run requested · Student');
assert.doesNotMatch(node('#canvas .notebook-document > .notebook-caption').textContent,/No additional execution occurred/);
saved.frames[6].archive_action_failed=true;saved.frames[6].status='error';state.selected='step';state.showInspector=true;context.render();
assert.match(node('inspector').innerHTML,/attempted action did not complete/);
saved.frames=saved.frames.slice(0,3);buttons.splice(3);
saved.terminal_status='tutor-error';
saved.frames.push({archive_stage:'tutor-error',status:'tutor-error',actions:[]});
const failed=node('button-3');failed.dataset.trail='3';buttons.push(failed);
state.showInspector=false;state.step=2;context.render();
assert.match(context.pendingReplyNote(),/later tutor request failed/);
assert.equal(context.statusText(saved.frames[2]),'Awaiting tutor · No reply is running');
assert.match(node('#conversation-messages > p.quiet:last-child').textContent,/failed tutor request/);
state.selected='context';context.renderInspector();
assert.match(node('inspector').innerHTML,/No tutor reply or new student decision followed/);

const observation={revision:1,output:'AUTHORED RESEARCHER OUTPUT'};
function policy(id,label,edited){
  const frames=['captured','tutor','revise-work','researcher-check',edited?'revise-work':'no-reply']
    .map((archive_stage,i)=>({archive_stage,label:archive_stage,status:i===4?'no-reply':'active',
      work:{revision:edited&&i===4?2:i<2?0:1,source:'saved code'},
      actions:i===2||edited&&i===4?[{decision:'revise-work',text:''}]:i===4?[{decision:'no-reply'}]:[],
      changes:{baseline_kind:'previous-saved-step',baseline_revision:0,unified_diff:''}}));
  frames[3].archive_observation=observation;frames[3].archive_observation_new=true;
  frames[3].archive_observation_actor='researcher';frames[4].archive_reaction=true;
  if(!edited){frames[4].archive_observation=observation;frames[4].archive_observation_new=false;
    frames[4].archive_observation_actor='researcher'}
  return {id,archive_message:true,simulation_workspace:true,policy_sample:true,policy_label:label,
    sample_index:1,authored_demo:false,model_decisions:2,execution_results:1,initialization:'Shared captured context',frames};
}
const latest={...structuredClone(saved),id:'latest',simulation_workspace:true};
const direct=policy('direct','Direct answer',false),hint=policy('hint','Guided hint',true);
const latestBefore=JSON.stringify(latest);
state.encounters=[direct,hint,latest];state.caseIndex=2;state.step=latest.frames.length-1;
state.showInspector=false;context.render();
const selector=node('simulation-run');
const runButton=id=>runButtons.find(button=>button.dataset.run===id);
const selectRun=id=>selector.onclick({target:runButton(id)});
assert.equal(node('simulation-run-row').hidden,false);
assert.equal(node('app').attributes['data-simulation-workspace'],'true');
assert.deepEqual(runButtons.map(button=>button.dataset.run),['latest','direct','hint']);
assert.equal(runButton('latest').attributes['aria-pressed'],'true');
assert.equal(runButton('direct').attributes['aria-label'],'Direct answer · sample 1');
assert.equal(runButton('hint').attributes['aria-label'],'Guided hint · sample 1');
assert.equal(runButton('latest').attributes['aria-label'],'Latest continuation');
assert.match(runButton('direct').innerHTML,/class="run-name"/);
assert.match(runButton('direct').innerHTML,/class="run-sample"[^>]*>Sample 1/);
assert.match(node('playback').inserted.html,/simulation-run-row/,'The run selector is inserted with the timeline');
assert.match(node('playback').inserted.html,/<div id="simulation-run"[^>]*role="group"/);
assert.match(node('.prototype-note').textContent,/^Authored test data · /);
state.showInspector=true;state.selected='turn:7';state.chatKey='stale';node('run-details').open=true;
const focusedRun=runButton('direct');focusedRun.focus();
selector.onclick({target:{closest:selector=>selector==='button[data-run]'?focusedRun:null}});
assert.equal(state.caseIndex,0);assert.equal(state.step,direct.frames.length-1,'Switching selects the saved final stage');
assert.equal(state.showInspector,false);assert.equal(state.selected,'step');assert.equal(state.chatKey,null);
assert.equal(node('run-details').open,false);assert.equal(runButton('direct').attributes['aria-pressed'],'true');
assert.equal(runButton('latest').attributes['aria-pressed'],'false');
assert.equal(document.activeElement,focusedRun,'Switching retains the same focused native button');
assert.doesNotMatch(context.sourceOnlyNotebook(),/Student-requested/);
assert.match(node('#canvas .notebook-document > .notebook-caption').textContent,/unchanged revision/i);
state.step=3;context.render();
assert.equal(buttons[3].dataset.loopStage,'researcher-check','Researcher runs retain the square-node style hook');
assert.match(buttons[3].attributes['aria-label'],/Researcher/);
assert.doesNotMatch(buttons[3].attributes['aria-label'],/Student/);
assert.match(context.sourceOnlyNotebook(),/Researcher-triggered local execution.*AUTHORED RESEARCHER OUTPUT/);
assert.match(node('#canvas .notebook-document > .notebook-caption').textContent,/researcher/i);
assert.doesNotMatch(node('#canvas .notebook-document > .notebook-caption').textContent,/student requested/i);
assert.match(node('#canvas .notebook-prompt').attributes.title,/researcher/i);
assert.doesNotMatch(node('#canvas .notebook-prompt').attributes.title,/student-requested/i);
state.selected='context';context.renderInspector();
assert.match(node('inspector').innerHTML,/researcher/i);
assert.doesNotMatch(node('inspector').innerHTML,/Only student-requested|Student-controlled continuation|No local execution was requested/);
assert.doesNotMatch(context.continuationReason(),/student-controlled/i);
selectRun('hint');
assert.equal(state.caseIndex,1);assert.equal(state.step,4);
assert.doesNotMatch(context.sourceOnlyNotebook(),/AUTHORED RESEARCHER OUTPUT/,'The reaction edit does not inherit an older revision result');
selectRun('latest');
assert.equal(state.caseIndex,2);assert.equal(state.step,latest.frames.length-1);
assert.equal(JSON.stringify(latest),latestBefore,'Policy inspection never changes the saved latest continuation');
assert.match(node('.prototype-note').textContent,/^Authored test data · /);
runButton('latest').focus();const unchangedRun=runButton('latest');context.renderOperationStatus();
assert.equal(document.activeElement,unchangedRun,'Status decoration preserves the run button');
direct.sample_index=2;context.renderOperationStatus();
assert.notEqual(runButton('latest'),unchangedRun,'Sample label changes rebuild the run choices');
assert.equal(document.activeElement,runButton('latest'),'Rebuilt choices restore focus to the same run');
assert.equal(runButton('direct').attributes['aria-label'],'Direct answer · sample 2');
state.refreshing=true;selectRun('direct');
assert.equal(state.caseIndex,2);assert.equal(runButton('latest').attributes['aria-pressed'],'true');
context.renderOperationStatus();assert.ok(runButtons.every(button=>button.disabled));
state.refreshing=false;context.renderOperationStatus();assert.ok(runButtons.every(button=>!button.disabled));
selector.onclick({target:{closest:()=>({dataset:{run:'missing'}})}});assert.equal(state.caseIndex,2);
selector.onclick({target:{closest:()=>null}});assert.equal(state.caseIndex,2);
state.encounters=[saved];state.caseIndex=0;state.step=2;context.render();
assert.equal(node('app').attributes['data-simulation-workspace'],'false');

saved.archive_message=false;
assert.equal(context.statusText(saved.frames[2]),'Generic status');
assert.equal(context.pendingReplyNote(),'Generic pending note');
context.renderInspector();assert.equal(node('inspector').innerHTML,'Generic inspector');
state.encounters=[];const before=renders;context.render();context.renderOperationStatus();
assert.equal(renders,before,'Empty or rejected data does not enter the frame renderer');
assert.equal(node('playback').hidden,true);
assert.equal(node('simulation-run-row').hidden,true);assert.ok(runButtons.every(button=>button.disabled));
console.log('Archive message: saved stages, native switching/focus, execution provenance, pending tutor, scoped copy and empty state pass.');
