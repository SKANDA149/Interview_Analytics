import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { clearActiveJob, jobElapsedSeconds, readActiveJob, saveActiveJob } from '../activeJob';

describe('active analysis recovery', () => {
  let entries: Map<string, string>;
  const api = 'http://127.0.0.1:8000';
  const job = { job_id: 'test-job', submission_time: '2026-10-30T10:00:00Z' };
  beforeEach(() => {
    entries = new Map();
    vi.stubGlobal('sessionStorage', {
      getItem: (key: string) => entries.get(key) ?? null,
      setItem: (key: string, value: string) => entries.set(key, value),
      removeItem: (key: string) => entries.delete(key),
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  it('recovers only the job acknowledged by this API, storing no media or transcript', () => {
    expect(readActiveJob(api)).toBeNull();
    saveActiveJob(api, job);
    expect(readActiveJob(api)).toEqual(job);
    expect(readActiveJob('http://127.0.0.1:8015')).toBeNull();
    expect(JSON.parse([...entries.values()][0])).toEqual(job);
    clearActiveJob(api);
    expect(readActiveJob(api)).toBeNull();
  });

  it.each(['invalid json', '{}', '{"job_id":"../bad","submission_time":"2026-10-30"}', '{"job_id":"job","submission_time":"bad"}'])('ignores corrupt recovery data: %s', value => {
    saveActiveJob(api, job);
    entries.set([...entries.keys()][0], value);
    expect(readActiveJob(api)).toBeNull();
  });

  it('does not interrupt analysis when browser storage is unavailable', () => {
    const blocked = () => { throw new Error('Storage disabled'); };
    vi.stubGlobal('sessionStorage', { getItem: blocked, setItem: blocked, removeItem: blocked });
    expect(() => saveActiveJob(api, job)).not.toThrow();
    expect(readActiveJob(api)).toBeNull();
    expect(() => clearActiveJob(api)).not.toThrow();
  });

  it('restores elapsed time from server timestamps and freezes it at completion', () => {
    const now = Date.parse('2026-10-30T10:02:15Z');
    expect(jobElapsedSeconds({...job, completion_time: null}, now)).toBe(135);
    expect(jobElapsedSeconds({...job, completion_time: '2026-10-30T10:01:00Z'}, now)).toBe(60);
    expect(jobElapsedSeconds({...job, submission_time: 'bad', completion_time: null}, now)).toBe(0);
    expect(jobElapsedSeconds({...job, completion_time: null}, 0)).toBe(0);
  });
});
