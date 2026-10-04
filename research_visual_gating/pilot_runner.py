"""
research_visual_gating/pilot_runner.py

Pilot orchestrator for: "VAD-Gated Selective Visual Analysis: CPU Cost vs
Information Loss in a Multimodal Interview Pipeline".

Conditions (all indexing into ONE shared 5 FPS frame grid, built once):
    A      - always-on: every grid frame processed (the reference for
             visual-event definition and for recall metrics).
    B/C/D/E - VAD-gated at 0/250/500/1000 ms symmetric padding (frozen VAD
             params: threshold=0.5, min_speech=250ms, min_silence=100ms;
             see vad.py). Padding is the only varied VAD-side parameter.
    F_B..F_E - matched-uniform controls: same processed-frame COUNT as the
             corresponding B/C/D/E condition (not a nominal target), spread
             evenly across the whole grid, ignoring audio entirely.

DECODE STRATEGY (locked after decode_calibration.py, not decided here):
Sequential single-pass decoding (cap.read() through every native frame
once) beat seek-per-timestamp (cap.set(POS_MSEC)+cap.read()) by ~8x on this
video/codec (0.00046s/native-frame decode vs 0.0223s/seek). Every
condition therefore decodes the ENTIRE video once per run - what varies
between conditions is only whether YuNet is invoked for a given grid
frame, never whether that frame's underlying native frame gets decoded.
THIS MEANS: none of the conditions in this pilot claim decode-time
savings. Only YuNet INFERENCE time is saved by gating. This is reported
honestly as the calibration finding it is, per the design doc's explicit
instruction not to silently claim decode savings that aren't real.

Timing isolation: only the sequential-decode + conditional-YuNet loop is
wrapped in profiling.measure() as "visual stage". VAD computation (run
once, up front, outside any timed condition block) is timed separately
and logged as vad_wall_time_s in run metadata, never folded into any
condition's wall_time_s/cpu_seconds.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from interview_pipeline.src.visual_presence import detect_faces, YUNET_MODEL_PATH, FACE_CONFIDENCE_THRESHOLD
from research_visual_gating.vad import (
    load_audio_16k_mono, get_raw_speech_intervals, DEFAULT_MODEL_PATH as VAD_MODEL_PATH,
    VAD_THRESHOLD, VAD_MIN_SPEECH_DURATION_MS, VAD_MIN_SILENCE_DURATION_MS,
)
from research_visual_gating.padding import dilate_and_merge, total_duration
from research_visual_gating.frame_grid import build_frame_grid, SAMPLE_FPS
from research_visual_gating.gating import select_frames_vad_gated, select_frames_matched_uniform
from research_visual_gating.visual_events import build_reference_intervals, interval_existence_recall, temporal_coverage_recall
from research_visual_gating.profiling import measure

CODE_VERSION = "research_visual_gating@v1-pilot"
PADDING_CONDITIONS = [("B", 0), ("C", 250), ("D", 500), ("E", 1000)]


def get_video_duration_and_fps(video_path: Path) -> tuple:
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")
        native_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if native_fps <= 0 or frame_count <= 0:
            raise RuntimeError(f"Could not read fps/frame_count from {video_path}")
        return frame_count / native_fps, native_fps
    finally:
        cap.release()


def sequential_process_video(video_path: Path, grid: list, target_grid_indices: set, native_fps: float) -> list:
    """ONE sequential decode pass over the whole video. For each grid
    timestamp whose index is in target_grid_indices, finds the nearest
    native frame and, only for those, runs YuNet. Returns a list of
    (grid_timestamp, face_detected: bool, confidence: float, num_faces: int)
    for PROCESSED frames only (skipped frames are not represented - they
    were never sent to YuNet, which is the entire point of gating)."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    # Map each target grid timestamp to its nearest native frame index.
    target_native_idx_to_grid = {}
    for gi in target_grid_indices:
        ts = grid[gi]
        native_idx = int(round(ts * native_fps))
        target_native_idx_to_grid[native_idx] = ts

    results = []
    try:
        native_i = 0
        remaining = dict(target_native_idx_to_grid)
        if not remaining:
            return results
        max_native_idx = max(remaining.keys())
        while native_i <= max_native_idx:
            ok, frame = cap.read()
            if not ok:
                break
            if native_i in remaining:
                ts = remaining.pop(native_i)
                faces = detect_faces(frame, model_path=YUNET_MODEL_PATH)
                if faces:
                    best = max(faces, key=lambda f: f.confidence)
                    results.append((ts, True, best.confidence, len(faces)))
                else:
                    results.append((ts, False, 0.0, 0))
            native_i += 1
    finally:
        cap.release()
    return results


@dataclass
class RunRecord:
    recording_id: str
    condition: str
    condition_type: str          # always_on / vad_gated / matched_uniform
    padding_ms: object
    matched_to_condition: object
    repeat_idx: int
    video_duration_s: float
    vad_speech_duration_s: float
    eligible_duration_s: float
    total_grid_frames: int
    processed_frames: int
    skipped_frames: int
    skip_pct: float
    wall_time_s: float
    cpu_seconds: float
    peak_rss_mb: float
    mean_rss_mb: object
    n_reference_intervals: object
    n_intervals_hit: object
    interval_existence_recall: object
    reference_face_time_s: object
    covered_face_time_s: object
    temporal_coverage_recall: object
    n_missed_intervals: object
    missed_interval_durations: object
    status: str
    model_config_id: str
    code_version: str
    run_timestamp: str
    notes: str


def _git_rev() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1])
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def run_pilot(video_path: Path, recording_id: str, repeats: int, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    video_duration, native_fps = get_video_duration_and_fps(video_path)
    grid = build_frame_grid(video_duration, fps=SAMPLE_FPS)
    print(f"[PILOT] video_duration={video_duration:.2f}s native_fps={native_fps} grid_size={len(grid)}")

    # --- VAD (timed separately, NEVER inside a condition's visual-stage timing) ---
    audio_path = video_path.parent.parent / "audio" / "full_audio.wav"
    if not audio_path.exists():
        audio_path = video_path  # fall back to letting ffmpeg pull audio straight from the video
    t0 = time.perf_counter()
    audio = load_audio_16k_mono(audio_path)
    raw_intervals = get_raw_speech_intervals(audio, VAD_MODEL_PATH)
    vad_wall_time_s = round(time.perf_counter() - t0, 4)
    print(f"[PILOT] VAD wall time: {vad_wall_time_s}s, raw intervals: {len(raw_intervals)}")

    padded_by_label = {
        label: dilate_and_merge(raw_intervals, pad_ms, video_duration)
        for label, pad_ms in PADDING_CONDITIONS
    }
    target_indices_by_label = {
        label: set(select_frames_vad_gated(grid, padded_by_label[label]))
        for label, _ in PADDING_CONDITIONS
    }

    code_version = _git_rev()
    model_config_id = f"yunet=2023mar,conf>={FACE_CONFIDENCE_THRESHOLD};vad=silero,thr={VAD_THRESHOLD},minspeech={VAD_MIN_SPEECH_DURATION_MS}ms,minsil={VAD_MIN_SILENCE_DURATION_MS}ms"

    all_records = []
    reference_intervals = None
    reference_processed_timestamps = None

    # Condition order: A first (needed to build the reference), then B-E,
    # then F_B-F_E (needs B-E's actual processed-frame counts).
    condition_plan = [("A", "always_on", None, None, set(range(len(grid))))]
    for label, pad_ms in PADDING_CONDITIONS:
        condition_plan.append((label, "vad_gated", pad_ms, None, target_indices_by_label[label]))

    for condition, condition_type, padding_ms, matched_to, target_indices in condition_plan:
        eligible_duration = total_duration(padded_by_label[condition]) if condition in target_indices_by_label else video_duration
        n_target = len(target_indices)

        for rep in range(-1, repeats):  # rep == -1 is the untimed warm-up
            with measure(sample_rss=True) as m:
                frame_results = sequential_process_video(video_path, grid, target_indices, native_fps)

            if rep == -1:
                if condition == "A":
                    reference_intervals = build_reference_intervals(
                        [(ts, present, conf) for ts, present, conf, _n in frame_results]
                    )
                    reference_processed_timestamps = {ts for ts, _p, _c, _n in frame_results}
                continue  # warm-up not recorded, per spec

            processed_ts = {ts for ts, _p, _c, _n in frame_results}
            n_processed = len(processed_ts)
            n_skipped = len(grid) - n_processed
            skip_pct = round(100.0 * n_skipped / len(grid), 2)

            if reference_intervals:
                exist = interval_existence_recall(processed_ts, reference_intervals)
                cov = temporal_coverage_recall(processed_ts, reference_intervals, grid)
            else:
                exist = {"recall": None, "n_intervals": None, "n_hit": None, "missed_intervals": []}
                cov = {"recall": None, "reference_face_time_s": None, "covered_face_time_s": None}

            rec = RunRecord(
                recording_id=recording_id,
                condition=condition,
                condition_type=condition_type,
                padding_ms=padding_ms,
                matched_to_condition=matched_to,
                repeat_idx=rep,
                video_duration_s=round(video_duration, 3),
                vad_speech_duration_s=round(sum(iv.end - iv.start for iv in raw_intervals), 3),
                eligible_duration_s=round(eligible_duration, 3),
                total_grid_frames=len(grid),
                processed_frames=n_processed,
                skipped_frames=n_skipped,
                skip_pct=skip_pct,
                wall_time_s=m.wall_time_s,
                cpu_seconds=m.cpu_seconds,
                peak_rss_mb=m.peak_rss_mb,
                mean_rss_mb=m.mean_rss_mb,
                n_reference_intervals=exist["n_intervals"],
                n_intervals_hit=exist["n_hit"],
                interval_existence_recall=exist["recall"],
                reference_face_time_s=cov["reference_face_time_s"],
                covered_face_time_s=cov["covered_face_time_s"],
                temporal_coverage_recall=cov["recall"],
                n_missed_intervals=len(exist["missed_intervals"]),
                missed_interval_durations=[iv.duration for iv in exist["missed_intervals"]],
                status="ok",
                model_config_id=model_config_id,
                code_version=code_version,
                run_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                notes="",
            )
            all_records.append(rec)
            print(f"[PILOT] {condition} rep={rep}: processed={n_processed} skip%={skip_pct} "
                  f"wall={m.wall_time_s}s cpu={m.cpu_seconds}s peakRSS={m.peak_rss_mb}MB "
                  f"exist_recall={exist['recall']} cov_recall={cov['recall']}")

    # --- Matched-uniform controls F_B..F_E, sized to the ACTUAL processed
    # frame count observed for each B-E condition's timed repeats (mean,
    # rounded) rather than the nominal/expected count. ---
    actual_processed_by_label = {}
    for label, _pad in PADDING_CONDITIONS:
        counts = [r.processed_frames for r in all_records if r.condition == label]
        actual_processed_by_label[label] = round(sum(counts) / len(counts)) if counts else 0

    for label, _pad in PADDING_CONDITIONS:
        target_count = actual_processed_by_label[label]
        f_indices = set(select_frames_matched_uniform(grid, target_count))
        f_condition = f"F_{label}"

        for rep in range(-1, repeats):
            with measure(sample_rss=True) as m:
                frame_results = sequential_process_video(video_path, grid, f_indices, native_fps)
            if rep == -1:
                continue

            processed_ts = {ts for ts, _p, _c, _n in frame_results}
            n_processed = len(processed_ts)
            n_skipped = len(grid) - n_processed
            skip_pct = round(100.0 * n_skipped / len(grid), 2)

            exist = interval_existence_recall(processed_ts, reference_intervals)
            cov = temporal_coverage_recall(processed_ts, reference_intervals, grid)

            rec = RunRecord(
                recording_id=recording_id,
                condition=f_condition,
                condition_type="matched_uniform",
                padding_ms=None,
                matched_to_condition=label,
                repeat_idx=rep,
                video_duration_s=round(video_duration, 3),
                vad_speech_duration_s=round(sum(iv.end - iv.start for iv in raw_intervals), 3),
                eligible_duration_s=None,
                total_grid_frames=len(grid),
                processed_frames=n_processed,
                skipped_frames=n_skipped,
                skip_pct=skip_pct,
                wall_time_s=m.wall_time_s,
                cpu_seconds=m.cpu_seconds,
                peak_rss_mb=m.peak_rss_mb,
                mean_rss_mb=m.mean_rss_mb,
                n_reference_intervals=exist["n_intervals"],
                n_intervals_hit=exist["n_hit"],
                interval_existence_recall=exist["recall"],
                reference_face_time_s=cov["reference_face_time_s"],
                covered_face_time_s=cov["covered_face_time_s"],
                temporal_coverage_recall=cov["recall"],
                n_missed_intervals=len(exist["missed_intervals"]),
                missed_interval_durations=[iv.duration for iv in exist["missed_intervals"]],
                status="ok",
                model_config_id=model_config_id,
                code_version=code_version,
                run_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                notes=f"target_count matched to mean processed_frames of condition {label}",
            )
            all_records.append(rec)
            print(f"[PILOT] {f_condition} rep={rep}: processed={n_processed} (target={target_count}) "
                  f"wall={m.wall_time_s}s cpu={m.cpu_seconds}s exist_recall={exist['recall']} cov_recall={cov['recall']}")

    # --- Sanity checks ---
    sanity = run_sanity_checks(all_records, grid, reference_intervals)
    print("[SANITY]", json.dumps(sanity, indent=2))

    # --- Write outputs ---
    ts_tag = time.strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"pilot_{recording_id}_{ts_tag}.json"
    csv_path = out_dir / f"pilot_{recording_id}_{ts_tag}.csv"
    ref_path = out_dir / f"reference_events_{recording_id}_{ts_tag}.json"

    json_path.write_text(json.dumps({
        "recording_id": recording_id,
        "video_path": str(video_path),
        "video_duration_s": video_duration,
        "vad_wall_time_s": vad_wall_time_s,
        "vad_frozen_params": {
            "threshold": VAD_THRESHOLD,
            "min_speech_duration_ms": VAD_MIN_SPEECH_DURATION_MS,
            "min_silence_duration_ms": VAD_MIN_SILENCE_DURATION_MS,
            "speech_pad_ms": 0,
        },
        "model_config_id": model_config_id,
        "code_version": code_version,
        "sanity_checks": sanity,
        "runs": [asdict(r) for r in all_records],
    }, indent=2))

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(all_records[0]).keys()))
        writer.writeheader()
        for r in all_records:
            writer.writerow(asdict(r))

    ref_path.write_text(json.dumps([asdict(iv) for iv in reference_intervals], indent=2))

    print(f"\n[PILOT] Wrote {json_path}\n[PILOT] Wrote {csv_path}\n[PILOT] Wrote {ref_path}")


def run_sanity_checks(records: list, grid: list, reference_intervals: list) -> dict:
    checks = {}

    a_records = [r for r in records if r.condition == "A"]
    checks["A_self_existence_recall_is_100pct"] = all(r.interval_existence_recall == 1.0 for r in a_records)
    checks["A_self_coverage_recall_is_100pct"] = all(r.temporal_coverage_recall == 1.0 for r in a_records)

    checks["all_conditions_share_grid_size"] = len(set(r.total_grid_frames for r in records)) == 1

    means = {}
    for label in ["B", "C", "D", "E"]:
        vals = [r.processed_frames for r in records if r.condition == label]
        means[label] = sum(vals) / len(vals) if vals else None
    checks["padding_monotonic_processed_frames_B_le_C_le_D_le_E"] = (
        means["B"] is not None and means["B"] <= means["C"] <= means["D"] <= means["E"]
    )

    for label in ["B", "C", "D", "E"]:
        b_mean = means[label]
        f_vals = [r.processed_frames for r in records if r.condition == f"F_{label}"]
        f_mean = sum(f_vals) / len(f_vals) if f_vals else None
        checks[f"F_{label}_matches_{label}_frame_count"] = (
            f_mean is not None and b_mean is not None and abs(f_mean - b_mean) <= 1
        )

    checks["no_failed_runs"] = all(r.status == "ok" for r in records)
    return checks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, default=Path("data/input/sample.mp4"))
    parser.add_argument("--recording-id", default="R1")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out-dir", type=Path, default=Path("research_visual_gating/results"))
    args = parser.parse_args()

    run_pilot(args.video, args.recording_id, args.repeats, args.out_dir)
