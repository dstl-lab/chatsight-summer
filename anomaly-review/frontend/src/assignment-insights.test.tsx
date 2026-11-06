import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { assignmentDemo } from "./assignment-demo";
import { collectQuestions, conceptGroups, distinctStudents, functionGroups, functionMentions, topicGroups } from "./assignment-insights";
import { AssignmentInsights } from "./components/AssignmentInsights";
import { App } from "./App";

describe("assignment question insights", () => {
  it("deduplicates overlapping source events and does not infer contradictory identities or assignments", () => {
    const dataset = assignmentDemo();
    const first = dataset.sessions[0];
    const duplicate = { ...first, id: "another-window", student_id: "STU-999", assignment_id: "different lab" };
    const questions = collectQuestions([first, duplicate]);
    expect(questions).toHaveLength(1);
    expect(questions[0].assignmentId).toBeNull();
    expect(questions[0].studentId).toBeNull();
    expect(distinctStudents(questions)).toEqual({ count: 0, missing: 1 });
  });

  it("groups literal matches with evidence and counts distinct students", () => {
    const dataset = assignmentDemo();
    const messages = collectQuestions(dataset.sessions);
    expect(messages).toHaveLength(5);
    const groups = topicGroups(messages);
    const dataframe = groups.find(group => group.id === "dataframes")!;
    expect(dataframe.messages).toHaveLength(2);
    expect(distinctStudents(dataframe.messages)).toEqual({ count: 2, missing: 0 });
    expect(groups.find(group => group.id === "errors")!.messages).toHaveLength(2);
  });

  it("finds explicit function calls and concept phrases, with one count per message", () => {
    const messages = collectQuestions(assignmentDemo().sessions);
    const get = functionGroups(messages).find(group => group.label === ".get()")!;
    expect(get.messages).toHaveLength(2);
    expect(get.evidence(get.messages[0])).toBe("df.get");
    expect(conceptGroups(messages).find(group => group.label === "Grouping and aggregation")!.messages).toHaveLength(1);
    expect(functionMentions("df.get('a') and df.get('b'), np.mean(x), if (x), and get help")).toEqual([
      { label: ".get()", matched: "df.get" }, { label: "np.mean()", matched: "np.mean" },
    ]);
    expect(functionMentions("I cannot get the right result")).toEqual([]);
    expect(functionMentions("What does .get() do?")).toEqual([{ label: ".get()", matched: ".get" }]);
  });

  it("shows matched function evidence and opens the original message", () => {
    const onInspect = vi.fn();
    render(<AssignmentInsights dataset={assignmentDemo()} onInspect={onInspect} />);
    fireEvent.click(screen.getByRole("button", { name: /\.get\(\)/ }));
    expect(screen.getByRole("heading", { name: ".get()" })).toBeInTheDocument();
    expect(screen.getByText("df.get", { selector: "code" })).toBeInTheDocument();
    expect(screen.getByText("table.get", { selector: "code" })).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "View conversation" })[0]);
    expect(onInspect).toHaveBeenCalledWith("assignment-example-0", "example-message-0");
  });

  it("filters questions and opens the original conversation evidence", () => {
    const onInspect = vi.fn();
    render(<AssignmentInsights dataset={assignmentDemo()} onInspect={onInspect} />);
    fireEvent.click(screen.getByRole("button", { name: /DataFrames and tables/ }));
    expect(screen.getByText(/filter return an empty table/)).toBeInTheDocument();
    expect(screen.queryByText(/index out of bounds/)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Search student messages"), { target: { value: "filter" } });
    fireEvent.click(screen.getByRole("button", { name: "View conversation" }));
    expect(onInspect).toHaveBeenCalledWith("assignment-example-0", "example-message-0");
  });

  it("opens an evidence message in the session timeline from the insights view", () => {
    Element.prototype.scrollIntoView = vi.fn();
    render(<App dataset={assignmentDemo()} />);
    fireEvent.click(screen.getByRole("button", { name: "Assignment insights" }));
    fireEvent.click(screen.getAllByRole("button", { name: "View conversation" })[0]);
    expect(screen.getByRole("button", { name: /Student Student message.*DataFrame filter/ })).toHaveAttribute("aria-expanded", "true");
  });
});
