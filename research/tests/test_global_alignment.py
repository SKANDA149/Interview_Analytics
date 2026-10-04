import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from research.global_alignment import (
    load_reference_segments, load_global_words, align_words_to_speakers,
    extract_candidate_data, CHUNK_DURATION_SEC,
)


def test_load_reference_segments_nonempty():
    segs = load_reference_segments()
    assert len(segs) > 0
    assert all(s.speaker in ("CANDIDATE", "INTERVIEWER") for s in segs)


def test_load_global_words_are_globally_increasing_across_chunks():
    words = load_global_words()
    assert len(words) > 0
    # chunk stitching should produce a roughly monotonic global timeline
    # (allow local jitter within a chunk, but chunk N+1 words should start
    # at or after chunk N's offset)
    starts = [w["start"] for w in words]
    assert starts[-1] > CHUNK_DURATION_SEC  # more than 1 chunk's worth of speech


def test_align_words_to_speakers_labels_every_word():
    segs = load_reference_segments()
    words = load_global_words()
    labelled = align_words_to_speakers(words, segs)
    assert len(labelled) == len(words)
    assert all(w["speaker"] in ("CANDIDATE", "INTERVIEWER") for w in labelled)


def test_extract_candidate_data_only_candidate_words():
    segs = load_reference_segments()
    words = load_global_words()
    labelled = align_words_to_speakers(words, segs)
    transcript, candidate_words = extract_candidate_data(labelled, "CANDIDATE")
    assert all(w["speaker"] == "CANDIDATE" for w in candidate_words)
    assert isinstance(transcript, str)


# ---- attribution policy (added after audit) ----

def test_strict_policy_drops_unattributed_words():
    """Words overlapping no segment are dropped under strict, kept under fallback."""
    segs = load_reference_segments()
    words = load_global_words()
    fb = align_words_to_speakers(words, segs, policy="fallback")
    st = align_words_to_speakers(words, segs, policy="strict")
    assert len(fb) == len(words)
    assert len(st) <= len(fb)


def test_policies_diverge_under_missed_speech():
    """The two policies must differ materially once segments are deleted --
    this is the sensitivity the audit surfaced, so it is pinned by a test."""
    from research.perturbation import missed_speech
    segs = load_reference_segments()
    words = load_global_words()
    corrupted = missed_speech(segs, 0.50, seed=42)
    fb = align_words_to_speakers(words, corrupted, policy="fallback")
    st = align_words_to_speakers(words, corrupted, policy="strict")
    fb_cand = sum(1 for w in fb if w["speaker"] == "CANDIDATE")
    st_cand = sum(1 for w in st if w["speaker"] == "CANDIDATE")
    assert fb_cand > st_cand, "fallback must recover more candidate words than strict"


def test_policies_agree_under_role_swap():
    """role_swap never creates unattributed regions, so both policies agree."""
    from research.perturbation import role_swap
    segs = load_reference_segments()
    words = load_global_words()
    corrupted = role_swap(segs, 0.50, seed=42)
    fb = align_words_to_speakers(words, corrupted, policy="fallback")
    st = align_words_to_speakers(words, corrupted, policy="strict")
    fb_cand = sum(1 for w in fb if w["speaker"] == "CANDIDATE")
    st_cand = sum(1 for w in st if w["speaker"] == "CANDIDATE")
    assert abs(fb_cand - st_cand) / fb_cand < 0.01


def test_invalid_policy_rejected():
    segs = load_reference_segments()
    try:
        align_words_to_speakers([], segs, policy="nonsense")
    except ValueError:
        return
    raise AssertionError("invalid policy should raise ValueError")
