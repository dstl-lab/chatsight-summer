'use strict';
// One verified student message with no execution, in the existing workspace.
(() => {
  const scoped=()=>current()?.archive_message===true;
  const waiting='Awaiting tutor · No reply is running';
  $('canvas').before($('playback'));

  const workspaceStatusText=statusText;
  statusText=function(f){
    if(!scoped())return workspaceStatusText(f);
    return f.archive_stage==='message'?waiting:f.archive_stage==='tutor'
      ?'Student has not acted':'Read only';
  };
  const workspacePendingNote=pendingReplyNote;
  pendingReplyNote=function(){return scoped()?waiting+'. Viewing this saved run sends nothing.':workspacePendingNote()};
  const workspaceReason=continuationReason;
  continuationReason=function(){return scoped()?'This saved student-controlled loop is read only.':workspaceReason()};

  const workspaceInspector=renderInspector;
  renderInspector=function(){
    if(!scoped())return workspaceInspector();
    const c=current(),f=frame();
    if(['context','controls','next-exercise','feedback'].includes(state.selected)){
      $('inspector').innerHTML='<div class="inspector-title">Saved run context</div><h2>Student-controlled continuation</h2>'
        +'<p>This is a simulated continuation from captured work, not recorded future student behavior.</p>'
        +'<p>No local execution was requested. The saved run stopped after the student’s message; no tutor reply is running. '
        +'No execution output, correctness verdict, or learning outcome is established.</p>'
        +'<p>Only the selected instructions, code cell, and supplied conversation are shown.</p><h3>Initialization</h3>'
        +block(c.initialization);
    }else if(state.selected==='work'){
      $('inspector').innerHTML='<div class="inspector-title">Saved evidence</div><h2>Notebook changes</h2>'
        +(f.changes.baseline_kind==='initial-work'?'<p>Initial selected-cell work.</p>'
          :`<p>Change from the previous displayed state, revision ${esc(f.changes.baseline_revision)}.</p>`)
        +(f.changes.unified_diff?block(f.changes.unified_diff):'<p>No source change.</p>');
    }else workspaceInspector();
  };

  function decorate(){
    const c=current(),f=c?.frames?.[state.step];
    if(!c||!f){$('playback').hidden=true;return}
    if(!scoped())return;
    document.querySelector('.prototype-note').textContent=(c.authored_demo===true?'Authored test data · ':'')+'Saved student-controlled loop';
    $('trail-title').textContent='Interaction timeline';
    $('trail-hint').textContent=`Step ${state.step+1} of ${c.frames.length} · ${c.model_decisions} student action · ${c.execution_calls} local executions`;
    $('trail').style.gridTemplateColumns=`repeat(${c.frames.length}, minmax(0, 1fr))`;
    $('trail').setAttribute('role','group');
    $('trail').setAttribute('aria-label','Saved student-controlled interaction timeline');
    $('trail').querySelectorAll('button[data-trail]').forEach(button=>{
      const index=Number(button.dataset.trail),event=c.frames[index];
      const [label,actor,icon]=event.archive_stage==='captured'
        ?['Captured',c.authored_demo===true?'Authored':'Recorded','notebook']
        :event.archive_stage==='tutor'?['Tutor reply','Tutor','tutor']
        :event.actions.some(action=>action.decision==='revise-work')?['Edit + message','Student','edit']
        :['Student message','Student','chat'];
      button.dataset.loopStage=event.archive_stage;
      button.setAttribute('aria-label',`${index+1}. ${label} · ${actor}`);
      // Base playback keeps its handlers, pressed state, and focus on these buttons.
      const html=`<span class="timeline-node" aria-hidden="true">${glyph(icon)}</span><span class="timeline-event">${label}</span><span class="timeline-actor">${actor}</span>`;
      if(button.innerHTML!==html)button.innerHTML=html;
    });
    const caption=document.querySelector('#canvas .notebook-document > .notebook-caption');
    if(caption)caption.textContent=f.archive_stage==='message'
      ?'No local check was requested. This revision has not been executed in this run; no course grade is established.'
      :'No execution result at this stage. No code was executed in this saved run.';
    const prompt=document.querySelector('#canvas .notebook-prompt');
    if(prompt)for(const key of ['title','aria-label'])prompt.setAttribute(key,f.archive_stage==='message'
      ?'This revision has not been executed in this run':'No execution result at this stage');
    if(f.archive_stage==='message'){
      const note=document.querySelector('#conversation-messages > p.quiet:last-child');
      if(note)note.textContent='This saved run stopped after the student’s message.';
    }
  }

  const workspaceRender=render;
  render=function(){if(current()?.frames?.[state.step])workspaceRender();decorate()};
  const workspaceOperationStatus=renderOperationStatus;
  renderOperationStatus=function(){workspaceOperationStatus();decorate()};
  if(current()?.frames?.[state.step])render();else decorate();
})();
