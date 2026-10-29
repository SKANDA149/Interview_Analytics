"""Run a fresh local HTTP/pipeline/restart regression without the user's database.

Usage (repository root):
    .\.venv\Scripts\python.exe scripts/verify_system.py --input path/to/short.mp4

Uses a separate API on port 8015 and unique ignored data/validation_runs/ paths.
No existing server is stopped; inputs and generated artifacts are retained.
"""
import argparse
import csv
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import psutil
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def request(base, path, *, data=None, headers=None):
    req = Request(base + path, data=data, headers=headers or {})
    try:
        with urlopen(req, timeout=15) as response:
            return response.status, response.read(), dict(response.headers)
    except HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def upload(base, filename, content):
    boundary = "validation" + uuid4().hex
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    return request(base, "/api/v1/interviews", data=body, headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Origin": "http://127.0.0.1:3000",
    })


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def serve(run_dir, port):
    import interview_pipeline.api.database as database
    database.DEFAULT_DB_PATH = run_dir / "interviews.db"
    import interview_pipeline.api.main as api
    api.API_RUNS_DIR = run_dir / "api_runs"
    api.API_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    import uvicorn
    uvicorn.run(api.app, host="127.0.0.1", port=port)


def validate_artifacts(run_dir, job_id, report_body, csv_body):
    output = run_dir / "api_runs" / job_id / "output"
    report = json.loads(report_body)
    disk_report = json.loads((output / "reports/final_report.json").read_text(encoding="utf-8"))
    check(report == disk_report, "API report differs from disk report")
    check(csv_body == (output / "reports/interview_timeline.csv").read_bytes(), "CSV download differs from disk")
    rows = list(csv.DictReader(io.StringIO(csv_body.decode("utf-8-sig"))))
    chunk_files = sorted((output / "outputs").glob("chunk_*.json"), key=lambda p: int(p.stem.split("_")[1]))
    chunks = [json.loads(p.read_text(encoding="utf-8")) for p in chunk_files]
    check(len(rows) == len(chunks) == report["metadata"]["total_chunks_processed"] > 0, "Chunk counts disagree")
    check([r["Chunk_ID"] for r in rows] == [c["chunk_id"] for c in chunks], "Chunk ordering disagrees")
    metrics = report["overall_metrics"]
    speech = [c["speech_analysis"] for c in chunks]
    duration = sum(s["actual_chunk_duration_sec"] for s in speech)
    active = sum(s["active_speech_duration_sec"] for s in speech)
    word_count = sum(len(c.get("words", [])) or len(c.get("transcript", "").split()) for c in chunks)
    check(word_count == report["metadata"]["total_recognized_words"] > 0, "Missing/inconsistent recognized words")
    check(abs(duration - report["metadata"]["total_chunk_duration_seconds"]) <= .011, "Total duration disagrees")
    check(metrics["overall_video_wpm"] == round(word_count * 60 / duration, 1), "Overall WPM formula disagrees")
    expected_active = round(word_count * 60 / active, 1) if active else None
    check(metrics["active_speech_wpm"] == expected_active, "Active WPM formula disagrees")
    speaking_rates = [s["words_per_minute"] for s in speech if s["words_per_minute"] > 0]
    expected_mean = round(sum(speaking_rates) / len(speaking_rates), 1) if speaking_rates else 0
    check(metrics["average_active_chunk_wpm"] == expected_mean, "Mean chunk WPM disagrees")
    check(metrics["average_words_per_minute"] == expected_mean, "Legacy WPM alias disagrees")
    check(metrics["average_face_visibility_pct"] == metrics["average_visual_stability"], "Visual alias disagrees")
    check(metrics["average_semantic_score"] is None, "Default semantic score should be null")
    check(metrics["semantic_evaluation"]["status"] == "not_evaluated", "Semantic status incorrect")
    for s, row, chunk in zip(speech, rows, chunks):
        check(0 <= s["total_silence_sec"] <= s["actual_chunk_duration_sec"] + .01, "Silence out of bounds")
        check(abs(s["total_silence_sec"] + s["active_speech_duration_sec"] - s["actual_chunk_duration_sec"]) <= .021, "Duration decomposition disagrees")
        check(float(row["WPM"]) == s["words_per_minute"], "CSV WPM disagrees")
        check(row["Face_Visibility"] == row["Visual_Stability"], "CSV visual alias disagrees")
        check(row["Semantic_Score"] == "N/A" and row["Semantic_Status"] == "not_evaluated", "CSV semantic status disagrees")
        check(chunk["content_analysis"]["semantic_score"] is None, "Chunk has unexpected semantic score")
    for csv_name, metric_name in [("Filler_Words", "total_filler_words"), ("Long_Pauses", "total_long_pauses"), ("Silence_Seconds", "total_silence_seconds")]:
        check(abs(sum(float(r[csv_name]) for r in rows) - metrics[metric_name]) <= .011, f"CSV total differs: {csv_name}")
    segments = json.loads((output / "diarization/segments.json").read_text(encoding="utf-8"))
    check(all(a["start"] <= b["start"] for a, b in zip(segments, segments[1:])), "Diarization not chronological")
    check(all(0 <= s["start"] < s["end"] for s in segments), "Invalid diarization interval")
    boundaries = [(c["chunk_start_sec"], c["chunk_end_sec"]) for c in chunks]
    check(all(a[1] <= b[0] for a, b in zip(boundaries, boundaries[1:])), "Overlapping visual chunk windows")
    scored = report["visual_summary_whole_video"].get("scored_samples", 0)
    check(sum(c["visual_analysis"]["n_samples"] for c in chunks) == scored, "Visual samples lost or counted twice across chunks")
    return {
        "chunks": len(chunks), "recognized_words": word_count,
        "duration_seconds": round(duration, 2), "metrics": metrics,
        "visual_summary": report["visual_summary_whole_video"],
        "diarization_segments": len(segments),
        "speaker_role_counts": {role: sum(s["speaker"] == role for s in segments) for role in sorted({s["speaker"] for s in segments})},
        "chunk_time_ranges": boundaries,
        "report_sha256": hashlib.sha256(report_body).hexdigest(),
        "csv_sha256": hashlib.sha256(csv_body).hexdigest(),
        "output_dir": str(output),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--port", type=int, default=8015)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--serve", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(args.serve, args.port)
        return
    if not args.input or not args.input.is_file():
        parser.error("--input must name an existing short local video")
    # Refuse occupied ports before launching, so a user's API cannot be mistaken for ours.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", args.port))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    run_dir = ROOT / "data/validation_runs" / stamp
    run_dir.mkdir(parents=True, exist_ok=False)
    base = f"http://127.0.0.1:{args.port}"
    evidence = {"started_utc": datetime.now(timezone.utc).isoformat(), "run_dir": str(run_dir), "base_url": base, "checks": []}
    evidence["versions"] = {name: importlib.metadata.version(name) for name in (
        "fastapi", "starlette", "uvicorn", "pydantic", "vosk", "onnxruntime", "scikit-learn", "torch", "torchaudio", "silero-vad", "soundfile", "mediapipe", "opencv-python", "pytest",
    )}
    evidence["python"] = sys.version
    process = None
    server_log = (run_dir / "server.log").open("ab")

    def start():
        process = subprocess.Popen([
            sys.executable, "-u", str(Path(__file__).resolve()), "--serve", str(run_dir), "--port", str(args.port),
        ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            check(process.poll() is None, "Validation API exited; inspect server.log")
            try:
                if request(base, "/health")[0] == 200:
                    return process
            except (URLError, OSError):
                pass
            time.sleep(.5)
        process.terminate()
        process.wait(timeout=15)
        raise TimeoutError("Validation API did not become healthy")

    def stop():
        if process is not None and process.poll() is None:
            children = psutil.Process(process.pid).children(recursive=True)
            process.terminate()
            process.wait(timeout=20)
            # Only stop children of this runner's own isolated API (e.g. a
            # pipeline left running after a validation timeout).
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass

    try:
        process = start()
        for path in ("/", "/health", "/docs", "/openapi.json", "/api/v1/interviews"):
            check(request(base, path)[0] == 200, f"Route failed: {path}")
        check(request(base, "/api/v1/interviews/unknown")[0] == 404, "Unknown job should be 404")
        check(upload(base, "invalid.txt", b"invalid")[0] == 400, "Unsupported extension accepted")
        check(upload(base, "empty.mp4", b"")[0] == 400, "Empty upload accepted")
        check(request(base, "/api/v1/interviews?limit=-1")[0] == 422, "Negative history limit accepted")
        evidence["checks"].append("routes_and_upload_validation")
        content = args.input.read_bytes()
        evidence["input"] = {"description": "Short local interview regression clip", "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        code, body, headers = upload(base, "phase6_5_interview.mp4", content)
        check(code == 202, f"Upload failed with HTTP {code}")
        check(headers.get("access-control-allow-origin") == "http://127.0.0.1:3000", "Upload CORS header missing")
        job_id = json.loads(body)["job_id"]
        evidence["job_id"] = job_id
        print(f"Validation job: {job_id}\nEvidence: {run_dir}", flush=True)
        deadline = time.monotonic() + args.timeout
        observed = []
        while time.monotonic() < deadline:
            code, body, _ = request(base, f"/api/v1/interviews/{job_id}")
            check(code == 200, "Job status unavailable")
            status = json.loads(body)
            if not observed or observed[-1] != status["status"]:
                observed.append(status["status"])
                print(f"Status: {status['status']}", flush=True)
            if status["status"] in ("completed", "failed"):
                break
            time.sleep(2)
        evidence["observed_statuses"] = observed
        evidence["final_status"] = status
        check(status["status"] == "completed", f"Job did not complete: {status}")
        code, report_body, _ = request(base, f"/api/v1/interviews/{job_id}/report")
        check(code == 200, "Report retrieval failed")
        code, csv_body, headers = request(base, f"/api/v1/interviews/{job_id}/timeline")
        check(code == 200 and "attachment" in headers.get("content-disposition", ""), "CSV download failed")
        check(request(base, f"/api/v1/interviews/{job_id}/logs?max_lines=10")[0] == 200, "Logs route failed")
        evidence["artifacts"] = validate_artifacts(run_dir, job_id, report_body, csv_body)
        evidence["checks"].append("fresh_upload_and_artifact_consistency")
        stop()
        process = start()
        code, body, _ = request(base, f"/api/v1/interviews/{job_id}")
        check(code == 200 and json.loads(body)["status"] == "completed", "Completed job lost after restart")
        check(request(base, f"/api/v1/interviews/{job_id}/report")[1] == report_body, "Report changed after restart")
        check(request(base, f"/api/v1/interviews/{job_id}/timeline")[1] == csv_body, "CSV changed after restart")
        history = json.loads(request(base, "/api/v1/interviews?limit=1&offset=0")[1])
        check(history["items"][0]["job_id"] == job_id and history["items"][0]["has_report"], "History lost after restart")
        check(not json.loads(request(base, "/api/v1/interviews?limit=1&offset=1")[1])["items"], "History offset incorrect")
        evidence["checks"].append("restart_persistence_and_downloads")
        evidence["result"] = "passed"
        print("PASS: fresh upload, JSON/CSV consistency, restart persistence and downloads", flush=True)
    except Exception as error:
        evidence["result"] = "failed"
        evidence["error"] = str(error)
        raise
    finally:
        stop()
        server_log.close()
        evidence["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (run_dir / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
