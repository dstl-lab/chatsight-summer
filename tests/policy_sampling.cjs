// Authored controller contract; no model calls or private course fixtures.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const elements=new Map(),requests=[];
const document={activeElement:null,getElementById:id=>elements.get(id),querySelector:s=>elements.get(s.replace(/^\./,''))||null};
function node(id){if(document.activeElement===elements.get(id))document.activeElement=null;const n={id,textContent:'',hidden:false,disabled:false,open:false,dataset:{},classList:{add(){}},setAttribute(){},addEventListener(){},focus(){if(!this.disabled)document.activeElement=this},matches(){return this.open},hidePopover(){this.open=false},contains(child){return !!child&&child.id.startsWith('policy-sample-')&&elements.get(child.id)===child},insertAdjacentHTML(_pos,html){register(html)},querySelector:s=>s==='.sampling-details'?elements.get('sampling-details'):s==='.sample-nav button:not(:disabled)'?['policy-sample-previous','policy-sample-next'].map(id=>elements.get(id)).find(n=>n&&!n.disabled):null,querySelectorAll:s=>[...elements.values()].filter(n=>s==='[data-outcome]'?n.dataset.outcome:s==='[data-tutor-policy]'?n.dataset.tutorPolicy:false)};Object.defineProperty(n,'innerHTML',{set(html){this.html=html;register(html)},get(){return this.html||''}});elements.set(id,n);return n}
function register(html){for(const m of html.matchAll(/<[^>]+>/g)){const id=m[0].match(/id="([^"]+)"/),policy=m[0].match(/data-policy="([^"]+)"/),outcome=m[0].match(/data-outcome="([^"]+)"/),tutor=m[0].match(/data-tutor-policy="([^"]+)"/);if(id||outcome||tutor){const n=node(id?.[1]||outcome&&policy[1]+':'+outcome[1]||'tutor:'+tutor[1]);n.disabled=/\sdisabled(?:\s|>)/.test(m[0]);if(policy)n.dataset.policy=policy[1];if(outcome)n.dataset.outcome=outcome[1];if(tutor)n.dataset.tutorPolicy=tutor[1]}}if(html.includes('class="sampling-details"'))node('sampling-details')}
['app','reset','view-description','chat-caption','prototype-note','explorer-heading','breadcrumb','version-captured','version-generated-description'].forEach(node);
const originals=['direct','hint'].map(id=>({id,frames:[{work:{source:'shared'}},{work:{source:id+' baseline'}}]}));
const state={encounters:structuredClone(originals),caseIndex:0,step:1};
const data={authored_demo:true,model:'authored',requested_per_condition:2,conditions:['direct','hint'].map(id=>({id,label:id,policy:'Authored policy',requested:2,valid:2,failed:0,status:'complete',categories:[{decision:'revise-work',count:2,proportion:1,interval:[0.1,1]}],samples:[1,2].map(index=>({index,decision:'revise-work',frame:{work:{source:id+' sample '+index}}}))}))};
data.continuation=true;
for(const c of data.conditions){c.reaction={sample_index:1,status:'complete'};for(const sample of c.samples)sample.frame.external_execution={status:'ok'};c.samples[0].reaction_frame={work:{source:c.id+' after feedback'},reaction:{status:'complete'}}}
const context=vm.createContext({document,state,structuredClone,AbortSignal,$:id=>elements.get(id),esc:String,glyph:()=>'<svg aria-hidden="true" focusable="false"></svg>',current:()=>state.encounters[state.caseIndex],notify(){},render(){},renderOperationStatus(){},fetch:async(url,opts)=>{requests.push({url,opts});return {ok:true,json:async()=>structuredClone(data)}}});
const tick=async()=>{for(let i=0;i<4;i++)await new Promise(setImmediate)};
(async()=>{vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../apps/policy-sampling.js'),'utf8'),context);await tick();
context.renderOperationStatus();assert.equal(elements.get('prototype-note').textContent,'Authored test data · No live comparison results');assert.match(elements.get('policy-sampling-summary').textContent,/No live comparison results/);assert.match(elements.get('policy-sampling-footer').innerHTML,/Configured model \(not called\)/);
elements.get('direct:revise-work').onclick();assert.equal(state.caseIndex,0);assert.equal(state.encounters[0].frames[1].work.source,'direct sample 1');assert.equal(state.encounters[1].frames[1].work.source,'hint baseline');
assert.equal(state.encounters[0].frames.length,3);assert.match(elements.get('view-description').textContent,/Saved local execution/);elements.get('policy-open-reaction').onclick();assert.equal(state.step,2);assert.equal(state.encounters[0].frames[2].work.source,'direct after feedback');assert.match(elements.get('view-description').textContent,/After execution/);
const panel=elements.get('policy-sampling-panel');assert.equal(panel.open,false);
panel.open=true;elements.get('policy-sample-next').focus();elements.get('policy-sample-next').onclick();assert.equal(state.encounters[0].frames[1].work.source,'direct sample 2');assert.equal(panel.open,true,'Next must keep the comparison open');assert.equal(document.activeElement,elements.get('policy-sample-previous'),'At the last sample, focus moves to Previous');
assert.equal(state.encounters[0].frames.length,2,'Selecting another draw must clear the prior reaction');assert.equal(state.step,1);
elements.get('policy-sample-previous').onclick();assert.equal(state.encounters[0].frames[1].work.source,'direct sample 1');assert.equal(panel.open,true,'Previous must keep the comparison open');assert.equal(document.activeElement,elements.get('policy-sample-next'),'At the first sample, focus moves to Next');
elements.get('hide-policy-sampling').onclick();assert.equal(panel.open,false);assert.equal(document.activeElement,elements.get('policy-sampling-toggle'));
elements.get('hint:revise-work').onclick();assert.equal(state.caseIndex,1);assert.equal(state.encounters[1].frames[1].work.source,'hint sample 1');
elements.get('tutor:direct').onclick();assert.equal(state.encounters[0].frames[1].work.source,'direct baseline');assert.equal(state.encounters[1].frames[1].work.source,'hint sample 1');
assert.equal(state.encounters[0].frames.length,2,'Restoring the tutor must clear its sample reaction');
state.encounters=structuredClone(originals);context.render();elements.get('hint:revise-work').onclick();elements.get('policy-original-reply').onclick();assert.equal(state.encounters[1].frames[1].work.source,'hint baseline');assert.deepEqual(state.encounters[0].frames[0],originals[0].frames[0]);assert.equal(requests.length,1);
for(const [status,label] of [['prepared','Reaction not generated'],['pending','Reaction pending'],['error','Reaction unavailable']]){data.conditions[0].reaction.status=status;delete data.conditions[0].samples[0].reaction_frame;await elements.get('reload-policy-sampling').onclick();elements.get('direct:revise-work').onclick();assert.equal(state.encounters[0].frames.length,2);assert.ok(elements.get('policy-sampling-footer').innerHTML.includes(label));elements.get('policy-sample-next').onclick();assert.ok(!elements.get('policy-sampling-footer').innerHTML.includes(label),'Reaction status belongs only to its selected sample')}
for(const status of ['tutor-error','tutor-pending','pending']){data.conditions[0].status=status;await elements.get('reload-policy-sampling').onclick();assert.equal(elements.get('tutor:direct').disabled,true);assert.equal(elements.get('direct:revise-work').disabled,true);const before=JSON.stringify(state.encounters);elements.get('tutor:direct').onclick();assert.equal(JSON.stringify(state.encounters),before);state.caseIndex=0;context.render();assert.match(elements.get('view-description').textContent,/No student action sampled/)}
data.authored_demo=false;await elements.get('reload-policy-sampling').onclick();assert.equal(elements.get('prototype-note').textContent,'Tutor policy sampling · Saved results');assert.match(elements.get('policy-sampling-distribution').innerHTML,/Observed model action frequencies/);

// Unified view: panel counts stay separate, while each sample replaces its full main timeline.
data.unified_workspace=true;
for(const c of data.conditions){
  c.status='complete';c.reaction={sample_index:1,status:'complete'};
  for(const sample of c.samples){
    sample.timeline=[
      {archive_stage:'captured',work:{source:'shared'}},
      {archive_stage:'tutor',work:{source:c.id+' baseline'}},
      {archive_stage:'revise-work',work:{source:c.id+' sample '+sample.index}},
      {archive_stage:'researcher-check',work:{source:c.id+' sample '+sample.index},archive_observation:{status:'ok'},archive_observation_new:true,archive_observation_actor:'researcher'},
      ...(sample.index===1?[{archive_stage:'no-reply',archive_reaction:true,work:{source:c.id+' sample '+sample.index},archive_observation:{status:'ok'},archive_observation_new:false,archive_observation_actor:'researcher'}]:[])];
  }
}
const latest={id:'archive-message',simulation_workspace:true,archive_message:true,frames:[{work:{source:'LATEST SAVED SOURCE'}}]};
state.encounters=[...data.conditions.map(c=>({id:c.id,simulation_workspace:true,archive_message:true,policy_sample:true,
  policy_label:c.label,sample_index:1,frames:structuredClone(c.samples[0].timeline)})),structuredClone(latest)];
state.caseIndex=2;state.step=0;
elements.get('prototype-note').textContent='Read only';elements.get('view-description').textContent='WORKSPACE TIMELINE';
node('run-details').open=true;
await elements.get('reload-policy-sampling').onclick();
assert.equal(document.title,'Student simulation');
assert.equal(elements.get('prototype-note').textContent,'Read only','Comparison metadata must not overwrite the selected run identity');
assert.match(elements.get('policy-sampling-toggle').innerHTML,/Compare samples/);
assert.match(elements.get('policy-comparison-scope').textContent,/separate run.*do not describe the latest continuation/);
assert.match(elements.get('policy-sampling-footer').innerHTML,/main timeline/);
const requestCount=requests.length;
elements.get('direct:revise-work').onclick();
assert.equal(state.caseIndex,0);assert.equal(state.step,2);assert.equal(state.encounters[0].sample_index,1);
assert.equal(state.encounters[0].frames.length,5);assert.equal(state.encounters[0].execution_results,1);
assert.doesNotMatch(elements.get('policy-sampling-footer').innerHTML,/No later student reaction saved/);
assert.ok(state.encounters[0].frames.every(f=>!f.external_execution&&!f.reaction));
assert.equal(elements.get('view-description').textContent,'WORKSPACE TIMELINE','Archive adapter owns timeline descriptions');
assert.equal(elements.get('run-details').open,false);
elements.get('policy-open-reaction').onclick();assert.equal(state.step,4);
panel.open=true;elements.get('policy-sample-next').focus();elements.get('policy-sample-next').onclick();
assert.equal(state.step,2);assert.equal(state.encounters[0].sample_index,2);assert.equal(state.encounters[0].frames.length,4);
assert.ok(state.encounters[0].frames.every(f=>!f.archive_reaction),'A different sample must remove the first sample’s reaction');
assert.match(elements.get('policy-sampling-footer').innerHTML,/No later student reaction saved/);
assert.equal(panel.open,true);assert.equal(document.activeElement,elements.get('policy-sample-previous'));
const chosenTimeline=JSON.stringify(state.encounters[0].frames);
elements.get('policy-original-reply').onclick();
assert.equal(state.step,1);assert.equal(state.encounters[0].sample_index,2);
assert.equal(JSON.stringify(state.encounters[0].frames),chosenTimeline,'Viewing the tutor does not discard the selected sample timeline');
state.refreshing=true;const beforeRefresh=JSON.stringify(state.encounters);
elements.get('hint:revise-work').onclick();assert.equal(JSON.stringify(state.encounters),beforeRefresh);
state.refreshing=false;state.caseIndex=2;state.step=0;context.render();
assert.deepEqual(state.encounters[2],latest,'Earlier samples never mutate the latest continuation');
assert.equal(elements.get('prototype-note').textContent,'Read only');
assert.match(elements.get('policy-sampling-footer').innerHTML,/main timeline/);
assert.equal(requests.length,requestCount,'Choosing and cycling saved samples adds no requests');
assert.ok(requests.every(r=>r.opts.method===undefined));
console.log('Policy sampling: standalone behavior, unified timelines, selected sample isolation, cycling focus, separate comparison scope and GET-only pass');
})().catch(e=>{console.error(e);process.exitCode=1});
