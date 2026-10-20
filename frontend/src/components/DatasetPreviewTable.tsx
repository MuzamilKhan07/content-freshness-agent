import React from 'react';
import { Table, AlertCircle, FileQuestion } from 'lucide-react';
import { ContentRecord } from '../types';

interface DatasetPreviewTableProps {
  records: ContentRecord[];
  columns: string[];
  totalRecords: number;
  loading: boolean;
  error: string | null;
  datasetAvailable: boolean;
}

export const DatasetPreviewTable: React.FC<DatasetPreviewTableProps> = ({
  records,
  columns: _columns,
  totalRecords,
  loading,
  error,
  datasetAvailable,
}) => {
  // Helper to render action badges
  const renderActionBadge = (action?: string | null) => {
    if (!action) return <span className="text-dim">-</span>;
    const lower = action.toLowerCase();
    if (lower.includes('update')) {
      return <span className="badge badge-action-update">{action}</span>;
    }
    if (lower.includes('rewrite')) {
      return <span className="badge badge-action-rewrite">{action}</span>;
    }
    if (lower.includes('archive')) {
      return <span className="badge badge-action-archive">{action}</span>;
    }
    return <span className="badge badge-action-ok">{action}</span>;
  };

  // Helper to render boolean flags
  const renderBooleanFlag = (val?: string | boolean | null) => {
    if (val === undefined || val === null || val === '') return <span className="text-dim">-</span>;
    const isTrue = val === true || String(val).toLowerCase() === 'true';
    return isTrue ? (
      <span className="flag-yes" title="Signal flagged">Yes</span>
    ) : (
      <span className="flag-no">No</span>
    );
  };

  // Helper to render staleness score
  const renderStalenessScore = (score?: string | number | null) => {
    if (score === undefined || score === null || score === '') {
      return <span className="text-dim">-</span>;
    }
    const num = parseFloat(String(score));
    if (isNaN(num)) return <span>{score}</span>;

    let color = 'var(--emerald-400)';
    if (num > 0.6) color = 'var(--rose-500)';
    else if (num > 0.3) color = 'var(--amber-500)';

    return (
      <span className="mono" style={{ fontWeight: 600, color }}>
        {num.toFixed(2)}
      </span>
    );
  };

  return (
    <div className="content-box" id="dataset-preview-container">
      <div className="content-box-header">
        <div>
          <h2 className="content-box-title">
            <Table size={20} color="var(--emerald-400)" />
            Dataset Sample Preview
          </h2>
          <p className="content-box-subtitle">
            Showing first {records.length} of {totalRecords} records from knowledge inventory
          </p>
        </div>
        <div className="preview-badge mono">
          Previewing 10 Records Max
        </div>
      </div>

      {loading ? (
        <div className="state-container">
          <div className="pulse-dot" style={{ width: 24, height: 24, marginBottom: 12 }} />
          <h3 className="state-title">Loading Knowledge Inventory...</h3>
          <p className="state-desc">Retrieving records and inspecting freshness signals.</p>
        </div>
      ) : error ? (
        <div className="state-container">
          <AlertCircle size={36} className="state-icon" color="var(--rose-500)" />
          <h3 className="state-title">Failed to Load Dataset</h3>
          <p className="state-desc">{error}</p>
        </div>
      ) : !datasetAvailable ? (
        <div className="state-container">
          <FileQuestion size={40} className="state-icon" />
          <h3 className="state-title">Dataset File Not Available</h3>
          <p className="state-desc">
            Place <code>ps11_content_inventory.csv</code> in the <code>data/</code> folder and click Sync Data.
          </p>
        </div>
      ) : records.length === 0 ? (
        <div className="state-container">
          <FileQuestion size={36} className="state-icon" />
          <h3 className="state-title">No Records Found</h3>
          <p className="state-desc">The dataset file exists but contains zero data rows.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="data-table" id="dataset-table">
            <thead>
              <tr>
                <th>Content ID</th>
                <th>Title</th>
                <th>Type</th>
                <th>Platform</th>
                <th>Subject Area</th>
                <th>Last Updated</th>
                <th>Last Reviewed</th>
                <th>Deprecated Tool?</th>
                <th>Broken Links?</th>
                <th>Staleness Ref</th>
                <th>Recommended Action</th>
              </tr>
            </thead>
            <tbody>
              {records.map((row, idx) => (
                <tr key={row.content_id || idx}>
                  <td>
                    <span className="badge badge-id">{row.content_id || `ROW-${idx + 1}`}</span>
                  </td>
                  <td style={{ fontWeight: 500, maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {row.title || 'Untitled Document'}
                  </td>
                  <td>
                    <span style={{ color: 'var(--text-muted)' }}>{row.content_type || '-'}</span>
                  </td>
                  <td>
                    <span className="badge badge-platform">{row.platform || '-'}</span>
                  </td>
                  <td>
                    <span style={{ color: '#cbd5e1' }}>{row.subject_area || '-'}</span>
                  </td>
                  <td className="mono" style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                    {row.last_updated || '-'}
                  </td>
                  <td className="mono" style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                    {row.last_reviewed || '-'}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    {renderBooleanFlag(row.mentions_deprecated_tool)}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    {renderBooleanFlag(row.has_broken_links)}
                  </td>
                  <td>
                    {renderStalenessScore(row.staleness_score)}
                  </td>
                  <td>
                    {renderActionBadge(row.recommended_action)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
