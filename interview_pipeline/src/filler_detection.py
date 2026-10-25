"""
Context-Aware Filler Word Detection Module.

Identifies vocal fillers and hesitation markers in transcript data while distinguishing
ordinary lexical/grammatical uses of words like "like", "so", and "you know" using
surrounding linguistic context, punctuation, and word-level speech timing.

Supported categories:
- Unconditional vocalic fillers: "um", "uh", "er", "ah", "hmm", "mm", "mhm"
- Context-aware discourse/hesitation fillers:
  - "like" (discourse marker vs. verb / comparison / preposition)
  - "so" (discourse hesitation / stall vs. conjunction / intensifier)
  - "you know" (parenthetical hesitation vs. question / transitive verb)
"""
from typing import Dict, List, Tuple, Any, Optional
import re

# ---------------------------------------------------------------------------
# Lexical & Grammatical Dictionaries
# ---------------------------------------------------------------------------

# 1. Non-lexical vocalizations (always disfluencies/fillers)
VOCALIC_FILLERS = {"um", "uh", "er", "ah", "hmm", "mm", "mhm"}

# 2. Contextual indicators for "like"
LIKE_VERB_PREV = {
    "i", "we", "you", "they", "he", "she", "it",
    "would", "'d", "d", "could", "should", "might", "to",
    "do", "did", "does", "don't", "didn't", "doesn't"
}

LIKE_COMPARISON_PREV = {
    "technologies", "tools", "languages", "things", "platforms",
    "frameworks", "libraries", "modules", "systems", "patterns",
    "concepts", "algorithms", "companies", "skills", "topics",
    "projects", "areas", "fields", "applications", "services",
    "features", "methods", "functions", "classes", "data", "types",
    "something", "anything", "nothing", "someone", "anyone", "somewhere"
}

LIKE_PERCEPTION_VERBS = {
    "look", "looks", "looked", "looking",
    "sound", "sounds", "sounded", "sounding",
    "feel", "feels", "felt", "feeling",
    "seem", "seems", "seemed", "seeming",
    "taste", "tastes", "tasted", "smell", "smells", "smelled",
    "act", "acts", "acted", "acting",
    "be", "is", "am", "are", "was", "were", "been", "being"
}

LIKE_DISCOURSE_NEXT = {
    "really", "literally", "basically", "totally", "super",
    "honestly", "actually", "completely", "pretty", "kinda",
    "kind", "sorta", "sort", "definitely"
}

# 3. Contextual indicators for "so"
SO_DISQUALIFY_NEXT = {
    "that", "as", "much", "many", "few", "little", "far",
    "good", "bad", "well", "fast", "high", "low", "long", "large",
    "big", "small", "important", "difficult", "easy", "simple",
    "often", "close", "hard", "deep", "strong", "great", "nice",
    "clear", "early", "late", "hot", "cold", "heavy", "light"
}

SO_DISCOURSE_NEXT = {
    "basically", "yeah", "anyway"
}

# 4. Contextual indicators for "you know"
YOU_KNOW_DISQUALIFY_PREV = {
    "do", "did", "does", "if", "as", "would", "let", "lead",
    "make", "help", "to", "will", "can", "could", "should"
}

YOU_KNOW_DISQUALIFY_NEXT = {
    "the", "a", "an", "this", "that", "these", "those",
    "what", "which", "how", "who", "whom", "where", "when",
    "why", "if", "whether", "about"
}


# ---------------------------------------------------------------------------
# Helper Normalization & Timing Functions
# ---------------------------------------------------------------------------

def _extract_word_tokens(transcript_data: dict) -> List[Dict[str, Any]]:
    """
    Extracts a standardized list of word dictionaries from transcript data.
    Ensures safe handling of malformed records, missing timestamps, or fallback text.
    """
    raw_words = transcript_data.get("words", [])
    if raw_words:
        cleaned_list = []
        for w in raw_words:
            if isinstance(w, dict):
                cleaned_list.append({
                    "raw": str(w.get("word", "")),
                    "start": float(w["start"]) if w.get("start") is not None else None,
                    "end": float(w["end"]) if w.get("end") is not None else None,
                })
            elif isinstance(w, str):
                cleaned_list.append({"raw": w, "start": None, "end": None})
        if cleaned_list:
            return cleaned_list

    # Fallback to tokenizing transcript string if words list is empty
    transcript_text = transcript_data.get("transcript", "")
    if transcript_text:
        tokens = transcript_text.strip().split()
        return [{"raw": tok, "start": None, "end": None} for tok in tokens]

    return []


def _clean_token(raw_token: str) -> str:
    """Removes non-alphanumeric punctuation and lowercases the token."""
    return re.sub(r"[^\w\s']", "", raw_token).strip().lower()


def _has_trailing_comma(raw_token: str) -> bool:
    """Checks if raw token ends with a comma."""
    return raw_token.rstrip().endswith(",")


def _has_pause_or_punct(
    gap: Optional[float],
    has_punct: bool,
    threshold: float = 0.25
) -> bool:
    """Returns True if there is an acoustic pause or punctuation mark."""
    if has_punct:
        return True
    if gap is not None and gap >= threshold:
        return True
    return False


# ---------------------------------------------------------------------------
# Category-Specific Evaluators
# ---------------------------------------------------------------------------

def _evaluate_like(
    cleaned_words: List[str],
    raw_words: List[str],
    i: int,
    gap_before: Optional[float],
    gap_after: Optional[float]
) -> Tuple[bool, str, str]:
    """
    Evaluates 'like'.
    Returns: (is_definite_filler, confidence, rule_reason)
    """
    N = len(cleaned_words)
    prev_w = cleaned_words[i - 1] if i > 0 else ""
    next_w = cleaned_words[i + 1] if i + 1 < N else ""
    prev_raw = raw_words[i - 1] if i > 0 else ""
    curr_raw = raw_words[i]
    next_raw = raw_words[i + 1] if i + 1 < N else ""

    has_comma_before = _has_trailing_comma(prev_raw)
    has_comma_after = _has_trailing_comma(curr_raw)

    # 1. High-Confidence Affirmative Rules (Overrides weak lexical priors)
    # Repetition: "like like"
    if prev_w == "like" or next_w == "like":
        return (True, "definite", "repetition")

    # Paired with vocalic filler: "like um", "uh like"
    if prev_w in VOCALIC_FILLERS or next_w in VOCALIC_FILLERS:
        return (True, "definite", "paired_with_vocalic_filler")

    # Parenthetical with punctuation: ", like,"
    if has_comma_before and has_comma_after:
        return (True, "definite", "parenthetical_commas")

    # Followed by discourse adverb: "like really", "like basically"
    if next_w in LIKE_DISCOURSE_NEXT:
        return (True, "definite", "discourse_approximator_with_adverb")

    # 2. Strict Disqualification Rules (Lexical / Grammatical)
    if next_w == "to":
        return (False, "disqualified", "verb_infinitive_like_to")

    if next_w.endswith("ing") and len(next_w) > 4:
        return (False, "disqualified", "verb_gerund_complement")

    if prev_w in LIKE_VERB_PREV:
        return (False, "disqualified", "verb_preceded_by_subject_or_modal")

    if prev_w in LIKE_PERCEPTION_VERBS:
        return (False, "disqualified", "comparative_perception_verb")

    if prev_w in LIKE_COMPARISON_PREV:
        return (False, "disqualified", "exemplification_preposition")

    # Comparison / demonstrative object without pause: "like this", "like that"
    if next_w in {"this", "that", "these", "those"}:
        if not (has_comma_before or (gap_before and gap_before >= 0.25)):
            return (False, "disqualified", "demonstrative_comparison")

    # Prepositional comparison: "looks like a ...", "act like the ..."
    if next_w in {"a", "an", "the"}:
        if not (has_comma_before or has_comma_after or (gap_before and gap_before >= 0.25)):
            return (False, "disqualified", "prepositional_determiner_phrase")

    # 3. Acoustic Hesitation Rules
    # Acoustic hesitation: pause before AND after
    if (gap_before and gap_before >= 0.25) and (gap_after and gap_after >= 0.25):
        return (True, "definite", "isolated_by_pauses")

    # Pause after and isolated
    if has_comma_after or (gap_after and gap_after >= 0.35):
        if prev_w not in LIKE_VERB_PREV and prev_w not in LIKE_PERCEPTION_VERBS:
            return (True, "definite", "trailing_hesitation_pause")

    # 3. Default: Ambiguous (Conservative: do not falsely count as filler)
    return (False, "ambiguous", "unconfirmed_discourse_marker")


def _evaluate_so(
    cleaned_words: List[str],
    raw_words: List[str],
    i: int,
    gap_before: Optional[float],
    gap_after: Optional[float]
) -> Tuple[bool, str, str]:
    """
    Evaluates 'so'.
    Returns: (is_definite_filler, confidence, rule_reason)
    """
    N = len(cleaned_words)
    prev_w = cleaned_words[i - 1] if i > 0 else ""
    next_w = cleaned_words[i + 1] if i + 1 < N else ""
    curr_raw = raw_words[i]

    has_comma_after = _has_trailing_comma(curr_raw)

    # 1. Disqualification Rules
    if next_w in SO_DISQUALIFY_NEXT:
        return (False, "disqualified", "conjunction_or_degree_intensifier")

    # Idiom: "and so on", "if so", "or so"
    if prev_w in {"and", "or", "if", "even"} and (next_w in {"on", "forth"} or i == N - 1):
        return (False, "disqualified", "idiomatic_phrase")

    # 2. Affirmative Filler Rules
    # Repetition: "so so"
    if prev_w == "so" or next_w == "so":
        return (True, "definite", "repetition")

    # Paired with vocalic filler: "so um", "so uh"
    if next_w in VOCALIC_FILLERS or prev_w in VOCALIC_FILLERS:
        return (True, "definite", "paired_with_vocalic_filler")

    # Trailing stall at end of utterance: "... yeah so"
    if i == N - 1 and (prev_w == "yeah" or (gap_before and gap_before >= 0.25)):
        return (True, "definite", "trailing_stall")

    # Standalone conversational stall followed by a pause: "so ... [pause] ..."
    if has_comma_after or (gap_after and gap_after >= 0.40):
        return (True, "definite", "hesitation_with_pause")

    # Followed by discourse marker: "so basically", "so yeah"
    if next_w in SO_DISCOURSE_NEXT:
        return (True, "definite", "introductory_stall_with_discourse_marker")

    # 3. Default:
    # Coordinating conjunction ("A so B") or fluent question opener ("so shall we start?")
    # These are grammatical transitions or ambiguous discourse openers.
    return (False, "ambiguous", "grammatical_conjunction_or_fluent_opener")


def _evaluate_you_know(
    cleaned_words: List[str],
    raw_words: List[str],
    i: int,
    gap_before: Optional[float],
    gap_after: Optional[float]
) -> Tuple[bool, int, str, str]:
    """
    Evaluates 'you know' (single token or bigram).
    Returns: (is_definite_filler, tokens_consumed, confidence, rule_reason)
    """
    N = len(cleaned_words)
    w = cleaned_words[i]

    # Check whether single token or bigram
    if w == "you know":
        tokens_consumed = 1
        next_idx = i + 1
    elif w == "you" and i + 1 < N and cleaned_words[i + 1] == "know":
        tokens_consumed = 2
        next_idx = i + 2
    else:
        return (False, 0, "not_applicable", "not_you_know")

    prev_w = cleaned_words[i - 1] if i > 0 else ""
    next_w = cleaned_words[next_idx] if next_idx < N else ""
    prev_raw = raw_words[i - 1] if i > 0 else ""
    last_consumed_raw = raw_words[i + tokens_consumed - 1]

    has_comma_before = _has_trailing_comma(prev_raw)
    has_comma_after = _has_trailing_comma(last_consumed_raw)

    # 1. Disqualification Rules
    # Question / modal / auxiliary: "do you know", "as you know", "let you know"
    if prev_w in YOU_KNOW_DISQUALIFY_PREV:
        return (False, tokens_consumed, "disqualified", "interrogative_or_auxiliary_clause")

    # Transitive verb taking object or clause: "you know the difference", "you know that"
    if next_w in YOU_KNOW_DISQUALIFY_NEXT:
        return (False, tokens_consumed, "disqualified", "transitive_verb_with_object")

    # 2. Affirmative Filler Rules
    # Trailing discourse tag at end of utterance: "it was hard, you know."
    if next_idx >= N:
        return (True, tokens_consumed, "definite", "utterance_final_tag")

    # Parenthetical with punctuation: ", you know,"
    if has_comma_before and has_comma_after:
        return (True, tokens_consumed, "definite", "parenthetical_commas")

    # Paired with vocalic filler: "you know um", "like you know"
    if next_w in VOCALIC_FILLERS or prev_w in VOCALIC_FILLERS or prev_w == "like":
        return (True, tokens_consumed, "definite", "paired_with_filler")

    # Isolated by pauses
    if (gap_before and gap_before >= 0.25) or (gap_after and gap_after >= 0.25) or has_comma_after:
        return (True, tokens_consumed, "definite", "hesitation_with_pause")

    # Followed immediately by new subject pronoun without conjunction: "you know, we had to"
    if next_w in {"i", "we", "they", "it"}:
        return (True, tokens_consumed, "definite", "parenthetical_before_clause")

    # 3. Default: Ambiguous
    return (False, tokens_consumed, "ambiguous", "unconfirmed_parenthetical")


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def detect_filler_words(transcript_data: dict) -> dict:
    """
    Detects vocal filler words in transcript data using explainable context rules.

    Distinguishes genuine vocal disfluencies from ordinary grammatical/lexical
    uses of "like", "so", and "you know".

    Args:
        transcript_data: Dictionary containing:
            - 'chunk_id': Identifier string
            - 'transcript': Full transcript string
            - 'words': List of word dicts [{'word': str, 'start': float, 'end': float}]

    Returns:
        Dictionary with:
            - 'chunk_id': str
            - 'filler_count': int (count of definite vocal fillers)
            - 'filler_words': list of dicts [{'word': str, 'timestamp': float, 'confidence': str, 'rule': str}]
            - 'ambiguous_count': int
            - 'ambiguous_words': list of dicts
            - 'filler_breakdown': dict mapping category -> count
    """
    chunk_id = transcript_data.get("chunk_id", "unknown")
    token_records = _extract_word_tokens(transcript_data)

    if not token_records:
        return {
            "chunk_id": chunk_id,
            "filler_count": 0,
            "filler_words": [],
            "ambiguous_count": 0,
            "ambiguous_words": [],
            "filler_breakdown": {}
        }

    raw_words = [rec["raw"] for rec in token_records]
    cleaned_words = [_clean_token(rec["raw"]) for rec in token_records]
    N = len(token_records)

    filler_words: List[Dict[str, Any]] = []
    ambiguous_words: List[Dict[str, Any]] = []
    breakdown: Dict[str, int] = {}

    i = 0
    while i < N:
        rec = token_records[i]
        w = cleaned_words[i]
        timestamp = rec["start"] if rec["start"] is not None else 0.0

        # Compute timing gaps to adjacent words
        prev_end = token_records[i - 1]["end"] if i > 0 else None
        curr_start = rec["start"]
        curr_end = rec["end"]
        next_start = token_records[i + 1]["start"] if i + 1 < N else None

        gap_before = (curr_start - prev_end) if (curr_start is not None and prev_end is not None) else None
        gap_after = (next_start - curr_end) if (next_start is not None and curr_end is not None) else None

        # -------------------------------------------------------------------
        # 1. Unconditional Vocalic Fillers ("um", "uh", "er", "ah", "hmm")
        # -------------------------------------------------------------------
        if w in VOCALIC_FILLERS:
            detection = {
                "word": w,
                "timestamp": timestamp,
                "confidence": "definite",
                "rule": "unconditional_vocalic_filler"
            }
            filler_words.append(detection)
            breakdown[w] = breakdown.get(w, 0) + 1
            i += 1
            continue

        # -------------------------------------------------------------------
        # 2. Multiword "you know" (single token or bigram)
        # -------------------------------------------------------------------
        if w == "you know" or (w == "you" and i + 1 < N and cleaned_words[i + 1] == "know"):
            is_filler, tokens_consumed, confidence, rule = _evaluate_you_know(
                cleaned_words, raw_words, i, gap_before, gap_after
            )
            item = {
                "word": "you know",
                "timestamp": timestamp,
                "confidence": confidence,
                "rule": rule
            }
            if is_filler:
                filler_words.append(item)
                breakdown["you know"] = breakdown.get("you know", 0) + 1
            elif confidence == "ambiguous":
                ambiguous_words.append(item)

            i += tokens_consumed
            continue

        # -------------------------------------------------------------------
        # 3. Context-Aware "like"
        # -------------------------------------------------------------------
        if w == "like":
            is_filler, confidence, rule = _evaluate_like(
                cleaned_words, raw_words, i, gap_before, gap_after
            )
            item = {
                "word": "like",
                "timestamp": timestamp,
                "confidence": confidence,
                "rule": rule
            }
            if is_filler:
                filler_words.append(item)
                breakdown["like"] = breakdown.get("like", 0) + 1
            elif confidence == "ambiguous":
                ambiguous_words.append(item)

            i += 1
            continue

        # -------------------------------------------------------------------
        # 4. Context-Aware "so"
        # -------------------------------------------------------------------
        if w == "so":
            is_filler, confidence, rule = _evaluate_so(
                cleaned_words, raw_words, i, gap_before, gap_after
            )
            item = {
                "word": "so",
                "timestamp": timestamp,
                "confidence": confidence,
                "rule": rule
            }
            if is_filler:
                filler_words.append(item)
                breakdown["so"] = breakdown.get("so", 0) + 1
            elif confidence == "ambiguous":
                ambiguous_words.append(item)

            i += 1
            continue

        # Unmatched standard word
        i += 1

    return {
        "chunk_id": chunk_id,
        "filler_count": len(filler_words),
        "filler_words": filler_words,
        "ambiguous_count": len(ambiguous_words),
        "ambiguous_words": ambiguous_words,
        "filler_breakdown": breakdown
    }
