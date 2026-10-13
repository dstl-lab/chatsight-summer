import { FlaskConical, Info } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { demoDataset } from "./data";
import { InvestigationView } from "./components/InvestigationView";
import { SessionQueue } from "./components/SessionQueue";
import { SummaryBar } from "./components/SummaryBar";
import type { DemoDataset, ReviewRecord } from "./types";

const STORAGE_KEY = "anomaly-review-instructor-reviews-v1";

function initialSelectedId(dataset: DemoDataset): string {
  const requested = new URLSearchParams(window.location.search).get("session");
  return dataset.sessions.some((session) => session.id === requested)
    ? requested! : dataset.sessions[0]?.id ?? "";
}

function readReviews(): Record<string, ReviewRecord> {
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "{}");
  } catch {
    return {};
  }
}

export function App({ dataset = demoDataset }: { dataset?: DemoDataset }) {
  const [selectedId, setSelectedId] = useState(() => initialSelectedId(dataset));
  const [reviews, setReviews] = useState<Record<string, ReviewRecord>>(readReviews);
  const selected = useMemo(
    () => dataset.sessions.find((session) => session.id === selectedId) ?? dataset.sessions[0],
    [dataset.sessions, selectedId],
  );

  useEffect(() => {
    if (!selectedId) return;
    const url = new URL(window.location.href);
    url.searchParams.set("session", selectedId);
    window.history.replaceState({}, "", url);
  }, [selectedId]);

  function saveReview(review: ReviewRecord) {
    const updated = { ...reviews, [selected.id]: review };
    setReviews(updated);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  }

  if (!selected) return <main className="empty-app">No synthetic sessions are available.</main>;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-copy" aria-label="ChatSight Session Review">
          <span className="product-name">ChatSight</span>
          <span className="brand-divider" aria-hidden="true">/</span>
          <span className="product-context">Session Review</span>
        </div>
        <span className="synthetic-label"><FlaskConical size={14} /> Synthetic data</span>
      </header>

      <div className="dataset-notice" role="note">
        <Info size={16} aria-hidden="true" />
        <span><strong>Demonstration only.</strong> Synthetic sessions and illustrative priorities. No anomaly ranking is implemented.</span>
      </div>

      <main>
        <SummaryBar summary={dataset.summary} reviewed={Object.keys(reviews).length} />
        <div className="workspace">
          <SessionQueue sessions={dataset.sessions} selectedId={selected.id}
                        reviewedIds={new Set(Object.keys(reviews))} onSelect={setSelectedId} />
          <InvestigationView key={selected.id} session={selected} review={reviews[selected.id]}
                             onSaveReview={saveReview} />
        </div>
      </main>
    </div>
  );
}
