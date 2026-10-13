export type MetricStatus = "known" | "unknown";
export type Priority = "high" | "medium" | "routine";
export type ReviewClassification = "tutor_issue" | "student_struggle" | "insufficient" | "";

export interface Metric<T = number> {
  status: MetricStatus;
  value: T | null;
  reason: string | null;
  evidence_refs: string[];
}

export interface ReferenceTime {
  status: "illustrative" | "unknown";
  lower_seconds: number | null;
  upper_seconds: number | null;
  basis: string;
}

export interface FlagReason {
  id: string;
  title: string;
  description: string;
  supporting_refs: string[];
  supporting_event_ids: string[];
}

export interface TimelineMetadata {
  label: string;
  value: string;
}

export interface CodeDiff {
  before: string | null;
  after: string | null;
}

export type TimelineKind =
  | "student_message"
  | "tutor_response"
  | "code_edit"
  | "execution"
  | "check_result"
  | "question_status"
  | "activity"
  | "inactivity";

export interface TimelineEvent {
  id: string;
  source_event_id: string | null;
  kind: TimelineKind;
  actor: string;
  title: string;
  body: string;
  occurred_at: string;
  duration_seconds?: number;
  phase: "before_help" | "help_boundary" | "after_help" | "ambiguous" | "unpartitioned";
  order_uncertain: boolean;
  source_pointers: string[];
  supporting_refs?: string[];
  code_diff: CodeDiff | null;
  metadata: TimelineMetadata[];
}

export interface DemoSession {
  id: string;
  review_rank: number;
  flagged: boolean;
  priority: Priority;
  priority_basis: string;
  scenario: string;
  synthetic: true;
  student_id: string;
  question_id: string;
  assignment_id: string;
  outcome: Metric<string>;
  active_time: Metric;
  post_help_active_time: Metric;
  elapsed_time: Metric;
  reference_active_time: ReferenceTime;
  failed_checks_after_help: Metric;
  tutor_requests: Metric;
  completed_tutor_responses: Metric;
  repeated_failures: Metric;
  continued_after_help: Metric<boolean>;
  resumed_after_help: Metric<boolean>;
  reasons: FlagReason[];
  timeline: TimelineEvent[];
  source_event_refs: string[];
  quality_warnings: string[];
}

export interface DemoDataset {
  contract_version: number;
  dataset: {
    id: string;
    synthetic: true;
    label: string;
    notice: string;
    priority_method: string;
  };
  summary: {
    total_sessions: number;
    flagged_sessions: number;
    high_priority_sessions: number;
  };
  sessions: DemoSession[];
}

export interface ReviewRecord {
  classification: ReviewClassification;
  notes: string;
  savedAt: string | null;
}
