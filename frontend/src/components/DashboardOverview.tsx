import React from 'react';
import {
  FileText,
  Layers,
  Link2Off,
  AlertTriangle,
  CalendarX2,
  FileSearch,
  PieChart,
  BarChart3,
  Sliders,
  ShieldCheck,
} from 'lucide-react';
import { DashboardSummaryResponse, DashboardDistributionsResponse } from '../types';

interface DashboardOverviewProps {
  summary: DashboardSummaryResponse | null;
  distributions: DashboardDistributionsResponse | null;
  loading: boolean;
  onNavigateToInventory: () => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  summary,
  distributions,
  loading,
  onNavigateToInventory,
}) => {
  return (
    <div>
      {/* 6 Real KPI Cards */}
      <div className="kpi-grid">
        {/* KPI 1: Total Indexed Documents */}
        <div className="kpi-card accent-blue" id="kpi-total-docs">
          <div className="kpi-header">
            <span className="kpi-label">Total Documents</span>
            <FileText size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value">
            {loading ? '...' : (summary?.total_documents ?? 0).toLocaleString()}
          </div>
          <div className="kpi-hint">Indexed knowledge records</div>
        </div>

        {/* KPI 2: Distinct Platforms */}
        <div className="kpi-card accent-indigo" id="kpi-distinct-platforms">
          <div className="kpi-header">
            <span className="kpi-label">Source Platforms</span>
            <Layers size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value">
            {loading ? '...' : summary?.distinct_platforms ?? 0}
          </div>
          <div className="kpi-hint">SharePoint, Confluence, etc.</div>
        </div>

        {/* KPI 3: Broken Links Detected */}
        <div className="kpi-card accent-rose" id="kpi-broken-links">
          <div className="kpi-header">
            <span className="kpi-label">Broken Link Flags</span>
            <Link2Off size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--rose-600)' }}>
            {loading ? '...' : summary?.broken_links ?? 0}
          </div>
          <div className="kpi-hint">
            {summary && summary.total_documents > 0
              ? `${Math.round((summary.broken_links / summary.total_documents) * 100)}% of total inventory`
              : 'Dead URL references'}
          </div>
        </div>

        {/* KPI 4: Deprecated Tool Mentions */}
        <div className="kpi-card accent-amber" id="kpi-deprecated-tools">
          <div className="kpi-header">
            <span className="kpi-label">Deprecated Tools</span>
            <AlertTriangle size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--amber-600)' }}>
            {loading ? '...' : summary?.deprecated_references ?? 0}
          </div>
          <div className="kpi-hint">
            {summary && summary.total_documents > 0
              ? `${Math.round((summary.deprecated_references / summary.total_documents) * 100)}% of total inventory`
              : 'References retired software'}
          </div>
        </div>

        {/* KPI 5: Missing Update Dates */}
        <div className="kpi-card accent-amber" id="kpi-missing-dates">
          <div className="kpi-header">
            <span className="kpi-label">Missing Update Date</span>
            <CalendarX2 size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value">
            {loading ? '...' : summary?.missing_update_dates ?? 0}
          </div>
          <div className="kpi-hint">No last_updated timestamp recorded</div>
        </div>

        {/* KPI 6: Metadata Completeness Issues */}
        <div className="kpi-card accent-emerald" id="kpi-completeness-issues">
          <div className="kpi-header">
            <span className="kpi-label">Metadata Incomplete</span>
            <FileSearch size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value">
            {loading ? '...' : summary?.missing_metadata_count ?? 0}
          </div>
          <div className="kpi-hint">
            {summary?.missing_metadata_count === 0
              ? 'All 200 documents have full core metadata'
              : 'Documents with missing fields'}
          </div>
        </div>
      </div>

      {/* Visual Analytics / Distributions Grid */}
      <div className="distributions-grid">
        {/* Platform Distribution */}
        <div className="card" id="card-platform-distribution">
          <div className="card-header">
            <span className="card-title">
              <PieChart size={17} color="var(--primary-600)" />
              Distribution by Platform
            </span>
            <span className="card-badge">{distributions?.by_platform.length || 0} Platforms</span>
          </div>
          <div className="card-body">
            <div className="dist-list">
              {distributions?.by_platform.map((item) => (
                <div key={item.label} className="dist-item">
                  <div className="dist-label-row">
                    <span className="dist-label">{item.label}</span>
                    <span className="dist-stats">
                      <strong>{item.count}</strong> ({item.percentage}%)
                    </span>
                  </div>
                  <div className="dist-bar-track">
                    <div
                      className="dist-bar-fill"
                      style={{ width: `${Math.min(item.percentage * 2, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Content Type Distribution */}
        <div className="card" id="card-type-distribution">
          <div className="card-header">
            <span className="card-title">
              <BarChart3 size={17} color="var(--indigo-600)" />
              Distribution by Content Type
            </span>
            <span className="card-badge">{distributions?.by_content_type.length || 0} Types</span>
          </div>
          <div className="card-body">
            <div className="dist-list">
              {distributions?.by_content_type.map((item) => (
                <div key={item.label} className="dist-item">
                  <div className="dist-label-row">
                    <span className="dist-label">{item.label}</span>
                    <span className="dist-stats">
                      <strong>{item.count}</strong> ({item.percentage}%)
                    </span>
                  </div>
                  <div className="dist-bar-track">
                    <div
                      className="dist-bar-fill indigo"
                      style={{ width: `${Math.min(item.percentage * 2.5, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Existing Reference Staleness Score Ranges */}
        <div className="card" id="card-reference-score-distribution">
          <div className="card-header">
            <span className="card-title">
              <Sliders size={17} color="var(--amber-600)" />
              Source Reference Score Distribution
            </span>
            <span className="card-badge" style={{ backgroundColor: 'var(--amber-50)', color: 'var(--amber-600)' }}>
              CSV Baseline
            </span>
          </div>
          <div className="card-body">
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 12 }}>
              <em>Note:</em> Preserved from original CSV reference field. The multi-signal decay scoring engine will be computed in Phase 3.
            </div>
            <div className="dist-list">
              {distributions?.by_reference_score.map((item) => {
                let barClass = 'emerald';
                if (item.label.includes('Critical')) barClass = 'rose';
                else if (item.label.includes('High') || item.label.includes('Moderate')) barClass = 'amber';

                return (
                  <div key={item.label} className="dist-item">
                    <div className="dist-label-row">
                      <span className="dist-label">{item.label}</span>
                      <span className="dist-stats">
                        <strong>{item.count}</strong> ({item.percentage}%)
                      </span>
                    </div>
                    <div className="dist-bar-track">
                      <div
                        className={`dist-bar-fill ${barClass}`}
                        style={{ width: `${Math.min(item.percentage * 2.5, 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Signal Integrity Summary */}
        <div className="card" id="card-signals-summary">
          <div className="card-header">
            <span className="card-title">
              <ShieldCheck size={17} color="var(--emerald-600)" />
              Knowledge Signal Integrity
            </span>
            <span className="card-badge">Phase 1 & 2 Signals</span>
          </div>
          <div className="card-body">
            <div className="dist-list">
              <div className="dist-item">
                <div className="dist-label-row">
                  <span className="dist-label">Clean Tool Mentions</span>
                  <span className="dist-stats">
                    {distributions?.by_signals.clean_tool_references ?? 0} docs
                  </span>
                </div>
                <div className="dist-bar-track">
                  <div
                    className="dist-bar-fill emerald"
                    style={{
                      width: summary?.total_documents
                        ? `${Math.round(((distributions?.by_signals.clean_tool_references || 0) / summary.total_documents) * 100)}%`
                        : '0%',
                    }}
                  />
                </div>
              </div>

              <div className="dist-item">
                <div className="dist-label-row">
                  <span className="dist-label">Deprecated Tool Mentions</span>
                  <span className="dist-stats" style={{ color: 'var(--amber-600)' }}>
                    {distributions?.by_signals.deprecated_tool_references ?? 0} docs
                  </span>
                </div>
                <div className="dist-bar-track">
                  <div
                    className="dist-bar-fill amber"
                    style={{
                      width: summary?.total_documents
                        ? `${Math.round(((distributions?.by_signals.deprecated_tool_references || 0) / summary.total_documents) * 100)}%`
                        : '0%',
                    }}
                  />
                </div>
              </div>

              <div className="dist-item">
                <div className="dist-label-row">
                  <span className="dist-label">Healthy / Intact Links</span>
                  <span className="dist-stats">
                    {distributions?.by_signals.intact_links ?? 0} docs
                  </span>
                </div>
                <div className="dist-bar-track">
                  <div
                    className="dist-bar-fill emerald"
                    style={{
                      width: summary?.total_documents
                        ? `${Math.round(((distributions?.by_signals.intact_links || 0) / summary.total_documents) * 100)}%`
                        : '0%',
                    }}
                  />
                </div>
              </div>

              <div className="dist-item">
                <div className="dist-label-row">
                  <span className="dist-label">Broken Links Flagged</span>
                  <span className="dist-stats" style={{ color: 'var(--rose-600)' }}>
                    {distributions?.by_signals.broken_links_detected ?? 0} docs
                  </span>
                </div>
                <div className="dist-bar-track">
                  <div
                    className="dist-bar-fill rose"
                    style={{
                      width: summary?.total_documents
                        ? `${Math.round(((distributions?.by_signals.broken_links_detected || 0) / summary.total_documents) * 100)}%`
                        : '0%',
                    }}
                  />
                </div>
              </div>
            </div>

            <div style={{ marginTop: 18, textAlign: 'right' }}>
              <button
                className="btn-secondary"
                onClick={onNavigateToInventory}
                style={{ fontSize: '0.8rem' }}
              >
                Browse All Documents &rarr;
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
