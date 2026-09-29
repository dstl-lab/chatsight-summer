'use strict';
// One verified saved loop, using the workspace's existing stages and renderers.
(() => {
  let encounters;
  const descriptions={
    captured:'Captured notebook and student question · No execution result at this stage.',
    tutor:'Saved tutor reply · Student has not acted.',
    edit:'Saved student edit · Generated before the local execution.',
    execution:'Researcher-triggered execution · Actual local output · No course grade.',
    reaction:'Saved next action after the local result · Any new edit is unexecuted.'
  };
  const events={
    captured:['Captured','Recorded','notebook'], tutor:['Tutor reply','Tutor','tutor'],
    edit:['Code edit','Student','edit'], execution:['Local run','Researcher','results'],
    reaction:['Next action','Student','student']
  };
  $('canvas').before($('playback'));

  function decorate(){
    const encounter=current(),selected=encounter?.frames?.[state.step];
    document.querySelector('.prototype-note').textContent=encounter?.loop_authored_demo===true?'Authored test data · Saved student loop':'Saved student loop';
    if(!encounter?.loop_example||!selected){$('playback').hidden=true;return}
    $('trail-title').textContent='Interaction timeline';
    $('trail-hint').textContent=`Step ${state.step+1} of ${encounter.frames.length}`;
    $('trail').setAttribute('role','group');
    $('trail').setAttribute('aria-label','Saved interaction timeline');
    $('trail').querySelectorAll('button[data-trail]').forEach(button=>{
      const index=Number(button.dataset.trail),stage=encounter.frames[index].loop_stage;
      const [label,origin,icon]=events[stage];
      const actor=stage==='captured'&&encounter.loop_authored_demo===true?'Authored':origin;
      button.dataset.loopStage=stage;
      button.setAttribute('aria-label',`${index+1}. ${label} · ${actor}`);
      // Keep the button itself: base playback owns its click handler and focus restoration.
      const content=`<span class="timeline-node" aria-hidden="true">${glyph(icon)}</span><span class="timeline-event">${label}</span><span class="timeline-actor">${actor}</span>`;
      if(button.innerHTML!==content)button.innerHTML=content;
    });
    $('view-description').textContent=selected.loop_stage==='reaction'&&selected.status==='no-reply'
      ?'Student chose no further action · No message or code change.'
      :descriptions[selected.loop_stage]||selected.label;
    if(['captured','tutor','edit'].includes(selected.loop_stage)){
      const caption=document.querySelector('#canvas .notebook-document > .notebook-caption');
      if(caption)caption.textContent='No execution result at this stage. Later stages show the saved local run; no course grade is established.';
      const prompt=document.querySelector('#canvas .notebook-prompt');
      if(prompt)for(const attribute of ['title','aria-label'])prompt.setAttribute(attribute,'No execution result at this stage');
    }
  }

  const workspaceRender=render;
  render=function(){
    if(encounters!==state.encounters){encounters=state.encounters;if(current()?.loop_example)state.step=0}
    if(state.encounters.length)workspaceRender();
    decorate();
  };
  const workspaceStatus=renderOperationStatus;
  renderOperationStatus=function(){workspaceStatus();decorate()};
  if(state.encounters.length)render();else decorate();
})();
