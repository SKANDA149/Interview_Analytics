import {
  HealthResponse,
  JobUploadResponse,
  JobStatusResponse,
  JobHistoryResponse,
  JobLogsResponse,
  FinalReport,
} from './types';

// Read API base URL from Vite environment, defaulting to local FastAPI host
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    let errorData: unknown = null;
    try {
      const json = await res.json();
      errorData = json;
      if (json && typeof json === 'object') {
        if ('detail' in json && typeof json.detail === 'string') {
          errorDetail = json.detail;
        } else if ('message' in json && typeof json.message === 'string') {
          errorDetail = json.message;
        }
      }
    } catch {
      // response was not json
      try {
        const text = await res.text();
        if (text) errorDetail = text;
      } catch {
        // ignore
      }
    }
    throw new ApiError(errorDetail, res.status, errorData);
  }
  return res.json() as Promise<T>;
}

async function fetchApi(url: string, options?: RequestInit): Promise<Response> {
  try {
    return await fetch(url, options);
  } catch {
    throw new ApiError(
      `Unable to reach the backend at ${API_BASE_URL}. Start the API and check the dashboard connection.`,
      0,
    );
  }
}

export const apiClient = {
  getBaseUrl(): string {
    return API_BASE_URL;
  },

  async checkHealth(): Promise<HealthResponse> {
    const res = await fetchApi(`${API_BASE_URL}/health`);
    return handleResponse<HealthResponse>(res);
  },

  async uploadInterview(file: File): Promise<JobUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    // Let the browser set the multipart/form-data boundary automatically!
    const res = await fetchApi(`${API_BASE_URL}/api/v1/interviews`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<JobUploadResponse>(res);
  },

  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const res = await fetchApi(`${API_BASE_URL}/api/v1/interviews/${encodeURIComponent(jobId)}`);
    return handleResponse<JobStatusResponse>(res);
  },

  async getInterviews(limit = 20, offset = 0): Promise<JobHistoryResponse> {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    const res = await fetchApi(`${API_BASE_URL}/api/v1/interviews?${params.toString()}`);
    return handleResponse<JobHistoryResponse>(res);
  },

  async getJobReport(jobId: string): Promise<FinalReport> {
    const res = await fetchApi(`${API_BASE_URL}/api/v1/interviews/${encodeURIComponent(jobId)}/report`);
    return handleResponse<FinalReport>(res);
  },

  async getJobTimelineCsv(jobId: string): Promise<string> {
    const res = await fetchApi(`${API_BASE_URL}/api/v1/interviews/${encodeURIComponent(jobId)}/timeline`);
    if (!res.ok) {
      let detail = `Failed to download timeline (status ${res.status})`;
      try {
        const json = await res.json();
        if (json?.detail) detail = json.detail;
      } catch {
        // ignore
      }
      throw new ApiError(detail, res.status);
    }
    return res.text();
  },

  async getJobLogs(jobId: string, maxLines = 500): Promise<JobLogsResponse> {
    const res = await fetchApi(
      `${API_BASE_URL}/api/v1/interviews/${encodeURIComponent(jobId)}/logs?max_lines=${maxLines}`
    );
    return handleResponse<JobLogsResponse>(res);
  },

  async downloadReportJson(jobId: string, filename?: string): Promise<void> {
    const report = await this.getJobReport(jobId);
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || `final_report_${jobId}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  },

  async downloadTimelineCsv(jobId: string, filename?: string): Promise<void> {
    const csvContent = await this.getJobTimelineCsv(jobId);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || `interview_timeline_${jobId}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  },
};
