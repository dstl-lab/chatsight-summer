'use strict';
// Verified student-controlled segments, using the existing read-only workspace.
(() => {
  const scoped=()=>current()?.archive_message===true;
  const waiting='Awaiting tutor · No reply is running';
  $('canvas').before($('playback'));

  const workspaceStatusText=statusText;
  statusText=function(f){
    if(!scoped())return workspaceStatusText(f);
    if(f.status==='awaiting-tutor')return current().frames.slice(current().frames.indexOf(f)+1).some(next=>next.archive_stage==='tutor')
      ?'Awaiting the next saved tutor reply':waiting;
    const stopped={'no-reply':'Student chose no further action',
      'action-limit':'Action limit reached · No further decision generated',
      'check-limit':'Local run limit reached · No further code executed',
      'tutor-error':'Tutor reply failed · No student decision followed',
      error:'Student action failed · Saved run stopped',
      'environment-error':'Execution environment unavailable · Saved run stopped',
      'execution-limit':'Execution limit reached · Saved run stopped',
      'setup-error':'Execution setup failed · Saved run stopped'};
    return stopped[f.status]||(f.archive_stage==='tutor'?'Student has not acted'
      :f.archive_stage==='captured'?'Read only':f.archive_stage==='request-check'
      ?'Student requested local execution · Ungraded':'Saved student action');
  };
  const workspacePendingNote=pendingReplyNote;
  pendingReplyNote=function(){
    if(!scoped())return workspacePendingNote();
    return (current().frames.slice(state.step+1).some(next=>next.archive_stage==='tutor')?'A later saved tutor reply follows this message.'
      :state.step<current().frames.length-1?'The later tutor request failed; no reply was saved.'
      :frame().status==='tutor-error'?'The tutor request failed. No reply is running.':waiting+'.')
      +' Viewing this saved run sends nothing.';
  };
  const workspaceReason=continuationReason;
  continuationReason=function(){return scoped()?'This saved student-controlled loop is read only.':workspaceReason()};

  const workspaceNotebook=sourceOnlyNotebook;
  sourceOnlyNotebook=function(){
    const html=workspaceNotebook(),f=frame();
    if(!scoped()||!f.archive_observation)return html;
    // The selected code is the final code/pre pair; leave its source renderer intact.
    const marker='</code></pre>',end=html.lastIndexOf(marker)+marker.length;
    const title=(f.archive_observation_new?'Student-requested local execution':'Previously observed local result')
      +' · revision '+f.archive_observation.revision;
    return html.slice(0,end)+externalExecution(f.archive_observation,title)+html.slice(end);
  };

  const workspaceInspector=renderInspector;
  renderInspector=function(){
    if(!scoped())return workspaceInspector();
    const c=current(),f=frame();
    if(['context','controls','next-exercise','feedback'].includes(state.selected)){
      $('inspector').innerHTML='<div class="inspector-title">Saved run context</div><h2>Student-controlled continuation</h2>'
        +'<p>This is a simulated continuation from captured work, not recorded future student behavior.</p>'
        +(c.terminal_status==='tutor-error'?'<p>The new tutor request failed. No tutor reply or new student decision followed, and no new code was executed. No request is running.</p>'
          :c.archive_continuation?'<p>A separately saved tutor reply and bounded student continuation follow the original message. '
          +'Only student-requested runs can supply local output. Results belong to their source revision; edits clear current feedback. '
          +'Local execution is ungraded and establishes neither correctness nor learning. No request is running.</p>'
          :'<p>No local execution was requested. The saved run stopped after the student’s message; no tutor reply is running. '
          +'No execution output, correctness verdict, or learning outcome is established.</p>')
        +'<p>Only the selected instructions, code cell, and supplied conversation are shown.</p><h3>Initialization</h3>'
        +block(c.initialization);
    }else if(state.selected==='work'){
      $('inspector').innerHTML='<div class="inspector-title">Saved evidence</div><h2>Notebook changes</h2>'
        +(f.changes.baseline_kind==='initial-work'?'<p>Initial selected-cell work.</p>'
          :`<p>Change from the previous displayed state, revision ${esc(f.changes.baseline_revision)}.</p>`)
        +(f.changes.unified_diff?block(f.changes.unified_diff):'<p>No source change.</p>');
    }else if(state.selected==='step'&&f.archive_action_failed){
      $('inspector').innerHTML='<div class="inspector-title">Saved evidence</div><h2>Student action failed</h2>'
        +'<p>The attempted action did not complete. The notebook shows the saved work after the attempt.</p>'
        +(f.actions.length?'<h3>Requested action</h3>'+block(f.actions[0]):'<p>No valid student action was saved.</p>');
    }else workspaceInspector();
  };

  function decorate(){
    const c=current(),f=c?.frames?.[state.step];
    if(!c||!f){$('playback').hidden=true;return}
    if(!scoped())return;
    document.querySelector('.prototype-note').textContent=(c.authored_demo===true?'Authored test data · ':'')+'Saved student-controlled loop';
    $('trail-title').textContent='Interaction timeline';
    $('trail-hint').textContent=`Step ${state.step+1} of ${c.frames.length} · `
      +(c.archive_continuation?`${c.execution_results} local result${c.execution_results===1?'':'s'}`
        :`${c.model_decisions} student action · ${c.execution_calls} local executions`);
    $('trail').style.gridTemplateColumns=`repeat(${c.frames.length}, minmax(${c.frames.length>5?'76px':'0'}, 1fr))`;
    $('trail').style.overflowX=c.frames.length>5?'auto':'visible';
    $('trail').setAttribute('role','group');
    $('trail').setAttribute('aria-label','Saved student-controlled interaction timeline');
    $('trail').querySelectorAll('button[data-trail]').forEach(button=>{
      const index=Number(button.dataset.trail),event=c.frames[index];
      const [label,actor,icon]=event.archive_stage==='captured'
        ?['Captured',c.authored_demo===true?'Authored':'Recorded','notebook']
        :event.archive_stage==='tutor'?['Tutor reply','Tutor','tutor']
        :event.archive_stage==='tutor-error'?['Tutor failed','Tutor','tutor']
        :event.archive_action_failed?['Action failed','Student','idle']
        :event.archive_stage==='request-check'?[event.archive_observation_new?'Local run':'Run requested','Student','results']
        :event.archive_stage==='no-reply'?['No further action','Student','idle']
        :event.archive_stage==='error'?['Decision failed','Student','idle']
        :event.actions.some(action=>action.decision==='revise-work')
          ?[event.archive_stage==='message'||event.actions[0]?.text?'Edit + message':'Code edit','Student','edit']
        :['Student message','Student','chat'];
      button.dataset.loopStage=event.archive_stage;
      button.setAttribute('aria-label',`${index+1}. ${label} · ${actor}`);
      // Base playback keeps its handlers, pressed state, and focus on these buttons.
      const html=`<span class="timeline-node" aria-hidden="true">${glyph(icon)}</span><span class="timeline-event">${label}</span><span class="timeline-actor">${actor}</span>`;
      if(button.innerHTML!==html)button.innerHTML=html;
    });
    const caption=document.querySelector('#canvas .notebook-document > .notebook-caption');
    if(caption)caption.textContent=f.archive_observation
      ?f.archive_observation_new?'The student requested this local run. Its saved output is shown; this is not a course grade.'
        :'Previously observed result for this unchanged revision. No new execution result is available at this step.'
      :c.archive_continuation?'No execution result for this revision at this stage. No output or course grade is inferred.'
      :f.archive_stage==='message'?'No local check was requested. This revision has not been executed in this run; no course grade is established.'
      :'No execution result at this stage. No code was executed in this saved run.';
    const prompt=document.querySelector('#canvas .notebook-prompt');
    if(prompt)for(const key of ['title','aria-label'])prompt.setAttribute(key,f.archive_observation
      ?'Saved student-requested local result; no historical execution count is inferred'
      :f.archive_stage==='message'&&!c.archive_continuation?'This revision has not been executed in this run':'No execution result at this stage');
    if(f.status==='awaiting-tutor'){
      const note=document.querySelector('#conversation-messages > p.quiet:last-child');
      if(note)note.textContent=state.step<current().frames.length-1
        ?c.terminal_status==='tutor-error'?'The following stage shows the failed tutor request.'
          :'The following stage contains the saved tutor continuation.':'This saved run stopped after the student’s message.';
    }
  }

  const workspaceRender=render;
  render=function(){if(current()?.frames?.[state.step])workspaceRender();decorate()};
  const workspaceOperationStatus=renderOperationStatus;
  renderOperationStatus=function(){workspaceOperationStatus();decorate()};
  if(current()?.frames?.[state.step])render();else decorate();
})();
