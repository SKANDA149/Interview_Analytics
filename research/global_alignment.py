"""
research/global_alignment.py

MINIMAL GLUE MODULE (new, necessary addition — approved).

This project's pipeline (interview_pipeline/src/pipeline.py) processes video
in independent 10-second chunks via Vosk STT and never attributes speech to
a speaker (CANDIDATE vs INTERVIEWER) at all — speech_analysis.py treats each
chunk's words as one undifferentiated stream. However, this project's data/
folder already contains a role-labelled reference diarization
(data/diarization/segments.json, global/absolute timestamps) that nothing in
the current code consumes.

The paper's angle requires diarization-aware candidate-only metrics, which
this pipeline never produced. This module adds the minimum glue needed:
1) stitch per-chunk Vosk word timestamps into one global timeline (each
   chunk is a fixed 10s window, per pipeline.py's chunk_duration=10), and
2) attribute each global word to CANDIDATE/INTERVIEWER via max-overlap
   against the reference diarization segments.
No existing pipeline module is modified; this only adds new read-only glue.
"""
import glob
import json
import os
from dataclasses import dataclass

CHUNK_DURATION_SEC = 10.0  # matches pipeline.py's split_video_into_chunks(chunk_duration=10)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@dataclass
class Segment:
    start: float
    end: float
    speaker: str


def load_reference_segments(path=None):
    path = path or os.path.join(DATA_DIR, "diarization", "segments.json")
    with open(path) as f:
        raw = json.load(f)
    return [Segment(start=item["start"], end=item["end"], speaker=item["speaker"]) for item in raw]


def load_global_words(outputs_dir=None):
    """
    Preferred path: data/outputs/full_transcript.json, produced by
    research/transcribe_full_audio.py, which transcribes the ENTIRE
    interview in one continuous pass and already carries GLOBAL (absolute)
    word timestamps -- no chunk-offset stitching needed or possible to get
    wrong. Falls back to stitching per-chunk chunk_NNN.json outputs (each a
    fixed CHUNK_DURATION_SEC window) only if that file is absent, for
    backward compatibility / partial-data smoke testing.
    """
    outputs_dir = outputs_dir or os.path.join(DATA_DIR, "outputs")

    full_transcript_path = os.path.join(outputs_dir, "full_transcript.json")
    if os.path.exists(full_transcript_path):
        with open(full_transcript_path) as f:
            data = json.load(f)
        return [{"word": w["word"], "start": w["start"], "end": w["end"]} for w in data.get("words", [])]

    chunk_files = sorted(glob.glob(os.path.join(outputs_dir, "chunk_*.json")))
    global_words = []
    for idx, path in enumerate(chunk_files):
        with open(path) as f:
            data = json.load(f)
        offset = idx * CHUNK_DURATION_SEC
        for w in data.get("words", []):
            if "start" not in w or "end" not in w:
                continue
            global_words.append({
                "word": w["word"],
                "start": w["start"] + offset,
                "end": w["end"] + offset,
            })
    return global_words


ATTRIBUTION_POLICIES = ("fallback", "strict")


def align_words_to_speakers(words, segments, policy="fallback"):
    """
    Max-overlap word-to-speaker alignment. For each word, picks the
    diarization segment with the greatest temporal overlap.

    A word may overlap NO segment at all -- this is rare in the reference
    diarization (4 / 2498 words) but becomes common once the missed_speech
    operator deletes candidate segments (33% of words at severity 0.50).
    How those unattributed words are handled materially changes downstream
    metrics, so it is an explicit, reported parameter rather than a hidden
    assumption:

      policy="fallback" -- assign the word to the NEAREST segment by
          boundary gap. Mirrors the recovery behaviour of the sibling
          project's production aligner. Keeps words attributed to CANDIDATE
          even when the segment covering them was deleted, so the WPM
          numerator stays high while the duration denominator shrinks.

      policy="strict" -- drop the word entirely (it is unattributed, and
          belongs to neither speaker). Numerator and denominator shrink
          together.

    Neither is "the" correct choice; they encode different pipeline design
    decisions, and the difference between them is itself a finding.
    """
    if policy not in ATTRIBUTION_POLICIES:
        raise ValueError(f"policy must be one of {ATTRIBUTION_POLICIES}, got {policy!r}")

    labelled = []
    if not segments:
        for w in words:
            labelled.append({**w, "speaker": "CANDIDATE"})
        return labelled

    sorted_segments = sorted(segments, key=lambda s: s.start)

    for w in words:
        w_start, w_end = w["start"], w["end"]
        best_seg = None
        best_overlap = 0.0
        for seg in sorted_segments:
            overlap = min(w_end, seg.end) - max(w_start, seg.start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_seg = seg

        if best_seg is None:
            if policy == "strict":
                continue  # unattributed -- belongs to neither speaker
            nearest = min(
                sorted_segments,
                key=lambda s: min(abs(w_start - s.end), abs(s.start - w_end))
            )
            best_seg = nearest

        labelled.append({**w, "speaker": best_seg.speaker})
    return labelled


def extract_candidate_data(labelled_words, candidate_label="CANDIDATE"):
    candidate_words = [w for w in labelled_words if w["speaker"] == candidate_label]
    candidate_transcript = " ".join(w["word"] for w in candidate_words).strip()
    return candidate_transcript, candidate_words
