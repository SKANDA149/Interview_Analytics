import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { JobHistoryItem } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { formatDate } from '../utils/formatters';
import {
  Video,
  CheckCircle2,
  Clock,
  AlertCircle,
  UploadCloud,
  ChevronRight,
  ShieldCheck,
  Cpu,
  Layers,
  ArrowRight,
} from 'lucide-react';

interface Props {
  onStartUpload: () => void;
  onViewDetails: (jobId: string) => void;
  onViewHistory: () => void;
}

export const OverviewPage: React.FC<Props> = ({
  onStartUpload,
  onViewDetails,
  onViewHistory,
}) => {
  const [history, setHistory] = useState<JobHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        // Fetch up to 100 history records to aggregate true counts
        const res = await apiClient.getInterviews(100, 0);
        if (mounted) {
          setHistory(res.items);
        }
      } catch (err: unknown) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to fetch interview history');
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };

    load();
    return () => {
      mounted = false;
    };
  }, []);

  const total = history.length;
  const completed = history.filter((j) => j.status === 'completed').length;
  const processing = history.filter((j) => j.status === 'running' || j.status === 'queued').length;
  const failed = history.filter((j) => j.status === 'failed').length;

  const recentItems = history.slice(0, 5);

  return (
    <div className="space-y-8">
      {/* Hero Banner */}
      <div className="bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-700 rounded-2xl p-6 sm:p-8 text-white shadow-lg relative overflow-hidden">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/15 backdrop-blur-sm text-xs font-medium mb-3">
            <Cpu className="w-3.5 h-3.5" /> Local CPU Multimedia Processing
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Automated Video Interview Analytics
          </h1>
          <p className="mt-2 text-sm sm:text-base text-blue-100 leading-relaxed">
            Privacy-first multimedia evaluation for local machines. Runs offline Vosk STT, WeSpeaker diarization, and YuNet/BlazePose visual presence without GPU or cloud APIs.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={onStartUpload}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white text-blue-700 hover:bg-blue-50 font-semibold text-sm shadow-sm transition"
            >
              <UploadCloud className="w-4 h-4" /> Start New Analysis
            </button>
            <button
              onClick={onViewHistory}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-800/60 hover:bg-blue-800/90 text-white font-medium text-sm backdrop-blur transition"
            >
              View All History <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Abstract Background pattern */}
        <div className="absolute right-0 top-0 bottom-0 w-1/3 opacity-10 pointer-events-none flex items-center justify-center">
          <Layers className="w-72 h-72 text-white" />
        </div>
      </div>

      {/* Aggregate Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Recorded</span>
            <Video className="w-4 h-4" />
          </div>
          <div className="mt-3 text-2xl font-bold text-slate-900 dark:text-white">
            {loading ? '-' : total}
          </div>
          <p className="mt-1 text-xs text-slate-400">Interviews registered in SQLite</p>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-emerald-600">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Completed</span>
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <div className="mt-3 text-2xl font-bold text-slate-900 dark:text-white">
            {loading ? '-' : completed}
          </div>
          <p className="mt-1 text-xs text-slate-400">Reports ready for review</p>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-amber-500">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">In Progress</span>
            <Clock className="w-4 h-4" />
          </div>
          <div className="mt-3 text-2xl font-bold text-slate-900 dark:text-white">
            {loading ? '-' : processing}
          </div>
          <p className="mt-1 text-xs text-slate-400">Queued or running jobs</p>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-rose-500">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Failed</span>
            <AlertCircle className="w-4 h-4" />
          </div>
          <div className="mt-3 text-2xl font-bold text-slate-900 dark:text-white">
            {loading ? '-' : failed}
          </div>
          <p className="mt-1 text-xs text-slate-400">Terminated or interrupted</p>
        </div>
      </div>

      {/* Recent Interviews Section */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">
              Recent Interviews
            </h2>
            <p className="text-xs text-slate-500">
              Latest analyses processed by the edge pipeline
            </p>
          </div>
          {total > 5 && (
            <button
              onClick={onViewHistory}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-1"
            >
              View all ({total}) <ChevronRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {loading ? (
          <div className="p-8 text-center text-sm text-slate-500">
            Loading interview history from SQLite...
          </div>
        ) : error ? (
          <div className="p-8 text-center text-rose-600 text-sm">
            {error}
          </div>
        ) : recentItems.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<Video className="w-6 h-6" />}
              title="No interviews recorded yet"
              description="Upload your first candidate video recording to begin automated speech, visual presence, and pacing evaluation."
              action={{
                label: "Upload Interview Video",
                onClick: onStartUpload,
              }}
            />
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {recentItems.map((item) => (
              <div
                key={item.job_id}
                onClick={() => onViewDetails(item.job_id)}
                className="p-4 sm:px-6 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-2.5 rounded-lg bg-blue-50 dark:bg-blue-950/50 text-blue-600 shrink-0">
                    <Video className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                      {item.original_filename}
                    </p>
                    <p className="text-xs text-slate-400 font-mono">
                      ID: {item.job_id.slice(0, 8)}... • {formatDate(item.created_at)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4 shrink-0">
                  <StatusBadge status={item.status} size="sm" />
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* System Highlights / Trust Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2 text-slate-800 dark:text-slate-200 font-semibold text-xs mb-1">
            <ShieldCheck className="w-4 h-4 text-emerald-600" /> Privacy & Local-First
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            Zero cloud API dependencies. Audio transcription and face analytics remain 100% on your local hardware.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2 text-slate-800 dark:text-slate-200 font-semibold text-xs mb-1">
            <Cpu className="w-4 h-4 text-blue-600" /> Micro-Chunk Pipelining
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            FFmpeg splits recordings into chunks for processing on consumer laptops. Memory use varies with recording length, models, and visual samples.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2 text-slate-800 dark:text-slate-200 font-semibold text-xs mb-1">
            <Layers className="w-4 h-4 text-purple-600" /> Automatic Diarization
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            WeSpeaker ResNet34 and Silero VAD group speech into speakers. A duration heuristic assigns candidate and interviewer roles before visual sampling.
          </p>
        </div>
      </div>
    </div>
  );
};
