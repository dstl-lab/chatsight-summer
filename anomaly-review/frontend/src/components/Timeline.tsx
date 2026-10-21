import {
  Activity, Bot, Braces, CheckCircle2, CircleAlert, Code2, MessageSquare,
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
  const size = 14;
  if (event.kind === "student_message") return <MessageSquare size={size} />;
  if (event.kind === "tutor_response") return <Bot size={size} />;
  if (event.kind === "code_edit" || event.kind === "code_capture") return <Code2 size={size} />;
  if (event.kind === "execution") return <Play size={size} />;
  if (event.kind === "inactivity") return <Pause size={size} />;
  if (event.kind === "activity") return <Activity size={size} />;
  if (event.kind === "question_status") return <Braces size={size} />;
  if (event.title.includes("pass")) return <CheckCircle2 size={size} />;
  if (event.title.includes("fail")) return <XCircle size={size} />;
  return <CircleAlert size={size} />;
}

function phaseTitle(phase: TimelineEvent["phase"]): string | null {
  if (phase === "before_help") return "Before first tutor reply";
  if (phase === "help_boundary") return "First tutor reply";
  if (phase === "after_help") return "After first tutor reply";
  if (phase === "ambiguous") return "Ordering uncertain";
  return null;
}

function CodeDiff({ before, after, capture }: { before: string | null; after: string | null; capture?: boolean }) {
  return (
    <div className={`code-diff ${before === null ? "code-diff--single" : ""}`}>
      {before !== null && (
        <div className="diff-pane diff-pane--before">
          <span className="diff-label">Before</span>
          <pre><code>- {before}</code></pre>
        </div>
      )}
      <div className="diff-pane diff-pane--after">
        <span className="diff-label">{capture ? "Captured source" : before === null ? "Source" : "After"}</span>
        <pre><code>{capture ? "" : "+ "}{after ?? "Source unavailable"}</code></pre>
      </div>
    </div>
  );
}

function readableText(value: string): string {
  return value.replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, "");
}

function preview(event: TimelineEvent): string {
  // Literal excerpts only. This is a display shortcut, never an evidence summary.
  const text = readableText(event.code_diff?.after ?? event.body);
  const errors = event.kind === "execution" ? text.match(/^[\w.]*?(?:Error|Exception):[^\n]*/gm) : null;
  const excerpt = (errors?.at(-1) ?? text).trim().replace(/\s+/g, " ");
  return excerpt.length > 240 ? excerpt.slice(0, 240) + "…" : excerpt;
}

function rowLabel(event: TimelineEvent): string {
  return ({ student_message: "Student", tutor_response: "AI tutor", code_edit: "Edit",
    code_capture: "Code capture", execution: "Run", inactivity: "Gap" } as Partial<Record<TimelineEvent["kind"], string>>)[event.kind] ?? event.title;
}

function TimelineCard({ event, highlighted, openCited }: { event: TimelineEvent; highlighted: boolean; openCited: boolean }) {
  const isMessage = event.kind === "student_message" || event.kind === "tutor_response";
  const [expanded, setExpanded] = useState(false);
  const excerpt = preview(event);

  useEffect(() => {
    if (highlighted && openCited) setExpanded(true);
  }, [highlighted, openCited]);

  const checkTone = event.kind === "check_result"
    ? event.title.toLowerCase().includes("pass") ? "timeline-card--check-pass" : "timeline-card--check-fail"
    : "";

  return (
    <article id={`ref-${event.id}`}
             data-source-ref={event.id}
             className={`timeline-card timeline-card--${event.kind} ${checkTone} ${highlighted ? "is-highlighted" : ""}`}>
      <div className="event-content">
        <button className="event-toggle" type="button" onClick={() => setExpanded((value) => !value)}
                aria-label={`${event.actor} ${event.title} · ${formatTimestamp(event.occurred_at)} · ${excerpt}${event.order_uncertain ? " · Ordering uncertain" : ""}${highlighted ? " · Cited" : ""}`}
                aria-expanded={expanded} aria-controls={`details-${event.id}`}>
          <time className="event-time" dateTime={event.occurred_at} title={formatTimestamp(event.occurred_at)}>{new Date(event.occurred_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit", hourCycle: "h23" })}</time>
          <span className="timeline-node" aria-hidden="true"><EventIcon event={event} /></span>
          <span className="event-label" title={event.title}>{rowLabel(event)}</span>
          <span className="event-preview">{excerpt}</span>
          {event.order_uncertain && <span className="row-order-warning" title="Relative order at this timestamp is unknown" aria-label="Ordering uncertain">?</span>}
          {highlighted && <span className="row-citation">Cited</span>}
          <ChevronDown size={16} className={`event-chevron ${expanded ? "is-expanded" : ""}`} aria-hidden="true" />
        </button>
        {expanded && (
          <div className="event-details" id={`details-${event.id}`}>
            <h4>{event.title}</h4>
            {event.order_uncertain && <div className="uncertain-notice">Relative order at this timestamp is unknown.</div>}
            {event.kind === "inactivity" && event.duration_seconds !== undefined && (
              <div className="gap-duration">Observed gap: {formatDuration(event.duration_seconds)}</div>
            )}
            <p className={isMessage ? "message-copy" : "event-copy"}>
              {readableText(event.body)}
            </p>
            {event.code_diff && <CodeDiff before={event.code_diff.before} after={event.code_diff.after} capture={event.kind === "code_capture"} />}
            <details className="event-provenance"><summary>Source details</summary>
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
            </details>
          </div>
        )}
      </div>
    </article>
  );
}

export function Timeline({ events, highlightedRefs }: TimelineProps) {
  const [filter, setFilter] = useState<TimelineFilter>("all");
  useEffect(() => { if (highlightedRefs.size) setFilter("all"); }, [highlightedRefs]);
  const visible = useMemo(() => filterTimeline(events, filter), [events, filter]);
  let previousPhase: TimelineEvent["phase"] | null = null;
  let previousDay: string | null = null;

  return (
    <section className="timeline-section timeline-section--compact" aria-labelledby="timeline-heading">
      <div className="section-heading-row">
        <div>
          <h3 id="timeline-heading">Session timeline</h3>
          <p>{visible.length} events · Click a row for full evidence.</p>
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
          const day = new Date(event.occurred_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZoneName: "short" });
          const newDay = day !== previousDay;
          previousDay = day;
          return (
            <div key={event.id}>
              {newDay && <div className="timeline-day">{day}</div>}
              {title && <div className={`phase-divider phase-divider--${event.phase}`}>{title}</div>}
              <TimelineCard event={event} highlighted={highlightedRefs.has(event.id)} openCited={highlightedRefs.size === 1} />
            </div>
          );
        })}
        {!visible.length && <p className="empty-state">No events match this timeline filter.</p>}
      </div>
    </section>
  );
}
