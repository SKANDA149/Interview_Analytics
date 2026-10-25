import React, { useState, useMemo } from 'react';
import { TimelineRow } from '../api/types';
import { Search, ChevronLeft, ChevronRight, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  rows: TimelineRow[];
}

export const TimelineTable: React.FC<Props> = ({ rows }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [expandedChunkId, setExpandedChunkId] = useState<string | null>(null);

  // Filter rows
  const filteredRows = useMemo(() => {
    if (!searchTerm.trim()) return rows;
    const term = searchTerm.toLowerCase();
    return rows.filter(
      (r) =>
        r.chunk_id.toLowerCase().includes(term) ||
        r.transcript.toLowerCase().includes(term)
    );
  }, [rows, searchTerm]);

  // Paginate
  const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const pageIndex = Math.min(currentPage, totalPages);
  const pagedRows = useMemo(() => {
    const start = (pageIndex - 1) * pageSize;
    return filteredRows.slice(start, start + pageSize);
  }, [filteredRows, pageIndex, pageSize]);

  const toggleExpand = (id: string) => {
    setExpandedChunkId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
      {/* Table Header Controls */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-50/50 dark:bg-slate-900/50">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
            Chunk-by-Chunk Timeline
          </h4>
          <span className="text-xs text-slate-500 px-2 py-0.5 rounded-full bg-slate-200/70 dark:bg-slate-800">
            {filteredRows.length} chunks
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Search box */}
          <div className="relative flex-1 sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search transcript..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full text-xs pl-9 pr-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Rows per page */}
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setCurrentPage(1);
            }}
            className="text-xs py-1.5 px-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 focus:outline-none"
          >
            <option value={10}>10 per page</option>
            <option value={25}>25 per page</option>
            <option value={50}>50 per page</option>
          </select>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 font-medium">
              <th className="py-2.5 px-4 w-24">Chunk</th>
              <th className="py-2.5 px-4 min-w-[240px]">Transcript</th>
              <th className="py-2.5 px-3 text-right">WPM</th>
              <th className="py-2.5 px-3 text-right">Fillers</th>
              <th className="py-2.5 px-3 text-right">Silence (s)</th>
              <th className="py-2.5 px-3 text-right">Pauses</th>
              <th className="py-2.5 px-3 text-right">Face Visibility</th>
              <th className="py-2.5 px-3 text-right">Semantic Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
            {pagedRows.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-slate-500 italic">
                  No chunk matching your filter.
                </td>
              </tr>
            ) : (
              pagedRows.map((r) => {
                const isExpanded = expandedChunkId === r.chunk_id;
                const hasLongText = r.transcript.length > 80;

                return (
                  <React.Fragment key={r.chunk_id}>
                    <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                      <td className="py-2.5 px-4 font-mono font-medium text-slate-700 dark:text-slate-300">
                        {r.chunk_id}
                      </td>
                      <td className="py-2.5 px-4 text-slate-800 dark:text-slate-200">
                        {r.transcript ? (
                          <div>
                            <span className={hasLongText && !isExpanded ? 'line-clamp-1' : ''}>
                              "{r.transcript}"
                            </span>
                            {hasLongText && (
                              <button
                                onClick={() => toggleExpand(r.chunk_id)}
                                className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-700 font-medium ml-2"
                              >
                                {isExpanded ? (
                                  <>
                                    Less <ChevronUp className="w-3 h-3" />
                                  </>
                                ) : (
                                  <>
                                    More <ChevronDown className="w-3 h-3" />
                                  </>
                                )}
                              </button>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">No speech detected</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-medium text-slate-700 dark:text-slate-300">
                        {r.wpm > 0 ? r.wpm : '-'}
                      </td>
                      <td className="py-2.5 px-3 text-right font-medium">
                        {r.filler_words > 0 ? (
                          <span className="inline-block px-1.5 py-0.5 rounded text-amber-700 bg-amber-50 dark:bg-amber-950/60 dark:text-amber-300 font-semibold">
                            {r.filler_words}
                          </span>
                        ) : (
                          <span className="text-slate-400">0</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-600 dark:text-slate-400">
                        {r.silence_seconds > 0 ? `${r.silence_seconds}s` : '0s'}
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-600 dark:text-slate-400">
                        {r.long_pauses > 0 ? (
                          <span className="text-rose-600 dark:text-rose-400 font-medium">
                            {r.long_pauses}
                          </span>
                        ) : (
                          '0'
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-medium">
                        {(r.face_visibility || r.visual_stability) !== 'N/A' ? (
                          <span className="text-emerald-600 dark:text-emerald-400">
                            {r.face_visibility || r.visual_stability}
                          </span>
                        ) : (
                          <span className="text-slate-400">N/A</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-medium">
                        {r.semantic_score !== 'N/A' ? (
                          <span className="text-slate-700 dark:text-slate-300">
                            {r.semantic_score}
                          </span>
                        ) : (
                          <span className="text-slate-400">N/A</span>
                        )}
                      </td>
                    </tr>
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="p-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500 bg-slate-50/30 dark:bg-slate-900/30">
          <span>
            Page {pageIndex} of {totalPages}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={pageIndex <= 1}
              className="p-1 rounded border border-slate-200 dark:border-slate-700 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              title="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={pageIndex >= totalPages}
              className="p-1 rounded border border-slate-200 dark:border-slate-700 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              title="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
