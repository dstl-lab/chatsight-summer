import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, Database, LoaderCircle, Upload } from "lucide-react";
import { parseBundle } from "../bundle";
import type { DemoDataset } from "../types";

interface Job {
  grouped?: boolean;
  optimization?: { workers: number; compact: boolean; thinking: string; transport: string };
  runtime?: { estimated_remaining_seconds: number | null; mean_call_seconds: number | null; p95_call_seconds: number | null; reused: number; transport: string; workers: number | null; usage: Record<string, number>; original_characters: number; sent_characters: number };
  kind?: "collection"; parent_id?: string;
  batches?: { id: string; filename: string; status: string; count: number; progress: { completed: number; failed: number; pending: number } }[];
  coverage?: Record<string, number> | null;
  import_progress?: { phase: string; events?: number; requests?: number; eligible?: number } | null;
  id: string; filename: string; status: string; count: number; minutes: number;
  created_at: string; error: string | null; eligible_sessions: number | null;
  source: { events: number; first_event_at: string; last_event_at: string; input_events?: number; duplicate_events?: number; missing_scope?: number; missing_occurrence_time?: number } | null;
  selection?: { exclusions: Record<string, number>; quality: Record<string, number> } | null;
  progress: { completed: number; failed: number; pending: number };
}
interface Service {
  ready: boolean;
  model_configured?: boolean;
  gemini_configured?: boolean;
  max_upload_bytes: number;
  model?: string;
  provider?: string;
  optimization?: Job["optimization"] | null;
  grouped?: boolean;
}
const running = (job: Job | null) => !!job && ["preparing", "analyzing"].includes(job.status);
const plural = (value: number, word: string) => `${value} ${word}${value === 1 ? "" : word.endsWith("ch") ? "es" : "s"}`;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "The upload service could not complete this request.");
  return body as T;
}

export function UploadPanel({ onDataset, onBusy, disabled = false, autoRestore = false }: {
  onDataset: (dataset: DemoDataset | null) => void; onBusy: (busy: boolean) => void; disabled?: boolean; autoRestore?: boolean;
}) {
  const [service, setService] = useState<Service | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [count, setCount] = useState(10);
  const [mode, setMode] = useState("all");
  const [minutes, setMinutes] = useState(25);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const callbacks = useRef({ onDataset, onBusy });
  callbacks.current = { onDataset, onBusy };
  const epoch = useRef(0);
  const busy = sending || running(job);

  const refresh = useCallback(async () => {
    const info = await request<Service>("/api/status");
    setService(info);
    const list = await request<{ jobs: Job[] }>("/api/jobs");
    setJobs(list.jobs);
    return list.jobs;
  }, []);

  useEffect(() => { callbacks.current.onBusy(busy); }, [busy]);

  const load = useCallback(async (next: Job) => {
    const ticket = epoch.current;
    if (next.kind === "collection") { callbacks.current.onDataset(null); return; }
    if (["ready", "completed", "stopped", "interrupted"].includes(next.status)) {
      const value = await request<unknown>(`/api/jobs/${next.id}/bundle`);
      if (ticket === epoch.current) callbacks.current.onDataset(parseBundle(JSON.stringify(value)));
    }
  }, []);

  const restoreAllowed = useRef(autoRestore);
  restoreAllowed.current = autoRestore;
  useEffect(() => {
    let cancelled = false;
    void refresh().then(async list => {
      if (cancelled || !restoreAllowed.current || epoch.current !== 0) return;
      let previous: string | null = null;
      try { previous = window.sessionStorage.getItem("chatsight-active-upload"); } catch { /* Optional convenience. */ }
      const saved = list.find(item => item.id === previous) ?? list.find(item => item.status !== "failed");
      if (!saved) return;
      const next = await request<Job>(`/api/jobs/${saved.id}`);
      if (cancelled || !restoreAllowed.current || epoch.current !== 0) return;
      setJob(next); await load(next);
    }).catch(() => { if (!cancelled) setService(null); });
    return () => { cancelled = true; };
  }, [refresh, load]);
  useEffect(() => {
    if (job) { try { window.sessionStorage.setItem("chatsight-active-upload", job.parent_id ?? job.id); } catch { /* Optional convenience. */ } }
  }, [job?.id]);
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    if (!job || !running(job)) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        const next = await request<Job>(`/api/jobs/${job.id}`);
        if (cancelled) return;
        if (!running(next)) {
          await load(next);
          if (!cancelled) { setJob(next); await refresh(); }
        } else { setJob(next); timer = setTimeout(() => { void tick(); }, 2000); }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Connection lost. Saved jobs can be reopened after reconnecting.");
        timer = setTimeout(() => { void tick(); }, 5000);
      }
    };
    timer = setTimeout(() => { void tick(); }, 500);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [job?.id, job?.status, load, refresh]);

  async function upload(file?: File) {
    if (!file || !service) return;
    const ticket = ++epoch.current;
    callbacks.current.onDataset(null); setJob(null); setError("");
    if (file.size > service.max_upload_bytes || !/\.jsonl(\.gz)?$/i.test(file.name)) {
      setError("Choose a recent PR100 .jsonl or .jsonl.gz export up to 2 GB. Sample mode accepts up to 50 MB."); return;
    }
    setSending(true);
    try {
      const next = await request<Job>(`/api/uploads?count=${count}&minutes=${minutes}&mode=${mode}`, {
        method: "POST", headers: { "Content-Type": "application/octet-stream", "X-Review-Request": "1", "X-File-Name": encodeURIComponent(file.name) },
        body: file,
      });
      if (epoch.current !== ticket) return;
      setJob(next); setShowUpload(false); if (!running(next)) await load(next); await refresh();
    } catch (err) { if (epoch.current === ticket) setError(err instanceof Error ? err.message : "Upload failed. Choose the file again."); }
    finally { if (epoch.current === ticket) setSending(false); }
  }

  async function open(id: string) {
    const ticket = ++epoch.current;
    setError(""); setSending(true); callbacks.current.onDataset(null);
    try {
      const next = await request<Job>(`/api/jobs/${id}`);
      if (epoch.current !== ticket) return;
      setJob(next); setShowUpload(false); await load(next);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not open this upload."); }
    finally { setSending(false); }
  }

  async function analyze() {
    if (!job) return;
    setError(""); setSending(true); callbacks.current.onDataset(null);
    try {
      setJob(await request<Job>(`/api/jobs/${job.id}/analyze`, { method: "POST", headers: { "X-Review-Request": "1" }, body: "" }));
    } catch (err) { setError(err instanceof Error ? err.message : "Analysis could not start. Saved responses remain available."); }
    finally { setSending(false); }
  }

  const collection = job?.kind === "collection";
  const unitName = job?.grouped ? "sequence" : "window";
  const modelConfigured = service?.model_configured ?? service?.gemini_configured ?? false;
  const providerName = service?.provider ?? "Gemini";
  const modelName = service?.model ? ` using ${service.model}` : "";
  const savedCount = job ? job.progress.completed + job.progress.failed : 0;
  const readyToAnalyze = job && ["ready", "stopped", "interrupted"].includes(job.status);
  const nextBatch = job?.batches?.find(batch => ["ready", "interrupted", "stopped"].includes(batch.status)) ?? job?.batches?.[0];
  const title = !job ? "Choose your data" : job.parent_id ? (job.filename.match(/batch \d+$/i)?.[0] ?? "Review batch").replace(/^b/, "B") : "Production data";
  const status = job ? ({ preparing: "Preparing data", analyzing: "Analysis in progress", ready: "Ready to analyze", completed: "Analysis complete", failed: "Import failed", stopped: "Analysis paused", interrupted: "Analysis paused" } as Record<string, string>)[job.status] ?? job.status : "";
  const dateRange = job?.source ? `${shortDate(job.source.first_event_at)} – ${shortDate(job.source.last_event_at)}` : "";

  return <section className={`upload-panel ${job && !collection ? "upload-panel--batch" : ""}`} aria-label="Upload recent PR100 data">
    <div className="upload-heading">
      <div className="data-title"><Database size={20} aria-hidden="true" /><div><h2>{title}</h2>
        {job && <p className="source-caption" title={job.filename}>{job.parent_id ? `${plural(job.count, unitName)} · ${job.grouped ? "grouped context" : `${job.minutes}-minute context`} · ${status}` : dateRange || job.filename}</p>}
      </div></div>
      <div className="data-switcher">
        {!!jobs.length && <label><span className="sr-only">Saved exports</span><select aria-label="Saved exports" disabled={busy || disabled} value={job?.parent_id ?? job?.id ?? ""} onChange={e => { if (e.target.value) void open(e.target.value); }}>
          <option value="">Choose saved export</option>{jobs.map(item => <option key={item.id} value={item.id}>{shortDate(item.created_at)} · {item.filename}</option>)}
        </select></label>}
        <button className="quiet-button" disabled={busy || disabled} onClick={() => setShowUpload(value => !value)}><Upload size={15} /> {showUpload ? "Close upload" : "Upload new"}</button>
      </div>
    </div>
    {!service ? <div className="inline-notice"><span>Local service unavailable.</span><button onClick={() => { void refresh().catch(() => setError("Start the local upload service, then reconnect.")); }}>Reconnect</button></div> : <>
      {(!job || showUpload) && <div className="upload-form">
        <label className="file-control upload-drop">Upload PR100 export<input aria-label="Upload PR100 export" type="file" accept=".jsonl,.gz" disabled={busy || disabled} onChange={e => { void upload(e.target.files?.[0]); e.target.value = ""; }} /></label>
        <p>Choose a .jsonl.gz export. Uploading does not start analysis.</p>
        <details className="upload-options"><summary>Import settings</summary><div className="upload-controls">
          <label>Coverage<select aria-label="Coverage" value={mode} disabled={busy || disabled} onChange={e => setMode(e.target.value)}><option value="all">All eligible tutor windows</option><option value="sample">Small development sample</option></select></label>
          {mode === "sample" && <label>Sessions to analyze<input aria-label="Sessions to analyze" type="number" min="1" max="20" value={count} disabled={busy || disabled} onChange={e => setCount(Math.max(1, Math.min(20, Number(e.target.value) || 1)))} /></label>}
          <label>Context per session<select aria-label="Context per session" value={minutes} disabled={busy || disabled} onChange={e => setMinutes(Number(e.target.value))}><option value="25">25 minutes (recommended)</option><option value="10">10 minutes</option></select></label>
        </div></details>
      </div>}
      {sending && <p role="status" className="request-status"><LoaderCircle size={16} /> Loading…</p>}
      {job && <div className="upload-job">
        <div className="job-overview">
          <div className="job-status"><span className={`status-dot status-dot--${job.status}`} /> <strong role="status">{status}</strong>
            {collection && job.status !== "preparing" && <span className="job-count">{job.count.toLocaleString()} {unitName}s · {plural(job.batches?.length ?? 0, "batch")}</span>}
          </div>
          <div className="job-actions">
            {job.parent_id && <button className="quiet-button" disabled={sending} onClick={() => { void open(job.parent_id!); }}><ArrowLeft size={14} /> All batches</button>}
            {collection && nextBatch && !running(job) && job.status !== "failed" && <button className="primary-button" disabled={sending || disabled} onClick={() => { void open(nextBatch.id); }}>{nextBatch.status === "completed" ? "Review results" : "Open next batch"}<ArrowRight size={15} /></button>}
            {!collection && readyToAnalyze && <button className="primary-button" disabled={!job.count || !modelConfigured || busy || disabled} onClick={() => { void analyze(); }}>{job.status === "ready" ? `Analyze ${plural(job.count, unitName)}` : "Continue analysis"}<ArrowRight size={15} /></button>}
            {!collection && job.status === "completed" && <span className="completion-label"><CheckCircle2 size={16} /> Results ready below</span>}
          </div>
        </div>
        {job.status === "preparing" && <p className="processing-copy">{job.import_progress?.phase ?? "Preparing uploaded events"}{job.import_progress?.events ? ` · ${job.import_progress.events.toLocaleString()} events read` : job.import_progress?.requests ? ` · ${job.import_progress.requests.toLocaleString()} requests checked` : ""}</p>}
        {job.count > 0 && (running(job) && job.status === "analyzing" || savedCount > 0) && <div className="analysis-progress"><progress aria-label="Analysis progress" max={job.count} value={savedCount} /><span>{job.progress.completed.toLocaleString()} / {job.count.toLocaleString()} analyzed{job.progress.failed > 0 ? ` · ${job.progress.failed} failed` : ""}</span></div>}
        {!collection && readyToAnalyze && <p className="model-disclosure">Analysis sends these {job.count} {unitName}s to {providerName}{modelName}.</p>}
        {job.runtime?.estimated_remaining_seconds != null && job.status === "analyzing" && <p className="eta-estimate">Est. {formatRemaining(job.runtime.estimated_remaining_seconds)} remaining · based on saved calls and configured limits</p>}
        {job.error && <p role="alert" className="job-error">{job.error}</p>}
        {!modelConfigured && readyToAnalyze && <p className="job-error">Add an API key for {providerName} to the local service to analyze.</p>}
        {!!job.batches?.length && <BatchList key={job.id} batches={job.batches} disabled={sending || disabled || job.status === "failed"} active={running(job)} grouped={job.grouped} onOpen={id => { void open(id); }} />}
        {collection && readyToAnalyze && <details className="bulk-analysis"><summary>Analyze the full export</summary><div><p>This starts {job.count.toLocaleString()} {unitName}s with {providerName}. Saved results are reused.</p><button disabled={!job.count || !modelConfigured || busy || disabled} onClick={() => { void analyze(); }}>Analyze all {job.count.toLocaleString()} {unitName}s</button></div></details>}
        {(job.source || job.coverage || job.selection) && <details className="data-details"><summary>Data details & coverage</summary><div className="details-content">
          <p className="source-filename">{job.filename}</p>
          {job.optimization && <p>{job.optimization.transport === "batch" ? "Google Batch API" : `${job.optimization.workers} parallel workers`} · {job.optimization.compact ? "Lossless compact prompts" : "Original prompt format"} · Thinking: {job.optimization.thinking}</p>}
          {job.grouped && <p>Time-based sequences can include several requests or questions. Groups have a 60-minute span cap; the coverage download maps requests to sequences.</p>}
          {job.runtime && <dl className="coverage-counts">
            <div><dt>Average call time</dt><dd>{job.runtime.mean_call_seconds == null ? "Not measured" : `${job.runtime.mean_call_seconds.toFixed(1)} sec`}</dd></div>
            <div><dt>Saved assessments reused</dt><dd>{job.runtime.reused}</dd></div>
            {Object.entries(job.runtime.usage).map(([key,value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{value.toLocaleString()}</dd></div>)}
            {job.runtime.original_characters > 0 && <div><dt>Input characters saved</dt><dd>{Math.round(100*(1-job.runtime.sent_characters/job.runtime.original_characters))}%</dd></div>}
          </dl>}
          {job.source && <p>{job.source.events.toLocaleString()} events · {dateRange}</p>}
          {job.source?.input_events && <p>{(job.source.duplicate_events ?? 0).toLocaleString()} duplicate receipts removed. {(job.source.missing_scope ?? 0).toLocaleString()} events lack notebook identity; {(job.source.missing_occurrence_time ?? 0).toLocaleString()} lack an occurrence time. These remain in the source archive.</p>}
          {job.coverage && <><p>Excluded requests are not negative findings. Windows can overlap.</p><dl className="coverage-counts">{Object.entries(job.coverage).map(([key, value]) => <div key={key}><dt>{coverageLabels[key] ?? key.replaceAll("_", " ")}</dt><dd>{value.toLocaleString()}</dd></div>)}</dl><a href={`/api/jobs/${job.id}/coverage`} download="pr100-coverage.private.jsonl">Download coverage</a></>}
          {job.selection && <dl className="coverage-counts">{Object.entries(job.selection.exclusions).map(([key, value]) => <div key={key}><dt>{coverageLabels[key] ?? key.replaceAll("_", " ")}</dt><dd>{value}</dd></div>)}</dl>}
          <p>{job.grouped ? "Grouped context includes the before/after windows of its member requests." : job.minutes === 25 ? "25-minute windows include 5 minutes before and 20 after a request." : "10-minute windows include 3 minutes before and 7 after a request."} Later activity outside that window is unavailable to the assessment.</p>
          {job.kind !== "collection" && ["ready", "completed", "stopped", "interrupted"].includes(job.status) && <a href={`/api/jobs/${job.id}/bundle`} download="pr100-review.private.json">Download review bundle</a>}
        </div></details>}
        {running(job) && !sending && <button className="quiet-button leave-job" onClick={() => { epoch.current++; setJob(null); setError(""); callbacks.current.onDataset(null); }}>Leave this view · continues in background</button>}
      </div>}
    </>}
    {error && <p role="alert" className="job-error">{error}</p>}
  </section>;
}

const shortDate = (value: string) => new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
const coverageLabels: Record<string, string> = {
  analysis_units: "Analysis sequences", tutor_requests: "Tutor requests", eligible: "Ready for analysis", not_tutor_mode: "Other tutor modes", missing_scope: "Missing notebook identity", missing_occurrence_time: "Missing event time",
  before_production_observation_start: "Before production start", awaiting_followup_window: "Awaiting follow-up", no_completed_response_for_anchor: "No completed response", invalid_anchor_request: "Invalid request binding",
  invalid_observation_links: "Inconsistent evidence links", mixed_or_unknown_tutor_mode: "Mixed tutor modes", oversized_window: "Over the size limit", eligible_with_partial_start: "Partial earlier context",
  missing_required_observation_family: "Missing observations", oversized_observation_window: "Over the size limit", mixed_or_unknown_mode_window: "Mixed tutor modes",
};

function BatchList({ batches, disabled, active, grouped = false, onOpen }: { batches: NonNullable<Job["batches"]>; disabled: boolean; active: boolean; grouped?: boolean; onOpen: (id: string) => void }) {
  const [page, setPage] = useState(0);
  const pageSize = 6;
  const start = page * pageSize;
  const labels: Record<string, string> = { ready: "Ready", completed: "Analyzed", analyzing: "Analyzing", stopped: "Paused", interrupted: "Paused", failed: "Failed" };
  return <section className="review-batches" aria-label="Review batches"><div className="batch-list-heading"><h3>Review batches</h3><span>{batches.length.toLocaleString()} total</span></div>
    <div className="batch-table-wrap"><table><thead><tr><th>Batch</th><th>{grouped ? "Sequences" : "Windows"}</th><th>Status</th><th><span className="sr-only">Action</span></th></tr></thead><tbody>
      {batches.slice(start, start + pageSize).map((batch, index) => <tr key={batch.id}><td>{start + index + 1}</td><td>{batch.count}</td><td><span className={`batch-status batch-status--${batch.status}`}>{labels[batch.status] ?? batch.status}</span></td><td><button aria-label={`Open batch ${start + index + 1}`} disabled={disabled || (active && batch.status !== "completed")} onClick={() => onOpen(batch.id)}>{batch.status === "completed" ? "Review" : "Open"}<ArrowRight size={14} /></button></td></tr>)}
    </tbody></table></div>
    {batches.length > pageSize && <nav className="batch-pagination" aria-label="Batch pages"><span>{start + 1}–{Math.min(start + pageSize, batches.length)} of {batches.length}</span><div><button disabled={page === 0} aria-label="Previous batches" onClick={() => setPage(value => value - 1)}>Previous</button><button disabled={start + pageSize >= batches.length} aria-label="Next batches" onClick={() => setPage(value => value + 1)}>Next</button></div></nav>}
  </section>;
}

function formatRemaining(seconds: number) {
  const minutes = Math.max(1, Math.ceil(seconds / 60));
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}
