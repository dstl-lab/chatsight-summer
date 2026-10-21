export type MetricStatus = "known" | "unknown";
export type Priority = "high" | "medium" | "low" | "none" | "insufficient_data" | "routine";
export type ReviewClassification = "tutor_issue" | "student_struggle" | "insufficient" | "";

export interface Metric<T = number> {
  status: MetricStatus;
  value: T | null;
  reason: string | null;
  evidence_refs: string[];
}

export interface ReferenceTime {
  status: "illustrative" | "calculated" | "unknown";
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
  | "inactivity"
  | "notebook_snapshot"
  | "code_capture";

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
  priority: Priority | null;
  priority_basis: string;
  scenario: string;
  synthetic: boolean;
  student_id: string;
  question_id: string | null;
  assignment_id: string | null;
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
  scope?: "conversation" | "question_episode" | "notebook_session";
  analysis?: Analysis;
  fusion?: CombinedPriority | null;
}

export interface DemoDataset {
  contract_version: number;
  dataset: {
    id: string;
    synthetic: boolean;
    label: string;
    notice: string;
    priority_method: string;
    input_sha256?: string;
    prompt_sha256?: string;
    analysis_version?: string;
    model?: string | null;
  };
  summary: {
    total_sessions: number;
    flagged_sessions: number;
    high_priority_sessions: number;
    medium_priority_sessions?: number;
    low_priority_sessions?: number;
    no_priority_sessions?: number;
    insufficient_data_sessions?: number;
  };
  sessions: DemoSession[];
}

export interface ReviewRecord {
  classification: ReviewClassification;
  notes: string;
  savedAt: string | null;
}

export type AnalysisDecision = "surface" | "no_supported_finding" | "insufficient_evidence";
export interface Finding {
  category: "persistent_difficulty" | "request_mismatch" | "advice_linked_obstacle";
  explanation: string;
  interpretations: { statement: string; evidence_ids: string[] }[];
  facts: { kind: string; record_id: string; related_id?: string | null; result?: string | null }[];
  highlight_ids: string[];
  recovery_evidence_ids: string[];
  uncertainties: string[];
}
export interface Analysis {
  state: "not_analyzed" | "completed" | "failed" | "rejected";
  decision: AnalysisDecision | null;
  summary: string;
  findings: Finding[];
  validation_errors: string[];
  notices: string[];
  model: string | null;
  source: string;
  semantic_interpretations_verified: false;
}

export type MetricSignalStatus = "strong_outlier" | "moderate_outlier" | "no_outlier" | "insufficient_data";
export interface MetricSignal {
  status: MetricSignalStatus;
  episode_id: string | null;
  score: number | null;
  above_threshold_metrics: string[];
  reasons: string[];
  evidence_refs: string[];
  source_event_ids: string[];
  data_limitations: string[];
}
export interface LlmSignal {
  status: "supported_finding" | "no_supported_finding" | "insufficient_evidence" | "not_analyzed";
  model: string | null;
  finding_categories: string[];
  evidence_refs: string[];
  source_event_ids: string[];
  data_limitations: string[];
}
export interface CombinedPriority {
  status: "scored" | "insufficient_data";
  priority: "high" | "medium" | "low" | "none" | "insufficient_data";
  rule: string;
  summary: string;
  metric_signal: MetricSignal;
  llm_signal: LlmSignal;
  shared_evidence_refs: string[];
  shared_source_event_ids: string[];
  config: {
    strong_composite_score: number;
    strong_single_tail_score: number;
    strong_contribution_count: number;
  };
  interpretation: string;
}
