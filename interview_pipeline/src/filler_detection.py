def detect_filler_words(transcript_data: dict) -> dict:
    """
    Detects common filler words in the transcript data.
    Common filler words: um, uh, like, you know, so.
    """
    filler_set = {"um", "uh", "like", "so"}
    
    words = transcript_data.get("words", [])
    chunk_id = transcript_data.get("chunk_id", "unknown")
    
    filler_words = []
    
    i = 0
    while i < len(words):
        word_info = words[i]
        w = word_info.get("word", "").strip().lower()
        
        if w == "you know":
            filler_words.append({
                "word": "you know",
                "timestamp": word_info.get("start", 0.0)
            })
            i += 1
            continue
            
        # Check for bigram "you know"
        if w == "you" and i + 1 < len(words):
            next_w = words[i+1].get("word", "").strip().lower()
            if next_w == "know":
                filler_words.append({
                    "word": "you know",
                    "timestamp": word_info.get("start", 0.0)
                })
                i += 2
                continue
                
        if w in filler_set:
            filler_words.append({
                "word": w,
                "timestamp": word_info.get("start", 0.0)
            })
            
        i += 1
        
    return {
        "chunk_id": chunk_id,
        "filler_count": len(filler_words),
        "filler_words": filler_words
    }
