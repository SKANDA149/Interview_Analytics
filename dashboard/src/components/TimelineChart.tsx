import React, { useState, useMemo } from 'react';
import { TimelineRow } from '../api/types';

interface Props {
  rows: TimelineRow[];
}

export const TimelineChart: React.FC<Props> = ({ rows }) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Compute boundaries for charting
  const chartData = useMemo(() => {
    return rows.map((r, i) => ({
      index: i,
      chunkId: r.chunk_id,
      wpm: r.wpm || 0,
      silence: r.silence_seconds || 0,
      fillers: r.filler_words || 0,
      visual: r.face_visibility_val ?? r.visual_stability_val,
      transcript: r.transcript,
    }));
  }, [rows]);

  if (chartData.length === 0) {
    return null;
  }

  const maxWpm = Math.max(...chartData.map((d) => d.wpm), 200);
  const maxSilence = Math.max(...chartData.map((d) => d.silence), 10);

  // SVG dimensions
  const width = 800;
  const height = 240;
  const padding = { top: 20, right: 30, bottom: 40, left: 45 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  const getX = (i: number) => {
    if (chartData.length <= 1) return padding.left + innerWidth / 2;
    return padding.left + (i / (chartData.length - 1)) * innerWidth;
  };

  const getY_Wpm = (wpm: number) => {
    return padding.top + innerHeight - (wpm / maxWpm) * innerHeight;
  };

  const getY_Silence = (silence: number) => {
    return padding.top + innerHeight - (silence / maxSilence) * innerHeight;
  };

  // Build SVG path for WPM
  const wpmPoints = chartData.map((d, i) => `${getX(i)},${getY_Wpm(d.wpm)}`).join(' ');

  // Active hover point
  const activePoint = hoveredIndex !== null ? chartData[hoveredIndex] : null;

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
            Interview Rhythm & Speech Dynamics
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Pacing (Words Per Minute) and Silence duration across 10-second micro-chunks
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1 bg-blue-600 rounded-full" />
            <span className="text-slate-600 dark:text-slate-300 font-medium">Pacing (WPM)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2 bg-amber-400/80 rounded-sm" />
            <span className="text-slate-600 dark:text-slate-300 font-medium">Silence (Sec)</span>
          </div>
        </div>
      </div>

      <div className="relative w-full aspect-[16/6] min-h-[220px]">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full overflow-visible"
          onMouseLeave={() => setHoveredIndex(null)}
        >
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
            const y = padding.top + innerHeight * (1 - pct);
            const valWpm = Math.round(maxWpm * pct);
            return (
              <g key={pct}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={width - padding.right}
                  y2={y}
                  stroke="currentColor"
                  className="text-slate-100 dark:text-slate-800"
                  strokeDasharray="4 4"
                />
                <text
                  x={padding.left - 8}
                  y={y + 4}
                  textAnchor="end"
                  className="text-[10px] fill-slate-400"
                >
                  {valWpm}
                </text>
              </g>
            );
          })}

          {/* Silence Bars */}
          {chartData.map((d, i) => {
            const barW = Math.max(2, Math.min(12, innerWidth / chartData.length - 2));
            const x = getX(i) - barW / 2;
            const y = getY_Silence(d.silence);
            const barH = padding.top + innerHeight - y;
            return (
              <rect
                key={`silence-${i}`}
                x={x}
                y={y}
                width={barW}
                height={barH}
                className="fill-amber-400/60 hover:fill-amber-500 transition-colors cursor-pointer"
                onMouseEnter={() => setHoveredIndex(i)}
              />
            );
          })}

          {/* WPM Line */}
          <polyline
            fill="none"
            stroke="#2563eb"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={wpmPoints}
          />

          {/* Interactive Points */}
          {chartData.map((d, i) => {
            const cx = getX(i);
            const cy = getY_Wpm(d.wpm);
            const isHovered = hoveredIndex === i;

            return (
              <g key={`wpm-dot-${i}`}>
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 5 : 2.5}
                  className={`transition-all cursor-pointer ${
                    isHovered
                      ? 'fill-blue-600 stroke-white stroke-2'
                      : 'fill-blue-600 hover:fill-blue-700'
                  }`}
                  onMouseEnter={() => setHoveredIndex(i)}
                />
              </g>
            );
          })}

          {/* Hover Crosshair */}
          {activePoint && (
            <line
              x1={getX(activePoint.index)}
              y1={padding.top}
              x2={getX(activePoint.index)}
              y2={padding.top + innerHeight}
              stroke="#64748b"
              strokeWidth="1"
              strokeDasharray="3 3"
              className="pointer-events-none"
            />
          )}

          {/* X Axis labels */}
          {chartData.map((_d, i) => {
            // Show every Nth label to prevent clutter
            const step = Math.max(1, Math.floor(chartData.length / 8));
            if (i % step !== 0 && i !== chartData.length - 1) return null;

            return (
              <text
                key={`xlabel-${i}`}
                x={getX(i)}
                y={height - 15}
                textAnchor="middle"
                className="text-[10px] fill-slate-400 font-mono"
              >
                #{i}
              </text>
            );
          })}
        </svg>

        {/* HTML Tooltip on hover */}
        {activePoint && (
          <div
            className="absolute pointer-events-none bg-slate-900 text-white rounded-lg p-2.5 shadow-xl text-xs z-20 transition-all border border-slate-700"
            style={{
              left: `${Math.min(
                85,
                Math.max(15, (getX(activePoint.index) / width) * 100)
              )}%`,
              top: '15px',
              transform: 'translateX(-50%)',
            }}
          >
            <div className="font-semibold text-slate-200 border-b border-slate-800 pb-1 mb-1.5 flex justify-between gap-4">
              <span>{activePoint.chunkId}</span>
              <span className="text-slate-400 font-normal">~{activePoint.index * 10}s mark</span>
            </div>
            <div className="space-y-1 text-slate-300">
              <div className="flex justify-between gap-3">
                <span className="text-slate-400">Pacing:</span>
                <span className="font-medium text-blue-400">{activePoint.wpm} WPM</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-slate-400">Silence:</span>
                <span className="font-medium text-amber-400">{activePoint.silence}s</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-slate-400">Fillers:</span>
                <span className="font-medium">{activePoint.fillers}</span>
              </div>
              {activePoint.visual !== null && (
                <div className="flex justify-between gap-3">
                  <span className="text-slate-400">Visual Stability:</span>
                  <span className="font-medium text-emerald-400">{activePoint.visual}%</span>
                </div>
              )}
            </div>
            {activePoint.transcript && (
              <p className="mt-2 text-[11px] text-slate-400 italic max-w-xs truncate border-t border-slate-800 pt-1.5">
                "{activePoint.transcript}"
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
