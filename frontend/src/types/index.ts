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

// Backward compatibility alias for Phase 1 components
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
