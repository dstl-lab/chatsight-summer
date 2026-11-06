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
