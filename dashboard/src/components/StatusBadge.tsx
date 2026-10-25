import React from 'react';
import { JobStatus } from '../api/types';
import { CheckCircle2, AlertCircle, Clock, Loader2 } from 'lucide-react';

interface Props {
  status: JobStatus;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export const StatusBadge: React.FC<Props> = ({ status, size = 'md', showIcon = true }) => {
  const configs: Record<
    JobStatus,
    { label: string; bg: string; text: string; border: string; icon: React.ReactNode }
  > = {
    queued: {
      label: 'Queued',
      bg: 'bg-amber-50 dark:bg-amber-950/40',
      text: 'text-amber-700 dark:text-amber-300',
      border: 'border-amber-200 dark:border-amber-800',
      icon: <Clock className="w-3.5 h-3.5 animate-pulse" />,
    },
    running: {
      label: 'Processing',
      bg: 'bg-blue-50 dark:bg-blue-950/40',
      text: 'text-blue-700 dark:text-blue-300',
      border: 'border-blue-200 dark:border-blue-800',
      icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
    },
    completed: {
      label: 'Completed',
      bg: 'bg-emerald-50 dark:bg-emerald-950/40',
      text: 'text-emerald-700 dark:text-emerald-300',
      border: 'border-emerald-200 dark:border-emerald-800',
      icon: <CheckCircle2 className="w-3.5 h-3.5" />,
    },
    failed: {
      label: 'Failed',
      bg: 'bg-rose-50 dark:bg-rose-950/40',
      text: 'text-rose-700 dark:text-rose-300',
      border: 'border-rose-200 dark:border-rose-800',
      icon: <AlertCircle className="w-3.5 h-3.5" />,
    },
  };

  const config = configs[status] || configs.queued;
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
    lg: 'text-sm px-3 py-1.5 gap-2 font-medium',
  }[size];

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border ${config.bg} ${config.text} ${config.border} ${sizeClasses}`}
    >
      {showIcon && config.icon}
      <span>{config.label}</span>
    </span>
  );
};
