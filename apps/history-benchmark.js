'use strict';
// A separate read-only view; notebook selection, drafts and playback stay intact.
(() => {
  const benchmark={active:false,requested:false,loading:false,data:null,error:'',index:0};
  let notebookTitle,notebookBreadcrumb,notebookResetTitle;
  const notebook=document.querySelector('[data-mode="simulate"]');
  notebook.insertAdjacentHTML('afterend',`<button id="history-benchmark-tab" aria-controls="history-benchmark" aria-pressed="false">${glyph('compare')}History benchmark</button>`);
  $('body-grid').insertAdjacentHTML('afterend',`<section id="history-benchmark" aria-label="History benchmark" hidden>
    <header class="hb-header"><div><h1>History benchmark</h1><p id="history-benchmark-summary">Saved chat replies · Read only</p></div>
      <div class="hb-navigation" aria-label="Benchmark cases"><label for="history-benchmark-case">Case</label><select id="history-benchmark-case" disabled></select><button id="history-benchmark-previous" aria-label="Previous benchmark case" disabled>Previous</button><button id="history-benchmark-next" aria-label="Next benchmark case" disabled>Next</button></div></header>
    <div id="history-benchmark-main" class="hb-main" tabindex="0" aria-label="Saved benchmark outcomes"></div>
    <aside class="hb-context conversation-panel" aria-label="Supplied benchmark conversation"><header><h2>${glyph('chat')}Supplied conversation</h2><p class="small muted">The observed next message is excluded from these inputs.</p></header><div id="history-benchmark-prefix" tabindex="0" aria-label="Earlier history and current exchange"></div></aside>
  </section>`);

  const number=value=>typeof value==='number'&&Number.isFinite(value)?value.toFixed(3):'Unavailable';
  const percent=value=>typeof value==='number'&&Number.isFinite(value)?(100*value).toFixed(0)+'%':'Unavailable';
  const bin=characters=>characters<=40?'≤40 characters':characters<=300?'41–300 characters':'>300 characters';
  const form=value=>value?.category===12?'No-reply category':value
    ?`${value.characters} characters · ${bin(value.characters)} · ${value.newline?'Newline':'No newline'} · ${value.backtick?'Backticks':'No backticks'}`:'No form observation';
  const category=index=>index===12?'No reply':`${['≤40','41–300','>300'][Math.floor(index/4)]} characters · ${index%4>=2?'newline':'no newline'} · ${index%2?'backticks':'no backticks'}`;
  const counts=value=>`${value.reply} replies · ${value['no-reply']} no-reply · ${value.error} errors`;

  function sync(){
    $('app').classList.toggle('history-benchmark-active',benchmark.active);
    $('body-grid').hidden=benchmark.active;
    $('history-benchmark').hidden=!benchmark.active;
    $('history-benchmark-tab').setAttribute('aria-pressed',String(benchmark.active));
    notebook.setAttribute('aria-pressed',String(!benchmark.active&&state.mode==='simulate'));
    if(benchmark.active){
      notebook.disabled=false;
      document.title='Student simulation · History benchmark';
      document.querySelector('.breadcrumb').textContent='Historical chat';
      document.querySelector('.reset-label').textContent='Reload benchmark';
      $('reset').title='Reload the saved benchmark without generating replies';
      $('reset').disabled=benchmark.loading;
    }
  }

  function drawHTML(draw){
    const error=draw.status==='error',quiet=!error&&draw.decision==='no-reply';
    return `<li class="hb-draw"><header><h3>Draw ${esc(draw.draw)}</h3><span>${error?'Missing outcome':quiet?'No reply selected':'Saved reply'}</span></header>`
      +(error?`<p class="hb-missing">Saved request failed${draw.error_type?' · '+esc(draw.error_type):''}.</p><p class="hb-form">This is missing data, not a student no-reply decision.</p>`
        :quiet?'<p class="hb-no-reply">The model selected no reply.</p><p class="hb-form">A separate outcome, not an empty message.</p>'
        :`<p class="hb-message">${esc(draw.text)}</p><p class="hb-form">${esc(form(draw.form))}</p>`)
      +'</li>';
  }

  function armHTML(arm){
    return `<section class="hb-arm" aria-label="${esc(arm.title)}"><header><h2>${esc(arm.title)}</h2><p class="hb-score">Form score <b>${number(arm.form_score)}</b></p><p class="hb-form">${esc(counts(arm.counts))}</p>`
      +`<p class="hb-form">Reply draws only: character MAE ${arm.character_mae===null?'Unavailable':number(arm.character_mae)} · newline ${percent(arm.newline_rate)} · backtick ${percent(arm.backtick_rate)}</p></header>`
      +`<ol class="hb-draws" aria-label="All five saved draws">${arm.draws.map(drawHTML).join('')}</ol></section>`;
  }

  function prefixHTML(turns){
    return turns.map(turn=>`<article class="chat-turn ${turn.role==='student'?'student':'tutor'}"><header><span class="avatar ${turn.role==='tutor'?'tutor':''}" aria-hidden="true">${glyph(turn.role==='student'?'student':'tutor')}</span><b>${turn.role==='student'?'Student':'Tutor'}</b></header><div class="message-body"><p class="literal-message">${esc(turn.text)}</p></div></article>`).join('');
  }

  function renderBenchmark(){
    const data=benchmark.data,c=data?.cases[benchmark.index];
    $('history-benchmark-case').disabled=!c||benchmark.loading;
    $('history-benchmark-previous').disabled=!c||benchmark.loading||benchmark.index===0;
    $('history-benchmark-next').disabled=!c||benchmark.loading||benchmark.index===data.cases.length-1;
    if(!c){
      $('history-benchmark-summary').textContent=benchmark.loading?'Verifying saved benchmark…':'Saved benchmark unavailable';
      $('history-benchmark-main').innerHTML=benchmark.loading?'<p class="hb-empty" role="status">Loading verified cases and saved draws…</p>'
        :`<div class="hb-empty" role="alert"><h2>Benchmark unavailable</h2><p>${esc(benchmark.error||'No verified benchmark is loaded.')}</p><p>Use Reload benchmark to check again. Nothing will be generated.</p></div>`;
      $('history-benchmark-prefix').innerHTML='<p class="hb-empty">No verified conversation to display.</p>';
      $('history-benchmark-case').innerHTML='';sync();return;
    }
    $('history-benchmark-summary').textContent=`${data.cases.length} cases · ${data.draws_per_condition} saved draws per condition · ${data.model}`;
    $('history-benchmark-case').value=c.id;
    const study=data.study,primary=study.primary;
    const arms=['current-exchange','history'].map(id=>c.conditions.find(arm=>arm.id===id));
    const limits=[...new Set([...(data.limits||[]),...(study.limits||[])])];
    $('history-benchmark-main').innerHTML=`<details class="hb-study" aria-label="Aggregate form scores"><summary>Study summary · form error ${number(primary.condition_means['current-exchange'])} → ${number(primary.condition_means.history)} <span>Lower is better</span></summary><div class="hb-study-body"><p class="hb-form">${esc(study.population)} · ${esc(study.scheduled_requests)} scheduled requests</p>
      <table><thead><tr><th scope="col">Condition</th><th scope="col">Mean score</th><th scope="col">Saved outcomes</th></tr></thead><tbody>${arms.map(arm=>`<tr><th scope="row">${esc(arm.title)}</th><td>${number(primary.condition_means[arm.id])}</td><td>${esc(counts(study.counts[arm.id]))}</td></tr>`).join('')}<tr><th scope="row">Visible-message baseline</th><td>${number(study.baseline.mean_form_score)}</td><td>Observed distribution · not a generator</td></tr></tbody></table>
      <p class="hb-form">Model means use ${esc(primary.complete_pairs)} complete case pairs; baseline uses all ${data.cases.length} cases. All-case history minus current-exchange score: ${number(primary.all_ten_mean)}. Negative means lower literal form error.</p>
      <details class="hb-limits"><summary>Scope and limits</summary><p>Chat-only benchmark: notebook actions and real silence probabilities are unobserved. These cases were selected because a later student message was recorded. Form scores measure length, newlines, and backticks, not meaning, learning, or general realism.</p><ul>${limits.map(limit=>`<li>${esc(limit)}</li>`).join('')}</ul></details></div></details>
      <section class="hb-reference" aria-label="Observed next message"><header><h2>Observed next message</h2><span>Recorded reference · ${esc(c.title)}</span></header><p class="hb-message">${esc(c.reference.text)}</p><p class="hb-form">${esc(form(c.reference))}</p><p class="hb-reference-note">One observed outcome, not the only plausible reply. This message was not supplied to either condition.</p></section>
      <div class="hb-arms">${arms.map(armHTML).join('')}</div>
      <section class="hb-baseline" aria-label="Visible-message distribution baseline"><h2>Visible-message distribution baseline</h2><p>Form score <b>${number(c.baseline.form_score)}</b> from ${esc(c.baseline.visible_student_messages)} visible student messages. This is a form-frequency distribution, not a text generator.</p><p class="hb-form">Case history minus current-exchange score: ${number(c.history_minus_current_exchange)}.</p>
      <details><summary>All 13 form categories</summary><table><thead><tr><th scope="col">Form</th><th scope="col">Messages</th><th scope="col">Probability</th></tr></thead><tbody>${c.baseline.category_counts.map((count,i)=>`<tr><th scope="row">${category(i)}</th><td>${esc(count)}</td><td>${percent(c.baseline.category_probabilities[i])}</td></tr>`).join('')}</tbody></table></details></section>`;
    $('history-benchmark-prefix').innerHTML=`<details class="hb-earlier"><summary>Earlier history · ${c.current_start} messages<br><span>History condition only</span></summary>`
      +(c.current_start?prefixHTML(c.prefix.slice(0,c.current_start)):'<p class="hb-form">No earlier messages in this prefix.</p>')
      +'</details><h3 class="chat-section-label hb-current">Current exchange · Both conditions</h3>'+prefixHTML(c.prefix.slice(c.current_start));
    sync();
  }

  function selectCase(index,focus){
    if(benchmark.loading||!benchmark.data||index<0||index>=benchmark.data.cases.length)return;
    benchmark.index=index;renderBenchmark();
    $('history-benchmark-main').scrollTop=0;$('history-benchmark-prefix').scrollTop=0;
    if(focus&&$(focus).disabled)$('history-benchmark-case').focus({preventScroll:true});
    notify('History benchmark · '+benchmark.data.cases[index].title+'. All saved draws are shown.');
  }

  function valid(data){
    return data?.version===1&&data.draws_per_condition===5&&Array.isArray(data.cases)&&data.cases.length===10
      &&data.study?.primary?.condition_means&&data.study.counts&&data.study.baseline
      &&['current-exchange','history'].every(id=>data.study.counts[id])
      &&data.cases.every(c=>Array.isArray(c.prefix)&&Number.isInteger(c.current_start)&&c.current_start>=0&&c.current_start<c.prefix.length
        &&typeof c.reference?.text==='string'&&Array.isArray(c.conditions)&&c.conditions.length===2
        &&c.baseline?.category_counts?.length===13&&c.baseline.category_probabilities?.length===13
        &&['current-exchange','history'].every(id=>c.conditions.filter(arm=>arm.id===id).length===1)
        &&c.conditions.every(arm=>arm.counts&&arm.draws?.length===5&&arm.draws.every((draw,i)=>draw.draw===i+1
          &&(draw.status==='error'&&draw.decision===null&&draw.form===null
            ||draw.status==='complete'&&['reply','no-reply'].includes(draw.decision)&&typeof draw.text==='string'&&draw.form))));
  }

  async function load(){
    if(benchmark.loading)return;
    benchmark.requested=true;benchmark.loading=true;benchmark.data=null;benchmark.error='';renderBenchmark();
    try{
      const response=await fetch('/api/history-benchmark',{cache:'no-store',signal:AbortSignal.timeout(15000)});
      const data=await response.json();
      if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'The saved benchmark could not be verified.');
      if(!valid(data))throw new Error('The saved benchmark has an unsupported or incomplete shape.');
      benchmark.data=data;
      $('history-benchmark-case').innerHTML=data.cases.map(c=>`<option value="${esc(c.id)}">${esc(c.title)} · ${esc(c.number)} of ${data.cases.length}</option>`).join('');
    }catch(error){benchmark.error=error.name==='TimeoutError'?'The local backend did not respond in time.':error.message;benchmark.data=null}
    finally{benchmark.loading=false;renderBenchmark()}
  }

  function activate(){
    if(!benchmark.active){notebookTitle=document.title;notebookBreadcrumb=document.querySelector('.breadcrumb').textContent;notebookResetTitle=$('reset').title}
    benchmark.active=true;
    const panel=$('policy-sampling-panel');if(panel?.matches(':popover-open'))panel.hidePopover();
    sync();if(!benchmark.requested)return load();
  }
  $('history-benchmark-tab').onclick=activate;
  $('history-benchmark-case').onchange=event=>selectCase(benchmark.data?.cases.findIndex(c=>c.id===event.target.value));
  $('history-benchmark-previous').onclick=()=>selectCase(benchmark.index-1,'history-benchmark-previous');
  $('history-benchmark-next').onclick=()=>selectCase(benchmark.index+1,'history-benchmark-next');
  const notebookClick=notebook.onclick;
  notebook.onclick=function(event){
    if(!benchmark.active)return notebookClick?.call(this,event);
    benchmark.active=false;renderOperationStatus();document.title=notebookTitle;
    document.querySelector('.breadcrumb').textContent=notebookBreadcrumb;
    $('reset').disabled=Boolean(state.refreshing||state.comparisonLoading);$('reset').title=notebookResetTitle;sync();
  };
  const resetClick=$('reset').onclick;
  $('reset').onclick=function(event){
    if(!benchmark.active)return resetClick?.call(this,event);
    event?.stopImmediatePropagation();return load();
  };
  const workspaceRender=render;
  render=function(){workspaceRender();sync()};
  const workspaceStatus=renderOperationStatus;
  renderOperationStatus=function(){workspaceStatus();sync()};
  sync();
  if(new URLSearchParams(window.location.search).get('view')==='benchmark')Promise.resolve(ready).then(activate);
})();
