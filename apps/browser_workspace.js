'use strict';
// Saved-session controller over the same HTML shell as the authored design preview.
const $ = id => document.getElementById(id);
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const block = value => `<pre>${esc(typeof value==='string'?value:JSON.stringify(value,null,2))}</pre>`;
const taskText = task => typeof task==='string'?task:Array.isArray(task)&&task.every(cell=>typeof cell?.source==='string')?task.map(cell=>cell.source).join('\n\n'):JSON.stringify(task,null,2);
const state = {kind:'notebook',scenarios:null,scenarioId:null,encounters:[],caseIndex:0,step:0,mode:'simulate',selected:'step',showInspector:false,controls:{send_enabled:false},operation:{status:'idle',message:''},policyDraft:null,replyDraft:'',replyMode:'policy',submitting:false,monitoring:false,refreshing:false,clientError:''};
Object.assign(state,{comparisonAvailable:false,policyWorkspaceAvailable:false,fidelityComparisonAvailable:false,replayAvailable:true,comparison:null,reviewIndex:0,comparisonLoading:false,comparisonError:'',comparisonEntryNote:'',chatOpen:true,chatKey:null});
Object.assign(state,{workspaceId:null,comparisonDraft:null,comparisonDirty:false,draftStored:false,comparisonEditing:false,comparisonSubmitting:false,comparisonMonitoring:false,comparisonOperation:{status:'idle',message:''}});
let pollTimer,comparisonPollTimer;
const current = () => state.encounters[state.caseIndex];
const frame = () => current().frames[state.step];
const notify = text => {$('status').textContent=text};
const decisionNames = {'reply':'Student reply','revise-work':'Work edited','request-check':'Local check requested','no-reply':'Student chose no reply'};
const isPolicyComparison = () => state.comparison?.kind==='saved-policy-comparison';
const isFidelityComparison = () => state.comparison?.kind==='saved-student-fidelity-comparison';
const comparisonBusy = () => state.comparisonLoading||state.comparisonSubmitting||state.comparisonMonitoring;
const comparisonContext = () => state.comparisonEditing?state.comparison?.controls?.sources?.find(s=>s.id===state.comparisonDraft?.source_id):state.comparison?.cases[state.reviewIndex];
const excerpt = (text,limit=90) => {const value=String(text||'').replace(/\s+/g,' ').trim();return value.length>limit?value.slice(0,limit)+'…':value};
const questionSummary = c => c.summary||excerpt(c.prefix?.turns?.at(-1)?.text);
const draftKey = () => state.workspaceId?'student-lab:policy-draft:'+state.workspaceId:null;
function persistComparisonDraft(){
  state.comparisonDirty=true;state.draftStored=false;
  try{if(draftKey()){window.sessionStorage.setItem(draftKey(),JSON.stringify(state.comparisonDraft));state.draftStored=true}}catch{}
}
function restoreComparisonDraft(){
  if(!draftKey())return;
  try{
    const value=JSON.parse(window.sessionStorage.getItem(draftKey()));
    if(!value||typeof value.source_id!=='string'||value.source_id.length>128||
       !['current_policy','proposed_policy'].every(key=>typeof value[key]==='string'&&value[key].length<=64000)||
       value.source_id&&!['session_sha256','state_sha256'].every(key=>typeof value.binding?.[key]==='string'&&value.binding[key].length<=128))return;
    state.comparisonDraft={source_id:value.source_id,binding:value.binding?{session_sha256:value.binding.session_sha256,state_sha256:value.binding.state_sha256}:undefined,current_policy:value.current_policy,proposed_policy:value.proposed_policy};
    state.comparisonDirty=true;state.draftStored=true;state.comparisonEntryNote='Your unsaved draft was restored in this tab. Verify its starting conversation before saving.';
  }catch{}
}
function clearComparisonDraft(){
  try{if(draftKey())window.sessionStorage.removeItem(draftKey())}catch{}
  state.comparisonDraft=null;state.comparisonDirty=false;state.draftStored=false;state.comparisonEntryNote='';
}
function discardComparisonDraft(){
  if(comparisonBusy())return;
  clearComparisonDraft();
  if(state.comparisonEditing)newComparison();else render();
  notify('Draft discarded. Saved comparisons are unchanged.');
}
const originNames = {authored:'Authored context',source:'Starting conversation',generated:'Simulated',supplied:'Supplied intervention',scripted:'Added tutor reply'};
function statusText(f){
  if(f.decisions_remaining===0&&['active','ready','awaiting-tutor'].includes(f.status))return 'Decision budget exhausted · simulation paused';
  return ({active:'Paused · student can continue', ready:'Paused · student can continue', 'awaiting-tutor':'Awaiting a tutor reply at this point', 'no-reply':'Student chose no reply',error:'Simulation stopped after an error','environment-error':'Execution unavailable · ungraded','execution-limit':'Execution limit reached · ungraded'})[f.status]||'Saved status: '+f.status;
}
function turns(){
  if(state.mode==='compare'){
    const c=comparisonContext();
    return c?[...c.prefix.context,...c.prefix.turns].map(t=>({...t,origin:t.origin||'source'})):[];
  }
  const f=frame();
  return [...f.dialogue,...(f.pending_message!==null?[{role:'student',origin:'generated',text:f.pending_message,pending:true}]:[])];
}
function selectMode(mode){
  if(state.submitting||state.monitoring||state.refreshing||comparisonBusy()||mode==='compare'&&!state.comparisonAvailable)return;
  mode=mode==='inspect'?'simulate':mode;
  if(mode==='simulate'&&!state.replayAvailable)return;
  state.mode=mode;state.showInspector=false;$('search').value='';$('run-details').open=false;
  const url=new URL(window.location.href);url.searchParams.set('view',mode==='compare'?'compare':'replay');window.history.replaceState(null,'',url);
  if(mode==='compare')return reloadComparison();
  if(state.encounters.length)render();else return reloadWorkspace();
}
function renderModeButtons(){
  document.querySelectorAll('[data-mode]').forEach(b=>{
    if(b.dataset.mode==='simulate')b.textContent=state.kind==='chat'?'Conversation':'Notebook';
    if(b.dataset.mode==='compare')b.textContent=state.fidelityComparisonAvailable||isFidelityComparison()?'Student fidelity':state.policyWorkspaceAvailable||isPolicyComparison()?'Tutor policies':state.comparison?.kind==='saved-communication-comparison'?'Reviewed replies':'Compare';
    b.hidden=b.dataset.mode==='inspect'||b.dataset.mode==='compare'&&!state.comparisonAvailable||b.dataset.mode==='simulate'&&!state.replayAvailable;
    b.disabled=state.submitting||state.monitoring||state.refreshing||comparisonBusy()||(!state.encounters.length&&state.mode!=='compare'&&b.dataset.mode!=='compare');
    b.setAttribute('aria-pressed',String(b.dataset.mode===state.mode));
  });
}
function selectFrame(index){state.step=index;state.selected='step';state.showInspector=false;render();notify(frame().label)}
function selectCase(index){state.caseIndex=index;state.step=current().frames.length-1;state.showInspector=false;state.selected='step';render();notify('Opened '+current().title)}
const workspaceUrl = endpoint => state.scenarios?.length?endpoint+'?scenario='+encodeURIComponent(state.scenarioId):endpoint;
async function selectScenario(id){
  if(state.refreshing||state.submitting||state.monitoring||!state.scenarios?.some(s=>s.id===id))return;
  if(id===state.scenarioId&&state.encounters.length)return;
  const focused=document.activeElement,restoreFocus=focused?.dataset.scenario===id;
  state.scenarioId=id;state.policyDraft=null;state.replyDraft='';state.replyMode='policy';state.clientError='';
  state.controls={send_enabled:false};state.operation={status:'idle',message:''};state.selected='step';
  const url=new URL(window.location.href);url.searchParams.set('scenario',id);window.history.replaceState(null,'',url);
  clearWorkspaceView('<p class="quiet">Loading selected conversation…</p>');
  $('canvas').scrollTop=0;
  await reloadWorkspace();
  if(restoreFocus&&(document.activeElement===document.body||document.activeElement===focused))
    [...document.querySelectorAll('[data-scenario]')].find(b=>b.dataset.scenario===id)?.focus({preventScroll:true});
}
function selectEvidence(key){state.selected=key;state.showInspector=true;$('run-details').open=false;render();$('inspector-toggle').focus()}
function renderCases(){
  const query=$('search').value.toLowerCase();
  if(state.mode==='compare'){
    document.querySelector('.breadcrumb').textContent=state.fidelityComparisonAvailable||isFidelityComparison()?'Student fidelity':state.policyWorkspaceAvailable||isPolicyComparison()?'Tutor policies':'Reviewed replies';
    document.querySelector('.explorer-heading').textContent=isFidelityComparison()?'Fidelity cases':isPolicyComparison()?'Saved comparisons':'Reviewed cases';
    $('conversation-guide').hidden=true;
    const label=isPolicyComparison()?'Filter policy comparisons':'Filter reviewed cases';
    $('search').placeholder=label+'…';$('search').setAttribute('aria-label',label);
    document.querySelector('label[for="search"]').textContent=label;
    $('cases').innerHTML=(state.comparison?.cases||[]).map((c,i)=>({c,i})).filter(({c})=>[c.title,questionSummary(c),c.source?.title,...(c.conditions||[]).map(condition=>condition.policy)].join(' ').toLowerCase().includes(query)).map(({c,i})=>
      `<button class="case-button" data-review-case="${i}" aria-pressed="${!state.comparisonEditing&&state.reviewIndex===i}"><span><b>${esc(c.title)}</b>${isFidelityComparison()?`<span class="case-summary">${esc(questionSummary(c))}</span><small>Recorded + 8 saved draws</small>`:isPolicyComparison()?`<span class="case-summary">${esc(questionSummary(c))}</span><small>${esc(c.source?.title||'Saved starting conversation')} · ${policyStatus(c)}</small><span class="case-summary">${c.conditions.map(condition=>`${esc(condition.id.toUpperCase())}: ${esc(excerpt(condition.policy,55))}`).join(' · ')}</span>`:'<small>Recorded + 2 simulated replies</small>'}</span></button>`).join('')||'<p class="empty">'+(query?'No matching comparisons.':state.comparison?'Your saved comparisons will appear here.':'No comparison loaded.')+'</p>';
    document.querySelectorAll('[data-review-case]').forEach(b=>{b.disabled=comparisonBusy();b.onclick=()=>{if(comparisonBusy())return;state.reviewIndex=Number(b.dataset.reviewCase);state.comparisonEditing=false;state.showInspector=false;render();$('canvas').scrollTop=0;notify('Opened '+state.comparison.cases[state.reviewIndex].title)}});
    return;
  }
  document.querySelector('.breadcrumb').textContent=state.kind==='chat'?'Conversation simulation':'Notebook simulation';
  document.querySelector('.explorer-heading').textContent=state.scenarios?.length?'Conversations':state.kind==='chat'?'Conversation':'Tasks';
  $('conversation-guide').hidden=!state.scenarios?.length;
  const label=state.scenarios?.length?'Filter saved conversations':state.kind==='chat'?'Filter saved conversation':'Filter saved tasks';
  $('search').placeholder=state.scenarios?.length?'Filter conversations…':state.kind==='chat'?'Filter conversation…':'Filter tasks…';
  $('search').setAttribute('aria-label',label);document.querySelector('label[for="search"]').textContent=label;
  if(state.scenarios?.length){
    $('cases').innerHTML=state.scenarios.filter(s=>(s.title+' '+(s.summary||'')).toLowerCase().includes(query)).map(s=>
      `<button class="case-button" data-scenario="${esc(s.id)}" aria-pressed="${state.scenarioId===s.id}"><span><b>${esc(s.title)}</b>${s.summary?`<span class="case-summary">${esc(s.summary)}</span>`:''}<small>${s.id===state.scenarioId&&current()?(current().frames.length===1?'Starting conversation only':(current().frames.length-1)+' saved result'+(current().frames.length===2?'':'s')):'Saved conversation'}</small></span></button>`).join('')||'<p class="empty">No matching conversations.</p>';
    document.querySelectorAll('[data-scenario]').forEach(b=>{b.disabled=state.refreshing||state.submitting||state.monitoring;b.onclick=()=>selectScenario(b.dataset.scenario)});
    return;
  }
  $('cases').innerHTML=state.encounters.map((c,i)=>({c,i})).filter(({c})=>(c.title+' '+taskText(c.task)).toLowerCase().includes(query))
    .map(({c,i})=>`<button class="case-button" data-case="${i}" aria-pressed="${state.caseIndex===i}"><span><b>${esc(c.title)}</b><small>${c.frames.length} saved state${c.frames.length===1?'':'s'}</small></span></button>`).join('')||'<p class="empty">No matching '+(state.kind==='chat'?'conversation':'tasks')+'.</p>';
  document.querySelectorAll('[data-case]').forEach(b=>b.onclick=()=>selectCase(Number(b.dataset.case)));
}
function pendingReplyNote(){
  if(state.step<current().frames.length-1)return 'This saved result ends before a tutor reply. Use Next to see later saved activity.';
  const next=state.submitting||state.monitoring?'A request is running; this is the last saved conversation.':
    state.controls.blocked_reason?'Open Saved results to inspect the saved request.':
    frame().decisions_remaining===0?'This run has reached its decision limit.':
    state.controls.send_enabled?'Use Reply to student to continue.':'This workspace is a saved replay; replies do not run automatically.';
  return 'No tutor reply follows this student message in the saved conversation. '+next;
}
function conversation(rows=turns(),offset=0){
  const simulationStart=state.kind==='chat'&&state.mode!=='compare'?rows.findIndex(t=>t.origin==='generated'):-1;
  return rows.length?rows.map((turn,i)=>`${i===simulationStart?'<h3 class="chat-section-label">Simulated continuation begins</h3>':''}${i>0&&turn.role==='student'&&turn.origin==='source'&&rows[i-1].role==='student'&&rows[i-1].origin==='source'?'<p class="chat-gap">No tutor message is recorded between these supplied student messages.</p>':''}<article class="chat-turn ${turn.role==='student'?'student':'tutor'}${state.showInspector&&state.selected==='turn:'+(i+offset)?' selected':''}" tabindex="-1" aria-label="Message ${i+offset+1}, ${turn.role==='student'?'Student':'Tutor'}"><header><span class="avatar ${turn.role==='tutor'?'tutor':''}" aria-hidden="true">${turn.role==='student'?'S':'T'}</span><div class="chat-identity"><b>${turn.role==='student'?'Student':'Tutor'}</b><span class="muted small">${esc(originNames[turn.origin]||(turn.origin?'Saved context':'Supplied context · origin unspecified'))}${turn.pending?' · awaiting reply':''}</span></div><button class="source-inspect" data-evidence="turn:${i+offset}" aria-label="Inspect source of message ${i+offset+1}" aria-pressed="${state.showInspector&&state.selected==='turn:'+(i+offset)}">Source</button></header><div class="message-body">${turn.role==='tutor'&&typeof turn.display_html==='string'?turn.display_html:`<p class="literal-message">${esc(turn.text)}</p>`}</div>${turn.pending?`<p class="reply-note">${esc(pendingReplyNote())}</p>`:''}</article>`).join(''):'<p class="quiet">No chat message at this saved state.</p>';
}
function renderChat(){
  const comparing=state.mode==='compare',c=comparisonContext();
  const available=comparing?Boolean(c):Boolean(state.encounters.length);
  const chatOnly=state.kind==='chat'&&!comparing,primaryChat=chatOnly&&available&&!state.showInspector;
  const visibleChat=chatOnly?available:state.chatOpen;
  const panel=$('conversation-panel'),parent=primaryChat?document.querySelector('.main'):$('body-grid');
  if(panel.parentElement!==parent){if(primaryChat)$('inspector').before(panel);else parent.append(panel)}
  panel.hidden=!visibleChat;
  $('chat-toggle').hidden=chatOnly;
  $('body-grid').classList.toggle('chat-primary',primaryChat);
  $('body-grid').classList.toggle('no-chat',!visibleChat);
  $('chat-toggle').textContent=state.chatOpen?'Hide chat':'Show chat';
  $('chat-toggle').setAttribute('aria-expanded',String(state.chatOpen));
  $('chat-title').textContent=isFidelityComparison()&&comparing?'Recorded conversation':comparing?'Shared conversation':'Student–tutor chat';
  $('chat-caption').textContent=comparing?(c?`${c.source?.title||c.title} · ${isFidelityComparison()?'before the next reply':'shared starting point'}`:'No saved context loaded'):available?`${current().title} · ${frame().label}`:'No saved conversation loaded';
  const key=comparing?'compare:'+state.comparisonEditing+':'+c?.id:`${state.scenarioId}:${current()?.id}:${state.step}`;
  const changed=state.chatKey!==key;
  if(visibleChat)state.chatKey=key;
  const rows=available?turns():[];
  $('chat-count').textContent=rows.length+' message'+(rows.length===1?'':'s');
  document.querySelectorAll('[data-chat-jump]').forEach(b=>b.disabled=rows.length<2);
  if(!available){$('conversation-messages').innerHTML='<p class="quiet">'+(state.comparisonLoading||state.refreshing||state.monitoring?'Loading saved conversation…':'No verified conversation to display.')+'</p>';return}
  const messages=$('conversation-messages'),previousScroll=messages.scrollTop;
  messages.innerHTML=comparing?`<p class="quiet chat-context-note">${esc(c.context_status)}</p><h3 class="chat-section-label">${isFidelityComparison()?'Earlier dialogue · history condition only':'Earlier messages supplied'}</h3>${c.prefix.context.length?conversation(rows.slice(0,c.prefix.context.length)):'<p class="quiet">No earlier messages supplied.</p>'}<h3 class="chat-section-label"${isPolicyComparison()||isFidelityComparison()?' id="tested-question"':''}>${isFidelityComparison()?'Current exchange · both conditions':isPolicyComparison()?'Question being tested · simulated':'Current exchange'}</h3>${conversation(rows.slice(c.prefix.context.length),c.prefix.context.length)}`:conversation(rows);
  if(changed&&visibleChat){
    if(comparing&&(isPolicyComparison()||isFidelityComparison()))messages.querySelector('#tested-question')?.scrollIntoView({block:'start'});
    else messages.scrollTop=!comparing&&state.step>0?(messages.querySelector('.chat-turn:last-of-type')?.offsetTop||0):0;
  }else messages.scrollTop=previousScroll;
  document.querySelectorAll('[data-evidence]').forEach(b=>b.onclick=()=>selectEvidence(b.dataset.evidence));
  document.querySelectorAll('.message-body pre').forEach(pre=>{pre.tabIndex=0;pre.setAttribute('aria-label','Tutor code block')});
}
function policyStatus(c){
  if(c.conditions.some(condition=>['failed','incomplete'].includes(condition.status)))return 'Needs attention';
  const ready=c.conditions.filter(condition=>condition.status==='ready').length;
  return ready===c.conditions.length?'Ready to run':ready?'One condition remaining':'Results saved';
}
function policyColumns(c){
  const labels={ready:'Ready to run','student-replied':'Reply saved','no-follow-up':'No follow-up',failed:'Failed',incomplete:'Incomplete'};
  const outcomes={ready:'This condition has not run. The shared question is the starting point.',
    'student-replied':'The simulated student sent a follow-up.',
    'no-follow-up':'The simulated student chose not to send a follow-up.',
    failed:'This condition stopped after a saved error. It has not been retried.',
    incomplete:'This condition has an unfinished saved request. No final student outcome is available.'};
  return '<div class="compare-grid saved-comparison policy-comparison">'+c.conditions.map(condition=>
    `<article class="comparison"><header><h2>Policy ${esc(condition.id.toUpperCase())}</h2><span class="status-badge" data-status="${esc(condition.status)}">${esc(labels[condition.status]||'Outcome unavailable')}</span><div class="kind">${esc(excerpt(condition.policy,100))}</div></header><details class="policy-instructions"${condition.status==='ready'?' open':''}><summary>Full tutor instructions</summary><p class="saved-message">${esc(condition.policy)}</p></details><div class="entry"><h3 class="chat-section-label">Tutor response</h3>${condition.tutor_reply!==null?`<div class="message-body">${condition.tutor_html||block(condition.tutor_reply)}</div>`:'<p class="quiet">No completed tutor response saved.</p>'}<h3 class="chat-section-label">Student outcome</h3><p class="quiet">${esc(outcomes[condition.status]||'Outcome unavailable.')}</p>${condition.student_reply!==null?`<p class="saved-message">${esc(condition.student_reply)}</p>`:''}</div></article>`
  ).join('')+'</div><p class="note">Same starting question, different tutor instructions. These saved simulations do not establish student realism, learning, or which policy works better for real students.</p>';
}
function newComparison(sourceId=null){
  if(comparisonBusy()||!state.comparison?.controls?.create_enabled)return;
  const sources=state.comparison.controls.sources;
  if(!state.comparisonDirty)state.comparisonEntryNote='';
  if(!state.comparisonDraft||!state.comparisonDirty&&sourceId!==null){
    const source=sourceId===null?sources[0]:sources.find(s=>s.id===sourceId);
    state.comparisonDraft={source_id:source?.id||'',binding:source?.binding,current_policy:state.policyDraft||'',proposed_policy:''};
    if(sourceId!==null&&!source)state.comparisonEntryNote='This conversation has already continued or is no longer eligible. Choose a saved starting conversation below.';
  }else if(sourceId!==null&&state.comparisonDraft.source_id!==sourceId){
    state.comparisonEntryNote='Your unsaved comparison is still open. Choose another starting conversation below if needed.';
  }
  state.comparisonEditing=true;state.showInspector=false;state.comparisonError='';state.chatOpen=true;
  render();$('comparison-source').focus();notify(state.comparisonDirty?'Unsaved comparison draft opened.':'New comparison draft opened.');
}
function canSaveComparison(){
  return state.mode==='compare'&&state.comparisonEditing&&!comparisonSaveReason();
}
function comparisonSaveReason(){
  const draft=state.comparisonDraft,source=comparisonContext();
  if(comparisonBusy())return 'Wait for the current request. Nothing will be sent again.';
  if(!state.comparison?.controls?.create_enabled)return 'Reload the workspace to verify the available starting conversations.';
  if(!draft?.source_id||!source)return 'Choose an available starting conversation.';
  if(['session_sha256','state_sha256'].some(key=>source.binding?.[key]!==draft.binding?.[key]))return 'This starting conversation changed. Select it again to review the current version before saving.';
  if(!draft.current_policy.trim())return 'Enter tutor instructions for Policy A.';
  if(!draft.proposed_policy.trim())return 'Enter tutor instructions for Policy B.';
  if(draft.current_policy.trim()===draft.proposed_policy.trim())return 'Change at least one instruction: Policy A and Policy B are identical.';
  return '';
}
function updateComparisonFeedback(){
  const reason=comparisonSaveReason(),draft=state.comparisonDraft;
  $('comparison-feedback').textContent=state.comparisonError||reason||'Ready to save. Saving creates a fixed comparison without sending model requests.';
  $('save-comparison').disabled=!canSaveComparison();
  const identical=Boolean(draft.current_policy.trim()&&draft.current_policy.trim()===draft.proposed_policy.trim());
  for(const [id,key] of [['current-policy','current_policy'],['proposed-policy','proposed_policy']])$(id).setAttribute('aria-invalid',String(state.comparisonDirty&&(!draft[key].trim()||identical)));
  $('draft-indicator').textContent=state.comparisonDirty?'Unsaved draft · '+(state.draftStored?'Recovered on refresh in this tab.':'Recovery storage unavailable; keep this page open until saved.'):'Draft · no comparison saved yet.';
}
function comparisonReuseReason(c){
  if(comparisonBusy())return 'Wait for the current request.';
  if(state.comparisonDirty)return 'Resume or discard your unsaved draft before reusing another setup.';
  if(!c?.source)return c?.reuse_unavailable_reason||'This exact starting conversation is unavailable for a new comparison.';
  if(!state.comparison.controls.sources.some(s=>s.id===c.source.id&&['session_sha256','state_sha256'].every(key=>s.binding[key]===c.source.binding[key])))return 'This starting conversation changed or is no longer available. Reload to check its saved state.';
  return '';
}
function reuseComparison(){
  const c=state.comparison?.cases[state.reviewIndex];
  if(!state.comparison?.controls?.create_enabled||comparisonReuseReason(c))return;
  state.comparisonDraft={source_id:c.source.id,binding:{...c.source.binding},current_policy:c.conditions.find(condition=>condition.id==='a').policy,proposed_policy:c.conditions.find(condition=>condition.id==='b').policy};
  state.comparisonEditing=true;state.showInspector=false;state.chatOpen=true;state.comparisonError='';
  state.comparisonEntryNote='Copied this exact starting conversation and both policies. Edit an instruction, then save a separate comparison. The original stays unchanged.';
  persistComparisonDraft();render();$('proposed-policy').focus();notify('Setup copied into an unsaved draft.');
}
function renderComparisonForm(){
  const draft=state.comparisonDraft,sources=state.comparison?.controls?.sources||[];
  $('canvas').innerHTML=`<form class="policy-setup" id="comparison-form">${state.comparisonEntryNote?`<p class="entry-note" role="status">${esc(state.comparisonEntryNote)}</p>`:''}<label for="comparison-source">1. Choose a starting conversation</label><select id="comparison-source" aria-describedby="comparison-feedback">${sources.length?'<option value="" disabled>Choose a saved starting conversation</option>'+sources.map(s=>`<option value="${esc(s.id)}">${esc(s.title)}${s.summary?' — '+esc(excerpt(s.summary)):''}</option>`).join(''):'<option value="">No eligible starting conversations</option>'}</select><p class="quiet">Both policies start from the same conversation and cached simulated question, shown in the chat.</p><h2 class="setup-step">2. Write the tutor instructions</h2><div class="policy-editors"><div><label for="current-policy">Policy A — draft</label><textarea id="current-policy" aria-describedby="comparison-feedback" maxlength="64000" required>${esc(draft.current_policy)}</textarea></div><div><label for="proposed-policy">Policy B — draft</label><textarea id="proposed-policy" aria-describedby="comparison-feedback" maxlength="64000" required>${esc(draft.proposed_policy)}</textarea></div></div><p class="quiet">Enter the instructions you want to compare. These drafts are not connected to a deployed tutor.</p><p class="form-feedback" id="comparison-feedback" role="status" tabindex="-1"></p><p class="draft-indicator" id="draft-indicator"></p><div class="draft-actions"><button class="primary" id="save-comparison" type="submit">Save comparison</button><button id="cancel-comparison" type="button">Saved comparisons</button><button id="discard-comparison" type="button"${state.comparisonDirty?'':' hidden'}>Discard draft</button></div><p class="draft-status">Next: review the saved instructions, then run both policies. Saving sends nothing. Draft recovery keeps only these setup fields in this browser tab.</p></form>`;
  $('comparison-source').value=sources.some(s=>s.id===draft.source_id)?draft.source_id:'';
  $('comparison-source').onchange=e=>{
    const source=sources.find(s=>s.id===e.target.value);if(!source||comparisonBusy())return;
    draft.source_id=source.id;draft.binding={...source.binding};state.comparisonEntryNote='';state.comparisonError='';state.showInspector=false;persistComparisonDraft();render();$('comparison-source').focus();
  };
  for(const [id,key]of [['current-policy','current_policy'],['proposed-policy','proposed_policy']]){
    $(id).disabled=comparisonBusy();$(id).oninput=e=>{draft[key]=e.target.value;state.comparisonError='';persistComparisonDraft();$('discard-comparison').hidden=false;updateComparisonFeedback()};
  }
  $('comparison-source').disabled=comparisonBusy()||!sources.length;
  updateComparisonFeedback();
  $('discard-comparison').disabled=comparisonBusy();$('discard-comparison').onclick=discardComparisonDraft;
  $('cancel-comparison').disabled=comparisonBusy();
  $('cancel-comparison').onclick=()=>{if(comparisonBusy())return;state.comparisonEditing=false;state.showInspector=false;render()};
  $('comparison-form').onsubmit=e=>{e.preventDefault();return submitComparison('save')};
}
function comparisonRunReason(c){
  if(state.mode!=='compare'||state.comparisonEditing)return 'Select a saved comparison to run.';
  if(!state.comparison?.controls?.create_enabled)return 'This saved comparison is read only.';
  if(comparisonBusy())return 'A request is running. Reloading checks saved progress without resending.';
  if(!state.comparison.controls.send_enabled)return 'Sending is disabled. This workspace can save comparisons, but cannot generate replies.';
  if(!c?.conditions?.some(condition=>condition.status==='ready'))return 'No untouched conditions remain. Saved outcomes are not rerun.';
  return '';
}
const brier = value => Number.isFinite(value)?value.toFixed(3):'Not scored';
function fidelityReview(review){
  const flag=value=>({yes:'Yes',no:'No',unclear:'Unclear'})[value]||'Not reviewed';
  return `<dl class="review-flags"><dt>Requests help / check</dt><dd>${flag(review?.help_request)}</dd><dt>Shows work / evidence</dt><dd>${flag(review?.work_present)}</dd></dl>${review?.note?`<p class="small muted">Review note: ${esc(review.note)}</p>`:''}`;
}
function fidelityComparison(c,study){
  const paired=study.paired,difference=paired.grounded_minus_current_exchange;
  const finding=!Number.isFinite(difference)?'Insufficient complete cases to compare':difference>0?'Earlier dialogue had higher error in this sample':difference<0?'Earlier dialogue had lower error in this sample':'Both conditions had equal error in this sample';
  return `<section class="fidelity-summary" aria-label="Completed benchmark result"><p class="kind">Closed benchmark · ${study.counts.cases} conversations · ${study.counts.scheduled_draws} saved draws</p><h2>${finding}</h2><p>Help-seeking and work submission · mean Brier error, 0–1 · lower is better.</p><dl class="fidelity-metrics"><div><dt>Current exchange only</dt><dd>${brier(paired['current-exchange']?.mean_brier)}</dd></div><div><dt>With earlier dialogue</dt><dd>${brier(paired.grounded?.mean_brier)}</dd></div><div><dt>History minus current</dt><dd>${Number.isFinite(difference)?(difference>0?'+':'')+difference.toFixed(4):'Not scored'}</dd></div></dl><p class="quiet">Recorded references: ${study.reference_counts.help_request.yes}/${study.counts.cases} request help; ${study.reference_counts.work_present.yes}/${study.counts.cases} show work. One reviewer · previously exposed development data. This does not establish overall student realism.</p><details><summary>Measures and limitations</summary><table class="fidelity-table"><caption>Error by communication flag · ${paired.cases} complete cases</caption><thead><tr><th scope="col">Condition</th><th scope="col">Help</th><th scope="col">Work</th></tr></thead><tbody>${c.conditions.map(condition=>`<tr><th scope="row">${esc(condition.title)}</th><td>${brier(paired[condition.id]?.help_request)}</td><td>${brier(paired[condition.id]?.work_present)}</td></tr>`).join('')}</tbody></table><p>${esc(study.metric)}</p><p>${study.counts.excluded_cases} excluded cases · ${study.counts.missing_judgments} missing judgments · ${study.counts.unclear_flags} unclear flags.</p>${c.conditions.map(condition=>{const d=study.dispositions[condition.id];return `<p>${esc(condition.title)}: ${d.reply} replies, ${d['no-reply']} no-reply decisions, ${d.error} errors.</p>`}).join('')}<ul>${study.limits.map(limit=>`<li>${esc(limit)}</li>`).join('')}</ul></details></section><article class="comparison fidelity-reference"><header><h2>Recorded next student message</h2><div class="kind">Reference · excluded from both generation inputs</div></header><div class="entry"><p class="saved-message">${esc(c.reference.text)}</p>${fidelityReview(c.reference.review)}</div></article><div class="compare-grid saved-comparison policy-comparison">${c.conditions.map(condition=>`<article class="comparison"><header><h2>${esc(condition.title)}</h2><div class="kind">${condition.id==='current-exchange'?'Current student request + recorded tutor reply':'Same exchange + earlier student and tutor messages'} · 4 draws</div></header>${condition.draws.map(draw=>`<section class="entry fidelity-draw"><h3>Draw ${draw.draw}</h3>${draw.status==='reply'?`<p class="saved-message">${esc(draw.text)}</p>`:`<p class="quiet">${draw.status==='no-reply'?'Simulator chose no reply.':'Generation failed; this is not student silence.'}</p>`}${draw.status==='reply'?fidelityReview(draw.review):'<p class="quiet">Help/work flags not applicable: no student message was generated.</p>'}</section>`).join('')}</article>`).join('')}</div><p class="note">All scheduled draws are retained. These are saved results; viewing does not generate replies or request new labels.</p>`;
}
function renderComparison(){
  const data=state.comparison,c=comparisonContext(),editable=data?.controls?.create_enabled===true;
  renderCases();renderModeButtons();
  $('playback').hidden=true;$('next-step').hidden=true;
  $('saved-results').hidden=true;$('continue-run').hidden=true;
  $('instructions').hidden=true;$('tutor-controls').textContent=isFidelityComparison()?'Study details':isPolicyComparison()?'Comparison details':'Review details';
  $('instructions').disabled=!c;$('tutor-controls').disabled=!c||state.comparisonEditing;
  $('tutor-controls').hidden=!c||state.comparisonEditing;
  $('run-details').hidden=true;
  $('new-comparison').hidden=!editable||state.comparisonEditing;
  $('new-comparison').textContent=state.comparisonDirty?'Resume draft':'New comparison';
  $('new-comparison').disabled=comparisonBusy();
  $('reuse-comparison').hidden=!editable||state.comparisonEditing||!c;
  $('reuse-comparison').disabled=Boolean(comparisonReuseReason(c));
  $('run-comparison').hidden=!editable||state.comparisonEditing||!c;
  $('run-comparison').disabled=Boolean(comparisonRunReason(c));
  $('run-comparison').textContent=c?.conditions?.filter(condition=>condition.status==='ready').length===1?'Run remaining condition':'Run both conditions';
  $('case-title').textContent=state.comparisonEditing?'New policy comparison':c?.title||(state.comparisonLoading?'Loading comparison…':editable?'Compare tutor instructions':'Comparison unavailable');
  $('view-description').textContent=state.comparisonEditing?'Set up → Save → Run → Compare responses':c?(isFidelityComparison()?'Same recorded tutor reply · two student input conditions · existing reviews':isPolicyComparison()?policyStatus(c)+(c.conditions.some(condition=>condition.status==='ready')?' · Review the instructions, then run the comparison.':' · Compare the tutor replies and student outcomes below.'):'Recorded next message and two saved simulated replies.'):editable?'Create a saved comparison before generating any replies.':'Read-only saved evidence';
  $('body-grid').classList.toggle('no-inspector',!state.showInspector);
  $('body-grid').classList.toggle('inspector-open',state.showInspector);
  $('inspector-toggle').hidden=!state.showInspector;
  if(state.comparisonEditing){
    renderComparisonForm();
    if(c&&state.showInspector)renderComparisonInspector(c,data);else $('inspector').innerHTML='';
  }else if(c){
    if(isFidelityComparison()){
      $('canvas').innerHTML=fidelityComparison(c,data.study);
    }else if(isPolicyComparison()){
      const remaining=c.conditions.filter(condition=>condition.status==='ready').length;
      $('canvas').innerHTML='<p class="comparison-scope">One simulated exchange per policy · exploratory comparison</p>'+policyColumns(c)+(editable?`<p class="policy-reuse-note" id="policy-reuse-note">${esc(comparisonReuseReason(c)||'Use this setup copies this exact starting conversation and both policies into a separate draft.')}</p><p class="policy-run-note quiet">${esc(comparisonRunReason(c)||`Run ${remaining===2?'both conditions':'the remaining condition'}: sends this conversation and each policy to Gemini for up to ${remaining*2} logical requests (${remaining} tutor replies and ${remaining} student decisions). Each request may make up to 4 adapter attempts. Completed, failed and unfinished requests are not resent.`)}</p>`:'');
    }else{
    const columns=[{title:'Recorded student',subtitle:'First observed next message',...c.reference},
      ...c.draws.map(d=>({title:'Simulated reply '+d.draw,subtitle:'Same setup · draw '+d.draw,...d}))];
    const flag=value=>({yes:'Yes',no:'No',unclear:'Unclear'})[value]||'Not reviewed';
    $('canvas').innerHTML='<div class="compare-grid saved-comparison">'+columns.map(message=>
      `<article class="comparison"><header><h2>${esc(message.title)}</h2><div class="kind">${esc(message.subtitle)}</div></header><div class="entry"><p class="saved-message">${esc(message.text)}</p></div><footer><dl class="review-flags"><dt>Requests help / check</dt><dd>${flag(message.review.help_request)}</dd><dt>Shows work / evidence</dt><dd>${flag(message.review.work_present)}</dd></dl>${message.review.note?`<p class="small muted">Review note: ${esc(message.review.note)}</p>`:''}${message.shared_review_with?`<p class="small muted">Same saved text as reply ${message.shared_review_with}; one review covers both.</p>`:''}</footer></article>`).join('')+'</div><p class="note">One historical simulation setup, two draws per case. Differences from the recorded message do not establish implausibility. These saved reviews do not measure a grounding improvement.</p>';
    }
    if(state.showInspector)renderComparisonInspector(c,data);else $('inspector').innerHTML='';
  }else{
    $('canvas').innerHTML=state.comparisonError?`<div role="alert"><p>${esc(state.comparisonError)}</p><p class="quiet">Reload saved comparison to check again. Nothing will be resent.</p></div>`:editable?'<p class="quiet">No comparisons saved yet. Choose New comparison to select a conversation and enter tutor instructions.</p>':'<p class="quiet" role="status">Verifying the saved comparison and message links…</p>';
    $('inspector').innerHTML='';
  }
  renderChat();renderOperationStatus();
  document.querySelectorAll('.comparison .message-body pre').forEach(pre=>{pre.tabIndex=0;pre.setAttribute('aria-label','Tutor code block')});
}
function renderComparisonInspector(c,data){
  if(state.selected.startsWith('turn:')){
    const turn=turns()[Number(state.selected.split(':')[1])];
    $('inspector').innerHTML='<div class="inspector-title">Conversation source</div><h2>Original message</h2>'+block(turn.text)+(isFidelityComparison()?'<p>Earlier dialogue is supplied only to the history condition. The current request and recorded tutor reply are supplied to both. The recorded next message is excluded from both inputs.</p>':isPolicyComparison()?'<p>Exact text shared by both tutor-policy conditions.</p>':'<p>Exact text from the shared review context. The recorded next message stays outside the generation inputs.</p>');
  }else if(isFidelityComparison()){
    $('inspector').innerHTML=`<div class="inspector-title">Completed student benchmark</div><h2>What changed between conditions?</h2><p>The baseline receives the current student request and recorded tutor reply. The history condition also receives earlier student and tutor messages. Model and generation setup remain the same.</p><p>Model: ${esc(data.study.model)}</p><h3>Existing human review</h3><p>Requests help / check: ${esc(data.definitions.help_request)}</p><p>Shows work / evidence: ${esc(data.definitions.work_present)}</p><p>Both flags can be yes. Unclear, missing labels, no-reply decisions and generation errors are distinct from no.</p><p>The fixed benchmark is closed. No winner is adopted and no additional labeling or generation is triggered by this view.</p>`;
  }else if(isPolicyComparison()){
    $('inspector').innerHTML='<div class="inspector-title">Saved policy comparison</div><h2>How to read this comparison</h2><p>Both conditions use the same supplied conversation and cached simulated question. Each has its own fixed tutor instructions and at most one new student decision.</p><p>The starting question is simulated. It is not an observed future student message.</p><div class="divider"></div><p>Ready means no new exchange has run. A failed or unfinished request is not student silence. A no-follow-up is a saved simulator choice.</p><p>Model: '+esc(c.model)+'</p><p>Viewing sends nothing. This comparison supplies no accuracy score or evidence of real policy effects.</p>';
  }else{
    $('inspector').innerHTML=`<div class="inspector-title">Existing human review</div><h2>How to read this comparison</h2><h3>Requests help / check</h3><p>${esc(data.definitions.help_request)}</p><div class="divider"></div><h3>Shows work / evidence</h3><p>${esc(data.definitions.work_present)}</p><div class="divider"></div><p>Both flags can be yes. Unclear and not reviewed remain separate from no.</p><p>One reviewer supplied these judgments. The cases had prior development exposure; coding reliability is unmeasured.</p><div class="divider"></div><p>Two replies from the same historical configuration do not compare baseline and grounded simulators. Notebook actions, correctness and learning remain unknown.</p><p>This view reads completed evidence and does not collect new labels or change the simulator.</p>`;
  }
}
function applyComparison(data){
  if(data.version!==1||!['saved-communication-comparison','saved-policy-comparison','saved-student-fidelity-comparison'].includes(data.kind)||!Array.isArray(data.cases)||(!data.cases.length&&!data.controls?.create_enabled))throw new Error('Unsupported saved comparison.');
  const selected=data.selected_id||state.comparison?.cases[state.reviewIndex]?.id;
  state.comparison=data;state.comparisonOperation=data.operation||{status:'idle',message:''};
  const index=data.cases.findIndex(c=>c.id===selected);
  state.reviewIndex=index>=0?index:Math.max(0,Math.min(state.reviewIndex,data.cases.length-1));
}
async function reloadComparison({monitor=false}={}){
  if(state.comparisonLoading)return;
  clearTimeout(comparisonPollTimer);
  state.comparisonLoading=true;if(!monitor)state.comparison=null;
  state.comparisonError='';state.showInspector=false;
  $('reset').disabled=true;render();
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
  try{
    const response=await fetch('/api/comparison',{cache:'no-store',signal:controller.signal});
    const data=await response.json();
    if(response.status===202){
      state.comparisonOperation=data.operation;state.comparisonMonitoring=true;
      comparisonPollTimer=setTimeout(()=>reloadComparison({monitor:true}),1500);return;
    }
    if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Could not read the saved comparison.');
    applyComparison(data);state.comparisonMonitoring=false;
    notify('Saved comparison loaded. No requests sent.');
  }catch(error){
    state.comparison=null;state.comparisonMonitoring=false;
    state.comparisonError=error.name==='AbortError'?'The local comparison did not respond in time. Reload to check saved progress; nothing will be resent.':error.message;
    notify('Saved comparison unavailable.');
  }
  finally{clearTimeout(timeout);state.comparisonLoading=false;$('reset').disabled=false;render();}
}
async function submitComparison(action){
  const saving=action==='save',c=state.comparison?.cases[state.reviewIndex];
  if(saving?!canSaveComparison():Boolean(comparisonRunReason(c)))return;
  const payload=saving?{...state.comparisonDraft,binding:{...state.comparisonDraft.binding}}:{comparison_id:c.id,comparison_sha256:c.comparison_sha256};
  state.comparisonSubmitting=true;state.comparisonError='';render();
  let completed=false;
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
  try{
    // A timeout only ends the HTTP wait. Recover with reads; never repeat the POST.
    const response=await fetch(saving?'/api/comparison':'/api/comparison/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:controller.signal});
    const data=await response.json();
    if(response.status===202){
      state.comparisonOperation=data.operation;state.comparisonMonitoring=true;
      comparisonPollTimer=setTimeout(()=>reloadComparison({monitor:true}),1500);return;
    }
    if(response.status>=500)throw new Error('The server could not confirm the request outcome.');
    if(!response.ok){state.comparisonError=typeof data.detail==='string'?data.detail:'The request was rejected. Reload saved comparison before trying again.';return}
    applyComparison(data);state.comparisonEditing=false;state.showInspector=false;
    if(saving)clearComparisonDraft();
    completed=true;
    notify(data.operation?.message||(saving?'Comparison saved. No model requests sent.':'Comparison results saved.'));
  }catch(error){
    state.comparisonMonitoring=true;
    await reloadComparison({monitor:true});
    state.comparisonError=error.name==='AbortError'?'The request response timed out. Saved status is shown; nothing was resent.':'The request response was lost. Saved status is shown; nothing was resent.';
  }finally{
    clearTimeout(timeout);state.comparisonSubmitting=false;render();
    (completed?$('case-title'):saving&&state.comparisonEditing?$('comparison-feedback'):$('operation-status')).focus();
  }
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
  if(key==='results'){
    $('inspector').innerHTML=`<div class="inspector-title">${esc(current().title)} · Entire ${state.kind==='chat'?'conversation':'task'} history</div><p class="quiet">All saved exchanges for this ${state.kind==='chat'?'conversation':'task'}, including those after the selected playback state. The chat sidebar remains at that selected state.</p><div class="saved-results">${current().saved_results_html||'<p>Saved exchange details are unavailable. Reload the saved run.</p>'}</div>`;
    document.querySelectorAll('#inspector pre').forEach(pre=>{pre.tabIndex=0;pre.setAttribute('aria-label','Saved exchange text')});
    return;
  }
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
  $('trail-hint').textContent=(state.kind==='chat'?frame().label:`State ${state.step+1} of ${current().frames.length}`)+' · no new generation';
  $('previous-step').disabled=state.step===0;
  $('trail').hidden=state.kind==='chat';
  $('trail').innerHTML=state.kind==='chat'?'':current().frames.map((f,i)=>`<button data-trail="${i}" aria-pressed="${i===state.step}"><span class="count">${i+1}</span>${esc(f.label)}</button>`).join('');
  document.querySelectorAll('[data-trail]').forEach(b=>b.onclick=()=>selectFrame(Number(b.dataset.trail)));
}
function render(){
  const focused=document.activeElement;
  const attr=['data-case','data-scenario','data-review-case','data-trail','data-evidence'].find(a=>focused?.hasAttribute(a));
  const value=attr?focused.getAttribute(attr):null;
  if(state.mode==='compare'){
    renderComparison();
    if(attr)document.querySelector(`[${attr}="${value}"]`)?.focus({preventScroll:true});
    return;
  }
  const c=current(),f=frame();
  $('new-comparison').hidden=!state.policyWorkspaceAvailable;$('run-comparison').hidden=true;$('reuse-comparison').hidden=true;
  $('new-comparison').textContent='Compare tutor policies';
  $('new-comparison').disabled=state.submitting||state.monitoring||state.refreshing||comparisonBusy();
  renderCases();
  renderModeButtons();
  $('instructions').hidden=false;$('instructions').textContent='Run context';$('tutor-controls').textContent='Tutor instructions';
  $('tutor-controls').hidden=false;$('run-details').hidden=false;
  $('continue-run').hidden=!state.controls.send_enabled;
  $('continue-run').textContent=f.status==='awaiting-tutor'?'Reply to student':'Continue run';
  $('continue-run').disabled=Boolean(continuationReason());
  $('tutor-controls').hidden=!$('continue-run').hidden&&!$('continue-run').disabled;
  $('saved-results').hidden=false;$('saved-results').disabled=false;
  $('case-title').textContent=c.title;
  $('view-description').textContent=`${f.label} · ${statusText(f)}`;
  $('canvas').innerHTML=state.kind==='chat'?'':`${notebook()}<p class="note">Saved results only. Moving between states makes no model requests and executes no code. One saved step may contain several student decisions.</p>`;
  $('next-step').hidden=state.mode!=='simulate';
  $('next-step').disabled=state.step===c.frames.length-1;
  $('next-step').textContent='Next';
  $('instructions').disabled=false;$('tutor-controls').disabled=false;
  $('body-grid').classList.toggle('no-inspector',!state.showInspector);
  $('body-grid').classList.toggle('inspector-open',state.showInspector);
  $('inspector-toggle').hidden=!state.showInspector;
  if(state.showInspector)renderInspector();else $('inspector').innerHTML='';
  renderTrail();renderChat();renderOperationStatus();
  if(attr)document.querySelector(`[${attr}="${value}"]`)?.focus({preventScroll:true});
}
function continuationReason(){
  if(state.mode==='compare')return 'Saved comparisons are read only.';
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
  $('inspector').innerHTML=`<div class="inspector-title">Tutor and student controls</div><h2>${waiting?'Reply to the student':'Continue the student'}</h2><p>${waiting?'The reply will be followed by one student decision.':'Continue one decision using the current '+(state.kind==='chat'?'conversation':'task and conversation')+'. Tutor instructions are used only when replying to a student message.'}</p>${waiting?'<label for="tutor-mode">Reply mode</label><select id="tutor-mode"><option value="policy">Generate from instructions</option><option value="reply">Write a reply</option></select>':''}<div${manual?' hidden':''}><label for="policy">Tutor instructions</label><textarea id="policy" maxlength="64000">${esc(state.policyDraft||'')}</textarea></div><div${manual?'':' hidden'}><label for="manual-reply">Your tutor reply</label><textarea id="manual-reply" maxlength="64000">${esc(state.replyDraft)}</textarea></div><p class="draft-status">Drafts stay in this page. Reload saved run preserves them; refreshing the browser or switching scenarios resets them.</p>${state.controls.reference?`<p>Configured tutor reference: ${esc(state.controls.reference.library)} ${esc(state.controls.reference.library_version)}. Used only for generated tutor replies.</p>`:''}<div class="divider"></div><p id="continuation-reason">${esc(continuationReason())}</p><button class="primary" id="submit-operation">${esc(submitLabel())}</button><p class="tiny" style="margin-top:12px">${state.controls.send_enabled?(state.kind==='chat'?'Sends the visible conversation to Gemini. This mode cannot execute notebook code. Playback sends nothing.':'Sends the visible task, work and conversation to Gemini. A local check runs only if the student requests it. Playback sends nothing.'):'Viewing only. No request can be sent from this workspace.'}</p>`;
  $('policy').oninput=e=>{state.policyDraft=e.target.value;updateSubmitButton()};
  $('manual-reply').oninput=e=>{state.replyDraft=e.target.value;updateSubmitButton()};
  if(waiting){$('tutor-mode').value=state.replyMode;$('tutor-mode').onchange=e=>{state.replyMode=e.target.value;renderControls();$('tutor-mode').focus()}}
  $('submit-operation').onclick=submitOperation;updateSubmitButton();
}
function renderOperationStatus(){
  document.querySelector('.reset-label').textContent=state.mode==='compare'?'Reload saved comparison':'Reload saved run';
  $('new-comparison').disabled=state.submitting||state.monitoring||state.refreshing||comparisonBusy();
  renderModeButtons();
  if(state.mode==='compare'){
    const editable=state.comparison?.controls?.create_enabled;
    document.querySelector('.prototype-note').textContent=comparisonBusy()?'Policy comparison · Checking saved progress':editable?(state.comparison.controls.send_enabled?'Policy comparison · Sending enabled':'Policy comparison · Save only'):'Saved comparison · Read only';
    const message=state.comparisonSubmitting?(state.comparisonEditing?'Saving comparison…':'Generating tutor and student replies · showing the last verified data.'):state.comparisonMonitoring?'Request running · showing the last verified data. Reloading checks progress without resending.':state.comparisonError||(state.comparisonEditing?'':state.comparisonOperation.message)||'';
    $('operation-status').textContent=message;$('operation-status').hidden=!message;return;
  }
  $('continue-run').disabled=Boolean(continuationReason());
  $('tutor-controls').hidden=!$('continue-run').hidden&&!$('continue-run').disabled;
  const message=state.submitting||state.monitoring?'Request running'+(state.encounters.length?' · showing the last saved state.':'.')+' Reloading checks progress without resending.':state.clientError||state.controls.blocked_reason||state.operation.message||'';
  $('operation-status').textContent=message;$('operation-status').hidden=!message;
  document.querySelector('.prototype-note').textContent=state.submitting||state.monitoring?'Simulation · Request running':state.controls.send_enabled?'Simulation · Sending enabled':'Saved simulation · Read only';
  document.querySelectorAll('[data-scenario]').forEach(b=>{b.disabled=state.refreshing||state.submitting||state.monitoring});
  updateSubmitButton();
}
function applyWorkspace(packet){
  if(state.scenarios?.length&&packet.scenario_id!==state.scenarioId)throw new Error('The response does not match the selected scenario. Reload before continuing.');
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
  $('saved-results').disabled=true;$('continue-run').hidden=true;
  $('new-comparison').hidden=true;$('run-comparison').hidden=true;$('reuse-comparison').hidden=true;
  $('body-grid').classList.toggle('no-inspector',true);$('body-grid').classList.toggle('inspector-open',false);
  renderModeButtons();
  $('canvas').innerHTML=message;
  renderChat();
  if(state.scenarios?.length)renderCases();
}
async function reloadWorkspace(){
  if(state.refreshing)return;
  clearTimeout(pollTimer);state.refreshing=true;$('reset').disabled=true;updateSubmitButton();
  if(!state.encounters.length){clearWorkspaceView('<p class="quiet" role="status">Loading saved evidence…</p>');$('case-title').textContent='Loading saved run';$('view-description').textContent='Verifying saved states and linked history…'}
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
  try{
    if(state.scenarios===null){
      const response=await fetch('/api/scenarios',{cache:'no-store',signal:controller.signal});
      const catalog=await response.json();
      if(!response.ok||catalog.version!==1||!Array.isArray(catalog.scenarios)||catalog.scenarios.some(s=>typeof s.id!=='string'||!s.id||typeof s.title!=='string')||new Set(catalog.scenarios.map(s=>s.id)).size!==catalog.scenarios.length)throw new Error('The saved scenario list could not be loaded.');
      state.scenarios=catalog.scenarios;
      state.comparisonAvailable=catalog.comparison_available===true;
      state.fidelityComparisonAvailable=catalog.fidelity_comparison_available===true;
      state.replayAvailable=catalog.replay_available!==false;
      state.policyWorkspaceAvailable=catalog.policy_workspace_available===true;
      state.workspaceId=typeof catalog.workspace_id==='string'?catalog.workspace_id:null;
      if(state.policyWorkspaceAvailable)restoreComparisonDraft();
      if(state.scenarios.length){
        state.kind='chat';state.scenarioId=new URLSearchParams(window.location.search).get('scenario')||state.scenarios[0].id;
        renderCases();
      }
    }
    if(!state.replayAvailable){state.mode='compare';return}
    const response=await fetch(workspaceUrl('/api/workspace'),{cache:'no-store',signal:controller.signal});
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
  }finally{clearTimeout(timeout);state.refreshing=false;$('reset').disabled=false;renderOperationStatus();if(!state.encounters.length)renderChat()}
}
async function submitOperation(){
  if(!canSubmit())return;
  const mode=['active','ready'].includes(frame().status)?'advance':state.replyMode;
  const payload={binding:{...frame().binding},mode,...(mode==='advance'?{}:{text:mode==='policy'?state.policyDraft:state.replyDraft})};
  state.submitting=true;state.clientError='';renderOperationStatus();
  try{
    // No timeout/retry: aborting an HTTP request would not cancel a saved backend operation.
    const response=await fetch(workspaceUrl('/api/continue'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const packet=await response.json();
    if(!response.ok)throw new Error(typeof packet.detail==='string'?packet.detail:'The request was rejected. Reload the saved run before trying again.');
    state.showInspector=false;state.mode='simulate';state.selected='step';
    applyWorkspace(packet);
    if(frame().actions.some(action=>action.text))document.querySelector('#conversation-messages .chat-turn:last-child')?.scrollIntoView({block:'nearest'});
    else $('canvas').scrollTop=0;
    notify(state.operation.message||'New result saved.');
  }catch(error){
    state.clientError=error.message||'Request outcome is unknown. Checking saved status; it will not be resent.';
    await reloadWorkspace();
  }finally{state.submitting=false;renderOperationStatus()}
}
document.title='Student lab · Simulation workspace';
$('app').classList.toggle('connected-workspace',true);
$('body-grid').insertAdjacentHTML('beforeend','<aside class="conversation-panel" id="conversation-panel" aria-label="Student and tutor conversation"><header><h2 id="chat-title">Student–tutor chat</h2><p id="chat-caption" class="small muted"></p><div class="chat-navigation"><span id="chat-count" class="small muted"></span><button data-chat-jump="first" aria-label="Go to first message" aria-controls="conversation-messages">First</button><button data-chat-jump="last" aria-label="Go to last message" aria-controls="conversation-messages">Last</button></div></header><div id="conversation-messages"></div></aside>');
$('inspector-toggle').insertAdjacentHTML('beforebegin','<button id="chat-toggle" aria-controls="conversation-panel" aria-expanded="true">Hide chat</button>');
$('instructions').insertAdjacentHTML('beforebegin','<button class="bare" id="tutor-controls">Tutor controls</button>');
$('instructions').insertAdjacentHTML('beforebegin','<button id="saved-results">Saved results</button>');
$('instructions').insertAdjacentHTML('beforebegin','<button class="bare" id="new-comparison" hidden>New comparison</button><button id="reuse-comparison" aria-describedby="policy-reuse-note" hidden>Use this setup</button><button class="primary" id="run-comparison" hidden>Run both conditions</button>');
$('instructions').insertAdjacentHTML('beforebegin','<button class="primary" id="continue-run" hidden>Continue run</button><details class="run-details" id="run-details"><summary id="run-details-toggle">Run details</summary><div class="run-details-actions" id="run-details-actions"></div></details>');
$('run-details-actions').append($('instructions'));
$('canvas').after($('inspector'));
document.querySelector('.trail-label').insertAdjacentHTML('beforeend','<div class="playback-buttons" id="playback-buttons"><button id="previous-step">Previous</button></div>');
$('playback-buttons').append($('next-step'));
$('canvas').insertAdjacentHTML('beforebegin','<div id="operation-status" role="status" aria-live="polite" hidden></div>');
$('case-title').tabIndex=-1;$('operation-status').tabIndex=-1;
document.querySelector('.prototype-note').textContent='Saved simulation · Read only';
document.querySelector('.breadcrumb').textContent='Notebook simulation';
document.querySelector('.explorer-heading').textContent='Tasks';
document.querySelector('.explorer-heading').insertAdjacentHTML('afterend','<p id="conversation-guide" class="conversation-guide" hidden>Each entry is a separate conversation used to start a simulation.</p>');
document.querySelector('.reset-label').textContent='Reload saved run';
$('reset').title='Reload saved run without generating or executing';
$('search').placeholder='Filter tasks…';$('search').setAttribute('aria-label','Filter saved tasks');
$('instructions').textContent='Run context';
$('inspector-toggle').textContent='Close details';
document.querySelectorAll('[data-mode]').forEach(b=>{if(b.dataset.mode==='compare')b.hidden=true;if(b.dataset.mode==='simulate')b.textContent='Replay';b.onclick=()=>selectMode(b.dataset.mode)});
$('search').oninput=()=>{if(state.mode==='compare'||state.encounters.length||state.scenarios?.length)renderCases()};
$('run-details').onkeydown=e=>{if(e.key==='Escape'){e.preventDefault();$('run-details').open=false;$('run-details-toggle').focus()}};
$('instructions').onclick=()=>selectEvidence('context');
$('continue-run').onclick=()=>selectEvidence('controls');
$('new-comparison').onclick=async()=>{
  if(state.submitting||state.monitoring||state.refreshing||comparisonBusy())return;
  const sourceId=state.mode==='compare'?null:state.scenarioId;
  if(state.mode!=='compare')await selectMode('compare');
  newComparison(sourceId);
};
$('run-comparison').onclick=()=>submitComparison('run');
$('reuse-comparison').onclick=reuseComparison;
$('previous-step').onclick=()=>{if(state.step>0)selectFrame(state.step-1)};
$('tutor-controls').onclick=()=>selectEvidence(state.mode==='compare'?'review':'controls');
$('saved-results').onclick=()=>selectEvidence('results');
$('chat-toggle').onclick=()=>{state.chatOpen=!state.chatOpen;if(state.chatOpen)state.chatKey=null;renderChat();if(!state.chatOpen&&state.selected.startsWith('turn:'))$('chat-toggle').focus()};
document.querySelectorAll('[data-chat-jump]').forEach(b=>b.onclick=()=>{const messages=$('conversation-messages'),first=b.dataset.chatJump==='first';messages.scrollTop=first?0:messages.scrollHeight;messages.querySelector(first?'.chat-turn':'.chat-turn:last-of-type')?.focus({preventScroll:true})});
$('next-step').onclick=()=>{if(state.step<current().frames.length-1)selectFrame(state.step+1)};
$('inspector-toggle').onclick=()=>{state.showInspector=false;render();(state.selected.startsWith('turn:')&&!state.chatOpen&&(state.kind!=='chat'||state.mode==='compare')?$('chat-toggle'):state.selected==='results'?$('saved-results'):state.selected==='controls'?($('tutor-controls').hidden?$('continue-run'):$('tutor-controls')):state.selected==='review'?$('tutor-controls'):state.selected==='context'?$('run-details-toggle'):document.querySelector(`[data-evidence="${state.selected}"]`)||document.querySelector(`[data-mode="${state.mode}"]`))?.focus()};
$('explorer-toggle').onclick=()=>{const shown=$('app').classList.toggle('show-explorer');$('explorer-toggle').setAttribute('aria-expanded',String(shown))};
$('reset').onclick=()=>state.mode==='compare'?reloadComparison({monitor:state.comparisonSubmitting||state.comparisonMonitoring}):reloadWorkspace();
window.addEventListener('beforeunload',event=>{if(state.comparisonDirty){event.preventDefault();event.returnValue=''}});
const ready=(async()=>{
  await reloadWorkspace();
  const params=new URLSearchParams(window.location.search);
  if(state.comparisonAvailable&&(!state.replayAvailable||params.get('view')==='compare'||
      (state.policyWorkspaceAvailable||state.fidelityComparisonAvailable)&&!params.has('view')&&!params.has('scenario'))){
    await selectMode('compare');
    if(state.mode==='compare'&&state.comparison?.controls?.create_enabled&&(state.comparisonDirty||!state.comparison.cases.length))newComparison();
  }
})();
