# Interview Analytics Dashboard

React 18 + TypeScript + Vite frontend for the local FastAPI/SQLite pipeline. See the [project README](../README.md) for setup, model paths, metrics and limitations.

## Run

Start the API from the project root in one terminal:

~~~powershell
.\.venv\Scripts\python.exe -m uvicorn interview_pipeline.api.main:app --host 127.0.0.1 --port 8000
~~~

In another terminal:

~~~powershell
cd V:\vscode\Interview_visual_copy\Interview_Analytics\dashboard
npm run dev -- --strictPort
~~~

Open [the dashboard](http://127.0.0.1:3000). Keep both terminals running. Tested Node/npm: 24.20.0/11.19.0. New installations need npm ci first; prepared demos do not need reinstalling.

## Configuration

VITE_API_BASE_URL selects the API, default http://127.0.0.1:8000. Change the terminal environment or local env file and restart Vite. The API's INTERVIEW_API_ALLOWED_ORIGINS must include the actual origin; defaults allow http://127.0.0.1:3000 and http://localhost:3000. Strict port selection prevents switching silently to an unsupported origin.

## Workflow and scope

1. Select/drop media and submit. Extensions and 500 MiB limit are checked; backend codec support still matters. MP4 video with speech is rehearsed.
2. Follow three-second polling and elapsed time. Refresh/navigation in the same tab restores acknowledged active jobs from session storage; elapsed time is reconciled with server timestamps. No second upload is submitted. Temporary status failures retry automatically and offer a retry button. Stages are coarse indicators, not measured percent complete. Failed jobs show logs.
3. Browse SQLite history and reports. Search filters filename/job ID in the current page; there is no global/status search.
4. Review speaking-rate variants, fillers, within-chunk silence/pauses and candidate-interval visual visibility. Speech totals include all speakers; roles are heuristic.
5. Search/paginate the timeline, expand transcripts, inspect SVG charts and download JSON/CSV. A failed timeline fetch shows a warning and Retry timeline action while the rest of the report remains visible. Titles/download filenames prefer the original upload name.

Semantic evaluation defaults to **Not evaluated — No rubric provided**. Old numeric-only reports show **Historical similarity** with a warning. No question/answer pairing or rubric-entry UI is implemented. Null metrics are unavailable; visibility is not posture stability, attention or candidate quality.

## Commands

| Command | Effect |
| --- | --- |
| npm test | Vitest unit tests |
| npm run build | TypeScript check and production bundle in dist |
| npm run dev -- --strictPort | Development dashboard, port 3000 |
| npm run preview -- --strictPort | Preview existing production build, port 3000; stop dev first |

Phase 6.5 recorded 16 passing frontend tests and a successful build. Live upload/download/restart behavior was checked separately.

Phase 6.7 recorded 25 passing frontend tests and a successful build. Strict port behavior is enabled by default for both dev and preview; explicit --strictPort flags remain valid. Session recovery is API-specific and tab-local, stores no media/transcripts, and is unavailable if browser session storage is disabled. Terminal or missing jobs clear the stored reference. Connection errors now identify the configured API and suggest starting/checking it.

## Main files

src/App.tsx manages hash navigation; src/api/ holds the HTTP client and schemas. Pages implement overview/upload/history/details. TimelineTable and TimelineChart show chunks; csvParser.ts handles current/legacy exports; semanticEvaluation.ts labels unavailable/historical values. Styling is in src/index.css.

## Troubleshooting

**Failed to fetch:** open [API health](http://127.0.0.1:8000/health), ensure both servers run, check API URL/CORS. Processing failures: inspect logs. Port occupied: reuse or stop the existing dashboard in its own terminal. Stop servers with Ctrl+C after active analysis finishes.
