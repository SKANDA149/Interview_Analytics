import { JobStatusResponse } from '../api/types';

export interface ActiveJob {
  job_id: string;
  submission_time: string;
}

const key = (apiUrl: string) => `interview-analytics:active-job:${apiUrl}`;

// Session storage survives refresh/navigation in this tab. No video or transcript
// is stored, and separate API environments cannot restore each other's job IDs.
export function readActiveJob(apiUrl: string): ActiveJob | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(key(apiUrl)) || 'null');
    if (value && typeof value.job_id === 'string' && /^[\w-]{1,128}$/.test(value.job_id)
      && typeof value.submission_time === 'string' && Number.isFinite(Date.parse(value.submission_time))) {
      return { job_id: value.job_id, submission_time: value.submission_time };
    }
  } catch { /* Storage may be disabled; the live job still works. */ }
  return null;
}

export function saveActiveJob(apiUrl: string, job: ActiveJob): void {
  try { sessionStorage.setItem(key(apiUrl), JSON.stringify(job)); } catch { /* Best effort. */ }
}

export function clearActiveJob(apiUrl: string): void {
  try { sessionStorage.removeItem(key(apiUrl)); } catch { /* Best effort. */ }
}

export function jobElapsedSeconds(job: Pick<JobStatusResponse, 'submission_time' | 'completion_time'>, now = Date.now()): number {
  const start = Date.parse(job.submission_time);
  const end = job.completion_time ? Date.parse(job.completion_time) : now;
  return Number.isFinite(start) && Number.isFinite(end) ? Math.max(0, Math.floor((end - start) / 1000)) : 0;
}
