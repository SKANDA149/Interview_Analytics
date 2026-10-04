# --- START OF FILE report_generator.py ---
import json
import csv
from pathlib import Path

def generate_aggregated_report(outputs_dir: Path, reports_dir: Path):
    """
    Reads all chunk JSONs, aggregates metrics, and exports a final JSON and CSV.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    json_files = sorted(outputs_dir.glob("chunk_*.json"))
    
    if not json_files:
        print("[WARNING] No JSON outputs found to aggregate.")
        return

    full_transcript = []
    total_fillers = 0
    total_long_pauses = 0
    total_silence_sec = 0.0
    wpm_list = []
    visual_scores = []
    
    csv_rows = []

    print(f"\n--- STAGE 4: Generating Aggregated Reports ---")
    
    for file_path in json_files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            chunk_id = data.get("chunk_id", "unknown")
            transcript = data.get("transcript", "").strip()
            
            if transcript:
                full_transcript.append(transcript)
                
            # Speech Analytics
            speech_analysis = data.get("speech_analysis", {})
            filler_count = speech_analysis.get("filler_count", 0)
            pauses = speech_analysis.get("long_pauses_count", 0)
            silence = speech_analysis.get("total_silence_sec", 0.0)
            wpm = speech_analysis.get("words_per_minute", 0.0)
            
            # Visual Analytics
            visual_analysis = data.get("visual_analysis", {})
            visual_vis = visual_analysis.get("face_visibility_pct", "N/A")
            # "N/A" means no CANDIDATE speech (and therefore no visual samples) in
            # this chunk's window - exclude it from the numeric average but still
            # surface it as-is in the per-chunk CSV row below.
            if isinstance(visual_vis, (int, float)):
                visual_scores.append(visual_vis)

            # Aggregate totals
            total_fillers += filler_count
            total_long_pauses += pauses
            total_silence_sec += silence
            if wpm > 0:
                wpm_list.append(wpm)
                
            # Add to CSV row
            csv_rows.append({
                "Chunk_ID": chunk_id,
                "Transcript": transcript,
                "Filler_Words": filler_count,
                "Long_Pauses": pauses,
                "Silence_Seconds": silence,
                "WPM": wpm,
                "Visual_Stability": f"{visual_vis}%"
            })

    # Calculate overall averages
    average_wpm = round(sum(wpm_list) / len(wpm_list), 1) if wpm_list else 0.0
    average_visual = round(sum(visual_scores) / len(visual_scores), 1) if visual_scores else 100.0
    
    # 1. Create Final Aggregated JSON
    final_summary = {
        "overall_metrics": {
            "total_chunks_processed": len(json_files),
            "total_filler_words": total_fillers,
            "total_long_pauses": total_long_pauses,
            "total_silence_seconds": round(total_silence_sec, 2),
            "average_words_per_minute": average_wpm,
            "average_visual_stability": average_visual
        },
        "full_interview_transcript": " ".join(full_transcript)
    }
    
    json_report_path = reports_dir / "final_aggregated_report.json"
    with open(json_report_path, "w", encoding="utf-8") as f:
        json.dump(final_summary, f, indent=4)
        
    # 2. Create CSV Export
    csv_report_path = reports_dir / "interview_timeline.csv"
    csv_headers = ["Chunk_ID", "Transcript", "Filler_Words", "Long_Pauses", "Silence_Seconds", "WPM", "Visual_Stability"]
    
    with open(csv_report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"  -> Aggregated JSON saved to: {json_report_path}")
    print(f"  -> CSV Export saved to: {csv_report_path}")