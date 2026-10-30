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

from interview_pipeline.api.main import app, run_interview_pipeline, recover_jobs

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


def test_job_status_includes_original_filename_without_changing_report_metadata(tmp_path):
    db_module.create_job('named-job', 'Original Interview.mp4', str(tmp_path), 'log', 'report', 'timeline')
    response = client.get('/api/v1/interviews/named-job')
    assert response.status_code == 200
    payload = response.json()
    assert payload['job_id'] == 'named-job'
    assert payload['original_filename'] == 'Original Interview.mp4'
    assert payload['status'] == 'queued'
    assert payload['submission_time']

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
    # Explicit times keep this chronology test independent of clock resolution.
    with patch.object(db_module, "now_iso", side_effect=[
        "2026-10-29T10:00:00+00:00",
        "2026-10-29T10:00:01+00:00",
    ]):
        db_module.create_job("job1", "file1.mp4", "x", "x", "x", "x")
        db_module.create_job("job2", "file2.mp4", "y", "y", "y", "y")
    
    response = client.get("/api/v1/interviews?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    # Ensure newest first (job2 was created after job1)
    assert data["items"][0]["job_id"] == "job2"
    assert data["items"][1]["job_id"] == "job1"


def test_history_equal_timestamps_and_pagination():
    tied_time = "2026-10-29T10:00:01+00:00"
    # Neither insertion order nor job ID alone matches the expected ordering.
    jobs = [
        ("job-a", tied_time),
        ("job-z", "2026-10-29T10:00:00+00:00"),
        ("job-c", tied_time),
        ("job-0", "2026-10-29T10:00:02+00:00"),
        ("job-b", tied_time),
    ]
    for job_id, created_at in jobs:
        with patch.object(db_module, "now_iso", return_value=created_at):
            db_module.create_job(job_id, f"{job_id}.mp4", "x", "x", "x", "x")

    expected = ["job-0", "job-c", "job-b", "job-a", "job-z"]
    for _ in range(2):
        response = client.get("/api/v1/interviews?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert set(data) == {"items", "limit", "offset"}
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert [item["job_id"] for item in data["items"]] == expected
        assert all(set(item) == {
            "job_id", "original_filename", "status", "created_at",
            "completed_at", "has_report",
        } for item in data["items"])

    # Page boundaries split the tied group without dropping or repeating jobs.
    for page_size in (1, 2, 3):
        actual = []
        for offset in range(0, len(expected) + page_size, page_size):
            response = client.get(
                f"/api/v1/interviews?limit={page_size}&offset={offset}"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == page_size
            assert data["offset"] == offset
            page_ids = [item["job_id"] for item in data["items"]]
            assert page_ids == expected[offset:offset + page_size]
            actual.extend(page_ids)
        assert actual == expected


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Interview Analytics API"
    assert data["version"] == "1.0.0"
    assert data["health_url"] == "/health"
    assert data["docs_url"] == "/docs"
    assert data["dashboard_url"] == "http://127.0.0.1:3000"


@pytest.mark.parametrize("query", ["limit=0", "limit=-1", "limit=101", "offset=-1"])
def test_history_rejects_invalid_pagination(query):
    assert client.get(f"/api/v1/interviews?{query}").status_code == 422


def test_upload_rejects_unsupported_extension():
    response = client.post("/api/v1/interviews", files={"file": ("notes.txt", b"text", "text/plain")})
    assert response.status_code == 400


@patch("interview_pipeline.api.main.job_executor.submit")
def test_startup_recovery_preserves_completed_and_handles_pending_jobs(mock_submit, tmp_path):
    input_path = tmp_path / "queued.mp4"
    input_path.write_bytes(b"test fixture")
    for job_id in ("interrupted", "missing", "queued", "done"):
        path = input_path if job_id == "queued" else tmp_path / "absent.mp4"
        db_module.create_job(job_id, "file.mp4", str(path), str(tmp_path / "log.txt"), "report", "timeline")
    db_module.update_job_status("interrupted", "running")
    db_module.update_job_status("done", "completed", process_exit_code=0)
    completed_before = db_module.get_job("done")

    recover_jobs()

    assert db_module.get_job("interrupted")["status"] == "failed"
    assert "restart" in db_module.get_job("interrupted")["error_message"]
    assert db_module.get_job("missing")["status"] == "failed"
    assert "missing" in db_module.get_job("missing")["error_message"]
    assert db_module.get_job("queued")["status"] == "queued"
    assert db_module.get_job("done") == completed_before
    mock_submit.assert_called_once()
    assert mock_submit.call_args.args[:3] == (run_interview_pipeline, "queued", input_path)

