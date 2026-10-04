import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from research.global_alignment import load_reference_segments, Segment
from research.perturbation import role_swap, missed_speech, _clone, OPERATORS, SEVERITIES

REF = load_reference_segments()


def segs_equal(a, b):
    if len(a) != len(b):
        return False
    return all(x.start == y.start and x.end == y.end and x.speaker == y.speaker for x, y in zip(a, b))


def test_role_swap_zero_severity_matches_reference():
    assert segs_equal(role_swap(REF, 0.0, seed=1), REF)


def test_role_swap_reproducible_same_seed():
    assert segs_equal(role_swap(REF, 0.25, seed=42), role_swap(REF, 0.25, seed=42))


def test_role_swap_different_seeds_differ():
    assert not segs_equal(role_swap(REF, 0.5, seed=1), role_swap(REF, 0.5, seed=2))


def test_role_swap_never_changes_timings():
    out = role_swap(REF, 0.5, seed=7)
    for orig, corrupted in zip(REF, out):
        assert orig.start == corrupted.start
        assert orig.end == corrupted.end


def test_role_swap_only_flips_between_candidate_interviewer():
    out = role_swap(REF, 0.5, seed=7)
    valid = {"CANDIDATE", "INTERVIEWER"}
    assert all(c.speaker in valid for c in out)


def test_role_swap_does_not_mutate_input():
    ref_copy = _clone(REF)
    role_swap(REF, 0.5, seed=3)
    assert segs_equal(REF, ref_copy)


def test_missed_speech_zero_severity_matches_reference():
    assert segs_equal(missed_speech(REF, 0.0, seed=1), REF)


def test_missed_speech_reproducible_same_seed():
    assert segs_equal(missed_speech(REF, 0.25, seed=42), missed_speech(REF, 0.25, seed=42))


def test_missed_speech_never_touches_interviewer_segments():
    ref_interviewer = [s for s in REF if s.speaker == "INTERVIEWER"]
    out = missed_speech(REF, 0.5, seed=9)
    out_interviewer = [s for s in out if s.speaker == "INTERVIEWER"]
    assert len(out_interviewer) == len(ref_interviewer)
    for o, c in zip(ref_interviewer, out_interviewer):
        assert o.start == c.start and o.end == c.end


def test_missed_speech_kept_candidate_segments_unchanged_timings():
    out = missed_speech(REF, 0.25, seed=9)
    out_candidate = {(s.start, s.end) for s in out if s.speaker == "CANDIDATE"}
    ref_candidate = {(s.start, s.end) for s in REF if s.speaker == "CANDIDATE"}
    assert out_candidate.issubset(ref_candidate)


def test_missed_speech_removes_approximately_requested_fraction():
    ref_candidate = [s for s in REF if s.speaker == "CANDIDATE"]
    total = sum(s.end - s.start for s in ref_candidate)
    for severity in (0.10, 0.25, 0.50):
        out = missed_speech(REF, severity, seed=5)
        out_dur = sum(s.end - s.start for s in out if s.speaker == "CANDIDATE")
        removed_frac = (total - out_dur) / total
        assert severity - 0.05 <= removed_frac <= severity + 0.15


def test_missed_speech_does_not_mutate_input():
    ref_copy = _clone(REF)
    missed_speech(REF, 0.5, seed=3)
    assert segs_equal(REF, ref_copy)


def test_missed_speech_candidate_count_monotonic_nonincreasing():
    counts = [sum(1 for s in missed_speech(REF, sev, seed=11) if s.speaker == "CANDIDATE") for sev in SEVERITIES]
    assert counts == sorted(counts, reverse=True)


def test_operators_and_severities_match_spec():
    assert set(OPERATORS.keys()) == {"role_swap", "missed_speech"}
    assert SEVERITIES == [0.0, 0.10, 0.25, 0.50]
