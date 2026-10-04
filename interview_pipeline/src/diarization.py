"""Minimal diarization data model.

NOTE: this file intentionally does NOT contain diarization/clustering logic.
It exists only to give visual_presence.py (and any other consumer) a stable
DiarizationSegment type plus a loader for the diarization output already on
disk at data/diarization/segments.json. The real diarization pipeline
(VAD -> speaker clustering -> role assignment) that PRODUCES that JSON lived
in a different copy of this project and is not part of this rebuild's scope.
"""
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class DiarizationSegment:
    """One labelled time interval from diarization + speaker-role assignment.
    `speaker` is expected to already be relabelled to "CANDIDATE" / "INTERVIEWER"
    (not a raw cluster id) by whatever produced the source JSON."""
    start: float
    end: float
    speaker: str


def load_segments(path) -> list:
    """Load a list of DiarizationSegment from a JSON file shaped like
    data/diarization/segments.json: a list of {"start", "end", "speaker"} objects."""
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [DiarizationSegment(start=item["start"], end=item["end"], speaker=item["speaker"]) for item in raw]


def save_segments(segments: list, path) -> None:
    """Write a list of DiarizationSegment back out in the same JSON shape."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [{"start": s.start, "end": s.end, "speaker": s.speaker} for s in segments]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
