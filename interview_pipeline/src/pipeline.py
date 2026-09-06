from pathlib import Path
import json
import time
import sys

try:
    from .chunking import split_video_into_chunks
    from .audio_extract import extract_audio, extract_full_audio
    from .stt import transcribe_full_audio, unload_whisper_model
    from .vad import run_vad
    from .diarization import run_diarization, generate_rttm, save_segments, load_segments
    from .speaker_roles import assign_speaker_roles
    from .speaker_alignment import align_words_to_speakers, build_speaker_turns, extract_candidate_data
    from .filler_detection import detect_filler_words
    from .pause_detection import detect_pauses
    from .speech_analysis import analyze_speech_fluency
    from .report_generator import generate_final_report
    from .nlp_scoring import evaluate_technical_answer
    from .visual_analytics import analyze_video_visuals
except ImportError:
    from interview_pipeline.src.chunking import split_video_into_chunks
    from interview_pipeline.src.audio_extract import extract_audio, extract_full_audio
    from interview_pipeline.src.stt import transcribe_full_audio, unload_whisper_model
    from interview_pipeline.src.vad import run_vad
    from interview_pipeline.src.diarization import run_diarization, generate_rttm, save_segments, load_segments
    from interview_pipeline.src.speaker_roles import assign_speaker_roles
    from interview_pipeline.src.speaker_alignment import align_words_to_speakers, build_speaker_turns, extract_candidate_data
    from interview_pipeline.src.filler_detection import detect_filler_words
    from interview_pipeline.src.pause_detection import detect_pauses
    from interview_pipeline.src.speech_analysis import analyze_speech_fluency
    from interview_pipeline.src.report_generator import generate_final_report
    from interview_pipeline.src.nlp_scoring import evaluate_technical_answer
    from interview_pipeline.src.visual_analytics import analyze_video_visuals


def _get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    import subprocess
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
            capture_output=True, text=True, check=True
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def run_pipeline(force_reprocess: bool = False,
                 input_video_path: str = "data/input/sample.mp4",
                 chunk_duration: int = 10,
                 nlp_config: dict = None,
                 n_speakers: int = 2):
    """
    Production pipeline for Edge-Based Interview Analytics.

    Sequential stages:
        1. Video Ingestion → 2. Chunking → 3. Full Audio Extraction →
        4. VAD → 5. Diarization → 6. Speaker Roles → 7. Transcription →
        8. Word-Speaker Alignment → 9. Candidate Extraction →
        10. Speech Analysis → 11. NLP Scoring → 12. Visual Analysis →
        13. Aggregation → 14. Report Generation
    """
    print("==================================================")
    print("[PIPELINE] Starting Edge-Based Interview Processing")
    print("==================================================")
    pipeline_start = time.time()
    stage_timings = {}

    # --- Paths ---
    input_video = Path(input_video_path)
    chunks_dir = Path("data/chunks")
    audio_dir = Path("data/audio")
    outputs_dir = Path("data/outputs")
    reports_dir = Path("data/reports")
    diarization_dir = Path("data/diarization")
    wespeaker_model = Path("models/wespeaker/voxceleb_resnet34_LM.onnx")
    identity_file = Path("data/.cache_identity.json")

    # ================================================================
    # CACHE INVALIDATION LOGIC
    # ================================================================
    import shutil
    
    def _get_video_identity(vp: Path) -> dict:
        if not vp.exists(): return None
        stat = vp.stat()
        return {"path": str(vp.absolute()), "size": stat.st_size, "mtime": stat.st_mtime}

    current_identity = _get_video_identity(input_video)
    
    if not force_reprocess and identity_file.exists():
        try:
            with open(identity_file, "r") as f:
                cached_identity = json.load(f)
            if cached_identity != current_identity:
                print(f"[PIPELINE] Video identity changed from {cached_identity.get('path')} to {current_identity.get('path')}. Forcing re-process.")
                force_reprocess = True
        except Exception:
            force_reprocess = True
    elif not force_reprocess and not identity_file.exists():
        force_reprocess = True

    if force_reprocess:
        print("[PIPELINE] Clearing old cache directories...")
        for d in [chunks_dir, audio_dir, outputs_dir, reports_dir, diarization_dir]:
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
                
    for d in [chunks_dir, audio_dir, outputs_dir, reports_dir, diarization_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # ================================================================
    # STAGE 1: Video Ingestion & Validation
    # ================================================================
    print("\n--- STAGE 1: Video Ingestion ---")
    t0 = time.time()

    if not input_video.exists():
        print(f"[PIPELINE] ERROR: Input video not found: {input_video}")
        return

    video_duration = _get_video_duration(input_video)
    print(f"[PIPELINE] Input: {input_video} ({video_duration:.1f}s)")
    stage_timings["ingestion"] = round(time.time() - t0, 2)

    # ================================================================
    # STAGE 2: Video Chunking
    # ================================================================
    print("\n--- STAGE 2: Video Chunking ---")
    t0 = time.time()

    existing_chunks = sorted(chunks_dir.glob("chunk_*.mp4"), key=lambda x: x.name)
    if existing_chunks and not force_reprocess:
        print(f"[PIPELINE] Found {len(existing_chunks)} cached chunks. Skipping.")
        chunks = existing_chunks
    else:
        chunks = split_video_into_chunks(
            input_path=input_video,
            output_dir=chunks_dir,
            chunk_duration=chunk_duration
        )
    stage_timings["chunking"] = round(time.time() - t0, 2)
    print(f"[PIPELINE] {len(chunks)} chunks ({chunk_duration}s each)")

    # ================================================================
    # STAGE 3: Full Audio Extraction
    # ================================================================
    print("\n--- STAGE 3: Full Audio Extraction ---")
    t0 = time.time()

    full_audio_path = audio_dir / "full_audio.wav"
    if full_audio_path.exists() and not force_reprocess:
        print(f"[PIPELINE] Full audio exists. Skipping extraction.")
    else:
        full_audio_path = extract_full_audio(input_video, audio_dir)
    stage_timings["audio_extraction"] = round(time.time() - t0, 2)

    # ================================================================
    # STAGE 4: Voice Activity Detection (Silero VAD)
    # ================================================================
    print("\n--- STAGE 4: Voice Activity Detection ---")
    t0 = time.time()

    diarization_cache = diarization_dir / "segments.json"
    if diarization_cache.exists() and not force_reprocess:
        print("[PIPELINE] Diarization cache found. Skipping VAD + diarization.")
        diarization_segments = load_segments(diarization_cache)
        stage_timings["vad"] = 0.0
        stage_timings["diarization"] = 0.0
    else:
        speech_segments = run_vad(full_audio_path)
        stage_timings["vad"] = round(time.time() - t0, 2)

        if not speech_segments:
            print("[PIPELINE] WARNING: VAD detected no speech. Pipeline will continue without diarization.")
            diarization_segments = []
            stage_timings["diarization"] = 0.0
        else:
            # ============================================================
            # STAGE 5: Speaker Diarization (WeSpeaker ONNX + Clustering)
            # ============================================================
            print("\n--- STAGE 5: Speaker Diarization ---")
            t0 = time.time()

            if not wespeaker_model.exists():
                print(f"[PIPELINE] WARNING: WeSpeaker model not found at {wespeaker_model}")
                print("[PIPELINE] Run: python scripts/download_models.py")
                print("[PIPELINE] Continuing without diarization.")
                diarization_segments = []
            else:
                diarization_segments = run_diarization(
                    audio_path=full_audio_path,
                    speech_segments=speech_segments,
                    model_path=wespeaker_model,
                    n_speakers=n_speakers
                )

            stage_timings["diarization"] = round(time.time() - t0, 2)

            if diarization_segments:
                # Save diarization outputs
                save_segments(diarization_segments, diarization_cache)
                generate_rttm(
                    diarization_segments,
                    file_id=input_video.stem,
                    output_path=diarization_dir / "diarization.rttm"
                )
                print(f"[PIPELINE] Saved {len(diarization_segments)} diarization segments.")

    # ================================================================
    # STAGE 6: Speaker Role Assignment
    # ================================================================
    print("\n--- STAGE 6: Speaker Role Assignment ---")
    t0 = time.time()

    if diarization_segments:
        role_map, diarization_segments = assign_speaker_roles(diarization_segments)
        # Re-save with role labels
        save_segments(diarization_segments, diarization_cache)
    else:
        role_map = {}
        print("[PIPELINE] No diarization data. All speech will be attributed to CANDIDATE.")

    stage_timings["role_assignment"] = round(time.time() - t0, 2)

    # ================================================================
    # STAGE 7: Full Audio Transcription (Faster-Whisper INT8)
    # ================================================================
    print("\n--- STAGE 7: Full Audio Transcription ---")
    t0 = time.time()

    transcript_cache = outputs_dir / "full_transcript.json"
    if transcript_cache.exists() and not force_reprocess:
        print("[PIPELINE] Full transcript cache found. Loading.")
        with open(transcript_cache, "r", encoding="utf-8") as f:
            transcript_data = json.load(f)
        # An empty cache is normally created after a missing dependency or a
        # failed transcription. It must not be treated as a completed analysis.
        if not transcript_data.get("words"):
            print("[PIPELINE] Empty transcript cache found. Re-transcribing audio.")
            transcript_data = transcribe_full_audio(full_audio_path)
            with open(transcript_cache, "w", encoding="utf-8") as f:
                json.dump(transcript_data, f, indent=2)
    else:
        transcript_data = transcribe_full_audio(full_audio_path)
        # Cache full transcript
        with open(transcript_cache, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, indent=2)

    if not transcript_data.get("words"):
        raise RuntimeError(
            "No speech was transcribed from the input audio. Verify that the "
            "video contains an audible speech track, then run with --force."
        )

    stage_timings["transcription"] = round(time.time() - t0, 2)
    print(f"[PIPELINE] Transcript: {len(transcript_data.get('words', []))} words")

    # Free Whisper model before loading NLP model
    unload_whisper_model()

    # ================================================================
    # STAGE 8: Word-Speaker Alignment
    # ================================================================
    print("\n--- STAGE 8: Word-Speaker Alignment ---")
    t0 = time.time()

    all_words = transcript_data.get("words", [])
    if diarization_segments and all_words:
        labelled_words = align_words_to_speakers(all_words, diarization_segments)
    else:
        # No diarization: attribute everything to CANDIDATE
        try:
            from .speaker_alignment import LabelledWord
        except ImportError:
            from interview_pipeline.src.speaker_alignment import LabelledWord
        labelled_words = [
            LabelledWord(word=w["word"], start=w["start"], end=w["end"], speaker="CANDIDATE")
            for w in all_words
        ]
        if all_words:
            print(f"[ALIGNMENT] No diarization. Attributed all {len(all_words)} words to CANDIDATE.")

    speaker_turns = build_speaker_turns(labelled_words)
    stage_timings["alignment"] = round(time.time() - t0, 2)
    print(f"[PIPELINE] {len(speaker_turns)} speaker turns identified")

    # ================================================================
    # STAGE 9: Candidate Extraction
    # ================================================================
    print("\n--- STAGE 9: Candidate-Only Extraction ---")
    t0 = time.time()

    candidate_transcript, candidate_words = extract_candidate_data(labelled_words, "CANDIDATE")
    stage_timings["candidate_extraction"] = round(time.time() - t0, 2)

    # ================================================================
    # STAGE 10: Candidate Speech & Fluency Analysis
    # ================================================================
    print("\n--- STAGE 10: Speech & Fluency Analysis ---")
    t0 = time.time()

    # Calculate candidate speech duration from diarization segments
    candidate_diar_segments = []
    if diarization_segments:
        candidate_diar_segments = [
            seg for seg in diarization_segments if seg.speaker == "CANDIDATE"
        ]
        candidate_speech_duration = sum(
            seg.end - seg.start for seg in candidate_diar_segments
        )
    elif candidate_words:
        candidate_speech_duration = candidate_words[-1]["end"] - candidate_words[0]["start"]
    else:
        candidate_speech_duration = 0.0

    # Build transcript dict compatible with existing module interfaces
    candidate_data = {
        "chunk_id": "full_interview",
        "words": candidate_words,
        "transcript": candidate_transcript
    }

    filler_result = detect_filler_words(candidate_data)

    # --- Diarization-aware silence & pause calculation ---
    # Only count inter-word gaps that fall within CANDIDATE diarization segments.
    # Gaps caused by interviewer turns are excluded.
    candidate_silence_sec = 0.0
    long_pauses = 0
    short_pauses = 0
    longest_pause = 0.0
    pause_durations = []

    if candidate_words and candidate_diar_segments:
        for i in range(len(candidate_words) - 1):
            gap_start = candidate_words[i]["end"]
            gap_end = candidate_words[i + 1]["start"]
            if gap_end <= gap_start:
                continue

            # Sum the portion of this gap that overlaps with candidate segments
            gap_in_candidate = 0.0
            for seg in candidate_diar_segments:
                overlap_start = max(gap_start, seg.start)
                overlap_end = min(gap_end, seg.end)
                if overlap_end > overlap_start:
                    gap_in_candidate += (overlap_end - overlap_start)

            if gap_in_candidate > 0:
                candidate_silence_sec += gap_in_candidate
                pause_durations.append(gap_in_candidate)
                if gap_in_candidate >= 1.5:
                    long_pauses += 1
                elif gap_in_candidate >= 0.3:
                    short_pauses += 1
                if gap_in_candidate > longest_pause:
                    longest_pause = gap_in_candidate

    elif candidate_words and not candidate_diar_segments:
        # Fallback: no diarization, use raw gaps (legacy behavior)
        for i in range(len(candidate_words) - 1):
            gap = candidate_words[i + 1]["start"] - candidate_words[i]["end"]
            if gap > 0:
                candidate_silence_sec += gap
                pause_durations.append(gap)
                if gap >= 1.5:
                    long_pauses += 1
                elif gap >= 0.3:
                    short_pauses += 1
                if gap > longest_pause:
                    longest_pause = gap

    average_pause = round(sum(pause_durations) / len(pause_durations), 2) if pause_durations else 0.0
    silence_ratio = round(min(100.0, (candidate_silence_sec / max(1.0, candidate_speech_duration)) * 100), 1)

    # WPM based on candidate speech duration
    wpm = round((len(candidate_words) / max(1.0, candidate_speech_duration)) * 60, 1)

    speech_metrics = {
        "total_speech_duration_sec": round(candidate_speech_duration, 2),
        "words_per_minute": wpm,
        "total_filler_words": filler_result["filler_count"],
        "filler_details": filler_result["filler_words"],
        "total_long_pauses": long_pauses,
        "total_short_pauses": short_pauses,
        "longest_pause_sec": round(longest_pause, 2),
        "average_pause_sec": average_pause,
        "total_silence_sec": round(candidate_silence_sec, 2),
        "silence_ratio_pct": silence_ratio
    }

    stage_timings["speech_analysis"] = round(time.time() - t0, 2)
    print(f"[PIPELINE] Candidate WPM: {speech_metrics['words_per_minute']}, "
          f"Fillers: {speech_metrics['total_filler_words']}, "
          f"Long pauses: {speech_metrics['total_long_pauses']}")

    # ================================================================
    # STAGE 11: Semantic NLP Scoring
    # ================================================================
    print("\n--- STAGE 11: Semantic NLP Scoring ---")
    t0 = time.time()

    if nlp_config is None:
        nlp_config = {
            "job_description": "Software engineering role involving problem-solving, system design, coding, and teamwork. The candidate should demonstrate technical competence, communication skills, and cultural fit.",
            "qualifications": "Bachelor's degree in Computer Science or related field\nStrong analytical and problem-solving abilities\nGood verbal and written communication skills",
            "responsibilities": "Develop and maintain software applications\nCollaborate with cross-functional teams\nParticipate in code reviews and design discussions",
            "key_skills": ["problem solving", "communication", "teamwork", "programming", "system design"]
        }
        
    nlp_result = evaluate_technical_answer(candidate_transcript, nlp_config)
    stage_timings["nlp_scoring"] = round(time.time() - t0, 2)
    print(f"[PIPELINE] NLP Overall Score: {nlp_result['overall_score']}% ({nlp_result['match_level']})")

    # ================================================================
    # STAGE 12: Visual Analysis (per video chunk)
    # ================================================================
    print("\n--- STAGE 12: Visual Analysis (DISABLED) ---")
    t0 = time.time()

    visual_results = []
    for i, chunk in enumerate(chunks):
        visual_results.append({"face_visibility_pct": "N/A", "head_posture_score": "Disabled"})

    visual_metrics = {
        "face_visibility_pct": "N/A",
        "head_posture_score": "Disabled"
    }

    stage_timings["visual_analysis"] = round(time.time() - t0, 2)
    print("[PIPELINE] Visual Analysis stage is currently disabled.")

    # ================================================================
    # STAGE 13: Timestamped Result Aggregation
    # ================================================================
    print("\n--- STAGE 13: Result Aggregation ---")
    t0 = time.time()

    # Build per-chunk timeline by slicing the global word list
    timeline = []
    for i, chunk in enumerate(chunks):
        chunk_start = i * chunk_duration
        chunk_end = (i + 1) * chunk_duration

        # Filter candidate words that fall within this chunk's time range
        chunk_candidate_words = [
            w for w in candidate_words
            if w["start"] >= chunk_start and w["start"] < chunk_end
        ]
        chunk_candidate_data = {"chunk_id": chunk.stem, "words": chunk_candidate_words}

        chunk_filler = detect_filler_words(chunk_candidate_data)
        chunk_pause = detect_pauses(chunk_candidate_data)
        chunk_fluency = analyze_speech_fluency(
            chunk_candidate_data,
            chunk_duration_sec=float(chunk_duration)
        )

        # Visual result for this chunk
        vis = visual_results[i] if i < len(visual_results) else {}

        timeline.append({
            "chunk_id": chunk.stem,
            "start_time": chunk_start,
            "end_time": chunk_end,
            "candidate_transcript": " ".join(w["word"] for w in chunk_candidate_words),
            "filler_words": chunk_filler["filler_count"],
            "long_pauses": chunk_pause["long_pauses"],
            "silence_sec": chunk_fluency["total_silence_sec"],
            "wpm": chunk_fluency["words_per_minute"],
            "face_visibility_pct": vis.get("face_visibility_pct", 0.0)
        })

    # Build diarization summary
    diarization_summary = {"total_speakers": 0, "speakers": []}
    if diarization_segments:
        speaker_durations = {}
        speaker_counts = {}
        for seg in diarization_segments:
            dur = seg.end - seg.start
            speaker_durations[seg.speaker] = speaker_durations.get(seg.speaker, 0.0) + dur
            speaker_counts[seg.speaker] = speaker_counts.get(seg.speaker, 0) + 1

        diarization_summary["total_speakers"] = len(speaker_durations)
        for spk, dur in speaker_durations.items():
            diarization_summary["speakers"].append({
                "role": spk,
                "total_speech_sec": round(dur, 2),
                "segment_count": speaker_counts[spk]
            })

    # Build speaker-labelled transcript for report
    speaker_labelled_transcript = [
        {"speaker": turn.speaker, "start": turn.start, "end": turn.end, "text": turn.text}
        for turn in speaker_turns
    ]

    stage_timings["aggregation"] = round(time.time() - t0, 2)

    # ================================================================
    # STAGE 14: Final Report Generation
    # ================================================================
    print("\n--- STAGE 14: Report Generation ---")
    t0 = time.time()

    total_time = round(time.time() - pipeline_start, 2)

    final_report = {
        "processing_metadata": {
            "input_video": str(input_video),
            "input_duration_sec": round(video_duration, 2),
            "total_chunks": len(chunks),
            "chunk_duration_sec": chunk_duration,
            "total_processing_time_sec": total_time,
            "stage_timings": stage_timings,
            "n_speakers_configured": n_speakers
        },
        "diarization_summary": diarization_summary,
        "candidate_metrics": {
            "speech": speech_metrics,
            "nlp": nlp_result,
            "visual": visual_metrics
        },
        "transcripts": {
            "full_transcript": transcript_data.get("transcript", ""),
            "speaker_labelled_transcript": speaker_labelled_transcript,
            "candidate_only_transcript": candidate_transcript
        },
        "timeline": timeline
    }

    generate_final_report(final_report, reports_dir)
    stage_timings["report_generation"] = round(time.time() - t0, 2)

    # Also write per-chunk JSON outputs for backward compatibility
    for entry in timeline:
        chunk_output = outputs_dir / f"{entry['chunk_id']}.json"
        with open(chunk_output, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2)

    # Save identity on success
    if current_identity:
        with open(identity_file, "w") as f:
            json.dump(current_identity, f)

    print("\n==================================================")
    print(f"[PIPELINE] Pipeline complete in {total_time:.2f} seconds")
    print("==================================================")
