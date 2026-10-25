/**
 * Data and time formatters for Interview Analytics Dashboard
 */

export function formatDate(isoString: string | null | undefined): string {
  if (!isoString) return 'Not available';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return isoString;
  }
}

export function formatDurationSeconds(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || isNaN(seconds)) return 'Not available';
  if (seconds < 0) return '0s';

  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(1);

  if (mins === 0) {
    return `${secs}s`;
  }
  return `${mins}m ${secs}s`;
}

export function formatFileSize(bytes: number): string {
  if (bytes <= 0 || isNaN(bytes)) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const val = (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1);
  return `${val} ${units[i] || 'MB'}`;
}

export function formatPercentage(val: number | null | undefined, decimals = 1): string {
  if (val === null || val === undefined || isNaN(val)) return 'Not available';
  return `${val.toFixed(decimals)}%`;
}

export function formatNumber(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return 'Not available';
  return val.toLocaleString();
}
