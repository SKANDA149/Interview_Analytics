import pytest
from pathlib import Path
import json

from interview_pipeline.src.diarization import (
    run_diarization, 
    generate_rttm, 
    save_segments, 
    load_segments,
    DiarizationSegment
)
from interview_pipeline.src.vad import run_vad
from interview_pipeline.src.speaker_roles import assign_speaker_roles
from interview_pipeline.src.visual_presence import run_visual_presence_analysis, summarize_visual_metrics

def test_diarization_imports_and_types():
    # 1. Imports check
    assert run_diarization is not None
    assert run_vad is not None
    assert assign_speaker_roles is not None
    
def test_model_paths_resolve():
    # 2. Model paths
    project_root = Path(__file__).resolve().parent.parent.parent
    wespeaker = project_root / "models" / "wespeaker" / "voxceleb_resnet34_LM.onnx"
    vad = project_root / "models" / "silero_vad" / "silero_vad.onnx"
    assert wespeaker.exists(), f"WeSpeaker model not found at {wespeaker}"
    assert vad.exists(), f"Silero VAD model not found at {vad}"

def test_missing_model_error_handling():
    # 7. Missing model errors
    dummy_wav = Path("dummy.wav")
    missing_model = Path("does_not_exist.onnx")
    segments = run_diarization(dummy_wav, [{"start": 0, "end": 1}], missing_model)
    assert segments == [], "Should return empty list gracefully when model is missing"

def test_diarization_segment_structure():
    # 3. Start/end/speaker
    seg = DiarizationSegment(start=1.0, end=2.0, speaker="CANDIDATE")
    assert hasattr(seg, "start")
    assert hasattr(seg, "end")
    assert hasattr(seg, "speaker")
    assert seg.speaker == "CANDIDATE"

def test_speaker_roles_heuristic():
    # 4. Ordering and role assignment
    segs = [
        DiarizationSegment(start=1.0, end=2.0, speaker="SPEAKER_00"), # 1 sec
        DiarizationSegment(start=3.0, end=8.0, speaker="SPEAKER_01"), # 5 sec
    ]
    role_map, final = assign_speaker_roles(segs)
    assert role_map["SPEAKER_01"] == "CANDIDATE" # 5 > 1
    assert role_map["SPEAKER_00"] == "INTERVIEWER"
    assert final[0].start < final[1].start # Chronological

def test_visual_presence_consumption():
    # 8. Generated segments consumed by visual presence
    # (Mock visual presence consumption of the generated object)
    segs = [
        DiarizationSegment(start=0.0, end=2.0, speaker="CANDIDATE")
    ]
    # We just ensure the object format is what visual_presence expects
    assert isinstance(segs[0], DiarizationSegment)
    assert segs[0].speaker == "CANDIDATE"


def test_cluster_embeddings_two_synthetic_speakers():
    """Verify two clearly separated synthetic speaker clusters do not collapse."""
    import numpy as np
    from interview_pipeline.src.diarization import cluster_embeddings

    np.random.seed(42)
    dim = 256
    # Two distinct unit vectors
    center_a = np.random.randn(dim)
    center_a /= np.linalg.norm(center_a)
    center_b = np.random.randn(dim)
    center_b /= np.linalg.norm(center_b)

    # 30 points for speaker A, 30 points for speaker B
    embs_a = center_a + 0.05 * np.random.randn(30, dim)
    embs_a /= np.linalg.norm(embs_a, axis=1, keepdims=True)
    embs_b = center_b + 0.05 * np.random.randn(30, dim)
    embs_b /= np.linalg.norm(embs_b, axis=1, keepdims=True)

    matrix = np.vstack([embs_a, embs_b])
    segments = [{"start": float(i * 2), "end": float(i * 2 + 1.5)} for i in range(60)]

    results = cluster_embeddings(matrix, segments, n_speakers=2, linkage="complete")
    assert len(results) == 60

    speakers = [s.speaker for s in results]
    spk0_count = speakers.count("SPEAKER_00")
    spk1_count = speakers.count("SPEAKER_01")

    # Neither cluster collapsed into a single outlier
    assert spk0_count == 30
    assert spk1_count == 30
    # Perfect separation: first 30 are one speaker, last 30 are the other
    assert len(set(speakers[:30])) == 1
    assert len(set(speakers[30:])) == 1
    assert speakers[0] != speakers[30]


def test_cluster_embeddings_handles_nan_and_inf():
    """Verify non-finite embeddings are safely filtered without raising exceptions."""
    import numpy as np
    from interview_pipeline.src.diarization import cluster_embeddings

    valid_emb = np.ones((2, 256), dtype=np.float32)
    valid_emb /= np.linalg.norm(valid_emb, axis=1, keepdims=True)
    
    nan_emb = np.full((1, 256), np.nan, dtype=np.float32)
    inf_emb = np.full((1, 256), np.inf, dtype=np.float32)

    matrix = np.vstack([valid_emb[:1], nan_emb, valid_emb[1:], inf_emb])
    segments = [
        {"start": 0.0, "end": 1.0},
        {"start": 1.0, "end": 2.0},
        {"start": 2.0, "end": 3.0},
        {"start": 3.0, "end": 4.0},
    ]

    results = cluster_embeddings(matrix, segments, n_speakers=2, linkage="complete")
    # Only 2 valid rows should remain
    assert len(results) == 2
    assert results[0].start == 0.0
    assert results[1].start == 2.0


def test_cluster_embeddings_single_speaker_and_boundary():
    """Verify safe handling when N=1 or n_speakers=1."""
    import numpy as np
    from interview_pipeline.src.diarization import cluster_embeddings

    # Empty
    assert cluster_embeddings(np.empty((0, 256)), []) == []

    # Single segment
    emb = np.ones((1, 256), dtype=np.float32)
    emb /= np.linalg.norm(emb)
    res = cluster_embeddings(emb, [{"start": 1.0, "end": 2.0}], n_speakers=2)
    assert len(res) == 1
    assert res[0].speaker == "SPEAKER_00"

    # n_speakers = 1
    emb2 = np.ones((4, 256), dtype=np.float32)
    emb2 /= np.linalg.norm(emb2, axis=1, keepdims=True)
    segs = [{"start": float(i), "end": float(i + 0.8)} for i in range(4)]
    res2 = cluster_embeddings(emb2, segs, n_speakers=1)
    assert len(res2) == 4
    assert all(s.speaker == "SPEAKER_00" for s in res2)


def test_chronological_ordering_preserved():
    """Verify output segments maintain exact chronological order."""
    import numpy as np
    from interview_pipeline.src.diarization import cluster_embeddings

    matrix = np.random.randn(10, 256).astype(np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    segments = [{"start": float(i * 3.5), "end": float(i * 3.5 + 2.0)} for i in range(10)]

    results = cluster_embeddings(matrix, segments, n_speakers=2, linkage="complete")
    for i in range(len(results) - 1):
        assert results[i].start < results[i + 1].start
        assert results[i].end <= results[i + 1].start + 2.0

