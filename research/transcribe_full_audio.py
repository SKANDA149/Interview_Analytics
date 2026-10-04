"""
research/transcribe_full_audio.py

Standalone, non-destructive full-interview transcription. Reuses
interview_pipeline.src.stt.format_transcription() UNMODIFIED, but runs Vosk
directly against data/audio/full_audio.wav in one pass instead of pipeline.py's
per-10s-chunk loop -- so it does not touch or overwrite any existing
data/outputs/chunk_*.json files, and does not require re-chunking or
re-extracting audio.

Produces data/outputs/full_transcript.json: {"chunk_id","transcript","words"}
with GLOBAL (absolute) word timestamps directly, ready for
research/global_alignment.py to consume without any chunk-offset stitching.

Run once, after models/vosk/vosk-model-small-en-us-0.15/ exists.
"""
import json
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vosk import Model, KaldiRecognizer
from interview_pipeline.src.stt import format_transcription

AUDIO_PATH = Path(__file__).resolve().parent.parent / "data" / "audio" / "full_audio.wav"
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "vosk" / "vosk-model-small-en-us-0.15"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "outputs" / "full_transcript.json"


def main():
    if not AUDIO_PATH.exists():
        raise SystemExit(f"Missing {AUDIO_PATH}")
    if not MODEL_PATH.exists():
        raise SystemExit(f"Missing Vosk model at {MODEL_PATH}")

    print(f"[TRANSCRIBE] Loading Vosk model from {MODEL_PATH} ...")
    t0 = time.time()
    model = Model(str(MODEL_PATH))
    print(f"[TRANSCRIBE] Model loaded in {time.time()-t0:.1f}s")

    wf = wave.open(str(AUDIO_PATH), "rb")
    channels, framerate, sampwidth = wf.getnchannels(), wf.getframerate(), wf.getsampwidth()
    if channels != 1 or framerate != 16000 or sampwidth != 2:
        raise SystemExit(f"Invalid audio format: {channels}ch {framerate}Hz {sampwidth*8}-bit")

    rec = KaldiRecognizer(model, framerate)
    rec.SetWords(True)

    results = []
    t0 = time.time()
    frames_read = 0
    total_frames = wf.getnframes()
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        frames_read += 4000
        if rec.AcceptWaveform(data):
            results.append(json.loads(rec.Result()))
        if frames_read % 400000 < 4000:
            pct = min(100.0, 100.0 * frames_read / total_frames)
            print(f"[TRANSCRIBE] {pct:.0f}% ({time.time()-t0:.0f}s elapsed)")
    results.append(json.loads(rec.FinalResult()))
    wf.close()

    result = format_transcription(results, "full_interview")
    print(f"[TRANSCRIBE] Done in {time.time()-t0:.1f}s. "
          f"{len(result['words'])} words, transcript length {len(result['transcript'])} chars.")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"[TRANSCRIBE] Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
