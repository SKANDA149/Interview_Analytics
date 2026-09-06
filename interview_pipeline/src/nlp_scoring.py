# --- START OF FILE src/nlp_scoring.py ---
import re

try:
    from sentence_transformers import SentenceTransformer, util
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

# Cache the model so it only loads into RAM once!
_nlp_model_cache = None

def load_nlp_model():
    global _nlp_model_cache
    if not HAS_SENTENCE_TRANSFORMERS:
        return None
    if _nlp_model_cache is None:
        try:
            print("  -> [INFO] Loading MiniLM NLP Model into memory (offline)...")
            _nlp_model_cache = SentenceTransformer('all-MiniLM-L6-v2', local_files_only=True)
        except Exception as e:
            print(f"  -> [WARNING] Could not load SentenceTransformer model: {e}")
            _nlp_model_cache = False
    return _nlp_model_cache if _nlp_model_cache is not False else None

def evaluate_technical_answer(transcript_text: str, config: dict) -> dict:
    """
    Evaluates the candidate's transcript against a structured NLP config.
    Returns separated metrics: semantic similarity, requirement coverage, and keyword coverage.
    """
    if not config:
        config = {}
    job_desc = config.get("job_description", "")
    quals = config.get("qualifications", "")
    resps = config.get("responsibilities", "")
    custom = config.get("custom_details", "")
    key_skills = config.get("key_skills", [])
    if isinstance(key_skills, str):
        key_skills = [s.strip() for s in key_skills.split(",") if s.strip()]
        
    weights = config.get("weights", {"semantic": 0.4, "requirements": 0.3, "keywords": 0.3})

    if not transcript_text or transcript_text.strip() == "":
        return {
            "semantic_score": 0.0, "requirement_score": 0.0, 
            "keyword_score": 0.0, "overall_score": 0.0, "match_level": "No Answer"
        }
        
    model = load_nlp_model()
    transcript_emb = model.encode(transcript_text, convert_to_tensor=True) if model else None

    def get_sim(text: str) -> float:
        if not text.strip(): 
            return 0.0
        if model is None or transcript_emb is None: 
            return _fallback_keyword_similarity(transcript_text, text)
        emb = model.encode(text, convert_to_tensor=True)
        return round(max(0.0, util.cos_sim(transcript_emb, emb).item()) * 100, 2)

    semantic_text = f"{job_desc} {custom}".strip()
    semantic_score = get_sim(semantic_text)

    # Requirement Coverage (Per Requirement)
    req_score = 0.0
    req_list = []
    if isinstance(quals, list): req_list.extend(quals)
    elif quals.strip(): req_list.extend([r.strip() for r in quals.split('\n') if r.strip()])
    
    if isinstance(resps, list): req_list.extend(resps)
    elif resps.strip(): req_list.extend([r.strip() for r in resps.split('\n') if r.strip()])

    if req_list:
        individual_scores = [get_sim(req) for req in req_list]
        req_score = round(sum(individual_scores) / len(individual_scores), 2)

    # Keyword Coverage (Explicitly Lexical)
    keyword_score = 0.0
    if key_skills:
        t_lower = transcript_text.lower()
        found = 0
        for skill in key_skills:
            # Word boundary matching for skills
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, t_lower):
                found += 1
        keyword_score = round((found / len(key_skills)) * 100, 2)

    # Configurable Overall Aggregation
    active_weights = []
    scores = []
    if semantic_text:
        active_weights.append(weights.get("semantic", 0.4))
        scores.append(semantic_score)
    if req_list:
        active_weights.append(weights.get("requirements", 0.3))
        scores.append(req_score)
    if key_skills:
        active_weights.append(weights.get("keywords", 0.3))
        scores.append(keyword_score)

    if sum(active_weights) > 0:
        overall_score = round(sum(w * s for w, s in zip(active_weights, scores)) / sum(active_weights), 2)
    else:
        overall_score = 0.0

    if overall_score >= 75:
        match_level = "Excellent"
    elif overall_score >= 50:
        match_level = "Acceptable"
    else:
        match_level = "Needs Improvement"
        
    return {
        "semantic_score": semantic_score,
        "requirement_score": req_score,
        "keyword_score": keyword_score,
        "overall_score": overall_score,
        "match_level": match_level
    }

def _fallback_keyword_similarity(transcript_text: str, target_text: str) -> float:
    """Fallback word-overlap similarity when sentence-transformers is offline or missing."""
    t_words = set(re.findall(r'\w+', transcript_text.lower()))
    i_words = set(re.findall(r'\w+', target_text.lower()))
    if not i_words:
        return 0.0
    overlap = len(t_words.intersection(i_words))
    return round(min(100.0, (overlap / len(i_words)) * 100 + 35.0), 2)