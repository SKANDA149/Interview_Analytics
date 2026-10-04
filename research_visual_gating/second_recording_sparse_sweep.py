"""
Experiment 2, Step 3 -- CHEAP sparse suitability sweep on the candidate second recording.
Frozen detector config: YuNet, FACE_CONFIDENCE_THRESHOLD = 0.6. No tuning, no new metric.
Sparse: one probe every 2.0s (not the 5 FPS production grid) -- this is a suitability
screen, not the pilot.
"""
import cv2, json

VIDEO = "/mnt/user-data/uploads/interview_visual/Interview_Analytics/data/input/sample.mp4"
MODEL = "/mnt/user-data/uploads/interview_visual/Interview_Analytics/models/yunet/face_detection_yunet_2023mar.onnx"
FACE_CONFIDENCE_THRESHOLD = 0.6
STEP_S = 2.0

cap = cv2.VideoCapture(VIDEO)
fps = cap.get(cv2.CAP_PROP_FPS)
n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
duration = n_frames / fps
print(f"video {W}x{H} fps={fps} frames={n_frames} duration={duration:.2f}s")

det = cv2.FaceDetectorYN.create(MODEL, "", (W, H), FACE_CONFIDENCE_THRESHOLD)

results = []
t = 0.0
while t < duration:
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
    ok, frame = cap.read()
    if not ok or frame is None:
        t += STEP_S; continue
    _, faces = det.detect(frame)
    n = 0 if faces is None else len(faces)
    best = float(faces[:, -1].max()) if n else 0.0
    # where is the face? record centre-x fraction + box height fraction, to test spatial stability
    if n:
        x, y, w, h = faces[0][:4]
        cx = (x + w / 2) / W; cy = (y + h / 2) / H; hf = h / H
    else:
        cx = cy = hf = None
    results.append({"t": round(t, 2), "n_faces": n, "conf": round(best, 4),
                    "cx": None if cx is None else round(float(cx), 4),
                    "cy": None if cy is None else round(float(cy), 4),
                    "hfrac": None if hf is None else round(float(hf), 4)})
    t += STEP_S
cap.release()

with open("sparse_sweep_results.json", "w") as f:
    json.dump({"video": "sample.mp4", "width": W, "height": H, "fps": fps,
               "duration_s": duration, "step_s": STEP_S,
               "face_confidence_threshold": FACE_CONFIDENCE_THRESHOLD,
               "probes": results}, f, indent=1)

n_tot = len(results)
n_face = sum(1 for r in results if r["n_faces"] > 0)
print(f"probes={n_tot}  face_present={n_face} ({100*n_face/n_tot:.1f}%)  face_absent={n_tot-n_face} ({100*(n_tot-n_face)/n_tot:.1f}%)")

# transitions between present/absent
present = [r["n_faces"] > 0 for r in results]
trans = sum(1 for i in range(1, n_tot) if present[i] != present[i-1])
print(f"present/absent transitions at 2s resolution: {trans}")

# spatial spread of detected face centres -- tests whether a FIXED ROI is even possible
cxs = [r["cx"] for r in results if r["cx"] is not None]
cys = [r["cy"] for r in results if r["cy"] is not None]
hfs = [r["hfrac"] for r in results if r["hfrac"] is not None]
if cxs:
    print(f"face centre x fraction: min={min(cxs):.3f} max={max(cxs):.3f} spread={max(cxs)-min(cxs):.3f}")
    print(f"face centre y fraction: min={min(cys):.3f} max={max(cys):.3f} spread={max(cys)-min(cys):.3f}")
    print(f"face height fraction  : min={min(hfs):.3f} max={max(hfs):.3f}  (Rec-1 self-view thumb was tiny)")
