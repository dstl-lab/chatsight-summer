'use strict';
// Read-only design preview. The connected workspace owns notebook/chat rendering.
(() => {
  const preview = {data:null,error:'',setup:false,runs:30,selected:null,frames:null,original:null};
  const labels = {'no-reply':'No further action',reply:'Send a message','revise-work':'Edit notebook'};
  const symbols = {'no-reply':'<path d="M5 10h10"/>',reply:'<path d="M4 4h12v9H8l-4 3Z"/>','revise-work':'<path d="m5 13 8-8 3 3-8 8H5Zm6-6 3 3"/>'};
  const icon = body => `<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">${body}</svg>`;
  const selectedSample = () => preview.data?.samples.find(s=>s.index===preview.selected);
  const selectedGroup = () => preview.data.samples.filter(s=>s.decision===selectedSample()?.decision);
  const percent = value => (100*value).toFixed(1)+'%';
  const branchIcon = icon('<circle cx="5" cy="5" r="2"/><circle cx="15" cy="5" r="2"/><circle cx="5" cy="15" r="2"/><path d="M5 7v6m2-3h3a5 5 0 0 0 5-3"/>');

  function mount(){
    if($('next-actions-panel'))return;
    $('reset').insertAdjacentHTML('afterend',`<button id="next-actions-toggle" popovertarget="next-actions-panel" aria-controls="next-actions-panel" aria-expanded="false">${branchIcon}Next actions<span class="sample-count" id="next-actions-count">…</span></button>`);
    $('app').insertAdjacentHTML('beforeend','<section popover="auto" id="next-actions-panel" class="sampling-panel" aria-label="Sampled next actions"></section>');
    $('next-actions-panel').addEventListener('toggle',()=>{
      $('next-actions-toggle').setAttribute('aria-expanded',String($('next-actions-panel').matches(':popover-open')));
    });
  }

  function closePanel(){
    $('next-actions-panel').hidePopover();
    $('next-actions-toggle').focus({preventScroll:true});
  }

  function choose(index){
    const sample=preview.data?.samples.find(s=>s.index===index);
    if(!sample||!preview.original)return;
    preview.selected=index;current().frames[2]=structuredClone(sample.frame);
    state.step=2;state.showInspector=false;state.selected='step';state.chatOpen=true;state.chatKey=null;
    render();
    closePanel();
    document.querySelector('#canvas [aria-label="Selected code cell, read only"]')?.scrollIntoView({block:'start'});
    if(sample.decision==='reply')document.querySelector('#conversation-messages .chat-turn:last-of-type')?.scrollIntoView({block:'nearest'});
    notify(`Showing saved sample ${index}: ${labels[sample.decision].toLowerCase()}. No generation or execution.`);
  }

  function restore(){
    if(!preview.original)return;
    current().frames[2]=structuredClone(preview.original);preview.selected=null;
    state.step=2;state.showInspector=false;state.chatKey=null;render();
    closePanel();notify('Original saved reaction restored.');
  }

  function row(key){
    const category=preview.data.categories.find(c=>c.decision===key);
    const count=category?.count||0,proportion=category?.proportion||0;
    const selected=selectedSample()?.decision===key&&state.step===2;
    return `<button class="action-row" id="action-${key}" data-action="${key}" aria-pressed="${selected}"${count?'':' disabled'} aria-label="${esc(labels[key])}: ${count} of ${preview.data.valid} valid samples${count?', inspect saved outcome':', none observed'}">
      <span class="action-name">${icon(symbols[key])}<span>${labels[key]}</span></span>
      <span class="action-meter" aria-hidden="true"><span style="width:${Math.max(0,Math.min(100,100*proportion))}%"></span></span>
      <span class="action-count">${count}<span> / ${preview.data.valid}</span></span>
      <span class="action-percentage">${count?percent(proportion):'0 observed'}</span>
      <span class="action-open" aria-hidden="true">${selected?'✓':count?'›':'—'}</span>
    </button>`;
  }

  function selection(){
    const sample=selectedSample();
    if(!sample)return '<span class="sampling-hint">Choose an outcome to view it in Reaction.</span>';
    const group=selectedGroup(),position=group.findIndex(s=>s.index===sample.index);
    return `<div class="sample-selection"><span class="sample-selection-label"><span class="sample-dot" aria-hidden="true"></span>${state.step===2?'Viewing':'Selected'} sample <b>${sample.index}</b></span><span class="sample-position">${position+1} of ${group.length} in this action</span><div class="sample-nav" role="group" aria-label="Browse samples within this action"><button id="sample-previous" aria-label="Previous saved sample"${position===0?' disabled':''}>‹</button><button id="sample-next" aria-label="Next saved sample"${position===group.length-1?' disabled':''}>›</button></div>${state.step!==2?'<button id="open-selected" class="text-action">Open Reaction</button>':''}<button id="original-reaction" class="text-action">Original reaction</button></div>`;
  }

  function setup(){
    if(!preview.setup)return '';
    return `<form class="sampling-setup" id="sampling-setup"><div><label for="sampling-runs">Number of runs</label><div class="run-setting"><input id="sampling-runs" type="number" min="1" max="100" step="1" value="${preview.runs}" aria-describedby="sampling-budget sampling-preview-note"><button id="sample-run-button" class="primary" disabled>Run ${preview.runs} samples</button></div></div><p id="sampling-budget">${preview.runs} independent next-action requests from this same starting point.</p><p id="sampling-preview-note">Design preview: new sampling is not connected. The saved results below are from 30 completed runs.</p></form>`;
  }

  function renderPreview(){
    mount();if(!$('next-actions-panel'))return;
    document.querySelector('.prototype-note').textContent='Design preview · Saved outcomes';
    document.title='Student lab · Next actions preview';
    $('app').classList.add('next-actions-preview');
    if(current()?.frames!==preview.frames){
      preview.frames=current()?.frames;preview.original=preview.frames?.[2]?structuredClone(preview.frames[2]):null;preview.selected=null;
    }
    const panel=$('next-actions-panel');
    $('next-actions-toggle').disabled=!state.encounters.length;
    if(!state.encounters.length&&panel.matches(':popover-open'))panel.hidePopover();
    $('next-actions-count').textContent=preview.data?.attempts??'…';
    if(preview.error){panel.innerHTML=`<p class="sampling-error" role="alert">${esc(preview.error)}</p><button id="reload-action-data">Reload saved outcomes</button>`;$('reload-action-data').onclick=load;return}
    if(!preview.data){panel.innerHTML='<p class="sampling-hint" role="status">Loading saved next actions…</p>';return}
    const data=preview.data;
    panel.innerHTML=`<header class="sampling-header"><div><h2>What happens next?</h2><p>After execution <span aria-hidden="true">·</span> ${data.valid} saved outcomes${data.failed?` · ${data.failed} failed requests`:''}</p></div><button id="new-action-batch" class="text-action" aria-expanded="${preview.setup}" aria-controls="sampling-setup">${preview.setup?'Close setup':'New batch'}</button><button class="sampling-close" id="hide-next-actions" aria-label="Hide next actions">×</button></header>
      ${setup()}<div class="action-distribution" aria-label="Observed next-action frequencies">${row('no-reply')}${row('reply')}${row('revise-work')}</div>
      <div class="sampling-footer">${selection()}<details class="sampling-details"><summary>About these runs</summary><div><p><b>Student model:</b> ${esc(data.model)}</p><p><b>Starting point:</b> ${esc(data.input_label)}. Every sample starts here, before the original saved reaction.</p><p>These frequencies describe this model at one starting point. They do not predict a real student's behavior. A code edit can also include a message.</p><table><caption>Marginal 95% sampling intervals</caption><tbody>${data.categories.map(c=>`<tr><th scope="row">${esc(labels[c.decision])}</th><td>${c.interval?c.interval.map(percent).join(' – '):'Unavailable'}</td></tr>`).join('')}</tbody></table><p>Intervals assume independent, stable sampling. Zero observed does not mean impossible. Selecting an outcome makes no model request.</p></div></details></div>`;
    panel.querySelectorAll('[data-action]').forEach(button=>button.onclick=()=>{
      const sample=data.samples.find(s=>s.decision===button.dataset.action);if(sample)choose(sample.index);
    });
    $('hide-next-actions').onclick=closePanel;
    $('new-action-batch').onclick=()=>{preview.setup=!preview.setup;renderPreview();(preview.setup?$('sampling-runs'):$('new-action-batch')).focus()};
    if(preview.setup){
      $('sampling-setup').onsubmit=e=>e.preventDefault();
      $('sampling-runs').oninput=e=>{
        const input=e.target,valid=input.checkValidity()&&input.value!=='';
        input.setAttribute('aria-invalid',String(!valid));
        if(valid)preview.runs=Number(input.value);
        $('sample-run-button').textContent=valid?`Run ${input.value} samples`:'Run samples';
        $('sampling-budget').textContent=valid?`${input.value} independent next-action requests from this same starting point.`:'Choose a whole number from 1 to 100.';
      };
    }
    if(selectedSample()){
      const group=selectedGroup(),position=group.findIndex(s=>s.index===preview.selected);
      $('sample-previous').onclick=()=>{if(position>0)choose(group[position-1].index)};
      $('sample-next').onclick=()=>{if(position<group.length-1)choose(group[position+1].index)};
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
  }

  async function load(){
    preview.error='';renderPreview();
    try{
      const response=await fetch('/api/next-actions',{cache:'no-store'});
      if(!response.ok)throw new Error('The saved action batch could not be verified.');
      preview.data=await response.json();renderPreview();
    }catch(error){preview.error=error.message||'Saved outcomes are unavailable.';renderPreview()}
  }
  // ponytail: preview wraps the existing renderer; add an explicit hook if this becomes a shipped workspace feature.
  const workspaceRender=render;
  render=function(){workspaceRender();renderPreview()};
  const workspaceStatus=renderOperationStatus;
  renderOperationStatus=function(){workspaceStatus();document.querySelector('.prototype-note').textContent='Design preview · Saved outcomes'};
  load();
})();
