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

def cluster_embeddings(
    embeddings_matrix: np.ndarray,
    valid_segments: list,
    n_speakers: int = 2,
    linkage: str = "complete"
) -> list:
    """
    Cluster speaker embeddings into speaker labels.
    
    Args:
        embeddings_matrix: (N, D) numpy array of L2-normalized embeddings.
        valid_segments: List of dicts [{"start": float, "end": float}, ...] of length N.
        n_speakers: Target number of speakers to cluster (default 2).
        linkage: Agglomerative clustering linkage ('complete' recommended to prevent chaining collapse).
        
    Returns:
        List of DiarizationSegment objects with speaker labels ("SPEAKER_00", "SPEAKER_01", etc.).
    """
    N = len(embeddings_matrix)
    if N == 0 or len(valid_segments) == 0:
        return []
        
    # Guard: check for non-finite values in matrix
    if not np.isfinite(embeddings_matrix).all():
        print("[DIARIZATION] Warning: Non-finite values detected in embeddings matrix.")
        valid_mask = np.isfinite(embeddings_matrix).all(axis=1)
        if not np.any(valid_mask):
            return []
        embeddings_matrix = embeddings_matrix[valid_mask]
        valid_segments = [seg for i, seg in enumerate(valid_segments) if valid_mask[i]]
        N = len(embeddings_matrix)
        
    def _get_seg_bounds(s):
        if isinstance(s, dict):
            return float(s['start']), float(s['end'])
        return float(s.start), float(s.end)

    if N <= 1 or n_speakers <= 1:
        labels = np.zeros(N, dtype=int)
    else:
        from sklearn.cluster import AgglomerativeClustering
        clustering = AgglomerativeClustering(
            n_clusters=min(n_speakers, N),
            metric='cosine',
            linkage=linkage
        )
        labels = clustering.fit_predict(embeddings_matrix)

        # Cluster separation diagnostics
        unique_labels = np.unique(labels)
        if len(unique_labels) >= 2:
            durations = [_get_seg_bounds(seg)[1] - _get_seg_bounds(seg)[0] for seg in valid_segments]
            counts = [int(np.sum(labels == lbl)) for lbl in unique_labels]
            total_durs = [sum(durations[i] for i in range(N) if labels[i] == lbl) for lbl in unique_labels]
            print(f"[DIARIZATION] Clustered {N} segments with linkage='{linkage}':")
            for lbl, c, d in zip(unique_labels, counts, total_durs):
                print(f"  -> SPEAKER_{lbl:02d}: {c} segments ({d:.1f}s)")
            
            # Check for degenerate/outlier cluster
            if min(counts) <= 1 and max(counts) > 10:
                print(f"[DIARIZATION] [WARNING] Degenerate cluster detected ({min(counts)} vs {max(counts)} segments).")

    results = []
    for seg, label in zip(valid_segments, labels):
        s_start, s_end = _get_seg_bounds(seg)
        results.append(DiarizationSegment(
            start=s_start,
            end=s_end,
            speaker=f'SPEAKER_{label:02d}'
        ))
    return results


def run_diarization(
    audio_path: Path,
    speech_segments: list,
    model_path: Path,
    n_speakers: int = 2,
    linkage: str = "complete"
) -> list:
    """
    Extract speaker embeddings and cluster into speakers.
    
    Args:
        audio_path: Path to full 16kHz mono WAV.
        speech_segments: Output from run_vad() — list of {"start", "end"} dicts.
        model_path: Path to WeSpeaker ResNet34 ONNX model file.
        n_speakers: Number of speakers to cluster (default 2).
        linkage: Clustering linkage ('complete' default, prevents outlier chaining).
    
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

        # Guard against non-finite or invalid embeddings
        if not np.isfinite(raw_emb).all():
            print(f"[DIARIZATION] Skipping segment {start:.2f}-{end:.2f} (non-finite embedding values)")
            continue

        norm = np.linalg.norm(raw_emb)
        if norm <= 0 or not np.isfinite(norm):
            print(f"[DIARIZATION] Skipping segment {start:.2f}-{end:.2f} (zero or invalid embedding norm)")
            continue

        embedding = raw_emb / norm
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
    results = cluster_embeddings(
        embeddings_matrix,
        valid_segments,
        n_speakers=n_speakers,
        linkage=linkage
    )
        
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
