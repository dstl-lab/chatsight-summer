import { describe, expect, it } from "vitest";
import { demoDataset, filterTimeline, formatDuration, metricDuration, referenceLabel } from "./data";

describe("UI data helpers", () => {
  it("preserves unknown values rather than displaying zero", () => {
    const ambiguous = demoDataset.sessions.find((session) => session.question_id === "Q4.3")!;
    expect(metricDuration(ambiguous.active_time)).toBe("Unknown");
    expect(referenceLabel(
      ambiguous.reference_active_time.lower_seconds,
      ambiguous.reference_active_time.upper_seconds,
    )).toBe("Unknown");
  });

  it("formats elapsed values without changing their meaning", () => {
    expect(formatDuration(31)).toBe("31 sec");
    expect(formatDuration(87)).toBe("1m 27s");
    expect(formatDuration(null)).toBe("Unknown");
  });

  it("filters timeline event families", () => {
    const session = demoDataset.sessions[0];
    expect(filterTimeline(session.timeline, "conversation").every((event) =>
      ["student_message", "tutor_response"].includes(event.kind))).toBe(true);
    expect(filterTimeline(session.timeline, "checks").every((event) =>
      ["check_result", "question_status"].includes(event.kind))).toBe(true);
  });
});
