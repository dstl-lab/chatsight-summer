import { ArrowDown, Crosshair } from "lucide-react";
import { useState } from "react";
import type { DemoSession, ReviewRecord } from "../types";
import { MetricStrip } from "./MetricStrip";
import { ReviewPanel } from "./ReviewPanel";
import { Timeline } from "./Timeline";
import { decisionLabel } from "../bundle";

interface InvestigationViewProps {
  session: DemoSession;
  review?: ReviewRecord;
  onSaveReview: (review: ReviewRecord) => boolean | void;
}

export function InvestigationView({ session, review, onSaveReview }: InvestigationViewProps) {
  const [highlightedRefs, setHighlightedRefs] = useState<Set<string>>(new Set());
  const supportedFindings = session.analysis?.decision === "surface" ? session.analysis.findings : [];
  const analysisModel = session.analysis?.model;
  const modelLabel = analysisModel?.toLowerCase().includes("gemini") ? "Gemini" : analysisModel ?? "the model";

  function jumpToEvidence(refs: string[], eventIds: string[]) {
    setHighlightedRefs(new Set(refs));
    const targetId = refs[0] ? `ref-${refs[0]}` : eventIds[0] ? `event-${eventIds[0]}` : null;
    window.setTimeout(() => {
      if (targetId) document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 20);
  }

  return (
    <section className="investigation" aria-label={`Investigation for ${session.student_id}, ${session.question_id ?? "question unknown"}`}>
      <header className="investigation-header">
        <div className="title-block">
          <div className="title-context">
            <span>{session.assignment_id ?? "Assignment unknown"}</span>
            <span className="priority-context">{session.analysis ? decisionLabel(session) : `${session.priority} priority`}</span>
          </div>
          <h2>{session.analysis ? session.question_id ?? "Notebook session" : <>{session.student_id} <span>/</span> {session.question_id ?? "Question unknown"}</>}</h2>
          {session.analysis ? <details className="scope-details"><summary>Session details</summary><p>{session.student_id}</p><p>{session.scope === "notebook_session" ? "PR100 notebook observation window; question intent may be unknown" : session.scope === "conversation" ? "Conversation evidence; question scope is unverified" : "Question-scoped evidence"}</p><p>{session.analysis.model ?? "No model inference"}</p></details> : <p>{session.scenario}</p>}
        </div>
        {(!session.analysis || session.outcome.status === "known") && <div className="outcome-block">
          <span>Outcome</span>
          <strong className={session.outcome.status === "unknown" ? "is-unknown" : ""}>
            {session.outcome.status === "known" && session.outcome.value
              ? session.outcome.value.replaceAll("_", " ") : "Unknown"}
          </strong>
        </div>}
      </header>

      <MetricStrip session={session} />

      <section className="reason-section" aria-labelledby="reason-heading">
        <div className="reason-heading">
          <h3 id="reason-heading">{session.fusion ? "Combined review evidence" : session.analysis ? "Session findings" : "Why was this flagged?"}</h3>
          {!session.analysis && <span className="placeholder-note">Illustrative evidence</span>}
        </div>
        <div className="reason-list">
          {session.reasons.map((reason) => (
            <button key={reason.id} className="reason-item"
                    onClick={() => jumpToEvidence(reason.supporting_refs, reason.supporting_event_ids)}>
              <span className="reason-icon"><Crosshair size={15} /></span>
              <span><strong>{reason.title}</strong><small>{reason.description}</small></span>
              <span className="reason-action">View in timeline <ArrowDown size={13} /></span>
            </button>
          ))}
        </div>
        {session.fusion && <div className="fusion-summary" aria-label="Combined priority explanation">
          <p><strong>{decisionLabel(session)}</strong> · {session.fusion.summary}</p>
          <dl>
            <div><dt>Metrics</dt><dd>{session.fusion.metric_signal.status.replaceAll("_", " ")}{session.fusion.metric_signal.score !== null ? ` · score ${session.fusion.metric_signal.score.toFixed(1)}` : ""}</dd></div>
            <div><dt>Model</dt><dd>{session.fusion.llm_signal.status.replaceAll("_", " ")}</dd></div>
            <div><dt>Shared evidence</dt><dd>{session.fusion.shared_source_event_ids.length || session.fusion.shared_evidence_refs.length ? "Yes" : "No"}</dd></div>
          </dl>
          <p>{session.fusion.interpretation}</p>
        </div>}
        {session.analysis?.state === "completed" && <section className="model-rationale" aria-labelledby="model-rationale-heading">
          <div className="model-rationale-heading">
            <h4 id="model-rationale-heading">Why {supportedFindings.length ? `${modelLabel} supports review` : `${modelLabel} does not support review`}</h4>
            {!analysisModel && <span>Synthetic example, not Gemini output</span>}
          </div>
          <p>{session.analysis.summary}</p>
          {supportedFindings.map((finding, index) => <div className="model-rationale-finding" key={index}>
            <strong>{finding.category.replaceAll("_", " ")}</strong>
            <p>{finding.explanation}</p>
            <button onClick={() => jumpToEvidence(finding.highlight_ids, [])}>Show the evidence used</button>
          </div>)}
          {!supportedFindings.length && <p>The analysis did not find enough cited evidence to recommend review.</p>}
        </section>}
        {session.analysis && <div className="analysis-details">
          <p>{session.analysis.state === "not_analyzed" ? "Analyze this batch to generate findings." : session.analysis.summary}</p>
          {!!session.analysis.validation_errors.length && <ul>{session.analysis.validation_errors.map((error, index) => <li key={index}>{error}</li>)}</ul>}
          {session.analysis.findings.map((finding, index) => <details key={index} className="finding-detail">
            <summary>Evidence and uncertainty · finding {index + 1}</summary>
            {finding.interpretations.map((item, itemIndex) => <p key={itemIndex}>{item.statement} <button onClick={() => jumpToEvidence(item.evidence_ids, [])}>Show cited evidence</button></p>)}
            {!!finding.recovery_evidence_ids.length && <button onClick={() => jumpToEvidence(finding.recovery_evidence_ids, [])}>Show later recovery or correction</button>}
            <ul>{finding.uncertainties.map((notice, noticeIndex) => <li key={noticeIndex}>{notice}</li>)}</ul>
            <p>Evidence checks do not establish that the interpretation is correct or that the tutor caused an outcome.</p>
          </details>)}
        </div>}
        {!!session.quality_warnings.length && <details className="quality-notices"><summary>Evidence coverage and missing information ({session.quality_warnings.length})</summary><ul>{session.quality_warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></details>}
      </section>

      <div className="investigation-body">
        <Timeline events={session.timeline} highlightedRefs={highlightedRefs} />
        <ReviewPanel sessionId={session.id} review={review} onSave={onSaveReview} />
      </div>
    </section>
  );
}
