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
