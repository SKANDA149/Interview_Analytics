# Memory-Optimized Asynchronous Multimedia Pipeline for Edge-Based Interview Analytics

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Stream%20Copy-green.svg)](https://ffmpeg.org/)
[![Vosk](https://img.shields.io/badge/Vosk-Offline%20STT-orange.svg)](https://alphacephei.com/vosk/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-red.svg)](https://opencv.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An edge-compatible, privacy-first multimedia processing pipeline designed for automated interview performance evaluation on resource-constrained consumer hardware (laptops with limited RAM/CPU, no dedicated GPU, and no active internet connection).

Developed at **Department of Computer Science & Engineering, SJB Institute of Technology**.

---

## 📖 Project Overview

Traditional automated interview analysis tools rely heavily on cloud APIs (e.g., OpenAI, Google Cloud) or high-end GPU infrastructure, introducing high operational costs, privacy risks, and network latency bottlenecks.

This project delivers a **local-first, memory-optimized architecture** that processes long-form interview recordings in micro-chunks without loading full video files into memory, maintaining a constant **$O(1)$ RAM footprint (~170 MB)**.

---

## ✨ Key Features

- **⚡ Sub-Second Video Chunking**: Utilizes FFmpeg stream copy (`-c copy`) to segment long interview recordings into 10-second intervals in **~0.06 seconds** without CPU-intensive re-encoding.
- **🎙️ 100% Offline Speech-to-Text**: Employs the Vosk Kaldi speech recognition engine for fast, on-device audio transcription with word-level timestamps (`start`, `end`).
- **🗣️ Speech Fluency & Filler Detection**: Detects common vocal fillers (`um`, `uh`, `like`, `so`, `you know`), calculates Words Per Minute (WPM) pacing, and flags hesitation silence gaps ($\ge 1.5$ seconds).
- **🧠 Semantic NLP Answer Scoring**: Uses MiniLM sentence vector embeddings (`all-MiniLM-L6-v2`) and Cosine Similarity to evaluate candidate answer accuracy against recruiter benchmark keys.
- **👀 Visual Posture & Face Analytics**: Uses OpenCV face detection to evaluate head posture stability and face visibility across video frames.
- **👥 Automatic Speaker Diarization**: Uses WeSpeaker and Silero VAD to cluster speakers and automatically distinguish the Candidate from the Interviewer based on speech duration, restricting visual analytics to Candidate-only segments.
- **⏭️ Skip-Logic Caching**: Automatically skips already processed video/audio chunks, avoiding redundant computations during repeated runs.
- **📊 Multi-Format Reporting & Dashboard**: Exports structured `final_aggregated_report.json` and `interview_timeline.csv`, paired with an interactive Web Analytics Studio.

---

## 📁 System Architecture & Directory Structure

```text
Interview_project/
├── data/
│   ├── input/               # Raw recorded interview video (sample.mp4)
│   ├── chunks/              # 10-second segmented MP4 chunks
│   ├── audio/               # Extracted 16kHz Mono WAV files
│   ├── outputs/             # Structured JSON output per chunk
│   └── reports/             # Aggregated final_aggregated_report.json & interview_timeline.csv
├── interview_pipeline/
│   └── src/
│       ├── chunking.py          # FFmpeg stream-copy video segmenter
│       ├── audio_extract.py     # 16kHz mono PCM WAV audio extractor
│       ├── stt.py               # Vosk offline speech-to-text engine
│       ├── filler_detection.py  # Vocal filler pattern detector
│       ├── speech_analysis.py   # WPM pacing & silence gap calculator
│       ├── visual_analytics.py  # OpenCV face visibility & posture analyzer
│       ├── nlp_scoring.py       # MiniLM vector cosine similarity scorer
│       ├── diarization.py       # WeSpeaker embeddings & clustering
│       ├── vad.py               # Silero VAD wrapper
│       ├── speaker_roles.py     # Candidate/Interviewer role assignment heuristic
│       ├── report_generator.py  # JSON/CSV report aggregator
│       └── pipeline.py          # Master pipeline orchestrator
├── models/
│   └── vosk/                # Offline Vosk speech model (vosk-model-small-en-us-0.15)
│   └── wespeaker/           # WeSpeaker ResNet34 ONNX
│   └── silero_vad/          # Silero VAD ONNX
├── dashboard/               # Interactive Web Analytics Studio UI
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── cli.py                   # Command-line interface entry point
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

---

## 🚀 Installation & Setup

### Prerequisites
- **Python 3.10+**
- **FFmpeg** installed and added to system `PATH`.

### Installation Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/Interview_project.git
   cd Interview_project
   ```

2. **Create and Activate Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Download Models** (Automatic or Manual):
   Download the small English model [vosk-model-small-en-us-0.15](https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip) and extract it into `models/vosk/vosk-model-small-en-us-0.15`.
   The `silero_vad.onnx` and `voxceleb_resnet34_LM.onnx` models should be placed in their respective `models/` subdirectories.

---

## 🏃 How to Run

### Diarization & Role Assignment
The pipeline identifies Candidate vs. Interviewer speech to focus the visual analysis.
- **Automatic Mode**: Triggered automatically if `--diarization` is omitted. The pipeline extracts full audio, runs Silero VAD, extracts speaker embeddings via WeSpeaker, clusters them via scikit-learn, and assigns the Candidate role to the speaker with the longest duration.
  *LIMITATION*: The duration heuristic assumes a typical interview where the candidate dominates talk time. It will mislabel speakers in highly conversational scenarios or pre-screening interviews where the interviewer speaks longer.
- **Precomputed Mode**: If you provide an existing JSON via `--diarization`, it skips automatic extraction and uses the provided segments.

### Basic Execution (Automatic Diarization & Visuals):
To run the full pipeline, automatically generating diarization and visual analytics:
```bash
python cli.py --input data/input/sample.mp4
```

### Precomputed Diarization:
To bypass automatic diarization and use an existing JSON:
```bash
python cli.py --input data/input/sample.mp4 --diarization data/diarization/segments.json
```

### Custom Output Directory:
To save outputs (chunks, audio, JSONs, reports) in a custom folder instead of the default `data/` directory:
```bash
python cli.py --input data/input/sample.mp4 --output-dir results/interview_1/
```

*Note: Dashboard and UI capabilities are planned for a future release.*

---

## 📊 Sample Output Metrics (`final_aggregated_report.json`)

```json
{
    "overall_metrics": {
        "total_chunks_processed": 8,
        "total_filler_words": 4,
        "total_long_pauses": 1,
        "total_silence_seconds": 30.31,
        "average_words_per_minute": 187.5,
        "average_visual_stability": 100.0
    },
    "full_interview_transcript": "first question is why investment banking... my last summer internship was on the fixed income trading desk..."
}
```

---

## 🎓 Academic Credits

**Institution**: SJB Institute of Technology, Bengaluru  
**Department**: Computer Science & Engineering  
**Under the Guidance of**: Asst. Prof. Vijayalaxmi Joshi  
**Project Team**:
- Skanda L (1JB23CS149)
- Swayam H (1JB23CS166)
- Thakur Sadanand (1JB23CS171)
- Udaya Aparanji (1JB23CS173)

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
