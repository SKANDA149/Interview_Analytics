"""
research_visual_gating/pilot_single_run_v1i.py

Checkpointed pilot runner for video1_infosys_h264.mp4 (the "v1i" recording),
mirroring pilot_single_run.py's one-(condition,repeat)-per-invocation design
(same reason: this environment kills any background process the moment the
launching shell call returns, and a single call has a hard ~180s ceiling).
Reuses every frozen module unchanged: vad.py, padding.py, frame_grid.py,
gating.py, visual_events.py, profiling.py, and pilot_runner.py's
get_video_duration_and_fps/_git_rev/PADDING_CONDITIONS. select_frames_random
and RANDOM_SEED are reused unchanged from offline_recompute.py (same fixed
seed 20260913, same sampling algorithm - "matched-control construction"
stays frozen).

REVISED (2026-09-13, recalibration pass) - simpler than the first version
of this file. The first version assumed the candidate's own tile changed
shape (off-camera / full-view / PIP during screen-share) and built a
canonical-pass-then-lookup architecture with a stateful persistence/
hysteresis smoother to keep layout-state assignment consistent across
conditions. Video inspection (see
vad-gated-video1-infosys-recalibration.md) showed the candidate/interviewer
identities were swapped and, once corrected, the actual candidate region
is a single FIXED thumbnail that never changes shape or position,
including through the interviewer's screen-share window. A fixed-ROI
detection is fully deterministic per frame - it needs no history, no
canonical pass, and no lookup file, so this version detects independently
in every run and drops all of that machinery. layout_state is now simply
FULL_VIEW iff a face was found in the one fixed CANDIDATE_ROI, OFF_CAMERA
otherwise (research_visual_gating/candidate_layout.py). There is exactly
one reference-interval set (no PIP split - see the recalibration report
for why a separate PIP category was evaluated and found unnecessary).

State that persists between calls (all under --out-dir):
  - vad_raw_intervals.json              - raw VAD output, computed once, cached
  - reference_frame_results_v1i.json    - Condition A's full per-frame
                                           (timestamp, layout_state, present,
                                           confidence, n_faces) records
  - runs.jsonl                          - one JSON line per completed TIMED run
                                           (warm-ups are executed but never appended)
  - _partial_<condition>_<repeat>.json  - part-1..N-1 scratch state; consumed
                                           by the final part

Required call order (identical in shape to pilot_single_run.py's):
  A   repeat=-1,0,1,2   (repeat=-1 also persists reference_frame_results_v1i.json)
  B   repeat=-1,0,1,2
  C   repeat=-1,0,1,2
  D   repeat=-1,0,1,2
  E   repeat=-1,0,1,2
  F_B repeat=-1,0,1,2   (target_count = mean of B's 3 timed processed_frames)
  F_C repeat=-1,0,1,2
  F_D repeat=-1,0,1,2
  F_E repeat=-1,0,1,2
  R_B repeat=-1,0,1,2   (same target_count as F_B - "equal processed-frame
                         budgets" across VAD/uniform/random)
  R_C repeat=-1,0,1,2
  R_D repeat=-1,0,1,2
  R_E repeat=-1,0,1,2

Does NOT change: VAD parameters, YuNet model/confidence threshold, 5 FPS
frame grid, padding values, the candidate ROI, the 200ms reference-merge
gap definition, or matched-control construction (uniform spacing /
fixed-seed random sampling).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from interview_pipeline.src.visual_presence import detect_faces, YUNET_MODEL_PATH, FACE_CONFIDENCE_THRESHOLD
from research_visual_gating.vad import (
    load_audio_16k_mono, get_raw_speech_intervals, DEFAULT_MODEL_PATH as VAD_MODEL_PATH,
    VAD_THRESHOLD, VAD_MIN_SPEECH_DURATION_MS, VAD_MIN_SILENCE_DURATION_MS, SpeechInterval,
)
from research_visual_gating.padding import dilate_and_merge, total_duration
from research_visual_gating.frame_grid import build_frame_grid, SAMPLE_FPS
from research_visual_gating.gating import select_frames_vad_gated, select_frames_matched_uniform
from research_visual_gating.offline_recompute import select_frames_random, RANDOM_SEED
from research_visual_gating.visual_events import build_reference_intervals, interval_existence_recall, temporal_coverage_recall
from research_visual_gating.profiling import measure
from research_visual_gating.pilot_runner import get_video_duration_and_fps, _git_rev, PADDING_CONDITIONS
from research_visual_gating.candidate_layout import detect_candidate_presence, OFF_CAMERA, FULL_VIEW

ALL_CONDITIONS = ["A", "B", "C", "D", "E", "F_B", "F_C", "F_D", "F_E", "R_B", "R_C", "R_D", "R_E"]


def process_range(video_path: Path, grid: list, target_grid_indices: set,
                   native_fps: float, native_start: int, native_end: int) -> list:
    """One sequential decode pass over [native_start, native_end). For each
    target grid timestamp, runs detect_candidate_presence against the one
    fixed CANDIDATE_ROI - fully independent per frame, no state carried
    across calls, so any condition/order/split produces identical
    per-timestamp results."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    target_native_idx_to_grid = {}
    for gi in target_grid_indices:
        ts = grid[gi]
        native_idx = int(round(ts * native_fps))
        if native_start <= native_idx < native_end:
            target_native_idx_to_grid[native_idx] = ts

    results = []
    try:
        if native_start > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, native_start)
        native_i = native_start
        remaining = dict(target_native_idx_to_grid)
        while native_i < native_end:
            ok, frame = cap.read()
            if not ok:
                break
            if native_i in remaining:
                ts = remaining.pop(native_i)
                r = detect_candidate_presence(frame, ts, YUNET_MODEL_PATH, detect_faces)
                results.append((r.timestamp, r.layout_state, r.present, r.confidence, r.n_faces))
            native_i += 1
    finally:
        cap.release()
    return results


def _load_or_compute_vad(out_dir: Path, video_path: Path) -> tuple:
    cache_path = out_dir / "vad_raw_intervals.json"
    if cache_path.exists():
        data = json.loads(cache_path.read_text())
        intervals = [SpeechInterval(start=d["start"], end=d["end"]) for d in data["intervals"]]
        return intervals, data["vad_wall_time_s"]

    audio_path = video_path.parent.parent / "audio" / "full_audio.wav"
    if not audio_path.exists():
        audio_path = video_path
    t0 = time.perf_counter()
    audio = load_audio_16k_mono(audio_path)
    intervals = get_raw_speech_intervals(audio, VAD_MODEL_PATH)
    vad_wall_time_s = round(time.perf_counter() - t0, 4)

    cache_path.write_text(json.dumps({
        "vad_wall_time_s": vad_wall_time_s,
        "intervals": [{"start": iv.start, "end": iv.end} for iv in intervals],
        "frozen_params": {
            "threshold": VAD_THRESHOLD,
            "min_speech_duration_ms": VAD_MIN_SPEECH_DURATION_MS,
            "min_silence_duration_ms": VAD_MIN_SILENCE_DURATION_MS,
            "speech_pad_ms": 0,
        },
    }, indent=2))
    return intervals, vad_wall_time_s


def _persist_reference(out_dir: Path, frame_results: list) -> None:
    (out_dir / "reference_frame_results_v1i.json").write_text(json.dumps(
        [[ts, state, present, conf, n] for ts, state, present, conf, n in frame_results]
    ))


def _load_reference_intervals(out_dir: Path):
    path = out_dir / "reference_frame_results_v1i.json"
    if not path.exists():
        return None
    records = json.loads(path.read_text())  # [ts, state, present, conf, n]
    ref_in = [(r[0], r[2], r[3]) for r in records]
    return build_reference_intervals(ref_in)


def _recall_block(processed_ts: set, ref_intervals: list, grid: list) -> dict:
    exist = interval_existence_recall(processed_ts, ref_intervals)
    cov = temporal_coverage_recall(processed_ts, ref_intervals, grid)
    missed = exist["missed_intervals"]
    return {
        "n_reference_intervals": exist["n_intervals"],
        "n_intervals_hit": exist["n_hit"],
        "interval_existence_recall": exist["recall"],
        "reference_face_time_s": cov["reference_face_time_s"],
        "covered_face_time_s": cov["covered_face_time_s"],
        "temporal_coverage_recall": cov["recall"],
        "n_missed_intervals": len(missed),
        "missed_interval_durations": [iv.duration for iv in missed],
    }


def _append_run(out_dir: Path, rec) -> None:
    with open(out_dir / "runs.jsonl", "a") as f:
        f.write(json.dumps(asdict(rec)) + "\n")


def _load_all_runs(out_dir: Path) -> list:
    path = out_dir / "runs.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _base_target_count(out_dir: Path, base_label: str) -> int:
    counts = [r["processed_frames"] for r in _load_all_runs(out_dir) if r["condition"] == base_label]
    if len(counts) < 3:
        print(f"ERROR: need 3 timed runs of condition {base_label} recorded before running a control matched "
              f"to it (found {len(counts)}). Run {base_label} repeats 0,1,2 first.", file=sys.stderr)
        sys.exit(2)
    return round(sum(counts) / len(counts))


def _partial_path(out_dir: Path, condition: str, repeat: int) -> Path:
    return out_dir / f"_partial_{condition}_{repeat}.json"


@dataclass
class RunRecordV1I:
    recording_id: str
    condition: str
    condition_type: str          # always_on / vad_gated / matched_uniform / random
    padding_ms: object
    matched_to_condition: object
    repeat_idx: int
    video_duration_s: float
    vad_speech_duration_s: float
    eligible_duration_s: object
    total_grid_frames: int
    processed_frames: int
    skipped_frames: int
    skip_pct: float
    n_off_camera_processed: int
    n_full_view_processed: int
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, default=Path("research_visual_gating/data/video1_infosys_h264.mp4"))
    parser.add_argument("--recording-id", default="video1_infosys")
    parser.add_argument("--out-dir", type=Path, default=Path("research_visual_gating/results/video1_infosys_checkpointed"))
    parser.add_argument("--condition", required=True, choices=ALL_CONDITIONS)
    parser.add_argument("--repeat", type=int, required=True, help="-1 = warm-up, 0/1/2 = timed")
    parser.add_argument("--part", type=int, default=None)
    parser.add_argument("--n-parts", type=int, default=None)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    video_duration, native_fps = get_video_duration_and_fps(args.video)
    grid = build_frame_grid(video_duration, fps=SAMPLE_FPS)
    total_native_frames = int(video_duration * native_fps) + 1

    raw_intervals, vad_wall_time_s = _load_or_compute_vad(args.out_dir, args.video)
    padded_by_label = {label: dilate_and_merge(raw_intervals, pad_ms, video_duration) for label, pad_ms in PADDING_CONDITIONS}
    vad_speech_duration_s = round(sum(iv.end - iv.start for iv in raw_intervals), 3)
    model_config_id = (f"yunet=2023mar,conf>={FACE_CONFIDENCE_THRESHOLD};"
                        f"vad=silero,thr={VAD_THRESHOLD},minspeech={VAD_MIN_SPEECH_DURATION_MS}ms,"
                        f"minsil={VAD_MIN_SILENCE_DURATION_MS}ms;candidate_layout=v1i_corrected")
    code_version = _git_rev()

    condition = args.condition
    padding_ms = None
    matched_to = None

    if condition == "A":
        condition_type = "always_on"
        target_indices = set(range(len(grid)))
        eligible_duration = video_duration
    elif condition in ("B", "C", "D", "E"):
        condition_type = "vad_gated"
        padding_ms = dict(PADDING_CONDITIONS)[condition]
        target_indices = set(select_frames_vad_gated(grid, padded_by_label[condition]))
        eligible_duration = total_duration(padded_by_label[condition])
    elif condition.startswith("F_"):
        condition_type = "matched_uniform"
        matched_to = condition.split("_")[1]
        target_count = _base_target_count(args.out_dir, matched_to)
        target_indices = set(select_frames_matched_uniform(grid, target_count))
        eligible_duration = None
    else:  # R_*
        condition_type = "random"
        matched_to = condition.split("_")[1]
        target_count = _base_target_count(args.out_dir, matched_to)
        target_indices = set(select_frames_random(grid, target_count, seed=RANDOM_SEED))
        eligible_duration = None

    # --- Decode + detect, possibly split into N equal-width native-frame ranges ---
    if args.part is None:
        with measure(sample_rss=True) as m:
            frame_results = process_range(args.video, grid, target_indices, native_fps, 0, total_native_frames)
        wall_time_s, cpu_seconds, peak_rss_mb, mean_rss_mb = m.wall_time_s, m.cpu_seconds, m.peak_rss_mb, m.mean_rss_mb
    else:
        if not args.n_parts or not (1 <= args.part <= args.n_parts):
            print("ERROR: --part requires --n-parts and 1 <= part <= n_parts.", file=sys.stderr)
            sys.exit(2)
        n_parts = args.n_parts
        native_start = (args.part - 1) * total_native_frames // n_parts
        native_end = args.part * total_native_frames // n_parts if args.part < n_parts else total_native_frames

        with measure(sample_rss=True) as m:
            part_results = process_range(args.video, grid, target_indices, native_fps, native_start, native_end)

        partial_path = _partial_path(args.out_dir, condition, args.repeat)
        if args.part == 1:
            accumulated = {
                "frame_results": [[ts, st, p, c, n] for ts, st, p, c, n in part_results],
                "wall_time_s": m.wall_time_s,
                "cpu_seconds": m.cpu_seconds,
                "peak_rss_mb": m.peak_rss_mb,
                "mean_rss_mb_list": [m.mean_rss_mb] if m.mean_rss_mb is not None else [],
            }
        else:
            if not partial_path.exists():
                print(f"ERROR: part={args.part} requested but accumulated state ({partial_path}) is missing. "
                      f"Run parts in order starting at --part 1.", file=sys.stderr)
                sys.exit(2)
            prev = json.loads(partial_path.read_text())
            accumulated = {
                "frame_results": prev["frame_results"] + [[ts, st, p, c, n] for ts, st, p, c, n in part_results],
                "wall_time_s": round(prev["wall_time_s"] + m.wall_time_s, 4),
                "cpu_seconds": round(prev["cpu_seconds"] + m.cpu_seconds, 4),
                "peak_rss_mb": round(max(prev["peak_rss_mb"], m.peak_rss_mb), 2),
                "mean_rss_mb_list": prev["mean_rss_mb_list"] + ([m.mean_rss_mb] if m.mean_rss_mb is not None else []),
            }

        if args.part < n_parts:
            partial_path.write_text(json.dumps(accumulated))
            print(f"[CHECKPOINT] {condition} repeat={args.repeat} part={args.part}/{n_parts}: "
                  f"native[{native_start}:{native_end}) -> {len(part_results)} processed frames, "
                  f"wall={m.wall_time_s}s cpu={m.cpu_seconds}s. Run --part {args.part + 1} next.")
            return

        frame_results = [tuple(r) for r in accumulated["frame_results"]]
        wall_time_s = accumulated["wall_time_s"]
        cpu_seconds = accumulated["cpu_seconds"]
        peak_rss_mb = accumulated["peak_rss_mb"]
        mrl = accumulated["mean_rss_mb_list"]
        mean_rss_mb = round(sum(mrl) / len(mrl), 2) if mrl else None
        print(f"[CHECKPOINT] {condition} repeat={args.repeat} part={args.part}/{n_parts} (FINAL): "
              f"native[{native_start}:{native_end}) -> {len(part_results)} processed frames. "
              f"Combined: wall={wall_time_s}s cpu={cpu_seconds}s total_processed={len(frame_results)}")

    if args.repeat == -1:
        if condition == "A":
            _persist_reference(args.out_dir, frame_results)
            print(f"[CHECKPOINT] {condition} repeat=-1 (warm-up): persisted reference_frame_results_v1i.json "
                  f"({len(frame_results)} frames). wall={wall_time_s}s (untimed/not recorded).")
        else:
            print(f"[CHECKPOINT] {condition} repeat=-1 (warm-up, not recorded). wall={wall_time_s}s")
        return

    processed_ts = {r[0] for r in frame_results}
    n_processed = len(processed_ts)
    n_skipped = len(grid) - n_processed
    skip_pct = round(100.0 * n_skipped / len(grid), 2)
    n_off_camera = sum(1 for r in frame_results if r[1] == OFF_CAMERA)
    n_full_view = sum(1 for r in frame_results if r[1] == FULL_VIEW)

    ref_intervals = _load_reference_intervals(args.out_dir)
    if ref_intervals is None:
        print("ERROR: reference_frame_results_v1i.json not found - run condition A repeat=-1 first.", file=sys.stderr)
        sys.exit(2)

    block = _recall_block(processed_ts, ref_intervals, grid)

    rec = RunRecordV1I(
        recording_id=args.recording_id,
        condition=condition,
        condition_type=condition_type,
        padding_ms=padding_ms,
        matched_to_condition=matched_to,
        repeat_idx=args.repeat,
        video_duration_s=round(video_duration, 3),
        vad_speech_duration_s=vad_speech_duration_s,
        eligible_duration_s=round(eligible_duration, 3) if eligible_duration is not None else None,
        total_grid_frames=len(grid),
        processed_frames=n_processed,
        skipped_frames=n_skipped,
        skip_pct=skip_pct,
        n_off_camera_processed=n_off_camera,
        n_full_view_processed=n_full_view,
        wall_time_s=wall_time_s,
        cpu_seconds=cpu_seconds,
        peak_rss_mb=peak_rss_mb,
        mean_rss_mb=mean_rss_mb,
        n_reference_intervals=block["n_reference_intervals"],
        n_intervals_hit=block["n_intervals_hit"],
        interval_existence_recall=block["interval_existence_recall"],
        reference_face_time_s=block["reference_face_time_s"],
        covered_face_time_s=block["covered_face_time_s"],
        temporal_coverage_recall=block["temporal_coverage_recall"],
        n_missed_intervals=block["n_missed_intervals"],
        missed_interval_durations=block["missed_interval_durations"],
        status="ok",
        model_config_id=model_config_id,
        code_version=code_version,
        run_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        notes=(f"target_count matched to mean processed_frames of condition {matched_to}"
               if condition_type in ("matched_uniform", "random") else ""),
    )
    _append_run(args.out_dir, rec)
    print(f"[CHECKPOINT] {condition} repeat={args.repeat} DONE: processed={n_processed} skip%={skip_pct} "
          f"(off_cam={n_off_camera} full_view={n_full_view}) "
          f"wall={wall_time_s}s cpu={cpu_seconds}s peakRSS={peak_rss_mb}MB "
          f"exist_recall={block['interval_existence_recall']} cov_recall={block['temporal_coverage_recall']}")


if __name__ == "__main__":
    main()
