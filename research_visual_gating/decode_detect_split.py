"""
PHASE 1D — minimum instrumentation to estimate the decode-vs-detect cost split.
Frozen config: YuNet face_detection_yunet_2023mar.onnx, FACE_CONFIDENCE_THRESHOLD=0.6,
CANDIDATE_ROI=(1075,560,205,160), 5-FPS grid. Nothing is tuned or redesigned.

HARDWARE CAVEAT: this runs in the analysis container, NOT the machine that produced
the pilot's wall_time_s. It estimates the RATIO / order of magnitude only and must not
be quoted as the pilot's own timing.
"""
import cv2, time, json
V="/mnt/user-data/uploads/interview_visual/Interview_Analytics/research_visual_gating/data/video1_infosys_h264.mp4"
M="/mnt/user-data/uploads/interview_visual/Interview_Analytics/models/yunet/face_detection_yunet_2023mar.onnx"
ROI=(1075,560,205,160); THR=0.6; GRID_STEP=0.2
N_GRID=2000   # first 2000 grid frames (400 s of video) -- enough for a stable ratio

def pass_over(detect):
    cap=cv2.VideoCapture(V); fps=cap.get(cv2.CAP_PROP_FPS)
    x,y,w,h=ROI
    det=cv2.FaceDetectorYN.create(M,"",(w,h),THR) if detect else None
    targets={round(i*GRID_STEP,3) for i in range(N_GRID)}
    last=max(targets)
    t0=time.perf_counter(); n_dec=0; n_det=0; i=0
    while True:
        ok,frame=cap.read()
        if not ok: break
        ts=round(i/fps,3); n_dec+=1; i+=1
        if ts>last+1.0: break
        g=round(round(ts/GRID_STEP)*GRID_STEP,3)
        if abs(ts-g)<1/(2*fps) and g in targets:
            if detect:
                det.detect(frame[y:y+h, x:x+w]); n_det+=1
    el=time.perf_counter()-t0; cap.release()
    return el,n_dec,n_det

d_only,nd,_=pass_over(False)
d_det,nd2,ndet=pass_over(True)
detect_cost=d_det-d_only
print(f"frames decoded: {nd}   detector invocations: {ndet}")
print(f"decode-only pass      : {d_only:.2f} s")
print(f"decode+detect pass    : {d_det:.2f} s")
print(f"attributable to YuNet : {detect_cost:.2f} s  ({100*detect_cost/d_det:.1f}% of total)")
print(f"attributable to decode: {d_only:.2f} s  ({100*d_only/d_det:.1f}% of total)")
print(f"per-detector-call cost: {1000*detect_cost/ndet:.3f} ms")
print(f"\nIMPLICATION: gating can only ever address the {100*detect_cost/d_det:.1f}% detector share.")
print(f"Max theoretical saving at 32.35% skip = {0.3235*100*detect_cost/d_det:.1f}% of total runtime.")
json.dump({"hardware_caveat":"analysis container, NOT the pilot machine; ratio/order-of-magnitude only",
 "n_grid_frames_benchmarked":ndet,"frames_decoded":nd,
 "decode_only_s":round(d_only,3),"decode_plus_detect_s":round(d_det,3),
 "detect_attributable_s":round(detect_cost,3),
 "detect_share_pct":round(100*detect_cost/d_det,1),"decode_share_pct":round(100*d_only/d_det,1),
 "per_call_ms":round(1000*detect_cost/ndet,3),
 "max_theoretical_saving_pct_at_32_35_skip":round(0.3235*100*detect_cost/d_det,1)},
 open("decode_detect_split.json","w"),indent=2)
