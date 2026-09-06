import cv2
from pathlib import Path

def analyze_video_visuals(video_chunk_path: Path) -> dict:
    # Analyzes video frames using OpenCV to evaluate candidate face presence and posture stability.
    cap = cv2.VideoCapture(str(video_chunk_path))
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    total_frames = 0
    face_detected_frames = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        total_frames += 1
        # Check 1 out of every 5 frames for memory optimization
        if total_frames % 5 == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            if len(faces) > 0:
                face_detected_frames += 1
                
    cap.release()
    
    checked_frames = max(1, total_frames // 5)
    face_stability_pct = round((face_detected_frames / checked_frames) * 100, 1)
    
    return {
        "face_visibility_pct": face_stability_pct,
        "head_posture_score": "Stable" if face_stability_pct >= 80 else "Needs Improvement"
    }