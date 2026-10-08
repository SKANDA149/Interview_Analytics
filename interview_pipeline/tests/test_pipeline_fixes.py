import os
from pathlib import Path
import json
import pytest
import subprocess

from interview_pipeline.src.chunking import _chunk_sort_key
from interview_pipeline.src.report_generator import generate_final_report


def test_chunk_sorting():
    """Verify numeric extraction for chunk sorting."""
    assert _chunk_sort_key(Path("chunk_000.mp4")) == 0
    assert _chunk_sort_key(Path("chunk_005.mp4")) == 5
    assert _chunk_sort_key(Path("chunk_042.mp4")) == 42
    assert _chunk_sort_key(Path("chunk_108.mp4")) == 108
    assert _chunk_sort_key(Path("invalid_name.mp4")) == 0


def test_cli_help(capsys):
    """Verify argparse is correctly set up and intercepts --help."""
    # We call the CLI as a subprocess to test argument parsing
    cli_path = Path(__file__).resolve().parent.parent.parent / "cli.py"
    
    result = subprocess.run(
        ["python", str(cli_path), "--help"], 
        capture_output=True, 
        text=True
    )
    
    assert result.returncode == 0
    assert "--input" in result.stdout
    assert "--output-dir" in result.stdout
    assert "--diarization" in result.stdout


def test_cli_missing_input():
    """Verify CLI fails gracefully when input video is missing."""
    cli_path = Path(__file__).resolve().parent.parent.parent / "cli.py"
    
    result = subprocess.run(
        ["python", str(cli_path), "--input", "does_not_exist.mp4"], 
        capture_output=True, 
        text=True
    )
    
    # Should exit with code 1 and print error to stderr
    assert result.returncode == 1
    assert "Input video not found" in result.stderr


def test_report_aggregation_data_preservation(tmp_path):
    """Verify report_generator doesn't drop NLP or visual summary data."""
    outputs_dir = tmp_path / "outputs"
    reports_dir = tmp_path / "reports"
    outputs_dir.mkdir()
    
    # Create fake chunk JSON with NLP score
    chunk_data = {
        "chunk_id": "chunk_000",
        "transcript": "hello world",
        "speech_analysis": {},
        "visual_analysis": {"face_visibility_pct": 85.5},
        "content_analysis": {"semantic_score": 75.0, "match_level": "Excellent"}
    }
    
    (outputs_dir / "chunk_000.json").write_text(json.dumps(chunk_data), encoding="utf-8")
    
    visual_summary_mock = {
        "face_visibility_pct": 90.0,
        "presence_pct": 95.0,
        "face_loss_event_count": 2
    }
    
    generate_final_report(
        outputs_dir=outputs_dir,
        reports_dir=reports_dir,
        visual_summary=visual_summary_mock,
        stage_timings={"chunking": 1.2},
        input_video_name="test.mp4"
    )
    
    # Assert JSON report structure
    final_json_path = reports_dir / "final_report.json"
    assert final_json_path.exists()
    
    report_data = json.loads(final_json_path.read_text(encoding="utf-8"))
    
    # Check that NLP average exists
    assert report_data["overall_metrics"]["average_semantic_score"] == 75.0
    
    # Check that visual summary is preserved untouched
    assert report_data["visual_summary_whole_video"] == visual_summary_mock
    
    # Assert CSV report structure
    csv_path = reports_dir / "interview_timeline.csv"
    assert csv_path.exists()
    
    csv_content = csv_path.read_text(encoding="utf-8")
    assert "Semantic_Score" in csv_content
    assert "75.0%" in csv_content
