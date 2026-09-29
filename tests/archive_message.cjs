// Authored three-frame adapter check; no model or execution requests.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const nodes=new Map();
const document={activeElement:null,querySelector:selector=>node(selector)};
function node(id){
  if(!nodes.has(id))nodes.set(id,{textContent:'',innerHTML:'',hidden:false,dataset:{},attributes:{},style:{},
    before(child){this.beforeNode=child},setAttribute(name,value){this.attributes[name]=value},
    querySelectorAll(){return buttons},focus(){document.activeElement=this}});
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
  render(){renders++;node('#canvas .notebook-document > .notebook-caption').textContent='Code execution is unavailable';
    node('#canvas .notebook-prompt').attributes={title:'Code execution unavailable'};
    node('#conversation-messages > p.quiet:last-child').textContent='This saved decision ends the branch.';
    node('view-description').textContent=context.statusText(saved.frames[state.step]);
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
saved.archive_message=false;
assert.equal(context.statusText(saved.frames[2]),'Generic status');
assert.equal(context.pendingReplyNote(),'Generic pending note');
context.renderInspector();assert.equal(node('inspector').innerHTML,'Generic inspector');
state.encounters=[];const before=renders;context.render();context.renderOperationStatus();
assert.equal(renders,before,'Empty or rejected data does not enter the frame renderer');
assert.equal(node('playback').hidden,true);
console.log('Archive message: saved final stage, native timeline/focus, unexecuted code, pending tutor, scoped copy and empty state pass.');
