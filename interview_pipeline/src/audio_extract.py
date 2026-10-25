from pathlib import Path
import subprocess
import wave

def extract_audio(chunk_path: Path, output_dir: Path) -> Path:
    """
    Extracts mono 16kHz WAV audio from a video chunk.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{chunk_path.stem}.wav"
    
    command = [
        "ffmpeg", "-y", "-i", str(chunk_path),
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        str(out_path)
    ]
    
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path


def get_media_duration(file_path: Path, default_sec: float = 10.0) -> float:
    """
    Determines the actual media duration in seconds.
    Tries standard library `wave` for fast, sample-accurate WAV duration.
    Falls back to `ffprobe` for video/media files, and finally to `default_sec`.
    """
    if not file_path:
        return default_sec

    path_obj = Path(file_path)
    if not path_obj.exists():
        return default_sec

    # 1. Fast sample-accurate WAV header parsing
    if path_obj.suffix.lower() == ".wav":
        try:
            with wave.open(str(path_obj), "rb") as wf:
                framerate = wf.getframerate()
                nframes = wf.getnframes()
                if framerate > 0 and nframes >= 0:
                    dur = nframes / float(framerate)
                    if dur > 0:
                        return dur
        except Exception:
            pass

    # 2. ffprobe fallback for video chunks or non-standard audio
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path_obj)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        dur = float(res.stdout.strip())
        if dur > 0:
            return dur
    except Exception:
        pass

    return default_sec

