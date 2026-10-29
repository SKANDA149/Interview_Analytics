import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
import threading
from typing import List, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "interview_analytics.db"

# Thread-local storage to safely share SQLite connections per thread
_local = threading.local()

def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a thread-local SQLite connection."""
    actual_db_path = db_path if db_path else DEFAULT_DB_PATH
    if not hasattr(_local, "connection") or _local.current_db_path != actual_db_path:
        if hasattr(_local, "connection"):
            _local.connection.close()
        _local.connection = sqlite3.connect(
            str(actual_db_path),
            check_same_thread=False,
            isolation_level=None
        )
        _local.connection.row_factory = sqlite3.Row
        _local.current_db_path = actual_db_path
    return _local.connection

def close_connection():
    if hasattr(_local, "connection"):
        _local.connection.close()
        delattr(_local, "connection")

def init_db(db_path: Optional[Path] = None):
    """Initialize the database schema."""
    actual_db_path = db_path if db_path else DEFAULT_DB_PATH
    actual_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(actual_db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interviews (
                job_id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                stored_input_path TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                process_exit_code INTEGER,
                processing_log_path TEXT,
                report_path TEXT,
                timeline_path TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON interviews(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON interviews(created_at DESC)")
        conn.commit()
    finally:
        conn.close()

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def create_job(
    job_id: str,
    original_filename: str,
    stored_input_path: str,
    processing_log_path: str,
    report_path: str,
    timeline_path: str,
    db_path: Optional[Path] = None
):
    """Insert a new job into the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    now = now_iso()
    cursor.execute("BEGIN")
    try:
        cursor.execute("""
            INSERT INTO interviews (
                job_id, original_filename, stored_input_path, status, created_at, 
                processing_log_path, report_path, timeline_path, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id, original_filename, stored_input_path, "queued", now,
            processing_log_path, report_path, timeline_path, now
        ))
        cursor.execute("COMMIT")
    except Exception:
        cursor.execute("ROLLBACK")
        raise

def get_job(job_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single job by ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interviews WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None

def update_job_status(
    job_id: str,
    status: str,
    error_message: Optional[str] = None,
    process_exit_code: Optional[int] = None,
    db_path: Optional[Path] = None
):
    """Update job status and relevant timestamps."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    now = now_iso()
    
    cursor.execute("BEGIN")
    try:
        if status == "running":
            cursor.execute("""
                UPDATE interviews 
                SET status = ?, started_at = ?, updated_at = ? 
                WHERE job_id = ?
            """, (status, now, now, job_id))
        elif status in ("completed", "failed"):
            cursor.execute("""
                UPDATE interviews 
                SET status = ?, completed_at = ?, error_message = ?, process_exit_code = ?, updated_at = ? 
                WHERE job_id = ?
            """, (status, now, error_message, process_exit_code, now, job_id))
        else:
            cursor.execute("""
                UPDATE interviews 
                SET status = ?, updated_at = ? 
                WHERE job_id = ?
            """, (status, now, job_id))
        cursor.execute("COMMIT")
    except Exception:
        cursor.execute("ROLLBACK")
        raise

def list_jobs(limit: int = 20, offset: int = 0, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """List jobs newest first, breaking timestamp ties by job_id descending.

    Job IDs provide a stable tie-breaker, not an insertion-time guarantee.
    Apply pagination after both sort keys so tied records have a fixed order.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT job_id, original_filename, status, created_at, completed_at, report_path
        FROM interviews
        ORDER BY created_at DESC, job_id DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    results = []
    for row in cursor.fetchall():
        d = dict(row)
        d["has_report"] = (d["status"] == "completed")
        d.pop("report_path", None)
        results.append(d)
        
    return results

def get_jobs_by_status(status: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Get all jobs by a specific status (used for recovery)."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interviews WHERE status = ?", (status,))
    return [dict(row) for row in cursor.fetchall()]
