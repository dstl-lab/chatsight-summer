import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Timeline } from "./components/Timeline";
import { InvestigationView } from "./components/InvestigationView";
import { parseBundle } from "./bundle";
import raw from "./findings-demo.synthetic.json";

const session = parseBundle(JSON.stringify(raw)).sessions[0];

describe("compact evidence review", () => {
  it("starts every event collapsed and keeps complete messages and code behind each row", () => {
    render(<Timeline events={session.timeline} highlightedRefs={new Set()} />);
    const rows = [...document.querySelectorAll<HTMLButtonElement>(".event-toggle")];
    expect(rows).toHaveLength(session.timeline.length);
    expect(rows.every(row => row.getAttribute("aria-expanded") === "false")).toBe(true);
    const message = session.timeline.find(event => event.kind === "tutor_response")!;
    fireEvent.click(document.getElementById(`ref-${message.id}`)!.querySelector("button")!);
    expect(document.getElementById(`details-${message.id}`)).toHaveTextContent(message.body);
    const code = session.timeline.find(event => event.code_diff?.after)!;
    fireEvent.click(document.getElementById(`ref-${code.id}`)!.querySelector("button")!);
    expect(document.getElementById(`details-${code.id}`)).toHaveTextContent(code.code_diff!.after!);
  });

  it("reveals filtered citations without opening every highlighted event", async () => {
    const { rerender } = render(<Timeline events={session.timeline} highlightedRefs={new Set()} />);
    fireEvent.click(screen.getByRole("button", { name: "Checks" }));
    const refs = new Set(session.analysis!.findings[0].highlight_ids);
    expect(refs.size).toBeGreaterThan(1);
    rerender(<Timeline events={session.timeline} highlightedRefs={refs} />);
    await waitFor(() => expect(screen.getByRole("button", { name: "All events" })).toHaveAttribute("aria-pressed", "true"));
    for (const ref of refs) {
      expect(document.getElementById(`ref-${ref}`)).toHaveClass("is-highlighted");
      expect(document.getElementById(`ref-${ref}`)!.querySelector("button")).toHaveAttribute("aria-expanded", "false");
    }
    const single = [...refs][0];
    rerender(<Timeline events={session.timeline} highlightedRefs={new Set([single])} />);
    await waitFor(() => expect(document.getElementById(`details-${single}`)).not.toBeNull());
  });

  it("puts interpretation limits beside the flag without duplicating the session summary or deciding the instructor review", () => {
    render(<InvestigationView session={session} onSaveReview={() => true} />);
    expect(screen.getByText("Possible interpretations, not confirmed tutor errors. You make the assessment.")).toBeVisible();
    const limit = document.querySelector(".flag-limit")!;
    expect(limit).toHaveTextContent(session.analysis!.findings[0].uncertainties[0]);
    expect(limit.closest("details")).toBeNull();
    expect(document.querySelector(".finding-detail")).not.toHaveAttribute("open");
    expect(document.querySelectorAll('input[type="radio"]:checked')).toHaveLength(0);
    fireEvent.click(screen.getByText("Full interpretation & evidence · flag 1"));
    for (const uncertainty of session.analysis!.findings[0].uncertainties) {
      expect(document.querySelector(".finding-detail")).toHaveTextContent(uncertainty);
    }
  });
});
