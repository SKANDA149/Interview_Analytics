# --- START OF FILE report_generator.py ---
import json
import csv
from pathlib import Path


def generate_final_report(report_data: dict, reports_dir: Path) -> None:
    """
    Write the final pipeline report to JSON and CSV.

    Args:
        report_data: Complete pipeline output dict containing processing_metadata,
                     diarization_summary, candidate_metrics, transcripts, and timeline.
        reports_dir: Directory for output files.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write final JSON report
    json_path = reports_dir / "final_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=4)
    print(f"[REPORT] Final JSON report saved: {json_path}")

    # 2. Write backward-compatible aggregated report (for dashboard)
    aggregated = _build_aggregated_report(report_data)
    agg_path = reports_dir / "final_aggregated_report.json"
    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump(aggregated, f, indent=4)

    # 3. Write timeline CSV
    timeline = report_data.get("timeline", [])
    csv_path = reports_dir / "interview_timeline.csv"
    csv_headers = [
        "Chunk_ID", "Start_Time", "End_Time", "Transcript",
        "Filler_Words", "Long_Pauses", "Silence_Seconds", "WPM",
        "Face_Visibility"
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        for entry in timeline:
            writer.writerow({
                "Chunk_ID": entry.get("chunk_id", ""),
                "Start_Time": entry.get("start_time", 0),
                "End_Time": entry.get("end_time", 0),
                "Transcript": entry.get("candidate_transcript", ""),
                "Filler_Words": entry.get("filler_words", 0),
                "Long_Pauses": entry.get("long_pauses", 0),
                "Silence_Seconds": entry.get("silence_sec", 0),
                "WPM": entry.get("wpm", 0),
                "Face_Visibility": entry.get("face_visibility_pct", 0)
            })

    print(f"[REPORT] Timeline CSV saved: {csv_path}")

    # 4. Write speaker-labelled transcript as a readable text file
    speaker_transcript = report_data.get("transcripts", {}).get("speaker_labelled_transcript", [])
    if speaker_transcript:
        txt_path = reports_dir / "speaker_transcript.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            for turn in speaker_transcript:
                speaker = turn.get("speaker", "UNKNOWN")
                start = turn.get("start", 0.0)
                end = turn.get("end", 0.0)
                text = turn.get("text", "")
                f.write(f"[{start:.1f}s - {end:.1f}s] {speaker}:\n  {text}\n\n")
        print(f"[REPORT] Speaker transcript saved: {txt_path}")


def _build_aggregated_report(report_data: dict) -> dict:
    """
    Build the backward-compatible aggregated report for the existing dashboard.
    Maps the new report structure to the old overall_metrics format.
    """
    speech = report_data.get("candidate_metrics", {}).get("speech", {})
    nlp = report_data.get("candidate_metrics", {}).get("nlp", {})

    return {
        "overall_metrics": {
            "total_chunks_processed": report_data.get("processing_metadata", {}).get("total_chunks", 0),
            "total_filler_words": speech.get("total_filler_words", 0),
            "total_long_pauses": speech.get("total_long_pauses", 0),
            "total_silence_seconds": speech.get("total_silence_sec", 0),
            "average_words_per_minute": speech.get("words_per_minute", 0),
            "semantic_score": nlp.get("overall_score", 0),
            "match_level": nlp.get("match_level", "N/A")
        },
        "full_interview_transcript": report_data.get("transcripts", {}).get("candidate_only_transcript", "")
    }


# Legacy function kept for backward compatibility
def generate_aggregated_report(outputs_dir: Path, reports_dir: Path) -> None:
    """
    Legacy report generator. Reads per-chunk JSONs and produces aggregated output.
    Retained for backward compatibility but the main pipeline now uses generate_final_report().
    """
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(outputs_dir.glob("chunk_*.json"))
    if not json_files:
        print("[REPORT] No chunk JSON outputs found.")
        return

    full_transcript = []
    total_fillers = 0
    total_long_pauses = 0
    total_silence_sec = 0.0
    wpm_list = []
    csv_rows = []

    for file_path in json_files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

            chunk_id = data.get("chunk_id", "unknown")
            transcript = data.get("candidate_transcript", data.get("transcript", "")).strip()

            if transcript:
                full_transcript.append(transcript)

            filler_count = data.get("filler_words", data.get("speech_analysis", {}).get("filler_count", 0))
            pauses = data.get("long_pauses", data.get("speech_analysis", {}).get("long_pauses_count", 0))
            silence = data.get("silence_sec", data.get("speech_analysis", {}).get("total_silence_sec", 0.0))
            wpm = data.get("wpm", data.get("speech_analysis", {}).get("words_per_minute", 0.0))

            total_fillers += filler_count
            total_long_pauses += pauses
            total_silence_sec += silence
            if wpm > 0:
                wpm_list.append(wpm)

            csv_rows.append({
                "Chunk_ID": chunk_id,
                "Transcript": transcript,
                "Filler_Words": filler_count,
                "Long_Pauses": pauses,
                "Silence_Seconds": silence,
                "WPM": wpm
            })

    average_wpm = round(sum(wpm_list) / len(wpm_list), 1) if wpm_list else 0.0

    final_summary = {
        "overall_metrics": {
            "total_chunks_processed": len(json_files),
            "total_filler_words": total_fillers,
            "total_long_pauses": total_long_pauses,
            "total_silence_seconds": round(total_silence_sec, 2),
            "average_words_per_minute": average_wpm
        },
        "full_interview_transcript": " ".join(full_transcript)
    }

    json_report_path = reports_dir / "final_aggregated_report.json"
    with open(json_report_path, "w", encoding="utf-8") as f:
        json.dump(final_summary, f, indent=4)

    csv_report_path = reports_dir / "interview_timeline.csv"
    csv_headers = ["Chunk_ID", "Transcript", "Filler_Words", "Long_Pauses", "Silence_Seconds", "WPM"]

    with open(csv_report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"[REPORT] Aggregated JSON: {json_report_path}")
    print(f"[REPORT] Timeline CSV: {csv_report_path}")