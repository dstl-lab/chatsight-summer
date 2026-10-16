import Ajv from "ajv";
import addFormats from "ajv-formats";
import schema from "./review-schema.json";
import type { DemoDataset, DemoSession, ReviewRecord } from "./types";

const ajv = new Ajv({ strict: false, allErrors: false });
addFormats(ajv);
const validShape = ajv.compile<DemoDataset>(schema);

export function parseBundle(text: string): DemoDataset {
  const value: unknown = JSON.parse(text);
  if (!validShape(value)) throw new Error("Unsupported or invalid review bundle. Export contract version 2 with session-findings.");
  const dataset = value;
  if (dataset.sessions.length > 1000) throw new Error("Bundle exceeds the 1,000-session browser limit.");
  const sessions = new Set<string>();
  for (const session of dataset.sessions) {
    if (sessions.has(session.id)) throw new Error("Duplicate session identity.");
    sessions.add(session.id);
    if (session.synthetic !== dataset.dataset.synthetic) throw new Error("Mixed dataset origins are not supported.");
    const refs = new Set(session.timeline.map(event => event.id));
    if (refs.size !== session.timeline.length) throw new Error("Duplicate timeline identity.");
    if (session.timeline.some(event => !Number.isFinite(Date.parse(event.occurred_at)) || !/(Z|[+-]\d\d:\d\d)$/.test(event.occurred_at))) throw new Error("Invalid or timezone-free timeline timestamp.");
    const analysis = session.analysis!;
    if (analysis.state !== "completed" && analysis.findings.length) throw new Error("Unaccepted findings cannot be displayed.");
    if (analysis.state === "not_analyzed" && analysis.decision !== null) throw new Error("Unanalyzed session has a decision.");
    if (["failed", "rejected"].includes(analysis.state) && analysis.decision !== "insufficient_evidence") throw new Error("Failed analysis has an unsafe decision.");
    if (analysis.state === "completed" && (analysis.decision === null || (analysis.decision === "surface") !== !!analysis.findings.length)) throw new Error("Decision and findings disagree.");
    if (session.flagged !== (analysis.state === "completed" && analysis.decision === "surface")) throw new Error("Flag does not match validated analysis.");
    const cited = [...session.source_event_refs, ...session.reasons.flatMap(reason => reason.supporting_refs),
      ...analysis.findings.flatMap(finding => [...finding.highlight_ids, ...finding.recovery_evidence_ids,
        ...finding.interpretations.flatMap(item => item.evidence_ids),
        ...finding.facts.flatMap(fact => fact.related_id ? [fact.record_id, fact.related_id] : [fact.record_id])])];
    for (const finding of analysis.findings) {
      const highlights = new Set([...finding.highlight_ids, ...finding.recovery_evidence_ids]);
      if (finding.interpretations.some(item => item.evidence_ids.some(ref => !highlights.has(ref)))) throw new Error("Interpretation evidence is not highlighted or recovery evidence.");
    }
    if (cited.some(ref => !refs.has(ref))) throw new Error("Finding cites an event missing from the timeline.");
    for (const metric of [session.outcome, session.active_time, session.post_help_active_time,
      session.elapsed_time, session.failed_checks_after_help, session.tutor_requests,
      session.completed_tutor_responses, session.repeated_failures, session.continued_after_help, session.resumed_after_help]) {
      if ((metric.status === "unknown") !== (metric.value === null) || metric.evidence_refs.some(ref => !refs.has(ref))) throw new Error("Invalid metric or metric evidence.");
    }
  }
  if (dataset.summary.total_sessions !== dataset.sessions.length ||
      dataset.summary.flagged_sessions !== dataset.sessions.filter(session => session.flagged).length ||
      dataset.summary.high_priority_sessions !== dataset.sessions.filter(session => session.priority === "high").length) throw new Error("Summary counts disagree with data.");
  return dataset;
}

export function decisionLabel(session: DemoSession): string {
  if (!session.analysis) return session.flagged ? "Illustratively flagged" : "Demo reference";
  if (session.analysis.state === "not_analyzed") return "Not analyzed";
  if (session.analysis.state === "rejected") return "Insufficient evidence · rejected";
  if (session.analysis.state === "failed") return "Insufficient evidence · failed";
  return ({ surface: "Flag for review", no_supported_finding: "No supported finding", insufficient_evidence: "Insufficient evidence" })[session.analysis.decision ?? "insufficient_evidence"];
}

export function reviewStorageKey(dataset: DemoDataset): string {
  return `anomaly-review-instructor-reviews-v2:${dataset.dataset.id}:${dataset.dataset.input_sha256 ?? "authored-demo"}`;
}

export function validateReviews(value: unknown, dataset: DemoDataset): Record<string, ReviewRecord> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid reviews.");
  const allowed = new Set(dataset.sessions.map(session => session.id));
  const result: Record<string, ReviewRecord> = {};
  for (const [id, review] of Object.entries(value)) {
    if (!allowed.has(id) || !review || typeof review !== "object" ||
        !["tutor_issue", "student_struggle", "insufficient"].includes(review.classification) ||
        typeof review.notes !== "string" || review.notes.length > 50000 ||
        !(review.savedAt === null || (typeof review.savedAt === "string" && Number.isFinite(Date.parse(review.savedAt))))) throw new Error("Review does not match this dataset or has invalid fields.");
    result[id] = { classification: review.classification, notes: review.notes, savedAt: review.savedAt };
  }
  return result;
}

export async function readLocalFile(file: File): Promise<string> {
  if (file.size > 25 * 1024 * 1024) throw new Error("Use an exported review bundle under 25 MB, not the full historical ZIP.");
  if (file.text) return file.text();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Could not read local file."));
    reader.readAsText(file);
  });
}

export function downloadReviews(dataset: DemoDataset, reviews: Record<string, ReviewRecord>) {
  const blob = new Blob([JSON.stringify({ version: 1, dataset_key: reviewStorageKey(dataset), reviews }, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "session-reviews.private.json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
