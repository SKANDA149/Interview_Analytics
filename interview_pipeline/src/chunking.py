from pathlib import Path
import re
import subprocess
import time
import csv
import math

from interview_pipeline.src.audio_extract import get_media_duration


def _chunk_sort_key(path: Path) -> int:
    """Extract the numeric index from a chunk filename for reliable sorting.
    e.g. chunk_042.mp4 → 42.  Falls back to 0 if the name doesn't match."""
    m = re.search(r"chunk_(\d+)", path.stem)
    return int(m.group(1)) if m else 0


def split_video_into_chunks(input_path: Path, output_dir: Path, chunk_duration: int = 10):
    """
    Splits a video into fixed-duration chunks using FFmpeg.

    Args:
        input_path (Path): Path to input video file
        output_dir (Path): Directory where chunks will be saved
        chunk_duration (int): Duration of each chunk in seconds

    Returns:
        List[Path]: chunk file paths sorted in numeric order.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_pattern = output_dir / "chunk_%03d.mp4"

    command = [
        "ffmpeg",
        "-i", str(input_path),
        "-c", "copy",
        "-f", "segment",
        "-segment_time", str(chunk_duration),
        "-segment_list", str(output_dir / "chunk_times.csv"),
        "-segment_list_type", "csv",
        "-reset_timestamps", "1",
        str(output_pattern)
    ]

    print(f"[INFO] Starting chunking: {input_path}")
    start_time = time.time()

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg chunking failed (exit {result.returncode}).\n"
            f"stderr: {result.stderr[-500:] if result.stderr else '(empty)'}"
        )

    elapsed = time.time() - start_time
    print(f"[INFO] Chunking completed in {elapsed:.2f} seconds")

    chunks = sorted(output_dir.glob("chunk_*.mp4"), key=_chunk_sort_key)
    print(f"[INFO] Generated {len(chunks)} chunks")

    return chunks


def get_chunk_time_ranges(chunks: list, chunk_duration: float = 10.0) -> dict:
    """Return original-video time windows, preferring FFmpeg's segment list.

    Legacy cached chunks without a manifest use cumulative measured media
    durations; that fallback is approximate because container/audio padding
    can differ from the original video timestamps.
    """
    if not chunks:
        return {}
    manifest = Path(chunks[0]).parent / "chunk_times.csv"
    try:
        with manifest.open(newline="", encoding="utf-8") as source:
            rows = list(csv.reader(source))
        windows = {}
        previous_end = 0.0
        for row in rows:
            name, start, end = Path(row[0]).name, float(row[1]), float(row[2])
            if not (math.isfinite(start) and math.isfinite(end) and start >= previous_end and end > start):
                raise ValueError("Invalid segment bounds")
            windows[name] = (start, end)
            previous_end = end
        if set(windows) != {Path(chunk).name for chunk in chunks}:
            raise ValueError("Segment list does not match chunk files")
        return windows
    except (OSError, ValueError, IndexError):
        print("[PIPELINE] No valid segment time manifest; using cumulative measured durations for cached chunks.")
        windows = {}
        start = 0.0
        for chunk in chunks:
            duration = get_media_duration(chunk, default_sec=float(chunk_duration))
            windows[Path(chunk).name] = (start, start + duration)
            start += duration
        return windows
