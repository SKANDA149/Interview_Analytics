"""
research/perturbation.py

Controlled, graded perturbation operators for diarization/role-attribution
error-sensitivity experiments. Operate on research.global_alignment.Segment
objects (this project's minimal glue substitute for a DiarizationSegment
class, since this pipeline never had one).

These operators NEVER mutate their input. Each returns a brand-new list of
Segment copies. The reference segments loaded from
data/diarization/segments.json are treated as ground truth and are never
written to by anything in this module.
"""
import random

from research.global_alignment import Segment


def _clone(segments):
    return [Segment(start=s.start, end=s.end, speaker=s.speaker) for s in segments]


def role_swap(segments, severity, seed, candidate_label="CANDIDATE", interviewer_label="INTERVIEWER"):
    """
    Priority 1 operator. With probability `severity`, flip a segment's
    CANDIDATE <-> INTERVIEWER label. Pure label permutation — timings are
    never touched.

    severity: float in [0, 1]. seed: int, required for reproducibility.
    """
    if not (0.0 <= severity <= 1.0):
        raise ValueError(f"severity must be in [0, 1], got {severity}")

    out = _clone(segments)
    if severity == 0.0:
        return out

    rng = random.Random(seed)
    flip_map = {candidate_label: interviewer_label, interviewer_label: candidate_label}
    for seg in out:
        if seg.speaker in flip_map and rng.random() < severity:
            seg.speaker = flip_map[seg.speaker]
    return out


def missed_speech(segments, severity, seed, candidate_label="CANDIDATE"):
    """
    Priority 2 operator. Simulates diarization/VAD under-detection by
    deleting a subset of the CANDIDATE's reference segments until removed
    duration reaches `severity` fraction of total candidate speech duration.
    INTERVIEWER segments are never touched.

    severity: float in [0, 1]. seed: int, required for reproducibility.
    """
    if not (0.0 <= severity <= 1.0):
        raise ValueError(f"severity must be in [0, 1], got {severity}")

    candidate_segs = [s for s in segments if s.speaker == candidate_label]
    total_candidate_duration = sum(s.end - s.start for s in candidate_segs)

    if severity == 0.0 or total_candidate_duration == 0.0 or not candidate_segs:
        return _clone(segments)

    target_removed = severity * total_candidate_duration

    rng = random.Random(seed)
    order = list(range(len(candidate_segs)))
    rng.shuffle(order)

    removed_duration = 0.0
    drop_indices = set()
    for idx in order:
        if removed_duration >= target_removed:
            break
        seg = candidate_segs[idx]
        drop_indices.add(idx)
        removed_duration += (seg.end - seg.start)

    kept_candidate = [seg for i, seg in enumerate(candidate_segs) if i not in drop_indices]
    kept_set_ids = {id(seg) for seg in kept_candidate}
    result = [s for s in segments if (s.speaker != candidate_label) or (id(s) in kept_set_ids)]
    return _clone(result)


OPERATORS = {
    "role_swap": role_swap,
    "missed_speech": missed_speech,
}

SEVERITIES = [0.0, 0.10, 0.25, 0.50]
