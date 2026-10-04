import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from research_visual_gating.visual_events import (
    build_reference_intervals, interval_existence_recall, temporal_coverage_recall,
    ReferenceInterval,
)
from research_visual_gating.frame_grid import build_frame_grid

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

print("test_visual_events.py")

# --- build_reference_intervals ---

# Simple contiguous run -> one interval
frames = [(0.0, True, 0.9), (0.2, True, 0.8), (0.4, True, 0.85), (0.6, False, 0.0)]
ivs = build_reference_intervals(frames)
check("contiguous presence merges into one interval", len(ivs) == 1)
check("interval spans first->last present frame", ivs[0].start == 0.0 and ivs[0].end == 0.4)
check("mean confidence computed correctly", abs(ivs[0].mean_confidence - (0.9+0.8+0.85)/3) < 1e-6)

# Flicker gap <= 200ms merges (grid step 0.2s here == exactly the merge threshold)
frames2 = [(1.0, True, 0.9), (1.1, False, 0.0), (1.2, True, 0.9)]
ivs2 = build_reference_intervals(frames2)
check("gap of exactly 200ms merges into one interval", len(ivs2) == 1)

# Gap > 200ms does NOT merge
frames3 = [(0.0, True, 0.9), (0.2, False, 0.0), (0.4, False, 0.0), (0.6, True, 0.9)]
ivs3 = build_reference_intervals(frames3)
check("gap > 200ms produces two separate intervals", len(ivs3) == 2)

# No face frames at all -> no intervals
check("all-absent input produces zero intervals",
      build_reference_intervals([(0.0, False, 0.0), (0.2, False, 0.0)]) == [])

# --- interval_existence_recall ---

ref = [ReferenceInterval(start=1.0, end=2.0, duration=1.0, mean_confidence=0.9),
       ReferenceInterval(start=5.0, end=6.0, duration=1.0, mean_confidence=0.9)]

# Sanity check: Condition A scored against itself (all reference points processed) = 100%
grid = build_frame_grid(10.0, fps=5)
all_ts = set(grid)
res_self = interval_existence_recall(all_ts, ref)
check("A-vs-itself: interval-existence recall == 100%", res_self["recall"] == 1.0)

cov_self = temporal_coverage_recall(all_ts, ref, grid)
check("A-vs-itself: temporal-coverage recall == 100%", cov_self["recall"] == 1.0)

# Missing one interval entirely
processed_missing_one = set(t for t in grid if not (5.0 <= t <= 6.0))
res_missing = interval_existence_recall(processed_missing_one, ref)
check("missing all frames of one interval -> recall 0.5, 1 missed", 
      res_missing["recall"] == 0.5 and len(res_missing["missed_intervals"]) == 1)

# Partial coverage within an interval still counts as "existence hit" (>=1 frame)
partial = {1.0}  # just the single boundary point of the first interval
res_partial = interval_existence_recall(partial | {5.0, 5.2, 5.4, 5.6, 5.8, 6.0}, ref)
check("a single hit anywhere in the interval satisfies existence recall",
      res_partial["recall"] == 1.0)

# Temporal coverage should be LOWER than existence recall when coverage is sparse but non-empty
cov_partial = temporal_coverage_recall(partial | {5.0, 5.2, 5.4, 5.6, 5.8, 6.0}, ref, grid)
check("temporal coverage penalizes sparse-but-existing coverage (< 100%)",
      cov_partial["recall"] < 1.0)
check("temporal coverage differs from existence recall for partial coverage",
      cov_partial["recall"] != res_partial["recall"])

# No processed frames at all -> both recalls are 0
res_empty = interval_existence_recall(set(), ref)
cov_empty = temporal_coverage_recall(set(), ref, grid)
check("zero processed frames -> existence recall 0.0", res_empty["recall"] == 0.0)
check("zero processed frames -> coverage recall 0.0", cov_empty["recall"] == 0.0)

print(f"visual_events: {passed} passed, {failed} failed")
if failed:
    sys.exit(1)

# --- Regression tests for the 2026-09-13 float-comparison merge bug ---
# Root cause: build_reference_intervals used to compare
# `ts - current_end <= gap_merge_seconds` on grid timestamps produced by
# `round(i * 0.2, 3)`. Consecutive gaps on the real 5443-frame grid are NOT
# uniformly 0.2 in float64 - some come out as 0.19999999999999996 (merges)
# and others as 0.20000000000000007 (does NOT merge under a bare `<=`
# comparison), fragmenting one continuous run into thousands of spurious
# intervals. These tests use the SAME grid-construction function the
# production pipeline uses, so they fail against the old float-subtraction
# implementation and pass against the index-based fix.

real_grid = build_frame_grid(1088.567, fps=5)  # the actual R1 pilot grid, 5443 frames

# Sanity: confirm this test grid genuinely reproduces the float artifact,
# so a pass below is not vacuous.
_diffs = [real_grid[i + 1] - real_grid[i] for i in range(len(real_grid) - 1)]
_n_gt_0_2 = sum(1 for d in _diffs if d > 0.2)
check("test fixture reproduces the float-representation artifact (some gaps > 0.2)",
      _n_gt_0_2 > 1000)

# A fully continuous face-visible run across the entire real grid must
# merge into exactly ONE interval, regardless of float gap jitter.
all_present = [(t, True, 0.9) for t in real_grid]
ivs_all = build_reference_intervals(all_present)
check("fully continuous presence on real 5443-frame grid merges into ONE interval "
      "(not fragmented by float gap jitter)", len(ivs_all) == 1)
check("single merged interval spans the whole grid",
      ivs_all[0].start == real_grid[0] and ivs_all[0].end == real_grid[-1])

# Four ISOLATED negative frames (not adjacent to each other or to the
# boundary) in an otherwise all-positive real grid must yield AT MOST 5
# true intervals (one per positive run between/around the 4 negatives) -
# not thousands.
neg_positions = {1000, 2000, 3000, 4000}
four_neg = [(t, i not in neg_positions, 0.9 if i not in neg_positions else 0.0)
            for i, t in enumerate(real_grid)]
ivs_four_neg = build_reference_intervals(four_neg)
check("4 isolated negative frames in an otherwise all-positive real grid "
      "yield at most 5 intervals (got %d)" % len(ivs_four_neg),
      len(ivs_four_neg) <= 5)
check("4 isolated negative frames yield AT LEAST 2 intervals (they must actually split)",
      len(ivs_four_neg) >= 2)

# The exact R1 pilot shape: only 4 negative frames total among 5443 must
# NOT fragment into anywhere close to ~2713 intervals (the bug's observed
# symptom on the real pilot data).
check("4 negatives among 5443 frames does not reproduce the ~2713-interval bug symptom",
      len(ivs_four_neg) < 20)

print(f"visual_events (incl. regression): {passed} passed, {failed} failed")
if failed:
    sys.exit(1)
