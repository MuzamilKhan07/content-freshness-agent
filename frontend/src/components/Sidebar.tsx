import React from 'react';
import {
  ShieldCheck,
  LayoutDashboard,
  FileSpreadsheet,
  ShieldAlert,
  GitCompare,
  Wrench,
  Settings,
} from 'lucide-react';

interface SidebarProps {
  activeTab: 'dashboard' | 'inventory' | 'audit';
  onSelectTab: (tab: 'dashboard' | 'inventory' | 'audit') => void;
  totalRecords?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  totalRecords,
}) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-icon">
          <ShieldCheck size={22} />
        </div>
        <div className="brand-title-wrap">
          <span className="sidebar-brand-name">FreshGuard AI</span>
          <span className="sidebar-brand-sub">Enterprise Knowledge</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-title">Core Modules</div>

        <button
          className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
          id="nav-dashboard"
          onClick={() => onSelectTab('dashboard')}
        >
          <div className="nav-item-left">
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </div>
        </button>

        <button
          className={`nav-item ${activeTab === 'inventory' ? 'active' : ''}`}
          id="nav-inventory"
          onClick={() => onSelectTab('inventory')}
        >
          <div className="nav-item-left">
            <FileSpreadsheet size={18} />
            <span>Content Inventory</span>
          </div>
          {totalRecords !== undefined && totalRecords > 0 && (
            <span className="card-badge mono" style={{ fontSize: '0.65rem' }}>
              {totalRecords}
            </span>
          )}
        </button>

        <button
          className={`nav-item ${activeTab === 'audit' ? 'active' : ''}`}
          id="nav-audit"
          onClick={() => onSelectTab('audit')}
        >
          <div className="nav-item-left">
            <ShieldAlert size={18} />
            <span>Audit Findings</span>
          </div>
          <span
            className="card-badge"
            style={{
              backgroundColor: activeTab === 'audit' ? 'rgba(255,255,255,0.2)' : 'var(--rose-50)',
              color: activeTab === 'audit' ? '#ffffff' : 'var(--rose-600)',
              fontSize: '0.65rem',
              fontWeight: 700,
            }}
          >
            Phase 3
          </span>
        </button>

        <div className="nav-section-title" style={{ marginTop: 14 }}>
          Intelligence (Upcoming)
        </div>

        <div className="nav-item disabled" title="Available in Phase 5: Semantic Contradictions">
          <div className="nav-item-left">
            <GitCompare size={18} />
            <span>Contradictions</span>
          </div>
          <span className="nav-badge-upcoming">Phase 5</span>
        </div>

        <div className="nav-item disabled" title="Available in Phase 6: Autonomous Remediation">
          <div className="nav-item-left">
            <Wrench size={18} />
            <span>Remediation</span>
          </div>
          <span className="nav-badge-upcoming">Phase 6</span>
        </div>

        <div className="nav-section-title" style={{ marginTop: 14 }}>
          Administration
        </div>

        <div className="nav-item disabled" title="Settings">
          <div className="nav-item-left">
            <Settings size={18} />
            <span>Settings</span>
          </div>
          <span className="nav-badge-upcoming">Phase 7</span>
        </div>
      </nav>

      <div className="sidebar-footer">
        <div><strong>Dataset:</strong> ps11_content_inventory</div>
        <div><strong>Scoring Engine:</strong> Active (Phase 3)</div>
        <div style={{ color: '#475569', marginTop: 4 }}>FastAPI &bull; React &bull; Vite</div>
      </div>
    </aside>
  );
};
