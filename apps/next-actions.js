'use strict';
// Sampling owns its panel; the connected workspace owns notebook/chat rendering.
(() => {
  const preview = {data:null,error:'',readError:'',setup:false,runs:'30',selected:null,selectedBatch:null,
    frames:null,original:null,batch:'saved',loading:false,pending:null,cancelling:null,timer:null,loadId:0};
  const labels = {'no-reply':'No further action',reply:'Send a message','revise-work':'Edit notebook'};
  const symbols = {'no-reply':'<path d="M5 10h10"/>',reply:'<path d="M4 4h12v9H8l-4 3Z"/>','revise-work':'<path d="m5 13 8-8 3 3-8 8H5Zm6-6 3 3"/>'};
  const icon = body => `<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">${body}</svg>`;
  const selectedSample = () => preview.selectedBatch===preview.batch?preview.data?.samples.find(s=>s.index===preview.selected):null;
  const selectedGroup = () => preview.data.samples.filter(s=>s.decision===selectedSample()?.decision);
  const percent = value => (100*value).toFixed(1)+'%';
  const branchIcon = icon('<circle cx="5" cy="5" r="2"/><circle cx="15" cy="5" r="2"/><circle cx="5" cy="15" r="2"/><path d="M5 7v6m2-3h3a5 5 0 0 0 5-3"/>');
  const activeBatch = () => preview.data?.active_batch;
  const samplingMode = () => preview.data?.enabled||preview.data?.batches?.some(batch=>batch.id!=='saved');
  const statusName = batch => batch.cancel_requested&&batch.status==='running'?'Stopping':({running:'Running',complete:'Complete',cancelled:'Cancelled',interrupted:'Interrupted',error:'Stopped after error'}[batch.status]||batch.status);
  const replaceHTML = (element,html) => {if(element.samplingHTML!==html){element.innerHTML=html;element.samplingHTML=html}};

  function mount(){
    if($('next-actions-panel'))return;
    $('reset').insertAdjacentHTML('afterend',`<button id="next-actions-toggle" popovertarget="next-actions-panel" aria-controls="next-actions-panel" aria-expanded="false">${branchIcon}Next actions<span class="sample-count" id="next-actions-count">…</span></button>`);
    $('app').insertAdjacentHTML('beforeend',`<section popover="auto" id="next-actions-panel" class="sampling-panel" aria-label="Sampled next actions">
      <header class="sampling-header"><div><h2>What happens next?</h2><p id="sampling-summary">Loading saved next actions…</p></div><button id="new-action-batch" class="text-action" aria-expanded="false" aria-controls="sampling-setup">New batch</button><button class="sampling-close" id="hide-next-actions" aria-label="Hide next actions">×</button></header>
      <div class="sampling-batches" id="sampling-batches" hidden><label for="sampling-batch">Batch</label><select id="sampling-batch"></select></div>
      <form class="sampling-setup" id="sampling-setup" hidden><div><label for="sampling-runs">Number of runs</label><div class="run-setting"><input id="sampling-runs" type="number" min="1" max="100" step="1" value="30" required aria-describedby="sampling-budget sampling-preview-note"><button id="sample-run-button" class="primary" disabled>Run 30 samples</button></div></div><p id="sampling-budget"></p><p id="sampling-preview-note"></p></form>
      <div id="sampling-progress" class="sampling-progress" hidden></div>
      <div id="sampling-error" class="sampling-error" role="alert" hidden></div><button id="reload-action-data" class="text-action" hidden>Check status</button>
      <div class="action-distribution" id="action-distribution" aria-label="Observed next-action frequencies"></div><div class="sampling-footer" id="sampling-footer"></div>
    </section>`);
    $('next-actions-panel').addEventListener('toggle',()=>{
      $('next-actions-toggle').setAttribute('aria-expanded',String($('next-actions-panel').matches(':popover-open')));
    });
    $('hide-next-actions').onclick=closePanel;
    $('new-action-batch').onclick=()=>{preview.setup=!preview.setup;renderPreview();(preview.setup?$('sampling-runs'):$('new-action-batch')).focus()};
    $('sampling-runs').oninput=e=>{preview.runs=e.target.value;renderSetup()};
    $('sampling-setup').onsubmit=startBatch;
    $('sampling-batch').onchange=e=>selectBatch(e.target.value);
    $('sampling-batch').onblur=()=>renderPreview();
    $('reload-action-data').onclick=()=>load();
  }

  function closePanel(){
    $('next-actions-panel').hidePopover();
    $('next-actions-toggle').focus({preventScroll:true});
  }

  function choose(index,keepOpen=false){
    const sample=preview.data?.samples.find(s=>s.index===index);
    if(!sample||!preview.original||preview.loading)return;
    preview.selected=index;preview.selectedBatch=preview.batch;current().frames[2]=structuredClone(sample.frame);
    state.step=2;state.showInspector=false;state.selected='step';state.chatOpen=true;state.chatKey=null;
    render();
    if(!keepOpen)closePanel();
    document.querySelector('#canvas [aria-label="Selected code cell, read only"]')?.scrollIntoView({block:'start'});
    notify(`Showing saved sample ${index}: ${labels[sample.decision].toLowerCase()}. No generation or execution.`);
  }

  function restoreFrame(){
    if(preview.selected!==null&&preview.original&&current()?.frames===preview.frames){
      current().frames[2]=structuredClone(preview.original);state.chatKey=null;
      preview.selected=null;preview.selectedBatch=null;render();
    }
  }

  function restore(){
    restoreFrame();state.step=2;state.showInspector=false;render();
    closePanel();notify('Original saved reaction restored.');
  }

  function row(key){
    const category=preview.data.categories.find(c=>c.decision===key);
    const count=category?.count||0,proportion=category?.proportion||0;
    const selected=selectedSample()?.decision===key&&state.step===2;
    return `<button class="action-row" id="action-${key}" data-action="${key}" aria-pressed="${selected}"${count&&!preview.loading?'':' disabled'} aria-label="${esc(labels[key])}: ${count} of ${preview.data.valid} valid samples${count?', inspect saved outcome':', none observed'}">
      <span class="action-name">${icon(symbols[key])}<span>${labels[key]}</span></span>
      <span class="action-meter" aria-hidden="true"><span style="width:${Math.max(0,Math.min(100,100*proportion))}%"></span></span>
      <span class="action-count">${count}<span> / ${preview.data.valid}</span></span>
      <span class="action-percentage">${count?percent(proportion):'0 observed'}</span>
      <span class="action-open" aria-hidden="true">${selected?'✓':count?'›':'—'}</span>
    </button>`;
  }

  function selection(){
    const sample=selectedSample();
    if(!sample)return `<span class="sampling-hint">${preview.data.valid?'Choose an outcome to view it in Reaction.':'No valid outcomes in this batch yet.'}</span>`;
    const group=selectedGroup(),position=group.findIndex(s=>s.index===sample.index);
    return `<div class="sample-selection"><span class="sample-selection-label"><span class="sample-dot" aria-hidden="true"></span>${state.step===2?'Viewing':'Selected'} sample <b>${sample.index}</b></span><span class="sample-position">${position+1} of ${group.length} in this action</span><div class="sample-nav" role="group" aria-label="Browse samples within this action"><button id="sample-previous" aria-label="Previous saved sample"${position===0?' disabled':''}>‹</button><button id="sample-next" aria-label="Next saved sample"${position===group.length-1?' disabled':''}>›</button></div>${state.step!==2?'<button id="open-selected" class="text-action">Open Reaction</button>':''}<button id="original-reaction" class="text-action">Original reaction</button></div>`;
  }

  function renderSetup(){
    const data=preview.data,input=$('sampling-runs'),valid=input.value!==''&&input.checkValidity();
    $('sampling-setup').hidden=!preview.setup;
    $('new-action-batch').textContent=preview.setup?'Close setup':'New batch';
    $('new-action-batch').setAttribute('aria-expanded',String(preview.setup));
    input.setAttribute('aria-invalid',String(!valid));
    $('sample-run-button').textContent=preview.pending?.sending?'Starting…':valid?`Run ${input.value} samples`:'Run samples';
    $('sample-run-button').disabled=!data?.enabled||!data?.csrf_token||!data?.binding?.input_sha256||!valid||!!activeBatch()||!!preview.pending||preview.loading||!!preview.readError;
    $('sampling-budget').textContent=valid?`${input.value} independent next-action requests from the fixed starting point.`:'Choose a whole number from 1 to 100.';
    $('sampling-preview-note').textContent=data?.enabled?
      `Run sends the course, notebook and conversation context to Google Gemini (${data.model}). Starting point: ${data.input_label}. Selecting another outcome does not change this input.`:
      data?.disabled_reason||'Design preview: new sampling is not enabled. You can inspect the saved outcomes below.';
  }

  function renderProgress(){
    const data=preview.data,active=activeBatch(),selected=data?.batches?.find(batch=>batch.id===preview.batch);
    const batch=active||selected,progress=$('sampling-progress');
    progress.hidden=!batch||batch.id==='saved';
    if(!progress.hidden){
      replaceHTML(progress,`<div><span role="status">${esc(statusName(batch))} · ${batch.finished} / ${batch.requested} finished</span>${active?`<button id="cancel-action-batch" class="text-action"${active.cancel_requested||preview.cancelling?' disabled':''}>${active.cancel_requested?'Stopping…':'Cancel'}</button>`:''}</div><progress max="${batch.requested}" value="${batch.finished}" aria-label="Finished sampling requests"></progress><p>${batch.valid} valid · ${batch.failed} failed${active?' · '+(active.id===preview.batch?'This batch':'Another batch')+' is running.':''}</p>${active?'<p>Cancel stops future requests; an in-flight request may finish.</p>':''}`);
      if($('cancel-action-batch'))$('cancel-action-batch').onclick=cancelBatch;
    }
    $('next-actions-count').textContent=active?`${active.finished}/${active.requested}`:preview.pending?'…':data?.attempts??'…';
    $('next-actions-toggle').title=active?`${statusName(active)}: ${active.finished} of ${active.requested} requests finished`:
      preview.pending?'Checking whether the batch started':`${data?.valid??0} saved outcomes`;
  }

  function renderPreview(){
    mount();const panel=$('next-actions-panel'),focused=panel.contains(document.activeElement)?document.activeElement:null;
    document.querySelector('.prototype-note').textContent=samplingMode()?'Next-action sampling · '+(preview.data.enabled?'Sending enabled':'Sending disabled'):'Design preview · Saved outcomes';
    document.title=samplingMode()?'Student lab · Next-action sampling':'Student lab · Next actions preview';
    $('app').classList.add('next-actions-preview');
    if(current()?.frames!==preview.frames){
      preview.frames=current()?.frames;preview.original=preview.frames?.[2]?structuredClone(preview.frames[2]):null;preview.selected=null;preview.selectedBatch=null;
    }
    $('next-actions-toggle').disabled=!state.encounters.length;
    if(!state.encounters.length&&panel.matches(':popover-open'))panel.hidePopover();
    $('new-action-batch').disabled=!preview.data;
    renderSetup();renderProgress();
    const message=[preview.error,preview.readError].filter(Boolean).join(' ');
    $('sampling-error').hidden=!message;$('sampling-error').textContent=message;
    $('reload-action-data').hidden=!message&&!preview.pending&&!preview.cancelling;
    $('reload-action-data').disabled=preview.loading||!!preview.pending?.sending;
    $('reload-action-data').textContent=preview.data?'Check status':'Reload saved outcomes';
    if(!preview.data)return;
    const data=preview.data,batches=(data.batches||[]).filter(batch=>batch.id!=='saved');
    const selectedLoaded=(data.selected_batch||'saved')===preview.batch;
    $('sampling-summary').textContent=preview.loading?'Loading batch…':selectedLoaded?`After execution · ${data.valid} saved outcomes${data.failed?` · ${data.failed} failed requests`:''}`:'Selected batch unavailable';
    $('sampling-batches').hidden=!batches.length;
    const batchSelect=$('sampling-batch');
    if(document.activeElement!==batchSelect){
      replaceHTML(batchSelect,'<option value="saved">Original saved batch</option>'+batches.map(batch=>{
        const time=new Date(batch.created_at).toLocaleString([], {month:'short',day:'numeric',hour:'numeric',minute:'2-digit',second:'2-digit'});
        return `<option value="${esc(batch.id)}">${esc(time)} · ${esc(statusName(batch))} · ${batch.finished}/${batch.requested}</option>`;
      }).join(''));
      batchSelect.value=preview.batch;
    }
    batchSelect.disabled=preview.loading||!!preview.pending?.sending;
    if(!selectedLoaded){
      replaceHTML($('action-distribution'),'');
      replaceHTML($('sampling-footer'),'<span class="sampling-hint">Waiting for this batch’s verified outcomes.</span>');
      return;
    }
    replaceHTML($('action-distribution'),row('no-reply')+row('reply')+row('revise-work'));
    const detailsOpen=panel.querySelector('.sampling-details')?.open;
    replaceHTML($('sampling-footer'),`${selection()}<details class="sampling-details"><summary>About these runs</summary><div><p><b>Student model:</b> ${esc(data.model)}</p><p><b>Starting point:</b> ${esc(data.input_label)}. Every sample starts here, before the original saved reaction.</p><p>These frequencies describe this model at one starting point. They do not predict a real student's behavior. A code edit can also include a message.</p><table><caption>Marginal 95% sampling intervals</caption><tbody>${data.categories.map(c=>`<tr><th scope="row">${esc(labels[c.decision])}</th><td>${c.interval?c.interval.map(percent).join(' – '):'Unavailable'}</td></tr>`).join('')}</tbody></table><p>Intervals assume independent, stable sampling. Zero observed does not mean impossible. Selecting an outcome makes no model request.</p></div></details>`);
    if(detailsOpen)panel.querySelector('.sampling-details').open=true;
    panel.querySelectorAll('[data-action]').forEach(button=>button.onclick=()=>{
      const sample=preview.data.samples.find(s=>s.decision===button.dataset.action);if(sample)choose(sample.index);
    });
    if(selectedSample()){
      const group=selectedGroup(),position=group.findIndex(s=>s.index===preview.selected);
      $('sample-previous').onclick=()=>{if(position>0)choose(group[position-1].index,true)};
      $('sample-next').onclick=()=>{if(position<group.length-1)choose(group[position+1].index,true)};
      $('original-reaction').onclick=restore;
      if($('open-selected'))$('open-selected').onclick=()=>choose(preview.selected);
      if(state.step===2){
        $('view-description').textContent=`Saved sample ${preview.selected} · ${labels[selectedSample().decision]} · After execution`;
        $('chat-caption').textContent=`Sample ${preview.selected} · After execution`;
        if(selectedSample().decision==='reply'){
          const turn=document.querySelector('#conversation-messages .chat-turn:last-of-type');
          turn?.classList.add('sampled-turn');
          const label=turn?.querySelector('.chat-identity > span');if(label)label.textContent=`Sample ${preview.selected} · Simulated`;
        }
      }
    }
    if(focused?.id&&document.activeElement!==focused){
      const target=$(focused.id);
      (target?.disabled?panel.querySelector('.sample-nav button:not(:disabled)'):target)?.focus({preventScroll:true});
    }
  }

  function schedulePoll(){
    clearTimeout(preview.timer);
    if(activeBatch())preview.timer=setTimeout(()=>load(true),2000);
  }

  function reconcile(data){
    const matched=preview.pending&&[...(data.batches||[]),data.active_batch].find(batch=>batch?.request_id===preview.pending.id);
    if(matched){preview.pending=null;preview.error='';notify(`Batch ${statusName(matched).toLowerCase()}: ${matched.finished} of ${matched.requested} finished.`)}
    if(preview.cancelling){
      const batch=[...(data.batches||[]),data.active_batch].find(batch=>batch?.id===preview.cancelling);
      if(batch&&(batch.cancel_requested||batch.status!=='running')){preview.cancelling=null;preview.error=''}
    }
  }

  async function readResponse(response){
    const data=await response.json();
    if(!response.ok){const error=new Error(typeof data.detail==='string'?data.detail:'The sampling request could not be completed.');error.status=response.status;throw error}
    return data;
  }

  async function load(poll=false){
    clearTimeout(preview.timer);
    const id=++preview.loadId,batch=preview.batch;
    if(!poll){preview.loading=true;renderPreview()}
    try{
      const response=await fetch('/api/next-actions'+(batch==='saved'?'':'?batch='+encodeURIComponent(batch)),{cache:'no-store',signal:AbortSignal.timeout(15000)});
      const data=await readResponse(response);
      if(id!==preview.loadId)return;
      preview.data=data;preview.readError='';reconcile(data);
      if(preview.pending&&!preview.pending.sending)preview.error='The start request has an unknown outcome. Check status before starting another batch; it will not be sent again automatically.';
    }catch(error){
      if(id!==preview.loadId)return;
      preview.readError=error.status?error.message:'Status could not be refreshed. Check the connection and try Check status.';
    }finally{
      if(id===preview.loadId){preview.loading=false;renderPreview();schedulePoll()}
    }
  }

  function selectBatch(id){
    if(id===preview.batch)return;
    restoreFrame();preview.batch=id;preview.error='';load();
  }

  async function startBatch(event){
    event.preventDefault();renderSetup();
    if($('sample-run-button').disabled)return;
    const data=preview.data;
    preview.pending={id:crypto.randomUUID(),sending:true};preview.error='';preview.readError='';
    clearTimeout(preview.timer);++preview.loadId;renderPreview();
    try{
      const response=await fetch('/api/next-actions/batches',{method:'POST',headers:{'Content-Type':'application/json','X-Workspace-Token':data.csrf_token},
        body:JSON.stringify({request_id:preview.pending.id,runs:Number(preview.runs),input_sha256:data.binding.input_sha256}),signal:AbortSignal.timeout(15000)});
      const snapshot=await readResponse(response);
      restoreFrame();preview.pending=null;preview.data=snapshot;preview.batch=snapshot.selected_batch||snapshot.active_batch?.id||'saved';preview.setup=false;
      renderPreview();$('next-actions-panel').scrollTop=0;
      ($('cancel-action-batch')||$('new-action-batch'))?.focus({preventScroll:true});
      notify('Sampling started. You can keep inspecting saved outcomes while it runs.');
    }catch(error){
      if(error.status&&error.status<500){preview.pending=null;preview.error=error.message}
      else{preview.pending.sending=false;preview.error='The start request has an unknown outcome. Checking saved status; no request will be resent.'}
      await load();
    }finally{renderPreview();schedulePoll()}
  }

  async function cancelBatch(){
    const batch=activeBatch();
    if(!batch||batch.cancel_requested||preview.cancelling)return;
    preview.cancelling=batch.id;preview.error='';renderPreview();
    try{
      const response=await fetch('/api/next-actions/batches/'+encodeURIComponent(batch.id)+'/cancel',{method:'POST',headers:{'X-Workspace-Token':preview.data.csrf_token},signal:AbortSignal.timeout(15000)});
      const data=await readResponse(response);
      preview.data={...preview.data,active_batch:data.active_batch,batches:data.batches};preview.cancelling=null;
      notify('Cancellation requested. The in-flight request may still finish.');
    }catch(error){
      if(error.status&&error.status<500){preview.cancelling=null;preview.error=error.message}
      else preview.error='Cancellation has an unknown outcome. Checking saved status; cancellation will not be resent automatically.';
    }
    await load();
  }

  // Keep the existing notebook/chat renderer; sampling polls only update this panel.
  const workspaceRender=render;
  render=function(){workspaceRender();renderPreview()};
  const workspaceStatus=renderOperationStatus;
  renderOperationStatus=function(){workspaceStatus();document.querySelector('.prototype-note').textContent=samplingMode()?'Next-action sampling · '+(preview.data.enabled?'Sending enabled':'Sending disabled'):'Design preview · Saved outcomes'};
  load();
})();
