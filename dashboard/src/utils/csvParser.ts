import { TimelineRow } from '../api/types';

/**
 * Parses raw CSV text into an array of string fields, handling quotes and commas.
 */
function parseCsvLine(line: string): string[] {
  const fields: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];

    if (char === '"') {
      if (inQuotes && i + 1 < line.length && line[i + 1] === '"') {
        current += '"';
        i++; // skip escaped quote
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      fields.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  fields.push(current.trim());
  return fields;
}

/**
 * Parses the raw interview_timeline.csv text into structured TimelineRow objects.
 */
export function parseTimelineCsv(csvText: string): TimelineRow[] {
  if (!csvText || !csvText.trim()) return [];

  const lines = csvText
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);

  if (lines.length < 2) return [];

  // Parse header
  const headers = parseCsvLine(lines[0]).map((h) => h.toLowerCase());
  const chunkIdx = headers.indexOf('chunk_id');
  const transcriptIdx = headers.indexOf('transcript');
  const fillerIdx = headers.indexOf('filler_words');
  const pauseIdx = headers.indexOf('long_pauses');
  const silenceIdx = headers.indexOf('silence_seconds');
  const wpmIdx = headers.indexOf('wpm');
  const visualIdx =
    headers.indexOf('face_visibility') !== -1
      ? headers.indexOf('face_visibility')
      : headers.indexOf('visual_stability');
  const semanticIdx = headers.indexOf('semantic_score');
  const semanticStatusIdx = headers.indexOf('semantic_status');
  const semanticReasonIdx = headers.indexOf('semantic_reason');

  const rows: TimelineRow[] = [];

  for (let i = 1; i < lines.length; i++) {
    const fields = parseCsvLine(lines[i]);
    if (fields.length === 0 || (fields.length === 1 && !fields[0])) continue;

    const chunk_id = chunkIdx >= 0 ? fields[chunkIdx] || `chunk_${i - 1}` : `chunk_${i - 1}`;
    const transcript = transcriptIdx >= 0 ? fields[transcriptIdx] || '' : '';
    const filler_words = fillerIdx >= 0 ? parseInt(fields[fillerIdx], 10) || 0 : 0;
    const long_pauses = pauseIdx >= 0 ? parseInt(fields[pauseIdx], 10) || 0 : 0;
    const silence_seconds = silenceIdx >= 0 ? parseFloat(fields[silenceIdx]) || 0.0 : 0.0;
    const wpm = wpmIdx >= 0 ? parseFloat(fields[wpmIdx]) || 0.0 : 0.0;

    const visual_raw = visualIdx >= 0 ? fields[visualIdx] || 'N/A' : 'N/A';
    const visual_num = parseFloat(visual_raw.replace('%', ''));
    const visual_val = isNaN(visual_num) ? null : visual_num;

    const semantic_raw = semanticIdx >= 0 ? fields[semanticIdx] || 'N/A' : 'N/A';
    const semantic_num = parseFloat(semantic_raw.replace('%', ''));
    const semantic_score_val = isNaN(semantic_num) ? null : semantic_num;
    const semantic_status = semanticStatusIdx >= 0
      ? fields[semanticStatusIdx] || 'not_evaluated'
      : semantic_score_val === null ? 'not_evaluated' : 'legacy_similarity';
    const semantic_reason = semanticReasonIdx >= 0 ? fields[semanticReasonIdx] || null : null;

    rows.push({
      chunk_id,
      transcript,
      filler_words,
      long_pauses,
      silence_seconds: Math.round(silence_seconds * 100) / 100,
      wpm: Math.round(wpm * 10) / 10,
      face_visibility: visual_raw,
      face_visibility_val: visual_val,
      visual_stability: visual_raw,
      visual_stability_val: visual_val,
      semantic_score: semantic_raw,
      semantic_score_val,
      semantic_status: semantic_status as TimelineRow['semantic_status'],
      semantic_reason,
    });
  }

  return rows;
}
