import { CheckCircle2, Save } from "lucide-react";
import { useEffect, useState } from "react";
import type { ReviewClassification, ReviewRecord } from "../types";

interface ReviewPanelProps {
  sessionId: string;
  review?: ReviewRecord;
  onSave: (review: ReviewRecord) => boolean | void;
}

const options: { value: Exclude<ReviewClassification, "">; title: string; detail: string }[] = [
  { value: "tutor_issue", title: "Potential tutor issue", detail: "Tutor behavior may warrant closer review." },
  { value: "student_struggle", title: "Student struggle", detail: "No apparent tutor contribution in the evidence." },
  { value: "insufficient", title: "Insufficient evidence", detail: "Available events do not support a conclusion." },
];

export function ReviewPanel({ sessionId, review, onSave }: ReviewPanelProps) {
  const [classification, setClassification] = useState<ReviewClassification>(review?.classification ?? "");
  const [notes, setNotes] = useState(review?.notes ?? "");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setClassification(review?.classification ?? "");
    setNotes(review?.notes ?? "");
  }, [sessionId, review?.classification, review?.notes]);

  useEffect(() => { setSaved(false); }, [sessionId]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!classification) return;
    const persisted = onSave({ classification, notes: notes.trim(), savedAt: new Date().toISOString() });
    setSaved(persisted !== false);
  }

  return (
    <section className="review-panel" aria-labelledby="review-heading">
      <h3 id="review-heading">Instructor assessment</h3>
      <p className="review-intro">The flag is a suggestion. Record your assessment; saved only in this browser.</p>
      <form onSubmit={submit}>
        <fieldset className="review-options">
          <legend className="sr-only">Session classification</legend>
          {options.map((option) => (
            <label className={`review-option ${classification === option.value ? "is-selected" : ""}`}
                   key={option.value}>
              <input type="radio" name={`classification-${sessionId}`} value={option.value}
                     checked={classification === option.value}
                     onChange={() => { setClassification(option.value); setSaved(false); }} />
              <span><strong>{option.title}</strong><small>{option.detail}</small></span>
            </label>
          ))}
        </fieldset>
        <label className="notes-field">
          <span>Optional notes</span>
          <textarea value={notes} rows={5} onChange={(event) => { setNotes(event.target.value); setSaved(false); }}
                    placeholder="Record what in the timeline influenced your assessment." />
        </label>
        <button className="save-review" type="submit" disabled={!classification}>
          {saved ? <CheckCircle2 size={17} /> : <Save size={17} />}
          {saved ? "Saved locally" : "Save review"}
        </button>
      </form>
      {review?.savedAt && !saved && (
        <p className="saved-note"><CheckCircle2 size={14} /> Previously saved in local browser state.</p>
      )}
    </section>
  );
}
