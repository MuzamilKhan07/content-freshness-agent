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

export interface ContentRecord {
  content_id?: string;
  title?: string;
  content_type?: string;
  platform?: string;
  author?: string;
  created_date?: string;
  last_updated?: string;
  last_reviewed?: string;
  page_views_90d?: string | number;
  linked_from_count?: string | number;
  mentions_deprecated_tool?: string | boolean;
  has_broken_links?: string | boolean;
  subject_area?: string;
  staleness_score?: string | number;
  recommended_action?: string;
  [key: string]: any;
}

export interface DatasetPreviewResponse {
  available: boolean;
  total_records: number;
  preview_count: number;
  columns: string[];
  preview: ContentRecord[];
  warnings: string[];
}
