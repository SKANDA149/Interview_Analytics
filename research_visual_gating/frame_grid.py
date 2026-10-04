"""
research_visual_gating/frame_grid.py

Builds the ONE shared 5 FPS frame-timestamp grid used identically by every
condition (A, B-E, F_B-F_E). Every condition selects a SUBSET of this same
grid rather than generating its own timestamps, so "total grid frames" is
guaranteed identical across conditions (sanity check #2 in the design doc).

Uses the same index-multiplication rule as
interview_pipeline.src.visual_presence.generate_sample_timestamps (start +
i*step, not accumulated float addition) to avoid floating-point drift -
reimplemented independently here (not imported) because that function
builds per-candidate-segment timestamps tied to diarization, which this
study must not depend on.
"""
from __future__ import annotations

SAMPLE_FPS = 5  # matches the production pipeline's fixed sampling rate


def build_frame_grid(duration_sec: float, fps: int = SAMPLE_FPS) -> list:
    """Returns a sorted list of float timestamps (seconds) covering
    [0, duration_sec] at 1/fps spacing, inclusive of t=0 and the last
    timestamp <= duration_sec."""
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")
    if duration_sec <= 0:
        raise ValueError(f"duration_sec must be positive, got {duration_sec}")

    step = 1.0 / fps
    n_steps = int(duration_sec * fps + 1e-9)
    grid = []
    for i in range(n_steps + 1):
        t = round(i * step, 3)
        if t > duration_sec + 1e-9:
            break
        grid.append(t)
    return grid
