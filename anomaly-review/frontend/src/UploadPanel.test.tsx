import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import raw from "./findings-demo.synthetic.json";
import { UploadPanel } from "./components/UploadPanel";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); window.sessionStorage.clear(); });
const id = "1".repeat(32);
function bundle(completed = false) {
  const data = structuredClone(raw);
  data.sessions = data.sessions.slice(0, 1);
  data.sessions[0].flagged = false; data.sessions[0].reasons = [];
  Object.assign(data.sessions[0].analysis, { state: completed ? "completed" : "not_analyzed", decision: completed ? "no_supported_finding" : null, findings: [], summary: "Fictional upload test." });
  data.summary.total_sessions = 1; data.summary.flagged_sessions = 0;
  return data;
}
function setup(saved = false) {
  const job = { id, filename: "fictional.jsonl", status: saved ? "completed" : "ready", count: 1, minutes: 25,
    created_at: "2026-10-16T12:00:00Z", error: null, eligible_sessions: 1, source: null,
    progress: { completed: saved ? 1 : 0, failed: 0, pending: 0 } };
  let analyzed = saved;
  const fetcher = vi.fn(async (path: string, options?: RequestInit) => {
    let data: unknown;
    if (path === "/api/status") data = { ready: true, model_configured: true, provider: "Authored test", max_upload_bytes: 50 * 1024 * 1024, model: "fictional-model" };
    else if (path === "/api/jobs") data = { jobs: saved ? [job] : [] };
    else if (path.startsWith("/api/uploads")) data = job;
    else if (path === `/api/jobs/${id}/analyze` && options?.method === "POST") {
      analyzed = true; data = { ...job, status: "analyzing" };
    } else if (path === `/api/jobs/${id}/bundle`) data = bundle(analyzed);
    else if (path === `/api/jobs/${id}`) data = { ...job, status: analyzed ? "completed" : "ready", progress: { completed: analyzed ? 1 : 0, failed: 0, pending: 0 } };
    else throw new Error("Unexpected request");
    return new Response(JSON.stringify(data), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetcher);
  const onDataset = vi.fn();
  render(<UploadPanel onDataset={onDataset} onBusy={vi.fn()} />);
  return { fetcher, onDataset };
}

describe("raw PR100 upload", () => {
  it("defaults to complete coverage, opens batches without dispatching analysis", async () => {
    const child = "2".repeat(32);
    const collection = { id, kind: "collection", filename: "week.jsonl.gz", status: "ready", count: 21, minutes: 25,
      created_at: "2026-10-17T12:00:00Z", error: null, source: null, coverage: { tutor_requests: 22, eligible: 21, awaiting_followup_window: 1 },
      progress: { completed: 0, failed: 0, pending: 0 }, batches: [{ id: child, filename: "batch 1", status: "ready", count: 20, progress: { completed: 0, failed: 0, pending: 0 } }] };
    const fetcher = vi.fn(async (path: string) => {
      const value = path === "/api/status" ? { ready: true, model_configured: true, provider: "Authored test", model: "fictional-model", max_upload_bytes: 2 * 1024 ** 3 } :
        path === "/api/jobs" ? { jobs: [] } : path.startsWith("/api/uploads") ? collection :
        path === `/api/jobs/${child}` ? { ...collection, kind: undefined, parent_id: id, id: child, count: 1, eligible_sessions: 21 } :
        path === `/api/jobs/${child}/bundle` ? bundle() : null;
      if (!value) throw new Error("Unexpected request");
      return new Response(JSON.stringify(value), { status: 200 });
    });
    vi.stubGlobal("fetch", fetcher);
    const onDataset = vi.fn();
    render(<UploadPanel onDataset={onDataset} onBusy={vi.fn()} />);
    fireEvent.change(await screen.findByLabelText("Upload PR100 export"), { target: { files: [new File(["fictional"], "week.jsonl.gz")] } });
    await screen.findByText("21 windows · 1 batch");
    expect(fetcher.mock.calls.some(([path]) => path.includes("mode=all"))).toBe(true);
    expect(fetcher.mock.calls.some(([path]) => path.endsWith("/analyze") || path === `/api/jobs/${id}/bundle`)).toBe(false);
    fireEvent.click(screen.getByText("Analyze the full export"));
    expect(screen.getByRole("button", { name: "Analyze all 21 windows" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Open batch 1" }));
    await screen.findByText("All batches");
    await waitFor(() => expect(onDataset).toHaveBeenLastCalledWith(expect.objectContaining({ sessions: expect.any(Array) })));
  });

  it("pages a large batch list and restores saved exports without starting analysis", async () => {
    const batches = Array.from({ length: 13 }, (_, i) => ({ id: String(i + 1).padStart(32, "0"), status: "ready", count: 20, filename: `batch ${i + 1}`, progress: { completed: 0, failed: 0, pending: 0 } }));
    const collection = { id, kind: "collection", filename: "fictional-week.jsonl.gz", status: "ready", count: 260, minutes: 25,
      created_at: "2026-10-17T12:00:00Z", source: null, progress: { completed: 0, failed: 0, pending: 0 }, batches };
    const fetcher = vi.fn(async (path: string) => new Response(JSON.stringify(path === "/api/status" ? { ready: true, model_configured: true, provider: "Authored test", model: "fictional-model" } : path === "/api/jobs" ? { jobs: [collection] } : collection), { status: 200 }));
    vi.stubGlobal("fetch", fetcher);
    render(<UploadPanel onDataset={vi.fn()} onBusy={vi.fn()} autoRestore />);
    await screen.findByRole("button", { name: "Open batch 1" });
    expect(screen.getAllByRole("button", { name: /^Open batch/ })).toHaveLength(6);
    expect(screen.getByRole("button", { name: /Analyze all/ }).closest("details")).not.toHaveAttribute("open");
    fireEvent.click(screen.getByRole("button", { name: "Next batches" }));
    expect(screen.queryByRole("button", { name: "Open batch 1" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open batch 7" })).toBeInTheDocument();
    expect(fetcher.mock.calls.some(([path]) => path.endsWith("/analyze"))).toBe(false);
  });

  it("keeps grouped analysis counts distinct from eligible requests and details collapsed", async () => {
    const collection = { id, kind: "collection", grouped: true, filename: "fictional-grouped.jsonl.gz", status: "ready", count: 2950, minutes: 25,
      created_at: "2026-10-18T12:00:00Z", source: null, coverage: { tutor_requests: 10295, eligible: 8284, analysis_units: 2950 },
      optimization: { workers: 4, compact: true, thinking: "default", transport: "concurrent" },
      progress: { completed: 0, failed: 0, pending: 0 }, batches: [{ id: "2".repeat(32), filename: "batch 1", count: 20, status: "ready", progress: { completed: 0, failed: 0, pending: 0 } }] };
    const fetcher = vi.fn(async (path: string) => new Response(JSON.stringify(path === "/api/status" ? { ready: true, gemini_configured: true } : path === "/api/jobs" ? { jobs: [collection] } : collection), { status: 200 }));
    vi.stubGlobal("fetch", fetcher);
    render(<UploadPanel onDataset={vi.fn()} onBusy={vi.fn()} autoRestore />);
    await screen.findByText("2,950 sequences · 1 batch");
    expect(screen.getByRole("columnheader", { name: "Sequences" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analyze all 2,950 sequences" })).toBeEnabled();
    expect(screen.getByText("Data details & coverage").closest("details")).not.toHaveAttribute("open");
    expect(screen.getByText("8,284")).toBeInTheDocument();
    expect(fetcher.mock.calls.some(([path]) => path.endsWith("/analyze"))).toBe(false);
  });

  it("previews without analysis and runs Gemini only through the explicit button", async () => {
    const { fetcher, onDataset } = setup();
    const input = await screen.findByLabelText("Upload PR100 export");
    fireEvent.change(screen.getByLabelText("Coverage"), { target: { value: "sample" } });
    fireEvent.change(screen.getByLabelText("Sessions to analyze"), { target: { value: "1" } });
    fireEvent.change(input, { target: { files: [new File(["fictional raw events"], "fictional.jsonl")] } });
    await screen.findByText("Ready to analyze");
    await waitFor(() => expect(onDataset).toHaveBeenLastCalledWith(expect.objectContaining({ sessions: expect.arrayContaining([expect.objectContaining({ analysis: expect.objectContaining({ state: "not_analyzed" }) })]) })));
    expect(fetcher.mock.calls.some(([path]) => path.endsWith("/analyze"))).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Analyze 1 window" }));
    await screen.findByText("Analysis complete", {}, { timeout: 3000 });
    expect(fetcher.mock.calls.filter(([path]) => path.endsWith("/analyze"))).toHaveLength(1);
    expect(onDataset).toHaveBeenLastCalledWith(expect.objectContaining({ sessions: expect.arrayContaining([expect.objectContaining({ analysis: expect.objectContaining({ state: "completed" }) })]) }));
  });

  it("rejects saved-results files as raw inputs and clears the prior dataset", async () => {
    const { fetcher, onDataset } = setup();
    fireEvent.change(await screen.findByLabelText("Upload PR100 export"), { target: { files: [new File(["{}"], "results.json")] } });
    expect(await screen.findByRole("alert")).toHaveTextContent(".jsonl or .jsonl.gz");
    expect(onDataset).toHaveBeenLastCalledWith(null);
    expect(fetcher.mock.calls.some(([path]) => path.startsWith("/api/uploads"))).toBe(false);
  });

  it("reopens a completed saved upload without posting another model request", async () => {
    const { fetcher, onDataset } = setup(true);
    const select = await screen.findByLabelText("Saved exports");
    fireEvent.change(select, { target: { value: id } });
    await waitFor(() => expect(onDataset).toHaveBeenLastCalledWith(expect.objectContaining({ summary: expect.objectContaining({ total_sessions: 1 }) })));
    expect(fetcher.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false);
  });
});
