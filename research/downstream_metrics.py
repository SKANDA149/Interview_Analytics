"""
research/downstream_metrics.py

Computes candidate-only fluency/content metrics from a (possibly corrupted)
diarization segment list plus the global word list, reusing this project's
EXISTING filler_detection.detect_filler_words and nlp_scoring.evaluate_
technical_answer unmodified. The word-speaker alignment and diarization-
aware pause/silence accounting are new glue (research/global_alignment.py
and the pause loop below) since this pipeline never computed them —
approved as a necessary minimal addition for the paper's angle.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from interview_pipeline.src.filler_detection import detect_filler_words
from interview_pipeline.src.nlp_scoring import evaluate_technical_answer
from research.global_alignment import align_words_to_speakers, extract_candidate_data

# pipeline.py ships a hardcoded placeholder ideal answer about DATA STRUCTURES.
# The recording in data/ is not a data-structures answer at all -- it is a
# self-introduction and "why this company" interview. Scoring it against the
# placeholder yields a 5.73% baseline, which is the cosine noise floor between
# two topically unrelated texts, not a content-quality measurement. Any
# dose-response measured against it is drift in a meaningless quantity.
# Retained only for traceability:
LEGACY_PLACEHOLDER_IDEAL_ANSWER = (
    "Data structures are used to organize, store, and manage data efficiently "
    "so it can be accessed and modified easily."
)

# Topic-matched reference answer for THIS recording. Written once, from the
# interview's actual subject matter (candidate self-introduction: education,
# technical skills, projects, extracurriculars; then motivation for joining
# the company). It was NOT tuned against the resulting score -- it is stated
# here verbatim so the scoring target is auditable rather than hidden.
DEFAULT_IDEAL_ANSWER = (
    "I am a computer science engineering student with a strong academic record. "
    "My technical skills include programming in Python, Java, C and C++, databases, "
    "web development, and tools such as Docker, Kubernetes and Ansible. I have "
    "applied these skills in academic projects and hackathons. Outside academics I "
    "take part in cultural activities, writing and volunteering, and I have held "
    "student leadership positions. I want to join this company because of its "
    "strong brand and reputation, the work-life balance it offers, the opportunity "
    "to learn from skilled colleagues, the possibility of global exposure, and the "
    "job security that comes from an established organisation. I consider myself "
    "focused, optimistic, and a team player who works steadily towards goals."
)


def compute_metrics(segments, words, ideal_answer=None, run_nlp=True, policy="fallback"):
    """
    segments: list[Segment] (corrupted or reference)
    words: list[dict] global words ({"word","start","end"}), from
           research.global_alignment.load_global_words()
    ideal_answer: optional str, defaults to pipeline.py's hardcoded ideal answer
    run_nlp: set False to skip semantic scoring for speed
    policy: "fallback" or "strict" -- how words overlapping NO diarization
            segment are handled. See global_alignment.align_words_to_speakers.
            Materially changes WPM under the missed_speech operator.
    """
    labelled_words = align_words_to_speakers(words, segments, policy=policy)
    candidate_transcript, candidate_words = extract_candidate_data(labelled_words, "CANDIDATE")

    candidate_diar_segments = [s for s in segments if s.speaker == "CANDIDATE"]
    candidate_speech_duration = sum(s.end - s.start for s in candidate_diar_segments)

    filler_data = {"chunk_id": "full_interview", "words": candidate_words, "transcript": candidate_transcript}
    filler_result = detect_filler_words(filler_data)

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

    average_pause = round(sum(pause_durations) / len(pause_durations), 2) if pause_durations else 0.0
    silence_ratio = round(min(100.0, (candidate_silence_sec / max(1.0, candidate_speech_duration)) * 100), 1)
    wpm = round((len(candidate_words) / max(1.0, candidate_speech_duration)) * 60, 1)

    metrics = {
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
        "num_candidate_words": len(candidate_words),
    }

    nlp_result = None
    if run_nlp:
        answer = ideal_answer if ideal_answer is not None else DEFAULT_IDEAL_ANSWER
        nlp_result = evaluate_technical_answer(candidate_transcript, answer)
    metrics["nlp"] = nlp_result
    metrics["policy"] = policy
    return metrics
