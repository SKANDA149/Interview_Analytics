import { describe, it, expect } from 'vitest';
import {
  formatDate,
  formatDurationSeconds,
  formatFileSize,
  formatPercentage,
  formatNumber,
} from '../formatters';

describe('formatters', () => {
  it('formats dates safely or returns Not available on empty', () => {
    expect(formatDate(null)).toBe('Not available');
    expect(formatDate(undefined)).toBe('Not available');
    expect(formatDate('')).toBe('Not available');
    expect(formatDate('2026-10-09T09:34:03.339596+00:00')).toContain('2026');
  });

  it('formats duration in seconds and minutes cleanly', () => {
    expect(formatDurationSeconds(null)).toBe('Not available');
    expect(formatDurationSeconds(undefined)).toBe('Not available');
    expect(formatDurationSeconds(NaN)).toBe('Not available');
    expect(formatDurationSeconds(0)).toBe('0.0s');
    expect(formatDurationSeconds(45.2)).toBe('45.2s');
    expect(formatDurationSeconds(125.5)).toBe('2m 5.5s');
  });

  it('formats file sizes accurately in KB and MB', () => {
    expect(formatFileSize(0)).toBe('0 B');
    expect(formatFileSize(1024)).toBe('1.0 KB');
    expect(formatFileSize(1048576 * 2.5)).toBe('2.5 MB');
  });

  it('preserves null/undefined without turning missing metrics into zero', () => {
    expect(formatPercentage(null)).toBe('Not available');
    expect(formatPercentage(undefined)).toBe('Not available');
    expect(formatPercentage(NaN)).toBe('Not available');
    expect(formatPercentage(85.54, 1)).toBe('85.5%');

    expect(formatNumber(null)).toBe('Not available');
    expect(formatNumber(undefined)).toBe('Not available');
    expect(formatNumber(1250)).toBe('1,250');
  });
});
