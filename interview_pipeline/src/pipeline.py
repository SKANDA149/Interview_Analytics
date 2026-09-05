from pathlib import Path
import json
import time
from interview_pipeline.src.chunking import split_video_into_chunks
from interview_pipeline.src.audio_extract import extract_audio
from interview_pipeline.src.stt import transcribe_audio
from interview_pipeline.src.filler_detection import detect_filler_words
from interview_pipeline.src.speech_analysis import analyze_speech_fluency
from interview_pipeline.src.report_generator import generate_aggregated_report
from interview_pipeline.src.nlp_scoring import evaluate_technical_answer
from interview_pipeline.src.visual_analytics import analyze_video_visuals



def run_pipeline():
    print("==================================================")
    print("[PIPELINE] Starting interview processing pipeline")
    print("==================================================")
    start_time = time.time()
    
    input_video = Path("data/input/sample.mp4")
    chunks_dir = Path("data/chunks")
    audio_dir = Path("data/audio")
    outputs_dir = Path("data/outputs")
    model_path = Path("models/vosk/vosk-model-small-en-us-0.15")

    outputs_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Chunking
    print(f"\n--- STAGE 1: Video Chunking ---")
    chunking_start_time = time.time()
    existing_chunks = list(chunks_dir.glob("chunk_*.mp4"))
    
    if existing_chunks:
        print(f"[PIPELINE] Found {len(existing_chunks)} existing chunks. Skipping chunking step.")
        chunks = sorted(existing_chunks, key=lambda x: x.name)
    else:
        print(f"[PIPELINE] Chunking video {input_video.name}")
        chunks = split_video_into_chunks(
            input_path=input_video,
            output_dir=chunks_dir,
            chunk_duration=10
        )
        print(f"[PIPELINE] Total chunks generated: {len(chunks)}")
        
    chunking_time = time.time() - chunking_start_time
    print(f"[PIPELINE] Stage 1 completed in {chunking_time:.2f} seconds")

    print(f"\n--- STAGE 2: Audio Extraction ---")
    print(f"--- STAGE 3: Speech-to-Text ---")
    
    # Process each chunk inside this loop
    for i, chunk in enumerate(chunks, 1):
        chunk_start_time = time.time()
        print(f"\n[PIPELINE] Processing chunk {i}/{len(chunks)}: {chunk.name}")
        
        output_file = outputs_dir / f"{chunk.stem}.json"
        
        # Skip logic for transcription
        if output_file.exists():
            print(f"  -> Output JSON exists ({output_file.name}). Skipping processing for {chunk.name}.")
            continue
            
        # Step 2: Extract Audio
        audio_start_time = time.time()
        expected_audio_path = audio_dir / f"{chunk.stem}.wav"
        
        if expected_audio_path.exists():
            print(f"  -> Audio exists ({expected_audio_path.name}). Skipping extraction.")
            audio_path = expected_audio_path
        else:
            audio_path = extract_audio(chunk, audio_dir)
            print(f"  -> Extracted audio in {time.time() - audio_start_time:.2f} seconds")
        
        # Step 3: Transcribe Audio
        stt_start_time = time.time()
        transcript_result = transcribe_audio(audio_path, model_path)
        print(f"  -> Transcription completed in {time.time() - stt_start_time:.2f} seconds")
        
        # Step 3.5: Filler Word Detection
        filler_result = detect_filler_words(transcript_result)
        
        # --- Advanced Speech Analytics ---

        fluency_start_time = time.time()
        fluency_result = analyze_speech_fluency(transcript_result, chunk_duration_sec=10.0)
        
        # Combine them into one neat "speech_analysis" dictionary in your JSON
        transcript_result["speech_analysis"] = {
            "filler_count": filler_result["filler_count"],
            "filler_words": filler_result["filler_words"],
            "words_per_minute": fluency_result["words_per_minute"],
            "total_silence_sec": fluency_result["total_silence_sec"],
            "silence_ratio_pct": fluency_result["silence_ratio_pct"],
            "long_pauses_count": fluency_result["long_pauses_count"]
        }
        
        # --- NEW CODE: SEMANTIC NLP ANALYSIS ---
        # For testing, we are hardcoding an ideal answer. Later, the recruiter will type this in the UI.
        ideal_answer = "Data structures are used to organize, store, and manage data efficiently so it can be accessed and modified easily."
        
        nlp_start_time = time.time()
        nlp_result = evaluate_technical_answer(transcript_result["transcript"], ideal_answer)
        transcript_result["content_analysis"] = nlp_result
        print(f"  -> NLP Evaluation completed in {time.time() - nlp_start_time:.2f} seconds (Score: {nlp_result['semantic_score']}%)")
        # --- END NEW CODE ---

        # --- VISUAL ANALYTICS ---
        visual_start_time = time.time()
        visual_result = analyze_video_visuals(chunk)
        transcript_result["visual_analysis"] = visual_result
        print(f"  -> Visual Evaluation completed in {time.time() - visual_start_time:.2f}s (Face Visibility: {visual_result['face_visibility_pct']}%)")
        # Step 4: Save Output JSON
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(transcript_result, f, indent=2)
            
        # --- MEMORY OPTIMIZATION CLEANUP ---
        # This deletes the video and audio chunks immediately after the JSON is made
        print("  -> Cleaning up temporary chunk files...")
        try:
            if chunk.exists():
                chunk.unlink()  
            if audio_path.exists():
                audio_path.unlink()  
        except Exception as e:
            print(f"  -> [WARNING] Could not delete temp files: {e}")
            
        chunk_end_time = time.time()
        print(f"[PIPELINE] Finished processing {chunk.name} in {chunk_end_time - chunk_start_time:.2f} seconds")

    # === THIS HAPPENS AFTER ALL CHUNKS ARE PROCESSED ===
    total_time = time.time() - start_time
    print("==================================================")
    print(f"[PIPELINE] Pipeline processing complete in {total_time:.2f} seconds")
    print("==================================================")

    # Trigger the Final Report Generation
    reports_dir = Path("data/reports")
    generate_aggregated_report(outputs_dir, reports_dir)
