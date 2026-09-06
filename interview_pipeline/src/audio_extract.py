from pathlib import Path
import subprocess

def extract_audio(chunk_path: Path, output_dir: Path) -> Path:
    """
    Extracts mono 16kHz WAV audio from a video file or chunk.
    Uses robust pcm_s16le audio codec settings compatible with Faster-Whisper.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{chunk_path.stem}.wav"
    
    command = [
        "ffmpeg", "-y",
        "-i", str(chunk_path.resolve()),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(out_path.resolve())
    ]
    
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"  -> [AUDIO] Successfully extracted 16kHz Mono WAV: {out_path.name}")
    except subprocess.CalledProcessError as e:
        print(f"  -> [WARNING] Audio extraction warning for {chunk_path.name}: {e.stderr[:200] if e.stderr else e}")
        # Create a zero-silent WAV header if audio extraction fails (e.g. video with no audio stream)
        _create_silent_wav(out_path)

    return out_path

def _create_silent_wav(out_path: Path, duration_sec: float = 10.0):
    """Fallback utility generating a 16kHz Mono silent WAV file."""
    import wave
    import struct
    try:
        sample_rate = 16000
        num_samples = int(sample_rate * duration_sec)
        with wave.open(str(out_path), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack('<' + ('h' * num_samples), *([0] * num_samples)))
    except Exception as ex:
        print(f"  -> [ERROR] Failed to generate silent WAV fallback: {ex}")

def extract_full_audio(video_path: Path, output_dir: Path) -> Path:
    """
    Extract the complete audio track from a video as a single 16kHz mono WAV.
    Used for VAD and diarization processing on the full interview.
    
    Args:
        video_path: Path to the source video file.
        output_dir: Directory to save the output WAV.
    
    Returns:
        Path to the extracted WAV file (output_dir / "full_audio.wav").
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "full_audio.wav"
    
    command = [
        "ffmpeg", "-y",
        "-i", str(video_path.resolve()),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(out_path.resolve())
    ]
    
    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"[AUDIO] Extracted full audio: {out_path.name}")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr[:200] if e.stderr else str(e)
        print(f"[AUDIO] Error extracting full audio: {error_msg}")
        _create_silent_wav(out_path, duration_sec=60.0)

    return out_path
