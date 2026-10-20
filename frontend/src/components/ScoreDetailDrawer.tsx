import React, { useEffect } from 'react';
import {
  X,
  HelpCircle,
  Clock,
  Link2,
  AlertTriangle,
  GitCompare,
  TrendingDown,
} from 'lucide-react';
import { ScoredDocument } from '../types';

interface ScoreDetailDrawerProps {
  document: ScoredDocument | null;
  onClose: () => void;
}

export const ScoreDetailDrawer: React.FC<ScoreDetailDrawerProps> = ({
  document,
  onClose,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!document) return null;

  const renderRiskBadge = (level: string) => {
    const lower = level.toLowerCase();
    let cls = 'low';
    if (lower.includes('critical')) cls = 'critical';
    else if (lower.includes('high')) cls = 'high';
    else if (lower.includes('moderate')) cls = 'moderate';
    else if (lower.includes('insufficient')) cls = 'insufficient';

    return <span className={`risk-badge ${cls}`}>{level}</span>;
  };

  const getSignalIcon = (name: string) => {
    switch (name) {
      case 'document_age':
        return <Clock size={16} color="var(--primary-600)" />;
      case 'broken_links':
        return <Link2 size={16} color="var(--rose-600)" />;
      case 'deprecated_tools':
        return <AlertTriangle size={16} color="var(--amber-600)" />;
      case 'contradictions':
        return <GitCompare size={16} color="#6366f1" />;
      case 'declining_views':
        return <TrendingDown size={16} color="#64748b" />;
      default:
        return <HelpCircle size={16} />;
    }
  };

  const signalsList = Object.values(document.signal_breakdown);

  return (
    <div className="drawer-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 620 }}>
        {/* Header */}
        <div className="drawer-header">
          <div className="drawer-title-section">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="drawer-content-id">{document.content_id}</span>
              {renderRiskBadge(document.risk_level)}
              {document.is_provisional && (
                <span className="coverage-pill" style={{ color: 'var(--amber-600)' }}>
                  Provisional ({document.evidence_coverage}% evidence)
                </span>
              )}
            </div>
            <h2 className="drawer-title">{document.title}</h2>
            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              <span className="badge-tag badge-platform">{document.platform}</span>
              <span className="badge-tag badge-type">{document.content_type}</span>
            </div>
          </div>
          <button
            className="btn-close"
            onClick={onClose}
            title="Close score explanation (Esc)"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Drawer Body */}
        <div className="drawer-body">
          {/* Top Score Summary Banner */}
          <div
            style={{
              backgroundColor: '#f8fafc',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 16,
            }}
          >
            <div>
              <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
                Calculated Freshness-Risk Score
              </span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 4 }}>
                <span style={{ fontSize: '2.2rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1 }}>
                  {document.calculated_score !== null ? document.calculated_score : 'N/A'}
                </span>
                <span style={{ fontSize: '1rem', color: 'var(--text-muted)', fontWeight: 600 }}>/ 100</span>
                {renderRiskBadge(document.risk_level)}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                Earned {document.earned_points.toFixed(0)} of {document.evaluated_max_points.toFixed(0)} points evaluated
              </div>
            </div>

            <div style={{ textAlign: 'right', minWidth: 150 }}>
              <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
                Evidence Completeness
              </span>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary-600)', marginTop: 2 }}>
                {document.evidence_coverage}%
              </div>
              <div className="dist-bar-track" style={{ width: 140, marginTop: 4, height: 6 }}>
                <div
                  className="dist-bar-fill"
                  style={{ width: `${Math.min(document.evidence_coverage, 100)}%` }}
                />
              </div>
            </div>
          </div>

          {/* Plain-Language Formula Explanation */}
          <div className="info-note" style={{ backgroundColor: '#f1f5f9', borderColor: '#cbd5e1', color: '#334155' }}>
            <strong style={{ display: 'block', marginBottom: 2 }}>Score Calculation Formula:</strong>
            <code>
              Normalized Score = ({document.earned_points.toFixed(0)} earned pts / {document.evaluated_max_points.toFixed(0)} evaluated max) &times; 100 ={' '}
              <strong>{document.calculated_score !== null ? document.calculated_score : 'Unavailable'}</strong>
            </code>
            <p style={{ marginTop: 4, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {document.is_provisional
                ? 'Score is marked provisional because contradiction checks (Phase 5) and view trend baselines are pending evaluation.'
                : 'All applicable signal evidence has been evaluated.'}
            </p>
          </div>

          {/* Priority Remediation Rank */}
          <div className="detail-section">
            <div className="detail-section-title">Remediation Prioritization</div>
            <div className="evidence-box">
              <div className="evidence-row">
                <span>Priority Rank</span>
                <strong style={{ color: document.priority_rank <= 2 ? 'var(--rose-600)' : 'var(--text-primary)' }}>
                  {document.priority_label}
                </strong>
              </div>
              <div className="evidence-row">
                <span>Priority Decision Reason</span>
                <span>{document.priority_explanation}</span>
              </div>
              <div className="evidence-row">
                <span>Top Risk Factor(s)</span>
                <div>
                  {document.top_contributing_factors.map((factor, idx) => (
                    <div key={idx} style={{ fontWeight: 500 }}>
                      &bull; {factor}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Granular Signal Breakdown */}
          <div className="detail-section">
            <div className="detail-section-title">Individual Signal Score Breakdown</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {signalsList.map((sig) => {
                const isEvaluated = sig.status === 'evaluated';
                const hasPoints = sig.actual_points !== null && sig.actual_points > 0;

                return (
                  <div
                    key={sig.signal_name}
                    className={`signal-card ${isEvaluated ? 'evaluated' : 'unknown'}`}
                  >
                    <div className="signal-card-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        {getSignalIcon(sig.signal_name)}
                        <span className="signal-name">{sig.display_name}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span
                          className="mono"
                          style={{
                            fontWeight: 700,
                            fontSize: '0.825rem',
                            color: hasPoints ? 'var(--rose-600)' : isEvaluated ? 'var(--emerald-600)' : 'var(--text-muted)',
                          }}
                        >
                          {isEvaluated ? `${sig.actual_points} / ${sig.max_points} pts` : `0 / ${sig.max_points} pts`}
                        </span>
                        <span className={`signal-status-pill ${sig.status}`}>{sig.status}</span>
                      </div>
                    </div>

                    <div style={{ marginTop: 2 }}>
                      <span className="signal-evidence">Evidence: {sig.evidence}</span>
                    </div>

                    <p className="signal-explanation">{sig.explanation}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Recommended Next Action */}
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
              <strong>Next Action:</strong> {document.recommended_action}
            </div>
          </div>

          {/* Comparison with CSV Baseline */}
          <div className="detail-section">
            <div className="detail-section-title">Reference Baseline Comparison</div>
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-item-label">Source CSV Staleness Score</span>
                <span className="detail-item-val mono">
                  {document.reference_staleness_score != null ? document.reference_staleness_score.toFixed(2) : 'N/A'}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-item-label">Source Recommended Action</span>
                <span className="detail-item-val">
                  {document.source_recommended_action || 'None'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
