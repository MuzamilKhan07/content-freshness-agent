import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  XCircle,
  Clock,
  Filter,
  Search,
  ChevronLeft,
  ChevronRight,
  Cpu,
  FileCheck,
} from 'lucide-react';
import {
  fetchEvidenceSummary,
  fetchEvidenceFindings,
  triggerEvidenceAudit,
} from '../services/api';
import {
  EvidenceItem,
  EvidenceSummaryResponse,
  EvidenceStatusType,
  EvidenceSignalType,
  EvidenceSeverityType,
  ScoredDocument,
} from '../types';
import { LiveUrlScanner } from './LiveUrlScanner';

interface EvidenceFindingsProps {
  onSelectScoredDocument?: (doc: ScoredDocument) => void;
  onSelectDocumentId?: (docId: string) => void;
}

export const EvidenceFindings: React.FC<EvidenceFindingsProps> = ({
  onSelectScoredDocument: _onSelectScoredDocument,
  onSelectDocumentId,
}) => {
  // Summary & Findings state
  const [summary, setSummary] = useState<EvidenceSummaryResponse | null>(null);
  const [findings, setFindings] = useState<EvidenceItem[]>([]);
  const [totalFindings, setTotalFindings] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(15);
  const [totalPages, setTotalPages] = useState<number>(1);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [signalTypeFilter, setSignalTypeFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [searchDocId, setSearchDocId] = useState<string>('');

  // Audit control configuration state
  const [enabledChecks, setEnabledChecks] = useState<{ [key: string]: boolean }>({
    metadata_inspection: true,
    url_verification: true,
    deprecated_tools: true,
    metadata_quality: true,
  });
  const [maxAuditDocs, setMaxAuditDocs] = useState<number>(500);

  // UI state
  const [loadingSummary, setLoadingSummary] = useState<boolean>(true);
  const [loadingFindings, setLoadingFindings] = useState<boolean>(true);
  const [isAuditing, setIsAuditing] = useState<boolean>(false);
  const [auditMessage, setAuditMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Load summary
  const loadSummary = useCallback(async () => {
    try {
      setLoadingSummary(true);
      const data = await fetchEvidenceSummary();
      setSummary(data);
    } catch (err: any) {
      console.error('Failed to load evidence summary:', err);
    } finally {
      setLoadingSummary(false);
    }
  }, []);

  // Load findings with current filters & pagination
  const loadFindings = useCallback(async () => {
    try {
      setLoadingFindings(true);
      const res = await fetchEvidenceFindings({
        page: currentPage,
        page_size: pageSize,
        status: statusFilter,
        signal_type: signalTypeFilter,
        severity: severityFilter,
        document_id: searchDocId.trim() || undefined,
      });
      setFindings(res.items);
      setTotalFindings(res.total);
      setTotalPages(res.total_pages);
    } catch (err: any) {
      console.error('Failed to load evidence findings:', err);
    } finally {
      setLoadingFindings(false);
    }
  }, [currentPage, pageSize, statusFilter, signalTypeFilter, severityFilter, searchDocId]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  useEffect(() => {
    loadFindings();
  }, [loadFindings]);

  // Handle running the audit
  const handleRunAudit = async () => {
    setIsAuditing(true);
    setAuditMessage({ text: 'Evidence Collection Agent is inspecting documents and validating signals...', type: 'info' });

    try {
      const activeCheckNames = Object.entries(enabledChecks)
        .filter(([_, active]) => active)
        .map(([name]) => name);

      const record = await triggerEvidenceAudit({
        max_documents: maxAuditDocs,
        enabled_checks: activeCheckNames,
      });

      setSummary(record.summary);
      setAuditMessage({
        text: `Evidence audit completed! ${record.document_ids.length} documents inspected, ${record.total_evidence_produced} evidence records produced across ${record.checks_performed.length} checks. Phase 3 scores refreshed.`,
        type: 'success',
      });
      // Reset page to 1 and reload
      setCurrentPage(1);
      await loadFindings();
    } catch (err: any) {
      setAuditMessage({
        text: err.message || 'Evidence audit run failed.',
        type: 'error',
      });
    } finally {
      setIsAuditing(false);
    }
  };

  const toggleCheck = (checkKey: string) => {
    setEnabledChecks((prev) => ({
      ...prev,
      [checkKey]: !prev[checkKey],
    }));
  };

  // Status Badge Helper
  const renderStatusBadge = (status: EvidenceStatusType) => {
    switch (status) {
      case 'confirmed':
        return (
          <span className="evidence-badge status-confirmed" title="Directly verified or sourced with high certainty">
            <CheckCircle2 size={12} /> Confirmed
          </span>
        );
      case 'suspected':
        return (
          <span className="evidence-badge status-suspected" title="Heuristic indicator detected; full independent verification pending">
            <AlertTriangle size={12} /> Suspected
          </span>
        );
      case 'unknown':
        return (
          <span className="evidence-badge status-unknown" title="Information unavailable or not determinable from available fields">
            <HelpCircle size={12} /> Unknown
          </span>
        );
      case 'failed':
        return (
          <span className="evidence-badge status-failed" title="Check was attempted but could not be safely resolved">
            <XCircle size={12} /> Failed
          </span>
        );
      default:
        return <span className="evidence-badge status-na">N/A</span>;
    }
  };

  // Severity Badge Helper
  const renderSeverityBadge = (severity: EvidenceSeverityType) => {
    const cls = `severity-${severity}`;
    return <span className={`evidence-badge ${cls}`}>{severity}</span>;
  };

  // Signal Type Badge Helper
  const renderSignalTypeBadge = (sig: EvidenceSignalType) => {
    let label = sig.replace(/_/g, ' ');
    return (
      <span className="badge-tag" style={{ textTransform: 'capitalize', fontSize: '0.72rem' }}>
        {label}
      </span>
    );
  };

  return (
    <div className="audit-findings-container">
      {/* Page Title & Header */}
      <div className="section-header" style={{ marginBottom: 16 }}>
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Cpu size={26} color="var(--primary-600)" />
            Evidence Collection Agent &amp; Content Verification
          </h1>
          <p className="page-subtitle">
            Autonomous multi-tool agent inspecting document metadata, running SSRF-guarded URL verification,
            detecting deprecated tools with explicit boundaries, and synchronizing verified evidence with Phase 3 scores.
          </p>
        </div>
      </div>

      {/* Live Webpage & URL Scanner */}
      <LiveUrlScanner
        onDocumentImported={async (docId) => {
          setAuditMessage({
            text: `Web document ${docId} imported into inventory catalog! Phase 3 scores refreshed.`,
            type: 'success',
          });
          await loadSummary();
          await loadFindings();
          if (onSelectDocumentId) {
            onSelectDocumentId(docId);
          }
        }}
      />

      {/* Audit Control Console */}
      <div className="card" style={{ marginBottom: 20, padding: '18px 22px', borderLeft: '4px solid var(--primary-600)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div style={{ flex: 1, minWidth: 320 }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>
              Agent Configuration &amp; Orchestration
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
              Select which verification tools the orchestrator executes across the enterprise inventory.
              Evidence findings are normalized, deduplicated, and directly fed back into freshness risk scores.
            </p>

            {/* Check toggles */}
            <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'center' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={enabledChecks.metadata_inspection}
                  onChange={() => toggleCheck('metadata_inspection')}
                  disabled={isAuditing}
                />
                <span style={{ fontWeight: 500 }}>Metadata Inspection</span>
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={enabledChecks.url_verification}
                  onChange={() => toggleCheck('url_verification')}
                  disabled={isAuditing}
                />
                <span style={{ fontWeight: 500 }}>Safe URL Verification (SSRF Protected)</span>
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={enabledChecks.deprecated_tools}
                  onChange={() => toggleCheck('deprecated_tools')}
                  disabled={isAuditing}
                />
                <span style={{ fontWeight: 500 }}>Deprecated-Tools Detection</span>
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={enabledChecks.metadata_quality}
                  onChange={() => toggleCheck('metadata_quality')}
                  disabled={isAuditing}
                />
                <span style={{ fontWeight: 500 }}>Metadata Quality Check</span>
              </label>
            </div>
          </div>

          {/* Action Button & Document Limit */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                Audit Max Docs:
              </label>
              <select
                className="select-input"
                style={{ height: 34, fontSize: '0.8rem', padding: '0 8px' }}
                value={maxAuditDocs}
                onChange={(e) => setMaxAuditDocs(Number(e.target.value))}
                disabled={isAuditing}
              >
                <option value={50}>50 documents</option>
                <option value={100}>100 documents</option>
                <option value={250}>250 documents</option>
                <option value={500}>All 500 documents</option>
              </select>
            </div>

            <button
              className="btn btn-primary"
              id="btn-run-evidence-audit"
              onClick={handleRunAudit}
              disabled={isAuditing}
              style={{ height: 42, padding: '0 20px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8, marginTop: 14 }}
            >
              {isAuditing ? (
                <>
                  <RotateCcw size={16} className="spin" />
                  <span>Collecting Evidence...</span>
                </>
              ) : (
                <>
                  <Play size={16} />
                  <span>Run Evidence Audit</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Audit Status Message Banner */}
        {auditMessage && (
          <div
            style={{
              marginTop: 14,
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              backgroundColor:
                auditMessage.type === 'success'
                  ? 'var(--emerald-50)'
                  : auditMessage.type === 'error'
                  ? 'var(--rose-50)'
                  : '#f0f9ff',
              border: `1px solid ${
                auditMessage.type === 'success'
                  ? 'var(--emerald-border)'
                  : auditMessage.type === 'error'
                  ? 'var(--rose-border)'
                  : '#bae6fd'
              }`,
              color:
                auditMessage.type === 'success'
                  ? '#065f46'
                  : auditMessage.type === 'error'
                  ? '#9f1239'
                  : '#0369a1',
            }}
          >
            {auditMessage.type === 'success' ? (
              <CheckCircle2 size={16} />
            ) : auditMessage.type === 'error' ? (
              <XCircle size={16} />
            ) : (
              <RotateCcw size={16} className="spin" />
            )}
            <span>{auditMessage.text}</span>
          </div>
        )}
      </div>

      {/* KPI Summary Cards */}
      <div className="metrics-grid" style={{ marginBottom: 20 }}>
        {/* Card 1: Inspected Documents */}
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-label">Documents Inspected</span>
            <FileCheck size={18} color="var(--primary-600)" />
          </div>
          <div className="metric-value">
            {loadingSummary ? '...' : summary?.documents_inspected ?? 0}
          </div>
          <div className="metric-footer">
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Checks attempted: <strong>{summary?.checks_attempted ?? 0}</strong>
            </span>
          </div>
        </div>

        {/* Card 2: Confirmed Findings */}
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-label">Confirmed Findings</span>
            <CheckCircle2 size={18} color="var(--rose-600)" />
          </div>
          <div className="metric-value" style={{ color: 'var(--rose-600)' }}>
            {loadingSummary ? '...' : summary?.confirmed_findings ?? 0}
          </div>
          <div className="metric-footer">
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Directly verified issues
            </span>
          </div>
        </div>

        {/* Card 3: Suspected Findings */}
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-label">Suspected Indicators</span>
            <AlertTriangle size={18} color="var(--amber-600)" />
          </div>
          <div className="metric-value" style={{ color: 'var(--amber-600)' }}>
            {loadingSummary ? '...' : summary?.suspected_findings ?? 0}
          </div>
          <div className="metric-footer">
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Heuristics needing verification
            </span>
          </div>
        </div>

        {/* Card 4: Unknown / Inconclusive Signals */}
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-label">Unknown / Missing Signals</span>
            <HelpCircle size={18} color="#64748b" />
          </div>
          <div className="metric-value" style={{ color: '#64748b' }}>
            {loadingSummary ? '...' : summary?.unknown_signals ?? 0}
          </div>
          <div className="metric-footer">
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Failed checks: <strong>{summary?.failed_checks ?? 0}</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Signal Breakdown Pills */}
      <div
        className="card"
        style={{
          padding: '12px 18px',
          marginBottom: 20,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 12,
          fontSize: '0.82rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Findings Breakdown:</span>
          <span>
            Broken Links: <strong className="mono" style={{ color: 'var(--rose-600)' }}>{summary?.broken_link_findings ?? 0}</strong>
          </span>
          <span>&bull;</span>
          <span>
            Deprecated Tools: <strong className="mono" style={{ color: 'var(--amber-600)' }}>{summary?.deprecated_reference_findings ?? 0}</strong>
          </span>
          <span>&bull;</span>
          <span>
            Metadata Quality Issues: <strong className="mono" style={{ color: 'var(--primary-600)' }}>{summary?.metadata_quality_findings ?? 0}</strong>
          </span>
        </div>

        {summary?.audit_completed_timestamp && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: '0.75rem' }}>
            <Clock size={14} />
            <span>Last audit run: {new Date(summary.audit_completed_timestamp).toLocaleString()}</span>
          </div>
        )}
      </div>

      {/* Filter and Search Toolbar */}
      <div className="card filter-card" style={{ marginBottom: 16, padding: '14px 18px' }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
          {/* Search by doc id */}
          <div style={{ position: 'relative', width: 220 }}>
            <Search size={15} style={{ position: 'absolute', left: 10, top: 10, color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="text-input"
              placeholder="Search Document ID..."
              value={searchDocId}
              onChange={(e) => {
                setSearchDocId(e.target.value);
                setCurrentPage(1);
              }}
              style={{ paddingLeft: 32, height: 36, fontSize: '0.82rem', width: '100%' }}
            />
          </div>

          {/* Filter dropdowns */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Filter size={14} color="var(--text-muted)" />
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Status:</span>
              <select
                className="select-input"
                style={{ height: 34, fontSize: '0.8rem' }}
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="all">All Statuses</option>
                <option value="confirmed">Confirmed</option>
                <option value="suspected">Suspected</option>
                <option value="unknown">Unknown</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Signal:</span>
              <select
                className="select-input"
                style={{ height: 34, fontSize: '0.8rem' }}
                value={signalTypeFilter}
                onChange={(e) => {
                  setSignalTypeFilter(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="all">All Signals</option>
                <option value="broken_links">Broken Links</option>
                <option value="deprecated_tools">Deprecated Tools</option>
                <option value="metadata_quality">Metadata Quality</option>
                <option value="document_age">Document Age</option>
                <option value="url_verification">URL Verification</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Severity:</span>
              <select
                className="select-input"
                style={{ height: 34, fontSize: '0.8rem' }}
                value={severityFilter}
                onChange={(e) => {
                  setSeverityFilter(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="moderate">Moderate</option>
                <option value="low">Low</option>
                <option value="info">Info</option>
              </select>
            </div>

            {(statusFilter !== 'all' || signalTypeFilter !== 'all' || severityFilter !== 'all' || searchDocId) && (
              <button
                className="btn btn-secondary"
                style={{ height: 34, padding: '0 10px', fontSize: '0.78rem' }}
                onClick={() => {
                  setStatusFilter('all');
                  setSignalTypeFilter('all');
                  setSeverityFilter('all');
                  setSearchDocId('');
                  setCurrentPage(1);
                }}
              >
                Reset Filters
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Findings Data Table */}
      <div className="card table-card" style={{ padding: 0 }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            Recorded Evidence Items ({totalFindings})
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Showing page {currentPage} of {Math.max(totalPages, 1)}
          </span>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 110 }}>Doc ID</th>
                <th style={{ width: 130 }}>Signal Type</th>
                <th style={{ width: 110 }}>Status</th>
                <th style={{ width: 90 }}>Severity</th>
                <th>Summary &amp; Provenance</th>
                <th style={{ width: 140 }}>Source Field</th>
                <th style={{ width: 180 }}>Recommended Action</th>
                <th style={{ width: 90 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loadingFindings ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
                    <RotateCcw size={20} className="spin" style={{ margin: '0 auto 8px auto', display: 'block' }} />
                    Loading evidence findings...
                  </td>
                </tr>
              ) : findings.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
                    <ShieldAlert size={28} style={{ margin: '0 auto 8px auto', display: 'block', color: 'var(--text-muted)' }} />
                    No evidence items match the selected filter criteria.
                  </td>
                </tr>
              ) : (
                findings.map((item) => (
                  <tr key={item.evidence_id}>
                    <td>
                      <button
                        className="btn-link mono"
                        style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--primary-600)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                        onClick={() => onSelectDocumentId && onSelectDocumentId(item.document_id)}
                        title="View document details"
                      >
                        {item.document_id}
                      </button>
                    </td>
                    <td>{renderSignalTypeBadge(item.signal_type)}</td>
                    <td>{renderStatusBadge(item.status)}</td>
                    <td>{renderSeverityBadge(item.severity)}</td>
                    <td>
                      <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {item.summary}
                      </div>
                      {item.evidence_reference && (
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }} className="mono">
                          Ref: {item.evidence_reference}
                        </div>
                      )}
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
                        Tool: <code>{item.tool_name}</code> &bull; Confidence: {(item.confidence * 100).toFixed(0)}%
                      </div>
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: '0.75rem', backgroundColor: '#f1f5f9', padding: '2px 6px', borderRadius: 4 }}>
                        {item.source_field}
                      </span>
                      {item.observed_value && (
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: 2 }} className="truncate-cell" title={item.observed_value}>
                          Val: {item.observed_value}
                        </div>
                      )}
                    </td>
                    <td>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        {item.recommended_action}
                      </div>
                    </td>
                    <td>
                      <button
                        className="btn-inspect"
                        onClick={() => onSelectDocumentId && onSelectDocumentId(item.document_id)}
                        title="Inspect Document"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div style={{ padding: '12px 18px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Page Size:</span>
            <select
              className="select-input"
              style={{ height: 28, fontSize: '0.75rem', padding: '0 6px' }}
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
            >
              <option value={10}>10</option>
              <option value={15}>15</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              className="btn btn-secondary"
              style={{ height: 30, padding: '0 8px' }}
              disabled={currentPage <= 1 || loadingFindings}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft size={16} />
            </button>
            <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>
              {currentPage} / {Math.max(totalPages, 1)}
            </span>
            <button
              className="btn btn-secondary"
              style={{ height: 30, padding: '0 8px' }}
              disabled={currentPage >= totalPages || loadingFindings}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
