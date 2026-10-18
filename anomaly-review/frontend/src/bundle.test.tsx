import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";
import { demoDataset } from "./data";
import raw from "./findings-demo.synthetic.json";
import { parseBundle, reviewStorageKey, validateReviews } from "./bundle";

function bundle() { return structuredClone(raw); }

describe("review bundle validation", () => {
  it("accepts the Python-produced contract and rejects invented evidence", () => {
    expect(parseBundle(JSON.stringify(raw)).sessions).toHaveLength(6);
    const changed = bundle();
    changed.sessions[0].analysis.findings[0].highlight_ids.push("FAKE");
    expect(() => parseBundle(JSON.stringify(changed))).toThrow(/missing from the timeline/);
  });
  it("rejects unsafe decisions, fabricated metrics and mismatched counts", () => {
    const changed = bundle();
    changed.sessions[0].analysis.state = "not_analyzed";
    expect(() => parseBundle(JSON.stringify(changed))).toThrow();
    const metric = bundle();
    Object.assign(metric.sessions[0].active_time, { value: 0 });
    expect(() => parseBundle(JSON.stringify(metric))).toThrow();
    const count = bundle();
    count.summary.flagged_sessions++;
    expect(() => parseBundle(JSON.stringify(count))).toThrow(/counts disagree/);
  });
  it("isolates reviews and rejects reviews for foreign sessions", () => {
    const a = parseBundle(JSON.stringify(raw));
    const b = parseBundle(JSON.stringify(raw));
    b.dataset.id = "different";
    expect(reviewStorageKey(a)).not.toBe(reviewStorageKey(b));
    expect(() => validateReviews({ unknown: { classification: "insufficient", notes: "", savedAt: null } }, a)).toThrow();
  });
  it("accepts notebook observation scope and renders a capture as source rather than a diff", () => {
    const doc = bundle();
    doc.sessions[0].scope = "notebook_session";
    const event = doc.sessions[0].timeline.find(item => item.kind === "code_edit")!;
    event.kind = "code_capture";
    event.title = "Source captured at execution";
    event.code_diff = { before: null, after: "fictional_capture = 1" };
    render(<App dataset={parseBundle(JSON.stringify(doc))} />);
    fireEvent.click(screen.getByRole("button", { name: /Notebook Source captured at execution/ }));
    expect(screen.getByText("Captured source")).toBeInTheDocument();
    expect(screen.getByText("fictional_capture = 1")).toBeInTheDocument();
    expect(screen.getByText(/PR100 notebook observation window/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^Notebook$/ }));
    expect(screen.getByRole("button", { name: /Notebook Source captured at execution/ })).toBeInTheDocument();
  });
});

describe("integrated review UI", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, "", "/");
    Element.prototype.scrollIntoView = vi.fn();
  });
  it("opens findings, shows evidence/recovery, and reveals hidden timeline events", async () => {
    render(<App dataset={demoDataset} />);
    fireEvent.click(screen.getByText("Examples & files"));
    fireEvent.click(screen.getByRole("button", { name: "Findings demo" }));
    expect(screen.getByRole("heading", { name: "Session findings" })).toBeInTheDocument();
    expect(screen.getByText(/No model inference/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^Checks$/ }));
    const student = screen.queryByRole("button", { name: /Student Student message/ });
    expect(student).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Difficulty persisted after help/ }));
    await waitFor(() => expect(screen.getByRole("button", { name: "All events" })).toHaveAttribute("aria-pressed", "true"));
    expect(screen.getAllByRole("button", { name: /Student Student message/ }).length).toBeGreaterThan(0);
  });
  it("imports recorded-origin bundles locally and clears the old dataset on invalid imports", async () => {
    render(<App dataset={demoDataset} />);
    const recorded = bundle();
    recorded.dataset.synthetic = false;
    recorded.dataset.id = "authored-recorded-import-test";
    recorded.dataset.label = "Authored import test";
    recorded.sessions.forEach(session => { session.synthetic = false; });
    fireEvent.change(screen.getByLabelText("Open local review bundle"), { target: { files: [new File([JSON.stringify(recorded)], "authored.json", { type: "application/json" })] } });
    await waitFor(() => expect(screen.getByText("Private recorded data")).toBeInTheDocument());
    expect(screen.getByText("Authored import test")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Open local review bundle"), { target: { files: [new File(["{}"], "invalid.json")] } });
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Could not open this review bundle"));
    expect(screen.queryByText("Authored import test")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Session findings" })).not.toBeInTheDocument();
  });
  it("imports reviews into the same session without retaining stale form values", async () => {
    const dataset = parseBundle(JSON.stringify(raw));
    render(<App dataset={dataset} />);
    const review = { version: 1, dataset_key: reviewStorageKey(dataset), reviews: {
      [dataset.sessions[0].id]: { classification: "insufficient", notes: "Imported review note", savedAt: "2026-10-15T12:00:00Z" },
    } };
    fireEvent.change(screen.getByLabelText("Import reviews"), { target: { files: [new File([JSON.stringify(review)], "reviews.json")] } });
    await waitFor(() => expect(screen.getByPlaceholderText(/Record what in the timeline/)).toHaveValue("Imported review note"));
    expect(screen.getByLabelText(/Insufficient evidence/)).toBeChecked();
  });
  it("treats message markup as literal text and never claims rejected output is a finding", () => {
    const doc = bundle();
    doc.sessions[0].timeline[0].body = '<img src=x onerror="alert(1)">';
    const dataset = parseBundle(JSON.stringify(doc));
    render(<App dataset={dataset} />);
    fireEvent.click(screen.getAllByRole("button", { name: /Notebook Code edited/ })[0]);
    expect(document.querySelector("img[src=x]")).toBeNull();
  });
});
