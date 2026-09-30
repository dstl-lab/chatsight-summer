'use strict';
// Saved samples share the workspace's notebook/chat renderer; choosing one never sends a request.
(() => {
  const comparison={data:null,error:'',loading:false,authoredDemo:null,encounters:null,originals:new Map(),selected:new Map()};
  const labels={'no-reply':'No further action',reply:'Send a message','revise-work':'Edit notebook'};
  const actionGlyph={'no-reply':'idle',reply:'chat','revise-work':'edit'};
  const tutorUnavailable=c=>['tutor-error','tutor-pending','pending'].includes(c.status);
  const unified=()=>comparison.data?.unified_workspace===true||state.encounters.some(c=>c.simulation_workspace===true);
  const workspaceLabel=()=>comparison.authoredDemo===true?'Authored test data · No live comparison results':comparison.data?'Tutor policy sampling · Saved results':'Tutor policy sampling · Loading saved results';
  const percent=value=>(100*value).toFixed(1)+'%';
  const condition=()=>comparison.data?.conditions.find(c=>c.id===current()?.id);
  const selectedSample=()=>condition()?.samples.find(s=>s.index===(unified()?current()?.sample_index:comparison.selected.get(condition().id)));
  const reactionIndex=sample=>sample?.timeline?.findIndex(f=>f.archive_reaction)??-1;
  const hasReaction=sample=>unified()?reactionIndex(sample)>=0:Boolean(sample?.reaction_frame);
  const group=()=>condition()?.samples.filter(s=>s.decision===selectedSample()?.decision)||[];
  const replaceHTML=(element,html)=>{if(element.policyHTML!==html){element.innerHTML=html;element.policyHTML=html}};

  function mount(){
    if($('policy-sampling-panel'))return;
    $('reset').insertAdjacentHTML('afterend','<button id="policy-sampling-toggle" popovertarget="policy-sampling-panel" aria-controls="policy-sampling-panel" aria-expanded="false"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="5" cy="5" r="2"/><circle cx="15" cy="5" r="2"/><circle cx="5" cy="15" r="2"/><path d="M5 7v6m2-3h3a5 5 0 0 0 5-3"/></svg>Compare next actions</button>');
    $('app').insertAdjacentHTML('beforeend',`<section popover="auto" id="policy-sampling-panel" class="sampling-panel policy-sampling-panel" aria-label="Compare sampled next actions">
      <header class="sampling-header"><div><h2 id="policy-sampling-title">What changes with the tutor reply?</h2><p id="policy-sampling-summary" role="status">Loading saved samples…</p></div><button class="sampling-close" id="hide-policy-sampling" aria-label="Hide next-action comparison">×</button></header>
      <div id="policy-sampling-error" class="sampling-error" role="alert" hidden></div><button id="reload-policy-sampling" class="text-action" hidden>Reload comparison</button>
      <p id="policy-comparison-scope" class="sampling-hint" hidden></p>
      <div id="policy-sampling-distribution"></div><div id="policy-sampling-footer" class="sampling-footer"></div>
    </section>`);
    $('policy-sampling-panel').addEventListener('toggle',()=>{
      $('policy-sampling-toggle').setAttribute('aria-expanded',String($('policy-sampling-panel').matches(':popover-open')));
    });
    $('hide-policy-sampling').onclick=closePanel;
    $('reload-policy-sampling').onclick=load;
    $('reset').addEventListener('click',load);
  }

  function closePanel(){
    $('policy-sampling-panel').hidePopover();
    $('policy-sampling-toggle').focus({preventScroll:true});
  }

  function open(id,index=null,keepOpen=false,step=1){
    const c=comparison.data?.conditions.find(c=>c.id===id),caseIndex=state.encounters.findIndex(c=>c.id===id);
    const baseline=comparison.originals.get(id),sample=c?.samples.find(s=>s.index===index);
    if(!c||tutorUnavailable(c)||caseIndex<0||!baseline||comparison.loading||state.refreshing||index!==null&&!sample)return;
    if(unified()&&sample&&!sample.timeline?.length)return;
    if(sample)comparison.selected.set(id,index);else comparison.selected.delete(id);
    state.caseIndex=caseIndex;
    if(unified()){
      if(sample){
        current().frames=structuredClone(sample.timeline);current().sample_index=index;
        current().execution_results=sample.timeline.filter(f=>f.archive_observation_new).length;
      }
      state.step=sample?step===2&&hasReaction(sample)?reactionIndex(sample):Math.min(2,current().frames.length-1):1;
      if($('run-details'))$('run-details').open=false;
    }else{
      current().frames=[current().frames[0],structuredClone(sample?sample.frame:baseline),
        ...(sample?.reaction_frame?[structuredClone(sample.reaction_frame)]:[])];
      state.step=step===2&&sample?.reaction_frame?2:1;
    }
    state.showInspector=false;state.selected='step';state.chatOpen=true;state.chatKey=null;
    render();if(!keepOpen)closePanel();
    document.querySelector('#canvas [aria-label="Selected code cell, read only"]')?.scrollIntoView({block:'start'});
    document.querySelector('#conversation-messages .chat-turn:last-of-type')?.scrollIntoView({block:'nearest'});
    notify(`${c.label} · ${sample?'saved sample '+index:'tutor reply'}. No generation or execution.`);
  }

  function outcome(c,key){
    const category=c.categories.find(row=>row.decision===key),count=category?.count||0;
    const selected=current()?.id===c.id&&state.step>0&&selectedSample()?.decision===key;
    const available=!tutorUnavailable(c)&&count>0&&c.samples.some(s=>s.decision===key)&&comparison.originals.has(c.id)&&!comparison.loading&&!state.refreshing;
    const frequency=category?.proportion,interval=category?.interval?.map(percent).join(' – ');
    return `<td><button class="policy-outcome" data-policy="${esc(c.id)}" data-outcome="${key}" aria-pressed="${selected}"${available?'':' disabled'} aria-label="${esc(c.label+': '+labels[key]+', '+count+' of '+c.valid+' valid samples'+(available?', inspect saved outcome':', none available'))}"${interval?` title="95% sampling interval: ${interval}"`:''}>
      <span class="action-count">${count}<span> / ${c.valid}</span></span><span class="action-percentage">${frequency===null||frequency===undefined?'—':percent(frequency)}</span>
      <span class="action-meter" aria-hidden="true"><span style="width:${Math.max(0,Math.min(100,100*(frequency||0)))}%"></span></span>
    </button></td>`;
  }

  function selection(){
    const sample=selectedSample(),c=condition();
    if(!sample)return '<p class="sampling-hint">'+(unified()?'Choose an outcome to open a saved policy sample in the main timeline.':'Choose an outcome to see its saved notebook and chat in Generated.')+'</p>';
    const samples=group(),position=samples.findIndex(s=>s.index===sample.index);
    const reactionStatus=(!hasReaction(sample)&&c.reaction?.sample_index===sample.index?{prepared:'Reaction not generated',pending:'Reaction pending',error:'Reaction unavailable'}[c.reaction.status]:null)
      ||(unified()&&!hasReaction(sample)?'No later student reaction saved':null);
    const actionStep=unified()?2:1,reactionStep=unified()?reactionIndex(sample):2;
    return `<div class="sample-selection"><span class="sample-selection-label"><span class="sample-dot" aria-hidden="true"></span>${esc(c.label)} · sample <b>${sample.index}</b></span><span class="sample-position">${position+1} of ${samples.length} in this action</span>${reactionStatus?`<span class="sample-position">${reactionStatus}</span>`:''}<div class="sample-nav" role="group" aria-label="Browse samples within this action"><button id="policy-sample-previous" aria-label="Previous saved sample"${position===0?' disabled':''}>‹</button><button id="policy-sample-next" aria-label="Next saved sample"${position===samples.length-1?' disabled':''}>›</button></div>${state.step!==actionStep?`<button id="policy-open-selected" class="text-action">${unified()?'View sampled action':'Open Generated'}</button>`:''}${hasReaction(sample)&&state.step!==reactionStep?'<button id="policy-open-reaction" class="text-action">View reaction</button>':''}<button id="policy-original-reply" class="text-action">${glyph('tutor')}Tutor reply</button></div>`;
  }

  function renderPanel(){
    mount();
    if(comparison.encounters!==state.encounters){
      comparison.encounters=state.encounters;comparison.originals.clear();comparison.selected.clear();
      state.encounters.forEach(c=>{if(c.frames[1])comparison.originals.set(c.id,structuredClone(c.frames[1]))});
    }
    const panel=$('policy-sampling-panel'),focused=panel.contains(document.activeElement)?document.activeElement:null;
    document.title=unified()?'Student simulation':'Student lab · Tutor policy sampling';
    $('app').classList.add('policy-sampling-workspace');
    if(!unified()){
      document.querySelector('.prototype-note').textContent=workspaceLabel();
      document.querySelector('.explorer-heading').textContent='Tutor policies';
      document.querySelector('.breadcrumb').textContent='Shared notebook checkpoint';
    }
    if(unified())replaceHTML($('policy-sampling-toggle'),glyph('compare')+'Compare samples');
    $('policy-sampling-title').textContent=unified()?'Compare saved samples':'What changes with the tutor reply?';
    $('policy-comparison-scope').hidden=!unified();
    $('policy-comparison-scope').textContent=unified()?'Earlier comparison · These independent policy samples are a separate run. Their counts do not describe the latest continuation.':'';
    $('policy-sampling-toggle').disabled=!state.encounters.length;
    if(!state.encounters.length&&panel.matches(':popover-open'))panel.hidePopover();
    $('policy-sampling-error').hidden=!comparison.error;$('policy-sampling-error').textContent=comparison.error;
    $('reload-policy-sampling').hidden=!comparison.error;$('reload-policy-sampling').disabled=comparison.loading;
    const data=comparison.data;
    $('policy-sampling-summary').textContent=comparison.loading?'Loading saved samples…':data?data.authored_demo?'Authored test data · No live comparison results':`${data.requested_per_condition} requested per policy · Same captured starting point`:'Comparison unavailable';
    if(!data){replaceHTML($('policy-sampling-distribution'),'');replaceHTML($('policy-sampling-footer'),'');return}
    replaceHTML($('policy-sampling-distribution'),`<table class="policy-frequency-table"><caption>${data.authored_demo?'Authored example action counts':'Observed model action frequencies'}</caption><thead><tr><th scope="col">Next action</th>${data.conditions.map(c=>`<th scope="col"><strong>${esc(c.label)}</strong><span class="policy-condition-count">${c.valid} valid · ${c.failed} failed</span><span class="policy-condition-count">${tutorUnavailable(c)?c.status==='tutor-error'?'Tutor failed · No student samples':'Tutor reply pending · No student samples':`${c.valid+c.failed} / ${c.requested} finished · ${esc(c.status)}`}</span><button class="text-action" data-tutor-policy="${esc(c.id)}"${comparison.loading||tutorUnavailable(c)||!comparison.originals.has(c.id)?' disabled':''}>${glyph('tutor')}${tutorUnavailable(c)?'Tutor reply unavailable':'View tutor reply'}</button></th>`).join('')}</tr></thead><tbody>${Object.keys(labels).map(key=>`<tr><th scope="row"><span class="policy-action-label">${glyph(actionGlyph[key])}<span>${labels[key]}</span></span></th>${data.conditions.map(c=>outcome(c,key)).join('')}</tr>`).join('')}</tbody></table>`);
    const detailsOpen=panel.querySelector('.sampling-details')?.open;
    replaceHTML($('policy-sampling-footer'),`${selection()}<details class="sampling-details"><summary>Policies and limits</summary><div><p><b>${data.authored_demo?'Configured model (not called)':'Student model'}:</b> ${esc(data.model)}</p><p>${data.authored_demo?'Tutor replies and student actions are authored examples for testing this interface. Counts and intervals are illustrative; no live comparison was run.':'Each available policy has one generated tutor reply, followed by independent student samples. Differences are conditional on those replies; they do not establish a general policy effect.'}</p><p>Percentages use valid samples only. ${data.authored_demo?'Example frequencies':'Model frequencies'} are not probabilities of real student behavior. A notebook edit may also include a message.</p><p>${data.continuation?`${data.execution_count} local source checks saved. Results attach to matching edits; repeated edits share one execution. Only the selected first sample per policy has a separate reaction request. Reactions are excluded from these counts, and any new edit is unexecuted. No course grade is established.`:'Source only: sampled edits are not executed or graded.'} Captured shows the shared state before either tutor reply.</p>${data.conditions.filter(c=>c.reaction).map(c=>`<p><b>${esc(c.label)} after execution:</b> sample ${c.reaction.sample_index} · ${esc(c.reaction.status)}${c.reaction.status==='error'?' · No reaction action saved.':''}</p>`).join('')}${data.conditions.map(c=>`<p><b>${esc(c.label)}:</b> ${esc(c.policy)}</p>`).join('')}<table><caption>${data.authored_demo?'Illustrative 95% intervals':'Marginal 95% sampling intervals'}</caption><thead><tr><th scope="col">Action</th>${data.conditions.map(c=>`<th scope="col">${esc(c.label)}</th>`).join('')}</tr></thead><tbody>${Object.keys(labels).map(key=>`<tr><th scope="row">${labels[key]}</th>${data.conditions.map(c=>`<td>${c.categories.find(row=>row.decision===key)?.interval?.map(percent).join(' – ')||'Unavailable'}</td>`).join('')}</tr>`).join('')}</tbody></table><p>Intervals assume independent, stable sampling. Zero observed does not mean impossible. Selecting an outcome makes no model request.</p></div></details>`);
    if(detailsOpen)panel.querySelector('.sampling-details').open=true;
    panel.querySelectorAll('[data-outcome]').forEach(button=>button.onclick=()=>{
      const c=data.conditions.find(c=>c.id===button.dataset.policy),sample=c?.samples.find(s=>s.decision===button.dataset.outcome);
      if(sample)open(c.id,sample.index);
    });
    panel.querySelectorAll('[data-tutor-policy]').forEach(button=>button.onclick=()=>open(button.dataset.tutorPolicy));
    const sample=selectedSample(),c=condition();
    if(sample){
      const samples=group(),position=samples.findIndex(s=>s.index===sample.index);
      $('policy-sample-previous').onclick=()=>{if(position>0)open(c.id,samples[position-1].index,true)};
      $('policy-sample-next').onclick=()=>{if(position<samples.length-1)open(c.id,samples[position+1].index,true)};
      $('policy-original-reply').onclick=()=>open(c.id);
      if($('policy-open-selected'))$('policy-open-selected').onclick=()=>open(c.id,sample.index);
      if($('policy-open-reaction'))$('policy-open-reaction').onclick=()=>open(c.id,sample.index,false,2);
    }
    if(c&&!unified()){
      $('version-captured').title='Shared captured notebook and conversation before either tutor reply';
      $('version-generated-description').textContent=tutorUnavailable(c)?'Tutor reply unavailable':sample?'Sampled student action':'Tutor reply · before student action';
      $('view-description').textContent=state.step===0?'Shared captured starting point · Before tutor reply':state.step===2?`${c.label} · Sample ${sample.index} · After execution · New edits are unexecuted`:tutorUnavailable(c)?`${c.label} · ${c.status==='tutor-error'?'Tutor generation failed':'Tutor reply pending'} · No student action sampled`:sample?`${c.label} · Sample ${sample.index} · ${labels[sample.decision]} · ${sample.frame.external_execution?'Saved local execution · No course grade':'Code not executed'}`:`${c.label} · Tutor reply · Student has not acted`;
      $('chat-caption').textContent=state.step===0?'Shared conversation · Before tutor reply':`${c.label} · ${tutorUnavailable(c)?'Tutor reply unavailable':sample?'Sample '+sample.index+(state.step===2?' · After execution':''):'Tutor reply'}`;
    }
    if(focused?.id&&document.activeElement!==focused){
      const target=$(focused.id);
      (target?.disabled?panel.querySelector('.sample-nav button:not(:disabled)'):target)?.focus({preventScroll:true});
    }
  }

  async function load(){
    if(comparison.loading)return;
    comparison.loading=true;comparison.error='';renderPanel();
    try{
      const response=await fetch('/api/policy-sampling',{cache:'no-store',signal:AbortSignal.timeout(15000)}),data=await response.json();
      if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'The saved comparison could not be loaded.');
      comparison.data=data;comparison.authoredDemo=data.authored_demo===true;
    }catch(error){comparison.error=error.name==='TimeoutError'?'The local backend did not respond in time. Reload the comparison.':error.message;comparison.data=null}
    finally{comparison.loading=false;renderPanel()}
  }

  const workspaceRender=render;
  render=function(){workspaceRender();renderPanel()};
  const workspaceStatus=renderOperationStatus;
  renderOperationStatus=function(){workspaceStatus();if(!unified())document.querySelector('.prototype-note').textContent=workspaceLabel()};
  load();
})();
