'use strict';
// Saved-session controller over the same HTML shell as the authored design preview.
const $ = id => document.getElementById(id);
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const block = value => `<pre>${esc(typeof value==='string'?value:JSON.stringify(value,null,2))}</pre>`;
const taskText = task => typeof task==='string'?task:Array.isArray(task)&&task.every(cell=>typeof cell?.source==='string')?task.map(cell=>cell.source).join('\n\n'):JSON.stringify(task,null,2);
const state = {kind:'notebook',encounters:[],caseIndex:0,step:0,mode:'simulate',selected:'step',showInspector:false,controls:{send_enabled:false},operation:{status:'idle',message:''},policyDraft:null,replyDraft:'',replyMode:'policy',submitting:false,monitoring:false,refreshing:false,clientError:''};
let pollTimer;
const current = () => state.encounters[state.caseIndex];
const frame = () => current().frames[state.step];
const notify = text => {$('status').textContent=text};
const decisionNames = {'reply':'Student reply','revise-work':'Work edited','request-check':'Local check requested','no-reply':'Student chose no reply'};
const missingNotebook='<div class="context-box"><h2>Notebook activity unavailable</h2><p>This scenario contains conversation only. Code pasted into chat is message text; notebook edits, runs and grader outcomes are unknown.</p></div>';
const originNames = {authored:'Authored context',source:'Supplied prefix',generated:'Simulated',supplied:'Supplied intervention',scripted:'Supplied tutor turn'};
function statusText(f){
  if(f.decisions_remaining===0&&['active','ready','awaiting-tutor'].includes(f.status))return 'Decision budget exhausted · simulation paused';
  return ({active:'Paused · student can continue', ready:'Paused · student can continue', 'awaiting-tutor':'Waiting for a tutor reply', 'no-reply':'Student chose no reply',error:'Simulation stopped after an error','environment-error':'Execution unavailable · ungraded','execution-limit':'Execution limit reached · ungraded'})[f.status]||'Saved status: '+f.status;
}
function turns(){
  const f=frame();
  return [...f.dialogue,...(f.pending_message!==null?[{role:'student',origin:'generated',text:f.pending_message,pending:true}]:[])];
}
function selectMode(mode){state.mode=mode;state.showInspector=false;render()}
function selectFrame(index){state.step=index;state.selected='step';render();notify(frame().label)}
function selectCase(index){state.caseIndex=index;state.step=current().frames.length-1;state.showInspector=false;state.selected='step';render();notify('Opened '+current().title)}
function selectEvidence(key){state.selected=key;state.showInspector=true;render();if(!window.matchMedia('(min-width:1001px)').matches)$('inspector-toggle').focus()}
function renderCases(){
  const query=$('search').value.toLowerCase();
  $('cases').innerHTML=state.encounters.map((c,i)=>({c,i})).filter(({c})=>(c.title+' '+taskText(c.task)).toLowerCase().includes(query))
    .map(({c,i})=>`<button class="case-button" data-case="${i}" aria-pressed="${state.caseIndex===i}"><span><b>${esc(c.title)}</b><small>${c.frames.length} saved state${c.frames.length===1?'':'s'}</small></span></button>`).join('')||'<p class="empty">No matching '+(state.kind==='chat'?'conversation':'tasks')+'.</p>';
  document.querySelectorAll('[data-case]').forEach(b=>b.onclick=()=>selectCase(Number(b.dataset.case)));
}
function conversation(){
  const rows=turns();
  return rows.length?rows.map((turn,i)=>`<article class="chat-turn"><header>${esc(turn.role==='student'?'Student':'Tutor')} <span class="muted small">${esc(originNames[turn.origin]||(turn.origin?'Saved context':'Supplied context · origin unspecified'))}${turn.pending?' · awaiting reply':''}</span></header><p style="white-space:pre-wrap">${esc(turn.text)}</p><button data-evidence="turn:${i}">Inspect source</button></article>`).join(''):'<p class="quiet">No chat message at this saved state.</p>';
}
function checkLabel(feedback){
  if(!feedback)return 'No check feedback for this revision.';
  return feedback.status==='checked'?(feedback.success?'Passed':'Failed')+' · local check':({
    'runtime-error':'Execution error · ungraded','environment-error':'Execution unavailable · ungraded','execution-limit':'Execution limit reached · ungraded'
  }[feedback.status]||'Saved check feedback');
}
function notebook(){
  const f=frame();
  return `<section class="notebook" aria-label="Saved notebook work"><div class="pane-title">Selected cell ${esc(f.work.cell_index)}<span class="spacer"></span><span class="muted small">Read only</span></div><div class="task"><b>Exercise</b><p style="white-space:pre-wrap">${esc(taskText(current().task))}</p></div><div class="cell"><div class="cell-head"><span>Python · revision ${esc(f.work.revision)}</span><button class="text-action" data-evidence="work">View changes</button></div>${f.work.source.split('\n').map((line,i)=>`<div class="code-line"><span class="line-number">${i+1}</span><code>${esc(line)}</code></div>`).join('')}</div><div class="output"${f.feedback?.success!==true?' style="background:var(--ground);color:var(--muted)"':''}><b>${esc(checkLabel(f.feedback))}</b>${f.feedback?`<br><button class="text-action" data-evidence="feedback">Inspect check result</button>`:''}</div></section>`;
}
function renderInspector(){
  const f=frame(),key=state.selected;
  if(key==='controls'){renderControls();return}
  let title,body;
  if(key==='work'){
    title='Notebook changes';body=`<p>${f.changes.baseline_kind==='initial-work'?'Initial selected-cell work.':`Net change from the previous saved state, revision ${esc(f.changes.baseline_revision)}. A saved step can contain several decisions.`}</p>`+(f.changes.unified_diff?block(f.changes.unified_diff):'<p>No source change.</p>');
  }else if(key==='feedback'){
    title='Local check result';body=`<p>${esc(checkLabel(f.feedback))}. This is the local checker, not the course autograder. A passing check does not establish learning.</p>`+block(f.feedback);
  }else if(key==='context'){
    title='Supplied run context';body='<h3>Initialization</h3>'+block(current().initialization)+(state.kind==='chat'?'<p>Only the supplied conversation and saved continuations are available. No notebook activity or learner traits are reconstructed.</p>':'<div class="divider"></div><h3>Activity</h3>'+block(current().activity)+'<p>Only the selected cell and saved interactions are available. Additional notebook actions and learner traits are unknown.</p>');
  }else if(key.startsWith('turn:')){
    const turn=turns()[Number(key.split(':')[1])];
    title='Conversation source';body=`<p>${turn.origin?'Saved origin: '+esc(turn.origin):'Origin not specified in the saved record'}${turn.pending?' · pending tutor reply':''}.</p>`+block(turn.text)+'<p>The saved origin identifies how the runner stored this message; it does not by itself prove a fresh provider request.</p>';
  }else{
    title=f.label;body=`<p>${esc(statusText(f))}. ${esc(f.decisions_remaining)} decisions remaining.</p><div class="divider"></div><h3>Decisions in this saved step</h3>`+(f.actions.length?f.actions.map(a=>`<p><b>${esc(decisionNames[a.decision]||a.decision)}</b></p>${a.text?block(a.text):''}${a.source!==null?block(a.source):''}`).join(''):'<p>No student decision recorded in this state.</p>')+'<div class="divider"></div><details><summary>Saved state identifiers</summary>'+block(f.binding)+'</details>';
  }
  $('inspector').innerHTML=`<div class="inspector-title">Saved evidence</div><h2>${esc(title)}</h2>${body}`;
}
function renderTrail(){
  $('playback').hidden=state.mode!=='simulate';
  $('playback').setAttribute('aria-label',state.kind==='chat'?'Conversation playback':'Notebook playback');
  $('trail-title').textContent='Saved playback';
  $('trail-hint').textContent=`State ${state.step+1} of ${current().frames.length} · no new generation`;
  $('trail').innerHTML=current().frames.map((f,i)=>`<button data-trail="${i}" aria-pressed="${i===state.step}"><span class="count">${i+1}</span>${esc(f.label)}</button>`).join('');
  document.querySelectorAll('[data-trail]').forEach(b=>b.onclick=()=>selectFrame(Number(b.dataset.trail)));
}
function render(){
  const focused=document.activeElement;
  const attr=['data-case','data-trail','data-evidence'].find(a=>focused?.hasAttribute(a));
  const value=attr?focused.getAttribute(attr):null;
  const c=current(),f=frame();
  renderCases();
  document.querySelector('.breadcrumb').textContent=state.kind==='chat'?'Conversation simulation':'Notebook simulation';
  document.querySelector('.explorer-heading').textContent=state.kind==='chat'?'Conversation':'Tasks';
  $('search').placeholder=state.kind==='chat'?'Filter conversation…':'Filter tasks…';
  $('search').setAttribute('aria-label',state.kind==='chat'?'Filter saved conversation':'Filter saved tasks');
  document.querySelector('label[for="search"]').textContent=state.kind==='chat'?'Filter saved conversation':'Filter saved tasks';
  document.querySelectorAll('[data-mode]').forEach(b=>{b.disabled=false;b.setAttribute('aria-pressed',String(b.dataset.mode===state.mode))});
  $('case-title').textContent=c.title;
  $('view-description').textContent=`${f.label} · ${statusText(f)}`;
  $('canvas').innerHTML=state.kind==='chat'?`<div class="inspect-content">${missingNotebook}<section aria-label="Student and tutor conversation"><h2>Conversation at this state</h2>${conversation()}</section><p class="note">Playback reads saved messages only. It makes no model requests. A no-reply decision does not establish learning or abandonment.</p></div>`:state.mode==='simulate'?`<div class="split-view">${notebook()}<section aria-label="Student and tutor conversation"><div class="chat-title">Conversation</div>${conversation()}</section></div><p class="note">Saved results only. Moving between states makes no model requests and executes no code. One saved step may contain several student decisions.</p>`:`<div class="inspect-content"><div class="context-box"><h2>Task</h2><p style="white-space:pre-wrap">${esc(taskText(c.task))}</p></div><h2>Conversation at this state</h2>${conversation()}<p class="note">Notebook state and recorded checks are available in Replay. Student silence does not establish learning or abandonment.</p></div>`;
  $('next-step').hidden=state.mode!=='simulate';
  $('next-step').disabled=state.step===c.frames.length-1;
  $('next-step').textContent=$('next-step').disabled?'Latest saved state':'Next saved step';
  $('instructions').disabled=false;$('tutor-controls').disabled=false;
  $('body-grid').classList.toggle('no-inspector',!state.showInspector);
  $('body-grid').classList.toggle('inspector-open',state.showInspector);
  $('inspector-toggle').hidden=!state.showInspector;
  if(state.showInspector)renderInspector();else $('inspector').innerHTML='';
  renderTrail();renderOperationStatus();
  document.querySelectorAll('[data-evidence]').forEach(b=>b.onclick=()=>selectEvidence(b.dataset.evidence));
  if(attr)document.querySelector(`[${attr}="${value}"]`)?.focus({preventScroll:true});
}
function continuationReason(){
  if(!state.encounters.length)return 'Load a saved session first.';
  if(!state.controls.send_enabled)return 'Sending is disabled in this workspace.';
  if(state.submitting||state.monitoring||state.refreshing)return 'Waiting for the current request.';
  if(state.caseIndex!==state.encounters.length-1||state.step!==current().frames.length-1)return 'Select the latest saved state to continue.';
  if(state.controls.blocked_reason)return state.controls.blocked_reason;
  if(!['active','ready','awaiting-tutor'].includes(frame().status))return 'This encounter has stopped. Its saved results remain available.';
  if(frame().decisions_remaining<=0)return 'The decision budget is exhausted.';
  return '';
}
function canSubmit(){
  return !continuationReason()&&(['active','ready'].includes(frame().status)||Boolean((state.replyMode==='policy'?state.policyDraft:state.replyDraft)?.trim()));
}
function submitLabel(){
  return frame().status==='awaiting-tutor'?(state.replyMode==='policy'?'Generate tutor reply + one decision':'Send reply + one decision'):'Continue one student decision';
}
function updateSubmitButton(){
  if(state.showInspector&&state.selected==='controls'){
    $('continuation-reason').textContent=continuationReason();$('submit-operation').disabled=!canSubmit();$('submit-operation').textContent=state.submitting||state.monitoring?'Request running…':submitLabel();
  }
}
function renderControls(){
  const waiting=frame().status==='awaiting-tutor';
  const manual=waiting&&state.replyMode==='reply';
  $('inspector').innerHTML=`<div class="inspector-title">Tutor and student controls</div><h2>${waiting?'Reply to the student':'Continue the student'}</h2><p>${waiting?'The reply will be followed by one student decision.':'Continue one decision using the current '+(state.kind==='chat'?'conversation':'task and conversation')+'. Tutor instructions are used only when replying to a student message.'}</p>${waiting?'<label for="tutor-mode">Reply mode</label><select id="tutor-mode"><option value="policy">Generate from instructions</option><option value="reply">Write a reply</option></select>':''}<div${manual?' hidden':''}><label for="policy">Tutor instructions</label><textarea id="policy" maxlength="64000">${esc(state.policyDraft||'')}</textarea></div><div${manual?'':' hidden'}><label for="manual-reply">Your tutor reply</label><textarea id="manual-reply" maxlength="64000">${esc(state.replyDraft)}</textarea></div><p class="draft-status">Drafts stay in this page. Reload saved run preserves them; refreshing the browser resets them.</p>${state.controls.reference?`<p>Configured tutor reference: ${esc(state.controls.reference.library)} ${esc(state.controls.reference.library_version)}. Used only for generated tutor replies.</p>`:''}<div class="divider"></div><p id="continuation-reason">${esc(continuationReason())}</p><button class="primary" id="submit-operation">${esc(submitLabel())}</button><p class="tiny" style="margin-top:12px">${state.controls.send_enabled?(state.kind==='chat'?'Sends the visible conversation to Gemini. This mode cannot execute notebook code. Playback sends nothing.':'Sends the visible task, work and conversation to Gemini. A local check runs only if the student requests it. Playback sends nothing.'):'Viewing only. No request can be sent from this workspace.'}</p>`;
  $('policy').oninput=e=>{state.policyDraft=e.target.value;updateSubmitButton()};
  $('manual-reply').oninput=e=>{state.replyDraft=e.target.value;updateSubmitButton()};
  if(waiting){$('tutor-mode').value=state.replyMode;$('tutor-mode').onchange=e=>{state.replyMode=e.target.value;renderControls();$('tutor-mode').focus()}}
  $('submit-operation').onclick=submitOperation;updateSubmitButton();
}
function renderOperationStatus(){
  const message=state.submitting||state.monitoring?'Request running'+(state.encounters.length?' · showing the last saved state.':'.')+' Reloading checks progress without resending.':state.clientError||state.controls.blocked_reason||state.operation.message||'';
  $('operation-status').textContent=message;$('operation-status').hidden=!message;
  document.querySelector('.prototype-note').textContent=state.submitting||state.monitoring?'Simulation · Request running':state.controls.send_enabled?'Simulation · Sending enabled':'Saved simulation · Read only';
  updateSubmitButton();
}
function applyWorkspace(packet){
  if(!['chat','notebook'].includes(packet.kind||'notebook')||packet.version!==1||!Array.isArray(packet.encounters)||!packet.encounters.length||packet.encounters.some(c=>!Array.isArray(c.frames)||!c.frames.length))throw new Error('Unsupported saved workspace response.');
  const previousId=current()?.id;
  state.kind=packet.kind||'notebook';state.encounters=packet.encounters;state.controls=packet.controls||{send_enabled:false};state.operation=packet.operation||{status:'idle',message:''};state.monitoring=false;
  if(state.policyDraft===null)state.policyDraft=state.controls.policy||'';
  const found=state.encounters.findIndex(c=>c.id===previousId);
  state.caseIndex=found>=0?found:state.encounters.length-1;state.step=current().frames.length-1;
  clearTimeout(pollTimer);render();
}
function clearWorkspaceView(message){
  state.encounters=[];state.showInspector=false;$('cases').innerHTML='';$('inspector').innerHTML='';$('playback').hidden=true;
  $('instructions').disabled=true;$('tutor-controls').disabled=true;$('next-step').hidden=true;$('inspector-toggle').hidden=true;
  $('body-grid').classList.toggle('no-inspector',true);$('body-grid').classList.toggle('inspector-open',false);
  document.querySelectorAll('[data-mode]').forEach(b=>b.disabled=true);
  $('canvas').innerHTML=message;
}
async function reloadWorkspace(){
  if(state.refreshing)return;
  clearTimeout(pollTimer);state.refreshing=true;$('reset').disabled=true;updateSubmitButton();
  if(!state.encounters.length){clearWorkspaceView('<p class="quiet" role="status">Loading saved evidence…</p>');$('case-title').textContent='Loading saved run';$('view-description').textContent='Verifying saved states and linked history…'}
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
  try{
    const response=await fetch('/api/workspace',{cache:'no-store',signal:controller.signal});
    const packet=await response.json();
    if(response.status===202){
      state.monitoring=true;renderOperationStatus();notify('Request running; checking saved status without resending.');
      if(!state.encounters.length){$('case-title').textContent='Request running';$('view-description').textContent='Waiting for the next saved state. No request will be resent.'}
      pollTimer=setTimeout(()=>reloadWorkspace(),1500);return;
    }
    if(!response.ok)throw new Error(typeof packet.detail==='string'?packet.detail:'The saved run could not be verified.');
    applyWorkspace(packet);notify('Saved run loaded.');
  }catch(error){
    state.monitoring=false;$('case-title').textContent='Saved run unavailable';$('view-description').textContent='No saved content is displayed.';
    clearWorkspaceView(`<div role="alert"><h2>Could not load saved results</h2><p>${esc(error.name==='AbortError'?'The local backend did not respond in time.':error.message)}</p><p class="quiet">Reload saved run to check again. An in-progress request may still finish; nothing will be resent.</p></div>`);
    notify('Saved run unavailable. Reload to check its status.');
  }finally{clearTimeout(timeout);state.refreshing=false;$('reset').disabled=false;renderOperationStatus()}
}
async function submitOperation(){
  if(!canSubmit())return;
  const mode=['active','ready'].includes(frame().status)?'advance':state.replyMode;
  const payload={binding:{...frame().binding},mode,...(mode==='advance'?{}:{text:mode==='policy'?state.policyDraft:state.replyDraft})};
  state.submitting=true;state.clientError='';renderOperationStatus();
  try{
    // No timeout/retry: aborting an HTTP request would not cancel a saved backend operation.
    const response=await fetch('/api/continue',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const packet=await response.json();
    if(!response.ok)throw new Error(typeof packet.detail==='string'?packet.detail:'The request was rejected. Reload the saved run before trying again.');
    state.showInspector=false;state.mode='simulate';state.selected='step';
    applyWorkspace(packet);
    if(frame().actions.some(action=>action.text))document.querySelector('.chat-turn:last-child')?.scrollIntoView({block:'nearest'});
    else $('canvas').scrollTop=0;
    notify(state.operation.message||'New result saved.');
  }catch(error){
    state.clientError=error.message||'Request outcome is unknown. Checking saved status; it will not be resent.';
    await reloadWorkspace();
  }finally{state.submitting=false;renderOperationStatus()}
}
document.title='Student lab · Simulation workspace';
$('instructions').insertAdjacentHTML('beforebegin','<button id="tutor-controls">Tutor controls</button>');
$('canvas').insertAdjacentHTML('beforebegin','<div id="operation-status" role="status" aria-live="polite" style="padding:12px 36px;border-bottom:1px solid var(--line);font-size:12px" hidden></div>');
document.querySelector('.prototype-note').textContent='Saved simulation · Read only';
document.querySelector('.breadcrumb').textContent='Notebook simulation';
document.querySelector('.explorer-heading').textContent='Tasks';
document.querySelector('.reset-label').textContent='Reload saved run';
$('reset').title='Reload saved run without generating or executing';
$('search').placeholder='Filter tasks…';$('search').setAttribute('aria-label','Filter saved tasks');
$('instructions').textContent='Run context';
$('inspector-toggle').textContent='Close details';
document.querySelectorAll('[data-mode]').forEach(b=>{if(b.dataset.mode==='compare')b.hidden=true;if(b.dataset.mode==='simulate')b.textContent='Replay';b.onclick=()=>selectMode(b.dataset.mode)});
$('search').oninput=()=>{if(state.encounters.length)renderCases()};
$('instructions').onclick=()=>selectEvidence('context');
$('tutor-controls').onclick=()=>selectEvidence('controls');
$('next-step').onclick=()=>{if(state.step<current().frames.length-1)selectFrame(state.step+1)};
$('inspector-toggle').onclick=()=>{state.showInspector=false;render();(state.selected==='context'?$('instructions'):state.selected==='controls'?$('tutor-controls'):document.querySelector(`[data-evidence="${state.selected}"]`)||document.querySelector(`[data-mode="${state.mode}"]`))?.focus()};
$('explorer-toggle').onclick=()=>{const shown=$('app').classList.toggle('show-explorer');$('explorer-toggle').setAttribute('aria-expanded',String(shown))};
$('reset').onclick=reloadWorkspace;
const ready=reloadWorkspace();
