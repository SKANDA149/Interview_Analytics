import { describe, it, expect } from 'vitest';
import { parseTimelineCsv } from '../csvParser';

describe('parseTimelineCsv', () => {
  it('parses verified interview_timeline.csv structure properly', () => {
    const sampleCsv = `Chunk_ID,Transcript,Filler_Words,Long_Pauses,Silence_Seconds,WPM,Visual_Stability,Semantic_Score
chunk_000,"hello world, testing interview",1,0,6.96,108.0,47.2%,2.18%
chunk_001,,0,0,0.0,0.0,N/A,N/A`;

    const rows = parseTimelineCsv(sampleCsv);
    expect(rows).toHaveLength(2);

    expect(rows[0].chunk_id).toBe('chunk_000');
    expect(rows[0].transcript).toBe('hello world, testing interview');
    expect(rows[0].filler_words).toBe(1);
    expect(rows[0].long_pauses).toBe(0);
    expect(rows[0].silence_seconds).toBe(6.96);
    expect(rows[0].wpm).toBe(108.0);
    expect(rows[0].visual_stability).toBe('47.2%');
    expect(rows[0].visual_stability_val).toBe(47.2);
    expect(rows[0].semantic_score).toBe('2.18%');
    expect(rows[0].semantic_score_val).toBe(2.18);

    expect(rows[1].chunk_id).toBe('chunk_001');
    expect(rows[1].transcript).toBe('');
    expect(rows[1].visual_stability).toBe('N/A');
    expect(rows[1].visual_stability_val).toBeNull();
    expect(rows[1].semantic_score).toBe('N/A');
    expect(rows[1].semantic_score_val).toBeNull();
  });

  it('handles empty or header-only CSV cleanly', () => {
    expect(parseTimelineCsv('')).toEqual([]);
    expect(parseTimelineCsv('Chunk_ID,Transcript')).toEqual([]);
  });

  it('supports Face_Visibility column alongside legacy Visual_Stability', () => {
    const modernCsv = `Chunk_ID,Transcript,Filler_Words,Long_Pauses,Silence_Seconds,WPM,Face_Visibility,Visual_Stability,Semantic_Score
chunk_000,"testing face visibility",0,0,2.5,120.0,92.5%,92.5%,15.0%`;

    const rows = parseTimelineCsv(modernCsv);
    expect(rows).toHaveLength(1);
    expect(rows[0].face_visibility).toBe('92.5%');
    expect(rows[0].face_visibility_val).toBe(92.5);
    expect(rows[0].visual_stability).toBe('92.5%');
  });
});
