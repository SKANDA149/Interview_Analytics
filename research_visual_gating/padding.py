"""
research_visual_gating/padding.py

Post-hoc symmetric padding/dilation of raw VAD speech intervals, and
interval merging. This is the ONLY experimental VAD-side variable in the
study (Conditions B/C/D/E = 0/250/500/1000 ms). The underlying VAD
detection parameters (vad.py) are frozen and identical across all of B-E.
"""
from __future__ import annotations

from dataclasses import dataclass

from research_visual_gating.vad import SpeechInterval


@dataclass
class Interval:
    start: float
    end: float


def dilate_and_merge(
    intervals: list,
    padding_ms: float,
    video_duration_sec: float,
) -> list:
    """Symmetrically expand each interval by padding_ms on both sides
    (start -= padding, end += padding), clamp to [0, video_duration_sec],
    then merge any intervals that now overlap or touch.

    Accepts SpeechInterval or Interval objects (anything with .start/.end);
    always returns a list of Interval, sorted by start, with no overlaps.
    """
    if padding_ms < 0:
        raise ValueError(f"padding_ms must be >= 0, got {padding_ms}")
    if video_duration_sec <= 0:
        raise ValueError(f"video_duration_sec must be > 0, got {video_duration_sec}")

    pad_sec = padding_ms / 1000.0

    padded = []
    for iv in intervals:
        start = max(0.0, iv.start - pad_sec)
        end = min(video_duration_sec, iv.end + pad_sec)
        if end > start:
            padded.append((start, end))

    if not padded:
        return []

    padded.sort(key=lambda t: t[0])

    merged = [list(padded[0])]
    for start, end in padded[1:]:
        last = merged[-1]
        if start <= last[1]:  # overlap or exact touch -> merge
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])

    return [Interval(start=s, end=e) for s, e in merged]


def total_duration(intervals: list) -> float:
    return sum(iv.end - iv.start for iv in intervals)


def is_within_any_interval(timestamp: float, intervals: list) -> bool:
    """Inclusive on both ends, matching the spec's "processes at least one
    frame inside that interval" language for eligibility checks."""
    return any(iv.start <= timestamp <= iv.end for iv in intervals)
