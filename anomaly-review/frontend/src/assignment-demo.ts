import { demoDataset } from "./data";
import type { DemoDataset, TimelineEvent } from "./types";

export function assignmentDemo(): DemoDataset {
  const rows = [
    ["STU-101", "Q1", "Why does my DataFrame filter return an empty table when I use df.get('age')?"],
    ["STU-102", "Q1", "How does this DataFrame select the right rows using table.get('score')?"],
    ["STU-103", "Q2", "I get an index out of bounds error when I access the array."],
    ["STU-104", "Q2", "Why does this array index give an error?"],
    ["STU-105", "Q3", "Can you explain how grouping works with df.groupby('city').mean()?"],
  ];
  const template = demoDataset.sessions[0];
  const sample = template.timeline.find(event => event.kind === "student_message")!;
  const tutorSample = template.timeline.find(event => event.kind === "tutor_response")!;
  const unknown = { status: "unknown" as const, value: null, reason: "Not included in this synthetic question example.", evidence_refs: [] };
  const sessions = rows.map(([student, question, body], index) => {
    const event: TimelineEvent = { ...sample, id: `example-message-${index}`, source_event_id: `example-source-${index}`,
      body, occurred_at: `2026-10-01T12:0${index}:00Z`, metadata: [], source_pointers: [], phase: "unpartitioned", code_diff: null };
    const reply: TimelineEvent = { ...tutorSample, id: `example-reply-${index}`, source_event_id: `example-reply-source-${index}`,
      body: "What have you tried so far, and what result did you expect?", occurred_at: `2026-10-01T12:0${index}:30Z`,
      metadata: [], source_pointers: [], phase: "unpartitioned", code_diff: null };
    return { ...template, id: `assignment-example-${index}`, student_id: student, question_id: question,
      assignment_id: "Synthetic lab: DataFrames and arrays", scenario: "Invented example", timeline: [event, reply],
      flagged: false, priority: null, outcome: unknown, active_time: unknown, post_help_active_time: unknown,
      elapsed_time: unknown, failed_checks_after_help: unknown, tutor_requests: unknown,
      completed_tutor_responses: unknown, repeated_failures: unknown, continued_after_help: unknown,
      resumed_after_help: unknown, reference_active_time: { status: "unknown" as const, lower_seconds: null, upper_seconds: null, basis: "Not available." },
      source_event_refs: [event.id, reply.id], reasons: [], quality_warnings: [], analysis: undefined, fusion: undefined };
  });
  return { ...demoDataset, dataset: { ...demoDataset.dataset, id: "assignment-insights-synthetic", label: "Synthetic assignment examples",
    notice: "All questions and students are invented for this demonstration." },
    summary: { total_sessions: sessions.length, flagged_sessions: 0, high_priority_sessions: 0 }, sessions };
}

export function studentStudyDemo(): DemoDataset {
  const dataset = assignmentDemo();
  dataset.dataset.id = "student-study-synthetic";
  const first = dataset.sessions[0];
  const sample = first.timeline[0];
  first.timeline = first.timeline.map(event => ({ ...event, metadata: [{ label: "Question", value: "Q1" }] }));
  const extra = [
    { id: "study-example-index", question: "Q2", kind: "student_message" as const, title: "Student message", body: "Why does the array index go out of bounds?", occurred_at: "2026-10-02T12:00:00Z" },
    { id: "study-example-group", question: "Q3", kind: "student_message" as const, title: "Student message", body: "How does grouping work before calculating a mean?", occurred_at: "2026-10-03T12:00:00Z" },
    { id: "study-edit-before", question: "Q1", kind: "code_edit" as const, title: "Code edited", body: "Recorded edit", occurred_at: "2026-10-01T12:00:05Z", code_diff: { before: null, after: "df.get('age') > '18'" } },
    { id: "study-run-error", question: "Q1", kind: "execution" as const, title: "Cell executed", body: "TypeError: cannot compare numbers with a string", occurred_at: "2026-10-01T12:00:10Z" },
    { id: "study-check-fail", question: "Q1", kind: "check_result" as const, title: "Check fail", body: "One check did not pass.", occurred_at: "2026-10-01T12:00:15Z" },
    { id: "study-edit-after", question: "Q1", kind: "code_edit" as const, title: "Code edited", body: "Recorded edit", occurred_at: "2026-10-01T12:00:40Z", code_diff: { before: "df.get('age') > '18'", after: "df.get('age') >= 18" } },
    { id: "study-check-pass", question: "Q1", kind: "check_result" as const, title: "Check pass", body: "One check passed; overall completion is unknown.", occurred_at: "2026-10-01T12:00:50Z" },
  ].map(({ question, ...item }) => ({ ...sample, ...item, actor: item.kind === "student_message" ? "Student" : item.kind === "check_result" ? "Autograder" : "Notebook", source_event_id: `source-${item.id}`, metadata: [{ label: "Question", value: question }] }));
  first.timeline = [...first.timeline, ...extra].sort((a, b) => a.occurred_at.localeCompare(b.occurred_at));
  first.source_event_refs = [...first.source_event_refs, ...extra.map(event => event.id)];
  return dataset;
}
