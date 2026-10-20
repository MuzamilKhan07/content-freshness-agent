import {
  HealthResponse,
  DatasetStatusResponse,
  DashboardSummaryResponse,
  DashboardDistributionsResponse,
  DocumentListResponse,
  DocumentRecord,
  DocumentQueryParams,
  AuditSummaryResponse,
  AuditDocumentListResponse,
  ScoredDocument,
  AuditRunResponse,
  AuditQueryParams,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchDatasetStatus(): Promise<DatasetStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/dataset/status`);
  if (!response.ok) {
    throw new Error(`Dataset status query failed: HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchDashboardSummary(): Promise<DashboardSummaryResponse> {
  const response = await fetch(`${API_BASE_URL}/dashboard/summary`);
  if (!response.ok) {
    throw new Error(`Dashboard summary query failed: HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchDashboardDistributions(): Promise<DashboardDistributionsResponse> {
  const response = await fetch(`${API_BASE_URL}/dashboard/distributions`);
  if (!response.ok) {
    throw new Error(`Dashboard distributions query failed: HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchDocuments(params: DocumentQueryParams = {}): Promise<DocumentListResponse> {
  const url = new URL(`${window.location.origin}${API_BASE_URL}/documents`);

  if (params.page !== undefined) url.searchParams.set('page', String(params.page));
  if (params.page_size !== undefined) url.searchParams.set('page_size', String(params.page_size));
  if (params.search && params.search.trim()) url.searchParams.set('search', params.search.trim());
  if (params.platform && params.platform !== 'all') url.searchParams.set('platform', params.platform);
  if (params.content_type && params.content_type !== 'all') url.searchParams.set('content_type', params.content_type);
  if (params.status && params.status !== 'all') url.searchParams.set('status', params.status);
  if (params.sort_by) url.searchParams.set('sort_by', params.sort_by);
  if (params.sort_order) url.searchParams.set('sort_order', params.sort_order);

  const response = await fetch(url.toString());
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch documents: HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchDocumentById(documentId: string): Promise<DocumentRecord> {
  const encodedId = encodeURIComponent(documentId.trim());
  const response = await fetch(`${API_BASE_URL}/documents/${encodedId}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Document ${documentId} not found (HTTP ${response.status})`);
  }
  return response.json();
}

// ---------------------------------------------------------
// Phase 3 Audit & Scoring Service Methods
// ---------------------------------------------------------

export async function fetchAuditSummary(): Promise<AuditSummaryResponse> {
  const response = await fetch(`${API_BASE_URL}/audit/summary`);
  if (!response.ok) {
    throw new Error(`Audit summary query failed: HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchAuditDocuments(params: AuditQueryParams = {}): Promise<AuditDocumentListResponse> {
  const url = new URL(`${window.location.origin}${API_BASE_URL}/audit/documents`);

  if (params.page !== undefined) url.searchParams.set('page', String(params.page));
  if (params.page_size !== undefined) url.searchParams.set('page_size', String(params.page_size));
  if (params.search && params.search.trim()) url.searchParams.set('search', params.search.trim());
  if (params.risk_level && params.risk_level !== 'all') url.searchParams.set('risk_level', params.risk_level);
  if (params.min_score !== undefined) url.searchParams.set('min_score', String(params.min_score));
  if (params.max_score !== undefined) url.searchParams.set('max_score', String(params.max_score));
  if (params.sort_by) url.searchParams.set('sort_by', params.sort_by);
  if (params.sort_order) url.searchParams.set('sort_order', params.sort_order);
  if (params.evidence_status && params.evidence_status !== 'all') url.searchParams.set('evidence_status', params.evidence_status);

  const response = await fetch(url.toString());
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch audit documents: HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchAuditDocumentDetail(documentId: string): Promise<ScoredDocument> {
  const encodedId = encodeURIComponent(documentId.trim());
  const response = await fetch(`${API_BASE_URL}/audit/documents/${encodedId}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Document ${documentId} scoring explanation not found (HTTP ${response.status})`);
  }
  return response.json();
}

export async function triggerAuditRun(): Promise<AuditRunResponse> {
  const response = await fetch(`${API_BASE_URL}/audit/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to execute audit run: HTTP ${response.status}`);
  }
  return response.json();
}
