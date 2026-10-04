import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from research_visual_gating.candidate_layout import (
    detect_candidate_presence, candidate_roi_for_state, CandidateFrameResult,
    FULL_VIEW, OFF_CAMERA, CANDIDATE_ROI, INTERVIEWER_ROI,
)

passed = 0
failed = 0

def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}")

print("test_candidate_layout.py")

FRAME_H, FRAME_W = 720, 1280


def _blank_frame(gray_value=51):
    return np.full((FRAME_H, FRAME_W, 3), gray_value, dtype=np.uint8)


def _fake_detect_faces_present(crop, model_path):
    class _Face:
        confidence = 0.91
    return [_Face()]


def _fake_detect_faces_absent(crop, model_path):
    return []


# --- candidate_roi_for_state ---

check("full_view maps to CANDIDATE_ROI", candidate_roi_for_state(FULL_VIEW) == CANDIDATE_ROI)
check("off_camera has no ROI to re-crop", candidate_roi_for_state(OFF_CAMERA) is None)
check("candidate ROI is never the interviewer ROI", CANDIDATE_ROI != INTERVIEWER_ROI)


# --- detect_candidate_presence ---

frame = _blank_frame()

r_present = detect_candidate_presence(frame, timestamp=10.0, model_path=None, detect_faces_fn=_fake_detect_faces_present)
check("a detected face yields present=True and layout_state=full_view", r_present.present is True and r_present.layout_state == FULL_VIEW)
check("confidence and n_faces are populated when present", r_present.confidence == 0.91 and r_present.n_faces == 1)

r_absent = detect_candidate_presence(frame, timestamp=20.0, model_path=None, detect_faces_fn=_fake_detect_faces_absent)
check("no detected face yields present=False and layout_state=off_camera", r_absent.present is False and r_absent.layout_state == OFF_CAMERA)
check("confidence and n_faces are zeroed when absent", r_absent.confidence == 0.0 and r_absent.n_faces == 0)

# layout_state is fully determined by the detection result, not by any
# external/stateful classifier - calling the function twice with the same
# inputs must give the identical result (no hidden state, no history
# dependence, unlike the withdrawn persistence-smoother design).
r_present_2 = detect_candidate_presence(frame, timestamp=10.0, model_path=None, detect_faces_fn=_fake_detect_faces_present)
check("detection is stateless/deterministic across repeated calls", r_present == r_present_2)

# CandidateFrameResult schema check
cfr = CandidateFrameResult(timestamp=1.0, layout_state=FULL_VIEW, present=True, confidence=0.9, n_faces=1)
check("CandidateFrameResult exposes timestamp/layout_state/present/confidence/n_faces",
      (cfr.timestamp, cfr.layout_state, cfr.present, cfr.confidence, cfr.n_faces) == (1.0, FULL_VIEW, True, 0.9, 1))

print(f"\n{passed} passed, {failed} failed")
if failed:
    sys.exit(1)
