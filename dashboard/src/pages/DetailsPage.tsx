import React, { useEffect, useState, useCallback } from 'react';
import { apiClient } from '../api/client';
import { FinalReport, JobStatusResponse, TimelineRow } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { MetricCard } from '../components/MetricCard';
import { TimelineChart } from '../components/TimelineChart';
import { TimelineTable } from '../components/TimelineTable';
import { LogViewer } from '../components/LogViewer';
import { parseTimelineCsv } from '../utils/csvParser';
import {
  formatDate,
  formatDurationSeconds,
  formatPercentage,
  formatNumber,
} from '../utils/formatters';
import {
  ArrowLeft,
  Download,
  FileText,
  Eye,
  MessageSquare,
  AlertTriangle,
  Copy,
  Check,
  RefreshCw,
  Cpu,
  ShieldAlert,
} from 'lucide-react';

interface Props {
  jobId: string;
  onBack: () => void;
}

export const DetailsPage: React.FC<Props> = ({ jobId, onBack }) => {
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [report, setReport] = useState<FinalReport | null>(null);
  const [timelineRows, setTimelineRows] = useState<TimelineRow[]>([]);
  const [logs, setLogs] = useState<string[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [transcriptCopied, setTranscriptCopied] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // 1. Fetch current status
      const statusData = await apiClient.getJobStatus(jobId);
      setJobStatus(statusData);

      // 2. If completed, fetch report and timeline
      if (statusData.status === 'completed') {
        const reportData = await apiClient.getJobReport(jobId);
        setReport(reportData);

        try {
          const csvText = await apiClient.getJobTimelineCsv(jobId);
          const parsed = parseTimelineCsv(csvText);
          setTimelineRows(parsed);
        } catch (csvErr) {
          console.warn('Failed to fetch timeline CSV:', csvErr);
        }
      } else if (statusData.status === 'failed') {
        // If failed, fetch logs
        try {
          const logData = await apiClient.getJobLogs(jobId);
          setLogs(logData.logs);
        } catch (logErr) {
          console.warn('Failed to fetch logs:', logErr);
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load interview details');
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle report downloads
  const handleDownloadJson = async () => {
    try {
      setIsDownloading(true);
      const filename = report?.metadata?.input_video
        ? `final_report_${report.metadata.input_video.replace(/\.[^/.]+$/, '')}.json`
        : `final_report_${jobId}.json`;
      await apiClient.downloadReportJson(jobId, filename);
    } catch (err) {
      alert(`Download failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleDownloadCsv = async () => {
    try {
      setIsDownloading(true);
      const filename = report?.metadata?.input_video
        ? `interview_timeline_${report.metadata.input_video.replace(/\.[^/.]+$/, '')}.csv`
        : `interview_timeline_${jobId}.csv`;
      await apiClient.downloadTimelineCsv(jobId, filename);
    } catch (err) {
      alert(`Download failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsDownloading(false);
    }
  };

  const copyTranscript = () => {
    if (!report?.full_interview_transcript) return;
    navigator.clipboard.writeText(report.full_interview_transcript);
    setTranscriptCopied(true);
    setTimeout(() => setTranscriptCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="py-20 text-center">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-600 mb-3" />
        <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">
          Loading Interview Analytics...
        </h3>
        <p className="text-xs text-slate-500 mt-1">Retrieving verified report from edge storage</p>
      </div>
    );
  }

  if (error || !jobStatus) {
    return (
      <div className="max-w-xl mx-auto py-12 text-center space-y-4">
        <div className="w-12 h-12 rounded-xl bg-rose-50 dark:bg-rose-950 text-rose-600 flex items-center justify-center mx-auto">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h3 className="text-lg font-bold text-slate-900 dark:text-white">
          Unable to Load Interview
        </h3>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {error || 'The requested job ID could not be found in the database.'}
        </p>
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium transition"
        >
          <ArrowLeft className="w-4 h-4" /> Back to History
        </button>
      </div>
    );
  }

  const isCompleted = jobStatus.status === 'completed';
  const isFailed = jobStatus.status === 'failed';
  const isProcessing = jobStatus.status === 'running' || jobStatus.status === 'queued';

  const metrics = report?.overall_metrics;
  const visual = report?.visual_summary_whole_video;
  const timings = report?.metadata?.stage_timings_seconds;

  return (
    <div className="space-y-8">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
            title="Back to interview history"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
                {report?.metadata?.input_video || `Interview ${jobId.slice(0, 8)}`}
              </h1>
              <StatusBadge status={jobStatus.status} size="sm" />
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Job ID: {jobId} • Submitted: {formatDate(jobStatus.submission_time)}
            </p>
          </div>
        </div>

        {/* Action Buttons (Download JSON & CSV) */}
        {isCompleted && (
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleDownloadCsv}
              disabled={isDownloading}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg shadow-sm transition"
              title="Download chunk-by-chunk metrics CSV"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Timeline (CSV)</span>
            </button>

            <button
              onClick={handleDownloadJson}
              disabled={isDownloading}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition"
              title="Download authoritative final_report.json"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Report (JSON)</span>
            </button>
          </div>
        )}
      </div>

      {/* When Job is In Progress */}
      {isProcessing && (
        <div className="p-8 rounded-2xl bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mx-auto" />
          <h3 className="text-base font-semibold text-blue-950 dark:text-blue-200">
            Interview is currently {jobStatus.status}...
          </h3>
          <p className="text-xs text-blue-700 dark:text-blue-300 max-w-md mx-auto">
            The single-worker CPU executor is running VAD, WeSpeaker diarization, Vosk STT, and YuNet face tracking. This may take a few minutes on consumer laptops.
          </p>
          <button
            onClick={loadData}
            className="px-4 py-1.5 text-xs font-medium rounded-lg bg-white dark:bg-slate-800 border border-blue-200 text-blue-700 dark:text-blue-300 hover:bg-blue-50 transition"
          >
            Check Status Again
          </button>
        </div>
      )}

      {/* When Job has Failed */}
      {isFailed && (
        <div className="space-y-6">
          <div className="p-5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800">
            <div className="flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-rose-900 dark:text-rose-200">
                  Execution Terminated with Error
                </h4>
                <p className="text-xs text-rose-700 dark:text-rose-300 font-mono mt-1">
                  {jobStatus.error || 'Pipeline exited with non-zero status.'}
                </p>
              </div>
            </div>
          </div>

          <LogViewer logs={logs} title="Process Output & Traceback" maxHeight="max-h-96" />
        </div>
      )}

      {/* Completed Report Content */}
      {isCompleted && (
        <div className="space-y-8">
          {/* Section 1: Key Performance Metrics Grid */}
          <div>
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-3">
              Key Performance Indicators
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
              <MetricCard
                title="Pacing"
                value={metrics?.average_active_chunk_wpm ?? metrics?.average_words_per_minute}
                unit="WPM"
                description={
                  metrics?.overall_video_wpm != null
                    ? `Active chunks (Overall: ${metrics.overall_video_wpm} WPM)`
                    : "Speech rate across active chunks"
                }
                tooltip={
                  `Active chunk rate: ${metrics?.average_active_chunk_wpm ?? metrics?.average_words_per_minute ?? 'N/A'} WPM (mean of speech chunks).` +
                  (metrics?.overall_video_wpm != null ? ` Overall video pacing: ${metrics.overall_video_wpm} WPM (total words / total minutes).` : '') +
                  (metrics?.active_speech_wpm != null ? ` Net speech rate: ${metrics.active_speech_wpm} WPM.` : '')
                }
              />

              <MetricCard
                title="Vocal Fillers"
                value={metrics?.total_filler_words}
                unit="words"
                description="Detected hesitation markers"
                tooltip="Matches vocal filler patterns: um, uh, like, so, and you know."
              />

              <MetricCard
                title="Total Silence"
                value={formatDurationSeconds(metrics?.total_silence_seconds)}
                description="Aggregated pause duration"
                tooltip="Sum of silent intervals between detected speech phrases."
              />

              <MetricCard
                title="Long Pauses"
                value={metrics?.total_long_pauses}
                unit="instances"
                description="Hesitation gaps ≥ 1.5s"
                tooltip="Number of pauses exceeding 1.5 seconds during candidate responses."
              />

              <MetricCard
                title="Full Visibility"
                value={visual?.face_visibility_pct}
                unit="%"
                description="Both shoulders & face visible"
                tooltip="Percentage of scored candidate frames with both face and both shoulders fully visible via BlazePose."
              />

              <MetricCard
                title="Visual Presence"
                value={visual?.presence_pct}
                unit="%"
                description="Candidate in camera frame"
                tooltip="Percentage of candidate speech duration where candidate face was detected by YuNet."
              />
            </div>
          </div>

          {/* Section 2: Visual Presence & Semantic Score Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Visual Analytics Deep Dive */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Eye className="w-4 h-4 text-emerald-600" />
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
                    Visual Presence & Posture Analysis
                  </h4>
                </div>
                <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                  YuNet + BlazePose
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1 text-xs">
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-slate-400">Mean Chunk Face Visibility:</span>
                  <p className="font-semibold text-slate-800 dark:text-slate-200 text-sm mt-0.5">
                    {formatPercentage(metrics?.average_face_visibility_pct ?? metrics?.average_visual_stability)}
                  </p>
                </div>

                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-slate-400">Partial Visibility:</span>
                  <p className="font-semibold text-slate-800 dark:text-slate-200 text-sm mt-0.5">
                    {formatPercentage(visual?.partial_visibility_pct)}
                  </p>
                </div>

                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-slate-400">Total Frames Scored:</span>
                  <p className="font-semibold text-slate-800 dark:text-slate-200 text-sm mt-0.5">
                    {formatNumber(visual?.scored_samples)}
                  </p>
                </div>

                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-slate-400">Face Loss Events:</span>
                  <p className="font-semibold text-slate-800 dark:text-slate-200 text-sm mt-0.5">
                    {visual?.face_loss_event_count ?? 'Not available'}
                  </p>
                </div>
              </div>

              <p className="text-[11px] text-slate-400 leading-relaxed italic">
                * Note: Chunk-level visual metrics reflect on-screen face visibility percentages; head-pose and posture stability scores are not computed. Visual analysis is gated to Candidate intervals.
              </p>
            </div>

            {/* Semantic Scoring Deep Dive */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-blue-600" />
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
                    Semantic Content Evaluation
                  </h4>
                </div>
                <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                  Context-Limited
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 space-y-1">
                <div className="flex items-baseline justify-between">
                  <span className="text-xs text-slate-500">Average Chunk Similarity:</span>
                  <span className="text-lg font-bold text-slate-900 dark:text-white">
                    {formatPercentage(metrics?.average_semantic_score)}
                  </span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-blue-600 h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(100, Math.max(0, metrics?.average_semantic_score || 0))}%`,
                    }}
                  />
                </div>
              </div>

              <div className="p-3 rounded-lg border border-amber-200 dark:border-amber-800/60 bg-amber-50/50 dark:bg-amber-950/20 text-xs text-amber-900 dark:text-amber-300 leading-relaxed space-y-1">
                <div className="font-semibold flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  Technical Limitation Note:
                </div>
                <p className="text-[11px] opacity-90">
                  Sentence-Transformers (MiniLM-L6-v2) currently compares chunks against a static benchmark answer ("Data structures..."). This metric indicates vocabulary alignment with technical keys, not overall human conversational intelligence.
                </p>
              </div>
            </div>
          </div>

          {/* Section 3: Time-Series Chart */}
          {timelineRows.length > 0 && <TimelineChart rows={timelineRows} />}

          {/* Section 4: Chunk-by-Chunk Timeline Table */}
          {timelineRows.length > 0 && <TimelineTable rows={timelineRows} />}

          {/* Section 5: Full Interview Transcript */}
          {report?.full_interview_transcript && (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm p-6 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-blue-600" />
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
                    Full Interview Stitched Transcript
                  </h4>
                  <span className="text-xs text-slate-400">
                    ({report.full_interview_transcript.split(/\s+/).filter(Boolean).length} words)
                  </span>
                </div>

                <button
                  onClick={copyTranscript}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition"
                  title="Copy full transcript"
                >
                  {transcriptCopied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy Transcript</span>
                    </>
                  )}
                </button>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-sans max-h-72 overflow-y-auto whitespace-pre-wrap select-text">
                {report.full_interview_transcript}
              </div>
            </div>
          )}

          {/* Section 6: Pipeline Execution Timings */}
          {timings && (
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-500">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-slate-400" />
                <span className="font-semibold text-slate-700 dark:text-slate-300">
                  Execution Stage Breakdown:
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-4 font-mono text-[11px]">
                {timings.chunking !== undefined && (
                  <span>Chunking: {timings.chunking}s</span>
                )}
                {timings.diarization !== undefined && (
                  <span>Diarization: {timings.diarization}s</span>
                )}
                {timings.visual_analysis !== undefined && (
                  <span>Visual Analysis: {timings.visual_analysis}s</span>
                )}
                {timings.per_chunk_processing !== undefined && (
                  <span>Per-Chunk Loop: {timings.per_chunk_processing}s</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
