# Interview Analytics System

Academic project: **Memory-Optimized Asynchronous Multimedia Pipeline for Edge-Based Interview Analytics**.

A local, CPU-oriented application for reviewing interview recordings through transcripts, speech measurements, estimated speaker roles and visual visibility. The CLI pipeline, FastAPI service, SQLite history and React dashboard are implemented. Outputs support human review; they are not validated hiring or candidate-quality scores.

## Implemented features

- FFmpeg stream-copy chunks, mono 16 kHz audio and local Vosk transcription with word timestamps.
- Silero VAD, WeSpeaker ONNX embeddings and cosine-distance agglomerative clustering with complete linkage (two speakers by default).
- Heuristic candidate/interviewer roles; 5 FPS visual sampling during estimated candidate speech with YuNet and MediaPipe pose landmarks.
- Speaking-rate variants, transcript-derived silence/long pauses, context-aware fillers and JSON/CSV reports.
- FastAPI uploads, one worker, isolated job outputs, logs and SQLite history across restarts.
- React dashboard: uploads, refresh-safe job tracking, history, charts, searchable chunk timelines, expandable transcripts and downloads.
- Default semantic evaluation: **Not evaluated — No rubric provided**. An explicit response/rubric helper exists; reliable question/answer pairing and rubric-entry UI/API do not.

Chunking reduces some processing working sets, but visual sampling currently retains frames in memory. Memory is not guaranteed constant with recording length. No fixed RAM or runtime guarantee is made.

## Run the prepared installation

Keep two PowerShell terminals open. Do not reinstall packages just to start a prepared environment.

Terminal 1 — API:

~~~powershell
cd V:\vscode\Interview_visual_copy\Interview_Analytics
.\.venv\Scripts\python.exe -m uvicorn interview_pipeline.api.main:app --host 127.0.0.1 --port 8000
~~~

Terminal 2 — dashboard:

~~~powershell
cd V:\vscode\Interview_visual_copy\Interview_Analytics\dashboard
npm run dev -- --strictPort
~~~

Open [the dashboard](http://127.0.0.1:3000). Check [API health](http://127.0.0.1:8000/health) and [API documentation](http://127.0.0.1:8000/docs). The API root shows metadata, not the dashboard.

Before a demo, from the project root:

~~~powershell
.\.venv\Scripts\python.exe scripts/demo_preflight.py --api-url http://127.0.0.1:8000 --dashboard-url http://127.0.0.1:3000
~~~

Wait for active jobs to finish before Ctrl+C in the API terminal. Stop the dashboard in its own terminal. Completed jobs survive restart while the database and artifacts remain available. Interrupted running jobs are marked failed; queued jobs with available inputs are requeued.

## Setup on another machine

Tested machine: Windows, Python 3.11.9, Node 24.20.0, npm 11.19.0, FFmpeg/ffprobe 8.1. A clean install on another machine has not been validated.

Install Python, Node/npm and FFmpeg/ffprobe first. From the root:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pytest pytest-mock httpx
cd dashboard
npm ci
~~~

The Windows MediaPipe pin matches the tested 1.0.1 environment. Non-Windows retains the historical 0.10.14 pin and needs separate validation. Other Python dependencies are mostly unpinned. An installed-package snapshot is evidence, not a portable lockfile.

Provide these assets before inference; model binaries are ignored:

| Asset | Expected location |
| --- | --- |
| Complete Vosk small English directory | models/vosk/vosk-model-small-en-us-0.15/ |
| WeSpeaker | models/wespeaker/voxceleb_resnet34_LM.onnx |
| YuNet | models/yunet/face_detection_yunet_2023mar.onnx |
| MediaPipe pose | models/pose_landmarker/pose_landmarker_lite.task |
| Silero ONNX | Bundled with the installed silero-vad package |

Acquire assets from their official distributors and check their terms. The current VAD loader does not read a separate models/silero_vad file. MiniLM is not needed for default evaluation. The optional explicit-rubric helper may resolve a SentenceTransformers model unless library offline mode is enabled. Prepare assets before an offline demo.

## Architecture and artifacts

~~~text
Dashboard -> FastAPI upload -> SQLite registration -> one worker -> CLI subprocess
 -> FFmpeg chunks + original-media segment manifest
 -> full-audio VAD -> WeSpeaker -> clustering -> speaker-role heuristic
 -> visual sampling during estimated candidate speech
 -> per-chunk audio/Vosk/speech/fillers/unavailable semantic status
 -> JSON + CSV -> API -> dashboard
~~~

| Location | Purpose |
| --- | --- |
| cli.py | Command-line entry point |
| interview_pipeline/src/ | Pipeline, inference and reporting |
| interview_pipeline/api/ | FastAPI and SQLite |
| interview_pipeline/tests/ | Backend regression tests |
| dashboard/ | React, TypeScript, Vite and Vitest |
| scripts/demo_preflight.py | Prerequisites and optional server checks |
| scripts/verify_system.py | Isolated fresh processing/restart validation |
| data/interview_analytics.db | Normal API database |
| data/api_runs/{job_id}/ | Job input, processing.log and output |
| data/validation_runs/ | Isolated validation databases and evidence |
| local_reports/ | Ignored reports, demo runbook, architecture/viva notes and limitations |

Current outputs: output/reports/final_report.json, output/reports/interview_timeline.csv, and chunk JSON under output/outputs/. New runs retain original-media chunk bounds from FFmpeg. final_aggregated_report.json is a historical filename.

## Metric definitions

| Field | Meaning |
| --- | --- |
| average_active_chunk_wpm | Arithmetic mean of nonzero chunk WPM |
| overall_video_wpm | Recognized words / summed measured chunk-audio minutes |
| active_speech_wpm | Recognized words / transcript-derived active-speech minutes; null if unavailable |
| total_silence_seconds | Leading/trailing silence and positive word gaps inside chunks, bounded by duration |
| total_long_pauses | Word gaps of at least 1.5 seconds inside chunks |
| total_filler_words | Rule-classified disfluencies; ambiguous markers do not automatically count |
| average_face_visibility_pct | Mean numeric chunk full-visibility percentage; null without observations |
| Whole-video face_visibility_pct | Full face/shoulder visibility among scored candidate-interval samples |
| Whole-video presence_pct | Partial or full visibility among those scored samples |
| average_semantic_score | Null by default; old numeric reports receive a historical-similarity warning |

Speech metrics include all recognized speakers. Visual metrics describe sampled visibility, not attention, emotion, posture stability or certain candidate identity. Whole-video sample-weighted visibility can differ from the mean chunk percentage. average_words_per_minute and average_visual_stability remain deprecated compatibility aliases.

## API and configuration

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /, /health, /docs, /openapi.json | Metadata, health and API docs |
| POST | /api/v1/interviews | Multipart file upload, HTTP 202 and job ID |
| GET | /api/v1/interviews?limit=10&offset=0 | History: timestamp descending, then job ID descending |
| GET | /api/v1/interviews/{job_id} | Status, timestamps and original filename |
| GET | /api/v1/interviews/{job_id}/report | JSON; HTTP 409 while pending |
| GET | /api/v1/interviews/{job_id}/timeline | CSV download |
| GET | /api/v1/interviews/{job_id}/logs | Processing logs |

Validation accepts MP4/MOV/AVI/MKV/WAV/MP3 up to 500 MiB. Acceptance does not guarantee codec/audio-only support; MP4 video with speech is rehearsed. Malformed media fails with diagnostics. Jobs run serially.

VITE_API_BASE_URL defaults to http://127.0.0.1:8000; restart Vite after changing it. INTERVIEW_API_ALLOWED_ORIGINS defaults to http://localhost:3000,http://127.0.0.1:3000. Use --strictPort to prevent Vite silently switching to an origin CORS rejects.

Vite now enables strict port selection by default for development and preview. Acknowledged active jobs are remembered in this browser tab's session storage, scoped to the API URL, so refresh or navigation can resume polling without submitting another upload. Only the job ID and submission timestamp are saved; terminal/missing jobs clear that reference. Disabled browser storage prevents refresh recovery but does not stop live analysis. Connection failures show recovery guidance, and timeline failures show a separate retry action without hiding the report. Report titles/downloads prefer the original uploaded filename.

## Verification

~~~powershell
cd V:\vscode\Interview_visual_copy\Interview_Analytics
.\.venv\Scripts\python.exe -m pytest interview_pipeline/tests -q
.\.venv\Scripts\python.exe -m pip check
git diff --check
cd dashboard
npm test
npm run build
~~~

Phase 6.5 recorded 145 backend and 16 frontend tests passing, a successful build and fresh upload/download/restart checks. Read the latest local phase report for subsequent results. The existing Starlette/httpx deprecation warning is separate from test failures.

Phase 6.7 final polish: 146 backend tests and 25 frontend tests passed, the production build passed, and controlled browser checks covered refresh recovery, connection errors, timeline retry, original filenames and strict-port behavior. These UI fixtures reused an existing report; they were not new inference/accuracy evaluations.

From the root, run another deliberate real-inference check:

~~~powershell
.\.venv\Scripts\python.exe scripts/verify_system.py --input data/validation_inputs/phase6_5_interview_20261029.mp4
~~~

Port 8015 must be free. This creates a separate API/database and saves evidence under the printed validation directory. The sample is local and absent in a fresh clone; substitute your own short MP4.

For standalone CLI work, always choose a new output directory:

~~~powershell
$demoRun = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
.\.venv\Scripts\python.exe cli.py --input data/input/sample.mp4 --output-dir "data/cli_runs/$demoRun"
~~~

Reused directories can reuse stale results. Prefer API isolation for the demo.

## Troubleshooting and limitations

- **Failed to fetch:** start the API; check health, API URL and dashboard origin. Both terminals must stay open.
- **Port in use:** reuse the intended server or stop it in its own terminal. Do not start duplicate APIs on the normal database.
- **Pipeline failed:** inspect logs/models; never mark failed jobs completed manually.
- **Git pager:** Q exits; git --no-pager diff avoids it.
- Speaker roles assume the candidate talks longer; near-equal durations use the opening-speaker heuristic. No labeled accuracy evaluation is claimed.
- Silence/pauses depend on STT timestamps; cross-chunk pauses are not counted. Transcripts can contain recognition errors.
- Shared CLI caches, retained-frame memory growth, the 100-job overview cap and page-local history search remain limits.
- Physical network-disconnection rehearsal is separate from library offline-mode checks.
- Keep recordings, transcripts, databases and binaries local. Ignore rules do not untrack files: review git ls-files data/ before release. Public deployment/authentication hardening is outside this local prototype.

## Academic credits

Department of Computer Science & Engineering, SJB Institute of Technology, Bengaluru. Guidance: Asst. Prof. Vijayalaxmi Joshi.

- Skanda L (1JB23CS149)
- Swayam H (1JB23CS166)
- Thakur Sadanand (1JB23CS171)
- Udaya Aparanji (1JB23CS173)
