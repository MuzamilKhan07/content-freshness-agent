import React, { useState, useEffect, useCallback } from 'react';
import {
  GitCompare,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Filter,
  Search,
  ChevronLeft,
  ChevronRight,
  X,
  FileText,
  ShieldAlert,
  Check,
  Ban,
  Archive,
} from 'lucide-react';
import {
  fetchContradictionsSummary,
  fetchContradictions,
  triggerContradictionAudit,
  reviewContradiction,
} from '../services/api';
import {
  ContradictionFinding,
  ContradictionSummaryResponse,
  ContradictionRelationshipType,
  ContradictionSeverityType,
  ContradictionReviewStatusType,
  RecencyAssessmentType,
} from '../types';

interface ContradictionDetectionProps {
  onSelectDocumentId?: (docId: string) => void;
}

export const ContradictionDetection: React.FC<ContradictionDetectionProps> = ({
  onSelectDocumentId,
}) => {
  // Summary and findings state
  const [summary, setSummary] = useState<ContradictionSummaryResponse | null>(null);
  const [findings, setFindings] = useState<ContradictionFinding[]>([]);
  const [totalFindings, setTotalFindings] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(15);
  const [totalPages, setTotalPages] = useState<number>(1);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [relFilter, setRelFilter] = useState<string>('all');
  const [sevFilter, setSevFilter] = useState<string>('all');
  const [subjectFilter, setSubjectFilter] = useState<string>('all');
  const [searchDocId, setSearchDocId] = useState<string>('');

  // Audit control configuration
  const [selectedSubject, setSelectedSubject] = useState<string>('all');
  const [maxComparisons, setMaxComparisons] = useState<number>(20);

  // UI state
  const [loadingSummary, setLoadingSummary] = useState<boolean>(true);
  const [loadingFindings, setLoadingFindings] = useState<boolean>(true);
  const [isAuditing, setIsAuditing] = useState<boolean>(false);
  const [auditMessage, setAuditMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Detail Modal / Comparison Drawer state
  const [selectedFinding, setSelectedFinding] = useState<ContradictionFinding | null>(null);
  const [reviewNote, setReviewNote] = useState<string>('');
  const [isReviewing, setIsReviewing] = useState<boolean>(false);
  const [reviewActionSuccess, setReviewActionSuccess] = useState<string | null>(null);

  // Load summary metrics
  const loadSummary = useCallback(async () => {
    try {
      setLoadingSummary(true);
      const data = await fetchContradictionsSummary();
      setSummary(data);
    } catch (err: any) {
      console.error('Failed to load contradictions summary:', err);
    } finally {
      setLoadingSummary(false);
    }
  }, []);

  // Load findings
  const loadFindings = useCallback(async () => {
    try {
      setLoadingFindings(true);
      const res = await fetchContradictions({
        page: currentPage,
        page_size: pageSize,
        relationship_type: relFilter,
        severity: sevFilter,
        status: statusFilter,
        document_id: searchDocId.trim() || undefined,
        subject_area: subjectFilter,
      });
      setFindings(res.items);
      setTotalFindings(res.total);
      setTotalPages(res.total_pages);
    } catch (err: any) {
      console.error('Failed to load contradictions:', err);
    } finally {
      setLoadingFindings(false);
    }
  }, [currentPage, pageSize, relFilter, sevFilter, statusFilter, searchDocId, subjectFilter]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  useEffect(() => {
    loadFindings();
  }, [loadFindings]);

  // Run audit
  const handleRunAudit = async () => {
    setIsAuditing(true);
    setAuditMessage({ text: 'AI Contradiction Agent is selecting candidate pairs and extracting claims...', type: 'info' });

    try {
      const updatedSummary = await triggerContradictionAudit({
        subject_area: selectedSubject === 'all' ? undefined : selectedSubject,
        max_comparisons: maxComparisons,
        force_reanalysis: true,
      });

      setSummary(updatedSummary);
      setAuditMessage({
        text: `Contradiction audit completed! ${updatedSummary.total_pairs_analyzed} candidate pairs analyzed. ${updatedSummary.total_findings} findings discovered across enterprise documents.`,
        type: 'success',
      });
      setCurrentPage(1);
      await loadFindings();
    } catch (err: any) {
      setAuditMessage({
        text: err.message || 'Contradiction audit execution failed.',
        type: 'error',
      });
    } finally {
      setIsAuditing(false);
    }
  };

  // Handle reviewing finding
  const handleReviewAction = async (newStatus: ContradictionReviewStatusType) => {
    if (!selectedFinding) return;

    if ((newStatus === 'dismissed' || newStatus === 'resolved') && !reviewNote.trim()) {
      alert('Please provide a brief reviewer note explaining the decision.');
      return;
    }

    try {
      setIsReviewing(true);
      const updated = await reviewContradiction(selectedFinding.contradiction_id, {
        status: newStatus,
        review_note: reviewNote.trim() || undefined,
        reviewed_by: 'Lead Knowledge Auditor',
      });

      setSelectedFinding(updated);
      setReviewActionSuccess(`Finding ${updated.contradiction_id} successfully marked as ${newStatus}. Freshness scores refreshed.`);
      await loadSummary();
      await loadFindings();
    } catch (err: any) {
      alert(`Review action failed: ${err.message}`);
    } finally {
      setIsReviewing(false);
    }
  };

  // Helper renderers
  const renderRelationshipBadge = (rel: ContradictionRelationshipType) => {
    switch (rel) {
      case 'contradiction':
        return (
          <span className="evidence-badge status-confirmed" style={{ fontWeight: 700 }}>
            <AlertTriangle size={12} /> Contradiction
          </span>
        );
      case 'supersession':
        return (
          <span className="evidence-badge status-suspected" style={{ fontWeight: 600 }}>
            <RotateCcw size={12} /> Superseded
          </span>
        );
      case 'scope_difference':
        return (
          <span className="evidence-badge status-unknown" style={{ fontWeight: 500 }}>
            <HelpCircle size={12} /> Scope Diff
          </span>
        );
      case 'complementary':
        return (
          <span className="evidence-badge status-na" style={{ color: 'var(--emerald-600)' }}>
            <CheckCircle2 size={12} /> Compatible
          </span>
        );
      default:
        return <span className="evidence-badge status-na">Unknown</span>;
    }
  };

  const renderStatusBadge = (status: ContradictionReviewStatusType) => {
    switch (status) {
      case 'confirmed':
        return (
          <span className="risk-badge critical" style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
            Confirmed Conflict
          </span>
        );
      case 'pending_review':
        return (
          <span className="risk-badge moderate" style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
            Pending Review
          </span>
        );
      case 'resolved':
        return (
          <span className="risk-badge low" style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
            Resolved
          </span>
        );
      case 'dismissed':
        return (
          <span className="risk-badge" style={{ backgroundColor: '#f1f5f9', color: '#64748b', fontSize: '0.72rem', padding: '2px 8px' }}>
            Dismissed
          </span>
        );
    }
  };

  const renderSeverityBadge = (sev: ContradictionSeverityType) => {
    const cls = `severity-${sev}`;
    return <span className={`evidence-badge ${cls}`}>{sev}</span>;
  };

  const renderRecencyBadge = (rec: RecencyAssessmentType) => {
    let label = 'Authority Unclear';
    let color = '#64748b';
    if (rec === 'newer_document_likely_authoritative') {
      label = 'Newer Doc Authoritative';
      color = 'var(--emerald-600)';
    } else if (rec === 'older_document_explicitly_superseded') {
      label = 'Older Doc Superseded';
      color = 'var(--rose-600)';
    }

    return (
      <span className="mono" style={{ fontSize: '0.72rem', color, fontWeight: 600 }}>
        {label}
      </span>
    );
  };

  return (
    <div className="audit-findings-container">
      {/* Header */}
      <div className="section-header" style={{ marginBottom: 16 }}>
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <GitCompare size={26} color="#6366f1" />
            AI Contradiction Detection Agent &amp; Cross-Document Reasoning
          </h1>
          <p className="page-subtitle">
            Semantic reasoning agent extracting structured claims across enterprise documents, identifying factual
            and procedural policy contradictions, evaluating temporal supersession, and updating freshness scores.
          </p>
        </div>
      </div>

      {/* Audit Console Card */}
      <div className="card" style={{ marginBottom: 20, padding: '18px 22px', borderLeft: '4px solid #6366f1' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div style={{ flex: 1, minWidth: 320 }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>
              Candidate Pair Orchestration &amp; Claim Extraction
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
              The agent clusters related documents by subject area, extracts structured procedural and numerical claims,
              and evaluates semantic compatibility. Confirmed findings directly penalize freshness-risk scores (up to 15 points).
            </p>

            <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Target Subject:</span>
                <select
                  className="select-input"
                  style={{ height: 34, fontSize: '0.8rem' }}
                  value={selectedSubject}
                  onChange={(e) => setSelectedSubject(e.target.value)}
                  disabled={isAuditing}
                >
                  <option value="all">All Subject Areas</option>
                  <option value="Security">Security &amp; Change Control</option>
                  <option value="Finance">Finance &amp; Travel Expenses</option>
                  <option value="Product">Product Release Management</option>
                  <option value="IT">IT Infrastructure &amp; Tooling</option>
                  <option value="Data Science">Data Science</option>
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Max Pairs:</span>
                <select
                  className="select-input"
                  style={{ height: 34, fontSize: '0.8rem' }}
                  value={maxComparisons}
                  onChange={(e) => setMaxComparisons(Number(e.target.value))}
                  disabled={isAuditing}
                >
                  <option value={10}>10 candidate pairs</option>
                  <option value={20}>20 candidate pairs</option>
                  <option value={50}>50 candidate pairs</option>
                </select>
              </div>
            </div>
          </div>

          <button
            className="btn btn-primary"
            id="btn-run-contradiction-audit"
            onClick={handleRunAudit}
            disabled={isAuditing}
            style={{
              height: 42,
              padding: '0 20px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              backgroundColor: '#4f46e5',
              marginTop: 14,
            }}
          >
            {isAuditing ? (
              <>
                <RotateCcw size={16} className="spin" />
                <span>Comparing Document Claims...</span>
              </>
            ) : (
              <>
                <Play size={16} />
                <span>Run Contradiction Audit</span>
              </>
            )}
          </button>
        </div>

        {/* Audit Status Message */}
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
              backgroundColor: auditMessage.type === 'success' ? 'var(--emerald-50)' : '#f0f9ff',
              border: `1px solid ${auditMessage.type === 'success' ? 'var(--emerald-border)' : '#bae6fd'}`,
              color: auditMessage.type === 'success' ? '#065f46' : '#0369a1',
            }}
          >
            {auditMessage.type === 'success' ? <CheckCircle2 size={16} /> : <RotateCcw size={16} className="spin" />}
            <span>{auditMessage.text}</span>
          </div>
        )}
      </div>

      {/* KPI Metrics Summary */}
      <div className="metrics-grid" style={{ marginBottom: 20 }}>
        {/* Card 1: Pairs Analyzed */}
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-label">Pairs Analyzed</span>
            <GitCompare size={18} color="#6366f1" />
          </div>
          <div className="metric-value">
            {loadingSummary ? '...' : summary?.total_pairs_analyzed ?? 0}
          </div>
          <div className="metric-footer">
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Candidate pairs compared
            </span>
          </div>
        </div>

        {/* Card 2: Confirmed Contradictions */}
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-label">Confirmed Contradictions</span>
            <AlertTriangle size={18} color="var(--rose-600)" />
          </div>
          <div className="metric-value" style={{ color: 'var(--rose-600)' }}>
            {loadingSummary ? '...' : summary?.confirmed_contradictions ?? 0}
          </div>
          <div className="metric-footer">
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Active in scoring engine (+15 pts)
            </span>
          </div>
        </div>

        {/* Card 3: Pending Review */}
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-label">Pending Human Review</span>
            <HelpCircle size={18} color="var(--amber-600)" />
          </div>
          <div className="metric-value" style={{ color: 'var(--amber-600)' }}>
            {loadingSummary ? '...' : summary?.pending_review_findings ?? 0}
          </div>
          <div className="metric-footer">
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Awaiting auditor verification
            </span>
          </div>
        </div>

        {/* Card 4: Resolved / Dismissed */}
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-label">Resolved / Dismissed</span>
            <CheckCircle2 size={18} color="var(--emerald-600)" />
          </div>
          <div className="metric-value" style={{ color: 'var(--emerald-600)' }}>
            {loadingSummary ? '...' : (summary?.resolved_findings ?? 0) + (summary?.dismissed_findings ?? 0)}
          </div>
          <div className="metric-footer">
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Audited historical decisions
            </span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card filter-card" style={{ marginBottom: 16, padding: '14px 18px' }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
          {/* Doc ID Search */}
          <div style={{ position: 'relative', width: 220 }}>
            <Search size={15} style={{ position: 'absolute', left: 10, top: 10, color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="text-input"
              placeholder="Search Doc ID..."
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
                <option value="pending_review">Pending Review</option>
                <option value="confirmed">Confirmed</option>
                <option value="resolved">Resolved</option>
                <option value="dismissed">Dismissed</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Relationship:</span>
              <select
                className="select-input"
                style={{ height: 34, fontSize: '0.8rem' }}
                value={relFilter}
                onChange={(e) => {
                  setRelFilter(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="all">All Types</option>
                <option value="contradiction">Contradiction</option>
                <option value="supersession">Supersession</option>
                <option value="scope_difference">Scope Difference</option>
                <option value="complementary">Compatible</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Severity:</span>
              <select
                className="select-input"
                style={{ height: 34, fontSize: '0.8rem' }}
                value={sevFilter}
                onChange={(e) => {
                  setSevFilter(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Subject:</span>
              <select
                className="select-input"
                style={{ height: 34, fontSize: '0.8rem' }}
                value={subjectFilter}
                onChange={(e) => {
                  setSubjectFilter(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="all">All Subjects</option>
                <option value="Security">Security</option>
                <option value="Finance">Finance</option>
                <option value="Product">Product</option>
                <option value="IT">IT</option>
                <option value="Data Science">Data Science</option>
              </select>
            </div>

            {(statusFilter !== 'all' || relFilter !== 'all' || sevFilter !== 'all' || searchDocId) && (
              <button
                className="btn btn-secondary"
                style={{ height: 34, padding: '0 10px', fontSize: '0.78rem' }}
                onClick={() => {
                  setStatusFilter('all');
                  setRelFilter('all');
                  setSevFilter('all');
                  setSearchDocId('');
                  setCurrentPage(1);
                }}
              >
                Reset
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Findings Data Table */}
      <div className="card table-card" style={{ padding: 0 }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            Detected Cross-Document Findings ({totalFindings})
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Page {currentPage} of {Math.max(totalPages, 1)}
          </span>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 100 }}>Finding ID</th>
                <th style={{ width: 140 }}>Document A</th>
                <th style={{ width: 140 }}>Document B</th>
                <th style={{ width: 120 }}>Relationship</th>
                <th style={{ width: 90 }}>Severity</th>
                <th style={{ width: 150 }}>Recency Assessment</th>
                <th style={{ width: 120 }}>Status</th>
                <th>Conflict Summary</th>
                <th style={{ width: 100 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loadingFindings ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
                    <RotateCcw size={20} className="spin" style={{ margin: '0 auto 8px auto', display: 'block' }} />
                    Loading contradiction findings...
                  </td>
                </tr>
              ) : findings.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
                    <ShieldAlert size={28} style={{ margin: '0 auto 8px auto', display: 'block', color: 'var(--text-muted)' }} />
                    No contradiction findings match the selected criteria.
                  </td>
                </tr>
              ) : (
                findings.map((item) => (
                  <tr key={item.contradiction_id}>
                    <td>
                      <span className="mono" style={{ fontWeight: 600, fontSize: '0.78rem' }}>
                        {item.contradiction_id}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn-link mono"
                        style={{ fontWeight: 600, fontSize: '0.78rem', color: 'var(--primary-600)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                        onClick={() => onSelectDocumentId && onSelectDocumentId(item.document_a_id)}
                        title={item.document_a_title}
                      >
                        {item.document_a_id}
                      </button>
                      <div className="truncate-cell" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {item.document_a_title}
                      </div>
                    </td>
                    <td>
                      <button
                        className="btn-link mono"
                        style={{ fontWeight: 600, fontSize: '0.78rem', color: 'var(--primary-600)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                        onClick={() => onSelectDocumentId && onSelectDocumentId(item.document_b_id)}
                        title={item.document_b_title}
                      >
                        {item.document_b_id}
                      </button>
                      <div className="truncate-cell" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {item.document_b_title}
                      </div>
                    </td>
                    <td>{renderRelationshipBadge(item.relationship_type)}</td>
                    <td>{renderSeverityBadge(item.severity)}</td>
                    <td>{renderRecencyBadge(item.recency_assessment)}</td>
                    <td>{renderStatusBadge(item.status)}</td>
                    <td>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }} className="truncate-cell" title={item.explanation}>
                        {item.explanation}
                      </div>
                    </td>
                    <td>
                      <button
                        className="btn-inspect"
                        onClick={() => {
                          setSelectedFinding(item);
                          setReviewNote(item.review_note || '');
                          setReviewActionSuccess(null);
                        }}
                      >
                        Compare
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
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

      {/* Side-by-Side Comparison Drawer / Modal */}
      {selectedFinding && (
        <div className="drawer-backdrop" onClick={() => setSelectedFinding(null)} role="dialog" aria-modal="true">
          <div
            className="drawer-panel"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: 840, width: '100%' }}
          >
            {/* Header */}
            <div className="drawer-header">
              <div className="drawer-title-section">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="drawer-content-id">{selectedFinding.contradiction_id}</span>
                  {renderRelationshipBadge(selectedFinding.relationship_type)}
                  {renderSeverityBadge(selectedFinding.severity)}
                  {renderStatusBadge(selectedFinding.status)}
                </div>
                <h2 className="drawer-title" style={{ fontSize: '1.15rem', marginTop: 4 }}>
                  Cross-Document Semantic Comparison
                </h2>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Detected: {new Date(selectedFinding.detected_at).toLocaleString()} &bull; Recency: {renderRecencyBadge(selectedFinding.recency_assessment)}
                </div>
              </div>
              <button
                className="btn-close"
                onClick={() => setSelectedFinding(null)}
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            {/* Body */}
            <div className="drawer-body">
              {reviewActionSuccess && (
                <div
                  style={{
                    backgroundColor: 'var(--emerald-50)',
                    border: '1px solid var(--emerald-border)',
                    color: '#065f46',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.82rem',
                    marginBottom: 16,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                  }}
                >
                  <CheckCircle2 size={16} />
                  <span>{reviewActionSuccess}</span>
                </div>
              )}

              {/* Side-by-side Document Comparison */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
                {/* Document A */}
                <div
                  style={{
                    padding: 16,
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                    backgroundColor: '#f8fafc',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                    <FileText size={16} color="var(--primary-600)" />
                    <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>Document A</span>
                    <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      ({selectedFinding.document_a_id})
                    </span>
                  </div>
                  <h4 style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 10 }}>
                    {selectedFinding.document_a_title}
                  </h4>

                  <div style={{ marginBottom: 10 }}>
                    <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
                      Extracted Claim
                    </span>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)', fontWeight: 500, marginTop: 2 }}>
                      {selectedFinding.claim_a}
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
                      Supporting Excerpt
                    </span>
                    <div
                      style={{
                        fontSize: '0.78rem',
                        color: 'var(--text-secondary)',
                        backgroundColor: '#ffffff',
                        padding: '8px 10px',
                        borderRadius: 'var(--radius-sm)',
                        borderLeft: '3px solid var(--primary-600)',
                        marginTop: 2,
                        fontStyle: 'italic',
                      }}
                    >
                      "{selectedFinding.supporting_excerpt_a}"
                    </div>
                  </div>
                </div>

                {/* Document B */}
                <div
                  style={{
                    padding: 16,
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                    backgroundColor: '#f8fafc',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                    <FileText size={16} color="var(--rose-600)" />
                    <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>Document B</span>
                    <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      ({selectedFinding.document_b_id})
                    </span>
                  </div>
                  <h4 style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 10 }}>
                    {selectedFinding.document_b_title}
                  </h4>

                  <div style={{ marginBottom: 10 }}>
                    <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
                      Extracted Claim
                    </span>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)', fontWeight: 500, marginTop: 2 }}>
                      {selectedFinding.claim_b}
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
                      Supporting Excerpt
                    </span>
                    <div
                      style={{
                        fontSize: '0.78rem',
                        color: 'var(--text-secondary)',
                        backgroundColor: '#ffffff',
                        padding: '8px 10px',
                        borderRadius: 'var(--radius-sm)',
                        borderLeft: '3px solid var(--rose-600)',
                        marginTop: 2,
                        fontStyle: 'italic',
                      }}
                    >
                      "{selectedFinding.supporting_excerpt_b}"
                    </div>
                  </div>
                </div>
              </div>

              {/* Semantic Reasoning & Explanation */}
              <div className="detail-section">
                <div className="detail-section-title">Conflict Analysis &amp; Reasoning</div>
                <div
                  style={{
                    backgroundColor: selectedFinding.relationship_type === 'contradiction' ? '#fff1f2' : '#f8fafc',
                    border: `1px solid ${selectedFinding.relationship_type === 'contradiction' ? 'var(--rose-border)' : 'var(--border-subtle)'}`,
                    borderRadius: 'var(--radius-md)',
                    padding: '12px 16px',
                    fontSize: '0.85rem',
                    color: selectedFinding.relationship_type === 'contradiction' ? '#9f1239' : 'var(--text-primary)',
                    lineHeight: 1.5,
                  }}
                >
                  <strong>Why they conflict:</strong> {selectedFinding.explanation}
                </div>
              </div>

              {/* Recommended Action */}
              <div className="detail-section">
                <div className="detail-section-title">Recommended Remediation Action</div>
                <div
                  style={{
                    backgroundColor: 'var(--amber-50)',
                    border: '1px solid var(--amber-border)',
                    borderRadius: 'var(--radius-md)',
                    padding: '12px 16px',
                    color: '#92400e',
                    fontSize: '0.85rem',
                    lineHeight: 1.4,
                  }}
                >
                  <strong>Next Action:</strong> {selectedFinding.recommended_action}
                </div>
              </div>

              {/* Reviewer Action Bar */}
              <div className="detail-section" style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 16 }}>
                <div className="detail-section-title">Human Auditor Review Controls</div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 10 }}>
                  Confirming this conflict registers active contradiction penalties in the Phase 3 freshness scoring engine (+15 points).
                  Dismissing or resolving removes active penalties while preserving review history.
                </p>

                <div style={{ marginBottom: 12 }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                    Review Decision Note:
                  </label>
                  <input
                    type="text"
                    className="text-input"
                    placeholder="Enter audit rationale (e.g. Verified by Security Architect as active policy conflict)..."
                    value={reviewNote}
                    onChange={(e) => setReviewNote(e.target.value)}
                    style={{ width: '100%', height: 36, fontSize: '0.82rem' }}
                    disabled={isReviewing}
                  />
                </div>

                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-primary"
                    style={{ backgroundColor: 'var(--rose-600)', display: 'flex', alignItems: 'center', gap: 6 }}
                    onClick={() => handleReviewAction('confirmed')}
                    disabled={isReviewing || selectedFinding.status === 'confirmed'}
                  >
                    <Check size={15} />
                    <span>Confirm Contradiction</span>
                  </button>

                  <button
                    className="btn btn-secondary"
                    style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                    onClick={() => handleReviewAction('dismissed')}
                    disabled={isReviewing || selectedFinding.status === 'dismissed'}
                  >
                    <Ban size={15} />
                    <span>Dismiss Finding</span>
                  </button>

                  <button
                    className="btn btn-secondary"
                    style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--emerald-600)' }}
                    onClick={() => handleReviewAction('resolved')}
                    disabled={isReviewing || selectedFinding.status === 'resolved'}
                  >
                    <Archive size={15} />
                    <span>Mark Resolved</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
