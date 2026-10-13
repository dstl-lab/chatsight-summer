import { ArrowDown, Crosshair } from "lucide-react";
import { useState } from "react";
import type { DemoSession, ReviewRecord } from "../types";
import { MetricStrip } from "./MetricStrip";
import { ReviewPanel } from "./ReviewPanel";
import { Timeline } from "./Timeline";

interface InvestigationViewProps {
  session: DemoSession;
  review?: ReviewRecord;
  onSaveReview: (review: ReviewRecord) => void;
}

export function InvestigationView({ session, review, onSaveReview }: InvestigationViewProps) {
  const [highlightedRefs, setHighlightedRefs] = useState<Set<string>>(new Set());

  function jumpToEvidence(refs: string[], eventIds: string[]) {
    setHighlightedRefs(new Set(refs));
    const targetId = eventIds[0] ? `event-${eventIds[0]}` : null;
    window.setTimeout(() => {
      if (targetId) document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 20);
  }

  return (
    <section className="investigation" aria-label={`Investigation for ${session.student_id}, ${session.question_id}`}>
      <header className="investigation-header">
        <div className="title-block">
          <div className="title-context">
            <span>{session.assignment_id}</span>
            <span className="priority-context">{session.priority} priority</span>
          </div>
          <h2>{session.student_id} <span>/</span> {session.question_id}</h2>
          <p>{session.scenario}</p>
        </div>
        <div className="outcome-block">
          <span>Outcome</span>
          <strong className={session.outcome.status === "unknown" ? "is-unknown" : ""}>
            {session.outcome.status === "known" && session.outcome.value
              ? session.outcome.value.replaceAll("_", " ") : "Unknown"}
          </strong>
        </div>
      </header>

      <MetricStrip session={session} />

      <section className="reason-section" aria-labelledby="reason-heading">
        <div className="reason-heading">
          <h3 id="reason-heading">Why was this flagged?</h3>
          <span className="placeholder-note">Illustrative evidence</span>
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
      </section>

      <div className="investigation-body">
        <Timeline events={session.timeline} highlightedRefs={highlightedRefs} />
        <ReviewPanel sessionId={session.id} review={review} onSave={onSaveReview} />
      </div>
    </section>
  );
}
