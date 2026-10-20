import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from '../components/Sidebar';
import { TopBar } from '../components/TopBar';
import { DashboardOverview } from '../components/DashboardOverview';
import { ContentInventory } from '../components/ContentInventory';
import { AuditFindings } from '../components/AuditFindings';
import { DocumentDetailDrawer } from '../components/DocumentDetailDrawer';
import { ScoreDetailDrawer } from '../components/ScoreDetailDrawer';
import {
  fetchHealth,
  fetchDatasetStatus,
  fetchDashboardSummary,
  fetchDashboardDistributions,
} from '../services/api';
import {
  HealthResponse,
  DatasetStatusResponse,
  DashboardSummaryResponse,
  DashboardDistributionsResponse,
  DocumentRecord,
  ScoredDocument,
} from '../types';

export const DashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'inventory' | 'audit'>('dashboard');
  const [selectedDocument, setSelectedDocument] = useState<DocumentRecord | null>(null);
  const [selectedScoredDocument, setSelectedScoredDocument] = useState<ScoredDocument | null>(null);

  // High-level metrics
  const [_health, setHealth] = useState<HealthResponse | null>(null);
  const [_datasetStatus, setDatasetStatus] = useState<DatasetStatusResponse | null>(null);
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [distributions, setDistributions] = useState<DashboardDistributionsResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [lastChecked, setLastChecked] = useState<string>('');

  const loadDashboardData = useCallback(async (isManual = false) => {
    if (isManual) {
      setIsRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      // 1. Health
      const h = await fetchHealth();
      setHealth(h);
      setBackendOnline(true);
      setLastChecked(new Date().toLocaleTimeString());

      // 2. Dataset Status
      const ds = await fetchDatasetStatus();
      setDatasetStatus(ds);

      // 3. Dashboard Summary
      const s = await fetchDashboardSummary();
      setSummary(s);

      // 4. Distributions
      const dist = await fetchDashboardDistributions();
      setDistributions(dist);
    } catch (err: any) {
      console.error('Error fetching dashboard metrics:', err);
      setBackendOnline(false);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData(false);
  }, [loadDashboardData]);

  return (
    <div className="app-layout">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={(tab) => setActiveTab(tab)}
        totalRecords={summary?.total_documents}
      />

      {/* Main Content Area */}
      <div className="main-wrapper">
        <TopBar
          activeTab={activeTab}
          backendOnline={backendOnline}
          isRefreshing={isRefreshing}
          onRefresh={() => loadDashboardData(true)}
          lastChecked={lastChecked}
        />

        <main className="page-container">
          {activeTab === 'dashboard' ? (
            <DashboardOverview
              summary={summary}
              distributions={distributions}
              loading={loading && !summary}
              onNavigateToInventory={() => setActiveTab('inventory')}
            />
          ) : activeTab === 'inventory' ? (
            <ContentInventory
              onSelectDocument={(doc) => setSelectedDocument(doc)}
              availablePlatforms={summary?.platforms_list || []}
              availableContentTypes={summary?.content_types_list || []}
            />
          ) : (
            <AuditFindings
              onSelectScoredDocument={(scoredDoc) => setSelectedScoredDocument(scoredDoc)}
            />
          )}
        </main>
      </div>

      {/* Slide-over Document Detail Drawer (Inventory View) */}
      <DocumentDetailDrawer
        document={selectedDocument}
        onClose={() => setSelectedDocument(null)}
      />

      {/* Slide-over Score Detail Drawer (Phase 3 Audit View) */}
      <ScoreDetailDrawer
        document={selectedScoredDocument}
        onClose={() => setSelectedScoredDocument(null)}
      />
    </div>
  );
};
