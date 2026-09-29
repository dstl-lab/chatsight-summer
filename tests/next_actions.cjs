// Controller contract check; the browser check covers real DOM, layout and HTTP.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const elements=new Map(),timers=new Map(),requests=[];
let timerId=0,renderCount=0,finishPost,losePost=false,loseCancel=false,failRead=false;
const base=new Set(['reset','app','view-description','chat-caption','prototype-note']);
const document={activeElement:null,getElementById:id=>elements.get(id)||null,
  querySelector:selector=>selector==='.prototype-note'?elements.get('prototype-note'):null};
function node(id){
  const element={id,value:'',textContent:'',hidden:false,disabled:false,dataset:{},attributes:{},open:false,
    classList:{add(){}},setAttribute(name,value){this.attributes[name]=value},addEventListener(){},
    focus(){document.activeElement=this},matches(){return this.open},hidePopover(){this.open=false},
    contains(child){return !!child&&!base.has(child.id)&&elements.get(child.id)===child},
    checkValidity(){return this.value!==''&&Number.isInteger(Number(this.value))&&Number(this.value)>=1&&Number(this.value)<=100},
    insertAdjacentHTML(_position,html){register(html)},
    querySelector:selector=>selector==='.sampling-details'?elements.get('sampling-details'):null,
    querySelectorAll:()=>['no-reply','reply','revise-work'].map(key=>elements.get('action-'+key)).filter(Boolean)};
  Object.defineProperty(element,'innerHTML',{get(){return this.html||''},set(html){this.html=html;register(html)}});
  elements.set(id,element);return element;
}
function register(html){
  for(const match of html.matchAll(/<[^>]*\bid="([^"]+)"[^>]*>/g)){
    const element=node(match[1]),value=match[0].match(/\bvalue="([^"]*)"/),action=match[0].match(/\bdata-action="([^"]*)"/);
    if(value)element.value=value[1];if(action)element.dataset.action=action[1];
  }
  if(html.includes('class="sampling-details"'))node('sampling-details');
}
base.forEach(node);
const original={label:'Original',work:{source:'ORIGINAL'}},sample={index:1,decision:'reply',frame:{label:'Sample',work:{source:'SAMPLED'}}};
const state={encounters:[{frames:[{}, {},structuredClone(original)]}],caseIndex:0,step:2};
const categories=[{decision:'no-reply',count:0,proportion:0,interval:null},{decision:'reply',count:1,proportion:1,interval:[0.2,1]},{decision:'revise-work',count:0,proportion:0,interval:null}];
let batches=[],active=null;
const packet=(selected='saved')=>({model:'authored-test-model',input_label:'Executed revision 1, before the saved reaction',
  binding:{input_sha256:'fixed-input'},enabled:true,csrf_token:'local-token',batches:structuredClone(batches),active_batch:active&&structuredClone(active),
  selected_batch:selected,attempts:selected==='saved'?1:batches.find(batch=>batch.id===selected)?.finished||0,
  valid:1,failed:0,categories,samples:[sample]});
const context=vm.createContext({document,state,structuredClone,crypto:require('node:crypto').webcrypto,AbortSignal,
  $:id=>document.getElementById(id),esc:String,current:()=>state.encounters[0],notify:()=>{},
  render:()=>{renderCount++},renderOperationStatus(){},
  setTimeout:callback=>{timers.set(++timerId,callback);return timerId},clearTimeout:id=>timers.delete(id),
  fetch:async(url,options={})=>{
    requests.push({url,options});
    if(options.method==='POST'&&url.endsWith('/cancel')){
      active.cancel_requested=true;if(loseCancel)throw new Error('Lost cancellation response');
      return {ok:true,json:async()=>packet(active.id)};
    }
    if(options.method==='POST'){
      const request=JSON.parse(options.body);
      active={id:'batch-'+(batches.length+1),request_id:request.request_id,status:'running',requested:request.runs,finished:1,valid:1,failed:0,created_at:'2026-09-29T01:00:00Z'};
      batches.push(active);
      if(losePost)throw new Error('Lost start response');
      return new Promise(resolve=>{finishPost=()=>resolve({ok:true,json:async()=>packet(active.id)})});
    }
    if(failRead)throw new Error('Read unavailable');
    const selected=new URL(url,'http://localhost').searchParams.get('batch')||'saved';
    return {ok:true,json:async()=>packet(selected)};
  }});
const tick=async()=>{for(let i=0;i<4;i++)await new Promise(setImmediate)};
const input=value=>{elements.get('sampling-runs').value=value;elements.get('sampling-runs').oninput({target:elements.get('sampling-runs')})};
const submit=()=>elements.get('sampling-setup').onsubmit({preventDefault(){}});
const poll=async()=>{const [id,callback]=timers.entries().next().value;timers.delete(id);await callback();await tick()};
const postCount=()=>requests.filter(request=>request.options.method==='POST').length;
(async()=>{
  vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../apps/next-actions.js'),'utf8'),context);await tick();
  assert.equal(postCount(),0,'Loading and viewing must never generate');
  assert.equal(elements.get('sampling-runs').value,'30');
  for(const invalid of ['', '0','1.5','101']){input(invalid);await submit();assert.equal(postCount(),0)}
  input('1');assert.equal(elements.get('sample-run-button').disabled,false);
  input('100');assert.equal(elements.get('sample-run-button').disabled,false);
  input('2');const starting=submit();await submit();assert.equal(postCount(),1,'Double submit must send only once');
  const sent=requests.find(request=>request.options.method==='POST');
  assert.equal(sent.options.headers['X-Workspace-Token'],'local-token');
  assert.deepEqual({...JSON.parse(sent.options.body),request_id:'id'}, {request_id:'id',runs:2,input_sha256:'fixed-input'});
  finishPost();await starting;
  elements.get('action-reply').onclick();assert.deepEqual(state.encounters[0].frames[2],sample.frame);
  const inputNode=elements.get('sampling-runs');input('17');inputNode.focus();
  const renders=renderCount;active.finished=2;await poll();
  assert.equal(elements.get('sampling-runs'),inputNode);assert.equal(inputNode.value,'17');
  assert.equal(document.activeElement,inputNode,'Polling must keep number input focus');
  assert.equal(renderCount,renders,'Polling must not rerender inspected notebook/chat');
  assert.deepEqual(state.encounters[0].frames[2],sample.frame);
  assert.equal(elements.get('next-actions-count').textContent,'2/2');
  active.status='complete';active=null;await poll();assert.equal(timers.size,0,'Completed batches stop polling');
  failRead=true;elements.get('sampling-batch').onchange({target:{value:'saved'}});await tick();
  assert.deepEqual(state.encounters[0].frames[2],original,'Changing batches must restore original reaction');
  assert.equal(elements.get('action-distribution').innerHTML,'','A failed batch selection must not display the previous batch');
  assert.equal(elements.get('sample-run-button').disabled,true);
  failRead=false;await elements.get('reload-action-data').onclick();
  losePost=true;await submit();await tick();
  assert.equal(postCount(),2,'A lost POST response must reconcile with GET only');
  assert.equal(elements.get('sampling-error').hidden,true,'Matching request ID recovers the accepted batch');
  assert.equal(elements.get('sample-run-button').disabled,true);
  failRead=true;await poll();assert.match(elements.get('sampling-error').textContent,/could not be refreshed/);
  assert.equal(postCount(),2);failRead=false;await poll();
  loseCancel=true;await elements.get('cancel-action-batch').onclick();
  assert.equal(postCount(),3,'Cancellation response loss must not resend');
  assert.match(elements.get('sampling-progress').innerHTML,/Stopping/);
  assert.equal(elements.get('sampling-error').hidden,true);
  active.status='cancelled';active=null;await poll();assert.equal(timers.size,0);
  assert.equal(postCount(),3);
  console.log('Next actions: bounded explicit start, single POST, read-only reconciliation, stable inspection/input, batch restore and cancel pass.');
})().catch(error=>{console.error(error);process.exitCode=1});
