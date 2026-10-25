"""Unit and regression tests for Phase 6.1 metric correctness and duration fixes.

Verifies:
- Accurate chunk duration extraction via wave / ffprobe fallback.
- Speech fluency calculations across varied chunk durations (nominal 10s, keyframe-aligned >10s, short final chunk).
- Silence and active speech boundary safeguards.
- Report generator outputs: average_face_visibility_pct, separate WPM metrics, and backward-compatible aliases.
"""
import wave
import struct
import json
import csv
from pathlib import Path
import pytest

from interview_pipeline.src.audio_extract import get_media_duration
from interview_pipeline.src.speech_analysis import analyze_speech_fluency
from interview_pipeline.src.report_generator import generate_final_report


def _create_synthetic_wav(path: Path, duration_sec: float, sample_rate: int = 16000):
    """Helper to generate a valid PCM WAV file of exact duration."""
    n_frames = int(duration_sec * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Write silent PCM frames
        wf.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))


# ─────────────────────────────────────────────────────────────────────────────
# 1. get_media_duration Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_get_media_duration_from_wav(tmp_path):
    wav_path = tmp_path / "test_11_4s.wav"
    _create_synthetic_wav(wav_path, duration_sec=11.4, sample_rate=16000)

    duration = get_media_duration(wav_path)
    assert pytest.approx(duration, abs=0.01) == 11.4


def test_get_media_duration_missing_file_fallback():
    missing = Path("non_existent_file.wav")
    assert get_media_duration(missing, default_sec=10.0) == 10.0
    assert get_media_duration(missing, default_sec=5.5) == 5.5


def test_get_media_duration_none_fallback():
    assert get_media_duration(None, default_sec=10.0) == 10.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. analyze_speech_fluency Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_speech_fluency_nominal_10s_chunk():
    """Hand-calculated case on standard 10.0s chunk:
    - Words: 'hello' (1.0 to 2.0s), 'world' (4.0 to 5.0s)
    - Gap between words = 4.0 - 2.0 = 2.0s (>= 1.5s -> 1 long pause)
    - Leading silence = 1.0s
    - Trailing silence = 10.0 - 5.0 = 5.0s
    - Total silence = 1.0 + 2.0 + 5.0 = 8.0s (80.0%)
    - Active speech = 10.0 - 8.0 = 2.0s
    - WPM = (2 words / 10.0s) * 60 = 12.0 WPM
    """
    transcript = {
        "words": [
            {"word": "hello", "start": 1.0, "end": 2.0},
            {"word": "world", "start": 4.0, "end": 5.0},
        ]
    }
    res = analyze_speech_fluency(transcript, chunk_duration_sec=10.0)

    assert res["words_per_minute"] == 12.0
    assert res["total_silence_sec"] == 8.0
    assert res["silence_ratio_pct"] == 80.0
    assert res["long_pauses_count"] == 1
    assert res["actual_chunk_duration_sec"] == 10.0
    assert res["active_speech_duration_sec"] == 2.0


def test_speech_fluency_longer_keyframe_aligned_chunk():
    """Keyframe-aligned chunk of 11.4 seconds with 30 words:
    - Duration = 11.4s
    - WPM = (30 / 11.4) * 60 = 157.9 WPM (not 180.0 WPM as when hard-coded to 10.0s!)
    """
    # 30 words evenly distributed across 10 seconds
    words = [{"word": f"w{i}", "start": 0.5 + i * 0.3, "end": 0.7 + i * 0.3} for i in range(30)]
    transcript = {"words": words}
    res = analyze_speech_fluency(transcript, chunk_duration_sec=11.4)

    assert res["words_per_minute"] == 157.9
    assert res["actual_chunk_duration_sec"] == 11.4
    assert res["active_speech_duration_sec"] > 0
    assert res["total_silence_sec"] + res["active_speech_duration_sec"] == pytest.approx(11.4, abs=0.01)


def test_speech_fluency_short_final_chunk():
    """Short final chunk of 3.5 seconds:
    - 7 words, start=0.2s, end=3.2s
    - WPM = (7 / 3.5) * 60 = 120.0 WPM
    """
    words = [{"word": f"w{i}", "start": 0.2 + i * 0.4, "end": 0.5 + i * 0.4} for i in range(7)]
    transcript = {"words": words}
    res = analyze_speech_fluency(transcript, chunk_duration_sec=3.5)

    assert res["words_per_minute"] == 120.0
    assert res["actual_chunk_duration_sec"] == 3.5
    assert res["total_silence_sec"] <= 3.5
    assert res["total_silence_sec"] + res["active_speech_duration_sec"] == pytest.approx(3.5, abs=0.01)


def test_speech_fluency_pure_silence():
    """Zero words chunk."""
    transcript = {"words": []}
    res = analyze_speech_fluency(transcript, chunk_duration_sec=10.24)

    assert res["words_per_minute"] == 0.0
    assert res["total_silence_sec"] == 10.24
    assert res["silence_ratio_pct"] == 100.0
    assert res["long_pauses_count"] == 0
    assert res["actual_chunk_duration_sec"] == 10.24
    assert res["active_speech_duration_sec"] == 0.0


def test_speech_fluency_boundary_safeguards():
    """Words timestamps extending slightly past chunk duration due to STT drift.
    Ensures silence duration cannot exceed chunk bounds.
    """
    transcript = {
        "words": [
            {"word": "edge", "start": 0.0, "end": 10.5}
        ]
    }
    res = analyze_speech_fluency(transcript, chunk_duration_sec=10.0)

    assert res["total_silence_sec"] == 0.0
    assert res["active_speech_duration_sec"] == 10.0
    assert res["silence_ratio_pct"] == 0.0
    assert res["words_per_minute"] == 6.0


# ─────────────────────────────────────────────────────────────────────────────
# 3. generate_final_report Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_generate_final_report_metric_names_and_compatibility(tmp_path):
    outputs_dir = tmp_path / "outputs"
    reports_dir = tmp_path / "reports"
    outputs_dir.mkdir(parents=True)

    # Chunk 0: Speech chunk (10.0s, 10 words, WPM=60.0, Face Vis=90%)
    chunk0 = {
        "chunk_id": "chunk_000",
        "transcript": "one two three four five six seven eight nine ten",
        "words": [{"word": f"w{i}", "start": float(i), "end": float(i)+0.5} for i in range(10)],
        "speech_analysis": {
            "filler_count": 1,
            "long_pauses_count": 0,
            "total_silence_sec": 5.0,
            "words_per_minute": 60.0,
            "actual_chunk_duration_sec": 10.0,
            "active_speech_duration_sec": 5.0,
        },
        "visual_analysis": {"face_visibility_pct": 90.0},
        "content_analysis": {"semantic_score": 50.0},
    }

    # Chunk 1: Pure silence chunk (10.0s, 0 words, WPM=0.0, Face Vis=80%)
    chunk1 = {
        "chunk_id": "chunk_001",
        "transcript": "",
        "words": [],
        "speech_analysis": {
            "filler_count": 0,
            "long_pauses_count": 0,
            "total_silence_sec": 10.0,
            "words_per_minute": 0.0,
            "actual_chunk_duration_sec": 10.0,
            "active_speech_duration_sec": 0.0,
        },
        "visual_analysis": {"face_visibility_pct": 80.0},
        "content_analysis": {"semantic_score": 0.0},
    }

    # Chunk 2: Final short chunk (5.0s, 10 words, WPM=120.0, Face Vis=100%)
    chunk2 = {
        "chunk_id": "chunk_002",
        "transcript": "alpha beta gamma delta epsilon zeta eta theta iota kappa",
        "words": [{"word": f"w{i}", "start": float(i)*0.4, "end": float(i)*0.4+0.3} for i in range(10)],
        "speech_analysis": {
            "filler_count": 0,
            "long_pauses_count": 0,
            "total_silence_sec": 2.0,
            "words_per_minute": 120.0,
            "actual_chunk_duration_sec": 5.0,
            "active_speech_duration_sec": 3.0,
        },
        "visual_analysis": {"face_visibility_pct": 100.0},
        "content_analysis": {"semantic_score": 70.0},
    }

    for c in (chunk0, chunk1, chunk2):
        with open(outputs_dir / f"{c['chunk_id']}.json", "w", encoding="utf-8") as f:
            json.dump(c, f)

    generate_final_report(
        outputs_dir=outputs_dir,
        reports_dir=reports_dir,
        visual_summary={"presence_pct": 99.0},
        input_video_name="test_video.mp4"
    )

    report_file = reports_dir / "final_report.json"
    assert report_file.exists()

    with open(report_file, "r", encoding="utf-8") as f:
        rep = json.load(f)

    metrics = rep["overall_metrics"]

    # 1. Visual metrics: verify average_face_visibility_pct and backward alias
    # (90 + 80 + 100) / 3 = 90.0%
    assert metrics["average_face_visibility_pct"] == 90.0
    assert metrics["average_visual_stability"] == 90.0  # deprecated alias matches exactly

    # 2. WPM metrics:
    # - Active chunks mean (chunks 0 and 2): (60.0 + 120.0) / 2 = 90.0 WPM
    assert metrics["average_active_chunk_wpm"] == 90.0
    assert metrics["average_words_per_minute"] == 90.0  # deprecated alias matches exactly

    # - Total words = 10 + 0 + 10 = 20 words
    # - Total duration = 10.0 + 10.0 + 5.0 = 25.0s = 0.4167 min
    # - overall_video_wpm = 20 / (25 / 60) = 48.0 WPM
    assert metrics["overall_video_wpm"] == 48.0

    # - Total active speech duration = 5.0 + 0.0 + 3.0 = 8.0s = 0.1333 min
    # - active_speech_wpm = 20 / (8 / 60) = 150.0 WPM
    assert metrics["active_speech_wpm"] == 150.0

    # 3. Metadata fields
    meta = rep["metadata"]
    assert meta["total_recognized_words"] == 20
    assert meta["total_chunk_duration_seconds"] == 25.0
    assert meta["total_active_speech_seconds"] == 8.0

    # 4. CSV timeline headers & rows
    csv_file = reports_dir / "interview_timeline.csv"
    assert csv_file.exists()

    with open(csv_file, "r", encoding="utf-8") as cf:
        reader = csv.DictReader(cf)
        headers = reader.fieldnames
        assert "Face_Visibility" in headers
        assert "Visual_Stability" in headers
        rows = list(reader)
        assert len(rows) == 3
        assert rows[0]["Face_Visibility"] == "90.0%"
        assert rows[0]["Visual_Stability"] == "90.0%"
