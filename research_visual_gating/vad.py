"""
research_visual_gating/vad.py

Minimal, torch-free Silero VAD wrapper: raw ONNX Runtime + NumPy only.

Why hand-written rather than `pip install silero-vad`: that package still
hard-imports torch+torchaudio even on its "onnx" code path (see inspection
notes), and a default `pip install torch` pulls a multi-GB CUDA toolkit that
contradicts this project's CPU-only, no-CUDA framing. This module
reimplements exactly the same streaming-inference and interval-extraction
algorithm as the official `silero_vad.utils_vad.get_speech_timestamps`
(ported by reading that source, version 6.2.1), using only onnxruntime and
numpy against the official `silero_vad.onnx` model file
(models/silero_vad/silero_vad.onnx, sha256 recorded in
research_visual_gating/MODEL_PROVENANCE.md).

FROZEN PARAMETERS (chosen = Silero's own published defaults, NOT tuned on
this recording or any other data in this project):
    VAD_THRESHOLD = 0.5
    VAD_MIN_SPEECH_DURATION_MS = 250
    VAD_MIN_SILENCE_DURATION_MS = 100
    VAD_SPEECH_PAD_MS = 0   <- deliberately 0, NOT Silero's own default of 30.
        Silero's own speech_pad_ms is a fixed, non-experimental pad baked
        into the reference algorithm. This study's post-hoc padding sweep
        (0/250/500/1000 ms, applied in padding.py) is what we vary
        instead, so raw intervals here must come out unpadded or the two
        paddings would confound each other.

These values must not change between conditions B-E; only the post-hoc
padding varies (see padding.py).
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort

VAD_THRESHOLD = 0.5
VAD_MIN_SPEECH_DURATION_MS = 250
VAD_MIN_SILENCE_DURATION_MS = 100
VAD_SPEECH_PAD_MS = 0  # see module docstring - intentional, not Silero's default

SAMPLE_RATE = 16000
WINDOW_SIZE_SAMPLES = 512  # fixed by the model for 16 kHz input
CONTEXT_SIZE = 64          # fixed by the model for 16 kHz input
STATE_SHAPE = (2, 1, 128)  # (layers, batch=1, hidden)

DEFAULT_MODEL_PATH = Path("models/silero_vad/silero_vad.onnx")


@dataclass
class SpeechInterval:
    start: float  # seconds
    end: float    # seconds


def load_audio_16k_mono(path: Path) -> np.ndarray:
    """Load an audio (or video) file as 16kHz mono float32 PCM in [-1, 1]
    via ffmpeg, entirely in memory (no intermediate file). Works whether
    `path` is already a 16kHz mono WAV or a video container with an audio
    track - ffmpeg resamples/downmixes either way, so callers never need to
    care which they were given."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Audio/video source not found: {path}")

    cmd = [
        "ffmpeg", "-v", "error", "-i", str(path),
        "-f", "f32le", "-acodec", "pcm_f32le",
        "-ac", "1", "-ar", str(SAMPLE_RATE),
        "-",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed decoding {path}: {proc.stderr.decode(errors='replace')}")
    audio = np.frombuffer(proc.stdout, dtype=np.float32).copy()
    return audio


class SileroVADSession:
    """Streaming Silero VAD inference, batch size fixed at 1. Numerically
    replicates silero_vad.utils_vad.OnnxWrapper.__call__ (v6.2.1): the
    concatenated (context + chunk) windowing and recurrent state passing,
    without any torch dependency."""

    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH):
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Silero VAD ONNX model not found: {model_path}")
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(model_path), sess_options=opts, providers=["CPUExecutionProvider"]
        )
        self.reset_states()

    def reset_states(self) -> None:
        self._state = np.zeros(STATE_SHAPE, dtype=np.float32)
        self._context = np.zeros((1, CONTEXT_SIZE), dtype=np.float32)

    def process_chunk(self, chunk_512: np.ndarray) -> float:
        """chunk_512: exactly WINDOW_SIZE_SAMPLES float32 samples, shape (512,)
        or (1, 512). Returns the speech probability for this chunk and
        advances internal state/context for the next call."""
        x = np.asarray(chunk_512, dtype=np.float32).reshape(1, -1)
        if x.shape[1] != WINDOW_SIZE_SAMPLES:
            raise ValueError(f"expected {WINDOW_SIZE_SAMPLES} samples, got {x.shape[1]}")

        x_with_context = np.concatenate([self._context, x], axis=1)  # (1, 576)
        ort_inputs = {
            "input": x_with_context.astype(np.float32),
            "state": self._state.astype(np.float32),
            "sr": np.array(SAMPLE_RATE, dtype=np.int64),
        }
        out, new_state = self.session.run(None, ort_inputs)
        self._state = new_state
        self._context = x_with_context[:, -CONTEXT_SIZE:]
        return float(out[0, 0])


def get_speech_probs(audio: np.ndarray, model_path: Path = DEFAULT_MODEL_PATH) -> np.ndarray:
    """Run the VAD over the whole signal, chunk by chunk (zero-padding the
    final partial chunk), returning one probability per WINDOW_SIZE_SAMPLES
    window - the same chunking `get_speech_timestamps` uses internally."""
    session = SileroVADSession(model_path)
    n = len(audio)
    probs = []
    for start in range(0, n, WINDOW_SIZE_SAMPLES):
        chunk = audio[start:start + WINDOW_SIZE_SAMPLES]
        if len(chunk) < WINDOW_SIZE_SAMPLES:
            chunk = np.pad(chunk, (0, WINDOW_SIZE_SAMPLES - len(chunk)))
        probs.append(session.process_chunk(chunk))
    return np.array(probs, dtype=np.float32)


def speech_probs_to_intervals(
    speech_probs: np.ndarray,
    audio_length_samples: int,
    threshold: float = VAD_THRESHOLD,
    min_speech_duration_ms: int = VAD_MIN_SPEECH_DURATION_MS,
    min_silence_duration_ms: int = VAD_MIN_SILENCE_DURATION_MS,
    speech_pad_ms: int = VAD_SPEECH_PAD_MS,
    sampling_rate: int = SAMPLE_RATE,
    window_size_samples: int = WINDOW_SIZE_SAMPLES,
) -> list:
    """Direct numpy port of silero_vad.utils_vad.get_speech_timestamps'
    thresholding/hangover state machine (v6.2.1), with
    max_speech_duration_s fixed at infinity (Silero's own default - the
    "split overly long speech chunks" branch never fires and is omitted
    for clarity, not skipped for convenience: with max_speech_samples=inf,
    `cur_sample - start > max_speech_samples` is always False in the
    original too).

    Returns a list of {"start": samples, "end": samples} dicts, unpadded
    by default (speech_pad_ms=0 here; see module docstring)."""
    neg_threshold = max(threshold - 0.15, 0.01)
    min_speech_samples = sampling_rate * min_speech_duration_ms / 1000
    min_silence_samples = sampling_rate * min_silence_duration_ms / 1000
    speech_pad_samples = sampling_rate * speech_pad_ms / 1000

    triggered = False
    speeches = []
    current_speech = {}
    temp_end = 0

    for i, prob in enumerate(speech_probs):
        cur_sample = window_size_samples * i

        if prob >= threshold and temp_end:
            temp_end = 0

        if prob >= threshold and not triggered:
            triggered = True
            current_speech["start"] = cur_sample
            continue

        if prob < neg_threshold and triggered:
            if not temp_end:
                temp_end = cur_sample
            sil_dur_now = cur_sample - temp_end
            if sil_dur_now < min_silence_samples:
                continue
            current_speech["end"] = temp_end
            if (current_speech["end"] - current_speech["start"]) > min_speech_samples:
                speeches.append(current_speech)
            current_speech = {}
            temp_end = 0
            triggered = False
            continue

    if current_speech and (audio_length_samples - current_speech["start"]) > min_speech_samples:
        current_speech["end"] = audio_length_samples
        speeches.append(current_speech)

    # speech_pad_ms application (symmetric, with shared-silence splitting
    # for adjacent chunks) - identical structure to the reference, but with
    # speech_pad_samples=0 by default this is a no-op.
    for i, speech in enumerate(speeches):
        if i == 0:
            speech["start"] = int(max(0, speech["start"] - speech_pad_samples))
        if i != len(speeches) - 1:
            silence_duration = speeches[i + 1]["start"] - speech["end"]
            if silence_duration < 2 * speech_pad_samples:
                speech["end"] += int(silence_duration // 2)
                speeches[i + 1]["start"] = int(max(0, speeches[i + 1]["start"] - silence_duration // 2))
            else:
                speech["end"] = int(min(audio_length_samples, speech["end"] + speech_pad_samples))
                speeches[i + 1]["start"] = int(max(0, speeches[i + 1]["start"] - speech_pad_samples))
        else:
            speech["end"] = int(min(audio_length_samples, speech["end"] + speech_pad_samples))

    return speeches


def get_raw_speech_intervals(
    audio: np.ndarray,
    model_path: Path = DEFAULT_MODEL_PATH,
    threshold: float = VAD_THRESHOLD,
    min_speech_duration_ms: int = VAD_MIN_SPEECH_DURATION_MS,
    min_silence_duration_ms: int = VAD_MIN_SILENCE_DURATION_MS,
) -> list:
    """End-to-end: raw 16kHz mono float32 audio -> list of SpeechInterval in
    seconds, using the frozen parameters. This is the single entry point
    the rest of the pilot should call; it fixes speech_pad_ms=0 so the only
    padding ever applied is the experimental one in padding.py."""
    probs = get_speech_probs(audio, model_path)
    raw = speech_probs_to_intervals(
        probs, len(audio),
        threshold=threshold,
        min_speech_duration_ms=min_speech_duration_ms,
        min_silence_duration_ms=min_silence_duration_ms,
        speech_pad_ms=0,
    )
    return [
        SpeechInterval(start=s["start"] / SAMPLE_RATE, end=s["end"] / SAMPLE_RATE)
        for s in raw
    ]
