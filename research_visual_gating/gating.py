"""
research_visual_gating/gating.py

Frame-selection policies applied to the SHARED frame grid
(frame_grid.build_frame_grid). Every condition is defined purely as "which
indices of the same grid do we keep" - no condition ever builds its own
timestamps.

Condition A (always-on):        keep every grid index (identity - not a
                                 function here, just `grid` itself).
Conditions B-E (VAD-gated):      keep grid indices whose timestamp falls
                                 inside a (padded) speech interval.
Conditions F_B-F_E (matched
uniform control):                keep an evenly-spaced subset of the grid,
                                 sized to match the ACTUAL processed-frame
                                 count of the corresponding B-E condition -
                                 not a nominal/expected count.
"""
from __future__ import annotations

import numpy as np

from research_visual_gating.padding import is_within_any_interval


def select_frames_vad_gated(grid: list, speech_intervals: list) -> list:
    """Grid indices (into `grid`) whose timestamp falls within any of the
    given (already-padded, already-merged) speech intervals."""
    return [i for i, t in enumerate(grid) if is_within_any_interval(t, speech_intervals)]


def select_frames_matched_uniform(grid: list, target_count: int) -> list:
    """An evenly-spaced subset of grid indices of exactly `target_count`
    size (when 0 < target_count <= len(grid)), spanning the FULL grid
    (first index 0, last index len(grid)-1 whenever target_count > 1) -
    this is the "spread uniformly across the whole video" control, not a
    contiguous block and not restricted to any sub-region.

    Deterministic: uses evenly spaced float positions rounded to the
    nearest integer index, de-duplicated while preserving order, then
    padded from the remaining unselected indices (in order) if rounding
    collisions left it short of target_count. This guarantees the control
    condition processes the same number of frames as its matched VAD
    condition, per the design's non-negotiable requirement.
    """
    n = len(grid)
    if target_count <= 0:
        return []
    if target_count >= n:
        return list(range(n))

    positions = np.linspace(0, n - 1, num=target_count)
    indices = sorted(set(int(round(p)) for p in positions))

    if len(indices) < target_count:
        chosen = set(indices)
        remaining = [i for i in range(n) if i not in chosen]
        # Fill shortfall from remaining indices closest to their "ideal"
        # neighbors, in ascending order, to keep the result deterministic
        # and still spread rather than clumped.
        need = target_count - len(indices)
        step = n / target_count
        fill_positions = [int(round(k * step)) for k in range(target_count)]
        for p in fill_positions:
            if need <= 0:
                break
            p = min(max(p, 0), n - 1)
            if p not in chosen:
                chosen.add(p)
                need -= 1
        if need > 0:
            for r in remaining:
                if need <= 0:
                    break
                if r not in chosen:
                    chosen.add(r)
                    need -= 1
        indices = sorted(chosen)

    return indices[:target_count] if len(indices) > target_count else indices
