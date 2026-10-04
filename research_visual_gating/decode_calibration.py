"""
research_visual_gating/decode_calibration.py

Standalone calibration (run once, before the timed pilot) comparing:
  (a) sequential grab/advance (cap.read() every frame from the start,
      discarding frames that aren't on the 5 FPS grid)
  (b) seek-per-timestamp (cap.set(CAP_PROP_POS_MSEC, ts*1000) + cap.read(),
      one shared VideoCapture reused across calls - this is what
      interview_pipeline.src.visual_presence.sample_frames already does)
for retrieving the SAME set of target grid timestamps, on the actual pilot
video/codec. Also times YuNet-only face detection in isolation (decode
excluded), so the pilot's time budget can be estimated honestly instead of
assumed.

This does not change how the real pilot decodes frames - it only decides,
with evidence, which of (a)/(b) `pilot_runner.py` should use, and reports
per-frame YuNet cost so the full 36-run time estimate is grounded in a real
measurement rather than a guess.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from interview_pipeline.src.visual_presence import detect_faces, YUNET_MODEL_PATH


def calibrate_decode(video_path: Path, calib_window_sec: float = 120.0, fps: int = 5) -> dict:
    video_path = Path(video_path)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {video_path}")
    native_fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    step = 1.0 / fps
    n_targets = int(calib_window_sec * fps)
    target_timestamps = [round(i * step, 3) for i in range(n_targets)]

    # --- (b) seek-per-timestamp ---
    cap = cv2.VideoCapture(str(video_path))
    t0 = time.perf_counter()
    seek_frames = []
    for ts in target_timestamps:
        cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000.0)
        ok, frame = cap.read()
        seek_frames.append(frame if ok else None)
    seek_elapsed = time.perf_counter() - t0
    cap.release()

    # --- (a) sequential grab/advance ---
    # Walk every native frame from t=0 to calib_window_sec, cap.read()-ing
    # each one, and keeping only the ones nearest each target timestamp
    # (nearest-native-frame match, since native_fps != 5 in general).
    cap = cv2.VideoCapture(str(video_path))
    t0 = time.perf_counter()
    seq_frames_by_target = {}
    target_idx = 0
    native_frame_i = 0
    max_native_frames = int(calib_window_sec * native_fps) + int(native_fps)
    while target_idx < len(target_timestamps) and native_frame_i < max_native_frames:
        ok, frame = cap.read()
        if not ok:
            break
        cur_t = native_frame_i / native_fps
        # advance target pointer to the timestamp this native frame now covers
        while target_idx < len(target_timestamps) and cur_t >= target_timestamps[target_idx] - (0.5 / native_fps):
            seq_frames_by_target[target_timestamps[target_idx]] = frame
            target_idx += 1
        native_frame_i += 1
    seq_elapsed = time.perf_counter() - t0
    cap.release()

    n_seq_native_frames_read = native_frame_i

    # --- YuNet-only per-frame cost (decode excluded - reuse seek_frames already in memory) ---
    valid_frames = [f for f in seek_frames if f is not None][:min(100, len(seek_frames))]
    t0 = time.perf_counter()
    for f in valid_frames:
        detect_faces(f, model_path=YUNET_MODEL_PATH)
    yunet_elapsed = time.perf_counter() - t0
    yunet_per_frame_s = yunet_elapsed / len(valid_frames) if valid_frames else None

    return {
        "video_path": str(video_path),
        "native_fps": native_fps,
        "calib_window_sec": calib_window_sec,
        "n_target_frames": len(target_timestamps),
        "seek_method": {
            "elapsed_s": round(seek_elapsed, 4),
            "per_frame_s": round(seek_elapsed / len(target_timestamps), 5),
            "n_reads_failed": sum(1 for f in seek_frames if f is None),
        },
        "sequential_method": {
            "elapsed_s": round(seq_elapsed, 4),
            "per_frame_s": round(seq_elapsed / len(target_timestamps), 5),
            "n_native_frames_read": n_seq_native_frames_read,
            "n_targets_matched": len(seq_frames_by_target),
        },
        "yunet_only": {
            "elapsed_s_for_n_frames": round(yunet_elapsed, 4),
            "n_frames_timed": len(valid_frames),
            "per_frame_s": round(yunet_per_frame_s, 5) if yunet_per_frame_s else None,
        },
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, default=Path("data/input/sample.mp4"))
    parser.add_argument("--calib-window-sec", type=float, default=120.0)
    args = parser.parse_args()

    result = calibrate_decode(args.video, args.calib_window_sec)
    print(json.dumps(result, indent=2))
