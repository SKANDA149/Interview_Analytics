import React, { useEffect, useState, useCallback } from 'react';
import { apiClient } from '../api/client';
import { JobHistoryItem } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { formatDate } from '../utils/formatters';
import {
  History,
  FileVideo,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Search,
  FileText,
} from 'lucide-react';

interface Props {
  onViewReport: (jobId: string) => void;
  onStartUpload: () => void;
}

export const HistoryPage: React.FC<Props> = ({ onViewReport, onStartUpload }) => {
  const [items, setItems] = useState<JobHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(0); // 0-based offset
  const pageSize = 10;
  const [filterTerm, setFilterTerm] = useState('');

  const fetchHistory = useCallback(async (offset: number) => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.getInterviews(pageSize, offset);
      setItems(res.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch interview history');
    } finally {
      setLoading(false);
    }
  }, [pageSize]);

  useEffect(() => {
    fetchHistory(page * pageSize);
  }, [page, fetchHistory, pageSize]);

  const filteredItems = items.filter(
    (item) =>
      item.original_filename.toLowerCase().includes(filterTerm.toLowerCase()) ||
      item.job_id.toLowerCase().includes(filterTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
            Interview History
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Browse and review past interview analysis reports persisted in SQLite.
          </p>
        </div>

        <button
          onClick={() => fetchHistory(page * pageSize)}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 rounded-lg shadow-sm transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Main Table Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden">
        {/* Filter bar */}
        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-4 bg-slate-50/50 dark:bg-slate-900/50">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by filename or job ID..."
              value={filterTerm}
              onChange={(e) => setFilterTerm(e.target.value)}
              className="w-full text-xs pl-9 pr-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <span className="text-xs text-slate-400">
            Page {page + 1}
          </span>
        </div>

        {/* Content Area */}
        {loading && items.length === 0 ? (
          <div className="p-12 text-center text-sm text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-3 text-blue-600" />
            Loading interviews from database...
          </div>
        ) : error ? (
          <div className="p-12 text-center text-rose-600 text-sm">
            <p className="font-semibold mb-1">Failed to load history</p>
            <p className="text-xs text-slate-500 mb-4">{error}</p>
            <button
              onClick={() => fetchHistory(page * pageSize)}
              className="px-4 py-1.5 rounded bg-slate-100 dark:bg-slate-800 text-xs font-medium"
            >
              Retry
            </button>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<History className="w-6 h-6" />}
              title={filterTerm ? 'No matching records' : 'No interviews recorded yet'}
              description={
                filterTerm
                  ? 'No historical interviews matched your search term.'
                  : 'Get started by running an interview analysis on your local video.'
              }
              action={
                filterTerm
                  ? { label: 'Clear Filter', onClick: () => setFilterTerm('') }
                  : { label: 'Upload Video', onClick: onStartUpload }
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-800/50 text-slate-500 font-medium">
                  <th className="py-3 px-4">Original File</th>
                  <th className="py-3 px-4">Job ID</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Submitted</th>
                  <th className="py-3 px-4">Completed</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredItems.map((item) => (
                  <tr
                    key={item.job_id}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2.5">
                        <FileVideo className="w-4 h-4 text-slate-400 shrink-0" />
                        <span className="font-medium text-slate-900 dark:text-white truncate max-w-xs">
                          {item.original_filename}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-500 text-[11px]">
                      {item.job_id}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={item.status} size="sm" />
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {formatDate(item.created_at)}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {formatDate(item.completed_at)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {item.has_report || item.status === 'completed' ? (
                        <button
                          onClick={() => onViewReport(item.job_id)}
                          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 shadow-sm transition"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          <span>View Report</span>
                        </button>
                      ) : (
                        <button
                          onClick={() => onViewReport(item.job_id)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800 transition"
                        >
                          <span>Details</span>
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <div className="p-3.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500 bg-slate-50/30 dark:bg-slate-900/30">
          <span>
            Showing page {page + 1}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
              className="inline-flex items-center gap-1 px-3 py-1 rounded border border-slate-200 dark:border-slate-700 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> Previous
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={items.length < pageSize || loading}
              className="inline-flex items-center gap-1 px-3 py-1 rounded border border-slate-200 dark:border-slate-700 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              Next <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
