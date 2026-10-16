import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { App } from "./App";
import { demoDataset } from "./data";
import { reviewStorageKey } from "./bundle";

describe("instructor prototype", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, "", "/");
  });

  it("shows synthetic provenance and dashboard totals", () => {
    render(<App />);
    expect(screen.getByText("Demonstration only.")).toBeInTheDocument();
    expect(screen.getByText("Total Sessions").previousElementSibling).toHaveTextContent("4");
    expect(screen.getByText("Flagged Sessions").previousElementSibling).toHaveTextContent("3");
    expect(screen.getByRole("heading", { name: "STU-104 / Q5.1" })).toBeInTheDocument();
    expect(screen.getByText("Repeated failures after tutor help")).toBeInTheDocument();
  });

  it("opens another session from the review queue", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /STU-067/ }));
    expect(screen.getByRole("heading", { name: "STU-067 / Q2.4" })).toBeInTheDocument();
    expect(screen.getByText("Multiple tutor responses before recovery")).toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get("session")).toBeTruthy();
  });

  it("stores an instructor assessment in browser-local state", () => {
    render(<App />);
    fireEvent.click(screen.getByLabelText(/Student struggle/));
    fireEvent.change(screen.getByPlaceholderText(/Record what in the timeline/), {
      target: { value: "Tutor response was relevant; the student continued testing." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save review" }));
    expect(screen.getByRole("button", { name: "Saved locally" })).toBeInTheDocument();
    const stored = JSON.parse(window.localStorage.getItem(reviewStorageKey(demoDataset))!);
    expect(Object.values(stored)[0]).toMatchObject({
      classification: "student_struggle",
      notes: "Tutor response was relevant; the student continued testing.",
    });
  });

  it("expands a collapsed timeline event", () => {
    render(<App />);
    const edit = screen.getAllByRole("button", { name: /Notebook Code edited/ })[0];
    expect(edit).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(edit);
    expect(edit).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Cell answer-5-1 changed to revision b-rev1.")).toBeInTheDocument();
  });
});
