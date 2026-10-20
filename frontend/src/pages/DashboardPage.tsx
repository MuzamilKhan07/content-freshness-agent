import React, { useEffect, useState, useCallback } from 'react';
import { Header } from '../components/Header';
import { MetricsOverview } from '../components/MetricsOverview';
import { DatasetPreviewTable } from '../components/DatasetPreviewTable';
import { DatasetWarnings } from '../components/DatasetWarnings';
import { fetchHealth, fetchDatasetStatus, fetchDatasetPreview } from '../services/api';
import { HealthResponse, DatasetStatusResponse, DatasetPreviewResponse } from '../types';

export const DashboardPage: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [status, setStatus] = useState<DatasetStatusResponse | null>(null);
  const [preview, setPreview] = useState<DatasetPreviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string>('');

  const loadData = useCallback(async (isManualRefresh = false) => {
    if (isManualRefresh) {
      setIsRefreshing(true);
    } else {
      setLoading(true);
    }
    setErrorMessage(null);

    try {
      // 1. Health check
      const healthData = await fetchHealth();
      setHealth(healthData);
      setBackendOnline(true);
      setLastChecked(new Date().toLocaleTimeString());

      // 2. Dataset Status
      const statusData = await fetchDatasetStatus();
      setStatus(statusData);

      // 3. Dataset Preview
      const previewData = await fetchDatasetPreview(10);
      setPreview(previewData);
    } catch (err: any) {
      console.error('Error fetching FreshGuard data:', err);
      setBackendOnline(false);
      setErrorMessage(
        err.message || 'Unable to connect to FreshGuard AI backend service. Please ensure the backend is running.'
      );
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData(false);
  }, [loadData]);

  const allWarnings = [
    ...(status?.warnings || []),
    ...(preview?.warnings || []),
  ].filter((v, i, a) => a.indexOf(v) === i); // Deduplicate

  return (
    <div className="app-container">
      <Header
        backendOnline={backendOnline}
        isRefreshing={isRefreshing}
        onRefresh={() => loadData(true)}
        lastChecked={lastChecked}
      />

      <main>
        <MetricsOverview
          datasetStatus={status}
          health={health}
          loading={loading && !status}
        />

        {allWarnings.length > 0 && (
          <DatasetWarnings
            warnings={allWarnings}
            isError={!status?.available}
          />
        )}

        <DatasetPreviewTable
          records={preview?.preview || []}
          columns={preview?.columns || status?.columns || []}
          totalRecords={preview?.total_records || status?.record_count || 0}
          loading={loading}
          error={errorMessage}
          datasetAvailable={status?.available ?? false}
        />
      </main>

      <footer className="app-footer">
        <div>
          <span>FreshGuard AI System &bull; Phase 1 Project Foundation</span>
        </div>
        <div>
          <span>Antigravity Environment &bull; Enterprise Content Freshness</span>
        </div>
      </footer>
    </div>
  );
};
