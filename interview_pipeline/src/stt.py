from pathlib import Path
import json
import wave
import sys
from vosk import Model, KaldiRecognizer

_model_cache = {}

def format_transcription(results: list, chunk_id: str) -> dict:
    """
    Converts raw Vosk results into the structured output dictionary.
    """
    full_text = []
    words = []
    
    for res_dict in results:
        if 'text' in res_dict and res_dict['text']:
            full_text.append(res_dict['text'])
        if 'result' in res_dict:
            for w in res_dict['result']:
                words.append({
                    "word": w['word'],
                    "start": w['start'],
                    "end": w['end']
                })
                
    return {
        "chunk_id": chunk_id,
        "transcript": " ".join(full_text).strip(),
        "words": words
    }

def transcribe_audio(audio_path: Path, model_path: Path) -> dict:
    """
    Transcribes a mono 16kHz WAV audio file using the Vosk offline model.
    Reads audio in streaming chunks to minimize memory usage.
    """
    global _model_cache
    model_str = str(model_path)
    chunk_id = audio_path.stem
    
    # Initialize default result structure
    result = {
        "chunk_id": chunk_id,
        "transcript": "",
        "words": []
    }
    
    # Load model once per path, no dynamic guessing
    try:
        if model_str not in _model_cache:
            _model_cache[model_str] = Model(model_str)
        model = _model_cache[model_str]
    except Exception as e:
        print(f"[ERROR] Failed to load Vosk model from {model_str}: {e}")
        return result
    
    # Open WAV file safely and validate format
    try:
        wf = wave.open(str(audio_path), "rb")
        
        # Audio Validation: Mono, 16kHz, PCM
        channels = wf.getnchannels()
        framerate = wf.getframerate()
        sampwidth = wf.getsampwidth()
        
        if channels != 1 or framerate != 16000 or sampwidth != 2:
            wf.close()
            raise ValueError(f"Invalid audio format. Expected mono, 16kHz, 16-bit PCM. Got {channels}ch, {framerate}Hz, {sampwidth*8}-bit.")
            
    except Exception as e:
        print(f"[ERROR] Failed to read audio file {audio_path}: {e}")
        return result
        
    try:
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)
        
        results = []
        
        # Read in chunks
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                results.append(res)
                
        res = json.loads(rec.FinalResult())
        results.append(res)
        
        # Format output using helper
        result = format_transcription(results, chunk_id)
        
    except Exception as e:
        print(f"[ERROR] Transcription failed for {audio_path}: {e}")
    finally:
        wf.close()
        
    return result
