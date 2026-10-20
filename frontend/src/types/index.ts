export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

export interface DatasetStatusResponse {
  available: boolean;
  record_count: number;
  columns: string[];
  warnings: string[];
  file_path?: string;
}

export interface DocumentRecord {
  content_id: string;
  title: string;
  content_type: string;
  platform: string;
  author: string | null;
  created_date: string | null;
  last_updated: string | null;
  last_reviewed: string | null;
  page_views_90d: number | null;
  linked_from_count: number | null;
  mentions_deprecated_tool: boolean;
  has_broken_links: boolean;
  subject_area: string | null;
  staleness_score: number | null;
  recommended_action: string | null;
  raw_data?: Record<string, any>;
}

// Backward compatibility alias
export type ContentRecord = DocumentRecord;

export interface DatasetPreviewResponse {
  available: boolean;
  total_records: number;
  preview_count: number;
  columns: string[];
  preview: ContentRecord[];
  warnings: string[];
}

export interface DocumentListResponse {
  items: DocumentRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  available_platforms: string[];
  available_content_types: string[];
}

export interface DashboardSummaryResponse {
  total_documents: number;
  distinct_platforms: number;
  distinct_content_types: number;
  missing_update_dates: number;
  deprecated_references: number;
  broken_links: number;
  missing_metadata_count: number;
  platforms_list: string[];
  content_types_list: string[];
}

export interface DistributionItem {
  label: string;
  count: number;
  percentage: number;
}

export interface DashboardDistributionsResponse {
  by_platform: DistributionItem[];
  by_content_type: DistributionItem[];
  by_reference_score: DistributionItem[];
  by_recommended_action: DistributionItem[];
  by_signals: Record<string, number>;
}

export interface DocumentQueryParams {
  page?: number;
  page_size?: number;
  search?: string;
  platform?: string;
  content_type?: string;
  status?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// ---------------------------------------------------------
// Phase 3 Freshness Scoring & Audit Models
// ---------------------------------------------------------

export type SignalStatusType = 'evaluated' | 'unknown' | 'not_applicable' | 'failed';
export type RiskLevelType = 'Critical' | 'High' | 'Moderate' | 'Low' | 'Insufficient Evidence';

export interface SignalScoreDetail {
  signal_name: string;
  display_name: string;
  status: SignalStatusType;
  max_points: number;
  actual_points: number | null;
  evidence: string;
  explanation: string;
  evaluation_timestamp?: string;
}

export interface ScoredDocument {
  content_id: string;
  title: string;
  platform: string;
  content_type: string;
  subject_area?: string | null;
  author?: string | null;
  last_updated?: string | null;
  last_reviewed?: string | null;

  calculated_score: number | null;
  raw_score: number;
  earned_points: number;
  evaluated_max_points: number;
  evidence_coverage: number;
  is_provisional: boolean;
  score_status: string;
  risk_level: RiskLevelType;

  priority_rank: number;
  priority_label: string;
  priority_explanation: string;
  top_contributing_factors: string[];
  recommended_action: string;

  signal_breakdown: Record<string, SignalScoreDetail>;

  reference_staleness_score?: number | null;
  source_recommended_action?: string | null;
  raw_data?: Record<string, any>;
}

export interface AuditSummaryResponse {
  total_documents: number;
  scored_documents: number;
  provisional_scores_count: number;
  insufficient_evidence_count: number;
  risk_distribution: Record<string, number>;
  broken_link_documents: number;
  deprecated_tool_documents: number;
  unknown_signals_count: number;
  average_risk_score: number;
  last_audit_timestamp: string;
}

export interface AuditDocumentListResponse {
  items: ScoredDocument[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  available_risk_levels: string[];
}

export interface AuditRunResponse {
  status: string;
  documents_evaluated: number;
  timestamp: string;
  summary: AuditSummaryResponse;
}

export interface AuditQueryParams {
  page?: number;
  page_size?: number;
  search?: string;
  risk_level?: string;
  min_score?: number;
  max_score?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  evidence_status?: string;
}

// ---------------------------------------------------------
// Phase 4 Evidence Collection Models
// ---------------------------------------------------------

export type EvidenceStatusType = 'confirmed' | 'suspected' | 'unknown' | 'failed' | 'not_applicable';
export type EvidenceSeverityType = 'critical' | 'high' | 'moderate' | 'low' | 'info';
export type EvidenceSignalType =
  | 'document_age'
  | 'broken_links'
  | 'deprecated_tools'
  | 'metadata_quality'
  | 'url_verification'
  | 'contradictions';

export interface EvidenceItem {
  evidence_id: string;
  document_id: string;
  signal_type: EvidenceSignalType;
  status: EvidenceStatusType;
  severity: EvidenceSeverityType;
  summary: string;
  source_field: string;
  observed_value?: string | null;
  evidence_reference?: string | null;
  detected_at: string;
  tool_name: string;
  confidence: number;
  recommended_action: string;
}

export interface EvidenceAuditRequest {
  document_ids?: string[];
  max_documents?: number;
  enabled_checks?: string[];
  custom_urls?: Record<string, string>;
}

export interface EvidenceSummaryResponse {
  documents_inspected: number;
  checks_attempted: number;
  confirmed_findings: number;
  suspected_findings: number;
  unknown_signals: number;
  failed_checks: number;
  broken_link_findings: number;
  deprecated_reference_findings: number;
  metadata_quality_findings: number;
  audit_start_timestamp: string;
  audit_completed_timestamp: string;
}

export interface EvidenceDocumentResponse {
  document_id: string;
  title: string;
  evidence_count: number;
  evidence_items: EvidenceItem[];
}

export interface EvidenceFindingListResponse {
  items: EvidenceItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface EvidenceAuditRecord {
  audit_id: string;
  status: string;
  start_time: string;
  completion_time: string;
  document_ids: string[];
  checks_performed: string[];
  summary: EvidenceSummaryResponse;
  total_evidence_produced: number;
}

// ---------------------------------------------------------
// Phase 5 AI Contradiction Detection Models
// ---------------------------------------------------------

export type ContradictionRelationshipType =
  | 'contradiction'
  | 'supersession'
  | 'complementary'
  | 'scope_difference'
  | 'insufficient_evidence';

export type ContradictionSeverityType = 'critical' | 'high' | 'medium' | 'low';

export type RecencyAssessmentType =
  | 'newer_document_likely_authoritative'
  | 'older_document_explicitly_superseded'
  | 'authority_unclear'
  | 'dates_unavailable';

export type ContradictionReviewStatusType =
  | 'pending_review'
  | 'confirmed'
  | 'dismissed'
  | 'resolved';

export interface ContradictionFinding {
  contradiction_id: string;
  audit_id: string;
  document_a_id: string;
  document_b_id: string;
  document_a_title: string;
  document_b_title: string;
  claim_a: string;
  claim_b: string;
  relationship_type: ContradictionRelationshipType;
  explanation: string;
  supporting_excerpt_a: string;
  supporting_excerpt_b: string;
  source_location_a?: string | null;
  source_location_b?: string | null;
  severity: ContradictionSeverityType;
  confidence: number;
  recency_assessment: RecencyAssessmentType;
  recommended_action: string;
  status: ContradictionReviewStatusType;
  review_note?: string | null;
  reviewed_at?: string | null;
  reviewed_by?: string | null;
  detected_at: string;
  subject_area?: string | null;
  model_name?: string | null;
}

export interface ContradictionAuditRequest {
  document_ids?: string[];
  subject_area?: string;
  max_comparisons?: number;
  force_reanalysis?: boolean;
}

export interface ContradictionSummaryResponse {
  total_pairs_analyzed: number;
  total_findings: number;
  confirmed_contradictions: number;
  pending_review_findings: number;
  dismissed_findings: number;
  resolved_findings: number;
  findings_by_severity: Record<string, number>;
  documents_with_active_contradictions: number;
  analysis_failures: number;
  last_audit_timestamp?: string | null;
}

export interface ContradictionListResponse {
  items: ContradictionFinding[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ContradictionReviewRequest {
  status: ContradictionReviewStatusType;
  review_note?: string;
  reviewed_by?: string;
}

// ---------------------------------------------------------
// Phase 6 AI Remediation & Validation Models
// ---------------------------------------------------------

export type RemediationJobStatusType =
  | 'created'
  | 'planning'
  | 'drafting'
  | 'validating'
  | 'ready_for_review'
  | 'completed'
  | 'failed';

export type ValidationStatusType =
  | 'not_run'
  | 'passed'
  | 'passed_with_warnings'
  | 'failed'
  | 'needs_human_review';

export type RevisionReviewStatusType =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'changes_requested';

export interface ChangeRecord {
  change_id: string;
  original_text: string;
  proposed_text: string;
  change_type: string;
  reason: string;
  supporting_evidence_refs: string[];
  validation_outcome: string;
  requires_human_review: boolean;
}

export interface ValidationResult {
  validation_status: ValidationStatusType;
  supported_claims_count: number;
  unsupported_claim_findings: string[];
  remaining_contradiction_refs: string[];
  potentially_omitted_requirements: string[];
  evidence_coverage_percent: number;
  unresolved_questions: string[];
  validation_summary: string;
  validated_at: string;
  validation_timestamp?: string;
  validator_name: string;
}

export interface RemediationPlan {
  document_id: string;
  primary_objective: string;
  findings_to_address: string[];
  required_source_references: string[];
  proposed_changes_outline: string[];
  unresolved_questions: string[];
  has_sufficient_content: boolean;
  risk_assessment: string;
  created_at: string;
}

export interface DraftRevision {
  revision_id: string;
  remediation_id: string;
  document_id: string;
  revision_number: number;
  original_content: string;
  proposed_content: string;
  revision_summary: string;
  changes: ChangeRecord[];
  supporting_evidence_ids: string[];
  unresolved_questions: string[];
  validation_status: ValidationStatusType;
  validation_result?: ValidationResult;
  review_status: RevisionReviewStatusType;
  review_note?: string | null;
  reviewed_at?: string | null;
  reviewed_by?: string | null;
  created_at: string;
}

export interface RemediationJob {
  remediation_id: string;
  document_id: string;
  document_title: string;
  created_at: string;
  created_by: string;
  status: RemediationJobStatusType;
  original_content_reference: string;
  risk_score_at_creation?: number | null;
  source_evidence_ids: string[];
  source_contradiction_ids: string[];
  plan?: RemediationPlan;
  draft_revision_id?: string | null;
  current_revision_id?: string | null;
  draft_revisions: DraftRevision[];
  validation_result?: ValidationResult;
  error_summary?: string | null;
}

export interface CreateRemediationJobRequest {
  document_id: string;
  remediation_objective?: string;
  source_evidence_ids?: string[];
  source_contradiction_ids?: string[];
  focus_sections?: string;
}

export interface ReviewRevisionRequest {
  action: 'approve' | 'reject' | 'request_changes';
  review_note?: string;
  reviewer_name?: string;
}

export interface RegenerateRevisionRequest {
  feedback_notes: string;
  focus_areas?: string[];
}

export interface RemediationSummaryResponse {
  total_jobs: number;
  active_jobs: number;
  ready_for_review_jobs: number;
  approved_revisions: number;
  rejected_revisions: number;
  changes_requested_revisions: number;
  validation_outcomes: Record<string, number>;
  last_activity_timestamp?: string | null;
}

export interface RemediationJobListResponse {
  items: RemediationJob[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}



