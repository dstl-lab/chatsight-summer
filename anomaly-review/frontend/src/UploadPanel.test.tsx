import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import raw from "./findings-demo.synthetic.json";
import { UploadPanel } from "./components/UploadPanel";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
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
    if (path === "/api/status") data = { ready: true, gemini_configured: true, max_upload_bytes: 50 * 1024 * 1024, model: "fictional-model" };
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
  it("previews without analysis and runs Gemini only through the explicit button", async () => {
    const { fetcher, onDataset } = setup();
    const input = await screen.findByLabelText("Upload PR100 export");
    fireEvent.change(screen.getByLabelText("Sessions to analyze"), { target: { value: "1" } });
    fireEvent.change(input, { target: { files: [new File(["fictional raw events"], "fictional.jsonl")] } });
    await screen.findByText("1 session ready from 1 eligible notebook scopes");
    await waitFor(() => expect(onDataset).toHaveBeenLastCalledWith(expect.objectContaining({ sessions: expect.arrayContaining([expect.objectContaining({ analysis: expect.objectContaining({ state: "not_analyzed" }) })]) })));
    expect(fetcher.mock.calls.some(([path]) => path.endsWith("/analyze"))).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Analyze 1 session with Gemini" }));
    await screen.findByText("Finished: 1 response saved, 0 requests failed", {}, { timeout: 3000 });
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
    const button = await screen.findByText(/fictional.jsonl · completed/);
    fireEvent.click(button);
    await waitFor(() => expect(onDataset).toHaveBeenLastCalledWith(expect.objectContaining({ summary: expect.objectContaining({ total_sessions: 1 }) })));
    expect(fetcher.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false);
  });
});
