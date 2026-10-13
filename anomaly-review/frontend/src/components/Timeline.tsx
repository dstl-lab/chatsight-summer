import {
  Activity, Bot, Braces, CheckCircle2, CircleAlert, Clock3, Code2, MessageSquare,
  ChevronDown, Pause, Play, TerminalSquare, XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { filterTimeline, formatDuration, formatTimestamp, type TimelineFilter } from "../data";
import type { TimelineEvent } from "../types";

interface TimelineProps {
  events: TimelineEvent[];
  highlightedRefs: Set<string>;
}

const filters: { id: TimelineFilter; label: string }[] = [
  { id: "all", label: "All events" },
  { id: "conversation", label: "Conversation" },
  { id: "notebook", label: "Notebook" },
  { id: "checks", label: "Checks" },
];

function EventIcon({ event }: { event: TimelineEvent }) {
  const size = 17;
  if (event.kind === "student_message") return <MessageSquare size={size} />;
  if (event.kind === "tutor_response") return <Bot size={size} />;
  if (event.kind === "code_edit") return <Code2 size={size} />;
  if (event.kind === "execution") return <Play size={size} />;
  if (event.kind === "inactivity") return <Pause size={size} />;
  if (event.kind === "activity") return <Activity size={size} />;
  if (event.kind === "question_status") return <Braces size={size} />;
  if (event.title.includes("pass")) return <CheckCircle2 size={size} />;
  if (event.title.includes("fail")) return <XCircle size={size} />;
  return <CircleAlert size={size} />;
}

function phaseTitle(phase: TimelineEvent["phase"]): string | null {
  if (phase === "before_help") return "Before first completed tutor response";
  if (phase === "help_boundary") return "First completed tutor response";
  if (phase === "after_help") return "After first completed tutor response";
  if (phase === "ambiguous") return "Ordering uncertain";
  return null;
}

function CodeDiff({ before, after }: { before: string | null; after: string | null }) {
  return (
    <div className={`code-diff ${before === null ? "code-diff--single" : ""}`}>
      {before !== null && (
        <div className="diff-pane diff-pane--before">
          <span className="diff-label">Before</span>
          <pre><code>- {before}</code></pre>
        </div>
      )}
      <div className="diff-pane diff-pane--after">
        <span className="diff-label">{before === null ? "Submitted code" : "After"}</span>
        <pre><code>+ {after ?? "Source unavailable"}</code></pre>
      </div>
    </div>
  );
}

function TimelineCard({ event, highlighted }: { event: TimelineEvent; highlighted: boolean }) {
  const initiallyExpanded = event.kind === "student_message" || event.kind === "tutor_response";
  const [expanded, setExpanded] = useState(initiallyExpanded || highlighted);

  useEffect(() => {
    if (highlighted) setExpanded(true);
  }, [highlighted]);

  const checkTone = event.kind === "check_result"
    ? event.title.toLowerCase().includes("pass") ? "timeline-card--check-pass" : "timeline-card--check-fail"
    : "";

  return (
    <article id={event.source_event_id ? `event-${event.source_event_id}` : event.id}
             data-source-ref={event.id}
             className={`timeline-card timeline-card--${event.kind} ${checkTone} ${highlighted ? "is-highlighted" : ""}`}>
      <div className="timeline-node" aria-hidden="true"><EventIcon event={event} /></div>
      <div className="event-content">
        <button className="event-toggle" type="button" onClick={() => setExpanded((value) => !value)}
                aria-expanded={expanded}>
          <span className="event-heading">
            <span className="event-actor">{event.actor}</span>
            <h4>{event.title}</h4>
          </span>
          <span className="event-time"><Clock3 size={13} /> {formatTimestamp(event.occurred_at)}</span>
          <ChevronDown size={16} className={`event-chevron ${expanded ? "is-expanded" : ""}`} aria-hidden="true" />
        </button>
        {expanded && (
          <div className="event-details">
            {event.order_uncertain && <div className="uncertain-notice">Relative order at this timestamp is unknown.</div>}
            {event.kind === "inactivity" && event.duration_seconds !== undefined && (
              <div className="gap-duration">Observed gap: {formatDuration(event.duration_seconds)}</div>
            )}
            <p className={event.kind === "student_message" || event.kind === "tutor_response" ? "message-copy" : "event-copy"}>
              {event.body}
            </p>
            {event.code_diff && <CodeDiff before={event.code_diff.before} after={event.code_diff.after} />}
            {!!event.metadata.length && (
              <dl className="event-metadata">
                {event.metadata.map((item) => (
                  <div key={`${item.label}-${item.value}`}><dt>{item.label}</dt><dd>{item.value}</dd></div>
                ))}
              </dl>
            )}
            <footer className="trace-row">
              <TerminalSquare size={13} aria-hidden="true" />
              {event.source_event_id ? (
                <><span>Source event {event.source_event_id}</span><code>{event.id}</code></>
              ) : (
                <span>Derived from adjacent source events</span>
              )}
            </footer>
          </div>
        )}
      </div>
    </article>
  );
}

export function Timeline({ events, highlightedRefs }: TimelineProps) {
  const [filter, setFilter] = useState<TimelineFilter>("all");
  const visible = useMemo(() => filterTimeline(events, filter), [events, filter]);
  let previousPhase: TimelineEvent["phase"] | null = null;

  return (
    <section className="timeline-section" aria-labelledby="timeline-heading">
      <div className="section-heading-row">
        <div>
          <h3 id="timeline-heading">Session timeline</h3>
          <p>Student, tutor, notebook, and check activity in observed order.</p>
        </div>
        <div className="segmented-control" aria-label="Filter timeline events">
          {filters.map((item) => (
            <button key={item.id} className={filter === item.id ? "is-active" : ""}
                    onClick={() => setFilter(item.id)} aria-pressed={filter === item.id}>
              {item.label}
            </button>
          ))}
        </div>
      </div>
      <div className="timeline">
        {visible.map((event) => {
          const title = event.phase !== previousPhase ? phaseTitle(event.phase) : null;
          previousPhase = event.phase;
          return (
            <div key={event.id}>
              {title && <div className={`phase-divider phase-divider--${event.phase}`}>{title}</div>}
              <TimelineCard event={event} highlighted={highlightedRefs.has(event.id)} />
            </div>
          );
        })}
        {!visible.length && <p className="empty-state">No events match this timeline filter.</p>}
      </div>
    </section>
  );
}
