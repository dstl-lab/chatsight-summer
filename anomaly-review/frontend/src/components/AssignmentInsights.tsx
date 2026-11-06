import { ArrowUpRight, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { collectQuestions, conceptGroups, distinctStudents, functionGroups, topicGroups, type DetailGroup } from "../assignment-insights";
import type { DemoDataset } from "../types";

export function AssignmentInsights({ dataset, onInspect }: { dataset: DemoDataset; onInspect: (sessionId: string, eventId: string) => void }) {
  const all = useMemo(() => collectQuestions(dataset.sessions), [dataset]);
  const assignments = useMemo(() => [...new Set(all.flatMap(item => item.assignmentId ? [item.assignmentId] : []))].sort(), [all]);
  const [assignment, setAssignment] = useState(assignments[0] ? `assignment:${assignments[0]}` : "unknown");
  const [topic, setTopic] = useState("all");
  const [query, setQuery] = useState("");
  const selected = all.filter(item => assignment === "unknown" ? !item.assignmentId : `assignment:${item.assignmentId}` === assignment);
  const groups = topicGroups(selected).map(group => ({ ...group, id: `topic:${group.id}`,
    evidence: (message: typeof selected[number]) => message.event.body.match(group.pattern)?.[0] ?? null }));
  const conceptDetails = conceptGroups(selected);
  const functionDetails = functionGroups(selected);
  const selectedTopic = [...conceptDetails, ...functionDetails, ...groups].find(group => group.id === topic);
  const filtered = selected.filter(item => (!selectedTopic || selectedTopic.messages.includes(item)) &&
    `${item.event.body} ${item.questionId ?? ""}`.toLowerCase().includes(query.trim().toLowerCase()));
  const students = distinctStudents(selected);

  function groupButtons(items: DetailGroup[]) {
    return items.map(group => { const count = distinctStudents(group.messages); return <button key={group.id} className={topic === group.id ? "is-selected" : ""} onClick={() => setTopic(group.id)} title={`Matches: ${group.description}`}><span>{group.label}<small>{count.count}{count.missing ? "+" : ""} known student IDs</small></span><strong>{group.messages.length}</strong></button>; });
  }

  return <main className="insights-page">
    <div className="insights-heading"><div><span className="insights-eyebrow">STUDENT QUESTIONS</span>
      <h1>Assignment insights</h1><p>Explore recurring topics in the messages available for this assignment.</p></div>
      <label className="insights-assignment">Assignment<select aria-label="Assignment" value={assignment} onChange={event => { setAssignment(event.target.value); setTopic("all"); }}>
        {assignments.map(item => <option value={`assignment:${item}`} key={item}>{item}</option>)}
        {all.some(item => !item.assignmentId) && <option value="unknown">Assignment unknown</option>}
        {!all.length && <option value="unknown">No messages available</option>}
      </select></label>
    </div>
    <div className="insights-totals" aria-label="Assignment coverage">
      <div><strong>{selected.length}</strong><span>Student messages</span></div>
      <div><strong>{students.missing ? `${students.count}+` : students.count}</strong><span>Known student IDs</span></div>
      <div><strong>{new Set(selected.map(item => item.sessionId)).size}</strong><span>Review windows</span></div>
    </div>
    <p className="insights-caveat">Counts cover only messages in this loaded dataset, which may be sampled or incomplete. {students.missing > 0 && `${students.missing} message(s) have no reliable student identifier. `}Matches show what messages mention, not confirmed confusion. A message can appear in multiple groups.</p>
    <div className="insights-layout">
      <aside className="insights-topics" aria-label="Question topics"><h2>Explore messages</h2>
        <button className={topic === "all" ? "is-selected" : ""} onClick={() => setTopic("all")}><span>All messages</span><strong>{selected.length}</strong></button>
        <h3>Specific functions</h3>{groupButtons(functionDetails)}
        {!functionDetails.length && <p>No explicit function calls found.</p>}
        <h3>Course concepts</h3>{groupButtons(conceptDetails)}
        {!conceptDetails.length && <p>No matching concept phrases found.</p>}
        <h3>Broader topics</h3>{groupButtons(groups)}
        {!groups.length && <p>No matching topic words found.</p>}
      </aside>
      <section className="insights-messages" aria-labelledby="questions-heading">
        <div className="insights-messages-heading"><div><h2 id="questions-heading">{selectedTopic?.label ?? "All student messages"}</h2>
          <p>{filtered.length} message{filtered.length === 1 ? "" : "s"}{selectedTopic ? ` · matches ${selectedTopic.description}` : ""}</p></div>
          <label className="insights-search"><Search size={16} aria-hidden="true" /><span className="sr-only">Search student messages</span><input placeholder="Search messages" value={query} onChange={event => setQuery(event.target.value)} /></label>
        </div>
        {filtered.map(item => <article className="insight-message" key={item.key}>
          <div className="insight-message-meta"><span>{item.studentId ?? "Student unknown"}</span><span>{item.questionId ?? "Question unknown"}</span><time dateTime={item.event.occurred_at}>{new Date(item.event.occurred_at).toLocaleString()}</time></div>
          <p>{item.event.body}</p>{selectedTopic?.evidence(item) && <span className="insights-match">Matched: <code>{selectedTopic.evidence(item)}</code></span>}
          <button onClick={() => onInspect(item.sessionId, item.event.id)}>View conversation <ArrowUpRight size={14} /></button>
        </article>)}
        {!filtered.length && <p className="insights-empty">No messages match this selection.</p>}
      </section>
    </div>
  </main>;
}
