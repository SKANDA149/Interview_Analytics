"""
research_visual_gating/candidate_layout.py

CORRECTED (2026-09-13, recalibration pass) candidate identification for
video1_infosys_h264.mp4. The first version of this module had the
candidate and interviewer regions SWAPPED - see
vad-gated-video1-infosys-recalibration.md for the full audit. That
version routed detection to a large main tile based on a pixel-brightness
layout classifier (off_camera / full_view / screen_share), assuming the
candidate's own video tile changed shape when the call switched to screen
sharing. Inspection of real frames showed the opposite: the large tile
is a heavily compressed, largely undetectable feed from the INTERVIEWER
(sometimes two interviewers at once), while the small, fixed, always-
sharp bottom-right thumbnail - locally rendered, not network-compressed -
is the CANDIDATE's own self-view, and it does not move, resize, or change
shape when the interviewer's tile switches to screen-share. A 1529-sample,
1Hz sweep of that fixed region across the whole recording found real,
non-saturated variation (91.82% present, 57 discrete absence intervals,
longest 24s) and confirmed the region's position/size is stable at all
10 spot-checked timestamps (30/60/250/500/700/850/950/1100/1250/1450s),
including during the interviewer's screen-share window.

Consequence: no separate "screen_share" layout state is needed for the
CANDIDATE (that concept described the INTERVIEWER's tile, not the
candidate's), so this module no longer implements one. Per the explicit
instruction not to build a complex layout model unless the video
demonstrates it's necessary, layout state here is now derived directly
from the detection result on ONE fixed region, not decided in advance by
a separate pixel-brightness classifier routing to different crops. There
is therefore also no need for the previous version's stateful
persistence/hysteresis smoother: a fixed single-ROI detection is fully
deterministic per frame and requires no continuity across neighboring
frames to be well-defined, so any condition (any subset of grid frames,
processed in any order or split across multiple calls) produces the
identical layout_state for a given timestamp with no shared/precomputed
state required.

Explicitly NOT used anywhere in this file: diarization, speaker
attribution, face embeddings, face recognition, or OCR. Candidate
presence is decided by the existing, frozen YuNet `detect_faces()` from
`interview_pipeline/src/visual_presence.py`, run against this file's one
fixed candidate ROI - never the interviewer's tile.

ROI coordinates are calibrated for video1_infosys_h264.mp4's exact
resolution (1280x720) and are NOT valid for any other recording.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

FULL_VIEW = "full_view"     # candidate visible (a face was detected in CANDIDATE_ROI)
OFF_CAMERA = "off_camera"   # candidate not visible (no face detected in CANDIDATE_ROI)

# The candidate's fixed self-view thumbnail. Confirmed spatially stable
# (same position/size) at t=30/60/250/500/700/850/950/1100/1250/1450s,
# including through the interviewer's screen-share window - see the
# recalibration report for the stability contact sheet.
CANDIDATE_ROI = (1075, 560, 205, 160)

# The interviewer's (sometimes two interviewers') large tile. Kept here
# only for documentation / possible future non-candidate analysis - NEVER
# used to decide candidate presence. YuNet detects a face in this region
# in roughly 2.5% of sparse whole-video samples (heavy compression makes
# most frames undetectable); this module does not attempt to fix that,
# since the interviewer's visibility is out of scope for this study.
INTERVIEWER_ROI = (0, 118, 893, 545)


def candidate_roi_for_state(layout_state: str) -> Optional[tuple]:
    """Kept for interface compatibility with the pilot runner. Always
    returns CANDIDATE_ROI for full_view; off_camera has no ROI to
    re-crop (there is nothing further to do once absence is already
    known) - callers should not call this to decide WHETHER to detect,
    only to report which crop a full_view detection came from."""
    if layout_state == FULL_VIEW:
        return CANDIDATE_ROI
    return None


@dataclass
class CandidateFrameResult:
    """timestamp: float, layout_state: one of FULL_VIEW/OFF_CAMERA
    (derived FROM the detection result, not decided ahead of it),
    present: bool, confidence: float, n_faces: int."""
    timestamp: float
    layout_state: str
    present: bool
    confidence: float
    n_faces: int


def detect_candidate_presence(frame: np.ndarray, timestamp: float, model_path, detect_faces_fn) -> CandidateFrameResult:
    """Crops the ONE fixed CANDIDATE_ROI and runs the frozen detect_faces_fn
    against it - never the interviewer's tile, never the whole frame.
    layout_state is FULL_VIEW iff a face was found, OFF_CAMERA otherwise;
    there is no separate classification step and nothing stateful."""
    x, y, w, h = CANDIDATE_ROI
    crop = frame[y:y + h, x:x + w]
    faces = detect_faces_fn(crop, model_path=model_path)
    if not faces:
        return CandidateFrameResult(timestamp=timestamp, layout_state=OFF_CAMERA,
                                     present=False, confidence=0.0, n_faces=0)
    best = max(faces, key=lambda f: f.confidence)
    return CandidateFrameResult(timestamp=timestamp, layout_state=FULL_VIEW,
                                 present=True, confidence=best.confidence, n_faces=len(faces))
