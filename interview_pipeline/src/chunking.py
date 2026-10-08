from pathlib import Path
import re
import subprocess
import time


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