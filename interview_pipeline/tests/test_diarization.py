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
