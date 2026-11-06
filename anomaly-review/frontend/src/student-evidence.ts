import type { DemoSession, TimelineEvent } from "./types";

export interface StudyEvent {
  event: TimelineEvent;
  questionId: string | null;
  assignmentId: string | null;
}
export interface StudyQuestion {
  assignmentId: string | null;
  questionId: string | null;
  events: StudyEvent[];
}

function questionFor(session: DemoSession, event: TimelineEvent): string | null {
  const values = event.metadata.filter(item => item.label.toLowerCase() === "question").map(item => item.value.trim());
  if (values.length) {
    const distinct = [...new Set(values)];
    return distinct.length === 1 && distinct[0] && !/^(unknown|none|null)$/i.test(distinct[0]) ? distinct[0] : null;
  }
  return session.scope === "question_episode" ? session.question_id : null;
}

export function studyQuestions(sessions: DemoSession[]): StudyQuestion[] {
  const events = new Map<string, StudyEvent>();
  for (const session of sessions) for (const event of session.timeline) {
    if (!["student_message", "tutor_response", "code_edit", "code_capture", "execution", "check_result"].includes(event.kind)) continue;
    const key = event.source_event_id ? `source:${event.source_event_id}` : `window:${session.id}:${event.id}`;
    const questionId = questionFor(session, event);
    const previous = events.get(key);
    if (previous) {
      if (previous.questionId !== questionId) previous.questionId = null;
      if (previous.assignmentId !== session.assignment_id) previous.assignmentId = null;
    } else events.set(key, { event, questionId, assignmentId: session.assignment_id });
  }
  const groups = new Map<string, StudyQuestion>();
  for (const item of events.values()) {
    const key = JSON.stringify([item.assignmentId, item.questionId]);
    const group = groups.get(key) ?? { assignmentId: item.assignmentId, questionId: item.questionId, events: [] };
    group.events.push(item); groups.set(key, group);
  }
  for (const group of groups.values()) group.events.sort((a, b) => a.event.occurred_at.localeCompare(b.event.occurred_at) || a.event.id.localeCompare(b.event.id));
  return [...groups.values()].sort((a, b) => Number(!a.questionId) - Number(!b.questionId) || (a.questionId ?? "").localeCompare(b.questionId ?? ""));
}

export function summarizeStudyQuestion(group: StudyQuestion) {
  const events = group.events.map(item => item.event);
  const checks = events.filter(event => event.kind === "check_result");
  const failed = checks.filter(event => /^check fail(?:ed)?$/i.test(event.title.trim())).length;
  const passed = checks.filter(event => /^check pass(?:ed)?$/i.test(event.title.trim())).length;
  const unknown = checks.length - failed - passed;
  const errors = [...new Set(events.filter(event => event.kind === "execution" || event.kind === "check_result")
    .flatMap(event => [...event.body.matchAll(/\b(?:IndexError|KeyError|TypeError|ValueError|AttributeError|NameError|SyntaxError|AssertionError|ZeroDivisionError)\b/g)].map(match => match[0])))];
  return { edits: events.filter(event => event.kind === "code_edit").length,
    captures: events.filter(event => event.kind === "code_capture").length,
    runs: events.filter(event => event.kind === "execution").length,
    tutorReplies: events.filter(event => event.kind === "tutor_response").length,
    failed, passed, unknown, errors };
}
