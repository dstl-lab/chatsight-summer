import { Flag, ListChecks, ScanSearch } from "lucide-react";
import type { DemoDataset } from "../types";

interface SummaryBarProps {
  summary: DemoDataset["summary"];
  reviewed: number;
}

const items = [
  { key: "total_sessions", label: "Total Sessions", icon: ScanSearch, tone: "neutral" },
  { key: "flagged_sessions", label: "Flagged Sessions", icon: Flag, tone: "flag" },
] as const;

export function SummaryBar({ summary, reviewed }: SummaryBarProps) {
  return (
    <section className="summary-grid" aria-label="Dataset summary">
      {items.map(({ key, label, icon: Icon, tone }) => (
        <div className={`summary-cell summary-cell--${tone}`} key={key}>
          <div className="summary-icon" aria-hidden="true"><Icon size={16} /></div>
          <div>
            <div className="summary-value">{summary[key]}</div>
            <div className="summary-label">{label}</div>
          </div>
        </div>
      ))}
      <div className="summary-cell summary-cell--reviewed">
        <div className="summary-icon" aria-hidden="true"><ListChecks size={16} /></div>
        <div>
          <div className="summary-value">{reviewed}</div>
          <div className="summary-label">Reviewed Sessions</div>
        </div>
      </div>
    </section>
  );
}
