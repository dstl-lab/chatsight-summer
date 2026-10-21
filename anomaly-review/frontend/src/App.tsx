import { FlaskConical, Info, LockKeyhole } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { demoDataset } from "./data";
import { downloadReviews, parseBundle, readLocalFile, reviewStorageKey, validateReviews } from "./bundle";
import { InvestigationView } from "./components/InvestigationView";
import { SessionQueue } from "./components/SessionQueue";
import { SummaryBar } from "./components/SummaryBar";
import { UploadPanel } from "./components/UploadPanel";
import type { DemoDataset, ReviewRecord } from "./types";

function initialSelectedId(dataset: DemoDataset): string {
  const requested = new URLSearchParams(window.location.search).get("session");
  return dataset.sessions.some(session => session.id === requested) ? requested! : dataset.sessions[0]?.id ?? "";
}
export function App({ dataset: initialDataset }: { dataset?: DemoDataset }) {
  const [dataset, setDataset] = useState<DemoDataset | null>(initialDataset ?? null);
  const [selectedId, setSelectedId] = useState(() => initialDataset ? initialSelectedId(initialDataset) : "");
  const [reviews, setReviews] = useState<Record<string, ReviewRecord>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadBusy, setUploadBusy] = useState(false);
  const selected = useMemo(() => dataset?.sessions.find(session => session.id === selectedId) ?? dataset?.sessions[0], [dataset, selectedId]);
  useEffect(() => {
    if (!dataset) { setReviews({}); return; }
    try { setReviews(validateReviews(JSON.parse(window.localStorage.getItem(reviewStorageKey(dataset)) ?? "{}"), dataset)); }
    catch { setReviews({}); setError("Saved reviews could not be read. Import a review download or continue in memory."); }
  }, [dataset]);
  useEffect(() => {
    const url = new URL(window.location.href);
    if (selectedId) url.searchParams.set("session", selectedId);
    else url.searchParams.delete("session");
    window.history.replaceState({}, "", url);
  }, [selectedId]);
  const choose = useCallback((next: DemoDataset | null) => {
    setDataset(next); setSelectedId(next?.sessions[0]?.id ?? ""); setReviews({}); setError("");
  }, []);
  async function chooseExample(loader: () => Promise<{ default: unknown }>) {
    setLoading(true);
    try { choose(parseBundle(JSON.stringify((await loader()).default))); }
    catch { setError("Could not open the bundled demonstration."); }
    finally { setLoading(false); }
  }
  async function importBundle(file?: File) {
    if (!file) return;
    choose(null); setLoading(true);
    try { choose(parseBundle(await readLocalFile(file))); }
    catch { setError("Could not open this review bundle. Select a valid version 2 or 3 JSON exported by session-findings. No previous dataset remains displayed."); }
    finally { setLoading(false); }
  }
  async function importReviews(file?: File) {
    if (!file || !dataset) return;
    setLoading(true);
    try {
      const data = JSON.parse(await readLocalFile(file));
      if (data.version !== 1 || data.dataset_key !== reviewStorageKey(dataset)) throw new Error("Wrong dataset");
      const next = validateReviews(data.reviews, dataset);
      window.localStorage.setItem(reviewStorageKey(dataset), JSON.stringify(next));
      setReviews(next); setError("");
    } catch { setError("Could not import reviews. Check that the file belongs to this exact dataset and browser storage is available."); }
    finally { setLoading(false); }
  }
  function saveReview(review: ReviewRecord) {
    if (!dataset || !selected) return false;
    const next = { ...reviews, [selected.id]: review };
    setReviews(next);
    try { window.localStorage.setItem(reviewStorageKey(dataset), JSON.stringify(next)); setError(""); return true; }
    catch { setError("Browser storage is unavailable. Your review is kept in memory; download reviews before leaving."); return false; }
  }
  return <div className="app-shell">
    <header className="app-header">
      <div className="brand-copy" aria-label="ChatSight Session Review"><span className="product-name">ChatSight</span><span className="brand-divider" aria-hidden="true">/</span><span className="product-context">Session Review</span></div>
      <span className="synthetic-label">{dataset?.dataset.synthetic ? <FlaskConical size={14} /> : <LockKeyhole size={14} />} {dataset?.dataset.synthetic ? "Synthetic data" : dataset ? "Private recorded data" : "Private workspace"}</span>
    <details className="dataset-tools"><summary>Examples &amp; files</summary><div className="dataset-toolbar" aria-label="Dataset controls">
      <button onClick={() => choose(demoDataset)} disabled={loading || uploadBusy}>Steven’s demo</button>
      <button onClick={() => { void chooseExample(() => import("./findings-demo.synthetic.json")); }} disabled={loading || uploadBusy}>Findings demo</button>
      <button onClick={() => { void chooseExample(() => import("./combined-demo.synthetic.json")); }} disabled={loading || uploadBusy}>Combined priority demo</button>
      <label className="file-control">Open local review bundle<input aria-label="Open local review bundle" type="file" accept=".json" disabled={loading || uploadBusy} onChange={event => { void importBundle(event.target.files?.[0]); event.target.value = ""; }} /></label>
      <button disabled={!dataset || loading || uploadBusy} onClick={() => { if (dataset) downloadReviews(dataset, reviews); }}>Download reviews</button>
      <label className="file-control">Import reviews<input aria-label="Import reviews" type="file" accept=".json" disabled={!dataset || loading || uploadBusy} onChange={event => { void importReviews(event.target.files?.[0]); event.target.value = ""; }} /></label>
    </div></details>
    </header>
    <UploadPanel onDataset={choose} onBusy={setUploadBusy} disabled={loading} autoRestore={!initialDataset && !dataset} />
    {error && <p role="alert" className="import-error">{error}</p>}
    {loading && <p role="status" className="dataset-notice">Reading local bundle. No network request.</p>}
    {dataset && <div className="dataset-notice" role="note"><Info size={16} aria-hidden="true" /><details><summary><strong>{dataset.contract_version === 1 ? "Demonstration only." : dataset.dataset.label}</strong> · {dataset.dataset.synthetic ? "Synthetic examples" : "Model findings need your review"}</summary><p>{dataset.dataset.notice} {dataset.contract_version === 1 ? "Illustrative priorities. No anomaly ranking is implemented." : "Model interpretations are not verified tutor errors. Viewing makes no model calls."}</p></details></div>}
    {dataset && selected ? <main><SummaryBar summary={dataset.summary} reviewed={Object.keys(reviews).length} analyzed={dataset.contract_version >= 2 ? dataset.sessions.filter(session => session.analysis?.state === "completed").length : undefined} /><div className="workspace">
      <SessionQueue key={dataset.dataset.id} sessions={dataset.sessions} selectedId={selected.id} reviewedIds={new Set(Object.keys(reviews))} onSelect={setSelectedId} />
      <InvestigationView key={`${dataset.dataset.id}:${selected.id}`} session={selected} review={reviews[selected.id]} onSaveReview={saveReview} />
    </div></main> : !loading && !uploadBusy && <main className="empty-app">Upload a PR100 export, open a saved review bundle, or select a synthetic demo to begin.</main>}
  </div>;
}
