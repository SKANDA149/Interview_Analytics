import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from research.global_alignment import load_reference_segments, load_global_words, extract_candidate_data
from research.perturbation import role_swap, missed_speech
from research.downstream_metrics import compute_metrics

REF = load_reference_segments()
WORDS = load_global_words()


def test_zero_severity_role_swap_matches_baseline_metrics():
    baseline = compute_metrics(REF, WORDS, run_nlp=False)
    result = compute_metrics(role_swap(REF, 0.0, seed=1), WORDS, run_nlp=False)
    for key in ("words_per_minute", "total_filler_words", "total_long_pauses",
                "total_short_pauses", "longest_pause_sec", "average_pause_sec",
                "total_silence_sec", "silence_ratio_pct", "total_speech_duration_sec"):
        assert baseline[key] == result[key], f"{key} differs at severity 0"


def test_zero_severity_missed_speech_matches_baseline_metrics():
    baseline = compute_metrics(REF, WORDS, run_nlp=False)
    result = compute_metrics(missed_speech(REF, 0.0, seed=1), WORDS, run_nlp=False)
    for key in ("words_per_minute", "total_filler_words", "total_long_pauses",
                "total_short_pauses", "longest_pause_sec", "average_pause_sec",
                "total_silence_sec", "silence_ratio_pct", "total_speech_duration_sec"):
        assert baseline[key] == result[key], f"{key} differs at severity 0"


def test_missed_speech_reduces_speech_duration_as_severity_increases():
    durations = []
    for severity in (0.0, 0.10, 0.25, 0.50):
        result = compute_metrics(missed_speech(REF, severity, seed=11), WORDS, run_nlp=False)
        durations.append(result["total_speech_duration_sec"])
    assert durations == sorted(durations, reverse=True)


def test_compute_metrics_runs_end_to_end_without_nlp():
    result = compute_metrics(REF, WORDS, run_nlp=False)
    for key in ("words_per_minute", "total_filler_words", "total_long_pauses",
                "silence_ratio_pct", "num_candidate_words"):
        assert key in result
    assert result["nlp"] is None


# ---- evidence for the truncation defect (added after audit) ----

def test_semantic_score_only_reflects_transcript_head():
    """AUDIT EVIDENCE. The content scorer (all-MiniLM-L6-v2, 256 word-piece
    limit) silently truncates, so it sees only ~the first 200 words of a
    ~1633-word candidate answer. Empirical signature: under missed_speech at
    low severities, different seeds delete different LATER segments -- total
    word counts differ by tens of words -- yet the scored HEAD of the
    transcript is byte-identical across all seeds. This test pins that
    signature without needing the model loaded, so the defect claim rests on
    reproducible evidence rather than inference about the model config.
    """
    from research.global_alignment import align_words_to_speakers

    def head_and_total(corrupted):
        t, _ = extract_candidate_data(
            align_words_to_speakers(WORDS, corrupted, policy="fallback"))
        toks = t.split()
        return " ".join(toks[:200]), len(toks)

    seeds = (42, 7, 123, 2024, 99)
    heads, totals = set(), []
    for seed in seeds:
        h, n = head_and_total(missed_speech(REF, 0.10, seed=seed))
        heads.add(h)
        totals.append(n)

    # the scored window is identical across every seed ...
    assert len(heads) == 1, "expected one shared 200-word head across seeds"
    # ... while the full transcripts genuinely differ in length
    assert len(set(totals)) > 1, "expected total word counts to differ by seed"


def test_extract_candidate_data_importable_for_audit_test():
    """Guards the import the audit test above depends on."""
    from research.global_alignment import extract_candidate_data as f
    assert callable(f)
