# --- START OF FILE src/nlp_scoring.py ---
"""Reference-alignment helpers for explicitly identified interview responses.

These helpers deliberately do not infer question/answer pairs from chunk-level
transcripts. A numeric value is only produced when a caller supplies both an
identified candidate response and its question-specific rubric/reference. The
value describes alignment with that reference; it is not a measure of factual
correctness, completeness, intelligence, or overall performance.
"""
import re

try:
    from sentence_transformers import SentenceTransformer, util

    HAS_ST = True
except ImportError:
    HAS_ST = False


_nlp_model_cache = None


def load_nlp_model():
    """Load the local similarity model once, if it is available offline."""
    global _nlp_model_cache
    if not HAS_ST:
        return None
    if _nlp_model_cache is None:
        try:
            print("  -> [INFO] Loading MiniLM NLP Model into memory (offline)...")
            _nlp_model_cache = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _nlp_model_cache = False
    return _nlp_model_cache if _nlp_model_cache is not False else None


def not_evaluated_result(reason: str = "No rubric provided") -> dict:
    """Return the canonical unavailable semantic-evaluation state."""
    return {
        "semantic_score": None,
        "match_level": "Not evaluated",
        "scoring_status": "not_evaluated",
        "scoring_reason": reason,
        "scoring_method": "not_available",
    }


def evaluate_chunk_without_rubric(_transcript_text: str) -> dict:
    """Return the safe default for a chunk with no trusted Q&A pairing.

    The transcript is intentionally unused: a chunk can contain either speaker
    (or both), and no generic reference answer is valid for every interview.
    """
    return not_evaluated_result()


def evaluate_response_against_rubric(candidate_response: str, rubric: str | None) -> dict:
    """Compare one known candidate response with its supplied rubric.

    This function does not perform speaker attribution or question detection.
    Its caller must already have a trustworthy candidate response associated
    with the supplied rubric.
    """
    if not rubric or not rubric.strip():
        return not_evaluated_result("No rubric provided")

    if not candidate_response or not candidate_response.strip():
        return {
            "semantic_score": 0.0,
            "match_level": "No response",
            "scoring_status": "evaluated",
            "scoring_reason": None,
            "scoring_method": "reference_similarity",
        }

    model = load_nlp_model()
    scoring_method = "reference_similarity"
    if model is not None:
        try:
            response_embedding = model.encode(candidate_response, convert_to_tensor=True)
            rubric_embedding = model.encode(rubric, convert_to_tensor=True)
            similarity = util.cos_sim(response_embedding, rubric_embedding).item()
            score_percentage = round(max(0.0, similarity) * 100, 2)
        except Exception:
            score_percentage = _fallback_keyword_similarity(candidate_response, rubric)
            scoring_method = "keyword_reference_overlap"
    else:
        score_percentage = _fallback_keyword_similarity(candidate_response, rubric)
        scoring_method = "keyword_reference_overlap"

    return {
        "semantic_score": score_percentage,
        "match_level": "Reference alignment",
        "scoring_status": "evaluated",
        "scoring_reason": None,
        "scoring_method": scoring_method,
    }


def _fallback_keyword_similarity(candidate_response: str, rubric: str) -> float:
    """Return rubric-token coverage without an artificial baseline bonus."""
    response_words = set(re.findall(r"\w+", candidate_response.lower()))
    rubric_words = set(re.findall(r"\w+", rubric.lower()))
    if not rubric_words:
        return 0.0
    overlap = len(response_words.intersection(rubric_words))
    return round((overlap / len(rubric_words)) * 100, 2)
