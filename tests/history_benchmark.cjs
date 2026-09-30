// Authored controller fixtures only: every request is a local, stubbed GET.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../apps/history-benchmark.js'),'utf8');
const esc=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const clone=value=>JSON.parse(JSON.stringify(value));
function fixture(){
  const cases=Array.from({length:10},(_,i)=>{
    const number=i+1;
    return {id:`course-account-v1-${String(number).padStart(2,'0')}`,number,title:`Case ${number}`,
      prefix:[{role:'student',text:`EARLIER_STUDENT_${number}`},{role:'tutor',text:`EARLIER_TUTOR_${number} <script>bad</script>`},
        {role:'student',text:`CURRENT_STUDENT_${number}`},{role:'tutor',text:`CURRENT_TUTOR_${number}`}],current_start:2,
      reference:{text:`REFERENCE_${number} <img onerror="bad">`,category:0,characters:30,newline:false,backtick:false},
      baseline:{visible_student_messages:2,form_score:.155,category_counts:[2,...Array(12).fill(0)],category_probabilities:[1,...Array(12).fill(0)]},
      conditions:['current-exchange','history'].map((id,arm)=>({id,title:arm?'History':'Current exchange',form_score:arm?.4:.43,
        counts:{reply:arm?5:3,'no-reply':arm?0:1,error:arm?0:1},character_mae:12,newline_rate:.2,backtick_rate:.4,
        draws:Array.from({length:5},(_,j)=>{
          const base={slot:`${number}-${id}-${j+1}`,draw:j+1};
          if(!arm&&j===3)return {...base,status:'complete',decision:'no-reply',text:'',form:{category:12,characters:null,newline:null,backtick:null},error_type:null};
          if(!arm&&j===4)return {...base,status:'error',decision:null,text:null,form:null,error_type:'Authored<Error>'};
          return {...base,status:'complete',decision:'reply',text:`DRAW_${number}_${id}_${j+1}\n<svg onload="bad"> \`literal\``,
            form:{category:7,characters:45,newline:true,backtick:true},error_type:null};
        })})),history_minus_current_exchange:-.03};
  });
  return {version:1,model:'authored-model',draws_per_condition:5,limits:['Authored limit <script>bad</script>'],cases,
    study:{population:'Authored ten-case fixture',scheduled_requests:100,counts:{'current-exchange':{reply:30,'no-reply':10,error:10},history:{reply:50,'no-reply':0,error:0}},
      primary:{condition_means:{'current-exchange':.43,history:.4},all_ten_mean:-.03,complete_pairs:10},baseline:{mean_form_score:.155},limits:['No semantic score.']}};
}
function harness(search=''){
  const nodes=new Map(),requests=[],state={mode:'simulate',caseIndex:0,step:2,selected:'turn:1',showInspector:true,
    refreshing:false,encounters:[{id:'direct',frames:[{source:'ORIGINAL_SOURCE'}]}],replyDraft:'KEEP_DRAFT'};
  const document={title:'Student simulation',activeElement:null,querySelector:selector=>node(selector)};
  function node(id){
    if(!nodes.has(id)){
      const classes=new Set();
      nodes.set(id,{id,innerHTML:'',textContent:'',hidden:false,disabled:false,value:'',title:'',attributes:{},scrollTop:0,
        classList:{toggle(name,on){on?classes.add(name):classes.delete(name)},contains:name=>classes.has(name)},
        insertAdjacentHTML(position,html){this.inserted={position,html}},setAttribute(key,value){this.attributes[key]=value},
        matches(){return Boolean(this.popoverOpen)},hidePopover(){this.popoverOpen=false},focus(){document.activeElement=this}});
    }
    return nodes.get(id);
  }
  const notebook=node('[data-mode="simulate"]');
  let notebookClicks=0,resetClicks=0,resolveReady;
  notebook.onclick=()=>{notebookClicks++};node('reset').onclick=()=>{resetClicks++};
  node('reset').title='Reload saved run without generating or executing';node('.breadcrumb').textContent='Notebook branch';
  node('body-grid').innerHTML='ORIGINAL_NOTEBOOK_DOM';node('policy-sampling-panel').popoverOpen=true;
  const h={state,node,document,requests,notebook,nextFetch:async()=>({ok:true,json:async()=>fixture()}),
    get notebookClicks(){return notebookClicks},get resetClicks(){return resetClicks},resolveReady:()=>resolveReady()};
  const context=vm.createContext({state,document,$:node,esc,glyph:()=>'<svg aria-hidden="true"></svg>',URLSearchParams,AbortSignal,
    window:{location:{search}},ready:new Promise(resolve=>{resolveReady=resolve}),notify(){},
    fetch(url,options){requests.push({url,options});return h.nextFetch()},
    render(){node('.breadcrumb').textContent='Notebook branch'},
    renderOperationStatus(){node('.reset-label').textContent='Reload saved run'}});
  vm.runInContext(source,context);h.context=context;return h;
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  const h=harness(),{node,notebook,state,document}=h,before=JSON.stringify(state);
  assert.equal(h.requests.length,0,'Opening the notebook does not fetch the benchmark');
  assert.equal(node('history-benchmark').hidden,true);
  await node('history-benchmark-tab').onclick();
  assert.equal(h.requests.length,1);assert.equal(node('body-grid').hidden,true);
  assert.equal(node('policy-sampling-panel').popoverOpen,false);
  assert.equal(node('history-benchmark-tab').attributes['aria-pressed'],'true');
  assert.equal(notebook.attributes['aria-pressed'],'false');
  assert.equal(node('.breadcrumb').textContent,'Historical chat');
  assert.equal(node('history-benchmark-case').innerHTML.match(/<option /g).length,10);
  for(let n=1;n<=10;n++){
    const html=node('history-benchmark-main').innerHTML,prefix=node('history-benchmark-prefix').innerHTML;
    assert.equal(node('history-benchmark-case').value,`course-account-v1-${String(n).padStart(2,'0')}`);
    assert.equal(html.match(/<li class="hb-draw">/g).length,10,'Every case displays all five draws in both arms');
    for(let d=1;d<=5;d++)assert.equal(html.match(new RegExp(`<h3>Draw ${d}</h3>`,'g')).length,2);
    assert.match(html,new RegExp(`REFERENCE_${n} &lt;img onerror=&quot;bad&quot;&gt;`));
    assert.match(html,new RegExp(`DRAW_${n}_history_5`));
    assert.doesNotMatch(prefix,/REFERENCE_/,'The observed target is never part of supplied input');
    assert.ok(prefix.indexOf(`EARLIER_STUDENT_${n}`)<prefix.indexOf(`EARLIER_TUTOR_${n}`));
    assert.ok(prefix.indexOf(`CURRENT_STUDENT_${n}`)<prefix.indexOf(`CURRENT_TUTOR_${n}`));
    assert.match(prefix,/<details class="hb-earlier"><summary>Earlier history · 2 messages/);
    assert.match(prefix,/<\/details><h3[^>]*>Current exchange · Both conditions/);
    assert.doesNotMatch(prefix,/<details[^>]*\bopen\b/,'Earlier history is collapsed by default');
    assert.match(html,/<details class="hb-study"[^>]*><summary>Study summary · form error 0\.430 → 0\.400/);
    assert.doesNotMatch(html,/<details[^>]*\bopen\b/,'Study details do not displace the outcomes initially');
    assert.ok(html.indexOf('</details></div></details>')<html.indexOf('class="hb-reference"'));
    assert.ok(html.indexOf('class="hb-reference"')<html.indexOf('class="hb-arms"'));
    assert.match(html,/One observed outcome, not the only plausible reply/);
    assert.match(html,/form-frequency distribution, not a text generator/);
    assert.match(html,/Missing outcome/);assert.match(html,/Authored&lt;Error&gt;/);
    assert.match(html,/missing data, not a student no-reply decision/);
    assert.match(html,/The model selected no reply/);
    assert.match(html,/45 characters · 41–300 characters · Newline · Backticks/);
    assert.doesNotMatch(html+prefix,/<script>|<img onerror|<svg onload/,'All source strings remain escaped literal text');
    if(n<10)node('history-benchmark-next').onclick();
  }
  assert.equal(h.requests.length,1,'Case navigation reuses the single verified snapshot');
  assert.equal(node('history-benchmark-next').disabled,true);
  assert.equal(document.activeElement,node('history-benchmark-case'),'Boundary navigation keeps keyboard focus on an enabled control');
  h.context.render();h.context.renderOperationStatus();
  assert.equal(node('body-grid').hidden,true);assert.equal(node('.reset-label').textContent,'Reload benchmark');
  assert.equal(node('.breadcrumb').textContent,'Historical chat');
  notebook.onclick();
  assert.equal(node('body-grid').hidden,false);assert.equal(node('body-grid').innerHTML,'ORIGINAL_NOTEBOOK_DOM');
  assert.equal(JSON.stringify(state),before,'Case, event, inspector, drafts and saved notebook data are untouched');
  assert.equal(h.notebookClicks,0,'Returning to Notebook does not run its selection-reset handler');
  assert.equal(document.title,'Student simulation');assert.equal(node('.breadcrumb').textContent,'Notebook branch');
  node('history-benchmark-tab').onclick();assert.equal(h.requests.length,1);
  assert.equal(node('history-benchmark-case').value,'course-account-v1-10');
  node('history-benchmark-previous').onclick();assert.equal(node('history-benchmark-case').value,'course-account-v1-09');
  node('history-benchmark-case').onchange({target:{value:'course-account-v1-01'}});
  assert.equal(node('history-benchmark-previous').disabled,true);

  let stopped=false;
  h.nextFetch=async()=>({ok:false,json:async()=>({detail:'Verification failed <unsafe>'})});
  await node('reset').onclick({stopImmediatePropagation(){stopped=true}});
  assert.equal(stopped,true,'Benchmark reload stops the separately installed policy reload listener');
  assert.equal(h.resetClicks,0);assert.equal(h.requests.length,2);
  assert.match(node('history-benchmark-main').innerHTML,/Verification failed &lt;unsafe&gt;/);
  assert.doesNotMatch(node('history-benchmark-main').innerHTML,/REFERENCE_|DRAW_/,'Failed verification clears previous outcomes');
  assert.doesNotMatch(node('history-benchmark-prefix').innerHTML,/CURRENT_|EARLIER_/);
  assert.equal(node('history-benchmark-case').innerHTML,'');assert.equal(node('history-benchmark-next').disabled,true);
  notebook.onclick();assert.equal(JSON.stringify(state),before);assert.equal(node('body-grid').hidden,false);

  // Returning while the GET is still pending must not strand the notebook reload button.
  node('history-benchmark-tab').onclick();
  let finish;
  h.nextFetch=()=>new Promise(resolve=>{finish=resolve});
  const loading=node('reset').onclick({stopImmediatePropagation(){}});
  assert.equal(node('reset').disabled,true);notebook.onclick();
  assert.equal(node('reset').disabled,false);assert.equal(node('reset').title,'Reload saved run without generating or executing');
  finish({ok:true,json:async()=>fixture()});await loading;
  assert.equal(node('reset').disabled,false);assert.equal(node('body-grid').hidden,false);
  assert.equal(JSON.stringify(state),before);
  node('history-benchmark-tab').onclick();
  h.nextFetch=async()=>({ok:true,json:async()=>({...fixture(),study:null})});
  await node('reset').onclick({stopImmediatePropagation(){}});
  assert.match(node('history-benchmark-main').innerHTML,/unsupported or incomplete shape/);
  assert.doesNotMatch(node('history-benchmark-main').innerHTML,/REFERENCE_|DRAW_/);
  for(const request of h.requests){assert.equal(request.url,'/api/history-benchmark');assert.equal(request.options.method,undefined,'No POST or generation request is sent')}

  const auto=harness('?view=benchmark');assert.equal(auto.requests.length,0);
  auto.resolveReady();await tick();
  assert.equal(auto.requests.length,1);assert.equal(auto.node('body-grid').hidden,true);
  assert.equal(auto.node('history-benchmark-case').value,'course-account-v1-01');
  console.log('History benchmark controller checks passed');
})().catch(error=>{console.error(error);process.exitCode=1});
