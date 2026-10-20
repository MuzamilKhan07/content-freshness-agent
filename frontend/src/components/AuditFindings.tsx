import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  Search,
  Play,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  FileQuestion,
  AlertCircle,
  CheckCircle,
  X,
  SlidersHorizontal,
} from 'lucide-react';
import {
  ScoredDocument,
  AuditSummaryResponse,
  AuditDocumentListResponse,
  AuditQueryParams,
} from '../types';
import { fetchAuditSummary, fetchAuditDocuments, triggerAuditRun } from '../services/api';

interface AuditFindingsProps {
  onSelectScoredDocument: (doc: ScoredDocument) => void;
}

export const AuditFindings: React.FC<AuditFindingsProps> = ({
  onSelectScoredDocument,
}) => {
  // Summary & list state
  const [summary, setSummary] = useState<AuditSummaryResponse | null>(null);
  const [data, setData] = useState<AuditDocumentListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRunningAudit, setIsRunningAudit] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [auditNotice, setAuditNotice] = useState<string | null>(null);

  // Filter & Pagination state
  const [search, setSearch] = useState<string>('');
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');
  const [riskLevel, setRiskLevel] = useState<string>('all');
  const [evidenceStatus, setEvidenceStatus] = useState<string>('all');
  const [minScore, setMinScore] = useState<string>('');
  const [maxScore, setMaxScore] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('priority');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Load audit summary & documents
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch summary
      const sum = await fetchAuditSummary();
      setSummary(sum);

      // 2. Fetch documents
      const params: AuditQueryParams = {
        page,
        page_size: pageSize,
        search: debouncedSearch,
        risk_level: riskLevel,
        evidence_status: evidenceStatus,
        min_score: minScore !== '' ? parseInt(minScore, 10) : undefined,
        max_score: maxScore !== '' ? parseInt(maxScore, 10) : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      };
      const docsRes = await fetchAuditDocuments(params);
      setData(docsRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load audit findings.');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, debouncedSearch, riskLevel, evidenceStatus, minScore, maxScore, sortBy, sortOrder]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle Run Audit execution
  const handleRunAudit = async () => {
    if (isRunningAudit) return;
    setIsRunningAudit(true);
    setAuditNotice(null);
    try {
      const res = await triggerAuditRun();
      setSummary(res.summary);
      setAuditNotice(`Freshness audit completed successfully: ${res.documents_evaluated} documents re-evaluated.`);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Error executing audit run.');
    } finally {
      setIsRunningAudit(false);
    }
  };

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
    setPage(1);
  };

  const clearFilters = () => {
    setSearch('');
    setDebouncedSearch('');
    setRiskLevel('all');
    setEvidenceStatus('all');
    setMinScore('');
    setMaxScore('');
    setSortBy('priority');
    setSortOrder('asc');
    setPage(1);
  };

  const hasActiveFilters =
    debouncedSearch.trim() !== '' ||
    riskLevel !== 'all' ||
    evidenceStatus !== 'all' ||
    minScore !== '' ||
    maxScore !== '';

  const renderSortIndicator = (field: string) => {
    if (sortBy !== field) {
      return <ArrowUpDown size={13} className="sort-icon" />;
    }
    return sortOrder === 'asc' ? (
      <ArrowUp size={13} className="sort-icon active" />
    ) : (
      <ArrowDown size={13} className="sort-icon active" />
    );
  };

  const renderRiskBadge = (level: string) => {
    const lower = level.toLowerCase();
    let cls = 'low';
    if (lower.includes('critical')) cls = 'critical';
    else if (lower.includes('high')) cls = 'high';
    else if (lower.includes('moderate')) cls = 'moderate';
    else if (lower.includes('insufficient')) cls = 'insufficient';

    return <span className={`risk-badge ${cls}`}>{level}</span>;
  };

  const riskCounts = summary?.risk_distribution || {};

  return (
    <div id="audit-findings-module">
      {/* Run Audit Banner */}
      <div className="audit-banner">
        <div className="audit-banner-left">
          <div className="audit-banner-icon">
            <ShieldAlert size={24} />
          </div>
          <div>
            <div className="audit-banner-title">Freshness Risk Scoring Engine</div>
            <div className="audit-banner-subtitle">
              Deterministic, explainable risk calculations based on verified age, broken hyperlinks, and retired tool mentions.
            </div>
          </div>
        </div>

        <button
          className="btn-run-audit"
          id="btn-run-audit-action"
          onClick={handleRunAudit}
          disabled={isRunningAudit}
        >
          <Play size={14} className={isRunningAudit ? 'spinning' : ''} />
          <span>{isRunningAudit ? 'Executing Engine Audit...' : 'Run Freshness Audit'}</span>
        </button>
      </div>

      {auditNotice && (
        <div
          className="info-note"
          style={{
            backgroundColor: 'var(--emerald-50)',
            borderColor: 'var(--emerald-border)',
            color: 'var(--emerald-600)',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>{auditNotice}</span>
          <button
            onClick={() => setAuditNotice(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* 6 Real Risk KPI Cards */}
      <div className="kpi-grid">
        {/* Critical Risk */}
        <div className="kpi-card accent-rose" id="kpi-critical-risk">
          <div className="kpi-header">
            <span className="kpi-label">Critical Risk (80-100)</span>
            <ShieldAlert size={18} className="kpi-icon" color="var(--rose-600)" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--rose-600)' }}>
            {loading && !summary ? '...' : riskCounts['Critical'] ?? 0}
          </div>
          <div className="kpi-hint">Requires immediate remediation</div>
        </div>

        {/* High Risk */}
        <div className="kpi-card accent-amber" id="kpi-high-risk">
          <div className="kpi-header">
            <span className="kpi-label">High Risk (60-79)</span>
            <ShieldAlert size={18} className="kpi-icon" color="#ea580c" />
          </div>
          <div className="kpi-value" style={{ color: '#ea580c' }}>
            {loading && !summary ? '...' : riskCounts['High'] ?? 0}
          </div>
          <div className="kpi-hint">Elevated decay indicators</div>
        </div>

        {/* Moderate Risk */}
        <div className="kpi-card accent-amber" id="kpi-moderate-risk">
          <div className="kpi-header">
            <span className="kpi-label">Moderate Risk (30-59)</span>
            <ShieldAlert size={18} className="kpi-icon" color="var(--amber-600)" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--amber-600)' }}>
            {loading && !summary ? '...' : riskCounts['Moderate'] ?? 0}
          </div>
          <div className="kpi-hint">Routine scheduled review</div>
        </div>

        {/* Low Risk */}
        <div className="kpi-card accent-emerald" id="kpi-low-risk">
          <div className="kpi-header">
            <span className="kpi-label">Low Risk (0-29)</span>
            <CheckCircle size={18} className="kpi-icon" color="var(--emerald-600)" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--emerald-600)' }}>
            {loading && !summary ? '...' : riskCounts['Low'] ?? 0}
          </div>
          <div className="kpi-hint">Currently healthy documents</div>
        </div>

        {/* Provisional Scores */}
        <div className="kpi-card accent-blue" id="kpi-provisional-scores">
          <div className="kpi-header">
            <span className="kpi-label">Provisional Scores</span>
            <SlidersHorizontal size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value">
            {loading && !summary ? '...' : summary?.provisional_scores_count ?? 0}
          </div>
          <div className="kpi-hint">Evaluated with partial evidence</div>
        </div>

        {/* Insufficient Evidence */}
        <div className="kpi-card accent-indigo" id="kpi-insufficient-evidence">
          <div className="kpi-header">
            <span className="kpi-label">Insufficient Evidence</span>
            <HelpCircle size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value">
            {loading && !summary ? '...' : summary?.insufficient_evidence_count ?? 0}
          </div>
          <div className="kpi-hint">Telemetry missing / pending scan</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-toolbar">
        <div className="search-box">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search by ID, title, domain, author..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            id="input-audit-search"
          />
        </div>

        <div className="filters-group">
          {/* Risk Level Filter */}
          <select
            className="select-filter"
            value={riskLevel}
            onChange={(e) => {
              setRiskLevel(e.target.value);
              setPage(1);
            }}
            id="select-filter-risk"
          >
            <option value="all">All Risk Levels</option>
            <option value="Critical">Critical Risk (80-100)</option>
            <option value="High">High Risk (60-79)</option>
            <option value="Moderate">Moderate Risk (30-59)</option>
            <option value="Low">Low Risk (0-29)</option>
            <option value="Insufficient Evidence">Insufficient Evidence</option>
          </select>

          {/* Evidence Completeness Filter */}
          <select
            className="select-filter"
            value={evidenceStatus}
            onChange={(e) => {
              setEvidenceStatus(e.target.value);
              setPage(1);
            }}
            id="select-filter-evidence"
          >
            <option value="all">All Evidence States</option>
            <option value="provisional">Provisional (Partial Coverage)</option>
            <option value="fully_evaluated">Fully Evaluated (100%)</option>
            <option value="insufficient_evidence">Insufficient Evidence</option>
          </select>

          {/* Min / Max score filter inputs */}
          <input
            type="number"
            min="0"
            max="100"
            className="search-input"
            style={{ width: 90, height: 36 }}
            placeholder="Min Score"
            value={minScore}
            onChange={(e) => {
              setMinScore(e.target.value);
              setPage(1);
            }}
            title="Minimum score threshold"
          />

          <input
            type="number"
            min="0"
            max="100"
            className="search-input"
            style={{ width: 90, height: 36 }}
            placeholder="Max Score"
            value={maxScore}
            onChange={(e) => {
              setMaxScore(e.target.value);
              setPage(1);
            }}
            title="Maximum score threshold"
          />

          {hasActiveFilters && (
            <button
              className="btn-clear-filters"
              onClick={clearFilters}
              title="Reset all active search and filter options"
            >
              <X size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Prioritized Findings Table */}
      <div className="table-card">
        {loading && !data ? (
          <div className="empty-state">
            <div className="dot-indicator" style={{ width: 24, height: 24, marginBottom: 8 }} />
            <h3 className="empty-state-title">Evaluating Prioritized Queue...</h3>
            <p className="empty-state-desc">Running deterministic scoring algorithm across documents.</p>
          </div>
        ) : error ? (
          <div className="empty-state">
            <AlertCircle size={36} color="var(--rose-600)" />
            <h3 className="empty-state-title">Failed to Load Findings</h3>
            <p className="empty-state-desc">{error}</p>
            <button className="btn-secondary" onClick={loadData} style={{ marginTop: 8 }}>
              Retry Evaluation
            </button>
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="empty-state">
            <FileQuestion size={36} className="empty-state-icon" />
            <h3 className="empty-state-title">No Scored Documents Match Filter Criteria</h3>
            <p className="empty-state-desc">
              Try adjusting your score thresholds, risk level filter, or search keywords.
            </p>
            {hasActiveFilters && (
              <button className="btn-secondary" onClick={clearFilters} style={{ marginTop: 8 }}>
                Clear Filters
              </button>
            )}
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="enterprise-table" id="audit-table">
              <thead>
                <tr>
                  <th className="sortable-th" onClick={() => handleSort('priority')}>
                    <div className="th-content">
                      <span>Priority Rank</span>
                      {renderSortIndicator('priority')}
                    </div>
                  </th>
                  <th className="sortable-th" onClick={() => handleSort('score')}>
                    <div className="th-content">
                      <span>Risk Score</span>
                      {renderSortIndicator('score')}
                    </div>
                  </th>
                  <th>Classification</th>
                  <th className="sortable-th" onClick={() => handleSort('evidence_coverage')}>
                    <div className="th-content">
                      <span>Evidence</span>
                      {renderSortIndicator('evidence_coverage')}
                    </div>
                  </th>
                  <th className="sortable-th" onClick={() => handleSort('content_id')}>
                    <div className="th-content">
                      <span>Document</span>
                      {renderSortIndicator('content_id')}
                    </div>
                  </th>
                  <th>Top Contributing Risk Factors</th>
                  <th className="sortable-th" onClick={() => handleSort('last_updated')}>
                    <div className="th-content">
                      <span>Last Updated</span>
                      {renderSortIndicator('last_updated')}
                    </div>
                  </th>
                  <th>Remediation Priority Reason</th>
                  <th style={{ textAlign: 'center' }}>Inspect</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((doc) => (
                  <tr
                    key={doc.content_id}
                    onClick={() => onSelectScoredDocument(doc)}
                    title="Click to view full scoring explanation"
                  >
                    <td>
                      <span
                        className="badge-tag"
                        style={{
                          fontWeight: 700,
                          backgroundColor: doc.priority_rank <= 2 ? 'var(--rose-50)' : '#f1f5f9',
                          color: doc.priority_rank <= 2 ? 'var(--rose-600)' : '#334155',
                          border: doc.priority_rank <= 2 ? '1px solid var(--rose-border)' : '1px solid #cbd5e1',
                        }}
                      >
                        Rank #{doc.priority_rank}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                        <span
                          className="mono"
                          style={{
                            fontSize: '1.05rem',
                            fontWeight: 800,
                            color:
                              doc.calculated_score !== null && doc.calculated_score >= 80
                                ? 'var(--rose-600)'
                                : doc.calculated_score !== null && doc.calculated_score >= 60
                                ? '#ea580c'
                                : doc.calculated_score !== null && doc.calculated_score >= 30
                                ? 'var(--amber-600)'
                                : 'var(--emerald-600)',
                          }}
                        >
                          {doc.calculated_score !== null ? doc.calculated_score : 'N/A'}
                        </span>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>/100</span>
                      </div>
                      {doc.is_provisional && (
                        <div style={{ fontSize: '0.65rem', color: 'var(--amber-600)', fontWeight: 600 }}>
                          Provisional
                        </div>
                      )}
                    </td>
                    <td>{renderRiskBadge(doc.risk_level)}</td>
                    <td>
                      <span className="coverage-pill" title={`${doc.evidence_coverage}% weights evaluated`}>
                        {doc.evidence_coverage}%
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <span className="doc-id-pill" style={{ alignSelf: 'flex-start' }}>
                          {doc.content_id}
                        </span>
                        <span
                          style={{
                            fontWeight: 600,
                            maxWidth: 220,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {doc.title}
                        </span>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                          {doc.platform} &bull; {doc.content_type}
                        </span>
                      </div>
                    </td>
                    <td style={{ maxWidth: 220, whiteSpace: 'normal', fontSize: '0.78rem' }}>
                      {doc.top_contributing_factors.slice(0, 2).map((factor, idx) => (
                        <div key={idx} style={{ color: 'var(--text-secondary)' }}>
                          &bull; {factor}
                        </div>
                      ))}
                    </td>
                    <td className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {doc.last_updated || 'Not provided'}
                    </td>
                    <td style={{ maxWidth: 260, whiteSpace: 'normal', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                      {doc.priority_explanation}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <button
                        className="btn-secondary"
                        style={{ padding: '4px 10px', fontSize: '0.75rem', fontWeight: 600 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectScoredDocument(doc);
                        }}
                      >
                        Explain Score
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {data && data.total > 0 && (
          <div className="table-pagination">
            <div className="pagination-info">
              Showing{' '}
              <strong>
                {Math.min((data.page - 1) * data.page_size + 1, data.total)}
              </strong>{' '}
              to{' '}
              <strong>
                {Math.min(data.page * data.page_size, data.total)}
              </strong>{' '}
              of <strong>{data.total.toLocaleString()}</strong> scored documents
            </div>

            <div className="pagination-controls">
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginRight: 6 }}>
                Per page:
              </span>
              <select
                className="select-filter"
                style={{ height: 32, paddingRight: 22 }}
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>

              <button
                className="btn-page"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={data.page <= 1 || loading}
                title="Previous page"
              >
                <ChevronLeft size={16} />
                <span>Prev</span>
              </button>

              <span className="page-indicator">
                Page {data.page} of {data.total_pages}
              </span>

              <button
                className="btn-page"
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                disabled={data.page >= data.total_pages || loading}
                title="Next page"
              >
                <span>Next</span>
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
