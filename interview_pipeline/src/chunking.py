from pathlib import Path
import subprocess
import time


def split_video_into_chunks(input_path: Path, output_dir: Path, chunk_duration: int = 10):
    """
    Splits a video into fixed-duration chunks using FFmpeg.

    Args:
        input_path (Path): Path to input video file
        output_dir (Path): Directory where chunks will be saved
        chunk_duration (int): Duration of each chunk in seconds
    """

    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")

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

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print("[ERROR] FFmpeg failed")
        raise e

    end_time = time.time()

    print(f"[INFO] Chunking completed in {end_time - start_time:.2f} seconds")

    chunks = list(output_dir.glob("chunk_*.mp4"))
    print(f"[INFO] Generated {len(chunks)} chunks")

    return chunks