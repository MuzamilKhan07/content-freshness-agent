import React from 'react';
import { Database, FileText, Columns, Activity } from 'lucide-react';
import { DatasetStatusResponse, HealthResponse } from '../types';

interface MetricsOverviewProps {
  datasetStatus: DatasetStatusResponse | null;
  health: HealthResponse | null;
  loading: boolean;
}

export const MetricsOverview: React.FC<MetricsOverviewProps> = ({
  datasetStatus,
  health,
  loading,
}) => {
  const isAvailable = datasetStatus?.available ?? false;
  const recordCount = datasetStatus?.record_count ?? 0;
  const columnCount = datasetStatus?.columns?.length ?? 0;

  return (
    <div className="metrics-grid">
      {/* Metric 1: Dataset Status */}
      <div className={`metric-card ${isAvailable ? 'accent-green' : 'accent-amber'}`} id="metric-dataset-status">
        <div className="metric-header">
          <span className="metric-title">Dataset Status</span>
          <div className="metric-icon-box">
            <Database size={18} />
          </div>
        </div>
        <div className="metric-value">
          {loading ? (
            <span className="text-dim">...</span>
          ) : isAvailable ? (
            <span style={{ color: 'var(--emerald-400)' }}>Available</span>
          ) : (
            <span style={{ color: 'var(--rose-500)' }}>Unavailable</span>
          )}
        </div>
        <div className="metric-subtext">
          {datasetStatus?.file_path ? `Source: ${datasetStatus.file_path}` : 'ps11_content_inventory.csv'}
        </div>
      </div>

      {/* Metric 2: Indexed Records */}
      <div className="metric-card accent-blue" id="metric-record-count">
        <div className="metric-header">
          <span className="metric-title">Indexed Records</span>
          <div className="metric-icon-box">
            <FileText size={18} />
          </div>
        </div>
        <div className="metric-value">
          {loading ? (
            <span className="text-dim">...</span>
          ) : (
            <span>{recordCount.toLocaleString()}</span>
          )}
        </div>
        <div className="metric-subtext">Total knowledge base documents</div>
      </div>

      {/* Metric 3: Available Columns */}
      <div className="metric-card accent-indigo" id="metric-column-count">
        <div className="metric-header">
          <span className="metric-title">Schema Columns</span>
          <div className="metric-icon-box">
            <Columns size={18} />
          </div>
        </div>
        <div className="metric-value">
          {loading ? (
            <span className="text-dim">...</span>
          ) : (
            <span>{columnCount}</span>
          )}
        </div>
        <div className="metric-subtext">Metadata & freshness signals</div>
      </div>

      {/* Metric 4: API Service State */}
      <div className="metric-card accent-green" id="metric-api-status">
        <div className="metric-header">
          <span className="metric-title">Backend Service</span>
          <div className="metric-icon-box">
            <Activity size={18} />
          </div>
        </div>
        <div className="metric-value">
          {health?.status ? (
            <span style={{ textTransform: 'capitalize' }}>{health.status}</span>
          ) : (
            <span className="text-dim">Standby</span>
          )}
        </div>
        <div className="metric-subtext">FastAPI v{health?.version || '0.1.0'} & OpenAI Ready</div>
      </div>
    </div>
  );
};
