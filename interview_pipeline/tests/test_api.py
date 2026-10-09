import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pathlib import Path
import json

from interview_pipeline.api.main import app, jobs, run_interview_pipeline, PROJECT_ROOT

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_jobs():
    """Clear the jobs registry before each test."""
    jobs.clear()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Interview Analytics API"}

@patch("interview_pipeline.api.main.job_executor.submit")
def test_valid_upload_and_registration(mock_submit, tmp_path):
    # Mocking a valid video file
    file_content = b"fake video content"
    response = client.post(
        "/api/v1/interviews",
        files={"file": ("test_video.mp4", file_content, "video/mp4")}
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    
    # Check job registration
    job_id = data["job_id"]
    assert job_id in jobs
    assert jobs[job_id]["status"] == "queued"
    mock_submit.assert_called_once()

def test_empty_upload_rejection():
    file_content = b""
    response = client.post(
        "/api/v1/interviews",
        files={"file": ("empty.mp4", file_content, "video/mp4")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_unsupported_file_rejection():
    file_content = b"fake content"
    response = client.post(
        "/api/v1/interviews",
        files={"file": ("test.pdf", file_content, "application/pdf")}
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()

@patch("interview_pipeline.api.main.MAX_UPLOAD_SIZE", 5) # 5 bytes limit for test
def test_oversized_upload_rejection():
    file_content = b"123456" # 6 bytes
    response = client.post(
        "/api/v1/interviews",
        files={"file": ("test.mp4", file_content, "video/mp4")}
    )
    assert response.status_code == 413
    assert "exceeds" in response.json()["detail"].lower()

def test_unknown_job_404():
    response = client.get("/api/v1/interviews/not-a-real-job")
    assert response.status_code == 404

def test_queued_status_response():
    jobs["fake-job-id"] = {
        "job_id": "fake-job-id",
        "status": "queued",
        "submission_time": "2023-01-01T00:00:00Z",
        "start_time": None,
        "completion_time": None,
        "error": None
    }
    response = client.get("/api/v1/interviews/fake-job-id")
    assert response.status_code == 200
    assert response.json()["status"] == "queued"

def test_report_not_ready():
    jobs["fake-job-id"] = {
        "job_id": "fake-job-id",
        "status": "running"
    }
    response = client.get("/api/v1/interviews/fake-job-id/report")
    assert response.status_code == 409

def test_missing_final_report_results_in_failure(tmp_path):
    # Integration test for the actual runner function
    job_id = "test-job-runner"
    jobs[job_id] = {"status": "queued"}
    
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc
        
        run_interview_pipeline(
            job_id,
            tmp_path / "video.mp4",
            tmp_path / "output",
            tmp_path / "log.txt"
        )
        
    assert jobs[job_id]["status"] == "failed"
    assert "not found" in jobs[job_id]["error"].lower()

def test_successful_job_completion(tmp_path):
    job_id = "test-success-job"
    jobs[job_id] = {"status": "queued", "output_dir": tmp_path}
    
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True)
    report_file = reports_dir / "final_report.json"
    report_file.write_text('{"success": true}')
    
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc
        
        run_interview_pipeline(
            job_id,
            tmp_path / "video.mp4",
            tmp_path,
            tmp_path / "log.txt"
        )
        
    assert jobs[job_id]["status"] == "completed"
    
    # Check report retrieval
    response = client.get(f"/api/v1/interviews/{job_id}/report")
    assert response.status_code == 200
    assert response.json() == {"success": True}

def test_subprocess_args_passed_correctly(tmp_path):
    # Verifies the exact CLI command invoked by the runner
    job_id = "test-args"
    jobs[job_id] = {"status": "queued"}
    video_path = tmp_path / "input.mp4"
    output_dir = tmp_path / "out"
    log_file = tmp_path / "log.txt"
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1) # Fail immediately so we don't have to write json
        
        run_interview_pipeline(job_id, video_path, output_dir, log_file)
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        # Should be: [sys.executable, cli_path, "--input", video_path, "--output-dir", output_dir]
        assert args[2] == "--input"
        assert args[3] == str(video_path)
        assert args[4] == "--output-dir"
        assert args[5] == str(output_dir)
        assert str(args[1]).endswith("cli.py")
