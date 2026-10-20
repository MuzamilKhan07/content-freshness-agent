import React from 'react';
import { ShieldCheck, RefreshCw, Server, AlertCircle } from 'lucide-react';

interface HeaderProps {
  backendOnline: boolean | null;
  isRefreshing: boolean;
  onRefresh: () => void;
  lastChecked?: string;
}

export const Header: React.FC<HeaderProps> = ({
  backendOnline,
  isRefreshing,
  onRefresh,
  lastChecked,
}) => {
  return (
    <header className="header-wrapper">
      <div className="brand-section">
        <div className="brand-icon-box" title="FreshGuard AI Engine">
          <ShieldCheck size={28} />
        </div>
        <div>
          <h1 className="brand-title">
            FreshGuard AI
            <span className="phase-pill">Phase 1 Foundation</span>
          </h1>
          <p className="brand-subtitle">
            Content Freshness & Decay Detection Agent
          </p>
        </div>
      </div>

      <div className="header-actions">
        {backendOnline === null ? (
          <div className="status-pill checking" id="connection-indicator">
            <span className="pulse-dot" />
            <span>Checking Backend...</span>
          </div>
        ) : backendOnline ? (
          <div className="status-pill online" id="connection-indicator" title={lastChecked ? `Last synchronized at ${lastChecked}` : 'Connected'}>
            <span className="pulse-dot" />
            <Server size={14} />
            <span>Backend Online</span>
          </div>
        ) : (
          <div className="status-pill offline" id="connection-indicator">
            <AlertCircle size={14} />
            <span>Backend Offline</span>
          </div>
        )}

        <button
          className="btn-refresh"
          id="btn-refresh-dataset"
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Refresh dataset status and preview"
        >
          <RefreshCw size={15} className={isRefreshing ? 'spinning' : ''} />
          <span>{isRefreshing ? 'Syncing...' : 'Sync Data'}</span>
        </button>
      </div>
    </header>
  );
};
