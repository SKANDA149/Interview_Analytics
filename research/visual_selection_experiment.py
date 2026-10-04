"""
research/visual_selection_experiment.py

Speech-guided selective visual analysis experiment.

Research question (locked, do not silently redefine):
    Can speech-derived candidate-speaking intervals be used to selectively
    activate video analysis, reducing computational cost on CPU/edge
    hardware while retaining the visual-analysis information relevant to
    candidate behavior?

Independent variable: WHICH video frames are sent to visual analysis.
    Condition A (full):      every 5-FPS timestamp across the whole video.
    Condition B (selective):  every 5-FPS timestamp inside candidate-speaking
                              intervals only.
Dependent variables: frame counts, wall-clock time, and (separately)
    agreement between B and the "A restricted to the same candidate-speech
    timestamps" subset -- NOT agreement between B and all of A.

This module changes NOTHING in interview_pipeline/src/visual_presence.py.
It reuses every function from Step 2 onward (detect_faces, detect_poses,
select_candidate_instance, classify_sample, aggregate) unchanged, and adds
only the one thing that module doesn't have: a full-video timestamp
generator, so Condition A can exist at all.

Interval source (per the approved design decision): the retention
comparison (Condition B vs. Condition A-restricted-to-candidate-speech)
should ultimately run on ORACLE candidate-speaking intervals, not raw
diarizer output, so diarization quality never becomes the hidden variable
in the retention result. This script accepts either -- pass
--intervals oracle.json to use a hand-verified interval file, or omit it
to fall back to data/diarization/segments.json (real diarizer output) for
initial plumbing/timing verification only. The run record's
"interval_source" field always states which was used, and any run using
real diarizer output is not sufficient on its own for a retention claim.
"""
import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from interview_pipeline.src.diarization import DiarizationSegment
from interview_pipeline.src.visual_presence import (
    SAMPLE_FPS,
    CANDIDATE_LABEL,
    SampleTimestamp,
    get_candidate_segments,
    generate_sample_timestamps,
    sample_frames,
    detect_faces,
    detect_poses,
    select_candidate_instance,
    classify_sample,
    aggregate,
    SampleResult,
    _aggregate_metrics_to_dict,
)

import cv2


def generate_full_video_timestamps(duration_sec: float, fps: int = SAMPLE_FPS) -> list:
    """Same 1/fps index-multiplication rule as visual_presence.generate_
    sample_timestamps(), applied to [0, duration_sec] as a single segment
    instead of per-candidate-segment."""
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")
    if duration_sec <= 0:
        raise ValueError(f"duration_sec must be positive, got {duration_sec}")

    step = 1.0 / fps
    n_steps = int(duration_sec * fps + 1e-9)
    timestamps = []
    for i in range(n_steps + 1):
        t = round(i * step, 3)
        if t > duration_sec + 1e-9:
            break
        timestamps.append(SampleTimestamp(timestamp=t, segment_start=0.0, segment_end=duration_sec))
    return timestamps


def get_video_duration_sec(video_path: Path) -> float:
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if fps <= 0 or frame_count <= 0:
            raise RuntimeError(f"Could not read fps/frame_count from {video_path}")
        return frame_count / fps
    finally:
        cap.release()


def load_oracle_intervals(path: Path) -> list:
    """Oracle candidate-speaking intervals: a JSON list of
    {"start": float, "end": float} objects, hand-verified, independent of
    any diarizer."""
    raw = json.loads(Path(path).read_text())
    return [
        DiarizationSegment(start=float(r["start"]), end=float(r["end"]), speaker=CANDIDATE_LABEL)
        for r in raw
    ]


def load_diarizer_candidate_segments(path: Path) -> list:
    raw = json.loads(Path(path).read_text())
    all_segments = [DiarizationSegment(start=r["start"], end=r["end"], speaker=r["speaker"]) for r in raw]
    return get_candidate_segments(all_segments)


def run_visual_analysis_on_timestamps(video_path: Path, sample_timestamps: list) -> tuple:
    """Identical model/threshold/detector code path as
    run_visual_presence_analysis() -- differs only in accepting a
    pre-built timestamp list instead of building one internally."""
    frame_samples = sample_frames(video_path, sample_timestamps)

    sample_results = []
    failed_reads = 0
    for frame_sample in frame_samples:
        if not frame_sample.success:
            failed_reads += 1
            continue
        faces = detect_faces(frame_sample.frame)
        poses = detect_poses(frame_sample.frame)
        instance = select_candidate_instance(faces, poses)
        classification = classify_sample(instance)
        sample_results.append(
            SampleResult(timestamp=frame_sample.timestamp, num_faces=len(faces), visibility=classification)
        )

    return sample_results, failed_reads, len(sample_results)


@dataclass
class RunRecord:
    recording_id: str
    condition: str
    interval_source: str
    video_duration_sec: float
    candidate_speech_duration_sec: float
    selected_fraction: float
    fps: int
    frames_available: int
    frames_processed: int
    frames_skipped: int
    frames_skipped_pct: float
    visual_runtime_sec: float
    model_load_included: bool
    peak_ram_mb: float
    face_detection_count: int
    face_detection_rate: float
    fully_visible_pct: float
    presence_pct: float
    uncertain_pct: float
    absence_run_count: int
    longest_continuous_absence_sec: float
    fps_config: int
    yunet_confidence_threshold: float
    shoulder_visibility_threshold: float
    repeat_index: int
    success: bool
    notes: str


def _try_peak_ram_mb() -> float:
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except ImportError:
        try:
            import psutil
            return psutil.Process().memory_info().peak_wset / (1024 * 1024)
        except Exception:
            return None
    except Exception:
        return None


def run_condition(
    video_path: Path,
    condition: str,
    recording_id: str,
    video_duration_sec: float,
    candidate_segments: list,
    interval_source: str,
    repeat_index: int = 0,
) -> tuple:
    candidate_speech_duration = sum(s.end - s.start for s in candidate_segments)

    if condition == "full":
        sample_timestamps = generate_full_video_timestamps(video_duration_sec, fps=SAMPLE_FPS)
    elif condition == "selective":
        sample_timestamps = generate_sample_timestamps(candidate_segments, fps=SAMPLE_FPS)
    else:
        raise ValueError(f"Unknown condition: {condition}")

    frames_available = len(sample_timestamps)

    t0 = time.perf_counter()
    sample_results, failed_reads, frames_processed = run_visual_analysis_on_timestamps(
        video_path, sample_timestamps
    )
    elapsed = time.perf_counter() - t0

    metrics = aggregate(sample_results)
    agg_dict = _aggregate_metrics_to_dict(metrics)

    from interview_pipeline.src.visual_presence import (
        FACE_CONFIDENCE_THRESHOLD, SHOULDER_VISIBILITY_THRESHOLD,
    )
    n_selected = sum(
        1 for r in sample_results
        if r.visibility.classification in ("partially_visible", "fully_visible")
    )

    record = RunRecord(
        recording_id=recording_id,
        condition=condition,
        interval_source=interval_source if condition == "selective" else "n/a",
        video_duration_sec=round(video_duration_sec, 3),
        candidate_speech_duration_sec=round(candidate_speech_duration, 3),
        selected_fraction=round(candidate_speech_duration / video_duration_sec, 4),
        fps=SAMPLE_FPS,
        frames_available=frames_available,
        frames_processed=frames_processed,
        frames_skipped=failed_reads,
        frames_skipped_pct=round(100.0 * failed_reads / frames_available, 2) if frames_available else 0.0,
        visual_runtime_sec=round(elapsed, 4),
        model_load_included=(repeat_index == 0),
        peak_ram_mb=_try_peak_ram_mb(),
        face_detection_count=n_selected,
        face_detection_rate=round(n_selected / frames_processed, 4) if frames_processed else 0.0,
        fully_visible_pct=agg_dict["full_visibility_rate"],
        presence_pct=agg_dict["presence_rate"],
        uncertain_pct=round(agg_dict["uncertain_samples"] / agg_dict["total_samples"], 4) if agg_dict["total_samples"] else None,
        absence_run_count=len(agg_dict["absence_runs"]),
        longest_continuous_absence_sec=agg_dict["longest_continuous_absence_seconds"],
        fps_config=SAMPLE_FPS,
        yunet_confidence_threshold=FACE_CONFIDENCE_THRESHOLD,
        shoulder_visibility_threshold=SHOULDER_VISIBILITY_THRESHOLD,
        repeat_index=repeat_index,
        success=True,
        notes="",
    )
    return record, sample_results, sample_timestamps


def compare_retention(full_results: list, selective_results: list) -> dict:
    """Compares Condition B against Condition A RESTRICTED TO THE SAME
    candidate-speech timestamps -- never against all of Condition A."""
    full_by_ts = {round(r.timestamp, 3): r for r in full_results}
    selective_by_ts = {round(r.timestamp, 3): r for r in selective_results}

    shared_ts = sorted(set(full_by_ts) & set(selective_by_ts))
    only_in_selective = sorted(set(selective_by_ts) - set(full_by_ts))

    agree = 0
    disagree = []
    for ts in shared_ts:
        a = full_by_ts[ts].visibility.classification
        b = selective_by_ts[ts].visibility.classification
        if a == b:
            agree += 1
        else:
            disagree.append({"timestamp": ts, "full_classification": a, "selective_classification": b})

    return {
        "n_shared_timestamps": len(shared_ts),
        "n_selective_only_timestamps": len(only_in_selective),
        "selective_only_timestamps_sample": only_in_selective[:10],
        "agreement_count": agree,
        "agreement_pct": round(100.0 * agree / len(shared_ts), 2) if shared_ts else None,
        "disagreement_count": len(disagree),
        "disagreements": disagree[:50],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--recording-id", required=True)
    parser.add_argument("--intervals", type=Path, default=None,
                         help="Oracle intervals JSON ([{start,end},...]). "
                              "If omitted, falls back to --diarization-segments "
                              "(real diarizer output) for plumbing/timing checks only.")
    parser.add_argument("--diarization-segments", type=Path,
                         default=Path("data/diarization/segments.json"))
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--out", type=Path, default=Path("research/results/visual_selection_pilot.json"))
    args = parser.parse_args()

    video_duration = get_video_duration_sec(args.video)

    if args.intervals is not None:
        candidate_segments = load_oracle_intervals(args.intervals)
        interval_source = "oracle"
    else:
        candidate_segments = load_diarizer_candidate_segments(args.diarization_segments)
        interval_source = "real_diarizer"
        print("[WARN] No --intervals given: using real diarizer output. "
              "This is sufficient for plumbing/timing verification only -- "
              "NOT for the information-retention claim (Phase 3), which "
              "requires oracle intervals per the approved design decision.")

    all_records = []
    full_results_by_repeat = []
    selective_results_by_repeat = []

    for rep in range(args.repeats):
        rec_a, results_a, _ = run_condition(
            args.video, "full", args.recording_id, video_duration,
            candidate_segments, interval_source, repeat_index=rep,
        )
        rec_b, results_b, _ = run_condition(
            args.video, "selective", args.recording_id, video_duration,
            candidate_segments, interval_source, repeat_index=rep,
        )
        all_records.append(asdict(rec_a))
        all_records.append(asdict(rec_b))
        full_results_by_repeat.append(results_a)
        selective_results_by_repeat.append(results_b)
        print(f"[repeat {rep}] full: {rec_a.frames_processed} frames, "
              f"{rec_a.visual_runtime_sec}s | selective: {rec_b.frames_processed} frames, "
              f"{rec_b.visual_runtime_sec}s")

    retention = compare_retention(full_results_by_repeat[0], selective_results_by_repeat[0])

    output = {
        "recording_id": args.recording_id,
        "video_path": str(args.video),
        "interval_source": interval_source,
        "runs": all_records,
        "retention_comparison_repeat_0": retention,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        ts = time.strftime("%Y%m%d_%H%M%S")
        args.out = args.out.with_name(f"{args.out.stem}_{ts}{args.out.suffix}")
    args.out.write_text(json.dumps(output, indent=2))
    print(f"\nWritten to {args.out}")
    print(f"Selected fraction: {all_records[0]['selected_fraction']:.1%}")
    print(f"Retention agreement on shared timestamps: {retention['agreement_pct']}%"
          f" ({retention['n_shared_timestamps']} shared timestamps)")


if __name__ == "__main__":
    main()
