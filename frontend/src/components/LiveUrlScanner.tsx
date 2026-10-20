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
        // Set default tab based on where issues are found
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
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg border border-indigo-500/20">
              <Globe className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                Live URL Freshness & Telemetry Scanner
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                  SSRF-Guarded
                </span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Paste any webpage or documentation link to automatically audit broken links, deprecated tools, and metadata decay.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Input Form */}
      <form onSubmit={handleScan} className="flex flex-col gap-3">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Link2 className="w-4 h-4" />
            </div>
            <input
              type="text"
              placeholder="Paste any URL (e.g. https://docs.example.com/team-guide)..."
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-slate-950 border border-slate-700/80 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={isScanning || !targetUrl.trim()}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg flex items-center justify-center gap-2 transition shadow-lg shadow-indigo-600/20 whitespace-nowrap"
            >
              {isScanning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Scanning Page...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  Scan URL
                </>
              )}
            </button>
          </div>
        </div>

        {/* Option toggles and quick samples */}
        <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 pt-1">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={checkLinks}
              onChange={(e) => setCheckLinks(e.target.checked)}
              className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0 focus:ring-offset-0 cursor-pointer"
            />
            <span>Probe extracted hyperlinks for HTTP 404/dead links (Safe network check)</span>
          </label>

          <div className="flex items-center gap-2 mt-2 sm:mt-0">
            <span className="text-slate-500">Try sample:</span>
            <button
              type="button"
              onClick={() => {
                setTargetUrl('https://example.com');
              }}
              className="text-indigo-400 hover:text-indigo-300 underline"
            >
              example.com
            </button>
          </div>
        </div>
      </form>

      {/* Error Message */}
      {errorMessage && (
        <div className="mt-4 p-3.5 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-300 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 text-rose-400" />
          <div className="flex-1">
            <p className="font-medium text-rose-200">Scan Notice</p>
            <p className="mt-0.5">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Success / Result View */}
      {scanResult && scanResult.status === 'success' && (
        <div className="mt-6 border-t border-slate-800 pt-5">
          {/* Page Overview Header */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-slate-950/80 border border-slate-800 rounded-xl p-4 mb-5">
            <div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 text-xs font-semibold rounded-full uppercase tracking-wider ${
                  scanResult.risk_level === 'Critical'
                    ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    : scanResult.risk_level === 'High'
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    : scanResult.risk_level === 'Moderate'
                    ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                    : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                }`}>
                  {scanResult.risk_level} Risk ({scanResult.freshness_score}/100)
                </span>
                <span className="text-xs text-slate-400">
                  HTTP {scanResult.status_code || 200}
                </span>
              </div>
              <h4 className="text-base font-semibold text-slate-100 mt-1">
                {scanResult.page_title}
              </h4>
              <a
                href={scanResult.url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 mt-0.5 truncate max-w-xl"
              >
                {scanResult.url}
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            {/* Import Button */}
            <div className="flex items-center gap-3">
              {importedDocId ? (
                <div className="px-3.5 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs font-medium text-emerald-400 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>{importSuccessMessage}</span>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={handleImport}
                  disabled={isImporting}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg flex items-center gap-2 transition shadow-md shadow-emerald-600/20 whitespace-nowrap"
                >
                  <Download className="w-3.5 h-3.5" />
                  {isImporting ? 'Importing...' : 'Add to Inventory Catalog'}
                </button>
              )}
            </div>
          </div>

          {/* 4 Hero KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-5">
            {/* Broken Links */}
            <div className={`p-4 rounded-xl border ${
              scanResult.broken_links_count > 0
                ? 'bg-rose-950/20 border-rose-800/40'
                : 'bg-slate-950/60 border-slate-800/80'
            }`}>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">Broken Links</span>
                <XCircle className={`w-4 h-4 ${scanResult.broken_links_count > 0 ? 'text-rose-400' : 'text-slate-500'}`} />
              </div>
              <div className="mt-2 text-2xl font-bold text-slate-100">
                {scanResult.broken_links_count}
              </div>
              <div className="mt-1 text-[11px] text-slate-400">
                {scanResult.links_checked_count} links probed
              </div>
            </div>

            {/* Deprecated Tools */}
            <div className={`p-4 rounded-xl border ${
              scanResult.deprecated_tools_count > 0
                ? 'bg-amber-950/20 border-amber-800/40'
                : 'bg-slate-950/60 border-slate-800/80'
            }`}>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">Deprecated Tools</span>
                <ShieldAlert className={`w-4 h-4 ${scanResult.deprecated_tools_count > 0 ? 'text-amber-400' : 'text-slate-500'}`} />
              </div>
              <div className="mt-2 text-2xl font-bold text-slate-100">
                {scanResult.deprecated_tools_count}
              </div>
              <div className="mt-1 text-[11px] text-slate-400">
                Retired tools detected
              </div>
            </div>

            {/* Metadata Quality */}
            <div className={`p-4 rounded-xl border ${
              scanResult.metadata_quality_issues_count > 0
                ? 'bg-yellow-950/20 border-yellow-800/40'
                : 'bg-slate-950/60 border-slate-800/80'
            }`}>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">Metadata Issues</span>
                <AlertTriangle className={`w-4 h-4 ${scanResult.metadata_quality_issues_count > 0 ? 'text-yellow-400' : 'text-slate-500'}`} />
              </div>
              <div className="mt-2 text-2xl font-bold text-slate-100">
                {scanResult.metadata_quality_issues_count}
              </div>
              <div className="mt-1 text-[11px] text-slate-400">
                Missing headers/attributes
              </div>
            </div>

            {/* Freshness Risk Score */}
            <div className="p-4 rounded-xl border bg-slate-950/60 border-slate-800/80">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">Risk Score</span>
                <Sparkles className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="mt-2 text-2xl font-bold text-slate-100">
                {scanResult.freshness_score}
                <span className="text-xs text-slate-400 font-normal"> / 100</span>
              </div>
              <div className="mt-1 text-[11px] text-slate-400">
                {scanResult.word_count} words extracted
              </div>
            </div>
          </div>

          {/* Sub-tabs */}
          <div className="flex border-b border-slate-800 gap-2 mb-4 text-xs font-medium">
            <button
              type="button"
              onClick={() => setActiveTab('deprecated')}
              className={`pb-2 px-1 border-b-2 flex items-center gap-1.5 transition ${
                activeTab === 'deprecated'
                  ? 'border-amber-500 text-amber-400'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              Deprecated Tools ({scanResult.deprecated_tools_count})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('links')}
              className={`pb-2 px-1 border-b-2 flex items-center gap-1.5 transition ${
                activeTab === 'links'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              Links ({scanResult.broken_links_count} broken / {scanResult.links_checked_count} checked)
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('metadata')}
              className={`pb-2 px-1 border-b-2 flex items-center gap-1.5 transition ${
                activeTab === 'metadata'
                  ? 'border-yellow-500 text-yellow-400'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              Metadata Quality ({scanResult.metadata_quality_issues_count})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('text')}
              className={`pb-2 px-1 border-b-2 flex items-center gap-1.5 transition ${
                activeTab === 'text'
                  ? 'border-slate-400 text-slate-200'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              Extracted Content
            </button>
          </div>

          {/* Tab 1: Deprecated Tools */}
          {activeTab === 'deprecated' && (
            <div>
              {scanResult.deprecated_tools.length === 0 ? (
                <div className="p-4 text-center text-xs text-slate-400 bg-slate-950/40 rounded-lg border border-slate-800/60">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 mx-auto mb-1" />
                  No deprecated tools detected. Document is clean of retired enterprise software mentions.
                </div>
              ) : (
                <div className="space-y-3">
                  {scanResult.deprecated_tools.map((hit, idx) => (
                    <div key={idx} className="p-3.5 bg-amber-950/20 border border-amber-800/40 rounded-lg text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-amber-300 flex items-center gap-1.5">
                          <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                          {hit.tool_name}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono text-[10px]">
                          Matched: "{hit.matched_text}"
                        </span>
                      </div>
                      <div className="mt-2 text-slate-300 bg-slate-950/80 p-2.5 rounded font-mono text-[11px] border border-slate-800">
                        "...{hit.context_excerpt}..."
                      </div>
                      {hit.recommended_replacement && (
                        <div className="mt-2 text-amber-400/90 text-[11px] flex items-center gap-1">
                          <ArrowRight className="w-3 h-3 text-amber-400" />
                          {hit.recommended_replacement}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Links */}
          {activeTab === 'links' && (
            <div>
              {scanResult.broken_links.length > 0 && (
                <div className="mb-4 space-y-2">
                  <h5 className="text-xs font-semibold text-rose-400 flex items-center gap-1.5">
                    <XCircle className="w-3.5 h-3.5 text-rose-400" />
                    Broken & Dead Hyperlinks ({scanResult.broken_links.length})
                  </h5>
                  {scanResult.broken_links.map((link, idx) => (
                    <div key={idx} className="p-2.5 bg-rose-950/20 border border-rose-800/40 rounded-lg text-xs flex items-center justify-between gap-3">
                      <div className="truncate">
                        <span className="text-rose-300 font-mono text-[11px]">{link.url}</span>
                        {link.anchor_text && (
                          <span className="text-slate-400 text-[10px] block truncate">
                            Anchor: "{link.anchor_text}"
                          </span>
                        )}
                      </div>
                      <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-mono text-[10px] whitespace-nowrap">
                        {link.error || `HTTP ${link.status_code || 'Fail'}`}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {scanResult.live_links.length > 0 && (
                <div className="space-y-2">
                  <h5 className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    Live & Verified Hyperlinks ({scanResult.live_links.length})
                  </h5>
                  {scanResult.live_links.slice(0, 8).map((link, idx) => (
                    <div key={idx} className="p-2 bg-slate-950/60 border border-slate-800/60 rounded-lg text-xs flex items-center justify-between gap-3">
                      <span className="text-slate-300 font-mono text-[11px] truncate">{link.url}</span>
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono text-[10px]">
                        HTTP {link.status_code || 200}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {scanResult.broken_links.length === 0 && scanResult.live_links.length === 0 && (
                <div className="p-4 text-center text-xs text-slate-400 bg-slate-950/40 rounded-lg border border-slate-800/60">
                  No outgoing hyperlinks were detected on this webpage.
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Metadata Quality */}
          {activeTab === 'metadata' && (
            <div>
              {scanResult.metadata_quality_issues.length === 0 ? (
                <div className="p-4 text-center text-xs text-slate-400 bg-slate-950/40 rounded-lg border border-slate-800/60">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 mx-auto mb-1" />
                  Metadata is healthy. Document has valid title, author attributes, and dates.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {scanResult.metadata_quality_issues.map((issue, idx) => (
                    <div key={idx} className="p-3 bg-yellow-950/20 border border-yellow-800/40 rounded-lg text-xs flex items-start gap-2.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 mt-0.5 flex-shrink-0" />
                      <div>
                        <span className="font-semibold text-yellow-300 uppercase tracking-wider text-[10px]">
                          Field: {issue.field}
                        </span>
                        <p className="text-slate-200 mt-0.5">{issue.issue}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 4: Raw Text */}
          {activeTab === 'text' && (
            <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 text-xs font-mono text-slate-300 max-h-60 overflow-y-auto leading-relaxed">
              {scanResult.text_preview || 'No visible plain text could be extracted.'}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
