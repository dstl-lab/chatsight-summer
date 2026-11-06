import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { assignmentDemo, studentStudyDemo } from "./assignment-demo";
import { collectQuestions } from "./assignment-insights";
import { StudentStudy, topicDistribution } from "./components/StudentStudy";
import { App } from "./App";
import { studyQuestions, summarizeStudyQuestion } from "./student-evidence";

describe("synthetic student study", () => {
  it("counts each message once even when concepts overlap", () => {
    const messages = collectQuestions(assignmentDemo().sessions);
    const groups = topicDistribution(messages);
    expect(groups.reduce((sum, group) => sum + group.count, 0)).toBe(messages.length);
    expect(groups.some(group => group.label === "Filtering rows")).toBe(true);
    expect(groups.some(group => group.label === "Other / not identified")).toBe(true);
  });

  it("shows only the selected synthetic student's messages and clears practice feedback on switch", () => {
    render(<StudentStudy dataset={assignmentDemo()} />);
    expect(screen.getAllByText(/DataFrame filter return an empty table/).length).toBeGreaterThan(0);
    expect(screen.queryAllByText(/index out of bounds/)).toHaveLength(0);
    fireEvent.click(screen.getByLabelText("age >= 18"));
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(screen.getByRole("status")).toHaveTextContent("Correct");
    fireEvent.change(screen.getByLabelText("Example student"), { target: { value: "STU-103" } });
    expect(screen.getAllByText(/index out of bounds/).length).toBeGreaterThan(0);
    expect(screen.queryAllByText(/DataFrame filter return an empty table/)).toHaveLength(0);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Check answer" })).toBeDisabled();
  });

  it("keeps the student demo unavailable to recorded bundles", () => {
    const dataset = assignmentDemo();
    dataset.dataset.synthetic = false;
    render(<App dataset={dataset} />);
    expect(screen.queryByRole("navigation", { name: "Dashboard views" })?.textContent).not.toContain("Student study demo");
  });

  it("keeps question-linked edits, checks, errors, and tutor replies together without implying completion", () => {
    const session = studentStudyDemo().sessions[0];
    const questions = studyQuestions([session]);
    const q1 = questions.find(item => item.questionId === "Q1")!;
    expect(summarizeStudyQuestion(q1)).toMatchObject({ edits: 2, runs: 1, failed: 1, passed: 1, tutorReplies: 1, errors: ["TypeError"] });
    expect(questions.find(item => item.questionId === "Q2")!.events).toHaveLength(1);
    expect(questions.find(item => item.questionId === "Q3")!.events).toHaveLength(1);
  });

  it("does not attach unknown or conflicting question evidence based on timing", () => {
    const session = studentStudyDemo().sessions[0];
    const unknown = { ...session.timeline[0], id: "unknown", source_event_id: "source-unknown", metadata: [{ label: "Question", value: "Unknown" }] };
    const conflicting = { ...unknown, id: "duplicate", metadata: [{ label: "Question", value: "Q2" }] };
    const groups = studyQuestions([{ ...session, timeline: [unknown, conflicting], scope: "notebook_session" }]);
    expect(groups).toHaveLength(1);
    expect(groups[0].questionId).toBeNull();
    expect(groups[0].events).toHaveLength(1);
  });

  it("shows source evidence and the recorded error beside question checks", () => {
    render(<StudentStudy dataset={studentStudyDemo()} />);
    expect(screen.getByText("1 failed · 1 passed checks")).toBeInTheDocument();
    expect(screen.getByText(/Error names in output: TypeError/)).toBeInTheDocument();
    expect(screen.getByText("2 edit observations · 1 run · 1 tutor reply")).toBeInTheDocument();
    expect(screen.getByText(/A passed check does not confirm/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("View 7 source events"));
    fireEvent.click(screen.getByText("Cell executed"));
    expect(screen.getByText(/TypeError: cannot compare numbers/)).toBeInTheDocument();
    expect(screen.getByText(/Source event: source-study-run-error/)).toBeInTheDocument();
  });
});
