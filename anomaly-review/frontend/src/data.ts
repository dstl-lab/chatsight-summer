import rawDemoData from "./demo-data.synthetic.json";
import type { DemoDataset, Metric, TimelineEvent } from "./types";

export const demoDataset = rawDemoData as DemoDataset;

export function formatDuration(seconds: number | null): string {
  if (seconds === null) return "Unknown";
  if (seconds < 60) return `${Math.round(seconds)} sec`;
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  return remaining ? `${minutes}m ${remaining}s` : `${minutes} min`;
}

export function metricDuration(metric: Metric): string {
  return metric.status === "known" ? formatDuration(metric.value) : "Unknown";
}

export function metricCount(metric: Metric): string {
  return metric.status === "known" && metric.value !== null ? String(metric.value) : "Unknown";
}

export function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    year: "numeric", month: "short", day: "numeric", timeZoneName: "short",
  }).format(new Date(value));
}

export type TimelineFilter = "all" | "conversation" | "notebook" | "checks";

export function filterTimeline(events: TimelineEvent[], filter: TimelineFilter): TimelineEvent[] {
  if (filter === "all") return events;
  const groups: Record<Exclude<TimelineFilter, "all">, TimelineEvent["kind"][]> = {
    conversation: ["student_message", "tutor_response"],
    notebook: ["code_edit", "execution", "activity", "inactivity", "notebook_snapshot"],
    checks: ["check_result", "question_status"],
  };
  return events.filter((event) => groups[filter].includes(event.kind));
}

export function referenceLabel(lower: number | null, upper: number | null): string {
  if (lower === null || upper === null) return "Unknown";
  return `${formatDuration(lower)} to ${formatDuration(upper)}`;
}
