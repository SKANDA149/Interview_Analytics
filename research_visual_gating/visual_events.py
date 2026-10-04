"""
research_visual_gating/visual_events.py

Defines "visual event" from Condition A (always-on) reference results, and
the two retention metrics used for every gated/control condition:
interval-existence recall and temporal-coverage recall. Per-frame recall
alone is deliberately NOT computed as a headline metric (it's a
restatement of skip percentage) - see design doc.

IMPORTANT LIMITATION (must appear in the paper, not just here): the
"reference" is Condition A's own YuNet output, not independent human
ground truth. All retention numbers are relative to this pipeline's own
established always-on operating point.

BUG FIX (2026-09-13): build_reference_intervals originally merged
consecutive positive frames by comparing floating-point timestamp gaps
(`ts - current_end <= gap_merge_seconds`). Grid timestamps are produced by
`round(i * 0.2, 3)`, and for many values of i the resulting float64 is not
bit-exact 0.2*k - consecutive gaps came out as both 0.19999999999999996
and 0.20000000000000007 depending on i, so the same nominal 200ms gap
sometimes compared <=0.200 and sometimes did not. On the R1 pilot data
(5439/5443 frames positive, only 4 negative frames total) this fragmented
what should have been a handful of intervals into ~2713 spurious
two-frame pseudo-intervals, invalidating interval_existence_recall and
every missed-interval statistic derived from it.

FIX: adjacency between two positive frames is now decided by their
INTEGER POSITIONS in the (grid-ordered) frame_results list, never by
subtracting float timestamps. The grid spacing is inferred once (median
of early consecutive gaps, robust to any single float artifact) and the
merge threshold is expressed as a frame-index gap
(round(gap_merge_seconds / grid_step)), so a whole-run flicker in the
float representation cannot change the discrete outcome. Timestamps are
still stored on the resulting ReferenceInterval objects (start/end/
duration are timestamp-based, purely for reporting) - only the merge
DECISION is now index-based.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

GAP_MERGE_SECONDS = 0.200  # gaps <= this are merged into one interval (flicker guard)


@dataclass
class ReferenceInterval:
    start: float
    end: float
    duration: float
    mean_confidence: float


def _infer_grid_step(frame_results: list, default: float = 1.0 / 5) -> float:
    """Median of the first ~50 consecutive timestamp gaps, rounded to 3
    decimals. Robust to an occasional float-representation outlier in any
    single gap (which is exactly the failure mode being fixed)."""
    n = min(50, len(frame_results) - 1)
    if n <= 0:
        return default
    diffs = [round(frame_results[i + 1][0] - frame_results[i][0], 3) for i in range(n)]
    diffs = [d for d in diffs if d > 0]
    if not diffs:
        return default
    return statistics.median(diffs)


def build_reference_intervals(
    frame_results: list,
    gap_merge_seconds: float = GAP_MERGE_SECONDS,
) -> list:
    """frame_results: list of (timestamp, face_detected: bool, confidence: float),
    sorted by timestamp, from Condition A only (every grid frame processed).
    Consecutive face-visible frames are merged into one interval; a gap
    between two face-visible frames of <= gap_merge_seconds also gets
    merged (bridges dropouts up to that many grid steps).

    Adjacency is decided on INTEGER FRAME-LIST POSITIONS, not on
    subtracting floating-point timestamps (see module docstring for why:
    grid timestamps are not always bit-exact multiples of the nominal
    step, which previously fragmented continuous face presence into
    thousands of spurious single/double-frame intervals). Timestamps are
    used only to populate the reported start/end/duration of each interval
    once its membership has been decided by index.
    """
    frame_results = sorted(frame_results, key=lambda r: r[0])
    if not frame_results:
        return []

    grid_step = _infer_grid_step(frame_results)
    merge_gap_steps = max(1, round(gap_merge_seconds / grid_step)) if grid_step > 0 else 1

    intervals = []
    current_start_i = None
    current_end_i = None
    current_confs = []

    def _flush():
        if current_start_i is not None:
            start_ts = frame_results[current_start_i][0]
            end_ts = frame_results[current_end_i][0]
            intervals.append(
                ReferenceInterval(
                    start=start_ts,
                    end=end_ts,
                    duration=round(end_ts - start_ts, 3),
                    mean_confidence=round(sum(current_confs) / len(current_confs), 4) if current_confs else 0.0,
                )
            )

    for i, (ts, present, conf) in enumerate(frame_results):
        if not present:
            continue
        if current_start_i is None:
            current_start_i = current_end_i = i
            current_confs = [conf]
        elif i - current_end_i <= merge_gap_steps:
            current_end_i = i
            current_confs.append(conf)
        else:
            _flush()
            current_start_i = current_end_i = i
            current_confs = [conf]

    _flush()
    return intervals


def interval_existence_recall(processed_timestamps: set, reference_intervals: list) -> dict:
    """Fraction of reference intervals with >= 1 processed-frame timestamp
    landing inside [start, end] (inclusive)."""
    if not reference_intervals:
        return {"recall": None, "n_intervals": 0, "n_hit": 0, "missed_intervals": []}

    n_hit = 0
    missed = []
    for iv in reference_intervals:
        hit = any(iv.start <= t <= iv.end for t in processed_timestamps)
        if hit:
            n_hit += 1
        else:
            missed.append(iv)

    return {
        "recall": round(n_hit / len(reference_intervals), 4),
        "n_intervals": len(reference_intervals),
        "n_hit": n_hit,
        "missed_intervals": missed,
    }


def temporal_coverage_recall(
    processed_timestamps: set,
    reference_intervals: list,
    grid: list,
) -> dict:
    """Discretized on the shared grid: for every grid timestamp that falls
    inside a reference (face-visible) interval, check whether that exact
    grid timestamp was processed. Coverage = (# reference-positive grid
    points processed) / (# reference-positive grid points), reported both
    as a fraction and as an approximate seconds figure (grid points *
    nominal grid spacing) for readability. This is NOT the same metric as
    interval-existence recall: a long interval needs most of its grid
    points covered to score well here, whereas existence recall is
    satisfied by a single hit.

    KNOWN LIMITATION (see repaired-pilot assessment): when the underlying
    recording is near-saturated with reference-positive frames (as R1 is,
    ~99.9%), `reference_face_time_s` approaches the full recording length
    and this metric becomes numerically close to (processed_frames /
    total_grid_frames) regardless of which frames were chosen - i.e. it
    degenerates into a restatement of the sampling budget and loses most
    of its power to distinguish selection strategies. It remains correct;
    it just is not informative on a saturated recording.
    """
    if not reference_intervals or not grid:
        return {"recall": None, "reference_face_time_s": 0.0, "covered_face_time_s": 0.0}

    grid_step = (grid[1] - grid[0]) if len(grid) > 1 else (1.0 / 5)

    ref_points = [t for t in grid if any(iv.start <= t <= iv.end for iv in reference_intervals)]
    if not ref_points:
        return {"recall": None, "reference_face_time_s": 0.0, "covered_face_time_s": 0.0}

    covered_points = [t for t in ref_points if t in processed_timestamps]

    reference_face_time_s = round(len(ref_points) * grid_step, 3)
    covered_face_time_s = round(len(covered_points) * grid_step, 3)

    return {
        "recall": round(len(covered_points) / len(ref_points), 4),
        "reference_face_time_s": reference_face_time_s,
        "covered_face_time_s": covered_face_time_s,
        "n_reference_points": len(ref_points),
        "n_covered_points": len(covered_points),
    }
