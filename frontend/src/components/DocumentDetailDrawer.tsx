import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { DocumentRecord } from '../types';

interface DocumentDetailDrawerProps {
  document: DocumentRecord | null;
  onClose: () => void;
}

export const DocumentDetailDrawer: React.FC<DocumentDetailDrawerProps> = ({
  document,
  onClose,
}) => {
  // Listen for Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!document) return null;

  const renderValue = (val: any) => {
    if (val === null || val === undefined || val === '') {
      return <span style={{ color: 'var(--text-light)', fontStyle: 'italic' }}>Not provided</span>;
    }
    return String(val);
  };

  return (
    <div className="drawer-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="drawer-header">
          <div className="drawer-title-section">
            <span className="drawer-content-id">{document.content_id}</span>
            <h2 className="drawer-title">{document.title || 'Untitled Document'}</h2>
            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              <span className="badge-tag badge-platform">{document.platform}</span>
              <span className="badge-tag badge-type">{document.content_type}</span>
            </div>
          </div>
          <button
            className="btn-close"
            onClick={onClose}
            title="Close inspector (Esc)"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="drawer-body">
          {/* Section 1: Core Metadata */}
          <div className="detail-section">
            <div className="detail-section-title">Core Metadata</div>
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-item-label">Subject Area / Domain</span>
                <span className="detail-item-val">{renderValue(document.subject_area)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-item-label">Author / Maintainer</span>
                <span className="detail-item-val">{renderValue(document.author)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-item-label">Source Platform</span>
                <span className="detail-item-val">{document.platform}</span>
              </div>
              <div className="detail-item">
                <span className="detail-item-label">Content Classification</span>
                <span className="detail-item-val">{document.content_type}</span>
              </div>
            </div>
          </div>

          {/* Section 2: Lifecycle & Engagement */}
          <div className="detail-section">
            <div className="detail-section-title">Lifecycle & Engagement</div>
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-item-label">Created Date</span>
                <span className="detail-item-val mono">{renderValue(document.created_date)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-item-label">Last Updated</span>
                <span className="detail-item-val mono">{renderValue(document.last_updated)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-item-label">Last Reviewed</span>
                <span className="detail-item-val mono">{renderValue(document.last_reviewed)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-item-label">90-Day Page Views</span>
                <span className="detail-item-val mono">
                  {document.page_views_90d !== null
                    ? document.page_views_90d.toLocaleString()
                    : 'Not provided'}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-item-label">Inbound References</span>
                <span className="detail-item-val mono">
                  {document.linked_from_count !== null
                    ? `${document.linked_from_count} documents`
                    : 'Not provided'}
                </span>
              </div>
            </div>
          </div>

          {/* Section 3: Risk Indicators & Baseline Action */}
          <div className="detail-section">
            <div className="detail-section-title">Recorded Freshness Signals</div>
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-item-label">Deprecated Tool References</span>
                <span className="detail-item-val">
                  {document.mentions_deprecated_tool ? (
                    <span className="flag-badge flag-yes">Yes (Flagged)</span>
                  ) : (
                    <span className="flag-badge" style={{ backgroundColor: 'var(--emerald-50)', color: 'var(--emerald-600)' }}>
                      Clean
                    </span>
                  )}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-item-label">Broken Links Flag</span>
                <span className="detail-item-val">
                  {document.has_broken_links ? (
                    <span className="flag-badge flag-yes">Yes (Dead URLs)</span>
                  ) : (
                    <span className="flag-badge" style={{ backgroundColor: 'var(--emerald-50)', color: 'var(--emerald-600)' }}>
                      Intact
                    </span>
                  )}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-item-label">CSV Reference Score</span>
                <span className="detail-item-val mono">
                  {document.staleness_score !== null ? document.staleness_score.toFixed(2) : 'Not provided'}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-item-label">Baseline Action</span>
                <span className="detail-item-val">
                  {document.recommended_action || 'Not provided'}
                </span>
              </div>
            </div>
          </div>

          {/* Section 4: Available Evidence for Phase 3 */}
          <div className="detail-section">
            <div className="detail-section-title">Available Evidence for Freshness Engine</div>
            <div className="evidence-box">
              <div className="evidence-row">
                <span>Signal: Age since last update</span>
                <strong className="mono">{document.last_updated || 'Unknown'}</strong>
              </div>
              <div className="evidence-row">
                <span>Signal: Age since review</span>
                <strong className="mono">{document.last_reviewed || 'Unknown'}</strong>
              </div>
              <div className="evidence-row">
                <span>Signal: Traffic & Criticality</span>
                <strong className="mono">{document.page_views_90d ?? 0} views / {document.linked_from_count ?? 0} links</strong>
              </div>
              <div className="evidence-row">
                <span>Signal: Deprecated Tool Reference</span>
                <strong style={{ color: document.mentions_deprecated_tool ? 'var(--rose-600)' : 'var(--emerald-600)' }}>
                  {document.mentions_deprecated_tool ? 'Positive Flag' : 'Negative'}
                </strong>
              </div>
              <div className="evidence-row">
                <span>Signal: Broken Hyperlinks</span>
                <strong style={{ color: document.has_broken_links ? 'var(--rose-600)' : 'var(--emerald-600)' }}>
                  {document.has_broken_links ? 'Positive Flag' : 'Negative'}
                </strong>
              </div>
            </div>
          </div>

          {/* Honest Transparency Notice */}
          <div className="info-note">
            <strong>Full Document Text Notice:</strong> Raw document body text is not stored in the <code>ps11_content_inventory.csv</code> dataset. Phase 3 freshness scoring and Phase 4 audits will evaluate the validated metadata signals and structural attributes demonstrated above.
          </div>
        </div>
      </div>
    </div>
  );
};
