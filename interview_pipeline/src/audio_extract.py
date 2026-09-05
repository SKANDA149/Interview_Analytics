from pathlib import Path
import subprocess

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
