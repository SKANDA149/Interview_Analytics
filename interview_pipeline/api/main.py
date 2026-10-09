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

from fastapi import FastAPI, UploadFile, File, HTTPException, status, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configuration
MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
API_RUNS_DIR = PROJECT_ROOT / "data" / "api_runs"
API_RUNS_DIR.mkdir(parents=True, exist_ok=True)

# Application state
app = FastAPI(
    title="Interview Analytics API",
    version="1.0.0",
    description="API for edge-based local interview analytics"
)

# CORS Configuration
# e.g. INTERVIEW_API_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
allowed_origins_env = os.environ.get("INTERVIEW_API_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job registry and single-worker queue
jobs = {}
job_executor = ThreadPoolExecutor(max_workers=1)

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    submission_time: str
    start_time: str | None = None
    completion_time: str | None = None
    error: str | None = None

def run_interview_pipeline(job_id: str, video_path: Path, output_dir: Path, log_file: Path):
    """Background worker task to run the CLI."""
    jobs[job_id]["status"] = "running"
    jobs[job_id]["start_time"] = datetime.now(timezone.utc).isoformat()
    
    cli_path = PROJECT_ROOT / "cli.py"
    
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"--- Starting Job {job_id} at {jobs[job_id]['start_time']} ---\n")
            proc = subprocess.run(
                [sys.executable, str(cli_path), "--input", str(video_path), "--output-dir", str(output_dir)],
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=str(PROJECT_ROOT)
            )
            f.write(f"\n--- Process exited with code {proc.returncode} ---\n")
            
        if proc.returncode != 0:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = f"Pipeline subprocess failed with exit code {proc.returncode}."
            jobs[job_id]["completion_time"] = datetime.now(timezone.utc).isoformat()
            return

        # Check for expected outputs
        final_report_path = output_dir / "reports" / "final_report.json"
        if not final_report_path.exists():
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = "Pipeline completed but final_report.json was not found."
            jobs[job_id]["completion_time"] = datetime.now(timezone.utc).isoformat()
            return
            
        # Verify JSON is valid
        try:
            with open(final_report_path, "r", encoding="utf-8") as rf:
                json.load(rf)
        except json.JSONDecodeError:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = "Pipeline completed but final_report.json is invalid JSON."
            jobs[job_id]["completion_time"] = datetime.now(timezone.utc).isoformat()
            return

        # Success
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["completion_time"] = datetime.now(timezone.utc).isoformat()
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = f"Unexpected execution error: {str(e)}"
        jobs[job_id]["completion_time"] = datetime.now(timezone.utc).isoformat()


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
    
    # Save the uploaded file with size limit enforcement
    try:
        bytes_written = 0
        with open(video_path, "wb") as out_file:
            while content := file.file.read(1024 * 1024):  # 1MB chunks
                bytes_written += len(content)
                if bytes_written > MAX_UPLOAD_SIZE:
                    out_file.close()
                    # Clean up
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
        
    # Register job
    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "submission_time": datetime.now(timezone.utc).isoformat(),
        "start_time": None,
        "completion_time": None,
        "error": None,
        "run_dir": job_dir,
        "video_path": video_path,
        "output_dir": output_dir,
        "log_file": log_file
    }
    
    # Queue the job
    job_executor.submit(run_interview_pipeline, job_id, video_path, output_dir, log_file)
    
    return {
        "job_id": job_id,
        "status": "queued",
        "status_url": f"/api/v1/interviews/{job_id}"
    }

@app.get("/api/v1/interviews/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job ID not found")
        
    job = jobs[job_id]
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "submission_time": job["submission_time"],
        "start_time": job["start_time"],
        "completion_time": job["completion_time"],
        "error": job["error"]
    }

@app.get("/api/v1/interviews/{job_id}/report")
def get_job_report(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job ID not found")
        
    job = jobs[job_id]
    if job["status"] in ["queued", "running"]:
        raise HTTPException(status_code=409, detail="Processing is not yet complete.")
        
    if job["status"] == "failed":
        raise HTTPException(status_code=400, detail=f"Job failed: {job['error']}")
        
    report_path = job["output_dir"] / "reports" / "final_report.json"
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
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job ID not found")
        
    job = jobs[job_id]
    if job["status"] in ["queued", "running"]:
        raise HTTPException(status_code=409, detail="Processing is not yet complete.")
        
    if job["status"] == "failed":
        raise HTTPException(status_code=400, detail=f"Job failed: {job['error']}")
        
    timeline_path = job["output_dir"] / "reports" / "interview_timeline.csv"
    if not timeline_path.exists():
        raise HTTPException(status_code=404, detail="Timeline CSV file is not available for this job.")
        
    return FileResponse(
        path=timeline_path,
        media_type="text/csv",
        filename=f"timeline_{job_id}.csv"
    )

@app.get("/api/v1/interviews/{job_id}/logs")
def get_job_logs(job_id: str, max_lines: int = 500):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job ID not found")
        
    job = jobs[job_id]
    log_file = job["log_file"]
    
    if not log_file.exists():
        return {"logs": []}
        
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            
        # Return only the last max_lines
        return {"logs": [line.rstrip('\n') for line in lines[-max_lines:]]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")
