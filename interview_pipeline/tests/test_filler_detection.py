"""
Comprehensive unit tests for context-aware filler-word detection.

Verifies:
1. Clear unconditional vocalic fillers (um, uh, er, ah, hmm).
2. Grammatical vs disfluent uses of "like" (comparisons, verbs vs hesitation).
3. Grammatical vs disfluent uses of "so" (conjunctions, intensifiers vs stalls).
4. Question/transitive vs parenthetical uses of "you know".
5. Capitalization and punctuation handling.
6. Repeated and adjacent fillers (e.g. "um uh", "like like").
7. Multiword phrases counted once (not double-counted).
8. Missing timestamps, empty transcripts, and malformed word records.
9. Aggregation consistency between chunk counts and overall totals.
"""
import pytest
from interview_pipeline.src.filler_detection import detect_filler_words


class TestClearVocalicFillers:
    """Tests for clear, non-lexical vocalic fillers that are unconditionally disfluent."""

    def test_um_and_uh_unconditional(self):
        """Um and uh should always be counted as definite fillers."""
        data = {
            "chunk_id": "test_01",
            "words": [
                {"word": "Um", "start": 1.0, "end": 1.4},
                {"word": "I", "start": 1.5, "end": 1.6},
                {"word": "think", "start": 1.7, "end": 2.0},
                {"word": "this", "start": 2.1, "end": 2.3},
                {"word": "works", "start": 2.4, "end": 2.8},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 1
        assert res["filler_words"][0]["word"] == "um"
        assert res["filler_words"][0]["confidence"] == "definite"

    def test_uh_in_sentence(self):
        """Uh in middle of sentence should be detected."""
        data = {
            "chunk_id": "test_02",
            "words": [
                {"word": "I", "start": 0.5, "end": 0.7},
                {"word": "was", "start": 0.8, "end": 1.0},
                {"word": "uh", "start": 1.1, "end": 1.3},
                {"word": "trying", "start": 1.4, "end": 1.8},
                {"word": "another", "start": 1.9, "end": 2.3},
                {"word": "approach", "start": 2.4, "end": 2.9},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 1
        assert res["filler_words"][0]["word"] == "uh"

    def test_other_vocalic_fillers(self):
        """Er, ah, and hmm should be recognized."""
        data = {
            "chunk_id": "test_03",
            "transcript": "er well ah that is hmm tricky",
            "words": [
                {"word": "er", "start": 0.1, "end": 0.3},
                {"word": "well", "start": 0.4, "end": 0.7},
                {"word": "ah", "start": 0.8, "end": 1.0},
                {"word": "that", "start": 1.1, "end": 1.3},
                {"word": "is", "start": 1.4, "end": 1.5},
                {"word": "hmm", "start": 1.6, "end": 1.9},
                {"word": "tricky", "start": 2.0, "end": 2.5},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 3
        words = [w["word"] for w in res["filler_words"]]
        assert words == ["er", "ah", "hmm"]


class TestLikeContextDisambiguation:
    """Tests distinguishing grammatical 'like' from disfluent 'like'."""

    def test_comparison_preposition_not_filler(self):
        """'technologies like SQL' is an ordinary preposition of exemplification, not a filler."""
        data = {
            "chunk_id": "like_01",
            "words": [
                {"word": "I", "start": 0.0, "end": 0.2},
                {"word": "know", "start": 0.3, "end": 0.5},
                {"word": "technologies", "start": 0.6, "end": 1.2},
                {"word": "like", "start": 1.3, "end": 1.5},
                {"word": "SQL", "start": 1.6, "end": 2.0},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 0

    def test_transitive_verb_not_filler(self):
        """'if you like this video' has 'like' functioning as a transitive verb, not a filler."""
        data = {
            "chunk_id": "like_02",
            "words": [
                {"word": "if", "start": 0.0, "end": 0.2},
                {"word": "you", "start": 0.3, "end": 0.5},
                {"word": "like", "start": 0.6, "end": 0.8},
                {"word": "this", "start": 0.9, "end": 1.1},
                {"word": "video", "start": 1.2, "end": 1.6},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 0

    def test_infinitive_verb_not_filler(self):
        """'I like to grow' has 'like' followed by infinitive, not a filler."""
        data = {
            "chunk_id": "like_03",
            "words": [
                {"word": "I", "start": 0.0, "end": 0.2},
                {"word": "would", "start": 0.3, "end": 0.5},
                {"word": "like", "start": 0.6, "end": 0.8},
                {"word": "to", "start": 0.9, "end": 1.0},
                {"word": "grow", "start": 1.1, "end": 1.4},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 0

    def test_perception_comparison_not_filler(self):
        """'looks like a good plan' has 'like' as comparative preposition with perception verb."""
        data = {
            "chunk_id": "like_04",
            "words": [
                {"word": "that", "start": 0.0, "end": 0.2},
                {"word": "looks", "start": 0.3, "end": 0.6},
                {"word": "like", "start": 0.7, "end": 0.9},
                {"word": "a", "start": 1.0, "end": 1.1},
                {"word": "good", "start": 1.2, "end": 1.4},
                {"word": "plan", "start": 1.5, "end": 1.8},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 0

    def test_discourse_approximator_with_really_is_filler(self):
        """'It was, like, really difficult.' functions as a colloquial discourse approximator."""
        data = {
            "chunk_id": "like_05",
            "words": [
                {"word": "It", "start": 0.0, "end": 0.2},
                {"word": "was,", "start": 0.3, "end": 0.5},
                {"word": "like,", "start": 0.6, "end": 0.8},
                {"word": "really", "start": 0.9, "end": 1.2},
                {"word": "difficult.", "start": 1.3, "end": 1.8},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 1
        assert res["filler_words"][0]["word"] == "like"

    def test_like_isolated_by_speech_pauses_is_filler(self):
        """'like' preceded and followed by noticeable acoustic pauses (>=0.25s) is a filler."""
        data = {
            "chunk_id": "like_06",
            "words": [
                {"word": "it", "start": 0.0, "end": 0.2},
                {"word": "took", "start": 0.3, "end": 0.6},
                # 0.4s gap before like
                {"word": "like", "start": 1.0, "end": 1.2},
                # 0.5s gap after like
                {"word": "five", "start": 1.7, "end": 2.0},
                {"word": "days", "start": 2.1, "end": 2.5},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 1
        assert res["filler_words"][0]["word"] == "like"


class TestSoContextDisambiguation:
    """Tests distinguishing grammatical 'so' from disfluent 'so'."""

    def test_so_that_conjunction_not_filler(self):
        """'so that the application works' is a subordinating conjunction, not a filler."""
        data = {
            "chunk_id": "so_01",
            "words": [
                {"word": "we", "start": 0.0, "end": 0.2},
                {"word": "optimize", "start": 0.3, "end": 0.8},
                {"word": "so", "start": 0.9, "end": 1.1},
                {"word": "that", "start": 1.2, "end": 1.4},
                {"word": "the", "start": 1.5, "end": 1.6},
                {"word": "application", "start": 1.7, "end": 2.2},
                {"word": "works", "start": 2.3, "end": 2.6},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 0

    def test_so_much_intensifier_not_filler(self):
        """'thank you so much' uses 'so' as degree adverb, not a filler."""
        data = {
            "chunk_id": "so_02",
            "words": [
                {"word": "thank", "start": 0.0, "end": 0.3},
                {"word": "you", "start": 0.4, "end": 0.6},
                {"word": "so", "start": 0.7, "end": 0.9},
                {"word": "much", "start": 1.0, "end": 1.3},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 0

    def test_fluent_turn_initial_so_is_ambiguous_not_filler(self):
        """'so shall we start?' is an introductory discourse marker; without a pause, not a disfluency."""
        data = {
            "chunk_id": "so_03",
            "words": [
                {"word": "so", "start": 0.0, "end": 0.2},
                {"word": "shall", "start": 0.25, "end": 0.5},
                {"word": "we", "start": 0.55, "end": 0.7},
                {"word": "start", "start": 0.75, "end": 1.1},
            ]
        }
        res = detect_filler_words(data)
        # Conservative: do not count fluent question openers as disfluent fillers
        assert res["filler_count"] == 0
        assert res["ambiguous_count"] == 1
        assert res["ambiguous_words"][0]["word"] == "so"

    def test_so_with_hesitation_pause_is_filler(self):
        """'so' followed by an acoustic pause (>=0.4s) indicates a conversational stall/hesitation."""
        data = {
            "chunk_id": "so_04",
            "words": [
                {"word": "so", "start": 0.0, "end": 0.3},
                # 0.6s pause
                {"word": "my", "start": 0.9, "end": 1.1},
                {"word": "approach", "start": 1.2, "end": 1.6},
                {"word": "was", "start": 1.7, "end": 1.9},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 1
        assert res["filler_words"][0]["word"] == "so"

    def test_trailing_so_is_filler(self):
        """Trailing 'yeah so' at end of utterance functions as a conversational stall."""
        data = {
            "chunk_id": "so_05",
            "words": [
                {"word": "only", "start": 0.0, "end": 0.3},
                {"word": "yeah", "start": 0.4, "end": 0.7},
                {"word": "so", "start": 0.8, "end": 1.1},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 1
        assert res["filler_words"][0]["word"] == "so"


class TestYouKnowDisambiguation:
    """Tests distinguishing grammatical 'you know' from disfluent 'you know'."""

    def test_ordinary_question_not_filler(self):
        """'Do you know the difference?' is an ordinary grammatical question, not a filler."""
        data = {
            "chunk_id": "yk_01",
            "words": [
                {"word": "Do", "start": 0.0, "end": 0.2},
                {"word": "you", "start": 0.25, "end": 0.4},
                {"word": "know", "start": 0.45, "end": 0.7},
                {"word": "the", "start": 0.75, "end": 0.9},
                {"word": "difference?", "start": 0.95, "end": 1.5},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 0

    def test_auxiliary_clause_let_you_know_not_filler(self):
        """'we will let you know' has 'you know' embedded in an auxiliary clause, not a filler."""
        data = {
            "chunk_id": "yk_02",
            "words": [
                {"word": "we", "start": 0.0, "end": 0.2},
                {"word": "will", "start": 0.25, "end": 0.4},
                {"word": "let", "start": 0.45, "end": 0.65},
                {"word": "you", "start": 0.7, "end": 0.85},
                {"word": "know", "start": 0.9, "end": 1.1},
                {"word": "the", "start": 1.15, "end": 1.3},
                {"word": "result", "start": 1.35, "end": 1.7},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 0

    def test_transitive_verb_with_that_clause_not_filler(self):
        """'you know that' is a transitive verb taking a complement clause, not a filler."""
        data = {
            "chunk_id": "yk_03",
            "words": [
                {"word": "you", "start": 0.0, "end": 0.2},
                {"word": "know", "start": 0.25, "end": 0.5},
                {"word": "that", "start": 0.55, "end": 0.8},
                {"word": "Python", "start": 0.85, "end": 1.2},
                {"word": "is", "start": 1.25, "end": 1.4},
                {"word": "dynamic", "start": 1.45, "end": 1.9},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 0

    def test_parenthetical_you_know_is_filler(self):
        """'it was, you know, quite a challenge' is a parenthetical vocal filler."""
        data = {
            "chunk_id": "yk_04",
            "words": [
                {"word": "it", "start": 0.0, "end": 0.2},
                {"word": "was,", "start": 0.25, "end": 0.5},
                {"word": "you", "start": 0.55, "end": 0.7},
                {"word": "know,", "start": 0.75, "end": 1.0},
                {"word": "quite", "start": 1.05, "end": 1.3},
                {"word": "a", "start": 1.35, "end": 1.45},
                {"word": "challenge", "start": 1.5, "end": 2.0},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 1
        assert res["filler_words"][0]["word"] == "you know"

    def test_utterance_final_tag_you_know_is_filler(self):
        """'it's difficult you know' at utterance end is a discourse filler tag."""
        data = {
            "chunk_id": "yk_05",
            "words": [
                {"word": "it's", "start": 0.0, "end": 0.3},
                {"word": "difficult", "start": 0.4, "end": 0.9},
                {"word": "you", "start": 1.0, "end": 1.2},
                {"word": "know", "start": 1.3, "end": 1.6},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 1
        assert res["filler_words"][0]["word"] == "you know"

    def test_you_know_counted_once_not_twice(self):
        """Ensure 'you know' increments filler_count by 1, never 2."""
        data = {
            "chunk_id": "yk_06",
            "words": [
                {"word": "you", "start": 1.0, "end": 1.2},
                {"word": "know", "start": 1.3, "end": 1.6},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 1
        assert len(res["filler_words"]) == 1


class TestEdgeCasesAndRobustness:
    """Tests for edge cases, formatting, missing values, and boundary behavior."""

    def test_empty_transcript(self):
        """Empty transcript must return zero count without error."""
        data = {"chunk_id": "empty", "words": [], "transcript": ""}
        res = detect_filler_words(data)
        assert res["filler_count"] == 0
        assert res["filler_words"] == []
        assert res["ambiguous_count"] == 0

    def test_missing_timestamps(self):
        """Words missing timestamps must be safely processed via lexical rules."""
        data = {
            "chunk_id": "notime",
            "transcript": "Um I like really was thinking",
            "words": [
                {"word": "Um"},
                {"word": "I"},
                {"word": "like"},
                {"word": "really"},
                {"word": "was"},
                {"word": "thinking"},
            ]
        }
        res = detect_filler_words(data)
        # 'um' is unconditional, 'like really' matches discourse approximator
        assert res["filler_count"] == 2
        words = [w["word"] for w in res["filler_words"]]
        assert words == ["um", "like"]

    def test_malformed_word_records(self):
        """String entries or None values in words list should not crash."""
        data = {
            "chunk_id": "malformed",
            "words": ["um", None, {"word": "uh", "start": None, "end": None}]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 2

    def test_repeated_and_adjacent_fillers(self):
        """Adjacent 'um uh' and repeated 'like like' should each be counted."""
        data = {
            "chunk_id": "repeat",
            "words": [
                {"word": "um", "start": 0.1, "end": 0.3},
                {"word": "uh", "start": 0.4, "end": 0.6},
                {"word": "like", "start": 0.7, "end": 0.9},
                {"word": "like", "start": 1.0, "end": 1.2},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 4

    def test_capitalization_and_punctuation(self):
        """Capitalization and attached punctuation should be normalized cleanly."""
        data = {
            "chunk_id": "caps_punct",
            "words": [
                {"word": "UM,", "start": 0.1, "end": 0.4},
                {"word": "SO...", "start": 0.5, "end": 0.8},
                {"word": "THAT", "start": 0.9, "end": 1.1},
            ]
        }
        res = detect_filler_words(data)
        # 'UM,' is vocalic filler (definite)
        # 'SO... THAT' is followed by 'that' -> disqualified as conjunction 'so that'
        assert res["filler_count"] == 1
        assert res["filler_words"][0]["word"] == "um"

    def test_breakdown_consistency(self):
        """Filler breakdown dictionary sum must match filler_count."""
        data = {
            "chunk_id": "breakdown_test",
            "words": [
                {"word": "um", "start": 0.1, "end": 0.3},
                {"word": "um", "start": 0.4, "end": 0.6},
                {"word": "uh", "start": 0.7, "end": 0.9},
            ]
        }
        res = detect_filler_words(data)
        assert res["filler_count"] == 3
        assert res["filler_breakdown"] == {"um": 2, "uh": 1}
        assert sum(res["filler_breakdown"].values()) == res["filler_count"]
