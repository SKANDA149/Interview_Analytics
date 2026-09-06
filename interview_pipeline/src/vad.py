"""Silero Voice Activity Detection for speech segment extraction."""
import torch
from pathlib import Path

torch.set_num_threads(1)

def run_vad(audio_path: Path, sampling_rate: int = 16000) -> list:
    """
    Detect speech segments in an audio file using Silero VAD.
    
    Args:
        audio_path: Path to 16kHz mono WAV file.
        sampling_rate: Audio sample rate (must be 16000).
    
    Returns:
        List of dicts [{"start": float_seconds, "end": float_seconds}, ...]
        Empty list on error.
    """
    try:
        from silero_vad import load_silero_vad, get_speech_timestamps
        import soundfile as sf
    except ImportError:
        print("[VAD] silero-vad or soundfile not installed. Cannot run VAD.")
        return []
        
    try:
        model = load_silero_vad(onnx=True)
        
        # Bypass torchaudio/torchcodec completely
        wav_data, _ = sf.read(str(audio_path), dtype='float32')
        wav = torch.from_numpy(wav_data)
        
        timestamps = get_speech_timestamps(
            wav,
            model,
            sampling_rate=sampling_rate,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=100,
            speech_pad_ms=30,
            return_seconds=True
        )
        
        del model
        
        num_segments = len(timestamps)
        total_duration = sum(t['end'] - t['start'] for t in timestamps)
        
        print(f"[VAD] Detected {num_segments} speech segments in {audio_path.name}")
        print(f"[VAD] Total speech duration: {total_duration:.1f}s")
        
        return timestamps
        
    except Exception as e:
        print(f"[VAD] Error: {e}")
        return []
