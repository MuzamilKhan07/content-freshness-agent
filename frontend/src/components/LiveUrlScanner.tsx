import React, { useState } from 'react';
import {
  Globe,
  Search,
  ExternalLink,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ShieldAlert,
  Download,
  Link2,
  Sparkles,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { inspectUrl, importScannedUrl } from '../services/api';
import { UrlInspectionResponse } from '../types';

interface LiveUrlScannerProps {
  onDocumentImported?: (docId: string) => void;
}

export const LiveUrlScanner: React.FC<LiveUrlScannerProps> = ({ onDocumentImported }) => {
  const [targetUrl, setTargetUrl] = useState<string>('');
  const [checkLinks, setCheckLinks] = useState<boolean>(true);
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [scanResult, setScanResult] = useState<UrlInspectionResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'deprecated' | 'links' | 'metadata' | 'text'>('deprecated');

  // Import state
  const [isImporting, setIsImporting] = useState<boolean>(false);
  const [importedDocId, setImportedDocId] = useState<string | null>(null);
  const [importSuccessMessage, setImportSuccessMessage] = useState<string | null>(null);

  const handleScan = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const urlToScan = targetUrl.trim();
    if (!urlToScan) return;

    setIsScanning(true);
    setErrorMessage(null);
    setScanResult(null);
    setImportedDocId(null);
    setImportSuccessMessage(null);

    try {
      const data = await inspectUrl(urlToScan, checkLinks, 15);
      setScanResult(data);
      if (data.status === 'error' && data.error_message) {
        setErrorMessage(data.error_message);
      } else {
        if (data.deprecated_tools_count > 0) {
          setActiveTab('deprecated');
        } else if (data.broken_links_count > 0) {
          setActiveTab('links');
        } else if (data.metadata_quality_issues_count > 0) {
          setActiveTab('metadata');
        } else {
          setActiveTab('links');
        }
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to inspect URL.');
    } finally {
      setIsScanning(false);
    }
  };

  const handleImport = async () => {
    if (!scanResult) return;
    setIsImporting(true);
    try {
      const res = await importScannedUrl({
        url: scanResult.url,
        title: scanResult.page_title,
        platform: 'Web',
        subject_area: 'Web Documentation',
        author: scanResult.author || 'External Author',
        raw_text: scanResult.text_preview,
        has_broken_links: scanResult.broken_links_count > 0,
        mentions_deprecated_tool: scanResult.deprecated_tools_count > 0,
      });

      setImportedDocId(res.document_id);
      setImportSuccessMessage(`Imported into catalog as ${res.document_id}!`);
      if (onDocumentImported) {
        onDocumentImported(res.document_id);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to import document into catalog.');
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="scanner-container">
      {/* Header */}
      <div className="scanner-header">
        <div className="scanner-title-group">
          <div className="scanner-icon-badge">
            <Globe size={22} />
          </div>
          <div>
            <h3 className="scanner-title">
              Live URL Freshness &amp; Decay Scanner
              <span className="scanner-pill-tag">SSRF Protected</span>
            </h3>
            <p className="scanner-subtitle">
              Paste any webpage or documentation link to extract broken links, deprecated tool references, and metadata decay.
            </p>
          </div>
        </div>
      </div>

      {/* Input Form */}
      <form onSubmit={handleScan} className="scanner-form">
        <div className="scanner-input-row">
          <div className="scanner-input-wrap">
            <Link2 className="scanner-input-icon" size={18} />
            <input
              type="text"
              placeholder="Paste any URL (e.g. https://docs.python.org/3/ or https://example.com)..."
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              className="scanner-input"
            />
          </div>

          <button
            type="submit"
            disabled={isScanning || !targetUrl.trim()}
            className="scanner-submit-btn"
          >
            {isScanning ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                Scanning Webpage...
              </>
            ) : (
              <>
                <Search size={16} />
                Scan URL
              </>
            )}
          </button>
        </div>

        {/* Options Row */}
        <div className="scanner-options-row">
          <label className="scanner-checkbox-label">
            <input
              type="checkbox"
              checked={checkLinks}
              onChange={(e) => setCheckLinks(e.target.checked)}
            />
            <span>Probe extracted hyperlinks for HTTP 404/dead links (Safe network check)</span>
          </label>

          <div className="scanner-samples">
            <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Try sample:</span>
            <button
              type="button"
              onClick={() => setTargetUrl('https://example.com')}
              className="scanner-sample-link"
            >
              example.com
            </button>
          </div>
        </div>
      </form>

      {/* Error Notice */}
      {errorMessage && (
        <div className="scanner-alert-box">
          <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: 2, color: '#e11d48' }} />
          <div>
            <div style={{ fontWeight: 700, color: '#9f1239', marginBottom: 2 }}>Scan Notice</div>
            <div>{errorMessage}</div>
          </div>
        </div>
      )}

      {/* Results View */}
      {scanResult && scanResult.status === 'success' && (
        <div className="scanner-results">
          {/* Page Meta Card */}
          <div className="scanner-page-meta-card">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: 9999,
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: 0.5,
                    backgroundColor:
                      scanResult.risk_level === 'Critical'
                        ? '#fee2e2'
                        : scanResult.risk_level === 'High'
                        ? '#fef3c7'
                        : scanResult.risk_level === 'Moderate'
                        ? '#fef9c3'
                        : '#dcfce7',
                    color:
                      scanResult.risk_level === 'Critical'
                        ? '#b91c1c'
                        : scanResult.risk_level === 'High'
                        ? '#b45309'
                        : scanResult.risk_level === 'Moderate'
                        ? '#a16207'
                        : '#15803d',
                  }}
                >
                  {scanResult.risk_level} Risk ({scanResult.freshness_score} / 100)
                </span>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  HTTP {scanResult.status_code || 200}
                </span>
                {scanResult.last_modified && (
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    &bull; Modified: {scanResult.last_modified}
                  </span>
                )}
              </div>
              <div className="scanner-page-title" style={{ marginTop: 4 }}>
                {scanResult.page_title}
              </div>
              <a
                href={scanResult.url}
                target="_blank"
                rel="noreferrer"
                className="scanner-page-url"
              >
                {scanResult.url}
                <ExternalLink size={12} />
              </a>
            </div>

            {/* Import Button */}
            <div>
              {importedDocId ? (
                <div className="scanner-imported-pill">
                  <CheckCircle2 size={16} />
                  <span>{importSuccessMessage}</span>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={handleImport}
                  disabled={isImporting}
                  className="scanner-import-btn"
                >
                  <Download size={15} />
                  {isImporting ? 'Importing...' : 'Add to Inventory Catalog'}
                </button>
              )}
            </div>
          </div>

          {/* 4 Hero KPI Cards */}
          <div className="scanner-kpi-grid">
            {/* Broken Links */}
            <div className={`scanner-kpi-card ${scanResult.broken_links_count > 0 ? 'has-issues' : 'is-healthy'}`}>
              <div className="scanner-kpi-header">
                <span className="scanner-kpi-label">Broken Links</span>
                {scanResult.broken_links_count > 0 ? (
                  <XCircle size={18} color="#e11d48" />
                ) : (
                  <CheckCircle2 size={18} color="#10b981" />
                )}
              </div>
              <div className="scanner-kpi-val" style={{ color: scanResult.broken_links_count > 0 ? '#e11d48' : '#0f172a' }}>
                {scanResult.broken_links_count}
              </div>
              <div className="scanner-kpi-subtext">
                {scanResult.links_checked_count} hyperlinks checked
              </div>
            </div>

            {/* Deprecated Tools */}
            <div className={`scanner-kpi-card ${scanResult.deprecated_tools_count > 0 ? 'has-warning' : 'is-healthy'}`}>
              <div className="scanner-kpi-header">
                <span className="scanner-kpi-label">Deprecated Tools</span>
                <ShieldAlert size={18} color={scanResult.deprecated_tools_count > 0 ? '#f59e0b' : '#10b981'} />
              </div>
              <div className="scanner-kpi-val" style={{ color: scanResult.deprecated_tools_count > 0 ? '#d97706' : '#0f172a' }}>
                {scanResult.deprecated_tools_count}
              </div>
              <div className="scanner-kpi-subtext">
                Legacy software detected
              </div>
            </div>

            {/* Metadata Quality */}
            <div className={`scanner-kpi-card ${scanResult.metadata_quality_issues_count > 0 ? 'has-warning' : 'is-healthy'}`}>
              <div className="scanner-kpi-header">
                <span className="scanner-kpi-label">Metadata Issues</span>
                <AlertTriangle size={18} color={scanResult.metadata_quality_issues_count > 0 ? '#f59e0b' : '#10b981'} />
              </div>
              <div className="scanner-kpi-val" style={{ color: scanResult.metadata_quality_issues_count > 0 ? '#b45309' : '#0f172a' }}>
                {scanResult.metadata_quality_issues_count}
              </div>
              <div className="scanner-kpi-subtext">
                Missing tags or attributes
              </div>
            </div>

            {/* Risk Score */}
            <div className="scanner-kpi-card">
              <div className="scanner-kpi-header">
                <span className="scanner-kpi-label">Freshness Risk</span>
                <Sparkles size={18} color="#4f46e5" />
              </div>
              <div className="scanner-kpi-val">
                {scanResult.freshness_score}
                <span style={{ fontSize: '0.9rem', color: '#94a3b8', fontWeight: 500 }}> / 100</span>
              </div>
              <div className="scanner-kpi-subtext">
                {scanResult.word_count} words extracted
              </div>
            </div>
          </div>

          {/* Sub-Tabs Bar */}
          <div className="scanner-tab-bar">
            <button
              type="button"
              onClick={() => setActiveTab('deprecated')}
              className={`scanner-tab-btn ${activeTab === 'deprecated' ? 'active' : ''}`}
            >
              Deprecated Tools
              <span className="scanner-tab-count">{scanResult.deprecated_tools_count}</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('links')}
              className={`scanner-tab-btn ${activeTab === 'links' ? 'active' : ''}`}
            >
              Hyperlinks
              <span className="scanner-tab-count">
                {scanResult.broken_links_count} broken / {scanResult.links_checked_count} checked
              </span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('metadata')}
              className={`scanner-tab-btn ${activeTab === 'metadata' ? 'active' : ''}`}
            >
              Metadata Quality
              <span className="scanner-tab-count">{scanResult.metadata_quality_issues_count}</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('text')}
              className={`scanner-tab-btn ${activeTab === 'text' ? 'active' : ''}`}
            >
              Extracted Content
            </button>
          </div>

          {/* Tab 1: Deprecated Tools Findings */}
          {activeTab === 'deprecated' && (
            <div>
              {scanResult.deprecated_tools.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', backgroundColor: '#f8fafc', borderRadius: 10, border: '1px solid #e2e8f0', color: '#64748b', fontSize: '0.85rem' }}>
                  <CheckCircle2 size={24} color="#10b981" style={{ margin: '0 auto 8px' }} />
                  <strong>Clean of Deprecated Tools</strong>
                  <p style={{ marginTop: 4, fontSize: '0.8rem' }}>No references to retired enterprise technologies or platforms were detected in the text.</p>
                </div>
              ) : (
                <div>
                  {scanResult.deprecated_tools.map((hit, idx) => (
                    <div key={idx} className="scanner-finding-card warning">
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontWeight: 700, color: '#92400e', display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.88rem' }}>
                          <ShieldAlert size={16} color="#d97706" />
                          {hit.tool_name}
                        </span>
                        <span style={{ padding: '2px 8px', borderRadius: 4, background: '#fef3c7', color: '#92400e', border: '1px solid #fde68a', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                          Token match: "{hit.matched_text}"
                        </span>
                      </div>
                      <div className="scanner-finding-excerpt">
                        "...{hit.context_excerpt}..."
                      </div>
                      {hit.recommended_replacement && (
                        <div style={{ marginTop: 8, fontSize: '0.8rem', color: '#b45309', display: 'flex', alignItems: 'center', gap: 6 }}>
                          <ArrowRight size={13} />
                          <strong>Recommended action:</strong> {hit.recommended_replacement}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Hyperlinks */}
          {activeTab === 'links' && (
            <div>
              {scanResult.broken_links.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#e11d48', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                    <XCircle size={16} />
                    Confirmed Broken or Blocked Hyperlinks ({scanResult.broken_links.length})
                  </div>
                  {scanResult.broken_links.map((link, idx) => (
                    <div key={idx} className="scanner-finding-card danger" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                      <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: '#be123c', fontWeight: 600 }}>
                          {link.url}
                        </span>
                        {link.anchor_text && (
                          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 2 }}>
                            Anchor label: "{link.anchor_text}"
                          </div>
                        )}
                      </div>
                      <span style={{ padding: '3px 8px', borderRadius: 6, background: '#ffe4e6', color: '#be123c', border: '1px solid #fecdd3', fontSize: '0.75rem', fontWeight: 700, whiteSpace: 'nowrap' }}>
                        {link.error || `HTTP ${link.status_code || 'Failed'}`}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {scanResult.live_links.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#059669', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                    <CheckCircle2 size={16} />
                    Verified Live Hyperlinks ({scanResult.live_links.length})
                  </div>
                  {scanResult.live_links.slice(0, 8).map((link, idx) => (
                    <div key={idx} className="scanner-finding-card success" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: '#334155', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {link.url}
                      </span>
                      <span style={{ padding: '2px 8px', borderRadius: 6, background: '#dcfce7', color: '#15803d', border: '1px solid #bbf7d0', fontSize: '0.75rem', fontWeight: 700 }}>
                        HTTP {link.status_code || 200}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {scanResult.broken_links.length === 0 && scanResult.live_links.length === 0 && (
                <div style={{ padding: '24px', textAlign: 'center', backgroundColor: '#f8fafc', borderRadius: 10, border: '1px solid #e2e8f0', color: '#64748b', fontSize: '0.85rem' }}>
                  No outgoing hyperlinks were found in this webpage.
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Metadata Quality */}
          {activeTab === 'metadata' && (
            <div>
              {scanResult.metadata_quality_issues.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', backgroundColor: '#f8fafc', borderRadius: 10, border: '1px solid #e2e8f0', color: '#64748b', fontSize: '0.85rem' }}>
                  <CheckCircle2 size={24} color="#10b981" style={{ margin: '0 auto 8px' }} />
                  <strong>Metadata is Complete &amp; Healthy</strong>
                  <p style={{ marginTop: 4, fontSize: '0.8rem' }}>Document has valid title, author, and timestamp attributes.</p>
                </div>
              ) : (
                <div>
                  {scanResult.metadata_quality_issues.map((issue, idx) => (
                    <div key={idx} className="scanner-finding-card warning" style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                      <AlertTriangle size={16} color="#d97706" style={{ marginTop: 2, flexShrink: 0 }} />
                      <div>
                        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#b45309', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                          Field: {issue.field}
                        </div>
                        <div style={{ fontSize: '0.82rem', color: '#334155', marginTop: 2 }}>
                          {issue.issue}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 4: Extracted Content */}
          {activeTab === 'text' && (
            <div className="scanner-code-preview">
              {scanResult.text_preview || 'No visible plain text could be extracted.'}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
