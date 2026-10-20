import { HealthResponse, DatasetStatusResponse, DatasetPreviewResponse } from '../types';

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

export async function fetchDatasetPreview(limit: number = 10): Promise<DatasetPreviewResponse> {
  const response = await fetch(`${API_BASE_URL}/dataset/preview?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Dataset preview query failed: HTTP ${response.status}`);
  }
  return response.json();
}
