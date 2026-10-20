import React, { useState, useEffect, useCallback } from 'react';
import {
  Wrench,
  Sparkles,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  RefreshCw,
  Search,
  FileText,
  ShieldAlert,
  HelpCircle,
  RotateCcw,
  PlusCircle,
  Check,
  GitBranch,
} from 'lucide-react';
import {
  RemediationJob,
  DraftRevision,
  RemediationSummaryResponse,
  ScoredDocument,
} from '../types';
import {
  fetchRemediationSummary,
  fetchRemediationJobs,
  fetchRemediationJob,
  createRemediationJob,
  generateRemediationDraft,
  validateRevision,
  reviewDraftRevision,
  regenerateDraftRevision,
  fetchDocumentContent,
  ingestDocumentContent,
  fetchAuditDocuments,
} from '../services/api';

interface RemediationWorkspaceProps {
  initialDocumentId?: string | null;
  onSelectDocumentId?: (docId: string) => void;
}

export const RemediationWorkspace: React.FC<RemediationWorkspaceProps> = ({
  initialDocumentId,
  onSelectDocumentId,
}) => {
  // Queue & Summary State
  const [summary, setSummary] = useState<RemediationSummaryResponse | null>(null);
  const [jobs, setJobs] = useState<RemediationJob[]>([]);
  const [totalJobs, setTotalJobs] = useState<number>(0);
  const [page] = useState<number>(1);
  const [pageSize] = useState<number>(12);
  const [searchDocId, setSearchDocId] = useState<string>(initialDocumentId || '');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [valFilter, setValFilter] = useState<string>('all');
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Active Selected Job / Workspace State
  const [selectedJob, setSelectedJob] = useState<RemediationJob | null>(null);
  const [activeRevision, setActiveRevision] = useState<DraftRevision | null>(null);
  const [activeRevisionIndex, setActiveRevisionIndex] = useState<number>(0);
  const [isGeneratingDraft, setIsGeneratingDraft] = useState<boolean>(false);
  const [isValidatingDraft, setIsValidatingDraft] = useState<boolean>(false);

  // Modal / Review action state
  const [reviewAction, setReviewAction] = useState<'approve' | 'reject' | 'request_changes' | null>(null);
  const [reviewNote, setReviewNote] = useState<string>('');
  const [reviewerName, setReviewName] = useState<string>('Enterprise Knowledge Lead');
  const [reviewSubmitting, setReviewSubmitting] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Regenerate modal state
  const [showRegenModal, setShowRegenModal] = useState<boolean>(false);
  const [regenFeedback, setRegenFeedback] = useState<string>('');

  // Create Job Modal state
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [candidateDocs, setCandidateDocs] = useState<ScoredDocument[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>(initialDocumentId || 'CNT-0001');
  const [customObjective, setCustomObjective] = useState<string>('');
  const [contentAvail, setContentAvail] = useState<boolean | null>(null);
  const [ingestText, setIngestText] = useState<string>('');
  const [isIngestingText, setIsIngestingText] = useState<boolean>(false);
  const [createJobSubmitting, setCreateJobSubmitting] = useState<boolean>(false);

  // Load summary and jobs queue
  const loadWorkspaceData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setIsRefreshing(true);
    else setLoading(true);

    try {
      const [sumRes, jobsRes] = await Promise.all([
        fetchRemediationSummary(),
        fetchRemediationJobs({
          page,
          page_size: pageSize,
          document_id: searchDocId.trim() || undefined,
          status: statusFilter,
          validation_status: valFilter,
        }),
      ]);
      setSummary(sumRes);
      setJobs(jobsRes.items || []);
      setTotalJobs(jobsRes.total || 0);

      // If initial doc ID provided, automatically pick it up or find its job
      if (initialDocumentId && !selectedJob) {
        const matchingJob = jobsRes.items.find((j) => j.document_id.toUpperCase() === initialDocumentId.toUpperCase());
        if (matchingJob) {
          openJobDetail(matchingJob.remediation_id);
        }
      }
    } catch (err) {
      console.error('Failed to load remediation workspace data:', err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [page, pageSize, searchDocId, statusFilter, valFilter, initialDocumentId, selectedJob]);

  useEffect(() => {
    loadWorkspaceData(false);
  }, [loadWorkspaceData]);

  // Candidate docs for creation modal
  useEffect(() => {
    if (showCreateModal) {
      fetchAuditDocuments({ page: 1, page_size: 50 })
        .then((res) => {
          setCandidateDocs(res.items || []);
        })
        .catch((e) => console.error('Failed to fetch candidate documents:', e));
    }
  }, [showCreateModal]);

  // Check content availability when candidate ID changes
  useEffect(() => {
    if (selectedCandidateId) {
      fetchDocumentContent(selectedCandidateId)
        .then((res) => {
          setContentAvail(res.has_content);
          if (res.has_content && res.full_text) {
            setIngestText(res.full_text);
          } else {
            setIngestText('');
          }
        })
        .catch(() => {
          setContentAvail(false);
          setIngestText('');
        });
    }
  }, [selectedCandidateId]);

  const openJobDetail = async (remediationId: string) => {
    try {
      const job = await fetchRemediationJob(remediationId);
      setSelectedJob(job);
      if (job.draft_revisions && job.draft_revisions.length > 0) {
        const latestIdx = job.draft_revisions.length - 1;
        setActiveRevisionIndex(latestIdx);
        setActiveRevision(job.draft_revisions[latestIdx]);
      } else {
        setActiveRevision(null);
      }
    } catch (e) {
      console.error('Failed to open job details:', e);
    }
  };

  const handleGenerateDraft = async () => {
    if (!selectedJob) return;
    setIsGeneratingDraft(true);
    setActionError(null);
    try {
      const newDraft = await generateRemediationDraft(selectedJob.remediation_id);
      await openJobDetail(selectedJob.remediation_id);
      setActiveRevision(newDraft);
      loadWorkspaceData(true);
    } catch (err: any) {
      setActionError(err.message || 'Draft generation failed');
    } finally {
      setIsGeneratingDraft(false);
    }
  };

  const handleValidateRevision = async () => {
    if (!activeRevision) return;
    setIsValidatingDraft(true);
    setActionError(null);
    try {
      const valRes = await validateRevision(activeRevision.revision_id);
      setActiveRevision({ ...activeRevision, validation_result: valRes, validation_status: valRes.validation_status });
      if (selectedJob) await openJobDetail(selectedJob.remediation_id);
      loadWorkspaceData(true);
    } catch (err: any) {
      setActionError(err.message || 'Validation failed');
    } finally {
      setIsValidatingDraft(false);
    }
  };

  const handleReviewSubmit = async () => {
    if (!activeRevision || !reviewAction) return;
    setReviewSubmitting(true);
    setActionError(null);
    try {
      const updated = await reviewDraftRevision(activeRevision.revision_id, {
        action: reviewAction,
        review_note: reviewNote,
        reviewer_name: reviewerName,
      });
      setActiveRevision(updated);
      setReviewAction(null);
      setReviewNote('');
      if (selectedJob) await openJobDetail(selectedJob.remediation_id);
      loadWorkspaceData(true);
    } catch (err: any) {
      setActionError(err.message || 'Review submission failed');
    } finally {
      setReviewSubmitting(false);
    }
  };

  const handleRegenerateSubmit = async () => {
    if (!activeRevision) return;
    setReviewSubmitting(true);
    setActionError(null);
    try {
      const newDraft = await regenerateDraftRevision(activeRevision.revision_id, {
        feedback_notes: regenFeedback || 'Regenerate draft incorporating human feedback.',
      });
      setShowRegenModal(false);
      setRegenFeedback('');
      setActiveRevision(newDraft);
      if (selectedJob) await openJobDetail(selectedJob.remediation_id);
      loadWorkspaceData(true);
    } catch (err: any) {
      setActionError(err.message || 'Regeneration failed');
    } finally {
      setReviewSubmitting(false);
    }
  };

  const handleCreateJob = async () => {
    if (!selectedCandidateId) return;
    setCreateJobSubmitting(true);
    setActionError(null);
    try {
      // If user typed custom text and content wasn't previously ingested, save text first
      if (ingestText.trim() && !contentAvail) {
        await ingestDocumentContent(selectedCandidateId, ingestText.trim(), 'manual_remediation_modal');
      }

      const job = await createRemediationJob({
        document_id: selectedCandidateId,
        remediation_objective: customObjective.trim() || undefined,
      });

      setShowCreateModal(false);
      setCustomObjective('');
      await loadWorkspaceData(true);
      await openJobDetail(job.remediation_id);
    } catch (err: any) {
      setActionError(err.message || 'Failed to create remediation job');
    } finally {
      setCreateJobSubmitting(false);
    }
  };

  const handleIngestTextInline = async () => {
    if (!selectedCandidateId || !ingestText.trim()) return;
    setIsIngestingText(true);
    try {
      await ingestDocumentContent(selectedCandidateId, ingestText.trim(), 'remediation_inline');
      setContentAvail(true);
    } catch (err) {
      console.error('Failed to ingest text:', err);
    } finally {
      setIsIngestingText(false);
    }
  };

  const getValidationBadge = (status: string) => {
    switch (status) {
      case 'passed':
        return <span className="risk-badge low"><CheckCircle size={13} style={{ marginRight: 4 }} /> Passed</span>;
      case 'passed_with_warnings':
        return <span className="risk-badge moderate"><AlertTriangle size={13} style={{ marginRight: 4 }} /> Warnings</span>;
      case 'failed':
        return <span className="risk-badge critical"><XCircle size={13} style={{ marginRight: 4 }} /> Failed</span>;
      case 'needs_human_review':
        return <span className="risk-badge high"><HelpCircle size={13} style={{ marginRight: 4 }} /> Needs Review</span>;
      default:
        return <span className="risk-badge insufficient"><Clock size={13} style={{ marginRight: 4 }} /> Not Run</span>;
    }
  };

  const getReviewBadge = (status: string) => {
    switch (status) {
      case 'approved':
        return <span className="evidence-badge status-confirmed"><Check size={12} /> Approved</span>;
      case 'rejected':
        return <span className="evidence-badge status-failed"><XCircle size={12} /> Rejected</span>;
      case 'changes_requested':
        return <span className="evidence-badge severity-high"><RotateCcw size={12} /> Changes Requested</span>;
      default:
        return <span className="evidence-badge status-suspected"><Clock size={12} /> Pending Review</span>;
    }
  };

  return (
    <div className="audit-view-container" style={{ paddingBottom: 40 }}>
      {/* Top Banner / Header */}
      <div className="section-header-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="card-badge" style={{ backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#10b981', fontWeight: 700 }}>
              Phase 6 Agent
            </span>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              AI Document Remediation, Rewriting & Validation
            </span>
          </div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: 4, color: 'var(--text-primary)' }}>
            Evidence-Grounded Document Remediation Workspace
          </h2>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', maxWidth: 750 }}>
            Autonomous planner, revision generator, and independent validation agents that convert detected decay signals and contradictions into verifiable, human-reviewable document proposals.
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            className="secondary-btn"
            onClick={() => loadWorkspaceData(true)}
            disabled={isRefreshing}
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <RefreshCw size={15} className={isRefreshing ? 'spin-icon' : ''} />
            <span>Refresh</span>
          </button>
          <button
            className="primary-btn"
            onClick={() => setShowCreateModal(true)}
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <PlusCircle size={16} />
            <span>New Remediation Job</span>
          </button>
        </div>
      </div>

      {/* KPI Summary Cards */}
      {summary && (
        <div className="metrics-row" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', marginTop: 16 }}>
          <div className="metric-box">
            <span className="metric-box-label">Total Jobs</span>
            <span className="metric-box-val">{summary.total_jobs}</span>
            <span className="metric-box-sub">Lifecycle managed</span>
          </div>
          <div className="metric-box">
            <span className="metric-box-label">Active Jobs</span>
            <span className="metric-box-val" style={{ color: '#0ea5e9' }}>{summary.active_jobs}</span>
            <span className="metric-box-sub">In planning or drafting</span>
          </div>
          <div className="metric-box">
            <span className="metric-box-label">Ready for Review</span>
            <span className="metric-box-val" style={{ color: 'var(--amber-600)' }}>{summary.ready_for_review_jobs}</span>
            <span className="metric-box-sub">Awaiting human sign-off</span>
          </div>
          <div className="metric-box">
            <span className="metric-box-label">Approved Proposals</span>
            <span className="metric-box-val" style={{ color: 'var(--emerald-600)' }}>{summary.approved_revisions}</span>
            <span className="metric-box-sub">Human validated & accepted</span>
          </div>
          <div className="metric-box">
            <span className="metric-box-label">Audit Validations</span>
            <div style={{ display: 'flex', gap: 6, marginTop: 4, fontSize: '0.75rem' }}>
              <span style={{ color: '#10b981' }}>{summary.validation_outcomes.passed || 0} passed</span>
              <span>&bull;</span>
              <span style={{ color: '#f59e0b' }}>{summary.validation_outcomes.passed_with_warnings || 0} warn</span>
              <span>&bull;</span>
              <span style={{ color: '#ef4444' }}>{summary.validation_outcomes.failed || 0} fail</span>
            </div>
            <span className="metric-box-sub">Independent Agent C checks</span>
          </div>
        </div>
      )}

      {/* Main Workspace Split: Left Queue, Right Review Panel */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedJob ? '360px 1fr' : '1fr', gap: 20, marginTop: 20 }}>
        {/* Remediation Queue Column */}
        <div className="table-card">
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Wrench size={17} color="var(--primary-600)" />
              <span>Remediation Queue</span>
              <span className="card-badge mono" style={{ fontSize: '0.72rem' }}>{totalJobs}</span>
            </h3>
            {selectedJob && (
              <button
                className="secondary-btn"
                style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                onClick={() => setSelectedJob(null)}
              >
                Expand List
              </button>
            )}
          </div>

          {/* Filters Bar */}
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <div style={{ position: 'relative', flex: 1 }}>
                <Search size={14} style={{ position: 'absolute', left: 10, top: 10, color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Filter Document ID..."
                  value={searchDocId}
                  onChange={(e) => setSearchDocId(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '6px 10px 6px 30px',
                    borderRadius: 6,
                    border: '1px solid var(--border-color)',
                    fontSize: '0.82rem',
                    backgroundColor: 'var(--bg-card)',
                    color: 'var(--text-primary)',
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                style={{
                  flex: 1,
                  padding: '5px 8px',
                  borderRadius: 6,
                  border: '1px solid var(--border-color)',
                  fontSize: '0.78rem',
                  backgroundColor: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                }}
              >
                <option value="all">All Job Statuses</option>
                <option value="ready_for_review">Ready For Review</option>
                <option value="planning">Planning</option>
                <option value="drafting">Drafting</option>
                <option value="completed">Completed</option>
                <option value="failed">Blocked/Failed</option>
              </select>

              <select
                value={valFilter}
                onChange={(e) => setValFilter(e.target.value)}
                style={{
                  flex: 1,
                  padding: '5px 8px',
                  borderRadius: 6,
                  border: '1px solid var(--border-color)',
                  fontSize: '0.78rem',
                  backgroundColor: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                }}
              >
                <option value="all">All Validation</option>
                <option value="passed">Passed</option>
                <option value="passed_with_warnings">With Warnings</option>
                <option value="failed">Failed</option>
                <option value="needs_human_review">Needs Review</option>
              </select>
            </div>
          </div>

          {/* Job Items List */}
          <div style={{ maxHeight: 680, overflowY: 'auto' }}>
            {loading ? (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
                <RefreshCw size={24} className="spin-icon" style={{ margin: '0 auto 12px' }} />
                <span>Loading remediation queue...</span>
              </div>
            ) : jobs.length === 0 ? (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
                <Wrench size={32} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
                <p>No remediation jobs found.</p>
                <button
                  className="primary-btn"
                  style={{ marginTop: 12, fontSize: '0.8rem' }}
                  onClick={() => setShowCreateModal(true)}
                >
                  Create First Job
                </button>
              </div>
            ) : (
              jobs.map((job) => {
                const isSelected = selectedJob?.remediation_id === job.remediation_id;
                const latestRev = job.draft_revisions && job.draft_revisions.length > 0
                  ? job.draft_revisions[job.draft_revisions.length - 1]
                  : null;

                return (
                  <div
                    key={job.remediation_id}
                    onClick={() => openJobDetail(job.remediation_id)}
                    style={{
                      padding: '12px 16px',
                      borderBottom: '1px solid var(--border-color)',
                      cursor: 'pointer',
                      backgroundColor: isSelected ? 'var(--primary-50)' : 'transparent',
                      borderLeft: isSelected ? '4px solid var(--primary-600)' : '4px solid transparent',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span
                        className="mono"
                        style={{
                          fontWeight: 700,
                          fontSize: '0.82rem',
                          color: 'var(--primary-600)',
                          textDecoration: onSelectDocumentId ? 'underline' : 'none',
                        }}
                        onClick={(e) => {
                          if (onSelectDocumentId) {
                            e.stopPropagation();
                            onSelectDocumentId(job.document_id);
                          }
                        }}
                        title={onSelectDocumentId ? 'View explainable scoring details' : undefined}
                      >
                        {job.document_id}
                      </span>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        {job.risk_score_at_creation != null && (
                          <span className="card-badge mono" style={{ fontSize: '0.7rem' }}>
                            Score: {job.risk_score_at_creation}
                          </span>
                        )}
                        <span className={`evidence-badge status-${job.status}`}>
                          {job.status.replace(/_/g, ' ')}
                        </span>
                      </div>
                    </div>

                    <div style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: 4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {job.document_title}
                    </div>

                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 2, lineClamp: 2, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {job.plan?.primary_objective || job.error_summary || 'Awaiting planning review'}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      <span>Revisions: {job.draft_revisions.length}</span>
                      {latestRev ? (
                        <div style={{ display: 'flex', gap: 6 }}>
                          {getValidationBadge(latestRev.validation_status)}
                          {getReviewBadge(latestRev.review_status)}
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>No draft generated</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Side-by-Side Review & Validation Workspace */}
        {selectedJob ? (
          <div className="table-card" style={{ display: 'flex', flexDirection: 'column' }}>
            {/* Active Job Header */}
            <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'var(--bg-app)' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span className="mono" style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--primary-600)' }}>
                    {selectedJob.document_id}
                  </span>
                  <span style={{ color: 'var(--border-color)' }}>&bull;</span>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Job: {selectedJob.remediation_id}</span>
                  <span style={{ color: 'var(--border-color)' }}>&bull;</span>
                  {selectedJob.risk_score_at_creation != null && (
                    <span className="card-badge" style={{ backgroundColor: 'var(--rose-50)', color: 'var(--rose-600)', fontSize: '0.7rem' }}>
                      Freshness Risk: {selectedJob.risk_score_at_creation}/100
                    </span>
                  )}
                </div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: 4, color: 'var(--text-primary)' }}>
                  {selectedJob.document_title}
                </h3>
              </div>

              {/* Revision Selector & Actions */}
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                {selectedJob.draft_revisions.length > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--bg-card)', padding: '4px 8px', borderRadius: 6, border: '1px solid var(--border-color)' }}>
                    <GitBranch size={15} color="var(--primary-600)" />
                    <select
                      value={activeRevisionIndex}
                      onChange={(e) => {
                        const idx = Number(e.target.value);
                        setActiveRevisionIndex(idx);
                        setActiveRevision(selectedJob.draft_revisions[idx]);
                      }}
                      style={{ border: 'none', background: 'transparent', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)', outline: 'none' }}
                    >
                      {selectedJob.draft_revisions.map((rev, idx) => (
                        <option key={rev.revision_id} value={idx}>
                          Revision v{rev.revision_number} ({rev.review_status})
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* If draft does not exist or user wants initial draft */}
                {selectedJob.draft_revisions.length === 0 ? (
                  <button
                    className="primary-btn"
                    onClick={handleGenerateDraft}
                    disabled={isGeneratingDraft || !selectedJob.plan?.has_sufficient_content}
                    style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                  >
                    <Sparkles size={16} className={isGeneratingDraft ? 'spin-icon' : ''} />
                    <span>{isGeneratingDraft ? 'Generating Draft...' : 'Generate AI Revision Draft'}</span>
                  </button>
                ) : (
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      className="secondary-btn"
                      onClick={handleValidateRevision}
                      disabled={isValidatingDraft}
                      style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem' }}
                      title="Run independent Agent C validator check"
                    >
                      <CheckCircle size={15} color="#10b981" />
                      <span>{isValidatingDraft ? 'Validating...' : 'Re-Validate'}</span>
                    </button>
                    <button
                      className="secondary-btn"
                      onClick={() => setShowRegenModal(true)}
                      style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem' }}
                    >
                      <RotateCcw size={15} />
                      <span>Regenerate (v{selectedJob.draft_revisions.length + 1})</span>
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Error Banner */}
            {actionError && (
              <div style={{ backgroundColor: 'var(--rose-50)', color: 'var(--rose-600)', padding: '10px 20px', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 8, borderBottom: '1px solid var(--border-color)' }}>
                <XCircle size={16} />
                <span>{actionError}</span>
              </div>
            )}

            {/* If blocked due to missing content */}
            {!selectedJob.plan?.has_sufficient_content && (
              <div style={{ padding: 30, backgroundColor: 'rgba(239, 68, 68, 0.05)', margin: 20, borderRadius: 8, border: '1px solid var(--rose-200)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--rose-600)', fontWeight: 600 }}>
                  <ShieldAlert size={20} />
                  <span>Remediation Blocked: Source document body text is missing</span>
                </div>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginTop: 8 }}>
                  The inventory dataset contains metadata and telemetry signals, but does not include full document text. Enter or upload the source text below to enable evidence-grounded rewriting.
                </p>
                <div style={{ marginTop: 14 }}>
                  <textarea
                    rows={4}
                    placeholder="Paste full document text or policy manual content..."
                    value={ingestText}
                    onChange={(e) => setIngestText(e.target.value)}
                    style={{ width: '100%', padding: 12, borderRadius: 6, border: '1px solid var(--border-color)', fontSize: '0.85rem', fontFamily: 'monospace' }}
                  />
                  <button
                    className="primary-btn"
                    onClick={async () => {
                      if (!ingestText.trim()) return;
                      await ingestDocumentContent(selectedJob.document_id, ingestText.trim());
                      // Reload job
                      openJobDetail(selectedJob.remediation_id);
                    }}
                    style={{ marginTop: 8 }}
                  >
                    Ingest Source Text & Re-Plan
                  </button>
                </div>
              </div>
            )}

            {/* Structured Remediation Plan Bar (Agent A) */}
            {selectedJob.plan && selectedJob.plan.has_sufficient_content && (
              <div style={{ padding: '12px 24px', backgroundColor: 'var(--bg-card)', borderBottom: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className="card-badge" style={{ backgroundColor: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6', fontWeight: 600, fontSize: '0.72rem' }}>
                      Agent A Plan
                    </span>
                    <span style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      Objective: {selectedJob.plan.primary_objective}
                    </span>
                  </div>
                  <span className="coverage-pill" style={{ fontSize: '0.72rem' }}>
                    Risk: {selectedJob.plan.risk_assessment}
                  </span>
                </div>

                {selectedJob.plan.findings_to_address.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                    {selectedJob.plan.findings_to_address.map((f, i) => (
                      <span key={i} className="card-badge" style={{ fontSize: '0.72rem', backgroundColor: 'var(--bg-app)' }}>
                        &bull; {f}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Revision Workspace: Side-by-Side & Validation */}
            {activeRevision ? (
              <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
                {/* Independent Validation Banner (Agent C) */}
                {activeRevision.validation_result && (
                  <div
                    style={{
                      padding: '12px 24px',
                      backgroundColor:
                        activeRevision.validation_result.validation_status === 'passed'
                          ? 'rgba(16, 185, 129, 0.08)'
                          : activeRevision.validation_result.validation_status === 'failed'
                          ? 'rgba(239, 68, 68, 0.08)'
                          : 'rgba(245, 158, 11, 0.08)',
                      borderBottom: '1px solid var(--border-color)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                          Validator Outcome:
                        </span>
                        {getValidationBadge(activeRevision.validation_result.validation_status)}
                      </div>
                      <span style={{ fontSize: '0.84rem', color: 'var(--text-primary)' }}>
                        {activeRevision.validation_result.validation_summary}
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: 12, fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                      <span>
                        Coverage: <strong>{activeRevision.validation_result.evidence_coverage_percent}%</strong>
                      </span>
                      <span>&bull;</span>
                      <span>
                        Supported: <strong>{activeRevision.validation_result.supported_claims_count}</strong>
                      </span>
                    </div>
                  </div>
                )}

                {/* Side-by-Side Content Comparison */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', flex: 1, minHeight: 380, borderBottom: '1px solid var(--border-color)' }}>
                  {/* Left: Original Version (Immutable) */}
                  <div style={{ borderRight: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-card)' }}>
                    <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'var(--bg-app)' }}>
                      <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <FileText size={14} />
                        Original Source Document (Immutable)
                      </span>
                      <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {activeRevision.original_content.length} chars
                      </span>
                    </div>
                    <div style={{ padding: 16, overflowY: 'auto', flex: 1, fontSize: '0.88rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', color: 'var(--text-primary)', fontFamily: 'var(--font-sans)' }}>
                      {activeRevision.original_content}
                    </div>
                  </div>

                  {/* Right: Proposed Revision */}
                  <div style={{ display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-card)' }}>
                    <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'var(--bg-app)' }}>
                      <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--primary-600)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Sparkles size={14} />
                        Proposed Revision (Draft v{activeRevision.revision_number})
                      </span>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        {getReviewBadge(activeRevision.review_status)}
                        <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                          {activeRevision.proposed_content.length} chars
                        </span>
                      </div>
                    </div>
                    <div style={{ padding: 16, overflowY: 'auto', flex: 1, fontSize: '0.88rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', color: 'var(--text-primary)', fontFamily: 'var(--font-sans)' }}>
                      {activeRevision.proposed_content}
                    </div>
                  </div>
                </div>

                {/* Substantive Change Provenance & Evidence Linkages */}
                <div style={{ padding: '16px 24px', backgroundColor: 'var(--bg-card)', borderBottom: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span>Substantive Modifications & Evidence Citations</span>
                      <span className="card-badge mono" style={{ fontSize: '0.72rem' }}>
                        {activeRevision.changes.length} Changes
                      </span>
                    </h4>
                  </div>

                  {activeRevision.changes.length === 0 ? (
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      No substantive modifications detected in this revision.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {activeRevision.changes.map((chg, idx) => (
                        <div
                          key={chg.change_id || idx}
                          style={{
                            padding: 12,
                            borderRadius: 6,
                            border: '1px solid var(--border-color)',
                            backgroundColor: chg.validation_outcome === 'supported' ? 'rgba(16, 185, 129, 0.04)' : 'rgba(239, 68, 68, 0.04)',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                              <span className="mono" style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                                {chg.change_id}
                              </span>
                              <span className="card-badge" style={{ fontSize: '0.7rem', textTransform: 'uppercase' }}>
                                {chg.change_type}
                              </span>
                            </div>
                            <span className={`evidence-badge status-${chg.validation_outcome === 'supported' ? 'confirmed' : 'failed'}`}>
                              {chg.validation_outcome}
                            </span>
                          </div>

                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: '0.82rem', marginTop: 4 }}>
                            <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.08)', padding: 8, borderRadius: 4, color: 'var(--rose-700)', textDecoration: 'line-through' }}>
                              {chg.original_text}
                            </div>
                            <div style={{ backgroundColor: 'rgba(16, 185, 129, 0.08)', padding: 8, borderRadius: 4, color: 'var(--emerald-700)', fontWeight: 500 }}>
                              {chg.proposed_text}
                            </div>
                          </div>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                            <span><strong>Reason:</strong> {chg.reason}</span>
                            {chg.supporting_evidence_refs.length > 0 && (
                              <div style={{ display: 'flex', gap: 6 }}>
                                {chg.supporting_evidence_refs.map((ref, rIdx) => (
                                  <span key={rIdx} className="card-badge mono" style={{ fontSize: '0.68rem', backgroundColor: 'var(--bg-app)' }}>
                                    {ref}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Review Notes / Audit Decision Bar */}
                {activeRevision.review_note && (
                  <div style={{ padding: '12px 24px', backgroundColor: 'var(--bg-app)', borderBottom: '1px solid var(--border-color)', fontSize: '0.82rem' }}>
                    <strong>Review Note by {activeRevision.reviewed_by || 'Reviewer'}:</strong> {activeRevision.review_note}
                    {activeRevision.reviewed_at && <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>({new Date(activeRevision.reviewed_at).toLocaleString()})</span>}
                  </div>
                )}

                {/* Review Actions Footer (Human Approval Controls) */}
                <div style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'var(--bg-card)' }}>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Human-in-the-loop audit: Approvals preserve original documents and maintain complete audit traceability.
                  </div>

                  {activeRevision.review_status === 'pending' || activeRevision.review_status === 'changes_requested' ? (
                    <div style={{ display: 'flex', gap: 10 }}>
                      <button
                        className="secondary-btn"
                        style={{ color: 'var(--rose-600)', borderColor: 'var(--rose-200)' }}
                        onClick={() => setReviewAction('reject')}
                      >
                        Reject Draft
                      </button>
                      <button
                        className="secondary-btn"
                        style={{ color: 'var(--amber-600)', borderColor: 'var(--amber-200)' }}
                        onClick={() => setReviewAction('request_changes')}
                      >
                        Request Changes
                      </button>
                      <button
                        className="primary-btn"
                        style={{ backgroundColor: '#10b981', borderColor: '#10b981' }}
                        onClick={() => setReviewAction('approve')}
                      >
                        <Check size={16} style={{ marginRight: 6 }} />
                        Approve Revision
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: '0.84rem', fontWeight: 600 }}>
                        Terminal Review State: {activeRevision.review_status.toUpperCase()}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
                <Sparkles size={40} style={{ margin: '0 auto 16px', opacity: 0.3 }} />
                <h4 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Ready to Synthesize Document Revision
                </h4>
                <p style={{ maxWidth: 450, margin: '8px auto 20px', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                  Click below to activate Agent B (Revision Agent) and Agent C (Validation Agent) to draft targeted, evidence-backed improvements.
                </p>
                <button
                  className="primary-btn"
                  onClick={handleGenerateDraft}
                  disabled={isGeneratingDraft || !selectedJob.plan?.has_sufficient_content}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 20px' }}
                >
                  <Sparkles size={16} className={isGeneratingDraft ? 'spin-icon' : ''} />
                  <span>{isGeneratingDraft ? 'Generating Draft...' : 'Generate AI Revision Draft'}</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="table-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 60, color: 'var(--text-muted)' }}>
            <Wrench size={48} style={{ opacity: 0.25, marginBottom: 16 }} />
            <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Select a Remediation Job
            </h3>
            <p style={{ maxWidth: 450, textAlign: 'center', fontSize: '0.88rem', color: 'var(--text-secondary)', marginTop: 8 }}>
              Select an existing document from the queue on the left to inspect side-by-side revisions, validation provenance, or start a new remediation job.
            </p>
            <button
              className="primary-btn"
              onClick={() => setShowCreateModal(true)}
              style={{ marginTop: 20 }}
            >
              Start New Remediation Job
            </button>
          </div>
        )}
      </div>

      {/* Modal: Human Review Action (Approve / Reject / Request Changes) */}
      {reviewAction && (
        <div className="modal-backdrop" onClick={() => setReviewAction(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div className="modal-header">
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, textTransform: 'capitalize' }}>
                {reviewAction === 'approve'
                  ? 'Confirm Revision Approval'
                  : reviewAction === 'reject'
                  ? 'Reject Document Revision'
                  : 'Request Further Changes'}
              </h3>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
                {reviewAction === 'approve'
                  ? 'Approving records acceptance within FreshGuard AI audit history. The original document is preserved immutable and no external repository is overwritten.'
                  : reviewAction === 'reject'
                  ? 'Rejection requires a documented reason for why this proposed revision is unsuitable.'
                  : 'Specify feedback points for the revision agent to incorporate into the next draft version.'}
              </p>

              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Reviewer Name
                </label>
                <input
                  type="text"
                  value={reviewerName}
                  onChange={(e) => setReviewName(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border-color)', fontSize: '0.85rem' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Review Notes {reviewAction !== 'approve' && <span style={{ color: 'var(--rose-600)' }}>* (Required)</span>}
                </label>
                <textarea
                  rows={3}
                  placeholder={
                    reviewAction === 'approve'
                      ? 'Optional acceptance remarks...'
                      : reviewAction === 'reject'
                      ? 'Detailed reason for rejection...'
                      : 'Specific guidelines for revision v2...'
                  }
                  value={reviewNote}
                  onChange={(e) => setReviewNote(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border-color)', fontSize: '0.85rem' }}
                />
              </div>
            </div>
            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button className="secondary-btn" onClick={() => setReviewAction(null)}>
                Cancel
              </button>
              <button
                className="primary-btn"
                style={{
                  backgroundColor:
                    reviewAction === 'approve' ? '#10b981' : reviewAction === 'reject' ? '#ef4444' : '#f59e0b',
                  borderColor:
                    reviewAction === 'approve' ? '#10b981' : reviewAction === 'reject' ? '#ef4444' : '#f59e0b',
                }}
                disabled={reviewSubmitting || (reviewAction !== 'approve' && !reviewNote.trim())}
                onClick={handleReviewSubmit}
              >
                {reviewSubmitting ? 'Recording...' : `Confirm ${reviewAction.replace(/_/g, ' ')}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Regenerate Draft with Feedback */}
      {showRegenModal && (
        <div className="modal-backdrop" onClick={() => setShowRegenModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div className="modal-header">
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>
                Regenerate Revision with Auditor Feedback
              </h3>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
                Provide specific guidance for Agent B to address in Revision v{(selectedJob?.draft_revisions.length || 0) + 1}. All previous draft versions will be archived in the revision history.
              </p>
              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Feedback & Focus Areas
                </label>
                <textarea
                  rows={4}
                  placeholder="e.g. Ensure the flight reimbursement deadline is explicitly stated as 30 calendar days..."
                  value={regenFeedback}
                  onChange={(e) => setRegenFeedback(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border-color)', fontSize: '0.85rem' }}
                />
              </div>
            </div>
            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button className="secondary-btn" onClick={() => setShowRegenModal(false)}>
                Cancel
              </button>
              <button
                className="primary-btn"
                disabled={reviewSubmitting}
                onClick={handleRegenerateSubmit}
              >
                {reviewSubmitting ? 'Regenerating...' : 'Generate New Revision'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Create New Remediation Job */}
      {showCreateModal && (
        <div className="modal-backdrop" onClick={() => setShowCreateModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 580 }}>
            <div className="modal-header">
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>
                Initiate AI Document Remediation
              </h3>
            </div>
            <div className="modal-body">
              <div style={{ marginBottom: 14 }}>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Target Document
                </label>
                <select
                  value={selectedCandidateId}
                  onChange={(e) => setSelectedCandidateId(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border-color)', fontSize: '0.85rem', backgroundColor: 'var(--bg-card)', color: 'var(--text-primary)' }}
                >
                  {candidateDocs.map((doc) => (
                    <option key={doc.content_id} value={doc.content_id}>
                      {doc.content_id} - {doc.title} (Score: {doc.calculated_score})
                    </option>
                  ))}
                </select>
              </div>

              {/* Content Availability Indicator */}
              <div style={{ marginBottom: 14, padding: 12, borderRadius: 6, backgroundColor: contentAvail ? 'rgba(16, 185, 129, 0.08)' : 'rgba(245, 158, 11, 0.08)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.82rem', fontWeight: 600, color: contentAvail ? '#10b981' : '#f59e0b' }}>
                  {contentAvail ? <CheckCircle size={15} /> : <AlertTriangle size={15} />}
                  <span>{contentAvail ? 'Document Text Available in Content Service' : 'Document Text Not Ingested (Optional Upload Below)'}</span>
                </div>
                {!contentAvail && (
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                    Remediation requires real document content. You can paste or upload the source text now.
                  </p>
                )}
              </div>

              {/* Optional Text Ingestion Field */}
              <div style={{ marginBottom: 14 }}>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Document Text / Body (Source Content)
                </label>
                <textarea
                  rows={4}
                  placeholder="Paste or edit the full document content here..."
                  value={ingestText}
                  onChange={(e) => setIngestText(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border-color)', fontSize: '0.82rem', fontFamily: 'monospace' }}
                />
                {!contentAvail && ingestText.trim() && (
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={handleIngestTextInline}
                    disabled={isIngestingText}
                    style={{ marginTop: 6, fontSize: '0.78rem', padding: '4px 10px' }}
                  >
                    {isIngestingText ? 'Saving text...' : 'Save Ingested Text Now'}
                  </button>
                )}
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Remediation Objective (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Harmonize domestic flight expense caps with handbook standard"
                  value={customObjective}
                  onChange={(e) => setCustomObjective(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border-color)', fontSize: '0.85rem' }}
                />
              </div>
            </div>
            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button className="secondary-btn" onClick={() => setShowCreateModal(false)}>
                Cancel
              </button>
              <button
                className="primary-btn"
                disabled={createJobSubmitting}
                onClick={handleCreateJob}
              >
                {createJobSubmitting ? 'Creating Job...' : 'Create Remediation Job'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
