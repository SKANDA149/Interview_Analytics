import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "interview_pipeline", "src"))

from diarization import DiarizationSegment
from research.perturbation import role_swap, missed_speech
from research.downstream_metrics import compute_metrics

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def load_reference_segments():
    with open(os.path.join(DATA_DIR, "diarization", "segments.json")) as f:
        raw = json.load(f)
    return [DiarizationSegment(**item) for item in raw]


def load_words():
    with open(os.path.join(DATA_DIR, "outputs", "full_transcript.json")) as f:
        data = json.load(f)
    return data["words"]


REF = load_reference_segments()
WORDS = load_words()


def test_zero_severity_role_swap_matches_baseline_metrics():
    baseline = compute_metrics(REF, WORDS, run_nlp=False)
    corrupted = role_swap(REF, 0.0, seed=1)
    result = compute_metrics(corrupted, WORDS, run_nlp=False)
    for key in ("words_per_minute", "total_filler_words", "total_long_pauses",
                "total_short_pauses", "longest_pause_sec", "average_pause_sec",
                "total_silence_sec", "silence_ratio_pct", "total_speech_duration_sec"):
        assert baseline[key] == result[key], f"{key} differs at severity 0"


def test_zero_severity_missed_speech_matches_baseline_metrics():
    baseline = compute_metrics(REF, WORDS, run_nlp=False)
    corrupted = missed_speech(REF, 0.0, seed=1)
    result = compute_metrics(corrupted, WORDS, run_nlp=False)
    for key in ("words_per_minute", "total_filler_words", "total_long_pauses",
                "total_short_pauses", "longest_pause_sec", "average_pause_sec",
                "total_silence_sec", "silence_ratio_pct", "total_speech_duration_sec"):
        assert baseline[key] == result[key], f"{key} differs at severity 0"


def test_missed_speech_reduces_speech_duration_as_severity_increases():
    durations = []
    for severity in (0.0, 0.10, 0.25, 0.50):
        corrupted = missed_speech(REF, severity, seed=11)
        result = compute_metrics(corrupted, WORDS, run_nlp=False)
        durations.append(result["total_speech_duration_sec"])
    assert durations == sorted(durations, reverse=True)


def test_compute_metrics_runs_end_to_end_without_nlp():
    result = compute_metrics(REF, WORDS, run_nlp=False)
    for key in ("words_per_minute", "total_filler_words", "total_long_pauses",
                "silence_ratio_pct", "num_candidate_words"):
        assert key in result
    assert result["nlp"] is None
