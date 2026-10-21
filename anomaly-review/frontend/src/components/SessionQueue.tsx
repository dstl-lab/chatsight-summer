import { Check, ChevronRight, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { metricCount, metricDuration, referenceLabel } from "../data";
import type { DemoSession, Priority } from "../types";
import { decisionLabel } from "../bundle";

interface SessionQueueProps {
  sessions: DemoSession[];
  selectedId: string;
  reviewedIds: Set<string>;
  onSelect: (id: string) => void;
}

const priorityLabel: Record<Priority, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
  none: "No priority",
  insufficient_data: "Insufficient data",
  routine: "Routine",
};

export function SessionQueue({ sessions, selectedId, reviewedIds, onSelect }: SessionQueueProps) {
  const [query, setQuery] = useState("");
  const [priority, setPriority] = useState<"all" | Priority>("all");
  const [decision, setDecision] = useState("all");
  const hasAnalysis = sessions.some(session => session.analysis);
  const visible = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return sessions.filter((session) => {
      const matchesText = !normalized || [session.student_id, session.question_id ?? "question unknown", session.scenario]
        .some((value) => value.toLowerCase().includes(normalized));
      const analysisState = session.analysis?.state;
      const matchesDecision = decision === "all" ||
        (decision === "not_analyzed" ? analysisState === "not_analyzed" : session.analysis?.decision === decision);
      return matchesText && (priority === "all" || session.priority === priority) && matchesDecision;
    });
  }, [priority, query, sessions, decision]);

  return (
    <aside className="queue-panel" aria-label="Session review queue">
      <div className="queue-heading">
        <h2>Sessions</h2>
        <span>{visible.length}</span>
      </div>
      <div className="queue-controls">
        <label className="search-control">
          <Search size={16} aria-hidden="true" />
          <span className="sr-only">Search sessions</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)}
                 placeholder="Search student or question" />
        </label>
        {hasAnalysis ? <><label className="select-control">
          <span className="sr-only">Filter by analysis decision</span>
          <select value={decision} onChange={event => setDecision(event.target.value)}>
            <option value="all">All analysis states</option>
            <option value="surface">Flagged for review</option>
            <option value="no_supported_finding">No supported finding</option>
            <option value="insufficient_evidence">Insufficient evidence</option>
            <option value="not_analyzed">Not analyzed</option>
          </select>
        </label>{sessions.some(session => session.fusion) && <label className="select-control">
          <span className="sr-only">Filter by combined priority</span>
          <select value={priority} onChange={(event) => setPriority(event.target.value as "all" | Priority)}>
            <option value="all">All priorities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="none">No priority</option>
            <option value="insufficient_data">Insufficient data</option>
          </select>
        </label>}</> : <label className="select-control">
          <span className="sr-only">Filter by priority</span>
          <select value={priority} onChange={(event) => setPriority(event.target.value as "all" | Priority)}>
            <option value="all">All priorities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
              <option value="low">Low</option>
            <option value="routine">Routine</option>
          </select>
        </label>}
      </div>
      <div className="queue-list">
        {visible.map((session) => (
          <button className={`queue-row ${selectedId === session.id ? "is-selected" : ""}`}
                  key={session.id} onClick={() => onSelect(session.id)}>
            <span className="queue-main">
              <span className="queue-title-line">
                <strong title={session.student_id}>{session.student_id.length > 18 ? `${session.student_id.slice(0, 10)}…${session.student_id.slice(-4)}` : session.student_id}</strong>
                {session.question_id && <span className="question-id">{session.question_id}</span>}
                {reviewedIds.has(session.id) && <Check size={14} className="reviewed-check" aria-label="Reviewed" />}
              </span>
              {hasAnalysis && session.timeline[0]?.occurred_at && <time className="queue-window-time" dateTime={session.timeline[0].occurred_at}>{new Date(session.timeline[0].occurred_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</time>}
            </span>
            {(!hasAnalysis || session.active_time.status === "known" || session.failed_checks_after_help.status === "known") && <span className="queue-evidence">
              <span><b>{metricDuration(session.active_time)}</b> <small>active</small></span>
              <span className="reference-copy">{session.reference_active_time.status === "illustrative" ? "Illustrative" : "Reference"} {referenceLabel(
                session.reference_active_time.lower_seconds,
                session.reference_active_time.upper_seconds,
              )}</span>
              <span><b>{metricCount(session.failed_checks_after_help)}</b> <small>post-help fails</small></span>
            </span>}
            <span className={`priority-text priority-text--${session.priority}`}>
              <i aria-hidden="true" /> {session.analysis ? decisionLabel(session) : session.priority ? priorityLabel[session.priority] : "Not ranked"}
            </span>
            <ChevronRight size={17} className="queue-chevron" aria-hidden="true" />
          </button>
        ))}
        {!visible.length && <p className="empty-state">No sessions match this filter.</p>}
      </div>
    </aside>
  );
}
