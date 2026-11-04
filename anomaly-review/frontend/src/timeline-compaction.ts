import type { TimelineEvent, TimelineKind } from "./types";

const COMPACTABLE_KINDS = new Set<TimelineKind>([
  "code_edit",
  "code_capture",
  "execution",
  "check_result",
  "activity",
  "notebook_snapshot",
]);

const LINK_LABELS = ["Cell", "Execution", "Revision", "Request", "Check", "Grader"] as const;

export interface TimelineAction {
  id: string;
  events: TimelineEvent[];
  representative: TimelineEvent;
  occurred_at: string;
  phase: TimelineEvent["phase"];
  order_uncertain: boolean;
  actor: string;
  label: string;
  summary: string;
  compacted: boolean;
}

function secondBucket(value: string): number {
  return Math.floor(Date.parse(value) / 1000);
}

function metadata(event: TimelineEvent): Map<string, Set<string>> {
  const values = new Map<string, Set<string>>();
  for (const item of event.metadata) {
    const value = item.value.trim();
    if (!value || value.toLowerCase() === "unknown") continue;
    const existing = values.get(item.label) ?? new Set<string>();
    existing.add(value);
    values.set(item.label, existing);
  }
  return values;
}

function intersects(left: Set<string> | undefined, right: Set<string> | undefined): boolean {
  return !!left && !!right && [...left].some((value) => right.has(value));
}

function conflicts(left: Set<string> | undefined, right: Set<string> | undefined): boolean {
  return !!left && !!right && !intersects(left, right);
}

function related(left: TimelineEvent, right: TimelineEvent): boolean {
  if (!COMPACTABLE_KINDS.has(left.kind) || !COMPACTABLE_KINDS.has(right.kind)) return false;
  if (left.phase !== right.phase || secondBucket(left.occurred_at) !== secondBucket(right.occurred_at)) return false;

  const leftMeta = metadata(left);
  const rightMeta = metadata(right);
  if (conflicts(leftMeta.get("Cell"), rightMeta.get("Cell"))) return false;
  if (LINK_LABELS.some((label) => intersects(leftMeta.get(label), rightMeta.get(label)))) return true;

  // Some exports record edit bursts without stable cell or revision identifiers.
  // Collapse only repeated observations of the same kind in that case.
  if (left.kind === right.kind && left.actor === right.actor) {
    if (left.kind === "code_edit" || left.kind === "code_capture") return true;
    return left.title === right.title;
  }
  return false;
}

function naturalList(parts: string[]): string {
  if (parts.length === 0) return "Recorded notebook activity";
  if (parts.length === 1) return parts[0];
  if (parts.length === 2) return `${parts[0]} and ${parts[1]}`;
  return `${parts.slice(0, -1).join(", ")}, and ${parts.at(-1)}`;
}

function actionSummary(events: TimelineEvent[]): string {
  const count = (kind: TimelineKind) => events.filter((event) => event.kind === kind).length;
  const edits = count("code_edit") + count("code_capture");
  const executions = count("execution");
  const checks = events.filter((event) => event.kind === "check_result");
  const activities = count("activity") + count("notebook_snapshot");
  const parts: string[] = [];

  if (edits) parts.push(edits === 1 ? "Edited code" : `Edited code ${edits} times`);
  if (executions) parts.push(executions === 1 ? "ran a cell" : `ran ${executions} cells`);
  if (checks.length) {
    const passed = checks.filter((event) => event.title.toLowerCase().includes("pass")).length;
    const failed = checks.filter((event) => event.title.toLowerCase().includes("fail") || event.title.toLowerCase().includes("error")).length;
    const unknown = checks.length - passed - failed;
    if (passed) parts.push(`${passed === 1 ? "a check" : `${passed} checks`} passed`);
    if (failed) parts.push(`${failed === 1 ? "a check" : `${failed} checks`} failed`);
    if (unknown) parts.push(`${unknown === 1 ? "a check result" : `${unknown} check results`} was recorded`);
  }
  if (activities) parts.push(`${activities === 1 ? "one activity signal" : `${activities} activity signals`} recorded`);
  return naturalList(parts);
}

function representative(events: TimelineEvent[]): TimelineEvent {
  for (let index = events.length - 1; index >= 0; index--) {
    if (events[index].kind === "check_result") return events[index];
  }
  for (let index = events.length - 1; index >= 0; index--) {
    if (events[index].kind === "execution") return events[index];
  }
  return events.at(-1)!;
}

function actionFrom(events: TimelineEvent[]): TimelineAction {
  const primary = representative(events);
  const compacted = events.length > 1;
  return {
    id: compacted ? `action:${events.map((event) => event.id).join(":")}` : events[0].id,
    events,
    representative: primary,
    occurred_at: events[0].occurred_at,
    phase: events[0].phase,
    order_uncertain: events.some((event) => event.order_uncertain),
    actor: compacted ? "Student workflow" : primary.actor,
    label: compacted ? "Notebook action" : primary.title,
    summary: compacted ? actionSummary(events) : "",
    compacted,
  };
}

function compactSegment(segment: TimelineEvent[]): TimelineAction[] {
  if (segment.length < 2) return segment.map((event) => actionFrom([event]));
  const parents = segment.map((_, index) => index);
  const find = (index: number): number => parents[index] === index ? index : (parents[index] = find(parents[index]));
  const union = (left: number, right: number) => {
    const leftRoot = find(left);
    const rightRoot = find(right);
    if (leftRoot !== rightRoot) parents[rightRoot] = leftRoot;
  };

  for (let left = 0; left < segment.length; left++) {
    for (let right = left + 1; right < segment.length; right++) {
      if (related(segment[left], segment[right])) union(left, right);
    }
  }

  const groups = new Map<number, { first: number; events: TimelineEvent[] }>();
  segment.forEach((event, index) => {
    const root = find(index);
    const group = groups.get(root) ?? { first: index, events: [] };
    group.events.push(event);
    group.first = Math.min(group.first, index);
    groups.set(root, group);
  });
  return [...groups.values()]
    .sort((left, right) => left.first - right.first)
    .map((group) => actionFrom(group.events));
}

/**
 * Create display actions without mutating or replacing raw evidence events.
 * Conversation boundaries and unrelated same-second observations remain separate.
 */
export function compactTimeline(events: TimelineEvent[]): TimelineAction[] {
  const actions: TimelineAction[] = [];
  let segment: TimelineEvent[] = [];

  const flush = () => {
    actions.push(...compactSegment(segment));
    segment = [];
  };

  for (const event of events) {
    const previous = segment.at(-1);
    const compatibleSegment = previous
      && COMPACTABLE_KINDS.has(event.kind)
      && secondBucket(previous.occurred_at) === secondBucket(event.occurred_at)
      && previous.phase === event.phase;
    if (!compatibleSegment) flush();
    if (!COMPACTABLE_KINDS.has(event.kind)) {
      actions.push(actionFrom([event]));
      continue;
    }
    segment.push(event);
  }
  flush();
  return actions;
}
