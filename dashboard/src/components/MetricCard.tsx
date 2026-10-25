import React from 'react';
import { Info } from 'lucide-react';

interface Props {
  title: string;
  value: string | number | null | undefined;
  unit?: string;
  icon?: React.ReactNode;
  description?: string;
  badge?: {
    text: string;
    variant?: 'neutral' | 'warning' | 'info';
  };
  tooltip?: string;
}

export const MetricCard: React.FC<Props> = ({
  title,
  value,
  unit,
  icon,
  description,
  badge,
  tooltip,
}) => {
  const isAvailable = value !== null && value !== undefined && value !== 'Not available' && value !== 'N/A';
  const displayVal = isAvailable ? value : 'Not available';

  const badgeStyles = {
    neutral: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700',
    warning: 'bg-amber-50 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-800',
    info: 'bg-blue-50 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-800',
  }[badge?.variant || 'neutral'];

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm hover:shadow-md transition">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            {title}
          </span>
          {tooltip && (
            <div className="group relative cursor-help">
              <Info className="w-3.5 h-3.5 text-slate-400 hover:text-slate-600 transition" />
              <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-48 p-2 bg-slate-800 text-white text-[11px] rounded shadow-lg z-50 pointer-events-none leading-relaxed">
                {tooltip}
              </div>
            </div>
          )}
        </div>
        {icon && (
          <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
            {icon}
          </div>
        )}
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span
          className={`text-2xl font-bold tracking-tight ${
            isAvailable ? 'text-slate-900 dark:text-white' : 'text-slate-400 dark:text-slate-500 text-lg'
          }`}
        >
          {displayVal}
        </span>
        {unit && isAvailable && (
          <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
            {unit}
          </span>
        )}
      </div>

      {(description || badge) && (
        <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 gap-2">
          {description && <span className="truncate">{description}</span>}
          {badge && (
            <span
              className={`inline-block px-2 py-0.5 rounded text-[11px] font-medium border ${badgeStyles}`}
            >
              {badge.text}
            </span>
          )}
        </div>
      )}
    </div>
  );
};
