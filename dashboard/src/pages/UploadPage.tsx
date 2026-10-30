import React, { useState, useRef, useEffect } from 'react';
import { apiClient, ApiError } from '../api/client';
import { JobStatusResponse } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { LogViewer } from '../components/LogViewer';
import { formatFileSize } from '../utils/formatters';
import { readActiveJob, saveActiveJob, clearActiveJob, jobElapsedSeconds } from '../utils/activeJob';
import {
  UploadCloud,
  FileVideo,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  X,
  FileText,
  Clock,
} from 'lucide-react';

interface Props {
  onViewReport: (jobId: string) => void;
}

const MAX_SIZE_MB = 500;
const MAX_BYTES = MAX_SIZE_MB * 1024 * 1024;
const ALLOWED_EXTS = ['.mp4', '.mov', '.avi', '.mkv', '.wav', '.mp3'];

export const UploadPage: React.FC<Props> = ({ onViewReport }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Active Job Tracking
  const [savedJob] = useState(() => readActiveJob(apiClient.getBaseUrl()));
  const [activeJobId, setActiveJobId] = useState<string | null>(savedJob?.job_id ?? null);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(() => savedJob ? jobElapsedSeconds({ ...savedJob, completion_time: null }) : 0);
  const [pollError, setPollError] = useState<string | null>(null);
  const [pollVersion, setPollVersion] = useState(0);
  const [failedLogs, setFailedLogs] = useState<string[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  // File validation
  const validateAndSetFile = (file: File) => {
    setFileError(null);
    setUploadError(null);

    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      setFileError(
        `Unsupported file type (${ext}). Please upload an audio or video file: ${ALLOWED_EXTS.join(', ')}`
      );
      return;
    }

    if (file.size > MAX_BYTES) {
      setFileError(
        `File size (${formatFileSize(file.size)}) exceeds the maximum limit of ${MAX_SIZE_MB} MB.`
      );
      return;
    }

    if (file.size === 0) {
      setFileError('The selected file is empty (0 bytes).');
      return;
    }

    setSelectedFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || isUploading) return;

    try {
      setIsUploading(true);
      setUploadError(null);
      setElapsedSeconds(0);

      const res = await apiClient.uploadInterview(selectedFile);
      const submissionTime = new Date().toISOString();
      saveActiveJob(apiClient.getBaseUrl(), { job_id: res.job_id, submission_time: submissionTime });
      setPollError(null);
      setActiveJobId(res.job_id);
      setJobStatus({
        job_id: res.job_id,
        status: res.status,
        submission_time: submissionTime,
        start_time: null,
        completion_time: null,
        error: null,
      });
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed. Check API connection.');
    } finally {
      setIsUploading(false);
    }
  };

  // Status Polling Effect
  useEffect(() => {
    if (!activeJobId) return;

    let mounted = true;
    let pollTimeout: ReturnType<typeof setTimeout> | null = null;
    let timerInterval: ReturnType<typeof setInterval> | null = null;

    // Increment elapsed timer while job is queued or running
    timerInterval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    const poll = async () => {
      let terminal = false;
      try {
        const statusData = await apiClient.getJobStatus(activeJobId);
        if (!mounted) return;
        setJobStatus(statusData);
        setPollError(null);
        setElapsedSeconds(jobElapsedSeconds(statusData));

        // If job completed or failed, stop polling
        if (statusData.status === 'completed' || statusData.status === 'failed') {
          terminal = true;
          clearActiveJob(apiClient.getBaseUrl());
          if (timerInterval) clearInterval(timerInterval);

          // If failed, auto-fetch logs for debugging
          if (statusData.status === 'failed') {
            try {
              setLoadingLogs(true);
              const logRes = await apiClient.getJobLogs(activeJobId);
              if (mounted) setFailedLogs(logRes.logs);
            } catch {
              // ignore log fetch failure
            } finally {
              if (mounted) setLoadingLogs(false);
            }
          }
        } else {
          saveActiveJob(apiClient.getBaseUrl(), { job_id: statusData.job_id, submission_time: statusData.submission_time });
        }
      } catch (err) {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 404) {
          terminal = true;
          clearActiveJob(apiClient.getBaseUrl());
          if (timerInterval) clearInterval(timerInterval);
          setActiveJobId(null);
          setJobStatus(null);
          setUploadError('The previous analysis is no longer available. Select a video to start another analysis.');
        } else {
          setPollError(err instanceof Error ? err.message : 'Unable to check analysis status.');
        }
      } finally {
        if (mounted && !terminal) pollTimeout = setTimeout(poll, 3000);
      }
    };

    poll();

    return () => {
      mounted = false;
      if (pollTimeout) clearTimeout(pollTimeout);
      if (timerInterval) clearInterval(timerInterval);
    };
  }, [activeJobId, pollVersion]);

  const resetForm = () => {
    setSelectedFile(null);
    clearActiveJob(apiClient.getBaseUrl());
    setPollError(null);
    setFileError(null);
    setUploadError(null);
    setActiveJobId(null);
    setJobStatus(null);
    setElapsedSeconds(0);
    setFailedLogs([]);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
          New Interview Analysis
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Upload an interview recording for automated speech, visual presence, and pacing evaluation.
        </p>
      </div>

      {!activeJobId ? (
        /* Upload Form */
        <form onSubmit={handleSubmit} className="space-y-6">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition flex flex-col items-center justify-center ${
              isDragging
                ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/20'
                : selectedFile
                ? 'border-emerald-300 dark:border-emerald-800 bg-emerald-50/20 dark:bg-emerald-950/10'
                : 'border-slate-300 dark:border-slate-700 hover:border-blue-400 bg-white dark:bg-slate-900'
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  validateAndSetFile(e.target.files[0]);
                }
              }}
              accept={ALLOWED_EXTS.join(',')}
              className="hidden"
            />

            <div className="w-14 h-14 rounded-2xl bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-4 shadow-sm">
              <UploadCloud className="w-7 h-7" />
            </div>

            <h3 className="text-base font-semibold text-slate-900 dark:text-white">
              {selectedFile ? 'Change selected file' : 'Click to select or drag and drop video'}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm">
              Supported formats: MP4, MOV, AVI, MKV, WAV, MP3 • Max size: {MAX_SIZE_MB} MB
            </p>

            {selectedFile && (
              <div
                onClick={(e) => e.stopPropagation()}
                className="mt-6 p-4 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-between gap-4 w-full max-w-md shadow-sm"
              >
                <div className="flex items-center gap-3 truncate">
                  <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950 text-blue-600">
                    <FileVideo className="w-5 h-5" />
                  </div>
                  <div className="truncate text-left">
                    <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-slate-500">
                      {formatFileSize(selectedFile.size)}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedFile(null)}
                  className="p-1 rounded text-slate-400 hover:text-slate-600 transition"
                  title="Remove file"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          {/* Validation & API Error Banners */}
          {fileError && (
            <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{fileError}</span>
            </div>
          )}

          {uploadError && (
            <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{uploadError}</span>
            </div>
          )}

          {/* Submit Action */}
          <div className="flex items-center justify-end gap-3">
            <button
              type="submit"
              disabled={!selectedFile || isUploading || !!fileError}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium text-sm shadow-sm transition"
            >
              {isUploading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Uploading to Edge Server...
                </>
              ) : (
                <>
                  <UploadCloud className="w-4 h-4" /> Start Pipeline Analysis
                </>
              )}
            </button>
          </div>
        </form>
      ) : (
        /* Real-Time Processing Status Screen */
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 sm:p-8 shadow-sm space-y-6">
          {!jobStatus && <p role="status" className="text-sm text-slate-500">Restoring your analysis status...</p>}
          {pollError && (
            <div role="alert" className="p-4 rounded-xl border border-amber-300 bg-amber-50 text-amber-900 text-sm space-y-2">
              <p>{pollError} Status checks will retry automatically.</p>
              <button type="button" onClick={() => setPollVersion((version) => version + 1)} className="underline font-medium">Retry status check</button>
            </div>
          )}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100 dark:border-slate-800">
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Active Job ID
              </span>
              <p className="text-lg font-mono font-bold text-slate-900 dark:text-white">
                {activeJobId}
              </p>
            </div>
            {jobStatus && <StatusBadge status={jobStatus.status} size="lg" />}
          </div>

          {/* Status Tracker */}
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600 dark:text-slate-300 font-medium">
                Pipeline Lifecycle:
              </span>
              <span className="font-mono text-xs text-slate-500 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" /> Elapsed: {elapsedSeconds}s
              </span>
            </div>

            {/* Stages overview */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div
                className={`p-3 rounded-xl border text-xs ${
                  jobStatus?.status !== 'queued'
                    ? 'border-emerald-200 bg-emerald-50/50 text-emerald-800 dark:bg-emerald-950/20 dark:border-emerald-800 dark:text-emerald-300'
                    : 'border-amber-200 bg-amber-50/50 text-amber-800 dark:bg-amber-950/20 dark:border-amber-800 dark:text-amber-300'
                }`}
              >
                <div className="font-semibold mb-1">1. Ingestion & Queue</div>
                <p className="text-[11px] opacity-80">
                  {jobStatus?.status === 'queued' ? 'Waiting in CPU executor queue...' : 'Accepted into SQLite'}
                </p>
              </div>

              <div
                className={`p-3 rounded-xl border text-xs ${
                  jobStatus?.status === 'running'
                    ? 'border-blue-300 bg-blue-50 text-blue-800 dark:bg-blue-950/30 dark:border-blue-800 dark:text-blue-300'
                    : jobStatus?.status === 'completed'
                    ? 'border-emerald-200 bg-emerald-50/50 text-emerald-800 dark:bg-emerald-950/20 dark:border-emerald-800 dark:text-emerald-300'
                    : 'border-slate-200 bg-slate-50 text-slate-500 dark:bg-slate-800 dark:border-slate-700'
                }`}
              >
                <div className="font-semibold mb-1">2. Multimodal Inference</div>
                <p className="text-[11px] opacity-80">
                  {jobStatus?.status === 'running'
                    ? 'VAD, Diarization, Vosk STT & YuNet running...'
                    : jobStatus?.status === 'completed'
                    ? 'Inference finished'
                    : 'Awaiting execution'}
                </p>
              </div>

              <div
                className={`p-3 rounded-xl border text-xs ${
                  jobStatus?.status === 'completed'
                    ? 'border-emerald-300 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/30 dark:border-emerald-800 dark:text-emerald-300'
                    : jobStatus?.status === 'failed'
                    ? 'border-rose-200 bg-rose-50 text-rose-800 dark:bg-rose-950/20 dark:border-rose-800 dark:text-rose-300'
                    : 'border-slate-200 bg-slate-50 text-slate-500 dark:bg-slate-800 dark:border-slate-700'
                }`}
              >
                <div className="font-semibold mb-1">3. Report Assembly</div>
                <p className="text-[11px] opacity-80">
                  {jobStatus?.status === 'completed'
                    ? 'final_report.json generated'
                    : jobStatus?.status === 'failed'
                    ? 'Failed'
                    : 'Awaiting output'}
                </p>
              </div>
            </div>
          </div>

          {/* Completed State */}
          {jobStatus?.status === 'completed' && (
            <div className="p-5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 space-y-4">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
                <div>
                  <h4 className="text-base font-semibold text-emerald-900 dark:text-emerald-200">
                    Analysis Completed Successfully!
                  </h4>
                  <p className="text-xs text-emerald-700 dark:text-emerald-300">
                    All audio chunks, speech fluency metrics, face visibility, and timeline records are ready.
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3 pt-2">
                <button
                  onClick={() => onViewReport(activeJobId)}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm shadow-sm transition"
                >
                  <FileText className="w-4 h-4" /> View Full Analytics Report <ArrowRight className="w-4 h-4" />
                </button>
                <button
                  onClick={resetForm}
                  className="px-4 py-2.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-sm font-medium hover:bg-slate-50 transition"
                >
                  Analyze Another Video
                </button>
              </div>
            </div>
          )}

          {/* Failed State */}
          {jobStatus?.status === 'failed' && (
            <div className="p-5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 space-y-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-6 h-6 text-rose-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-base font-semibold text-rose-900 dark:text-rose-200">
                    Analysis Pipeline Failed
                  </h4>
                  <p className="text-xs text-rose-700 dark:text-rose-300 mt-1 font-mono">
                    {jobStatus.error || 'The background process encountered an unhandled error.'}
                  </p>
                </div>
              </div>

              {loadingLogs && (
                <p className="text-xs text-rose-600 dark:text-rose-400 animate-pulse">
                  Loading failure diagnostic logs...
                </p>
              )}

              {failedLogs.length > 0 && (
                <div className="mt-4">
                  <LogViewer logs={failedLogs} title="Failure Logs" maxHeight="max-h-60" />
                </div>
              )}

              <div className="pt-2">
                <button
                  onClick={resetForm}
                  className="px-4 py-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-sm font-medium hover:bg-slate-50 transition"
                >
                  Try Again with Another Video
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
