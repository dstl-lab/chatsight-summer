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
saved.archive_message=false;
assert.equal(context.statusText(saved.frames[2]),'Generic status');
assert.equal(context.pendingReplyNote(),'Generic pending note');
context.renderInspector();assert.equal(node('inspector').innerHTML,'Generic inspector');
state.encounters=[];const before=renders;context.render();context.renderOperationStatus();
assert.equal(renders,before,'Empty or rejected data does not enter the frame renderer');
assert.equal(node('playback').hidden,true);
console.log('Archive message: saved final stage, native timeline/focus, unexecuted code, pending tutor, scoped copy and empty state pass.');
