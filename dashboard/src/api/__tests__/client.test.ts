import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient, ApiError } from '../client';

describe('ApiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('provides base URL defaulting to http://127.0.0.1:8000', () => {
    expect(apiClient.getBaseUrl()).toBe('http://127.0.0.1:8000');
  });

  it('sends upload request using multipart FormData with "file" key', async () => {
    const fakeResponse = {
      job_id: 'test-123',
      status: 'queued',
      status_url: '/api/v1/interviews/test-123',
    };

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => fakeResponse,
    });
    vi.stubGlobal('fetch', mockFetch);

    const fakeFile = new File(['fake content'], 'interview.mp4', { type: 'video/mp4' });
    const result = await apiClient.uploadInterview(fakeFile);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe('http://127.0.0.1:8000/api/v1/interviews');
    expect(options.method).toBe('POST');
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get('file')).toBe(fakeFile);
    expect(result.job_id).toBe('test-123');
  });

  it('queries job status and history with correct query params', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [], limit: 20, offset: 40 }),
    });
    vi.stubGlobal('fetch', mockFetch);

    await apiClient.getInterviews(20, 40);
    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('/api/v1/interviews?limit=20&offset=40');
  });

  it('parses error details and raises ApiError on HTTP failures', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'Processing is not yet complete.' }),
    });
    vi.stubGlobal('fetch', mockFetch);

    await expect(apiClient.getJobReport('job-pending')).rejects.toThrow(ApiError);
    await expect(apiClient.getJobReport('job-pending')).rejects.toThrow('Processing is not yet complete.');
  });
});
