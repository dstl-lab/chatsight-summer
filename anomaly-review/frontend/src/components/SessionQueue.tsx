import { Check, ChevronRight, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { metricCount, metricDuration, referenceLabel } from "../data";
import type { DemoSession, Priority } from "../types";

interface SessionQueueProps {
  sessions: DemoSession[];
  selectedId: string;
  reviewedIds: Set<string>;
  onSelect: (id: string) => void;
}

const priorityLabel: Record<Priority, string> = {
  high: "High",
  medium: "Medium",
  routine: "Routine",
};

export function SessionQueue({ sessions, selectedId, reviewedIds, onSelect }: SessionQueueProps) {
  const [query, setQuery] = useState("");
  const [priority, setPriority] = useState<"all" | Priority>("all");
  const visible = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return sessions.filter((session) => {
      const matchesText = !normalized || [session.student_id, session.question_id, session.scenario]
        .some((value) => value.toLowerCase().includes(normalized));
      return matchesText && (priority === "all" || session.priority === priority);
    });
  }, [priority, query, sessions]);

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
        <label className="select-control">
          <span className="sr-only">Filter by priority</span>
          <select value={priority} onChange={(event) => setPriority(event.target.value as "all" | Priority)}>
            <option value="all">All priorities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="routine">Routine</option>
          </select>
        </label>
      </div>
      <div className="queue-list">
        {visible.map((session) => (
          <button className={`queue-row ${selectedId === session.id ? "is-selected" : ""}`}
                  key={session.id} onClick={() => onSelect(session.id)}>
            <span className="queue-main">
              <span className="queue-title-line">
                <strong>{session.student_id}</strong>
                <span className="question-id">{session.question_id}</span>
                {reviewedIds.has(session.id) && <Check size={14} className="reviewed-check" aria-label="Reviewed" />}
              </span>
            </span>
            <span className="queue-evidence">
              <span><b>{metricDuration(session.active_time)}</b> <small>active</small></span>
              <span className="reference-copy">Typical {referenceLabel(
                session.reference_active_time.lower_seconds,
                session.reference_active_time.upper_seconds,
              )}</span>
              <span><b>{metricCount(session.failed_checks_after_help)}</b> <small>post-help fails</small></span>
            </span>
            <span className={`priority-text priority-text--${session.priority}`}>
              <i aria-hidden="true" /> {priorityLabel[session.priority]}
            </span>
            <ChevronRight size={17} className="queue-chevron" aria-hidden="true" />
          </button>
        ))}
        {!visible.length && <p className="empty-state">No sessions match this filter.</p>}
      </div>
    </aside>
  );
}
