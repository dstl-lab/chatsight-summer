import { useCallback, useEffect, useRef, useState } from "react";
import { parseBundle } from "../bundle";
import type { DemoDataset } from "../types";

interface Job {
  id: string; filename: string; status: string; count: number; minutes: number;
  created_at: string; error: string | null; eligible_sessions: number | null;
  source: { events: number; first_event_at: string; last_event_at: string } | null;
  selection?: { exclusions: Record<string, number>; quality: Record<string, number> } | null;
  progress: { completed: number; failed: number; pending: number };
}
interface Service { ready: boolean; gemini_configured: boolean; max_upload_bytes: number; model: string }
const running = (job: Job | null) => !!job && ["preparing", "analyzing"].includes(job.status);
const plural = (value: number, word: string) => `${value} ${word}${value === 1 ? "" : "s"}`;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "The upload service could not complete this request.");
  return body as T;
}

export function UploadPanel({ onDataset, onBusy, disabled = false }: {
  onDataset: (dataset: DemoDataset | null) => void; onBusy: (busy: boolean) => void; disabled?: boolean;
}) {
  const [service, setService] = useState<Service | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [count, setCount] = useState(10);
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
  }, []);
  useEffect(() => { void refresh().catch(() => setService(null)); }, [refresh]);
  useEffect(() => { callbacks.current.onBusy(busy); }, [busy]);

  const load = useCallback(async (next: Job) => {
    const ticket = epoch.current;
    if (["ready", "completed", "stopped", "interrupted"].includes(next.status)) {
      const value = await request<unknown>(`/api/jobs/${next.id}/bundle`);
      if (ticket === epoch.current) callbacks.current.onDataset(parseBundle(JSON.stringify(value)));
    }
  }, []);

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
      setError("Choose a recent PR100 .jsonl or .jsonl.gz export under 50 MB."); return;
    }
    setSending(true);
    try {
      const next = await request<Job>(`/api/uploads?count=${count}&minutes=${minutes}`, {
        method: "POST", headers: { "Content-Type": "application/octet-stream", "X-Review-Request": "1", "X-File-Name": encodeURIComponent(file.name) },
        body: file,
      });
      if (epoch.current !== ticket) return;
      setJob(next); if (!running(next)) await load(next); await refresh();
    } catch (err) { if (epoch.current === ticket) setError(err instanceof Error ? err.message : "Upload failed. Choose the file again."); }
    finally { if (epoch.current === ticket) setSending(false); }
  }

  async function open(id: string) {
    const ticket = ++epoch.current;
    setError(""); setSending(true); callbacks.current.onDataset(null);
    try {
      const next = await request<Job>(`/api/jobs/${id}`);
      if (epoch.current !== ticket) return;
      setJob(next); await load(next);
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

  return <section className="upload-panel" aria-label="Upload recent PR100 data">
    <div className="upload-heading"><div><h2>Upload recent PR100 data</h2><p>Use a private export prepared by someone with database access. This dashboard does not connect to the database.</p></div>
      <span className={service ? "service-ready" : "service-offline"}>{service ? "Upload service connected" : "Upload service offline"}</span></div>
    {!service ? <p>Start the local upload service to prepare raw data. Saved review bundles still open without it. <button onClick={() => { void refresh().catch(() => setError("Upload service is unavailable. Start session-findings-app and reconnect.")); }}>Reconnect</button></p> : <>
      <div className="upload-controls">
        <label>Sessions to analyze<input aria-label="Sessions to analyze" type="number" min="1" max="20" value={count} disabled={busy || disabled} onChange={e => setCount(Math.max(1, Math.min(20, Number(e.target.value) || 1)))} /></label>
        <label>Context per session<select aria-label="Context per session" value={minutes} disabled={busy || disabled} onChange={e => setMinutes(Number(e.target.value))}><option value="25">25 minutes (recommended)</option><option value="10">10 minutes</option></select></label>
        <label className="file-control">Upload PR100 export<input aria-label="Upload PR100 export" type="file" accept=".jsonl,.gz" disabled={busy || disabled} onChange={e => { void upload(e.target.files?.[0]); e.target.value = ""; }} /></label>
      </div>
      <p className="upload-hint">Prepares your requested number of eligible notebook windows. Upload and preview make no model calls. Analysis sends selected messages, captured code, outputs and checks to Gemini.</p>
      {sending && <p role="status">Sending request…</p>}
      {job && <div className="upload-job"><strong>{job.filename}</strong>
        <p role="status">{job.status === "preparing" ? "Preparing uploaded events…" : job.status === "analyzing" ? `Analyzing: ${job.progress.completed + job.progress.failed} / ${job.count} responses saved` : job.status === "ready" ? `${plural(job.count, "session")} ready from ${job.eligible_sessions} eligible notebook scopes` : job.status === "completed" ? `Finished: ${plural(job.progress.completed, "response")} saved, ${plural(job.progress.failed, "request")} failed` : job.status === "failed" ? "Could not prepare this export" : "Analysis stopped; saved results are preserved"}</p>
        {job.source && <small>{job.source.events.toLocaleString()} events · {new Date(job.source.first_event_at).toLocaleString()} – {new Date(job.source.last_event_at).toLocaleString()} · {job.minutes}-minute context</small>}
        {job.selection && <details><summary>Preparation coverage</summary><p>Windows are selected before analysis. Larger or inconsistent windows are excluded rather than shortened.</p><ul>{Object.entries(job.selection.exclusions).map(([key, value]) => <li key={key}>{({ missing_required_observation_family: "Windows without required observations", oversized_observation_window: "Windows over the analysis size limit", invalid_observation_links: "Windows with inconsistent event links", mixed_or_unknown_mode_window: "Windows with mixed or unknown tutor mode" } as Record<string, string>)[key] ?? "Other excluded windows"}: {value}</li>)}</ul>{!!job.selection.quality.missing_page_notebook_identity && <p>Records without a usable page/notebook identity: {job.selection.quality.missing_page_notebook_identity}</p>}</details>}
        {job.error && <p role="alert">{job.error}</p>}
        {running(job) && !sending && <button onClick={() => { epoch.current++; setJob(null); setError(""); callbacks.current.onDataset(null); }}>Leave job view (continues in service)</button>}
        {["ready", "stopped", "interrupted"].includes(job.status) && <button className="analyze-button" disabled={!service.gemini_configured || busy || disabled} onClick={() => { void analyze(); }}>{job.status === "ready" ? `Analyze ${plural(job.count, "session")} with Gemini` : "Continue untouched sessions with Gemini"}</button>}
        {!service.gemini_configured && <p>The service needs a Gemini key to analyze. Database credentials are not needed.</p>}
        {["ready", "completed", "stopped", "interrupted"].includes(job.status) && <a href={`/api/jobs/${job.id}/bundle`} download="pr100-review.private.json">Download review bundle</a>}
      </div>}
      {!!jobs.length && <details className="saved-uploads"><summary>Saved uploads ({jobs.length})</summary><ul>{jobs.map(item => <li key={item.id}><button disabled={busy || disabled} onClick={() => { void open(item.id); }}>{item.filename} · {item.status} · {new Date(item.created_at).toLocaleString()}</button></li>)}</ul></details>}
    </>}
    {error && <p role="alert" className="import-error">{error}</p>}
  </section>;
}
