"""
research_visual_gating/pilot_single_run.py

Checkpointed variant of pilot_runner.py's condition loop: runs exactly ONE
(condition, repeat) combination per invocation and appends its result to a
JSON-lines file, so the pilot can be driven across many short-lived shell
calls (the execution environment kills any background process the moment
the shell call that launched it returns - confirmed empirically, each
call runs in its own throwaway PID namespace) while producing the SAME
per-run computation as pilot_runner.py's single-process loop would have:
same modules (vad.py, padding.py, frame_grid.py, gating.py,
visual_events.py, profiling.py), same RunRecord schema, same sequential
decode-then-conditionally-detect strategy. Nothing about the experimental
design changes; only HOW the 36 runs get invoked changes.

TIME-BUDGET SPLITTING (--part 1|2): a single call processing the full
grid (Condition A, or any condition whose frame count approaches ~5000)
can exceed this environment's ~180s hard per-call ceiling. When a run
needs splitting, it is done as TWO sequential decode passes over disjoint,
contiguous NATIVE-frame ranges (seek once to the range's start via
CAP_PROP_POS_FRAMES, then decode sequentially through it - one seek per
part, not per frame, so this does not reintroduce the per-frame seek cost
the calibration ruled out). Part 1's raw per-frame results and timing are
persisted to a small partial-state file; part 2 loads that, appends its
own range's results, and only THEN builds the final RunRecord (summed
wall_time_s and cpu_seconds across both parts, max of the two peak_rss_mb
values). This is purely a consequence of the shell time limit, not a
change to what is measured - the combined wall_time_s equals what one
uninterrupted process would have measured processing the same frames in
the same order.

State that persists between calls (all under --out-dir):
  - vad_raw_intervals.json           - raw VAD output, computed once, cached
  - reference_frame_results.json     - Condition A's full per-frame detections,
                                        written after Condition A repeat=-1 completes
  - runs.jsonl                       - one JSON line per completed TIMED run
                                        (warm-ups are executed but never appended)
  - _partial_<condition>_<repeat>.json - part-1 scratch state, consumed and
                                        left in place (informational) by part 2

Required call order (identical run order to the single-process design):
  A  repeat=-1        (also persists reference_frame_results.json)
  A  repeat=0,1,2
  B  repeat=-1,0,1,2
  C  repeat=-1,0,1,2
  D  repeat=-1,0,1,2
  E  repeat=-1,0,1,2
  F_B repeat=-1,0,1,2  (target_count = mean of B's 3 timed processed_frames)
  F_C repeat=-1,0,1,2
  F_D repeat=-1,0,1,2
  F_E repeat=-1,0,1,2
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
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
from research_visual_gating.visual_events import build_reference_intervals, interval_existence_recall, temporal_coverage_recall
from research_visual_gating.profiling import measure
from research_visual_gating.pilot_runner import (
    get_video_duration_and_fps, RunRecord, _git_rev, PADDING_CONDITIONS,
)


def sequential_process_range(video_path: Path, grid: list, target_grid_indices: set,
                              native_fps: float, native_start: int, native_end: int) -> list:
    """Same semantics as pilot_runner.sequential_process_video, restricted
    to native frame indices [native_start, native_end). Seeks ONCE to
    native_start (CAP_PROP_POS_FRAMES), then decodes sequentially through
    the range - one seek per call, not per frame."""
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


def _load_reference_intervals(out_dir: Path) -> list:
    path = out_dir / "reference_frame_results.json"
    if not path.exists():
        return None
    frame_results = json.loads(path.read_text())
    return build_reference_intervals([(r[0], r[1], r[2]) for r in frame_results])


def _persist_reference_frame_results(out_dir: Path, frame_results: list) -> None:
    path = out_dir / "reference_frame_results.json"
    path.write_text(json.dumps([[ts, present, conf, n] for ts, present, conf, n in frame_results]))


def _append_run(out_dir: Path, rec: RunRecord) -> None:
    path = out_dir / "runs.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(asdict(rec)) + "\n")


def _load_all_runs(out_dir: Path) -> list:
    path = out_dir / "runs.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _partial_path(out_dir: Path, condition: str, repeat: int) -> Path:
    return out_dir / f"_partial_{condition}_{repeat}.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, default=Path("data/input/sample.mp4"))
    parser.add_argument("--recording-id", default="R1")
    parser.add_argument("--out-dir", type=Path, default=Path("research_visual_gating/results/R1_checkpointed"))
    parser.add_argument("--condition", required=True,
                         choices=["A", "B", "C", "D", "E", "F_B", "F_C", "F_D", "F_E"])
    parser.add_argument("--repeat", type=int, required=True, help="-1 = warm-up, 0/1/2 = timed")
    parser.add_argument("--part", type=int, default=None,
                         help="1-indexed part number (with --n-parts) to split this run's "
                              "decode pass into N sequential, equal-width native-frame ranges, "
                              "to stay under the shell's per-call time limit. Omit (with "
                              "--n-parts also omitted) for conditions light enough for one call.")
    parser.add_argument("--n-parts", type=int, default=None,
                         help="Total number of parts this run is split into. Required if --part is given.")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    video_duration, native_fps = get_video_duration_and_fps(args.video)
    grid = build_frame_grid(video_duration, fps=SAMPLE_FPS)
    total_native_frames = int(video_duration * native_fps) + 1

    raw_intervals, vad_wall_time_s = _load_or_compute_vad(args.out_dir, args.video)
    padded_by_label = {
        label: dilate_and_merge(raw_intervals, pad_ms, video_duration)
        for label, pad_ms in PADDING_CONDITIONS
    }
    vad_speech_duration_s = round(sum(iv.end - iv.start for iv in raw_intervals), 3)
    model_config_id = (f"yunet=2023mar,conf>={FACE_CONFIDENCE_THRESHOLD};"
                        f"vad=silero,thr={VAD_THRESHOLD},minspeech={VAD_MIN_SPEECH_DURATION_MS}ms,"
                        f"minsil={VAD_MIN_SILENCE_DURATION_MS}ms")
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
    else:  # F_B .. F_E
        condition_type = "matched_uniform"
        base_label = condition.split("_")[1]
        matched_to = base_label
        all_runs = _load_all_runs(args.out_dir)
        counts = [r["processed_frames"] for r in all_runs if r["condition"] == base_label]
        if len(counts) < 3:
            print(f"ERROR: need 3 timed runs of condition {base_label} recorded before running {condition} "
                  f"(found {len(counts)}). Run {base_label} repeats 0,1,2 first.", file=sys.stderr)
            sys.exit(2)
        target_count = round(sum(counts) / len(counts))
        target_indices = set(select_frames_matched_uniform(grid, target_count))
        eligible_duration = None

    # --- Decode + detect, possibly split into N equal-width native-frame ranges ---
    if args.part is None:
        with measure(sample_rss=True) as m:
            frame_results = sequential_process_range(args.video, grid, target_indices, native_fps, 0, total_native_frames)
        wall_time_s, cpu_seconds, peak_rss_mb, mean_rss_mb = m.wall_time_s, m.cpu_seconds, m.peak_rss_mb, m.mean_rss_mb
    else:
        if not args.n_parts or not (1 <= args.part <= args.n_parts):
            print("ERROR: --part requires --n-parts and 1 <= part <= n_parts.", file=sys.stderr)
            sys.exit(2)
        n_parts = args.n_parts
        native_start = (args.part - 1) * total_native_frames // n_parts
        native_end = args.part * total_native_frames // n_parts if args.part < n_parts else total_native_frames

        with measure(sample_rss=True) as m:
            part_results = sequential_process_range(args.video, grid, target_indices, native_fps, native_start, native_end)

        partial_path = _partial_path(args.out_dir, condition, args.repeat)
        if args.part == 1:
            accumulated = {
                "frame_results": [[ts, p, c, n] for ts, p, c, n in part_results],
                "wall_time_s": m.wall_time_s,
                "cpu_seconds": m.cpu_seconds,
                "peak_rss_mb": m.peak_rss_mb,
                "mean_rss_mb_list": [m.mean_rss_mb] if m.mean_rss_mb is not None else [],
            }
        else:
            if not partial_path.exists():
                print(f"ERROR: part={args.part} requested but the accumulated state from earlier parts "
                      f"({partial_path}) is missing. Run parts in order starting at --part 1.", file=sys.stderr)
                sys.exit(2)
            prev = json.loads(partial_path.read_text())
            accumulated = {
                "frame_results": prev["frame_results"] + [[ts, p, c, n] for ts, p, c, n in part_results],
                "wall_time_s": round(prev["wall_time_s"] + m.wall_time_s, 4),
                "cpu_seconds": round(prev["cpu_seconds"] + m.cpu_seconds, 4),
                "peak_rss_mb": round(max(prev["peak_rss_mb"], m.peak_rss_mb), 2),
                "mean_rss_mb_list": prev["mean_rss_mb_list"] + ([m.mean_rss_mb] if m.mean_rss_mb is not None else []),
            }

        if args.part < n_parts:
            partial_path.write_text(json.dumps(accumulated))
            print(f"[CHECKPOINT] {condition} repeat={args.repeat} part={args.part}/{n_parts}: "
                  f"native[{native_start}:{native_end}) -> {len(part_results)} processed frames, "
                  f"wall={m.wall_time_s}s cpu={m.cpu_seconds}s. Run --part {args.part+1} next.")
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
            _persist_reference_frame_results(args.out_dir, frame_results)
            print(f"[CHECKPOINT] {condition} repeat=-1 (warm-up): persisted reference_frame_results.json "
                  f"({len(frame_results)} frames). wall={wall_time_s}s (untimed/not recorded).")
        else:
            print(f"[CHECKPOINT] {condition} repeat=-1 (warm-up, not recorded). wall={wall_time_s}s")
        return

    processed_ts = {ts for ts, _p, _c, _n in frame_results}
    n_processed = len(processed_ts)
    n_skipped = len(grid) - n_processed
    skip_pct = round(100.0 * n_skipped / len(grid), 2)

    reference_intervals = _load_reference_intervals(args.out_dir)
    if reference_intervals is None:
        print("ERROR: reference_frame_results.json not found - run condition A repeat=-1 first.", file=sys.stderr)
        sys.exit(2)

    exist = interval_existence_recall(processed_ts, reference_intervals)
    cov = temporal_coverage_recall(processed_ts, reference_intervals, grid)

    rec = RunRecord(
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
        wall_time_s=wall_time_s,
        cpu_seconds=cpu_seconds,
        peak_rss_mb=peak_rss_mb,
        mean_rss_mb=mean_rss_mb,
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
        notes=(f"target_count matched to mean processed_frames of condition {matched_to}"
               if condition_type == "matched_uniform" else ""),
    )
    _append_run(args.out_dir, rec)
    print(f"[CHECKPOINT] {condition} repeat={args.repeat} DONE: processed={n_processed} skip%={skip_pct} "
          f"wall={wall_time_s}s cpu={cpu_seconds}s peakRSS={peak_rss_mb}MB "
          f"exist_recall={exist['recall']} cov_recall={cov['recall']}")


if __name__ == "__main__":
    main()
