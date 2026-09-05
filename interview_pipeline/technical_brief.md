# Technical Brief: Multi-Pipeline Asyme Interview Analysis

## 1. Executive Summary
This document provides a technical breakdown of the Multi-Pipeline Asyme Interview Analysis project. The system is designed to ingest long-form interview video/audio, parallelize the transcription and analysis processes, and synthesize the results into structured, actionable insights using advanced LLM inference. 

By leveraging asynchronous orchestration and modular pipeline design, the system reduces the processing time of a 60-minute interview to under 5 minutes.

---

## 2. Exact Features Implemented
The "factory line" architecture is divided into three distinct stages to ensure high throughput and fault tolerance:

### Stage 1: The Input Pipe (Ingestion)
- **Video Chunking:** The pipeline begins by ingesting raw video files and systematically splitting them into smaller, fixed-duration segments (e.g., 10-second chunks). This is handled by `chunking.py` using `ffmpeg`.
- **Audio Extraction:** For each chunk, optimal audio is isolated and extracted to a 16kHz mono WAV format (`audio_extract.py`). This guarantees the STT engine receives normalized, high-quality input without visual overhead.

### Stage 2: The Asyme Engine (Concurrent Analysis)
- **Parallel Processing:** Instead of processing the video linearly, the Asyme Engine spins up concurrent workers to handle the chunks simultaneously. 
- **STT Processing:** Each chunk is passed through an offline Speech-to-Text model (`stt.py` using Vosk) to generate precise word-level timestamps.
- **LLM Inference:** The transcribed chunks are then immediately analyzed by the AI model to score the candidate's responses on a per-chunk basis.

### Stage 3: The Synthesis Pipe (Report Merging)
- **Recombination:** Once all chunks are processed, the Synthesis Pipe aggregates the individual JSON outputs from the `data/outputs/` directory.
- **Dashboard Generation:** The pipe reconciles overlapping context and merges the data into a single, comprehensive dashboard report, resolving any conflicting signals and finalizing the candidate's profile.

---

## 3. Methods & Orchestration

### The Manager View
The core orchestration of the pipeline is governed by a centralized "Manager View" (implemented in `pipeline.py`). 
- **Agent Orchestration:** The Manager acts as the dispatcher, keeping track of which chunks have been processed (via file existence checks) and assigning pending chunks to available workers.
- **Autonomy & Debugging:** The system employs autonomous agent patterns to handle localized errors. If a specific chunk fails during audio extraction or transcription (e.g., due to a corrupted frame), the worker agent can autonomously debug, retry, or flag the segment without crashing the entire 60-minute pipeline run.

---

## 4. Technical Techniques (Technical Nuggets)

### Asyme Logic
- **Aggressive Parallelization:** The true performance driver of the system is the Asyme (Asynchronous/Symmetric) Logic. By decoupling the video into independent, stateless chunks, we achieve high concurrency. This allows a 60-minute interview to be fully transcribed and analyzed in under 5 minutes, constrained only by the available CPU/GPU workers rather than the length of the video.

### Custom Prompting (Gemini 3)
- **Hidden Signal Detection:** The analysis phase utilizes tailored system instructions sent to Gemini 3.1 Pro. The prompts are specifically engineered to go beyond literal transcription, analyzing the word-level timings and text to detect "hidden signals."
- **Behavioral Indicators:** The model is prompted to identify hesitation (e.g., high density of filler words, long pauses between timestamps) and confidence (clear, uninterrupted speech patterns).

### Data Structuring
- **JSON Dashboard Methodology:** The raw analysis is strictly typed and transformed into a structured JSON schema. 
- **Quantitative Rankings:** The prompt enforces the generation of quantitative data, converting qualitative candidate traits into 1–10 rankings across specific behavioral and technical categories. This structured output is easily consumable by frontend dashboards and database systems.

---

## 5. Verifiable Methodology

The development process utilized a strict artifact-driven approach to ensure verifiability:
1. **Chunking & Audio Extraction:** Modularity is verifiable through `chunking.py` and `audio_extract.py`, which strictly handle file I/O and format validation.
2. **STT Artifacts:** `stt.py` ensures that every transcription generates an intermediate structured artifact (e.g., `chunk_001.json`) containing the raw text and word-level timestamps. 
3. **State Management:** The orchestration in `pipeline.py` verifies the presence of these artifacts at each step, ensuring the pipeline can be paused, resumed, and audited at any point without losing data. 

This strict separation of concerns—ingestion, transcription, and synthesis—ensures the pipeline remains robust and highly extensible for future analysis modules.
