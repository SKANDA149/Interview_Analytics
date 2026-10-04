"""
Experiment 1 (manual visual validation) frame extraction.
Reads the 133-item frame_extract_list.json (sample_id + timestamp), seeks the video at
each timestamp, crops to the fixed CANDIDATE_ROI, and writes one PNG per sample_id.
Read-only w.r.t. the pilot: does not touch reference_frame_results_v1i.json, runs.jsonl,
vad_raw_intervals.json, or any pilot module. No YuNet/VAD inference performed here.
"""
import json, os, cv2

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "results", "video1_infosys_checkpointed", "manual_validation_frames")
VIDEO_PATH = os.path.join(BASE, "data", "video1_infosys_h264.mp4")
LIST_PATH = os.path.join(DATA_DIR, "frame_extract_list.json")
CANDIDATE_ROI = (1075, 560, 205, 160)  # x, y, w, h -- frozen, corrected ROI from the pilot

with open(LIST_PATH) as f:
    samples = json.load(f)

cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)
frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
print("video fps:", fps, "frame_count:", frame_count)

x, y, w, h = CANDIDATE_ROI
ok_count = 0
fail = []
for s in samples:
    ts = s["timestamp"]
    frame_no = round(ts * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ret, frame = cap.read()
    if not ret or frame is None:
        fail.append(s["sample_id"])
        continue
    crop = frame[y:y+h, x:x+w]
    out_path = os.path.join(DATA_DIR, f"{s['sample_id']}.png")
    cv2.imwrite(out_path, crop)
    ok_count += 1

cap.release()
print("extracted:", ok_count, "of", len(samples))
print("failures:", fail)
