'use strict';
// Saved-session controller over the same HTML shell as the authored design preview.
const $ = id => document.getElementById(id);
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const block = value => `<pre>${esc(typeof value==='string'?value:JSON.stringify(value,null,2))}</pre>`;
const taskText = task => typeof task==='string'?task:Array.isArray(task)&&task.every(cell=>typeof cell?.source==='string')?task.map(cell=>cell.source).join('\n\n'):JSON.stringify(task,null,2);
const state = {encounters:[],caseIndex:0,step:0,mode:'simulate',selected:'step',showInspector:false};
const current = () => state.encounters[state.caseIndex];
const frame = () => current().frames[state.step];
const notify = text => {$('status').textContent=text};
const decisionNames = {'reply':'Student reply','revise-work':'Work edited','request-check':'Local check requested','no-reply':'Student chose no reply'};
const originNames = {authored:'Authored context',source:'Recorded context',generated:'Simulated',supplied:'Supplied intervention',scripted:'Scripted intervention'};
function statusText(f){
  if(f.decisions_remaining===0&&['active','awaiting-tutor'].includes(f.status))return 'Decision budget exhausted · simulation paused';
  return ({active:'Paused · student can continue', 'awaiting-tutor':'Waiting for a tutor reply', 'no-reply':'Student chose no reply',error:'Simulation stopped after an error','environment-error':'Execution unavailable · ungraded','execution-limit':'Execution limit reached · ungraded'})[f.status]||'Saved status: '+f.status;
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
    .map(({c,i})=>`<button class="case-button" data-case="${i}" aria-pressed="${state.caseIndex===i}"><span><b>${esc(c.title)}</b><small>${c.frames.length} saved states</small></span></button>`).join('')||'<p class="empty">No matching tasks.</p>';
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
  let title,body;
  if(key==='work'){
    title='Notebook changes';body=`<p>${f.changes.baseline_kind==='initial-work'?'Initial selected-cell work.':`Net change from the previous saved state, revision ${esc(f.changes.baseline_revision)}. A saved step can contain several decisions.`}</p>`+(f.changes.unified_diff?block(f.changes.unified_diff):'<p>No source change.</p>');
  }else if(key==='feedback'){
    title='Local check result';body=`<p>${esc(checkLabel(f.feedback))}. This is the local checker, not the course autograder. A passing check does not establish learning.</p>`+block(f.feedback);
  }else if(key==='context'){
    title='Supplied run context';body='<h3>Initialization</h3>'+block(current().initialization)+'<div class="divider"></div><h3>Activity</h3>'+block(current().activity)+'<p>Only the selected cell and saved interactions are available. Additional notebook actions and learner traits are unknown.</p>';
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
  document.querySelectorAll('[data-mode]').forEach(b=>{b.disabled=false;b.setAttribute('aria-pressed',String(b.dataset.mode===state.mode))});
  $('case-title').textContent=c.title;
  $('view-description').textContent=`${f.label} · ${statusText(f)}`;
  $('canvas').innerHTML=state.mode==='simulate'?`<div class="split-view">${notebook()}<section aria-label="Student and tutor conversation"><div class="chat-title">Conversation</div>${conversation()}</section></div><p class="note">Saved results only. Moving between states makes no model requests and executes no code. One saved step may contain several student decisions.</p>`:`<div class="inspect-content"><div class="context-box"><h2>Task</h2><p style="white-space:pre-wrap">${esc(taskText(c.task))}</p></div><h2>Conversation at this state</h2>${conversation()}<p class="note">Notebook state and recorded checks are available in Replay. Student silence does not establish learning or abandonment.</p></div>`;
  $('next-step').hidden=state.mode!=='simulate';
  $('next-step').disabled=state.step===c.frames.length-1;
  $('next-step').textContent=$('next-step').disabled?'Latest saved state':'Next saved step';
  $('instructions').disabled=false;
  $('body-grid').classList.toggle('no-inspector',!state.showInspector);
  $('body-grid').classList.toggle('inspector-open',state.showInspector);
  $('inspector-toggle').hidden=!state.showInspector;
  if(state.showInspector)renderInspector();else $('inspector').innerHTML='';
  renderTrail();
  document.querySelectorAll('[data-evidence]').forEach(b=>b.onclick=()=>selectEvidence(b.dataset.evidence));
  if(attr)document.querySelector(`[${attr}="${value}"]`)?.focus({preventScroll:true});
}
async function reloadWorkspace(){
  const previousId=current()?.id;
  state.encounters=[];state.showInspector=false;
  $('reset').disabled=true;$('instructions').disabled=true;$('next-step').hidden=true;$('playback').hidden=true;
  $('inspector-toggle').hidden=true;$('body-grid').classList.toggle('no-inspector',true);$('body-grid').classList.toggle('inspector-open',false);
  $('inspector').innerHTML='';$('cases').innerHTML='';$('case-title').textContent='Loading saved run';$('view-description').textContent='Verifying saved states and linked history…';
  $('canvas').innerHTML='<p class="quiet" role="status">Loading…</p>';
  document.querySelectorAll('[data-mode]').forEach(b=>b.disabled=true);
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
  try{
    const response=await fetch('/api/workspace',{cache:'no-store',signal:controller.signal});
    const packet=await response.json();
    if(!response.ok)throw new Error(packet.detail||'The saved run could not be verified.');
    if(packet.version!==1||!Array.isArray(packet.encounters)||!packet.encounters.length||packet.encounters.some(c=>!Array.isArray(c.frames)||!c.frames.length))throw new Error('Unsupported saved workspace response.');
    state.encounters=packet.encounters;
    const found=state.encounters.findIndex(c=>c.id===previousId);
    state.caseIndex=found>=0?found:state.encounters.length-1;state.step=current().frames.length-1;
    render();notify('Saved run loaded. Viewing only.');
  }catch(error){
    state.encounters=[];$('cases').innerHTML='';$('case-title').textContent='Saved run unavailable';$('view-description').textContent='No saved content is displayed.';
    $('canvas').innerHTML=`<div role="alert"><h2>Could not load saved results</h2><p>${esc(error.name==='AbortError'?'The local backend did not respond in time.':error.message)}</p><p class="quiet">Check that the local workspace server is running, then choose Reload saved run.</p></div>`;
    notify('Saved run unavailable. Reload to try again.');
  }finally{clearTimeout(timeout);$('reset').disabled=false}
}
document.title='Student lab · Saved simulation';
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
$('next-step').onclick=()=>{if(state.step<current().frames.length-1)selectFrame(state.step+1)};
$('inspector-toggle').onclick=()=>{state.showInspector=false;render();(state.selected==='context'?$('instructions'):document.querySelector(`[data-evidence="${state.selected}"]`)||document.querySelector(`[data-mode="${state.mode}"]`))?.focus()};
$('explorer-toggle').onclick=()=>{const shown=$('app').classList.toggle('show-explorer');$('explorer-toggle').setAttribute('aria-expanded',String(shown))};
$('reset').onclick=reloadWorkspace;
const ready=reloadWorkspace();
