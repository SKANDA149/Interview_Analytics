import os
import sys
import uuid
import time
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime, timezone
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, status, Request, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from interview_pipeline.api.database import (
    init_db, create_job, get_job, update_job_status, 
    list_jobs, get_jobs_by_status
)

# Configuration
MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
API_RUNS_DIR = PROJECT_ROOT / "data" / "api_runs"
API_RUNS_DIR.mkdir(parents=True, exist_ok=True)

# Single-worker queue to prevent CPU saturation
job_executor = ThreadPoolExecutor(max_workers=1)

def recover_jobs():
    """Recover jobs on startup."""
    init_db()
    
    # 1. Running jobs -> mark as failed (interrupted by restart)
    running_jobs = get_jobs_by_status("running")
    for job in running_jobs:
        update_job_status(
            job_id=job["job_id"],
            status="failed",
            error_message="Job interrupted by server restart."
        )
        print(f"[RECOVERY] Marked running job {job['job_id']} as failed.")
        
    # 2. Queued jobs -> re-queue them
    queued_jobs = get_jobs_by_status("queued")
    for job in queued_jobs:
        video_path = Path(job["stored_input_path"])
        job_dir = API_RUNS_DIR / job["job_id"]
        output_dir = job_dir / "output"
        log_file = Path(job["processing_log_path"])
        
        if video_path.exists():
            print(f"[RECOVERY] Re-queuing job {job['job_id']}.")
            job_executor.submit(run_interview_pipeline, job["job_id"], video_path, output_dir, log_file)
        else:
            update_job_status(
                job_id=job["job_id"],
                status="failed",
                error_message="Queued job input video is missing on disk."
            )
            print(f"[RECOVERY] Failed queued job {job['job_id']} (missing file).")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    recover_jobs()
    yield
    # Shutdown
    job_executor.shutdown(wait=False)

# Application state
app = FastAPI(
    title="Interview Analytics API",
    version="1.0.0",
    description="API for edge-based local interview analytics with SQLite persistence",
    lifespan=lifespan
)

# CORS Configuration
allowed_origins_env = os.environ.get("INTERVIEW_API_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class JobStatusResponse(BaseModel):
    job_id: str
    original_filename: str | None = None
    status: str
    submission_time: str
    start_time: str | None = None
    completion_time: str | None = None
    error: str | None = None

class JobHistoryList(BaseModel):
    items: list
    limit: int
    offset: int

def run_interview_pipeline(job_id: str, video_path: Path, output_dir: Path, log_file: Path):
    """Background worker task to run the CLI."""
    update_job_status(job_id, "running")
    
    cli_path = PROJECT_ROOT / "cli.py"
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n--- Starting Job {job_id} ---\n")
            proc = subprocess.run(
                [sys.executable, str(cli_path), "--input", str(video_path), "--output-dir", str(output_dir)],
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=str(PROJECT_ROOT)
            )
            f.write(f"\n--- Process exited with code {proc.returncode} ---\n")
            
        if proc.returncode != 0:
            update_job_status(
                job_id, "failed",
                error_message=f"Pipeline subprocess failed with exit code {proc.returncode}.",
                process_exit_code=proc.returncode
            )
            return

        # Check for expected outputs
        final_report_path = output_dir / "reports" / "final_report.json"
        if not final_report_path.exists():
            update_job_status(
                job_id, "failed",
                error_message="Pipeline completed but final_report.json was not found.",
                process_exit_code=proc.returncode
            )
            return
            
        # Verify JSON is valid
        try:
            with open(final_report_path, "r", encoding="utf-8") as rf:
                json.load(rf)
        except json.JSONDecodeError:
            update_job_status(
                job_id, "failed",
                error_message="Pipeline completed but final_report.json is invalid JSON.",
                process_exit_code=proc.returncode
            )
            return

        # Success
        update_job_status(job_id, "completed", process_exit_code=proc.returncode)
        
    except Exception as e:
        update_job_status(
            job_id, "failed",
            error_message=f"Unexpected execution error: {str(e)}"
        )


@app.get("/")
def root():
    return {
        "service": "Interview Analytics API",
        "version": "1.0.0",
        "health_url": "/health",
        "docs_url": "/docs",
        "dashboard_url": "http://127.0.0.1:3000"
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Interview Analytics API"}

@app.post("/api/v1/interviews", status_code=status.HTTP_202_ACCEPTED)
def upload_interview(request: Request, file: UploadFile = File(...)):
    # Validate extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty file or no filename provided")
        
    ext = Path(file.filename).suffix.lower()
    if ext not in [".mp4", ".mov", ".avi", ".mkv", ".wav", ".mp3"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {ext}")
        
    job_id = str(uuid.uuid4())
    job_dir = API_RUNS_DIR / job_id
    input_dir = job_dir / "input"
    output_dir = job_dir / "output"
    
    try:
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job directories: {str(e)}")

    server_filename = f"interview_{job_id}{ext}"
    video_path = input_dir / server_filename
    log_file = job_dir / "processing.log"
    report_path = output_dir / "reports" / "final_report.json"
    timeline_path = output_dir / "reports" / "interview_timeline.csv"
    
    # Save the uploaded file with size limit enforcement
    try:
        bytes_written = 0
        with open(video_path, "wb") as out_file:
            while content := file.file.read(1024 * 1024):  # 1MB chunks
                bytes_written += len(content)
                if bytes_written > MAX_UPLOAD_SIZE:
                    out_file.close()
                    shutil.rmtree(job_dir, ignore_errors=True)
                    raise HTTPException(status_code=413, detail=f"File exceeds maximum upload size of {MAX_UPLOAD_SIZE // (1024*1024)} MB")
                out_file.write(content)
                
        if bytes_written == 0:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            
    except HTTPException:
        raise
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {str(e)}")
        
    # Register job in SQLite
    create_job(
        job_id=job_id,
        original_filename=file.filename,
        stored_input_path=str(video_path),
        processing_log_path=str(log_file),
        report_path=str(report_path),
        timeline_path=str(timeline_path)
    )
    
    # Queue the job
    job_executor.submit(run_interview_pipeline, job_id, video_path, output_dir, log_file)
    
    return {
        "job_id": job_id,
        "status": "queued",
        "status_url": f"/api/v1/interviews/{job_id}"
    }

@app.get("/api/v1/interviews", response_model=JobHistoryList)
def get_interviews_history(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    items = list_jobs(limit=limit, offset=offset)
    return {
        "items": items,
        "limit": limit,
        "offset": offset
    }

@app.get("/api/v1/interviews/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found")
        
    return {
        "job_id": job["job_id"],
        "original_filename": job["original_filename"],
        "status": job["status"],
        "submission_time": job["created_at"],
        "start_time": job["started_at"],
        "completion_time": job["completed_at"],
        "error": job["error_message"]
    }

@app.get("/api/v1/interviews/{job_id}/report")
def get_job_report(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found")
        
    if job["status"] in ["queued", "running"]:
        raise HTTPException(status_code=409, detail="Processing is not yet complete.")
        
    if job["status"] == "failed":
        raise HTTPException(status_code=400, detail=f"Job failed: {job['error_message']}")
        
    report_path = Path(job["report_path"])
    if not report_path.exists():
        raise HTTPException(status_code=500, detail="Report file is missing despite successful job status.")
        
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)
        return report_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report: {str(e)}")

@app.get("/api/v1/interviews/{job_id}/timeline")
def get_job_timeline(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found")
        
    if job["status"] in ["queued", "running"]:
        raise HTTPException(status_code=409, detail="Processing is not yet complete.")
        
    if job["status"] == "failed":
        raise HTTPException(status_code=400, detail=f"Job failed: {job['error_message']}")
        
    timeline_path = Path(job["timeline_path"])
    if not timeline_path.exists():
        raise HTTPException(status_code=404, detail="Timeline CSV file is not available for this job.")
        
    return FileResponse(
        path=timeline_path,
        media_type="text/csv",
        filename=f"timeline_{job_id}.csv"
    )

@app.get("/api/v1/interviews/{job_id}/logs")
def get_job_logs(job_id: str, max_lines: int = 500):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found")
        
    log_file = Path(job["processing_log_path"])
    
    if not log_file.exists():
        return {"logs": []}
        
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            
        # Return only the last max_lines
        return {"logs": [line.rstrip('\n') for line in lines[-max_lines:]]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")
