"""Final report aggregation module.

Aggregates chunk-level JSONs into a single authoritative final_report.json
and an interview_timeline.csv. Fixes previous data loss issues by including
NLP semantic scores and the whole-video visual summary.
"""
import json
import csv
from pathlib import Path

from interview_pipeline.src.chunking import _chunk_sort_key


def generate_final_report(
    outputs_dir: Path,
    reports_dir: Path,
    visual_summary: dict | None = None,
    stage_timings: dict | None = None,
    input_video_name: str = "unknown.mp4",
):
    """
    Reads all chunk JSONs, aggregates metrics, and exports a final JSON and CSV.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    json_files = sorted(outputs_dir.glob("chunk_*.json"), key=_chunk_sort_key)
    
    if not json_files:
        print("[WARNING] No JSON outputs found to aggregate.")
        return

    full_transcript = []
    total_fillers = 0
    total_long_pauses = 0
    total_silence_sec = 0.0
    total_words_count = 0
    total_chunk_duration_sec = 0.0
    total_active_speech_sec = 0.0

    wpm_list = []
    visual_scores = []
    semantic_scores = []
    semantic_statuses = []
    semantic_reasons = []
    
    csv_rows = []

    print(f"\n--- STAGE 6: Generating Aggregated Reports ---")
    
    for file_path in json_files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            chunk_id = data.get("chunk_id", "unknown")
            transcript = data.get("transcript", "").strip()
            
            if transcript:
                full_transcript.append(transcript)

            # Word counting (prefer word timestamps list, fallback to tokenized transcript)
            words_in_chunk = len(data.get("words", []))
            if words_in_chunk == 0 and transcript:
                words_in_chunk = len(transcript.split())
            total_words_count += words_in_chunk
                
            # Speech Analytics
            speech_analysis = data.get("speech_analysis", {})
            filler_count = speech_analysis.get("filler_count", 0)
            pauses = speech_analysis.get("long_pauses_count", 0)
            silence = speech_analysis.get("total_silence_sec", 0.0)
            wpm = speech_analysis.get("words_per_minute", 0.0)

            # Actual chunk duration
            chunk_dur = speech_analysis.get("actual_chunk_duration_sec")
            if chunk_dur is None or chunk_dur <= 0:
                chunk_dur = 10.0
            total_chunk_duration_sec += chunk_dur

            # Active speech duration
            active_dur = speech_analysis.get("active_speech_duration_sec")
            if active_dur is None:
                active_dur = max(0.0, chunk_dur - silence) if words_in_chunk > 0 else 0.0
            total_active_speech_sec += active_dur
            
            # Visual Analytics (Face Visibility)
            visual_analysis = data.get("visual_analysis", {})
            visual_vis = visual_analysis.get("face_visibility_pct", "N/A")
            if isinstance(visual_vis, (int, float)):
                visual_scores.append(visual_vis)

            # NLP / Content Analytics
            content_analysis = data.get("content_analysis", {})
            semantic_score = content_analysis.get("semantic_score")
            scoring_status = content_analysis.get("scoring_status")
            scoring_reason = content_analysis.get("scoring_reason")
            # Reports created before Phase 6.4 lack status metadata. Preserve
            # their numeric values for compatibility, but mark them as legacy
            # similarity rather than validated answer evaluation.
            is_legacy_score = scoring_status is None and isinstance(semantic_score, (int, float))
            if scoring_status == "evaluated" and isinstance(semantic_score, (int, float)):
                semantic_scores.append(semantic_score)
                semantic_statuses.append("evaluated")
            elif is_legacy_score:
                semantic_scores.append(semantic_score)
                semantic_statuses.append("legacy_similarity")
            elif scoring_status == "not_evaluated":
                semantic_statuses.append("not_evaluated")
                if scoring_reason:
                    semantic_reasons.append(str(scoring_reason))

            # Aggregate totals
            total_fillers += filler_count
            total_long_pauses += pauses
            total_silence_sec += silence
            if wpm > 0:
                wpm_list.append(wpm)
                
            # Add to CSV row
            csv_rows.append({
                "Chunk_ID": chunk_id,
                "Start_Seconds": data.get("chunk_start_sec", ""),
                "End_Seconds": data.get("chunk_end_sec", ""),
                "Transcript": transcript,
                "Filler_Words": filler_count,
                "Long_Pauses": pauses,
                "Silence_Seconds": silence,
                "WPM": wpm,
                "Face_Visibility": f"{visual_vis}%" if str(visual_vis) != "N/A" else "N/A",
                "Visual_Stability": f"{visual_vis}%" if str(visual_vis) != "N/A" else "N/A",
                "Semantic_Score": f"{semantic_score}%" if isinstance(semantic_score, (int, float)) else "N/A",
                "Semantic_Status": scoring_status or ("legacy_similarity" if is_legacy_score else "not_evaluated"),
                "Semantic_Reason": scoring_reason or "",
            })

    # Calculate overall averages
    average_active_chunk_wpm = round(sum(wpm_list) / len(wpm_list), 1) if wpm_list else 0.0
    overall_video_wpm = (
        round(total_words_count / (total_chunk_duration_sec / 60.0), 1)
        if total_chunk_duration_sec > 0
        else 0.0
    )
    active_speech_wpm = (
        round(total_words_count / (total_active_speech_sec / 60.0), 1)
        if total_active_speech_sec > 0
        else None
    )

    average_face_visibility = (
        round(sum(visual_scores) / len(visual_scores), 1) if visual_scores else None
    )
    average_semantic = round(sum(semantic_scores) / len(semantic_scores), 1) if semantic_scores else None
    if "evaluated" in semantic_statuses:
        semantic_evaluation = {"status": "evaluated", "reason": None}
    elif "legacy_similarity" in semantic_statuses:
        semantic_evaluation = {
            "status": "legacy_similarity",
            "reason": "Historical similarity score; rubric and response pairing are unknown.",
        }
    else:
        semantic_evaluation = {
            "status": "not_evaluated",
            "reason": semantic_reasons[0] if semantic_reasons else "No rubric provided",
        }
    
    # 1. Create Final Aggregated JSON (One authoritative schema)
    final_summary = {
        "metadata": {
            "input_video": input_video_name,
            "total_chunks_processed": len(json_files),
            "total_recognized_words": total_words_count,
            "total_chunk_duration_seconds": round(total_chunk_duration_sec, 2),
            "total_active_speech_seconds": round(total_active_speech_sec, 2),
            "stage_timings_seconds": stage_timings or {}
        },
        "overall_metrics": {
            "total_filler_words": total_fillers,
            "total_long_pauses": total_long_pauses,
            "total_silence_seconds": round(total_silence_sec, 2),
            "average_active_chunk_wpm": average_active_chunk_wpm,
            "overall_video_wpm": overall_video_wpm,
            "active_speech_wpm": active_speech_wpm,
            "average_words_per_minute": average_active_chunk_wpm,  # Deprecated backward-compatible alias
            "average_face_visibility_pct": average_face_visibility,
            "average_visual_stability": average_face_visibility,  # Deprecated backward-compatible alias
            "average_semantic_score": average_semantic,
            "semantic_evaluation": semantic_evaluation,
        },
        "visual_summary_whole_video": visual_summary or {},
        "full_interview_transcript": " ".join(full_transcript)
    }
    
    # Use one single authoritative report file name to avoid overlap/confusion.
    json_report_path = reports_dir / "final_report.json"
    with open(json_report_path, "w", encoding="utf-8") as f:
        json.dump(final_summary, f, indent=4)
        
    # 2. Create CSV Export
    csv_report_path = reports_dir / "interview_timeline.csv"
    csv_headers = [
        "Chunk_ID", "Transcript", "Filler_Words", "Long_Pauses", 
        "Silence_Seconds", "WPM", "Face_Visibility", "Visual_Stability", "Semantic_Score",
        "Semantic_Status", "Semantic_Reason", "Start_Seconds", "End_Seconds"
    ]
    
    with open(csv_report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"  -> Aggregated JSON saved to: {json_report_path}")
    print(f"  -> CSV Export saved to: {csv_report_path}")
