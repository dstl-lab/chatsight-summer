import type { DemoSession, TimelineEvent } from "./types";

export interface QuestionMessage {
  key: string;
  sessionId: string;
  studentId: string | null;
  assignmentId: string | null;
  questionId: string | null;
  event: TimelineEvent;
}

export interface Topic {
  id: string;
  label: string;
  description: string;
  pattern: RegExp;
}

export interface DetailGroup {
  id: string;
  label: string;
  description: string;
  messages: QuestionMessage[];
  evidence: (message: QuestionMessage) => string | null;
}

// These are literal keyword groups, not conclusions about intent or understanding.
export const topics: Topic[] = [
  { id: "dataframes", label: "DataFrames and tables", description: "dataframe, column, row, table", pattern: /\b(data\s*frame|dataframe|columns?|rows?|tables?)\b/i },
  { id: "indexing", label: "Indexing and keys", description: "index, indexing, key, out of bounds", pattern: /\b(index(?:ing|es)?|indices|key(?:s|error)?|out of (?:bounds|range))\b/i },
  { id: "arrays", label: "Arrays and lists", description: "array, list, numpy", pattern: /\b(arrays?|lists?|numpy)\b/i },
  { id: "errors", label: "Errors and debugging", description: "error, exception, traceback, bug", pattern: /\b(error|exception|traceback|bug|debug|wrong|fail(?:ed|ing)?)\b/i },
  { id: "explanations", label: "Explanation requests", description: "explain, understand, why, how does", pattern: /\b(explain|understand|why|how does|what does)\b/i },
  { id: "solutions", label: "Solution-related wording", description: "solution, answer, solve", pattern: /\b(solution|answer|solve)\b/i },
];

// Seeded from the DSC 10 course profile; phrases are deliberately explicit.
export const concepts: Topic[] = [
  { id: "filtering", label: "Filtering rows", description: "filter, filtering, subset, select rows", pattern: /\b(filter(?:ing|ed|s)?|subset|select(?:ing)? (?:the )?rows)\b/i },
  { id: "aggregation", label: "Grouping and aggregation", description: "groupby, group by, grouping, aggregation", pattern: /\b(groupby|group\s+by|grouping|aggregat(?:e|ion|ing))\b/i },
  { id: "types", label: "Data types and conversion", description: "data type, dtype, type conversion", pattern: /\b(data types?|dtype|type conversion|type casting)\b/i },
  { id: "missing", label: "Missing values", description: "missing values, NaN, null values", pattern: /\b(missing values?|nan|null values?)\b/i },
  { id: "chaining", label: "Method chaining", description: "method chaining, chained methods", pattern: /\b(method chaining|chained methods?)\b/i },
  { id: "visualization", label: "Plots and visualization", description: "plot, histogram, bar chart", pattern: /\b(plot(?:ting|s)?|histograms?|bar charts?|visuali[sz]ation)\b/i },
  { id: "strings", label: "String operations", description: "string method, text processing", pattern: /\b(string methods?|text processing)\b/i },
  { id: "indexing", label: "Indexing and bounds", description: "index, indexing, out of bounds", pattern: /\b(index(?:ing|es)?|indices|out of (?:bounds|range))\b/i },
];

const nonFunctions = new Set(["if", "while", "for", "with", "return", "and", "or", "not", "printout"]);

export function functionMentions(text: string): { label: string; matched: string }[] {
  const found = new Map<string, string>();
  // Function calls only: prose about a feature or bare names do not establish a call.
  const pattern = /(?<![\w.])(\.?[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\(/g;
  for (const match of text.matchAll(pattern)) {
    const isBareMethod = match[1].startsWith(".");
    const parts = match[1].replace(/^\./, "").split(".");
    const last = parts[parts.length - 1];
    if (nonFunctions.has(last.toLowerCase())) continue;
    const label = parts.length === 1 ? `${isBareMethod ? "." : ""}${last}()` : ["np", "numpy", "pd", "bpd"].includes(parts[0])
      ? `${parts[0]}.${parts.slice(1).join(".")}()` : `.${last}()`;
    if (!found.has(label)) found.set(label, match[1]);
  }
  return [...found].map(([label, matched]) => ({ label, matched }));
}

export function conceptGroups(messages: QuestionMessage[]): DetailGroup[] {
  return concepts.map(concept => ({ id: `concept:${concept.id}`, label: concept.label, description: concept.description,
    messages: messages.filter(message => concept.pattern.test(message.event.body)),
    evidence: (message: QuestionMessage) => message.event.body.match(concept.pattern)?.[0] ?? null }))
    .filter(group => group.messages.length > 0)
    .sort((a, b) => b.messages.length - a.messages.length || a.label.localeCompare(b.label));
}

export function functionGroups(messages: QuestionMessage[]): DetailGroup[] {
  const names = new Set(messages.flatMap(message => functionMentions(message.event.body).map(item => item.label)));
  return [...names].map(label => ({ id: `function:${label}`, label, description: "Explicit function call in the message",
    messages: messages.filter(message => functionMentions(message.event.body).some(item => item.label === label)),
    evidence: (message: QuestionMessage) => functionMentions(message.event.body).find(item => item.label === label)?.matched ?? null }))
    .sort((a, b) => b.messages.length - a.messages.length || a.label.localeCompare(b.label));
}

function usableStudentId(value: string): string | null {
  const id = value.trim();
  return !id || /^(unknown|anonymous|authored example|student unknown)$/i.test(id) ? null : id;
}

export function collectQuestions(sessions: DemoSession[]): QuestionMessage[] {
  const messages = new Map<string, QuestionMessage>();
  for (const session of sessions) {
    for (const event of session.timeline) {
      if (event.kind !== "student_message" || !event.body.trim()) continue;
      const key = event.source_event_id ? `source:${event.source_event_id}` : `window:${session.id}:${event.id}`;
      const existing = messages.get(key);
      const studentId = usableStudentId(session.student_id);
      if (existing) {
        // Contradictory window metadata cannot establish a shared assignment or identity.
        if (existing.assignmentId !== session.assignment_id) existing.assignmentId = null;
        if (existing.studentId !== studentId) existing.studentId = null;
        if (existing.questionId !== session.question_id) existing.questionId = null;
        continue;
      }
      messages.set(key, { key, sessionId: session.id, studentId, assignmentId: session.assignment_id, questionId: session.question_id, event });
    }
  }
  return [...messages.values()].sort((a, b) => a.event.occurred_at.localeCompare(b.event.occurred_at) || a.key.localeCompare(b.key));
}

export function topicGroups(messages: QuestionMessage[]) {
  return topics.map(topic => ({ ...topic, messages: messages.filter(message => topic.pattern.test(message.event.body)) }))
    .filter(topic => topic.messages.length > 0)
    .sort((a, b) => b.messages.length - a.messages.length || a.label.localeCompare(b.label));
}

export function distinctStudents(messages: QuestionMessage[]): { count: number; missing: number } {
  return { count: new Set(messages.flatMap(message => message.studentId ? [message.studentId] : [])).size,
    missing: messages.filter(message => !message.studentId).length };
}
