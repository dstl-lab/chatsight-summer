import { BookOpen, CheckCircle2, CircleHelp, MessageSquareText } from "lucide-react";
import { useMemo, useState } from "react";
import { collectQuestions, concepts, type QuestionMessage } from "../assignment-insights";
import { studyQuestions, summarizeStudyQuestion } from "../student-evidence";
import type { DemoDataset } from "../types";

const exercises = [
  { id: "filtering", label: "Filtering rows", prompt: "You want only rows where the value in age is at least 18. Which condition describes that?", choices: ["age > 18", "age >= 18", "age < 18"], answer: 1, explanation: "At least 18 includes 18, so the comparison needs >=." },
  { id: "indexing", label: "Indexing and bounds", prompt: "A Python list contains 3 items. What is the largest valid index?", choices: ["2", "3", "4"], answer: 0, explanation: "List indices start at 0, so the valid indices are 0, 1, and 2." },
  { id: "aggregation", label: "Grouping and aggregation", prompt: "What does a group-by operation help you do?", choices: ["Sort every value alphabetically", "Combine rows by a shared value before summarizing", "Remove all missing values automatically"], answer: 1, explanation: "Grouping organizes rows by a shared key so an aggregation can summarize each group." },
];
const colors = ["#287b70", "#da9651", "#6079a5", "#b77175", "#8c7caa", "#667e52", "#ba846b", "#698b90", "#a3adb2"];

export function topicDistribution(messages: QuestionMessage[]) {
  const counts = new Map<string, number>();
  for (const message of messages) {
    const label = concepts.find(concept => concept.pattern.test(message.event.body))?.label ?? "Other / not identified";
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return [...counts.entries()].map(([label, count], index) => ({ label, count, color: colors[index % colors.length] }));
}

export function StudentStudy({ dataset }: { dataset: DemoDataset }) {
  const students = useMemo(() => [...new Set(dataset.sessions.map(session => session.student_id))].sort(), [dataset]);
  const [student, setStudent] = useState(students[0] ?? "");
  const [exerciseId, setExerciseId] = useState(exercises[0].id);
  const [choice, setChoice] = useState<number | null>(null);
  const [checked, setChecked] = useState(false);
  const messages = useMemo(() => collectQuestions(dataset.sessions.filter(session => session.student_id === student)), [dataset, student]);
  const questions = useMemo(() => studyQuestions(dataset.sessions.filter(session => session.student_id === student)), [dataset, student]);
  const distribution = topicDistribution(messages);
  let runningPercent = 0;
  const stops = distribution.map(item => { const start = runningPercent; runningPercent += item.count / messages.length * 100; return `${item.color} ${start}% ${runningPercent}%`; });
  const exercise = exercises.find(item => item.id === exerciseId)!;

  return <main className="study-page">
    <div className="study-header"><div><span className="study-eyebrow">STUDY SPACE · SYNTHETIC DEMO</span><h1>Your study overview</h1><p>Review your questions and try a short practice problem.</p></div>
      <label>Example student<select aria-label="Example student" value={student} onChange={event => { setStudent(event.target.value); setChoice(null); setChecked(false); }}>
        {students.map(id => <option key={id} value={id}>{id}</option>)}
      </select></label>
    </div>
    <div className="study-banner"><CircleHelp size={17} /><span>Topic scores are not available. Questions you ask do not measure mastery; this demo uses invented records.</span></div>
    <div className="study-grid">
      <section className="study-overview" aria-labelledby="study-overview-title"><div className="study-section-title"><MessageSquareText size={18} /><h2 id="study-overview-title">Your question topics</h2></div>
        <p>One keyword group per message, based on the available conversation. This chart describes mentions, not understanding.</p>
        <div className="study-chart-row"><div className="study-pie" role="img" aria-label={`Question topic distribution: ${distribution.map(item => `${item.label}, ${item.count} messages`).join("; ") || "no messages"}`} style={{ background: stops.length ? `conic-gradient(${stops.join(", ")})` : "#e7ebeb" }}><span><strong>{messages.length}</strong><small>messages</small></span></div>
          <ul className="study-legend">{distribution.map(item => <li key={item.label}><i style={{ background: item.color }} /><span>{item.label}</span><strong>{item.count}</strong></li>)}</ul></div>
        <h3>From your conversations</h3>{messages.map(message => { const group = questions.find(question => question.events.some(item => item.event.id === message.event.id)); return <article className="study-message" key={message.key}><span>{group?.assignmentId ?? "Assignment unknown"} · {group?.questionId ?? "Question unknown"}</span><p>{message.event.body}</p></article>; })}
        {!messages.length && <p>No messages are available for this example.</p>}
      </section>
      <section className="study-practice" aria-labelledby="practice-title"><div className="study-section-title"><BookOpen size={18} /><h2 id="practice-title">Practice a concept</h2></div>
        <p>Sample questions written for this prototype.</p>
        <label className="study-select">Topic<select aria-label="Practice topic" value={exerciseId} onChange={event => { setExerciseId(event.target.value); setChoice(null); setChecked(false); }}>
          {exercises.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select></label>
        <fieldset key={exercise.id}><legend>{exercise.prompt}</legend>{exercise.choices.map((item, index) => <label className={`study-choice ${choice === index ? "is-selected" : ""}`} key={item}><input type="radio" name="practice-choice" value={index} checked={choice === index} onChange={() => { setChoice(index); setChecked(false); }} /><span>{item}</span></label>)}</fieldset>
        <button className="study-submit" disabled={choice === null} onClick={() => setChecked(true)}>Check answer</button>
        {checked && <div className="study-feedback" role="status"><strong><CheckCircle2 size={16} /> {choice === exercise.answer ? "Correct" : "Not quite"}</strong><p>{exercise.explanation}</p><small>This one answer is not a topic mastery score.</small></div>}
      </section>
    </div>
    <section className="study-activity" aria-labelledby="study-activity-title"><div className="study-section-title"><MessageSquareText size={18} /><h2 id="study-activity-title">Your work by question</h2></div>
      <p>Observed edits, runs, checks, and tutor messages appear together when the question link is available. A passed check does not confirm the whole question is complete.</p>
      {questions.map(group => { const summary = summarizeStudyQuestion(group); const mentioned = concepts.filter(concept => group.events.some(item => item.event.kind === "student_message" && concept.pattern.test(item.event.body))); return <article className="study-question" key={JSON.stringify([group.assignmentId, group.questionId])}>
        <header><div><span>{group.assignmentId ?? "Assignment unknown"}</span><h3>{group.questionId ?? "Question unknown"}</h3></div>
          <div className="study-checks">{summary.failed + summary.passed + summary.unknown ? <>{summary.failed} failed · {summary.passed} passed{summary.unknown > 0 ? ` · ${summary.unknown} unknown` : ""} checks</> : "No checks observed"}</div></header>
        {!group.questionId && <p className="study-attribution">This activity could not be reliably linked to a question.</p>}
        <p className="study-activity-summary">Topics mentioned: {mentioned.length ? mentioned.map(concept => concept.label).join(", ") : "Not identified"}</p>
        <p className="study-activity-summary">{summary.edits} edit observation{summary.edits === 1 ? "" : "s"} · {summary.runs} run{summary.runs === 1 ? "" : "s"} · {summary.tutorReplies} tutor {summary.tutorReplies === 1 ? "reply" : "replies"}{summary.captures ? ` · ${summary.captures} code capture${summary.captures === 1 ? "" : "s"}` : ""}</p>
        {summary.errors.length > 0 && <p className="study-errors">Error names in output: {summary.errors.join(", ")}</p>}
        <details className="study-event-list"><summary>View {group.events.length} source events</summary>
          {group.events.map(({ event }) => <details key={event.id} className="study-event"><summary><strong>{event.title}</strong><time dateTime={event.occurred_at}>{new Date(event.occurred_at).toLocaleString()}</time>{event.order_uncertain && <span>Order uncertain</span>}</summary>
            <p>{event.body}</p>{event.code_diff?.before != null && <><span>Before</span><pre>{event.code_diff.before}</pre></>}{event.code_diff?.after != null && <><span>{event.kind === "code_capture" ? "Captured source" : "After"}</span><pre>{event.code_diff.after}</pre></>}
            <small>Source event: {event.source_event_id ?? "Unavailable"} · Timeline reference: {event.id}</small>
          </details>)}
        </details>
      </article>; })}
      {!questions.length && <p>No activity is available for this student.</p>}
      <p className="study-activity-limit">A failed check or error does not show how wrong an answer is. Missing activity and missing outcomes remain unknown.</p>
    </section>
  </main>;
}
