"""Interview Analytics Pipeline — master orchestrator.

Coordinates: chunking → audio extraction → Vosk STT → filler detection →
speech fluency → NLP scoring → visual presence → report generation.

All paths are parameterized; nothing is hard-coded to a single video.
Model paths resolve relative to the project root passed by the caller.
"""
from pathlib import Path
import json
import sys
import time

from interview_pipeline.src.chunking import split_video_into_chunks, _chunk_sort_key, get_chunk_time_ranges
from interview_pipeline.src.audio_extract import extract_audio, get_media_duration
from interview_pipeline.src.stt import transcribe_audio
from interview_pipeline.src.filler_detection import detect_filler_words
from interview_pipeline.src.speech_analysis import analyze_speech_fluency
from interview_pipeline.src.report_generator import generate_final_report
from interview_pipeline.src.nlp_scoring import evaluate_chunk_without_rubric
from interview_pipeline.src.diarization import load_segments
from interview_pipeline.src.visual_presence import (
    run_visual_presence_analysis,
    summarize_visual_metrics,
    bucket_visual_results_by_chunk,
)


def run_pipeline(
    *,
    input_video: Path,
    output_dir: Path,
    diarization_path: Path | None = None,
    project_root: Path | None = None,
    chunk_duration: int = 10,
):
    """Run the full interview analysis pipeline.

    Args:
        input_video: Absolute path to the input video file.
        output_dir: Base directory for all pipeline outputs (chunks, audio,
                    outputs, reports sub-directories will be created here).
        diarization_path: Optional path to pre-computed diarization JSON.
                          If None, visual presence analysis is skipped.
        project_root: Project root directory for resolving model paths.
                      Defaults to the parent of this file's package.
        chunk_duration: Duration of each chunk in seconds.
    """
    print("==================================================")
    print("[PIPELINE] Starting interview processing pipeline")
    print("==================================================")
    start_time = time.time()

    # ── Resolve project root for model paths ──
    if project_root is None:
        # Fallback: two levels up from this file (interview_pipeline/src/pipeline.py)
        project_root = Path(__file__).resolve().parent.parent.parent

    # ── Validate input video ──
    input_video = Path(input_video).resolve()
    if not input_video.exists():
        print(f"[ERROR] Input video not found: {input_video}", file=sys.stderr)
        sys.exit(1)

    # ── Set up directory structure under output_dir ──
    output_dir = Path(output_dir)
    chunks_dir = output_dir / "chunks"
    audio_dir = output_dir / "audio"
    outputs_dir = output_dir / "outputs"
    reports_dir = output_dir / "reports"

    for d in (chunks_dir, audio_dir, outputs_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)

    # ── Validate Vosk model ──
    model_path = project_root / "models" / "vosk" / "vosk-model-small-en-us-0.15"
    if not model_path.exists():
        print(
            f"[ERROR] Vosk model not found at {model_path}\n"
            f"Download from: https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip\n"
            f"Extract into: {model_path.parent}",
            file=sys.stderr,
        )
        sys.exit(1)

    stage_timings = {}

    # ════════════════════════════════════════════════════════════════════
    # STAGE 1: Video Chunking
    # ════════════════════════════════════════════════════════════════════
    print(f"\n--- STAGE 1: Video Chunking ---")
    t0 = time.time()
    existing_chunks = sorted(chunks_dir.glob("chunk_*.mp4"), key=_chunk_sort_key)

    if existing_chunks:
        print(f"[PIPELINE] Found {len(existing_chunks)} existing chunks. Skipping chunking.")
        chunks = existing_chunks
    else:
        print(f"[PIPELINE] Chunking video: {input_video.name}")
        chunks = split_video_into_chunks(input_video, chunks_dir, chunk_duration)
        print(f"[PIPELINE] Total chunks generated: {len(chunks)}")

    stage_timings["chunking"] = round(time.time() - t0, 2)
    print(f"[PIPELINE] Stage 1 completed in {stage_timings['chunking']:.2f}s")
    chunk_time_ranges = get_chunk_time_ranges(chunks, chunk_duration)

    if not chunks:
        print("[ERROR] No chunks produced — video may be empty or unreadable.", file=sys.stderr)
        sys.exit(1)

    from interview_pipeline.src.diarization import load_segments, save_segments, run_diarization, generate_rttm
    from interview_pipeline.src.vad import run_vad
    from interview_pipeline.src.speaker_roles import assign_speaker_roles

    # ════════════════════════════════════════════════════════════════════
    # STAGE 1.5: Diarization
    # ════════════════════════════════════════════════════════════════════
    print(f"\n--- STAGE 1.5: Speaker Diarization ---")
    t0 = time.time()
    diarization_dir = output_dir / "diarization"
    diarization_dir.mkdir(parents=True, exist_ok=True)
    
    if diarization_path and diarization_path.exists():
        print(f"[PIPELINE] Using supplied precomputed diarization: {diarization_path}")
    else:
        print("[PIPELINE] No diarization supplied. Generating automatically...")
        full_audio_path = audio_dir / f"{input_video.stem}_full.wav"
        if not full_audio_path.exists():
            print(f"[PIPELINE] Extracting full 16kHz audio to {full_audio_path.name}...")
            # Extract full 16kHz mono audio directly
            import subprocess
            proc = subprocess.run([
                "ffmpeg", "-y", "-i", str(input_video),
                "-vn", "-ac", "1", "-ar", "16000", str(full_audio_path)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                print(f"[ERROR] Failed to extract full audio: {proc.stderr.decode(errors='ignore')}", file=sys.stderr)
                sys.exit(1)
                
        print("[PIPELINE] Running VAD...")
        speech_segments = run_vad(full_audio_path)
        if not speech_segments:
            print("[ERROR] VAD found no speech segments. Diarization failed.", file=sys.stderr)
            sys.exit(1)
            
        wespeaker_model = project_root / "models" / "wespeaker" / "voxceleb_resnet34_LM.onnx"
        print("[PIPELINE] Running WeSpeaker Diarization...")
        raw_segments = run_diarization(full_audio_path, speech_segments, wespeaker_model)
        if not raw_segments:
            print("[ERROR] Diarization/Clustering failed.", file=sys.stderr)
            sys.exit(1)
            
        print("[PIPELINE] Assigning Speaker Roles...")
        role_map, final_segments = assign_speaker_roles(raw_segments)
        if not final_segments:
            print("[ERROR] Role assignment failed.", file=sys.stderr)
            sys.exit(1)
            
        diarization_path = diarization_dir / "segments.json"
        save_segments(final_segments, diarization_path)
        generate_rttm(final_segments, "interview", diarization_dir / "diarization.rttm")
        print(f"[PIPELINE] Diarization generated and saved to {diarization_path}")

    stage_timings["diarization"] = round(time.time() - t0, 2)
    print(f"[PIPELINE] Stage 1.5 completed in {stage_timings['diarization']:.2f}s")

    # ════════════════════════════════════════════════════════════════════
    # STAGE 5: Visual Presence Analysis (whole-video, pre-loop)
    # ════════════════════════════════════════════════════════════════════
    print(f"\n--- STAGE 5: Visual Presence Analysis ---")
    t0 = time.time()
    visual_analysis_result = None
    visual_summary = None

    if diarization_path and diarization_path.exists():
        diarization_segments = load_segments(diarization_path)
        visual_analysis_result = run_visual_presence_analysis(input_video, diarization_segments)
        visual_summary = summarize_visual_metrics(visual_analysis_result)
        print(
            f"[PIPELINE] Visual analysis complete "
            f"(presence={visual_summary.get('presence_pct')}%, "
            f"full_visibility={visual_summary.get('face_visibility_pct')}%)"
        )
    else:
        reason = "no diarization file provided" if not diarization_path else f"file not found: {diarization_path}"
        print(f"[PIPELINE] [WARNING] Skipping visual presence analysis — {reason}.")

    stage_timings["visual_analysis"] = round(time.time() - t0, 2)

    # ════════════════════════════════════════════════════════════════════
    # STAGES 2-4: Per-chunk processing loop
    # ════════════════════════════════════════════════════════════════════
    print(f"\n--- STAGES 2-4: Audio / STT / Speech / NLP / Visual bucketing ---")
    t0 = time.time()

    for i, chunk in enumerate(chunks):
        chunk_start_time = time.time()
        print(f"\n[PIPELINE] Processing chunk {i + 1}/{len(chunks)}: {chunk.name}")

        output_file = outputs_dir / f"{chunk.stem}.json"

        # Skip already-processed chunks
        if output_file.exists():
            print(f"  -> Output JSON exists ({output_file.name}). Skipping.")
            continue

        # ── Audio extraction ──
        expected_audio = audio_dir / f"{chunk.stem}.wav"
        if expected_audio.exists():
            print(f"  -> Audio exists ({expected_audio.name}). Skipping extraction.")
            audio_path = expected_audio
        else:
            audio_path = extract_audio(chunk, audio_dir)
            print(f"  -> Audio extracted.")

        # ── Measure actual chunk duration ──
        actual_chunk_dur = get_media_duration(audio_path, default_sec=float(chunk_duration))

        # ── Vosk STT ──
        transcript_result = transcribe_audio(audio_path, model_path)
        if not transcript_result.get("words"):
            print(f"  -> [WARNING] Empty transcript for {chunk.name}.")

        # ── Filler detection ──
        filler_result = detect_filler_words(transcript_result)

        # ── Speech fluency ──
        fluency_result = analyze_speech_fluency(transcript_result, chunk_duration_sec=actual_chunk_dur)

        transcript_result["speech_analysis"] = {
            "filler_count": filler_result["filler_count"],
            "filler_words": filler_result["filler_words"],
            "words_per_minute": fluency_result["words_per_minute"],
            "total_silence_sec": fluency_result["total_silence_sec"],
            "silence_ratio_pct": fluency_result["silence_ratio_pct"],
            "long_pauses_count": fluency_result["long_pauses_count"],
            "actual_chunk_duration_sec": fluency_result["actual_chunk_duration_sec"],
            "active_speech_duration_sec": fluency_result["active_speech_duration_sec"],
        }

        # ── Semantic evaluation availability ──
        # Chunk transcripts cannot reliably identify interviewer questions,
        # candidate response turns, or their question-specific rubrics. Do
        # not turn a generic chunk comparison into an answer-quality score.
        transcript_result["content_analysis"] = evaluate_chunk_without_rubric(
            transcript_result["transcript"]
        )

        # ── Visual bucketing ──
        chunk_start_sec, chunk_end_sec = chunk_time_ranges[chunk.name]
        transcript_result["chunk_start_sec"] = chunk_start_sec
        transcript_result["chunk_end_sec"] = chunk_end_sec
        if visual_analysis_result is not None:
            chunk_visual = bucket_visual_results_by_chunk(
                visual_analysis_result, chunk_start_sec, chunk_end_sec
            )
        else:
            chunk_visual = {"face_visibility_pct": "N/A", "n_samples": 0}
        transcript_result["visual_analysis"] = chunk_visual

        # ── Save chunk JSON ──
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(transcript_result, f, indent=2)

        # Clean up temporary audio (keep chunks for potential re-use)
        try:
            if audio_path.exists():
                audio_path.unlink()
        except OSError as e:
            print(f"  -> [WARNING] Could not delete {audio_path.name}: {e}")

        elapsed = time.time() - chunk_start_time
        print(f"[PIPELINE] Finished {chunk.name} in {elapsed:.2f}s")

    stage_timings["per_chunk_processing"] = round(time.time() - t0, 2)

    # ════════════════════════════════════════════════════════════════════
    # STAGE 6: Final Report Generation
    # ════════════════════════════════════════════════════════════════════
    total_time = time.time() - start_time
    print("\n==================================================")
    print(f"[PIPELINE] Processing complete in {total_time:.2f}s")
    print("==================================================")

    generate_final_report(
        outputs_dir=outputs_dir,
        reports_dir=reports_dir,
        visual_summary=visual_summary,
        stage_timings=stage_timings,
        input_video_name=input_video.name,
    )
