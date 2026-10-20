import React from 'react';
import { RefreshCw, Server, AlertCircle } from 'lucide-react';

interface TopBarProps {
  activeTab: 'dashboard' | 'inventory' | 'audit' | 'evidence' | 'contradictions' | 'remediation';
  backendOnline: boolean | null;
  isRefreshing: boolean;
  onRefresh: () => void;
  lastChecked?: string;
}

export const TopBar: React.FC<TopBarProps> = ({
  activeTab,
  backendOnline,
  isRefreshing,
  onRefresh,
  lastChecked,
}) => {
  const getTitles = () => {
    switch (activeTab) {
      case 'dashboard':
        return {
          title: 'Knowledge Health Dashboard',
          subtitle: 'Real-time KPI metrics and knowledge distribution derived from enterprise inventory',
        };
      case 'inventory':
        return {
          title: 'Content Inventory & Catalog',
          subtitle: 'Explore, filter, and inspect document metadata across enterprise platforms',
        };
      case 'audit':
        return {
          title: 'Audit Findings & Risk Prioritization',
          subtitle: 'Explainable freshness-risk scores (0–100) and deterministic remediation queue',
        };
      case 'evidence':
        return {
          title: 'Evidence Collection Agent & Content Verification',
          subtitle: 'Autonomous verification agent collecting traceable, SSRF-safe signals and updating risk scores',
        };
      case 'contradictions':
        return {
          title: 'AI Contradiction Detection Agent & Cross-Document Reasoning',
          subtitle: 'Extract claims, detect procedural conflicts, assess supersession, and review semantic contradictions',
        };
      case 'remediation':
        return {
          title: 'AI Remediation, Rewriting & Validation Agents',
          subtitle: 'Multi-agent remediation workflow with evidence-grounded revisions, independent validation, and human review',
        };
    }
  };

  const { title, subtitle } = getTitles();

  return (
    <header className="topbar">
      <div className="topbar-title-section">
        <h1>{title}</h1>
        <span className="topbar-subtitle">{subtitle}</span>
      </div>

      <div className="topbar-actions">
        {backendOnline === null ? (
          <div className="status-badge checking">
            <span className="dot-indicator" />
            <span>Checking Backend...</span>
          </div>
        ) : backendOnline ? (
          <div className="status-badge online" title={lastChecked ? `Last synchronized at ${lastChecked}` : 'Connected'}>
            <span className="dot-indicator" />
            <Server size={13} />
            <span>FastAPI Live</span>
          </div>
        ) : (
          <div className="status-badge offline">
            <AlertCircle size={13} />
            <span>Backend Offline</span>
          </div>
        )}

        <button
          className="btn-secondary"
          id="btn-sync-data"
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Synchronize metrics and audit findings from backend"
        >
          <RefreshCw size={14} className={isRefreshing ? 'spinning' : ''} />
          <span>{isRefreshing ? 'Syncing...' : 'Sync Data'}</span>
        </button>
      </div>
    </header>
  );
};
