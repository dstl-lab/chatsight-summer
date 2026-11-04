import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Timeline } from "./components/Timeline";
import { compactTimeline } from "./timeline-compaction";
import type { TimelineEvent, TimelineKind } from "./types";

function event(
  id: string,
  kind: TimelineKind,
  occurredAt: string,
  metadata: { label: string; value: string }[] = [],
  extra: Partial<TimelineEvent> = {},
): TimelineEvent {
  const titles: Partial<Record<TimelineKind, string>> = {
    code_edit: "Code edited",
    execution: "Cell executed",
    check_result: "Check failed",
    student_message: "Student message",
    tutor_response: "Tutor response",
  };
  return {
    id,
    source_event_id: `source-${id}`,
    kind,
    actor: kind === "check_result" ? "Autograder" : kind === "student_message" ? "Student" : "Notebook",
    title: titles[kind] ?? "Activity",
    body: `${id} full evidence`,
    occurred_at: occurredAt,
    phase: "after_help",
    order_uncertain: false,
    source_pointers: [`line:${id}`],
    code_diff: kind === "code_edit" ? { before: "x = 0", after: "x = 1" } : null,
    metadata,
    ...extra,
  };
}

const burst = [
  event("edit-1", "code_edit", "2026-10-30T12:00:00.100Z", [
    { label: "Cell", value: "cell-1" },
    { label: "Revision", value: "revision-2" },
  ]),
  event("run-1", "execution", "2026-10-30T12:00:00.350Z", [
    { label: "Cell", value: "cell-1" },
    { label: "Revision", value: "revision-2" },
    { label: "Execution", value: "execution-1" },
  ]),
  event("check-1", "check_result", "2026-10-30T12:00:00.800Z", [
    { label: "Execution", value: "execution-1" },
    { label: "Check", value: "check-1" },
  ]),
];

describe("timeline action compaction", () => {
  it("groups a linked same-second edit, execution, and check without changing raw events", () => {
    const original = structuredClone(burst);
    const actions = compactTimeline(burst);

    expect(actions).toHaveLength(1);
    expect(actions[0].events.map((item) => item.id)).toEqual(["edit-1", "run-1", "check-1"]);
    expect(actions[0].summary).toBe("Edited code, ran a cell, and a check failed");
    expect(burst).toEqual(original);
  });

  it("keeps unrelated cells, conversation boundaries, phases, and later seconds separate", () => {
    const actions = compactTimeline([
      ...burst.slice(0, 2),
      event("other-cell", "code_edit", "2026-10-30T12:00:00.500Z", [{ label: "Cell", value: "cell-2" }]),
      event("message", "student_message", "2026-10-30T12:00:00.600Z"),
      event("later", "execution", "2026-10-30T12:00:01.050Z", [{ label: "Execution", value: "execution-2" }]),
      event("other-phase", "execution", "2026-10-30T12:00:01.100Z", [{ label: "Execution", value: "execution-2" }], { phase: "before_help" }),
    ]);

    expect(actions.map((action) => action.events.map((item) => item.id))).toEqual([
      ["edit-1", "run-1"],
      ["other-cell"],
      ["message"],
      ["later"],
      ["other-phase"],
    ]);
  });

  it("groups identifier-free edit bursts conservatively and preserves uncertainty", () => {
    const actions = compactTimeline([
      event("edit-a", "code_edit", "2026-10-30T12:00:00Z", [], { order_uncertain: true, phase: "ambiguous" }),
      event("edit-b", "code_edit", "2026-10-30T12:00:00Z", [], { order_uncertain: true, phase: "ambiguous" }),
      event("unlinked-check", "check_result", "2026-10-30T12:00:00Z", [], { order_uncertain: true, phase: "ambiguous" }),
    ]);

    expect(actions).toHaveLength(2);
    expect(actions[0].events.map((item) => item.id)).toEqual(["edit-a", "edit-b"]);
    expect(actions[0].order_uncertain).toBe(true);
    expect(actions[1].events[0].id).toBe("unlinked-check");
  });

  it("renders one action row while retaining expandable and citable raw evidence", () => {
    render(<Timeline events={burst} highlightedRefs={new Set(["check-1"])} />);

    expect(screen.getByText("1 actions from 3 events · Click a row for full evidence.")).toBeVisible();
    const toggle = screen.getByRole("button", { name: /Compacted notebook action/ });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Grouped for display only. All 3 source events remain available below.")).toBeVisible();
    expect(document.getElementById("ref-check-1")?.closest("article")).toHaveClass("is-highlighted");

    const rawEdit = screen.getByText("Code edited", { selector: "strong" }).closest("details")!;
    fireEvent.click(rawEdit.querySelector("summary")!);
    expect(rawEdit).toHaveTextContent("edit-1 full evidence");
    expect(rawEdit).toHaveTextContent("x = 1");
  });
});
