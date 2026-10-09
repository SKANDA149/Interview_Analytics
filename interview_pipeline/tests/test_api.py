import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pathlib import Path
import json

from interview_pipeline.api.database import init_db
import interview_pipeline.api.database as db_module

# Patch the default database path for testing
TEST_DB_PATH = Path(__file__).parent / "test_interviews.db"
db_module.DEFAULT_DB_PATH = TEST_DB_PATH

from interview_pipeline.api.main import app, run_interview_pipeline

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown_db():
    """Create a fresh test database for each test and remove it afterwards."""
    init_db(TEST_DB_PATH)
    conn = db_module.get_connection(TEST_DB_PATH)
    conn.execute("DELETE FROM interviews")
    yield
    conn.execute("DELETE FROM interviews")
    db_module.close_connection()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Interview Analytics API"}

@patch("interview_pipeline.api.main.job_executor.submit")
def test_valid_upload_and_registration(mock_submit, tmp_path):
    file_content = b"fake video content"
    response = client.post(
        "/api/v1/interviews",
        files={"file": ("test_video.mp4", file_content, "video/mp4")}
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    
    # Check DB
    job_id = data["job_id"]
    job = db_module.get_job(job_id)
    assert job is not None
    assert job["status"] == "queued"
    mock_submit.assert_called_once()

def test_empty_upload_rejection():
    file_content = b""
    response = client.post(
        "/api/v1/interviews",
        files={"file": ("empty.mp4", file_content, "video/mp4")}
    )
    assert response.status_code == 400

@patch("interview_pipeline.api.main.MAX_UPLOAD_SIZE", 5)
def test_oversized_upload_rejection():
    file_content = b"123456"
    response = client.post(
        "/api/v1/interviews",
        files={"file": ("test.mp4", file_content, "video/mp4")}
    )
    assert response.status_code == 413

def test_unknown_job_404():
    response = client.get("/api/v1/interviews/not-a-real-job")
    assert response.status_code == 404

def test_report_not_ready(tmp_path):
    job_id = "fake-job-id"
    db_module.create_job(job_id, "file.mp4", str(tmp_path), str(tmp_path), str(tmp_path), str(tmp_path))
    db_module.update_job_status(job_id, "running")
    
    response = client.get(f"/api/v1/interviews/{job_id}/report")
    assert response.status_code == 409

def test_missing_final_report_results_in_failure(tmp_path):
    job_id = "test-job-runner"
    db_module.create_job(job_id, "file.mp4", str(tmp_path), str(tmp_path), str(tmp_path), str(tmp_path))
    
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
        
    job = db_module.get_job(job_id)
    assert job["status"] == "failed"
    assert "not found" in job["error_message"].lower()

def test_successful_job_completion(tmp_path):
    job_id = "test-success-job"
    report_path = tmp_path / "reports" / "final_report.json"
    db_module.create_job(job_id, "file.mp4", str(tmp_path), str(tmp_path), str(report_path), str(tmp_path))
    
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True)
    report_path.write_text('{"success": true}')
    
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
        
    job = db_module.get_job(job_id)
    assert job["status"] == "completed"
    
    response = client.get(f"/api/v1/interviews/{job_id}/report")
    assert response.status_code == 200
    assert response.json() == {"success": True}

def test_history_endpoint():
    # Insert 2 jobs
    db_module.create_job("job1", "file1.mp4", "x", "x", "x", "x")
    db_module.create_job("job2", "file2.mp4", "y", "y", "y", "y")
    
    response = client.get("/api/v1/interviews?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    # Ensure newest first (job2 was created after job1)
    assert data["items"][0]["job_id"] == "job2"
    assert data["items"][1]["job_id"] == "job1"
