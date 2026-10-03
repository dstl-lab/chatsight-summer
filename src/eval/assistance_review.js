'use strict';
function validateResponse(response, packet, completed) {
  const fail = message => {throw new Error(message);};
  if (response.version !== 1 || response.rubric_id !== packet.rubric_id || response.packet_id !== packet.packet_id || response.phase !== packet.phase) fail('Wrong packet, rubric or stage.');
  if (!Array.isArray(response.judgments) || response.judgments.length !== packet.cases.length || new Set(response.judgments.map(j=>j.case_id)).size !== packet.cases.length) fail('Expected one judgment for every case.');
  if (completed && (!response.completed || !response.completed_at || !response.reviewer_alias?.trim() || !['yes','no','unsure'].includes(response.prior_exposure) || response.human_attestation !== true || response.no_prior_labels_or_model !== true || response.prefix_before_outcome !== true)) fail('Complete all reviewer declarations, including exposure and review order.');
  for (const c of packet.cases) {
    const j=response.judgments.find(j=>j.case_id===c.id);
    if (!j || !Array.isArray(j.evidence)) fail('Missing case or evidence list.');
    const allowed=new Set(c.turns.flatMap(t=>t.lines.map(l=>`${t.id}:${l.line}`)));
    const cited=j.evidence.map(e=>`${e.turn_id}:${e.line}`);
    if (new Set(cited).size!==cited.length || cited.some(k=>!allowed.has(k))) fail(`${c.id}: invalid evidence line.`);
    if (!completed) continue;
    if (!['definite','none','unclear'].includes(j.status)) fail(`${c.id}: choose a judgment.`);
    if (j.status==='definite' && (!Array.isArray(j.labels) || !j.labels.length || new Set(j.labels).size!==j.labels.length || j.labels.some(v=>!packet.kinds.includes(v)))) fail(`${c.id}: select supported assistance kinds.`);
    if (j.status==='none' && (!Array.isArray(j.labels) || j.labels.length)) fail(`${c.id}: No request must have an empty label set.`);
    if (j.status==='unclear' && (j.labels!==null || !j.note?.trim())) fail(`${c.id}: explain the uncertainty without guessing labels.`);
    if (!j.evidence.some(e=>e.turn_id===c.focus_turn_id)) fail(`${c.id}: cite the highlighted student message.`);
    if (j.status==='none' && c.turns.find(t=>t.id===c.focus_turn_id).lines.some(l=>!cited.includes(`${c.focus_turn_id}:${l.line}`))) fail(`${c.id}: cite every nonblank highlighted-message line for No request.`);
  }
  return true;
}
if (typeof module !== 'undefined') module.exports={validateResponse};
else {
  const packet=JSON.parse(document.getElementById('packet').textContent), $=id=>document.getElementById(id);
  let prefixHash=null;
  const node=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
  $('title').textContent=packet.phase==='prefix'?'Stage 1 · Previous student request':'Stage 2 · Next student request';
  packet.instructions.split('\n').forEach(p=>$('instructions').append(node('p',p)));
  packet.examples.forEach(([text,answer])=>{$('examples').append(node('p',text+' → '+answer));});
  if(packet.phase==='outcome'){$('gate').hidden=false;$('review').hidden=true;}
  for(const c of packet.cases){
    const article=node('article');article.className='case';article.id=c.id;article.append(node('h2',c.id));
    article.append(node('p','Judge the highlighted student message. Check source lines as evidence.'));
    for(const t of c.turns){
      const turn=node('section');turn.className='turn'+(t.id===c.focus_turn_id?' focus':'');
      turn.append(node('h3',`${t.id} · ${t.role}${t.id===c.focus_turn_id?' · message to judge':''}`));
      for(const l of t.lines){const label=node('label');label.className='source-line';const input=node('input');input.type='checkbox';input.dataset.turn=t.id;input.dataset.line=l.line;input.className='evidence';label.append(input,node('span',`${l.line}  ${l.text}`));turn.append(label);}
      article.append(turn);
    }
    const status=node('fieldset');status.append(node('legend','Judgment'));
    for(const [value,labelText] of [['definite','Definite expressed request'],['none','No expressed request'],['unclear','Unclear / insufficient context']]){const label=node('label'),input=node('input');input.type='radio';input.name=c.id+'-status';input.value=value;label.append(input,document.createTextNode(' '+labelText));status.append(label);}
    article.append(status);const kinds=node('fieldset');kinds.className='kinds';kinds.append(node('legend','Requested kinds — select only for a definite request'));
    for(const kind of packet.kinds){const label=node('label'),input=node('input');input.type='checkbox';input.value=kind;input.className='kind';input.disabled=true;label.append(input,document.createTextNode(' '+kind));kinds.append(label);}article.append(kinds);
    status.onchange=()=>{const definite=article.querySelector('input[type=radio]:checked')?.value==='definite';article.querySelectorAll('.kind').forEach(e=>{e.disabled=!definite;if(!definite)e.checked=false;});};
    const noteLabel=node('label','Notes / ambiguity (required for Unclear)'),note=node('textarea');note.className='note';noteLabel.append(note);article.append(noteLabel);$('cases').append(article);
  }
  function response(completed){
    return {version:1,rubric_id:packet.rubric_id,packet_id:packet.packet_id,phase:packet.phase,reviewer_alias:$('reviewer').value.trim()||null,prior_exposure:$('exposure').value||null,human_attestation:$('human').checked,no_prior_labels_or_model:$('independent').checked,prefix_before_outcome:$('ordered').checked,completed,completed_at:completed?new Date().toISOString():null,prefix_response_sha256:prefixHash,
      judgments:packet.cases.map(c=>{const a=$(c.id),status=a.querySelector('input[type=radio]:checked')?.value||null;return {case_id:c.id,status,labels:status==='definite'?[...a.querySelectorAll('.kind:checked')].map(e=>e.value):status==='none'?[]:null,evidence:[...a.querySelectorAll('.evidence:checked')].map(e=>({turn_id:e.dataset.turn,line:Number(e.dataset.line)})),note:a.querySelector('.note').value};})};
  }
  function save(completed){
    $('error').textContent='';try{const r=response(completed);validateResponse(r,packet,completed);const text=JSON.stringify(r,null,2)+'\n';$('output').value=text;const url=URL.createObjectURL(new Blob([text],{type:'application/json'})),a=node('a');a.href=url;a.download=`assistance-${packet.phase}-${completed?'complete':'draft'}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('status').textContent='Download requested. Check Downloads; the same JSON is available above.';}catch(e){$('error').textContent=e.message;}
  }
  $('save-draft').onclick=()=>save(false);$('save-complete').onclick=()=>save(true);
  $('prefix-file').onchange=async()=>{try{const file=$('prefix-file').files[0];if(!file)return;const text=await file.text(),r=JSON.parse(text);validateResponse(r,{...packet,packet_id:packet.prefix_packet_id,phase:'prefix',cases:packet.prefix_cases},true);const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));prefixHash=[...new Uint8Array(hash)].map(v=>v.toString(16).padStart(2,'0')).join('');$('reviewer').value=r.reviewer_alias;$('gate').hidden=true;$('review').hidden=false;$('error').textContent='';$('status').textContent='Completed prefix response bound. Its judgments are not displayed. Complete the stage 2 declarations separately.';}catch(e){$('error').textContent='Could not unlock stage 2: '+e.message;}};
}
