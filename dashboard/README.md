# Interview Analytics Dashboard (Phase 5)

A local-first, modern web dashboard built with **React**, **TypeScript**, and **Vite** for the CPU-based Interview Analytics System. It interfaces directly with the local FastAPI backend (`http://127.0.0.1:8000`) to upload videos, track analysis jobs in real time, inspect candidate metrics, explore chunk-by-chunk timelines, and download authoritative reports.

---

## Features

- **Real-Time Job Monitoring:** Live polling of queued and running background jobs with elapsed execution timer and diagnostic log viewer on failure.
- **Client-Side Upload Validation:** Drag-and-drop file upload with format restrictions (`.mp4`, `.mov`, `.avi`, `.mkv`, `.wav`, `.mp3`) and 500 MB file size limit enforcement before upload.
- **Persistent Interview History:** Paginated browsing of past interviews stored in SQLite with job status, timestamps, and quick action links.
- **Comprehensive Analytics Deep Dive:**
  - Executive KPI summary cards (Word Count, Speaking Rate WPM, Filler Word Count, Long Pauses, Silence Duration).
  - Whole-video visual presence & face visibility analysis with high-contrast indicator bars.
  - Semantic relevance score display with an explicit experimental research disclaimer.
  - Interactive SVG-based Timeline Chart (chunk-by-chunk WPM and silence seconds with hover tooltips).
  - Paginated and filterable Chunk Timeline Table with expandable transcripts.
  - Authoritative report downloads (`final_report.json` and `interview_timeline.csv`).
- **Academic Integrity:** Zero metric fabrication. Metrics not generated or unsupported by the current backend are explicitly marked as "Not available".
- **Zero Heavy Graph Dependencies:** Lightweight, responsive SVG-based charts optimized for low-resource edge/laptop environments.
- **Light & Dark Mode:** Automatic detection and manual toggle for high-contrast viewing.

---

## Prerequisites

- **Node.js**: v18.0.0 or higher (`v24.20.0` tested)
- **npm**: v9.0.0 or higher (`11.19.0` tested)
- **Python Backend**: Python 3.10+ virtual environment with FastAPI dependencies (`.\.venv\`)

---

## Quick Start

### 1. Start the FastAPI Backend

From the repository root (`Interview_Analytics`):

```powershell
.\.venv\Scripts\uvicorn.exe interview_pipeline.api.main:app --host 127.0.0.1 --port 8000
```

Verify backend health:
- `http://127.0.0.1:8000/health` -> `{"status":"ok","service":"Interview Analytics API"}`
- Interactive API Docs: `http://127.0.0.1:8000/docs`

### 2. Start the Frontend Dashboard

In a separate terminal, navigate to the `dashboard/` directory:

```powershell
cd dashboard
npm install
npm run dev
```

The Vite dev server will start at:
```
http://127.0.0.1:3000
```

> **Note on CORS:** The FastAPI backend is pre-configured to allow requests from `http://127.0.0.1:3000` and `http://localhost:3000`. The Vite server is configured to use port `3000` on `127.0.0.1` by default to avoid CORS friction.

---

## Available Scripts

In the `dashboard/` directory:

| Script | Command | Description |
|---|---|---|
| `dev` | `npm run dev` | Starts Vite local development server on `http://127.0.0.1:3000`. |
| `build` | `npm run build` | Runs TypeScript compiler (`tsc`) and bundles optimized production assets into `dist/`. |
| `preview` | `npm run preview` | Previews the production build locally on `http://127.0.0.1:3000`. |
| `test` | `npm test` | Runs unit tests via Vitest. |

---

## Project Structure

```
dashboard/
├── index.html                   # HTML entrypoint
├── package.json                 # React, Vite, TypeScript, Lucide, Vitest
├── tsconfig.json                # Strict TypeScript configuration
├── vite.config.ts               # Vite configuration (port 3000, 127.0.0.1)
├── src/
│   ├── main.tsx                 # Application mount
│   ├── App.tsx                  # Hash-based routing, navbar, footer
│   ├── index.css                # Base stylesheet and theme variables
│   ├── api/
│   │   ├── client.ts            # Centralized API fetch wrapper
│   │   ├── types.ts             # Strict TypeScript types matching FastAPI & final_report.json
│   │   └── __tests__/
│   │       └── client.test.ts   # Vitest unit tests for API client
│   ├── components/
│   │   ├── Navbar.tsx           # Global navigation with real-time API health status badge
│   │   ├── StatusBadge.tsx      # Standardized Queued / Running / Completed / Failed badges
│   │   ├── MetricCard.tsx       # KPI display card with tooltips and warning badges
│   │   ├── TimelineChart.tsx    # Responsive SVG line & bar chart for chunk metrics
│   │   ├── TimelineTable.tsx    # Filterable & expandable chunk-by-chunk table
│   │   ├── LogViewer.tsx        # Monospace terminal log viewer for execution logs
│   │   └── EmptyState.tsx       # Reusable zero-data placeholder
│   ├── pages/
│   │   ├── OverviewPage.tsx     # System dashboard landing page with stats and recent jobs
│   │   ├── UploadPage.tsx       # Video upload dropzone and live polling progression
│   │   ├── HistoryPage.tsx      # Paginated interview history with status filter
│   │   └── DetailsPage.tsx      # Deep dive analytics report, visual presence & downloads
│   └── utils/
│       ├── formatters.ts        # Formatting helpers (duration, date, size, percent)
│       ├── csvParser.ts         # RFC 4180-compliant CSV parser for interview_timeline.csv
│       └── __tests__/
│           ├── formatters.test.ts # Vitest unit tests for formatters
│           └── csvParser.test.ts  # Vitest unit tests for CSV parser
```

---

## API Endpoints Utilized

| Endpoint | Method | Frontend Usage |
|---|---|---|
| `/health` | GET | Periodic health check polling in the Navbar. |
| `/api/v1/interviews` | POST | Video file multipart upload initiating background job. |
| `/api/v1/interviews` | GET | Interview history listing with pagination. |
| `/api/v1/interviews/{id}` | GET | Real-time status polling (queued/running/completed/failed). |
| `/api/v1/interviews/{id}/report` | GET | Complete analytical metrics JSON (`final_report.json`). |
| `/api/v1/interviews/{id}/timeline` | GET | Chunk-by-chunk CSV timeline (`interview_timeline.csv`). |
| `/api/v1/interviews/{id}/logs` | GET | Execution diagnostic logs for failed runs. |

---

## Design and Edge Computing Principles

1. **Local-First & Offline Capable:** Runs entirely on the user's workstation without third-party cloud analytics or external trackers.
2. **Honest Metric Reporting:** The dashboard strictly reflects backend schema output. When metrics (e.g. candidate vs. interviewer speech share) are not measured or produced, the dashboard indicates "Not available" rather than fabricating numbers.
3. **Low Overhead:** Zero runtime charting library bloat (e.g., Chart.js, Recharts, D3). Custom inline SVG rendering guarantees snappy rendering on resource-constrained laptops.
4. **Resilient Polling:** Real-time polling cleanly terminates upon job completion, unmounting, or failure, preventing memory leaks and background network spam.
