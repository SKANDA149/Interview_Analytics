"""
research_visual_gating/offline_recompute.py

OFFLINE repair-and-extend analysis for the R1 pilot. Does NOT invoke
YuNet, does NOT decode video, does NOT touch runs.jsonl or the original
pilot_report_R1.md / vad-gated-visual-pilot-results.md. Reads only the
already-persisted artifacts:
  - results/R1_checkpointed/reference_frame_results.json  (Condition A's
    5443 per-frame face-detection results, unchanged)
  - results/R1_checkpointed/vad_raw_intervals.json        (cached raw VAD
    output, unchanged)
  - results/R1_checkpointed/runs.jsonl                    (for the already-
    measured processed_frames counts of B/C/D/E, used only to size the
    matched-uniform and random controls exactly as the original pilot did)

Recomputes, with the FIXED (index-based) build_reference_intervals:
  1. Corrected reference intervals + occupancy statistics.
  2. Corrected interval-existence recall and temporal-coverage recall for
     A, B, C, D, E, F_B..F_E (frame *selections* for all of these are
     deterministic functions of the shared grid + cached VAD intervals +
     padding + target_count, so they are recomputed here rather than
     re-read from anywhere - there was never a stored per-run selection
     mask, only aggregate counts).
  3. NEW: deterministic random-sampling controls R_B..R_E at the same
     target_count as their matched VAD/uniform counterparts, using a
     fixed, recorded seed (see RANDOM_SEED below).

Writes one output file: results/R1_checkpointed/corrected_analysis.json.
Prints a human-readable summary table to stdout. No experimental
parameter (VAD threshold, padding values, YuNet confidence, frame grid)
is changed anywhere in this script.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from research_visual_gating.frame_grid import build_frame_grid, SAMPLE_FPS
from research_visual_gating.padding import dilate_and_merge, Interval
from research_visual_gating.gating import select_frames_vad_gated, select_frames_matched_uniform
from research_visual_gating.visual_events import (
    build_reference_intervals, interval_existence_recall, temporal_coverage_recall,
)

OUT_DIR = Path("research_visual_gating/results/R1_checkpointed")
VIDEO_DURATION_S = 1088.567  # from runs.jsonl video_duration_s (unchanged, not re-measured)
PADDING_CONDITIONS = [("B", 0), ("C", 250), ("D", 500), ("E", 1000)]

# Fixed, recorded seed for the new random-sampling control. This is an
# ANALYSIS addition (Task 3) - it does not touch the VAD, YuNet, or
# frame-grid parameters of the original design.
RANDOM_SEED = 20260913


def load_reference_frame_results() -> list:
    data = json.loads((OUT_DIR / "reference_frame_results.json").read_text())
    # stored as [ts, present, conf, n_faces] - keep only what build_reference_intervals needs
    return [(r[0], r[1], r[2]) for r in data]


def load_vad_intervals() -> list:
    data = json.loads((OUT_DIR / "vad_raw_intervals.json").read_text())
    from research_visual_gating.vad import SpeechInterval
    return [SpeechInterval(start=d["start"], end=d["end"]) for d in data["intervals"]]


def load_processed_frame_counts() -> dict:
    """Mean processed_frames for each timed VAD condition B/C/D/E, exactly
    as F_B..F_E's target_count was computed during the original pilot."""
    counts = {}
    for line in (OUT_DIR / "runs.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        counts.setdefault(r["condition"], []).append(r["processed_frames"])
    return {c: round(sum(v) / len(v)) for c, v in counts.items()}


def select_frames_random(grid: list, target_count: int, seed: int) -> list:
    """Deterministic random subset of grid indices, exactly target_count
    in size (when 0 < target_count <= len(grid)), no replacement, sorted.
    A fixed seed makes this fully reproducible across re-runs of this
    script."""
    n = len(grid)
    if target_count <= 0:
        return []
    if target_count >= n:
        return list(range(n))
    rng = random.Random(seed)
    return sorted(rng.sample(range(n), target_count))


def missed_interval_stats(missed: list) -> dict:
    durs = [iv.duration for iv in missed]
    return {
        "n_missed": len(missed),
        "sum_missed_face_time_s": round(sum(durs), 3),
        "mean_duration_s": round(sum(durs) / len(durs), 4) if durs else 0.0,
        "max_duration_s": round(max(durs), 4) if durs else 0.0,
        "n_zero_duration": sum(1 for d in durs if d == 0.0),
        "n_over_0_4s": sum(1 for d in durs if d >= 0.4),
        "durations": durs,
    }


def evaluate(label: str, condition_type: str, indices: set, grid: list, reference_intervals: list) -> dict:
    processed_ts = {grid[i] for i in indices}
    exist = interval_existence_recall(processed_ts, reference_intervals)
    cov = temporal_coverage_recall(processed_ts, reference_intervals, grid)
    missed_stats = missed_interval_stats(exist["missed_intervals"])
    return {
        "condition": label,
        "condition_type": condition_type,
        "processed_frames": len(indices),
        "interval_existence_recall": exist["recall"],
        "n_reference_intervals": exist["n_intervals"],
        "n_intervals_hit": exist["n_hit"],
        "temporal_coverage_recall": cov["recall"],
        "reference_face_time_s": cov["reference_face_time_s"],
        "covered_face_time_s": cov["covered_face_time_s"],
        **missed_stats,
    }


def main():
    grid = build_frame_grid(VIDEO_DURATION_S, fps=SAMPLE_FPS)
    total_grid_frames = len(grid)

    # --- Occupancy (from Condition A's raw per-frame results, unchanged) ---
    frame_results = load_reference_frame_results()
    n_positive = sum(1 for r in frame_results if r[1])
    n_negative = total_grid_frames - n_positive
    occupancy_pct = round(100 * n_positive / total_grid_frames, 4)

    reference_intervals = build_reference_intervals(frame_results)

    occupancy_report = {
        "total_grid_frames": total_grid_frames,
        "positive_reference_frames": n_positive,
        "negative_reference_frames": n_negative,
        "face_presence_occupancy_pct": occupancy_pct,
        "corrected_reference_interval_count": len(reference_intervals),
        "original_reported_reference_interval_count": 2713,
    }

    # --- Recompute deterministic frame selections for every condition ---
    raw_vad = load_vad_intervals()
    padded_by_label = {label: dilate_and_merge(raw_vad, pad_ms, VIDEO_DURATION_S)
                        for label, pad_ms in PADDING_CONDITIONS}
    measured_counts = load_processed_frame_counts()  # from original runs.jsonl, e.g. {"A":5443,"B":3978,...}

    results = []

    # A: always-on
    a_indices = set(range(total_grid_frames))
    results.append(evaluate("A", "always_on", a_indices, grid, reference_intervals))

    for label, pad_ms in PADDING_CONDITIONS:
        vad_indices = set(select_frames_vad_gated(grid, padded_by_label[label]))
        consistency = (len(vad_indices) == measured_counts.get(label))
        rec = evaluate(label, "vad_gated", vad_indices, grid, reference_intervals)
        rec["padding_ms"] = pad_ms
        rec["matches_original_processed_frame_count"] = consistency
        rec["original_processed_frames"] = measured_counts.get(label)
        results.append(rec)

        target_count = len(vad_indices)  # match the ACTUAL recomputed count, same rule pilot used

        uniform_indices = set(select_frames_matched_uniform(grid, target_count))
        rec_u = evaluate(f"F_{label}", "matched_uniform", uniform_indices, grid, reference_intervals)
        rec_u["matched_to_condition"] = label
        rec_u["target_count"] = target_count
        results.append(rec_u)

        random_indices = set(select_frames_random(grid, target_count, seed=RANDOM_SEED))
        rec_r = evaluate(f"R_{label}", "random", random_indices, grid, reference_intervals)
        rec_r["matched_to_condition"] = label
        rec_r["target_count"] = target_count
        rec_r["random_seed"] = RANDOM_SEED
        results.append(rec_r)

    output = {
        "note": "OFFLINE recomputation. No YuNet inference or video decode was performed. "
                "Reference frame-level detections and VAD intervals are read unchanged from "
                "the original pilot's cached artifacts. Uses the FIXED (index-based) "
                "build_reference_intervals. Original pilot_report_R1.md / "
                "vad-gated-visual-pilot-results.md are left untouched.",
        "occupancy": occupancy_report,
        "results": results,
    }

    out_path = OUT_DIR / "corrected_analysis.json"
    out_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"Wrote {out_path}")

    # --- Human-readable summary ---
    print()
    print("=== OCCUPANCY (corrected) ===")
    for k, v in occupancy_report.items():
        print(f"  {k}: {v}")

    print()
    print("=== PER-CONDITION SUMMARY (corrected metrics) ===")
    header = f"{'cond':8}{'type':16}{'frames':8}{'exist_recall':14}{'cov_recall':12}{'n_missed':10}{'sum_missed_s':14}"
    print(header)
    for r in results:
        print(f"{r['condition']:8}{r['condition_type']:16}{r['processed_frames']:<8}"
              f"{str(r['interval_existence_recall']):14}{str(r['temporal_coverage_recall']):12}"
              f"{r['n_missed']:<10}{r['sum_missed_face_time_s']:<14}")


if __name__ == "__main__":
    main()
