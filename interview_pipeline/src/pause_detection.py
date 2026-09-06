# --- START OF FILE pause_detection.py ---

def detect_pauses(transcript_data: dict) -> dict:
    """
    Detects and classifies pauses between spoken words using
    word-level timestamps from the STT output.

    For every consecutive pair of words, calculates:
        pause_duration = next_word.start - current_word.end

    Classification:
        0.5 - 1.5 seconds  →  Short Pause
        > 1.5 seconds      →  Long Pause

    Gaps under 0.5 seconds are considered natural speech gaps
    and are ignored.

    Args:
        transcript_data: The STT output dict containing 'words' list,
                         where each word has 'word', 'start', and 'end' keys.

    Returns:
        dict with keys:
            pause_count     (int)   - Total number of detected pauses
            short_pauses    (int)   - Count of pauses between 0.5 and 1.5 seconds
            long_pauses     (int)   - Count of pauses over 1.5 seconds
            longest_pause   (float) - Duration of the longest pause in seconds
            average_pause   (float) - Average duration across all detected pauses
            pauses          (list)  - Detailed list of each pause with context
    """
    words = transcript_data.get("words", [])

    pauses = []

    # Walk through consecutive word pairs and measure the gap
    for i in range(len(words) - 1):
        current_word = words[i]
        next_word = words[i + 1]

        current_end = current_word.get("end", 0.0)
        next_start = next_word.get("start", 0.0)

        # Calculate the silence gap between the two words
        gap = next_start - current_end

        # Ignore negative values (overlapping timestamps) and
        # gaps under 0.5 seconds (natural speech rhythm)
        if gap < 0.5:
            continue

        # Classify the pause by duration
        if gap > 1.5:
            pause_type = "long"
        else:
            pause_type = "short"

        pauses.append({
            "start_after": current_word.get("word", ""),
            "duration": round(gap, 2),
            "type": pause_type
        })

    # Compute summary statistics
    pause_count = len(pauses)
    short_pauses = sum(1 for p in pauses if p["type"] == "short")
    long_pauses = sum(1 for p in pauses if p["type"] == "long")

    if pause_count > 0:
        durations = [p["duration"] for p in pauses]
        longest_pause = max(durations)
        average_pause = round(sum(durations) / pause_count, 2)
    else:
        longest_pause = 0.0
        average_pause = 0.0

    return {
        "pause_count": pause_count,
        "short_pauses": short_pauses,
        "long_pauses": long_pauses,
        "longest_pause": longest_pause,
        "average_pause": average_pause,
        "pauses": pauses
    }
