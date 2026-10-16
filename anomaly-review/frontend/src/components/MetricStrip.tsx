import { AlertCircle, Clock3, MessageSquareMore } from "lucide-react";
import { formatDuration, metricCount, metricDuration, referenceLabel } from "../data";
import type { DemoSession } from "../types";

export function MetricStrip({ session }: { session: DemoSession }) {
  const reference = session.reference_active_time;
  const active = session.active_time.status === "known" ? session.active_time.value : null;
  const max = Math.max(active ?? 0, reference.upper_seconds ?? 0, 1) * 1.12;
  const activeWidth = active === null ? 0 : Math.min(100, (active / max) * 100);
  const bandLeft = reference.lower_seconds === null ? 0 : (reference.lower_seconds / max) * 100;
  const bandWidth = reference.lower_seconds === null || reference.upper_seconds === null
    ? 0 : ((reference.upper_seconds - reference.lower_seconds) / max) * 100;

  return (
    <section className="metric-strip" aria-label="Behavioral metrics">
      <div className="metric-cell metric-cell--time">
        <div className="metric-label"><Clock3 size={15} /> Active time</div>
        <div className="metric-value">{metricDuration(session.active_time)}</div>
        <div className="comparison-track" aria-hidden="true">
          {reference.status === "illustrative" &&
            <span className="reference-band" style={{ left: `${bandLeft}%`, width: `${bandWidth}%` }} />}
          {active !== null && <span className="active-marker" style={{ left: `${activeWidth}%` }} />}
        </div>
        <div className="metric-detail">
          {reference.status === "illustrative" ? "Illustrative reference" : "Reference unavailable"}: {referenceLabel(reference.lower_seconds, reference.upper_seconds)} · Post-help: {metricDuration(session.post_help_active_time)}
        </div>
      </div>
      <div className="metric-cell">
        <div className="metric-label"><AlertCircle size={15} /> Failed checks after help</div>
        <div className="metric-value">{metricCount(session.failed_checks_after_help)}</div>
        <div className="metric-detail">{metricCount(session.repeated_failures)} repeated</div>
      </div>
      <div className="metric-cell">
        <div className="metric-label"><MessageSquareMore size={15} /> {session.analysis ? "Student messages" : "Tutor requests"}</div>
        <div className="metric-value">{metricCount(session.tutor_requests)}</div>
        <div className="metric-detail">{metricCount(session.completed_tutor_responses)} completed responses</div>
      </div>
    </section>
  );
}
