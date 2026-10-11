import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "interview_pipeline", "src"))

from diarization import DiarizationSegment
from research.perturbation import role_swap, missed_speech, _clone, OPERATORS, SEVERITIES


def load_reference():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "diarization", "segments.json")
    with open(path) as f:
        raw = json.load(f)
    return [DiarizationSegment(**item) for item in raw]


REF = load_reference()


def segs_equal(a, b):
    if len(a) != len(b):
        return False
    return all(x.start == y.start and x.end == y.end and x.speaker == y.speaker for x, y in zip(a, b))


# ---------------- role_swap ----------------

def test_role_swap_zero_severity_matches_reference():
    out = role_swap(REF, 0.0, seed=1)
    assert segs_equal(out, REF)


def test_role_swap_reproducible_same_seed():
    a = role_swap(REF, 0.25, seed=42)
    b = role_swap(REF, 0.25, seed=42)
    assert segs_equal(a, b)


def test_role_swap_different_seeds_differ():
    a = role_swap(REF, 0.5, seed=1)
    b = role_swap(REF, 0.5, seed=2)
    assert not segs_equal(a, b)


def test_role_swap_never_changes_timings():
    out = role_swap(REF, 0.5, seed=7)
    for orig, corrupted in zip(REF, out):
        assert orig.start == corrupted.start
        assert orig.end == corrupted.end


def test_role_swap_only_flips_between_candidate_interviewer():
    out = role_swap(REF, 0.5, seed=7)
    valid = {"CANDIDATE", "INTERVIEWER"}
    for corrupted in out:
        assert corrupted.speaker in valid


def test_role_swap_does_not_mutate_input():
    ref_copy = _clone(REF)
    role_swap(REF, 0.5, seed=3)
    assert segs_equal(REF, ref_copy)


def test_role_swap_higher_severity_flips_more_on_average():
    # deterministic check across many seeds: expected flip count scales with severity
    def flips(sev, seed):
        out = role_swap(REF, sev, seed=seed)
        return sum(1 for o, c in zip(REF, out) if o.speaker != c.speaker)

    low = sum(flips(0.1, s) for s in range(20)) / 20
    high = sum(flips(0.5, s) for s in range(20)) / 20
    assert high > low


# ---------------- missed_speech ----------------

def test_missed_speech_zero_severity_matches_reference():
    out = missed_speech(REF, 0.0, seed=1)
    assert segs_equal(out, REF)


def test_missed_speech_reproducible_same_seed():
    a = missed_speech(REF, 0.25, seed=42)
    b = missed_speech(REF, 0.25, seed=42)
    assert segs_equal(a, b)


def test_missed_speech_different_seeds_may_differ():
    a = missed_speech(REF, 0.5, seed=1)
    b = missed_speech(REF, 0.5, seed=2)
    # not a strict guarantee for tiny inputs, but true for this 350-segment file
    assert not segs_equal(a, b)


def test_missed_speech_never_touches_interviewer_segments():
    ref_interviewer = [s for s in REF if s.speaker == "INTERVIEWER"]
    out = missed_speech(REF, 0.5, seed=9)
    out_interviewer = [s for s in out if s.speaker == "INTERVIEWER"]
    assert len(out_interviewer) == len(ref_interviewer)
    for o, c in zip(ref_interviewer, out_interviewer):
        assert o.start == c.start and o.end == c.end and o.speaker == c.speaker


def test_missed_speech_kept_candidate_segments_unchanged_timings():
    out = missed_speech(REF, 0.25, seed=9)
    out_candidate = {(s.start, s.end) for s in out if s.speaker == "CANDIDATE"}
    ref_candidate = {(s.start, s.end) for s in REF if s.speaker == "CANDIDATE"}
    # every kept candidate segment must be an exact (start,end) match to some reference segment
    assert out_candidate.issubset(ref_candidate)


def test_missed_speech_removes_approximately_requested_fraction():
    ref_candidate = [s for s in REF if s.speaker == "CANDIDATE"]
    total = sum(s.end - s.start for s in ref_candidate)
    for severity in (0.10, 0.25, 0.50):
        out = missed_speech(REF, severity, seed=5)
        out_candidate_duration = sum(s.end - s.start for s in out if s.speaker == "CANDIDATE")
        removed = total - out_candidate_duration
        removed_frac = removed / total
        # segment-granularity greedy removal: allow tolerance of one largest segment
        assert removed_frac >= severity - 0.05
        assert removed_frac <= severity + 0.15


def test_missed_speech_does_not_mutate_input():
    ref_copy = _clone(REF)
    missed_speech(REF, 0.5, seed=3)
    assert segs_equal(REF, ref_copy)


def test_missed_speech_candidate_segment_count_monotonic_nonincreasing():
    counts = []
    for severity in SEVERITIES:
        out = missed_speech(REF, severity, seed=11)
        counts.append(sum(1 for s in out if s.speaker == "CANDIDATE"))
    assert counts == sorted(counts, reverse=True)


# ---------------- operators registry ----------------

def test_operators_registry_contains_both():
    assert set(OPERATORS.keys()) == {"role_swap", "missed_speech"}


def test_severities_grid_matches_spec():
    assert SEVERITIES == [0.0, 0.10, 0.25, 0.50]
