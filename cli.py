import os
import argparse
import sys
import webbrowser
import http.server
import socketserver
import json
from pathlib import Path
from urllib.parse import urlparse

# Prevent tokenizers deadlock on systems when loading transformers
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from interview_pipeline.src.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Memory-Optimized Multimedia Pipeline for Edge-Based Interview Analytics"
    )
    parser.add_argument(
        "--force", "-f", action="store_true",
        help="Force re-processing of all video chunks and outputs, ignoring existing cache."
    )
    parser.add_argument(
        "--video", "-v", type=str, default="data/input/sample.mp4",
        help="Path to input interview video file (default: data/input/sample.mp4)"
    )
    parser.add_argument(
        "--chunk-duration", "-c", type=int, default=10,
        help="Chunk duration in seconds (default: 10)"
    )
    parser.add_argument(
        "--speakers", "-s", type=int, default=2,
        help="Number of speakers to detect via diarization (default: 2)"
    )
    parser.add_argument(
        "--no-dashboard", action="store_true",
        help="Run pipeline headlessly without launching the dashboard."
    )
    
    args = parser.parse_args()

    if args.no_dashboard:
        # Headless mode: run pipeline immediately with default NLP config
        run_pipeline(
            force_reprocess=args.force,
            input_video_path=args.video,
            chunk_duration=args.chunk_duration,
            nlp_config=None,
            n_speakers=args.speakers
        )
    else:
        # Default mode: launch the dashboard
        launch_dashboard_server(args=args)

def launch_dashboard_server(port: int = 8000, args=None):
    project_root = Path(__file__).parent.resolve()
    print("\n==================================================")
    print(f"[DASHBOARD] Launching Edge Analytics Dashboard on http://localhost:{port}")
    print("==================================================")
    webbrowser.open(f"http://localhost:{port}/dashboard/index.html")
    
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args_init, **kwargs):
            super().__init__(*args_init, directory=str(project_root), **kwargs)

        extensions_map = http.server.SimpleHTTPRequestHandler.extensions_map.copy()
        extensions_map['.csv'] = 'text/csv'

        def log_message(self, format, *log_args):
            # Suppress default request logging for cleaner output
            pass

        def do_POST(self):
            parsed_path = urlparse(self.path)

            if parsed_path.path == '/api/run-pipeline':
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                
                try:
                    config = json.loads(body) if body else {}
                    
                    # Build NLP config from dashboard inputs
                    job_title = config.get("job_title", "").strip()
                    job_desc = config.get("job_description", "").strip()
                    key_skills_raw = config.get("key_skills", "").strip()
                    additional = config.get("additional_keywords", "").strip()
                    
                    # Parse comma-separated skills into a list
                    if isinstance(key_skills_raw, str):
                        key_skills = [s.strip() for s in key_skills_raw.split(",") if s.strip()]
                    elif isinstance(key_skills_raw, list):
                        key_skills = key_skills_raw
                    else:
                        key_skills = []
                    
                    # Compose the job description with the title for richer semantic context
                    full_description = job_desc
                    if job_title and job_desc:
                        full_description = f"{job_title} role. {job_desc}"
                    elif job_title and not job_desc:
                        full_description = f"{job_title} role."
                    
                    nlp_config = {
                        "job_description": full_description,
                        "qualifications": "",
                        "responsibilities": "",
                        "custom_details": additional,
                        "key_skills": key_skills
                    }
                    
                    # Use None to trigger pipeline defaults if everything is empty
                    if not full_description.strip() and not key_skills and not additional:
                        nlp_config = None
                    
                    print(f"\n[API] Running pipeline with NLP config from dashboard...")
                    
                    # Determine CLI args for the pipeline
                    video_path = "data/input/sample.mp4"
                    chunk_duration = 10
                    force = False
                    n_speakers = 2
                    
                    if args:
                        video_path = args.video
                        chunk_duration = args.chunk_duration
                        force = args.force
                        n_speakers = args.speakers
                    
                    run_pipeline(
                        force_reprocess=force,
                        input_video_path=video_path,
                        chunk_duration=chunk_duration,
                        nlp_config=nlp_config,
                        n_speakers=n_speakers
                    )
                    
                    # Read and return the generated report
                    report_path = project_root / "data" / "reports" / "final_report.json"
                    if report_path.exists():
                        with open(report_path, "r", encoding="utf-8") as f:
                            report_data = json.load(f)
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps(report_data).encode('utf-8'))
                    else:
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": "Pipeline completed but no report was generated."}).encode('utf-8'))
                        
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            else:
                self.send_error(404, "Not Found")

    try:
        with socketserver.ThreadingTCPServer(("", port), Handler) as httpd:
            print(f"[DASHBOARD] Server active at http://localhost:{port}/dashboard/index.html (Press Ctrl+C to stop)")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[DASHBOARD] Server stopped.")

if __name__ == "__main__":
    main()