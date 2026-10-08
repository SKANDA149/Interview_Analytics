"""Speaker Embedding + Clustering + RTTM."""
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import numpy as np
import gc

@dataclass
class DiarizationSegment:
    start: float
    end: float
    speaker: str

def run_diarization(
    audio_path: Path,
    speech_segments: list,
    model_path: Path,
    n_speakers: int = 2
) -> list:
    """
    Extract speaker embeddings and cluster into speakers.
    
    Args:
        audio_path: Path to full 16kHz mono WAV.
        speech_segments: Output from run_vad() — list of {"start", "end"} dicts.
        model_path: Path to WeSpeaker ResNet34 ONNX model file.
        n_speakers: Number of speakers to cluster (default 2).
    
    Returns:
        List of DiarizationSegment objects with speaker labels ("SPEAKER_00", "SPEAKER_01", etc).
        Empty list on error.
    """
    if not model_path.exists():
        print(f"[DIARIZATION] Error: Model path {model_path} does not exist.")
        return []
        
    if not speech_segments:
        print("[DIARIZATION] No speech segments provided.")
        return []
        
    try:
        import onnxruntime as ort
        import soundfile as sf
        import torch
        import torchaudio.compliance.kaldi as kaldi
        from sklearn.cluster import AgglomerativeClustering
    except ImportError as e:
        print(f"[DIARIZATION] Missing dependency: {e}")
        return []

    try:
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2
        opts.inter_op_num_threads = 1
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session = ort.InferenceSession(str(model_path), sess_options=opts, providers=['CPUExecutionProvider'])
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        
        audio_data, sr = sf.read(str(audio_path), dtype='float32')
    except Exception as e:
        print(f"[DIARIZATION] Error loading model or audio: {e}")
        return []
        
    all_embeddings = []
    valid_segments = []
    
    total = len(speech_segments)
    for i, seg in enumerate(speech_segments):
        start = seg['start']
        end = seg['end']
        
        if end - start < 0.3:
            print(f"[DIARIZATION] Skipping segment {start:.2f}-{end:.2f} (too short)")
            continue
            
        segment_audio = audio_data[int(start * sr) : int(end * sr)]
        wav_tensor = torch.from_numpy(segment_audio).float().unsqueeze(0)
        
        fbank = kaldi.fbank(
            wav_tensor * (1 << 15),
            num_mel_bins=80,
            frame_length=25.0,
            frame_shift=10.0,
            dither=0.0,
            sample_frequency=float(sr),
            energy_floor=0.0,
            window_type='povey'
        )
        fbank = fbank - torch.mean(fbank, dim=0, keepdim=True)
        fbank_np = fbank.unsqueeze(0).numpy().astype(np.float32)
        
        outputs = session.run([output_name], {input_name: fbank_np})
        raw_emb = outputs[0][0]
        norm = np.linalg.norm(raw_emb)
        embedding = raw_emb / norm if norm > 0 else raw_emb
        
        all_embeddings.append(embedding)
        valid_segments.append(seg)
        
        if (i + 1) % 20 == 0 or (i + 1) == total:
            print(f"[DIARIZATION] Extracted embeddings for {i+1}/{total} segments")
            
    N = len(all_embeddings)
    if N == 0:
        print("[DIARIZATION] No valid embeddings extracted.")
        del session
        gc.collect()
        return []
        
    embeddings_matrix = np.stack(all_embeddings)
    
    if N <= 1:
        labels = np.zeros(N, dtype=int)
    else:
        clustering = AgglomerativeClustering(
            n_clusters=min(n_speakers, N),
            metric='cosine',
            linkage='average'
        )
        labels = clustering.fit_predict(embeddings_matrix)
        
    results = []
    for seg, label in zip(valid_segments, labels):
        results.append(DiarizationSegment(
            start=seg['start'],
            end=seg['end'],
            speaker=f'SPEAKER_{label:02d}'
        ))
        
    del session
    gc.collect()
    
    print(f"[DIARIZATION] Clustered {N} segments into {min(n_speakers, N)} speakers")
    return results

def generate_rttm(segments: list, file_id: str = "interview", output_path: Path = None) -> str:
    """
    Generate RTTM formatted text from DiarizationSegment list.
    Optionally writes to output_path.
    Returns the RTTM string.
    """
    lines = []
    for s in segments:
        duration = s.end - s.start
        lines.append(f"SPEAKER {file_id} 1 {s.start:.3f} {duration:.3f} <NA> <NA> {s.speaker} <NA> <NA>")
        
    rttm_text = "\n".join(lines)
    
    if output_path:
        output_path.write_text(rttm_text, encoding="utf-8")
        
    return rttm_text

def save_segments(segments: list, output_path: Path) -> None:
    """Save DiarizationSegment list to JSON."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump([asdict(s) for s in segments], f, indent=2)

def load_segments(input_path: Path) -> list:
    """Load DiarizationSegment list from JSON."""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [DiarizationSegment(**item) for item in data]
