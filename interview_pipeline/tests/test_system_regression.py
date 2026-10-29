"""Regression coverage for issues found during full-system validation."""
import csv
import json

import pytest

from interview_pipeline.src.chunking import get_chunk_time_ranges
from interview_pipeline.src.report_generator import generate_final_report


def test_visual_chunk_windows_follow_ffmpeg_boundaries(tmp_path):
    chunks = [tmp_path / f"chunk_{i:03d}.mp4" for i in range(3)]
    (tmp_path / "chunk_times.csv").write_text(
        "chunk_000.mp4,0.000000,12.140000\n"
        "chunk_001.mp4,12.140000,20.900000\n"
        "chunk_002.mp4,20.900000,25.000000\n", encoding="utf-8",
    )
    windows = get_chunk_time_ranges(chunks)
    assert windows == {
        "chunk_000.mp4": (0.0, 12.14),
        "chunk_001.mp4": (12.14, 20.9),
        "chunk_002.mp4": (20.9, 25.0),
    }
    # A sample after the nominal ten-second boundary belongs only to chunk 0.
    owners = [name for name, (start, end) in windows.items() if start <= 11.0 < end]
    assert owners == ["chunk_000.mp4"]


@pytest.mark.parametrize("manifest", [None, "chunk_000.mp4,nan,20\n", "other.mp4,0,10\n"])
def test_cached_chunk_windows_use_measured_durations(tmp_path, monkeypatch, manifest):
    if manifest is not None:
        (tmp_path / "chunk_times.csv").write_text(manifest, encoding="utf-8")
    chunks = [tmp_path / "chunk_000.mp4", tmp_path / "chunk_001.mp4"]
    monkeypatch.setattr("interview_pipeline.src.chunking.get_media_duration", lambda p, **kw: 12.14 if p == chunks[0] else 3.5)
    windows = get_chunk_time_ranges(chunks)
    assert windows["chunk_000.mp4"] == (0.0, 12.14)
    assert windows["chunk_001.mp4"] == (12.14, 15.64)


def test_unavailable_visual_data_and_exported_time_bounds(tmp_path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "chunk_000.json").write_text(json.dumps({
        "chunk_id": "chunk_000", "transcript": "hello", "words": [],
        "chunk_start_sec": 12.14, "chunk_end_sec": 20.9,
        "visual_analysis": {"face_visibility_pct": "N/A", "n_samples": 0},
        "content_analysis": {"semantic_score": None, "scoring_status": "not_evaluated"},
    }), encoding="utf-8")
    reports = tmp_path / "reports"
    generate_final_report(outputs, reports)
    metrics = json.loads((reports / "final_report.json").read_text(encoding="utf-8"))["overall_metrics"]
    assert metrics["average_face_visibility_pct"] is None
    assert metrics["average_visual_stability"] is None
    with (reports / "interview_timeline.csv").open(encoding="utf-8", newline="") as source:
        row = next(csv.DictReader(source))
    assert float(row["Start_Seconds"]) == 12.14
    assert float(row["End_Seconds"]) == 20.9
    assert row["Face_Visibility"] == "N/A"
