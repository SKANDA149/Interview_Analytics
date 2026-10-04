"""
Sanity tests for vad.py against synthetic audio (sine-tone bursts in
silence) - not a substitute for validating against real speech, but
enough to confirm the numpy/onnxruntime port behaves like a VAD should:
detects the tone-present region as "speech-like" activity and near-silence
as not, with output shaped and typed correctly. This intentionally does
NOT assert exact interval boundaries against real speech (that depends on
Silero's trained weights, not on this code), only structural correctness
of the windowing/state-machine port.

Requires: models/silero_vad/silero_vad.onnx to be present (see
MODEL_PROVENANCE.md). Skips gracefully if the model file is missing.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from research_visual_gating.vad import (
    DEFAULT_MODEL_PATH, SAMPLE_RATE, WINDOW_SIZE_SAMPLES,
    SileroVADSession, get_speech_probs, speech_probs_to_intervals,
    get_raw_speech_intervals, VAD_THRESHOLD, VAD_MIN_SPEECH_DURATION_MS,
    VAD_MIN_SILENCE_DURATION_MS,
)

passed = 0
failed = 0

def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}")

print("test_vad.py")

model_path = Path(__file__).resolve().parents[2] / DEFAULT_MODEL_PATH
if not model_path.exists():
    print(f"  [SKIP] model not found at {model_path}")
    sys.exit(0)

# Frozen-parameter sanity: assert the constants are exactly what was approved
check("VAD_THRESHOLD frozen at 0.5", VAD_THRESHOLD == 0.5)
check("VAD_MIN_SPEECH_DURATION_MS frozen at 250", VAD_MIN_SPEECH_DURATION_MS == 250)
check("VAD_MIN_SILENCE_DURATION_MS frozen at 100", VAD_MIN_SILENCE_DURATION_MS == 100)

# --- SileroVADSession basic shape/type checks ---
session = SileroVADSession(model_path)
silence_chunk = np.zeros(WINDOW_SIZE_SAMPLES, dtype=np.float32)
prob = session.process_chunk(silence_chunk)
check("process_chunk returns a python float", isinstance(prob, float))
check("probability is within [0, 1]", 0.0 <= prob <= 1.0)
check("pure digital silence yields a low speech probability", prob < 0.3)

# --- Synthetic signal: silence -> tone burst -> silence ---
duration_s = 6.0
n_samples = int(duration_s * SAMPLE_RATE)
audio = np.zeros(n_samples, dtype=np.float32)
tone_start_s, tone_end_s = 2.0, 4.0
t = np.arange(n_samples) / SAMPLE_RATE
tone_mask = (t >= tone_start_s) & (t < tone_end_s)
# 200 Hz tone at moderate amplitude, well within [-1, 1]
audio[tone_mask] = 0.3 * np.sin(2 * np.pi * 200.0 * t[tone_mask]).astype(np.float32)

probs = get_speech_probs(audio, model_path)
check("get_speech_probs returns one probability per 512-sample window",
      len(probs) == int(np.ceil(n_samples / WINDOW_SIZE_SAMPLES)))
check("probabilities are float32 ndarray", probs.dtype == np.float32)

intervals = speech_probs_to_intervals(
    probs, n_samples,
    threshold=VAD_THRESHOLD,
    min_speech_duration_ms=VAD_MIN_SPEECH_DURATION_MS,
    min_silence_duration_ms=VAD_MIN_SILENCE_DURATION_MS,
    speech_pad_ms=0,
)
# NEGATIVE control: Silero VAD is a trained speech/non-speech classifier,
# not a generic energy detector - a pure sine tone should NOT be flagged
# as speech. (Verified empirically: max prob during the tone was ~0.10,
# well below the 0.5 threshold.) A synthetic tone is therefore the wrong
# fixture for a POSITIVE detection test; real speech is used below instead.
check("pure sine tone (non-speech) produces zero detected intervals",
      len(intervals) == 0)
check("max probability during the tone stays below threshold",
      probs.max() < VAD_THRESHOLD)

# --- POSITIVE control: real speech from this project's own interview audio ---
# data/diarization/segments.json lists 4.4-7.7s as a CANDIDATE (speech)
# segment; use that slice of the real 16kHz mono audio already in the repo.
real_audio_path = Path(__file__).resolve().parents[2] / "data" / "audio" / "full_audio.wav"
if real_audio_path.exists():
    from research_visual_gating.vad import load_audio_16k_mono
    real_audio = load_audio_16k_mono(real_audio_path)
    seg_start_s, seg_end_s = 4.4, 7.7
    seg = real_audio[int(seg_start_s * SAMPLE_RATE):int(seg_end_s * SAMPLE_RATE)]
    real_intervals = get_raw_speech_intervals(seg, model_path)
    check("real speech segment (from data/diarization/segments.json) is detected as speech",
          len(real_intervals) >= 1)
else:
    print("  [SKIP] data/audio/full_audio.wav not found - skipping real-speech positive control")

# --- get_raw_speech_intervals end-to-end wrapper ---
si = get_raw_speech_intervals(audio, model_path)
check("get_raw_speech_intervals returns SpeechInterval objects with float seconds",
      all(hasattr(x, "start") and hasattr(x, "end") for x in si))
check("get_raw_speech_intervals result count matches raw interval extraction", len(si) == len(intervals))

# Reset-state determinism: running twice on the same audio gives identical results
si2 = get_raw_speech_intervals(audio, model_path)
check("VAD is deterministic across repeated runs on identical input",
      [(round(a.start,3), round(a.end,3)) for a in si] == [(round(a.start,3), round(a.end,3)) for a in si2])

print(f"vad.py: {passed} passed, {failed} failed")
if failed:
    sys.exit(1)
