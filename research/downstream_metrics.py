"""
research/downstream_metrics.py

Replicates pipeline.py Stage 8-11 (word-speaker alignment -> candidate
extraction -> speech/fluency analysis -> semantic NLP scoring) so that
corrupted diarization variants can be re-scored WITHOUT touching or
redesigning the production pipeline. All logic below is copied verbatim
from interview_pipeline/src/pipeline.py (lines ~264-402) and calls only
existing, unmodified pipeline functions.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from interview_pipeline.src.speaker_alignment import (
    align_words_to_speakers,
    build_speaker_turns,
    extract_candidate_data,
    LabelledWord,
)
from interview_pipeline.src.filler_detection import detect_filler_words

try:
    from interview_pipeline.src.nlp_scoring import evaluate_technical_answer
    _NLP_AVAILABLE = True
except Exception:
    _NLP_AVAILABLE = False

DEFAULT_NLP_CONFIG = {
    "job_description": "Software engineering role involving problem-solving, system design, coding, and teamwork. The candidate should demonstrate technical competence, communication skills, and cultural fit.",
    "qualifications": "Bachelor's degree in Computer Science or related field\nStrong analytical and problem-solving abilities\nGood verbal and written communication skills",
    "responsibilities": "Develop and maintain software applications\nCollaborate with cross-functional teams\nParticipate in code reviews and design discussions",
    "key_skills": ["problem solving", "communication", "teamwork", "programming", "system design"],
}


def compute_metrics(diarization_segments, words, nlp_config=None, run_nlp=True):
    """
    Faithful re-implementation of pipeline.py Stages 8-11.

    diarization_segments: list[DiarizationSegment] (start, end, speaker)
    words: list[dict] with at least "word","start","end" (Whisper words)
    nlp_config: optional dict, defaults to pipeline.py's default config
    run_nlp: set False to skip Stage 11 (semantic scoring) for speed;
             speech/fluency metrics are unaffected by diarization-only
             corruption operators in a way that still needs NLP re-run
             per condition, so leave True unless explicitly profiling.

    Returns a dict matching pipeline.py's speech_metrics keys plus
    an "nlp" sub-dict (or None if skipped/unavailable).
    """
    # Stage 8: Word-Speaker Alignment
    if diarization_segments and words:
        labelled_words = align_words_to_speakers(words, diarization_segments)
    else:
        labelled_words = [
            LabelledWord(word=w["word"], start=w["start"], end=w["end"], speaker="CANDIDATE")
            for w in words
        ]
    speaker_turns = build_speaker_turns(labelled_words)

    # Stage 9: Candidate Extraction
    candidate_transcript, candidate_words = extract_candidate_data(labelled_words, "CANDIDATE")

    # Stage 10: Speech & Fluency Analysis
    candidate_diar_segments = []
    if diarization_segments:
        candidate_diar_segments = [seg for seg in diarization_segments if seg.speaker == "CANDIDATE"]
        candidate_speech_duration = sum(seg.end - seg.start for seg in candidate_diar_segments)
    elif candidate_words:
        candidate_speech_duration = candidate_words[-1]["end"] - candidate_words[0]["start"]
    else:
        candidate_speech_duration = 0.0

    candidate_data = {
        "chunk_id": "full_interview",
        "words": candidate_words,
        "transcript": candidate_transcript,
    }
    filler_result = detect_filler_words(candidate_data)

    candidate_silence_sec = 0.0
    long_pauses = 0
    short_pauses = 0
    longest_pause = 0.0
    pause_durations = []

    if candidate_words and candidate_diar_segments:
        for i in range(len(candidate_words) - 1):
            gap_start = candidate_words[i]["end"]
            gap_end = candidate_words[i + 1]["start"]
            if gap_end <= gap_start:
                continue
            gap_in_candidate = 0.0
            for seg in candidate_diar_segments:
                overlap_start = max(gap_start, seg.start)
                overlap_end = min(gap_end, seg.end)
                if overlap_end > overlap_start:
                    gap_in_candidate += (overlap_end - overlap_start)
            if gap_in_candidate > 0:
                candidate_silence_sec += gap_in_candidate
                pause_durations.append(gap_in_candidate)
                if gap_in_candidate >= 1.5:
                    long_pauses += 1
                elif gap_in_candidate >= 0.3:
                    short_pauses += 1
                if gap_in_candidate > longest_pause:
                    longest_pause = gap_in_candidate
    elif candidate_words and not candidate_diar_segments:
        for i in range(len(candidate_words) - 1):
            gap = candidate_words[i + 1]["start"] - candidate_words[i]["end"]
            if gap > 0:
                candidate_silence_sec += gap
                pause_durations.append(gap)
                if gap >= 1.5:
                    long_pauses += 1
                elif gap >= 0.3:
                    short_pauses += 1
                if gap > longest_pause:
                    longest_pause = gap

    average_pause = round(sum(pause_durations) / len(pause_durations), 2) if pause_durations else 0.0
    silence_ratio = round(min(100.0, (candidate_silence_sec / max(1.0, candidate_speech_duration)) * 100), 1)
    wpm = round((len(candidate_words) / max(1.0, candidate_speech_duration)) * 60, 1)

    speech_metrics = {
        "total_speech_duration_sec": round(candidate_speech_duration, 2),
        "words_per_minute": wpm,
        "total_filler_words": filler_result["filler_count"],
        "filler_details": filler_result["filler_words"],
        "total_long_pauses": long_pauses,
        "total_short_pauses": short_pauses,
        "longest_pause_sec": round(longest_pause, 2),
        "average_pause_sec": average_pause,
        "total_silence_sec": round(candidate_silence_sec, 2),
        "silence_ratio_pct": silence_ratio,
    }

    # Stage 11: Semantic NLP Scoring
    nlp_result = None
    if run_nlp and _NLP_AVAILABLE:
        cfg = nlp_config if nlp_config is not None else DEFAULT_NLP_CONFIG
        nlp_result = evaluate_technical_answer(candidate_transcript, cfg)

    speech_metrics["nlp"] = nlp_result
    speech_metrics["num_speaker_turns"] = len(speaker_turns)
    speech_metrics["num_candidate_words"] = len(candidate_words)
    return speech_metrics
