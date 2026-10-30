/**
 * API and Data Types for Interview Analytics Dashboard
 * Strictly matching the FastAPI backend and final_report.json schemas.
 */

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface HealthResponse {
  status: string;
  service: string;
}

export interface JobUploadResponse {
  job_id: string;
  status: JobStatus;
  status_url: string;
}

export interface JobStatusResponse {
  job_id: string;
  original_filename?: string | null;
  status: JobStatus;
  submission_time: string;
  start_time: string | null;
  completion_time: string | null;
  error: string | null;
}

export interface JobHistoryItem {
  job_id: string;
  original_filename: string;
  status: JobStatus;
  created_at: string;
  completed_at: string | null;
  has_report: boolean;
}

export interface JobHistoryResponse {
  items: JobHistoryItem[];
  limit: number;
  offset: number;
}

export interface JobLogsResponse {
  logs: string[];
}

export interface ReportMetadata {
  input_video: string;
  total_chunks_processed: number;
  stage_timings_seconds: {
    chunking?: number;
    diarization?: number;
    visual_analysis?: number;
    per_chunk_processing?: number;
    [key: string]: number | undefined;
  };
}

export interface OverallMetrics {
  total_filler_words: number;
  total_long_pauses: number;
  total_silence_seconds: number;
  average_active_chunk_wpm?: number;
  overall_video_wpm?: number | null;
  active_speech_wpm?: number | null;
  average_words_per_minute?: number; // Deprecated backward-compatible alias for average_active_chunk_wpm
  average_face_visibility_pct?: number | null;
  average_visual_stability?: number | null; // Deprecated backward-compatible alias for average_face_visibility_pct
  // Null when no trustworthy response/rubric evaluation was available.
  average_semantic_score: number | null;
  semantic_evaluation?: SemanticEvaluation;
}

export type SemanticEvaluationStatus = 'evaluated' | 'not_evaluated' | 'legacy_similarity';

export interface SemanticEvaluation {
  status: SemanticEvaluationStatus;
  reason: string | null;
}

export interface AbsenceRun {
  start_sec?: number;
  end_sec?: number;
  duration_sec?: number;
  [key: string]: unknown;
}

export interface VisualSummary {
  face_visibility_pct?: number;
  presence_pct?: number;
  partial_visibility_pct?: number;
  head_posture_score?: string;
  total_samples?: number;
  scored_samples?: number;
  uncertain_samples?: number;
  face_loss_event_count?: number;
  longest_continuous_absence_sec?: number;
  multiple_face_events?: number;
  absence_runs?: AbsenceRun[];
}

export interface FinalReport {
  metadata: ReportMetadata;
  overall_metrics: OverallMetrics;
  visual_summary_whole_video: VisualSummary;
  full_interview_transcript: string;
}

export interface TimelineRow {
  chunk_id: string;
  transcript: string;
  filler_words: number;
  long_pauses: number;
  silence_seconds: number;
  wpm: number;
  face_visibility: string;
  face_visibility_val: number | null;
  visual_stability: string; // Deprecated backward-compatible alias
  visual_stability_val: number | null; // Deprecated backward-compatible alias
  semantic_score: string;
  semantic_score_val: number | null;
  semantic_status: SemanticEvaluationStatus;
  semantic_reason: string | null;
}

