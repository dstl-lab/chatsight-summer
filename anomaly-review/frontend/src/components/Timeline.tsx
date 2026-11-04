import {
  Activity, Bot, Braces, CheckCircle2, CircleAlert, Code2, MessageSquare,
  ChevronDown, Pause, Play, TerminalSquare, XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { filterTimeline, formatDuration, formatTimestamp, type TimelineFilter } from "../data";
import type { TimelineEvent } from "../types";
import { compactTimeline, type TimelineAction } from "../timeline-compaction";

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

function EventDetails({ event, heading = true }: { event: TimelineEvent; heading?: boolean }) {
  const isMessage = event.kind === "student_message" || event.kind === "tutor_response";
  return (
    <>
      {heading && <h4>{event.title}</h4>}
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
    </>
  );
}

function TimelineCard({ action, highlightedRefs, openCited }: {
  action: TimelineAction;
  highlightedRefs: Set<string>;
  openCited: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const event = action.representative;
  const citedEvents = action.events.filter((item) => highlightedRefs.has(item.id));
  const highlighted = citedEvents.length > 0;
  const excerpt = action.compacted ? action.summary : preview(event);

  useEffect(() => {
    if (highlighted && openCited) setExpanded(true);
  }, [highlighted, openCited]);

  const checks = action.events.filter((item) => item.kind === "check_result");
  const checkTone = checks.length
    ? checks.some((item) => item.title.toLowerCase().includes("fail") || item.title.toLowerCase().includes("error"))
      ? "timeline-card--check-fail"
      : "timeline-card--check-pass"
    : "";
  const detailsId = `details-${action.events[0].id}`;
  const displayLabel = action.compacted ? action.label : rowLabel(event);
  const displayTitle = action.compacted ? "Compacted notebook action" : event.title;

  return (
    <article id={action.compacted ? undefined : `ref-${event.id}`}
             data-source-ref={action.events.map((item) => item.id).join(" ")}
             className={`timeline-card timeline-card--${event.kind} ${action.compacted ? "timeline-card--group" : ""} ${checkTone} ${highlighted ? "is-highlighted" : ""}`}>
      {action.compacted && action.events.map((item) => <span key={item.id} id={`ref-${item.id}`} className="event-ref-anchor" />)}
      <div className="event-content">
        <button className="event-toggle" type="button" onClick={() => setExpanded((value) => !value)}
                aria-label={`${action.actor} ${displayTitle} · ${formatTimestamp(action.occurred_at)} · ${excerpt}${action.order_uncertain ? " · Ordering uncertain" : ""}${highlighted ? " · Cited" : ""}`}
                aria-expanded={expanded} aria-controls={detailsId}>
          <time className="event-time" dateTime={action.occurred_at} title={formatTimestamp(action.occurred_at)}>{new Date(action.occurred_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit", hourCycle: "h23" })}</time>
          <span className="timeline-node" aria-hidden="true"><EventIcon event={event} /></span>
          <span className="event-label" title={displayTitle}>{displayLabel}</span>
          <span className="event-preview">{excerpt}</span>
          {action.order_uncertain && <span className="row-order-warning" title="Relative order at this timestamp is unknown" aria-label="Ordering uncertain">?</span>}
          {action.compacted && <span className="event-count">{action.events.length} events</span>}
          {highlighted && <span className="row-citation">{citedEvents.length > 1 ? `${citedEvents.length} cited` : "Cited"}</span>}
          <ChevronDown size={16} className={`event-chevron ${expanded ? "is-expanded" : ""}`} aria-hidden="true" />
        </button>
        {expanded && (
          <div className="event-details" id={detailsId}>
            {action.compacted ? (
              <>
                <div className="compaction-note">Grouped for display only. All {action.events.length} source events remain available below.</div>
                <div className="grouped-events">
                  {action.events.map((item) => {
                    const cited = highlightedRefs.has(item.id);
                    return <details className={`grouped-event ${cited ? "is-cited" : ""}`} key={item.id}
                                    data-source-ref={item.id} open={cited && openCited}>
                      <summary>
                        <time dateTime={item.occurred_at}>{new Date(item.occurred_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit", fractionalSecondDigits: 3, hourCycle: "h23" })}</time>
                        <span>{rowLabel(item)}</span>
                        <strong>{item.title}</strong>
                        {cited && <em>Cited</em>}
                      </summary>
                      <div className="grouped-event-details"><EventDetails event={item} heading={false} /></div>
                    </details>;
                  })}
                </div>
              </>
            ) : <EventDetails event={event} />}
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
  const actions = useMemo(() => compactTimeline(visible), [visible]);
  let previousPhase: TimelineEvent["phase"] | null = null;
  let previousDay: string | null = null;

  return (
    <section className="timeline-section timeline-section--compact" aria-labelledby="timeline-heading">
      <div className="section-heading-row">
        <div>
          <h3 id="timeline-heading">Session timeline</h3>
          <p>{actions.length} actions from {visible.length} events · Click a row for full evidence.</p>
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
        {actions.map((action) => {
          const title = action.phase !== previousPhase ? phaseTitle(action.phase) : null;
          previousPhase = action.phase;
          const day = new Date(action.occurred_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZoneName: "short" });
          const newDay = day !== previousDay;
          previousDay = day;
          return (
            <div key={action.id}>
              {newDay && <div className="timeline-day">{day}</div>}
              {title && <div className={`phase-divider phase-divider--${action.phase}`}>{title}</div>}
              <TimelineCard action={action} highlightedRefs={highlightedRefs} openCited={highlightedRefs.size === 1} />
            </div>
          );
        })}
        {!actions.length && <p className="empty-state">No events match this timeline filter.</p>}
      </div>
    </section>
  );
}
