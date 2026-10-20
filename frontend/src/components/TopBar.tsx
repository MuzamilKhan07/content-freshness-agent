import React from 'react';
import { RefreshCw, Server, AlertCircle } from 'lucide-react';

interface TopBarProps {
  activeTab: 'dashboard' | 'inventory';
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
  return (
    <header className="topbar">
      <div className="topbar-title-section">
        <h1>{activeTab === 'dashboard' ? 'Knowledge Health Dashboard' : 'Content Inventory & Catalog'}</h1>
        <span className="topbar-subtitle">
          {activeTab === 'dashboard'
            ? 'Real-time KPI metrics and knowledge distribution derived from enterprise inventory'
            : 'Explore, filter, and inspect document metadata across enterprise platforms'}
        </span>
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
          title="Synchronize metrics and documents from backend"
        >
          <RefreshCw size={14} className={isRefreshing ? 'spinning' : ''} />
          <span>{isRefreshing ? 'Syncing...' : 'Sync Data'}</span>
        </button>
      </div>
    </header>
  );
};
