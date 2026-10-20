import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileQuestion,
  AlertCircle,
  X,
} from 'lucide-react';
import { DocumentRecord, DocumentListResponse, DocumentQueryParams } from '../types';
import { fetchDocuments } from '../services/api';

interface ContentInventoryProps {
  onSelectDocument: (doc: DocumentRecord) => void;
  availablePlatforms: string[];
  availableContentTypes: string[];
}

export const ContentInventory: React.FC<ContentInventoryProps> = ({
  onSelectDocument,
  availablePlatforms,
  availableContentTypes,
}) => {
  // Query state
  const [search, setSearch] = useState<string>('');
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');
  const [platform, setPlatform] = useState<string>('all');
  const [contentType, setContentType] = useState<string>('all');
  const [status, setStatus] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('content_id');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);

  // Response state
  const [data, setData] = useState<DocumentListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1); // Reset to page 1 on search change
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Load documents
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: DocumentQueryParams = {
        page,
        page_size: pageSize,
        search: debouncedSearch,
        platform,
        content_type: contentType,
        status,
        sort_by: sortBy,
        sort_order: sortOrder,
      };
      const res = await fetchDocuments(params);
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch inventory documents.');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, debouncedSearch, platform, contentType, status, sortBy, sortOrder]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Toggle sorting
  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
    setPage(1);
  };

  const clearFilters = () => {
    setSearch('');
    setDebouncedSearch('');
    setPlatform('all');
    setContentType('all');
    setStatus('all');
    setSortBy('content_id');
    setSortOrder('asc');
    setPage(1);
  };

  const hasActiveFilters =
    debouncedSearch.trim() !== '' ||
    platform !== 'all' ||
    contentType !== 'all' ||
    status !== 'all';

  // Render sort indicator
  const renderSortIndicator = (field: string) => {
    if (sortBy !== field) {
      return <ArrowUpDown size={13} className="sort-icon" />;
    }
    return sortOrder === 'asc' ? (
      <ArrowUp size={13} className="sort-icon active" />
    ) : (
      <ArrowDown size={13} className="sort-icon active" />
    );
  };

  // Helper for score formatting
  const renderStalenessScore = (score: number | null) => {
    if (score === null || score === undefined) return <span className="text-muted">Not provided</span>;
    let scoreClass = 'score-low';
    if (score > 0.8) scoreClass = 'score-critical';
    else if (score > 0.6) scoreClass = 'score-high';
    else if (score > 0.4) scoreClass = 'score-moderate';
    else if (score > 0.2) scoreClass = 'score-mild';

    return <span className={`score-tag ${scoreClass}`}>{score.toFixed(2)}</span>;
  };

  // Helper for action pill
  const renderActionPill = (action: string | null) => {
    if (!action) return <span className="text-muted">Not provided</span>;
    const lower = action.toLowerCase();
    let cls = 'action-no-action';
    if (lower.includes('review')) cls = 'action-review';
    else if (lower.includes('update')) cls = 'action-update';
    else if (lower.includes('merge')) cls = 'action-merge';
    else if (lower.includes('rewrite')) cls = 'action-rewrite';
    else if (lower.includes('archive')) cls = 'action-archive';

    return <span className={`action-pill ${cls}`}>{action}</span>;
  };

  return (
    <div id="content-inventory-module">
      {/* Filter and Search Bar */}
      <div className="filter-toolbar">
        <div className="search-box">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search by ID, title, domain, author..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            id="input-inventory-search"
          />
        </div>

        <div className="filters-group">
          <select
            className="select-filter"
            value={platform}
            onChange={(e) => {
              setPlatform(e.target.value);
              setPage(1);
            }}
            id="select-filter-platform"
          >
            <option value="all">All Platforms ({availablePlatforms.length})</option>
            {availablePlatforms.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>

          <select
            className="select-filter"
            value={contentType}
            onChange={(e) => {
              setContentType(e.target.value);
              setPage(1);
            }}
            id="select-filter-content-type"
          >
            <option value="all">All Types ({availableContentTypes.length})</option>
            {availableContentTypes.map((ct) => (
              <option key={ct} value={ct}>
                {ct}
              </option>
            ))}
          </select>

          <select
            className="select-filter"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            id="select-filter-status"
          >
            <option value="all">All Actions</option>
            <option value="Review Needed">Review Needed</option>
            <option value="Update Required">Update Required</option>
            <option value="Merge with Another">Merge with Another</option>
            <option value="Rewrite">Rewrite</option>
            <option value="Archive">Archive</option>
            <option value="No Action">No Action</option>
          </select>

          {hasActiveFilters && (
            <button
              className="btn-clear-filters"
              onClick={clearFilters}
              title="Reset all active search and filter options"
            >
              <X size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Table Card */}
      <div className="table-card">
        {loading && !data ? (
          <div className="empty-state">
            <div className="dot-indicator" style={{ width: 24, height: 24, marginBottom: 8 }} />
            <h3 className="empty-state-title">Loading Content Catalog...</h3>
            <p className="empty-state-desc">Querying paginated inventory and applying filters.</p>
          </div>
        ) : error ? (
          <div className="empty-state">
            <AlertCircle size={36} color="var(--rose-600)" />
            <h3 className="empty-state-title">Failed to Load Documents</h3>
            <p className="empty-state-desc">{error}</p>
            <button className="btn-secondary" onClick={loadData} style={{ marginTop: 8 }}>
              Retry Query
            </button>
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="empty-state">
            <FileQuestion size={36} className="empty-state-icon" />
            <h3 className="empty-state-title">No Matching Documents</h3>
            <p className="empty-state-desc">
              No inventory records match your search query or filter selection.
            </p>
            {hasActiveFilters && (
              <button className="btn-secondary" onClick={clearFilters} style={{ marginTop: 8 }}>
                Clear Filters
              </button>
            )}
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="enterprise-table" id="inventory-table">
              <thead>
                <tr>
                  <th className="sortable-th" onClick={() => handleSort('content_id')}>
                    <div className="th-content">
                      <span>Document ID</span>
                      {renderSortIndicator('content_id')}
                    </div>
                  </th>
                  <th className="sortable-th" onClick={() => handleSort('title')}>
                    <div className="th-content">
                      <span>Title</span>
                      {renderSortIndicator('title')}
                    </div>
                  </th>
                  <th className="sortable-th" onClick={() => handleSort('platform')}>
                    <div className="th-content">
                      <span>Platform</span>
                      {renderSortIndicator('platform')}
                    </div>
                  </th>
                  <th className="sortable-th" onClick={() => handleSort('content_type')}>
                    <div className="th-content">
                      <span>Content Type</span>
                      {renderSortIndicator('content_type')}
                    </div>
                  </th>
                  <th>Subject Area</th>
                  <th className="sortable-th" onClick={() => handleSort('last_updated')}>
                    <div className="th-content">
                      <span>Last Updated</span>
                      {renderSortIndicator('last_updated')}
                    </div>
                  </th>
                  <th className="sortable-th" onClick={() => handleSort('last_reviewed')}>
                    <div className="th-content">
                      <span>Last Reviewed</span>
                      {renderSortIndicator('last_reviewed')}
                    </div>
                  </th>
                  <th className="sortable-th" onClick={() => handleSort('staleness_score')}>
                    <div className="th-content">
                      <span>Ref Score</span>
                      {renderSortIndicator('staleness_score')}
                    </div>
                  </th>
                  <th>Dead Links?</th>
                  <th>Deprecated Tool?</th>
                  <th>Recommended Action</th>
                  <th style={{ textAlign: 'center' }}>Inspect</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((doc) => (
                  <tr
                    key={doc.content_id}
                    onClick={() => onSelectDocument(doc)}
                    title="Click to inspect document metadata"
                  >
                    <td>
                      <span className="doc-id-pill">{doc.content_id}</span>
                    </td>
                    <td style={{ fontWeight: 600, maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {doc.title || <span className="text-muted">Not provided</span>}
                    </td>
                    <td>
                      <span className="badge-tag badge-platform">{doc.platform}</span>
                    </td>
                    <td>
                      <span className="badge-tag badge-type">{doc.content_type}</span>
                    </td>
                    <td>
                      <span style={{ color: 'var(--text-secondary)' }}>
                        {doc.subject_area || <span className="text-muted">Not provided</span>}
                      </span>
                    </td>
                    <td className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {doc.last_updated || <span className="text-muted">Not provided</span>}
                    </td>
                    <td className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {doc.last_reviewed || <span className="text-muted">Not provided</span>}
                    </td>
                    <td>{renderStalenessScore(doc.staleness_score)}</td>
                    <td style={{ textAlign: 'center' }}>
                      {doc.has_broken_links ? (
                        <span className="flag-badge flag-yes">Yes</span>
                      ) : (
                        <span className="flag-no">No</span>
                      )}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      {doc.mentions_deprecated_tool ? (
                        <span className="flag-badge flag-yes">Yes</span>
                      ) : (
                        <span className="flag-no">No</span>
                      )}
                    </td>
                    <td>{renderActionPill(doc.recommended_action)}</td>
                    <td style={{ textAlign: 'center' }}>
                      <button
                        className="btn-secondary"
                        style={{ padding: '3px 8px', fontSize: '0.75rem' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectDocument(doc);
                        }}
                      >
                        <ExternalLink size={12} style={{ marginRight: 4 }} />
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {data && data.total > 0 && (
          <div className="table-pagination">
            <div className="pagination-info">
              Showing{' '}
              <strong>
                {Math.min((data.page - 1) * data.page_size + 1, data.total)}
              </strong>{' '}
              to{' '}
              <strong>
                {Math.min(data.page * data.page_size, data.total)}
              </strong>{' '}
              of <strong>{data.total.toLocaleString()}</strong> documents
            </div>

            <div className="pagination-controls">
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginRight: 6 }}>
                Per page:
              </span>
              <select
                className="select-filter"
                style={{ height: 32, paddingRight: 22 }}
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>

              <button
                className="btn-page"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={data.page <= 1 || loading}
                title="Previous page"
              >
                <ChevronLeft size={16} />
                <span>Prev</span>
              </button>

              <span className="page-indicator">
                Page {data.page} of {data.total_pages}
              </span>

              <button
                className="btn-page"
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                disabled={data.page >= data.total_pages || loading}
                title="Next page"
              >
                <span>Next</span>
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
