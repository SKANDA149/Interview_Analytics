"""Align Whisper word timestamps with diarization speaker segments."""
from dataclasses import dataclass
from typing import List, Tuple

try:
    from .diarization import DiarizationSegment
except ImportError:
    from interview_pipeline.src.diarization import DiarizationSegment

@dataclass
class LabelledWord:
    word: str
    start: float
    end: float
    speaker: str

@dataclass
class SpeakerTurn:
    speaker: str
    start: float
    end: float
    text: str

def align_words_to_speakers(
    words: list,
    diarization_segments: list
) -> list:
    """
    Map each Whisper word to a speaker using maximum temporal overlap.
    
    Args:
        words: List of dicts with keys "word", "start", "end" (from Whisper).
        diarization_segments: List of DiarizationSegment objects.
    
    Returns:
        List of LabelledWord objects.
    """
    if not words:
        return []
        
    labelled_words = []
    
    for word_dict in words:
        word_start = word_dict.get("start", 0.0)
        word_end = word_dict.get("end", 0.0)
        word_text = word_dict.get("word", "")
        
        if not diarization_segments:
            labelled_words.append(LabelledWord(word=word_text, start=word_start, end=word_end, speaker="UNKNOWN"))
            continue
            
        max_overlap = 0.0
        best_segment = None
        
        for seg in diarization_segments:
            overlap = max(0.0, min(word_end, seg.end) - max(word_start, seg.start))
            if overlap > max_overlap:
                max_overlap = overlap
                best_segment = seg
                
        if max_overlap == 0.0:
            # Nearest neighbor
            mid = (word_start + word_end) / 2
            min_dist = float('inf')
            
            for seg in diarization_segments:
                if mid < seg.start:
                    dist = seg.start - mid
                elif mid > seg.end:
                    dist = mid - seg.end
                else:
                    dist = 0.0
                    
                if dist < min_dist:
                    min_dist = dist
                    best_segment = seg
                    
        assigned_speaker = best_segment.speaker if best_segment else "UNKNOWN"
        labelled_words.append(LabelledWord(word=word_text, start=word_start, end=word_end, speaker=assigned_speaker))
        
    print(f"[ALIGNMENT] Aligned {len(labelled_words)} words to speakers")
    return labelled_words

def build_speaker_turns(labelled_words: list) -> list:
    """
    Group consecutive same-speaker words into SpeakerTurn objects.
    
    Returns:
        List of SpeakerTurn objects.
    """
    if not labelled_words:
        return []
        
    turns = []
    current_speaker = labelled_words[0].speaker
    current_words = []
    
    for lw in labelled_words:
        if lw.speaker != current_speaker:
            if current_words:
                turn_text = " ".join([w.word.strip() for w in current_words if w.word.strip()]).strip()
                turns.append(SpeakerTurn(
                    speaker=current_speaker,
                    start=current_words[0].start,
                    end=current_words[-1].end,
                    text=turn_text
                ))
            current_speaker = lw.speaker
            current_words = [lw]
        else:
            current_words.append(lw)
            
    if current_words:
        turn_text = " ".join([w.word.strip() for w in current_words if w.word.strip()]).strip()
        turns.append(SpeakerTurn(
            speaker=current_speaker,
            start=current_words[0].start,
            end=current_words[-1].end,
            text=turn_text
        ))
        
    return turns

def extract_candidate_data(
    labelled_words: list,
    candidate_label: str = "CANDIDATE"
) -> tuple:
    """
    Extract candidate-only transcript and word list.
    
    Args:
        labelled_words: List of LabelledWord objects.
        candidate_label: The speaker label for the candidate.
    
    Returns:
        Tuple of:
            candidate_transcript: str (space-joined candidate words)
            candidate_words: list of dicts [{"word": str, "start": float, "end": float}, ...]
                             Compatible with existing filler_detection, pause_detection,
                             and speech_analysis module interfaces.
    """
    if not labelled_words:
        return ("", [])
        
    candidate_words_list = [w for w in labelled_words if w.speaker == candidate_label]
    
    if not candidate_words_list:
        print(f"[ALIGNMENT] Warning: No words found for speaker '{candidate_label}'")
        return ("", [])
        
    candidate_transcript = " ".join([w.word.strip() for w in candidate_words_list if w.word.strip()]).strip()
    
    candidate_words_dicts = [
        {
            "word": w.word.strip().lower(),
            "start": w.start,
            "end": w.end
        }
        for w in candidate_words_list
    ]
    
    print(f"[ALIGNMENT] Extracted {len(candidate_words_dicts)} candidate words from {len(labelled_words)} total words")
    
    return (candidate_transcript, candidate_words_dicts)
