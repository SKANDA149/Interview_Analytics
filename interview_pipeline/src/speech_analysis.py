# --- START OF FILE speech_analysis.py ---

def analyze_speech_fluency(transcript_data: dict, chunk_duration_sec: float = 10.0) -> dict:
    """
    Analyzes Vosk transcript timestamps to calculate pacing, silence, and hesitation.
    """
    words = transcript_data.get("words", [])
    word_count = len(words)
    
    # 1. Handle empty chunks (total silence)
    if word_count == 0:
        return {
            "words_per_minute": 0.0,
            "total_silence_sec": chunk_duration_sec,
            "silence_ratio_pct": 100.0,
            "long_pauses_count": 0
        }

    total_silence_duration = 0.0
    long_pauses_count = 0
    
    # 2. Calculate Silence Between Words
    for i in range(word_count - 1):
        current_word_end = words[i].get("end", 0.0)
        next_word_start = words[i+1].get("start", 0.0)
        
        # Gap between the end of one word and start of the next
        gap = next_word_start - current_word_end
        
        if gap > 0:
            total_silence_duration += gap
            
        # If there is a silence gap of more than 1.5 seconds, flag it as a "Hesitation/Long Pause"
        if gap >= 1.5:
            long_pauses_count += 1

    # 3. Add silence at the beginning and end of the chunk
    first_word_start = words[0].get("start", 0.0)
    last_word_end = words[-1].get("end", chunk_duration_sec)
    
    total_silence_duration += first_word_start  # Silence before the first word
    total_silence_duration += max(0, chunk_duration_sec - last_word_end) # Silence after last word

    # 4. Calculate Pacing (Words Per Minute)
    # Formula: (Total Words / Duration in Seconds) * 60
    wpm = (word_count / chunk_duration_sec) * 60

    # 5. Calculate Silence Ratio
    silence_ratio = (total_silence_duration / chunk_duration_sec) * 100

    return {
        "words_per_minute": round(wpm, 1),
        "total_silence_sec": round(total_silence_duration, 2),
        "silence_ratio_pct": round(silence_ratio, 1),
        "long_pauses_count": long_pauses_count
    }