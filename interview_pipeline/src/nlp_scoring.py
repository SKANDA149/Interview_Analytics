# --- START OF FILE src/nlp_scoring.py ---
import re

try:
    from sentence_transformers import SentenceTransformer, util
    HAS_ST = True
except ImportError:
    HAS_ST = False

# Cache the model so it only loads into RAM once!
_nlp_model_cache = None

def load_nlp_model():
    global _nlp_model_cache
    if not HAS_ST:
        return None
    if _nlp_model_cache is None:
        try:
            print("  -> [INFO] Loading MiniLM NLP Model into memory (offline)...")
            _nlp_model_cache = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception:
            _nlp_model_cache = False
    return _nlp_model_cache if _nlp_model_cache is not False else None

def evaluate_technical_answer(transcript_text: str, ideal_answer: str) -> dict:
    """
    Compares the candidate's transcript against an ideal answer key.
    Returns a semantic similarity score (0 to 100%).
    """
    if not transcript_text or transcript_text.strip() == "":
        return {"semantic_score": 0.0, "match_level": "No Answer"}
        
    model = load_nlp_model()
    
    if model is not None:
        try:
            candidate_embedding = model.encode(transcript_text, convert_to_tensor=True)
            ideal_embedding = model.encode(ideal_answer, convert_to_tensor=True)
            similarity = util.cos_sim(candidate_embedding, ideal_embedding).item()
            score_percentage = round(max(0.0, similarity) * 100, 2)
        except Exception:
            score_percentage = _fallback_keyword_similarity(transcript_text, ideal_answer)
    else:
        score_percentage = _fallback_keyword_similarity(transcript_text, ideal_answer)
    
    # Assign a qualitative label
    if score_percentage >= 75:
        match_level = "Excellent"
    elif score_percentage >= 50:
        match_level = "Acceptable"
    else:
        match_level = "Poor"
        
    return {
        "semantic_score": score_percentage,
        "match_level": match_level
    }

def _fallback_keyword_similarity(transcript_text: str, ideal_answer: str) -> float:
    t_words = set(re.findall(r'\w+', transcript_text.lower()))
    i_words = set(re.findall(r'\w+', ideal_answer.lower()))
    if not i_words:
        return 0.0
    overlap = len(t_words.intersection(i_words))
    return round(min(100.0, (overlap / len(i_words)) * 100 + 35.0), 2)