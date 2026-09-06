"""Speaker role assignment for interview diarization."""
from pathlib import Path

# Import the DiarizationSegment dataclass from the diarization module
try:
    from .diarization import DiarizationSegment
except ImportError:
    from interview_pipeline.src.diarization import DiarizationSegment

def assign_speaker_roles(segments: list) -> tuple:
    """
    Assign semantic roles (CANDIDATE / INTERVIEWER) to diarization speaker labels.
    
    Heuristic:
    1. Sum total speech duration per speaker label.
    2. Speaker with greater total duration → CANDIDATE (interviewees talk more).
    3. If durations are within 10% of each other, the speaker who speaks
       SECOND chronologically is CANDIDATE (interviewers typically open).
    
    Args:
        segments: List of DiarizationSegment objects with raw speaker labels.
    
    Returns:
        Tuple of:
            role_map: dict mapping raw labels to roles, e.g. {"SPEAKER_00": "CANDIDATE", "SPEAKER_01": "INTERVIEWER"}
            relabelled_segments: New list of DiarizationSegment with .speaker set to role labels
    """
    if not segments:
        return ({}, [])
        
    durations = {}
    for seg in segments:
        durations[seg.speaker] = durations.get(seg.speaker, 0.0) + (seg.end - seg.start)
        
    # Sort speakers by total duration descending
    sorted_speakers = sorted(durations.items(), key=lambda x: x[1], reverse=True)
    
    role_map = {}
    
    if len(sorted_speakers) == 1:
        spk = sorted_speakers[0][0]
        role_map[spk] = "CANDIDATE"
        print("[ROLES] Only 1 speaker detected, assigning as CANDIDATE")
    else:
        speaker_a, dur_a = sorted_speakers[0]
        speaker_b, dur_b = sorted_speakers[1]
        
        ratio = min(dur_a, dur_b) / max(dur_a, dur_b) if max(dur_a, dur_b) > 0 else 0
        
        if ratio > 0.9:
            # Chronological heuristic
            first_speaker = segments[0].speaker
            if first_speaker == speaker_a:
                role_map[speaker_a] = "INTERVIEWER"
                role_map[speaker_b] = "CANDIDATE"
            else:
                role_map[speaker_b] = "INTERVIEWER"
                role_map[speaker_a] = "CANDIDATE"
            print(f"[ROLES] Similar talk times ({dur_a:.1f}s vs {dur_b:.1f}s). Using chronological heuristic.")
        else:
            role_map[speaker_a] = "CANDIDATE"
            role_map[speaker_b] = "INTERVIEWER"
            print(f"[ROLES] Assigned CANDIDATE={speaker_a} ({dur_a:.1f}s), INTERVIEWER={speaker_b} ({dur_b:.1f}s)")
            
        if len(sorted_speakers) > 2:
            print(f"[ROLES] Warning: {len(sorted_speakers)} speakers detected, expected 2.")
            interviewer_idx = 1
            for spk, _ in sorted_speakers[2:]:
                if role_map.get(spk) is None:
                    role_map[spk] = f"INTERVIEWER_{interviewer_idx:02d}"
                    interviewer_idx += 1
                
    relabelled_segments = []
    for seg in segments:
        new_seg = DiarizationSegment(
            start=seg.start,
            end=seg.end,
            speaker=role_map.get(seg.speaker, seg.speaker)
        )
        relabelled_segments.append(new_seg)
        
    return (role_map, relabelled_segments)
