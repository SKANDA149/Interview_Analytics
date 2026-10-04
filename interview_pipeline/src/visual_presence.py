"""Candidate face presence / visibility (head-to-chest) - visual analysis module.

Synchronizes with the existing diarization + speaker-role pipeline
(diarization.py -> speaker_roles.py) rather than reimplementing any of it.
Visual analysis (frame sampling, face/pose detection, visibility scoring)
is only ever performed inside the candidate's speaking intervals.

Status: rebuilt in this copy of the project (2026-09) following the
originally-confirmed 9-step implementation plan. Design decisions (model
choice, thresholds, candidate-selection heuristic, segment-first sampling
strategy) match the original build:
  [x] Step 1 - candidate segment extraction
  [x] Step 2 - 5 FPS timestamp generation within candidate segments
  [x] Step 3 - frame sampling from the source video (direct seek, segment-first)
  [x] Step 4 - YuNet face detection
  [x] Step 5 - MediaPipe BlazePose-Lite pose detection
  [x] Step 6 - candidate instance selection (largest-bbox heuristic)
  [x] Step 7 - per-sample visibility classification
  [x] Step 8 - aggregation (presence rate, avg full-visibility %, absence events)
  [x] Step 9 - run_visual_presence_analysis() orchestrator entry point
"""
from dataclasses import dataclass
from pathlib import Path

try:
    from .diarization import DiarizationSegment
except ImportError:
    from interview_pipeline.src.diarization import DiarizationSegment

import cv2

# ---------------------------------------------------------------------------
# Config (fixed defaults for v1 - explicitly subject to change later).
# ---------------------------------------------------------------------------

SAMPLE_FPS = 5                          # fixed requirement, not tunable
FACE_CONFIDENCE_THRESHOLD = 0.6         # YuNet detection confidence floor
SHOULDER_VISIBILITY_THRESHOLD = 0.5     # BlazePose landmark 11/12 visibility floor
ABSENCE_EVENT_FLOOR_SECONDS = 1.0       # min contiguous gap to count as a face-loss event
CANDIDATE_LABEL = "CANDIDATE"           # matches speaker_roles.py's role label

# Model paths: plain relative Path("models/..."), resolved against the
# current working directory (the project root, run from there).
YUNET_MODEL_PATH = Path("models/yunet/face_detection_yunet_2023mar.onnx")
POSE_LANDMARKER_MODEL_PATH = Path("models/pose_landmarker/pose_landmarker_lite.task")

MIN_POSE_DETECTION_CONFIDENCE = 0.5     # MediaPipe's own detector-stage confidence floor
MIN_POSE_PRESENCE_CONFIDENCE = 0.5      # MediaPipe's own landmark-stage presence floor
MAX_POSES_PER_FRAME = 4                 # generous cap for "other people may appear"

AMBIGUOUS_SIZE_RATIO = 0.9              # two faces this close in bbox area -> "uncertain"
FACE_POSE_MATCH_PADDING = 0.3           # fractional bbox padding when matching a pose's nose to a face

NO_FACE_STATUS = "no_face"
SELECTED_STATUS = "selected"
UNCERTAIN_STATUS = "uncertain"

ABSENT_STATUS = "absent"
PARTIALLY_VISIBLE_STATUS = "partially_visible"
FULLY_VISIBLE_STATUS = "fully_visible"

# A run of absent samples continues across a timestamp gap only if that gap
# stays within 1.5 sample-intervals - stops absence runs from bridging across
# a candidate-segment boundary where there's no visual data at all.
MAX_SAMPLE_GAP_FOR_RUN_CONTINUITY_SECONDS = 1.5 / SAMPLE_FPS


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SampleTimestamp:
    """One point in time to sample, carrying its parent segment's bounds
    along for later steps (frame retrieval, per-segment aggregation)."""
    timestamp: float
    segment_start: float
    segment_end: float


@dataclass
class FrameSample:
    """A retrieved (or failed-to-retrieve) video frame for one SampleTimestamp."""
    timestamp: float
    segment_start: float
    segment_end: float
    frame: object   # numpy.ndarray (BGR) when success is True, else None
    success: bool


@dataclass
class FaceDetection:
    """One face YuNet found in a frame."""
    bbox: tuple        # (x, y, w, h) in pixels, top-left origin
    confidence: float  # YuNet's own detection score, 0-1
    landmarks: list    # 5 (x, y) pixel points: right eye, left eye, nose tip,
                        # right mouth corner, left mouth corner


@dataclass
class PoseLandmark:
    """One of BlazePose's 33 body landmarks, in pixel coordinates."""
    x: float
    y: float
    z: float
    visibility: float   # 0-1, confidence the landmark is in-frame and unoccluded
    presence: float     # 0-1, confidence the landmark exists in the image at all


@dataclass
class PoseDetection:
    """One person's 33-point BlazePose skeleton for a single frame."""
    landmarks: list      # 33 PoseLandmark objects; 11/12 = left/right shoulder


@dataclass
class CandidateInstance:
    """The outcome of select_candidate_instance() for one sampled frame."""
    status: str          # NO_FACE_STATUS / SELECTED_STATUS / UNCERTAIN_STATUS
    face: object = None  # FaceDetection, when status == SELECTED_STATUS; else None
    pose: object = None  # PoseDetection, when a pose was matched; else None


@dataclass
class VisibilityClassification:
    """The outcome of classify_sample() for one sampled frame."""
    classification: str                # ABSENT / PARTIALLY_VISIBLE / FULLY_VISIBLE / UNCERTAIN
    face_confidence: float = None
    left_shoulder_visibility: float = None
    right_shoulder_visibility: float = None
    has_matched_pose: bool = False


@dataclass
class SampleResult:
    """One fully-processed sampled frame - what the orchestrator produces
    per timestamp, and what aggregate() consumes."""
    timestamp: float
    num_faces: int
    visibility: VisibilityClassification


@dataclass
class AbsenceRun:
    """One contiguous run of ABSENT_STATUS samples, found by aggregate()."""
    start_timestamp: float
    end_timestamp: float
    duration: float
    num_samples: int


@dataclass
class AggregateMetrics:
    """The whole-video (or whole-batch) summary aggregate() produces."""
    total_samples: int
    uncertain_samples: int
    scored_samples: int

    absent_samples: int
    partially_visible_samples: int
    fully_visible_samples: int

    presence_rate: float
    full_visibility_rate: float
    partial_visibility_rate: float

    absence_runs: list
    longest_continuous_absence_seconds: float
    face_loss_event_count: int

    multiple_face_events: int


# ---------------------------------------------------------------------------
# Step 1: candidate segment extraction
# ---------------------------------------------------------------------------

def get_candidate_segments(diarization_segments: list) -> list:
    """Filter diarization output down to CANDIDATE-labelled intervals.
    Thin wrapper - no new diarization/role-assignment logic here."""
    candidate_segments = [seg for seg in diarization_segments if seg.speaker == CANDIDATE_LABEL]
    if not candidate_segments:
        print("[VISUAL] No segments labelled 'CANDIDATE' found - check speaker_roles output.")
    else:
        total_duration = sum(seg.end - seg.start for seg in candidate_segments)
        print(f"[VISUAL] Found {len(candidate_segments)} candidate segment(s), "
              f"{total_duration:.1f}s total speaking time to sample at {SAMPLE_FPS} FPS.")
    return candidate_segments


# ---------------------------------------------------------------------------
# Step 2: 5 FPS timestamp generation within candidate segments
# ---------------------------------------------------------------------------

def generate_sample_timestamps(candidate_segments: list, fps: int = SAMPLE_FPS) -> list:
    """Flatten each candidate segment into a list of SampleTimestamp at
    1/fps spacing. Uses index multiplication (start + i*step), not
    accumulated float addition, to avoid floating-point drift near segment
    boundaries."""
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")

    step = 1.0 / fps
    timestamps = []
    for seg in candidate_segments:
        duration = seg.end - seg.start
        if duration <= 0:
            print(f"[VISUAL] Skipping zero/negative-duration segment {seg.start:.2f}-{seg.end:.2f}")
            continue
        n_steps = int(duration * fps + 1e-9)
        for i in range(n_steps + 1):
            t = round(seg.start + i * step, 3)
            if t > seg.end + 1e-9:
                break
            timestamps.append(SampleTimestamp(timestamp=t, segment_start=seg.start, segment_end=seg.end))

    print(f"[VISUAL] Generated {len(timestamps)} sample timestamp(s) at {fps} FPS "
          f"across {len(candidate_segments)} candidate segment(s).")
    return timestamps


# ---------------------------------------------------------------------------
# Step 3: frame sampling from the source video (direct seek, segment-first)
# ---------------------------------------------------------------------------

def sample_frame(video_path, timestamp: float):
    """Seek the source video to `timestamp` (seconds) and grab one frame.
    Returns a BGR numpy array, or None if the frame couldn't be read
    (video missing, timestamp past the end, decode failure, etc.)."""
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"[VISUAL] Video not found: {video_path}")
        return None

    cap = cv2.VideoCapture(str(video_path))
    try:
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
        success, frame = cap.read()
        if not success or frame is None:
            print(f"[VISUAL] Failed to read frame at {timestamp:.2f}s "
                  f"(past end of video, or an unreadable frame)")
            return None
        return frame
    finally:
        cap.release()


def sample_frames(video_path, sample_timestamps: list) -> list:
    """Batched version of sample_frame() - one VideoCapture reused across
    every timestamp for the same video, rather than reopening per-frame."""
    video_path = Path(video_path)
    results = []

    if not video_path.exists():
        print(f"[VISUAL] Video not found: {video_path}")
        for st in sample_timestamps:
            results.append(FrameSample(
                timestamp=st.timestamp, segment_start=st.segment_start,
                segment_end=st.segment_end, frame=None, success=False,
            ))
        return results

    cap = cv2.VideoCapture(str(video_path))
    try:
        failures = 0
        for st in sample_timestamps:
            cap.set(cv2.CAP_PROP_POS_MSEC, st.timestamp * 1000.0)
            success, frame = cap.read()
            if not success or frame is None:
                failures += 1
                results.append(FrameSample(
                    timestamp=st.timestamp, segment_start=st.segment_start,
                    segment_end=st.segment_end, frame=None, success=False,
                ))
            else:
                results.append(FrameSample(
                    timestamp=st.timestamp, segment_start=st.segment_start,
                    segment_end=st.segment_end, frame=frame, success=True,
                ))
        if failures:
            print(f"[VISUAL] {failures} sample timestamp(s) had unreadable frames and were skipped.")
        else:
            print(f"[VISUAL] Successfully read all {len(sample_timestamps)} sampled frame(s) "
                  f"from {video_path.name}.")
    finally:
        cap.release()

    return results


# ---------------------------------------------------------------------------
# Step 4: YuNet face detection
# ---------------------------------------------------------------------------

_yunet_detector_cache = {}


def _get_yunet_detector(model_path: Path, input_size: tuple):
    key = (str(model_path), input_size)
    if key not in _yunet_detector_cache:
        if not Path(model_path).exists():
            raise FileNotFoundError(f"YuNet model not found at {model_path}")
        _yunet_detector_cache[key] = cv2.FaceDetectorYN.create(
            str(model_path), "", input_size, score_threshold=0.0,
        )
    return _yunet_detector_cache[key]


def detect_faces(frame, model_path: Path = YUNET_MODEL_PATH) -> list:
    """Run YuNet face detection on one frame. Returns a list of
    FaceDetection with confidence >= FACE_CONFIDENCE_THRESHOLD."""
    if frame is None:
        return []

    h, w = frame.shape[:2]
    detector = _get_yunet_detector(model_path, (w, h))
    detector.setInputSize((w, h))

    _, faces = detector.detect(frame)
    if faces is None:
        return []

    results = []
    for row in faces:
        confidence = float(row[14])
        if confidence < FACE_CONFIDENCE_THRESHOLD:
            continue
        bbox = (float(row[0]), float(row[1]), float(row[2]), float(row[3]))
        landmarks = [(float(row[4 + 2 * i]), float(row[5 + 2 * i])) for i in range(5)]
        results.append(FaceDetection(bbox=bbox, confidence=confidence, landmarks=landmarks))
    return results


# ---------------------------------------------------------------------------
# Step 5: MediaPipe BlazePose-Lite pose detection
# ---------------------------------------------------------------------------

_pose_landmarker_cache = {}


def _get_pose_landmarker(model_path: Path):
    key = str(model_path)
    if key not in _pose_landmarker_cache:
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Pose landmarker model not found at {model_path}")
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision

        base_options = mp_python.BaseOptions(model_asset_path=str(model_path))
        options = mp_vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
            num_poses=MAX_POSES_PER_FRAME,
            min_pose_detection_confidence=MIN_POSE_DETECTION_CONFIDENCE,
            min_pose_presence_confidence=MIN_POSE_PRESENCE_CONFIDENCE,
        )
        _pose_landmarker_cache[key] = mp_vision.PoseLandmarker.create_from_options(options)
    return _pose_landmarker_cache[key]


def detect_poses(frame, model_path: Path = POSE_LANDMARKER_MODEL_PATH) -> list:
    """Run BlazePose-Lite on one frame. Returns a list of PoseDetection,
    landmarks converted from MediaPipe's 0-1 normalized coords to pixels."""
    if frame is None:
        return []

    import mediapipe as mp

    h, w = frame.shape[:2]
    landmarker = _get_pose_landmarker(model_path)

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    result = landmarker.detect(mp_image)
    if not result.pose_landmarks:
        return []

    poses = []
    for person_landmarks in result.pose_landmarks:
        landmarks = [
            PoseLandmark(
                x=lm.x * w, y=lm.y * h, z=lm.z,
                visibility=lm.visibility, presence=lm.presence,
            )
            for lm in person_landmarks
        ]
        poses.append(PoseDetection(landmarks=landmarks))
    return poses


# ---------------------------------------------------------------------------
# Step 6: candidate instance selection (largest-bbox heuristic)
# ---------------------------------------------------------------------------

def _face_bbox_area(face: FaceDetection) -> float:
    _, _, w, h = face.bbox
    return max(0.0, w) * max(0.0, h)


def _pose_matches_face(pose: "PoseDetection", face: FaceDetection) -> bool:
    """A pose "matches" a face if its nose landmark (index 0) falls inside
    the face's bbox, padded by FACE_POSE_MATCH_PADDING on each side."""
    x, y, w, h = face.bbox
    pad_x, pad_y = w * FACE_POSE_MATCH_PADDING, h * FACE_POSE_MATCH_PADDING
    x0, y0 = x - pad_x, y - pad_y
    x1, y1 = x + w + pad_x, y + h + pad_y

    nose = pose.landmarks[0]
    return x0 <= nose.x <= x1 and y0 <= nose.y <= y1


def _find_matching_pose(face: FaceDetection, poses: list):
    """Among poses whose nose falls inside face's (padded) bbox, pick the
    one whose nose is closest to the face's own center."""
    fx, fy, fw, fh = face.bbox
    face_center = (fx + fw / 2.0, fy + fh / 2.0)

    candidates = [p for p in poses if _pose_matches_face(p, face)]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    def dist(p):
        nose = p.landmarks[0]
        return (nose.x - face_center[0]) ** 2 + (nose.y - face_center[1]) ** 2

    return min(candidates, key=dist)


def select_candidate_instance(faces: list, poses: list) -> CandidateInstance:
    """Pick the candidate's face (and matching pose, if any) among all
    detected faces in a frame. Diarization has no spatial information, so
    this uses a largest-bounding-box heuristic: the biggest face is assumed
    to be the person closest to the camera / most prominent, i.e. the
    candidate. If the top two faces are near-identical in size
    (AMBIGUOUS_SIZE_RATIO), the frame is marked UNCERTAIN rather than
    guessing."""
    if not faces:
        return CandidateInstance(status=NO_FACE_STATUS)

    sorted_faces = sorted(faces, key=_face_bbox_area, reverse=True)

    if len(sorted_faces) >= 2:
        largest_area = _face_bbox_area(sorted_faces[0])
        second_area = _face_bbox_area(sorted_faces[1])
        if largest_area > 0 and (second_area / largest_area) > AMBIGUOUS_SIZE_RATIO:
            print(f"[VISUAL] {len(faces)} faces detected, top 2 too similar in size "
                  f"(ratio={second_area / largest_area:.2f} > {AMBIGUOUS_SIZE_RATIO}) - "
                  f"marking uncertain.")
            return CandidateInstance(status=UNCERTAIN_STATUS)

    chosen_face = sorted_faces[0]
    matched_pose = _find_matching_pose(chosen_face, poses)
    return CandidateInstance(status=SELECTED_STATUS, face=chosen_face, pose=matched_pose)


# ---------------------------------------------------------------------------
# Step 7: per-sample visibility classification
# ---------------------------------------------------------------------------

def classify_sample(candidate_instance: CandidateInstance) -> VisibilityClassification:
    """Apply the head-to-chest visibility rule to one CandidateInstance.

    fully_visible  = a face was selected AND both shoulder landmarks
                      (BlazePose idx 11/12) have visibility >= threshold.
    partially_visible = a face was selected but shoulder data doesn't clear
                      the bar (no matched pose, or one/both shoulders below
                      threshold) - never a negative/penalized outcome.
    absent         = no face was detected in the frame at all.
    uncertain      = candidate identity itself was ambiguous (step 6) -
                      passed straight through, untouched.
    """
    if candidate_instance.status == UNCERTAIN_STATUS:
        return VisibilityClassification(classification=UNCERTAIN_STATUS)

    if candidate_instance.status == NO_FACE_STATUS:
        return VisibilityClassification(classification=ABSENT_STATUS)

    face = candidate_instance.face
    pose = candidate_instance.pose

    if pose is None:
        return VisibilityClassification(
            classification=PARTIALLY_VISIBLE_STATUS,
            face_confidence=face.confidence,
            has_matched_pose=False,
        )

    left_shoulder = pose.landmarks[11].visibility
    right_shoulder = pose.landmarks[12].visibility

    if left_shoulder >= SHOULDER_VISIBILITY_THRESHOLD and right_shoulder >= SHOULDER_VISIBILITY_THRESHOLD:
        classification = FULLY_VISIBLE_STATUS
    else:
        classification = PARTIALLY_VISIBLE_STATUS

    return VisibilityClassification(
        classification=classification,
        face_confidence=face.confidence,
        left_shoulder_visibility=left_shoulder,
        right_shoulder_visibility=right_shoulder,
        has_matched_pose=True,
    )


# ---------------------------------------------------------------------------
# Step 8: aggregation
# ---------------------------------------------------------------------------

def aggregate(samples: list) -> AggregateMetrics:
    """
    Roll up a list of per-sample SampleResult records into the project's
    confirmed aggregate shape: one average visibility percentage across the
    whole video, plus presence/absence detail.

    UNCERTAIN_STATUS samples are counted and reported, but excluded from
    every rate calculation's denominator: they represent "we don't know,"
    not "absent" or "visible."

    Absence runs are built over the chronologically-sorted SCORED samples
    only - a run only continues across samples that are actually temporally
    adjacent (see MAX_SAMPLE_GAP_FOR_RUN_CONTINUITY_SECONDS), so a run never
    bridges across a candidate-segment boundary.
    """
    total_samples = len(samples)
    uncertain = [s for s in samples if s.visibility.classification == UNCERTAIN_STATUS]
    scored = sorted(
        (s for s in samples if s.visibility.classification != UNCERTAIN_STATUS),
        key=lambda s: s.timestamp,
    )

    absent = [s for s in scored if s.visibility.classification == ABSENT_STATUS]
    partial = [s for s in scored if s.visibility.classification == PARTIALLY_VISIBLE_STATUS]
    full = [s for s in scored if s.visibility.classification == FULLY_VISIBLE_STATUS]
    scored_count = len(scored)

    if scored_count:
        presence_rate = (len(partial) + len(full)) / scored_count
        full_visibility_rate = len(full) / scored_count
        partial_visibility_rate = len(partial) / scored_count
    else:
        presence_rate = None
        full_visibility_rate = None
        partial_visibility_rate = None

    absence_runs = []
    current_run = []

    def _flush_current_run():
        if not current_run:
            return
        start = current_run[0].timestamp
        end = current_run[-1].timestamp
        duration = (end - start) + (1.0 / SAMPLE_FPS)
        absence_runs.append(
            AbsenceRun(start_timestamp=start, end_timestamp=end, duration=duration, num_samples=len(current_run))
        )

    previous_sample = None
    for sample in scored:
        is_absent = sample.visibility.classification == ABSENT_STATUS
        if is_absent:
            if current_run and previous_sample is not None:
                gap = sample.timestamp - previous_sample.timestamp
                if gap > MAX_SAMPLE_GAP_FOR_RUN_CONTINUITY_SECONDS:
                    _flush_current_run()
                    current_run = []
            current_run.append(sample)
        else:
            _flush_current_run()
            current_run = []
        previous_sample = sample
    _flush_current_run()

    longest_continuous_absence_seconds = max((r.duration for r in absence_runs), default=0.0)
    face_loss_event_count = sum(1 for r in absence_runs if r.duration >= ABSENCE_EVENT_FLOOR_SECONDS)
    multiple_face_events = sum(1 for s in samples if s.num_faces >= 2)

    print(
        f"[VISUAL] Aggregated {total_samples} sample(s) ({len(uncertain)} uncertain, excluded from rates): "
        f"full={full_visibility_rate if full_visibility_rate is None else f'{full_visibility_rate:.1%}'}, "
        f"presence={presence_rate if presence_rate is None else f'{presence_rate:.1%}'}, "
        f"{len(absence_runs)} absence run(s), {face_loss_event_count} face-loss event(s), "
        f"longest={longest_continuous_absence_seconds:.1f}s."
    )

    return AggregateMetrics(
        total_samples=total_samples,
        uncertain_samples=len(uncertain),
        scored_samples=scored_count,
        absent_samples=len(absent),
        partially_visible_samples=len(partial),
        fully_visible_samples=len(full),
        presence_rate=presence_rate,
        full_visibility_rate=full_visibility_rate,
        partial_visibility_rate=partial_visibility_rate,
        absence_runs=absence_runs,
        longest_continuous_absence_seconds=longest_continuous_absence_seconds,
        face_loss_event_count=face_loss_event_count,
        multiple_face_events=multiple_face_events,
    )


# ---------------------------------------------------------------------------
# Step 9: orchestrator - ties steps 1-8 together into one entry point.
# ---------------------------------------------------------------------------

def _sample_result_to_dict(sample: SampleResult) -> dict:
    v = sample.visibility
    return {
        "timestamp": round(sample.timestamp, 3),
        "num_faces_detected": sample.num_faces,
        "classification": v.classification,
        "face_confidence": v.face_confidence,
        "left_shoulder_visibility": v.left_shoulder_visibility,
        "right_shoulder_visibility": v.right_shoulder_visibility,
        "has_matched_pose": v.has_matched_pose,
    }


def _absence_run_to_dict(run: AbsenceRun) -> dict:
    return {
        "start_timestamp": round(run.start_timestamp, 3),
        "end_timestamp": round(run.end_timestamp, 3),
        "duration_seconds": round(run.duration, 3),
        "num_samples": run.num_samples,
    }


def _aggregate_metrics_to_dict(metrics: AggregateMetrics) -> dict:
    def _rate(x):
        return None if x is None else round(x, 4)

    return {
        "total_samples": metrics.total_samples,
        "uncertain_samples": metrics.uncertain_samples,
        "scored_samples": metrics.scored_samples,
        "absent_samples": metrics.absent_samples,
        "partially_visible_samples": metrics.partially_visible_samples,
        "fully_visible_samples": metrics.fully_visible_samples,
        "presence_rate": _rate(metrics.presence_rate),
        "full_visibility_rate": _rate(metrics.full_visibility_rate),
        "partial_visibility_rate": _rate(metrics.partial_visibility_rate),
        "longest_continuous_absence_seconds": round(metrics.longest_continuous_absence_seconds, 3),
        "face_loss_event_count": metrics.face_loss_event_count,
        "multiple_face_events": metrics.multiple_face_events,
        "absence_runs": [_absence_run_to_dict(r) for r in metrics.absence_runs],
    }


def run_visual_presence_analysis(video_path, diarization_segments: list) -> dict:
    """Orchestrates steps 1-8 end to end for one video. See module docstring
    for the pipeline this ties together. Returns:
        {
            "video_path": str,
            "candidate_segment_count": int,
            "sample_fps": int,
            "timestamped_results": [ ...one dict per successfully-read sample ],
            "aggregate": { ...whole-video summary },
        }
    No CANDIDATE segments is not an error - it just means there's nothing to
    visually analyze, and the result comes back empty rather than raising.
    """
    video_path = Path(video_path)

    candidate_segments = get_candidate_segments(diarization_segments)
    print(
        f"[VISUAL] run_visual_presence_analysis: {len(candidate_segments)} CANDIDATE "
        f"segment(s) found in diarization output for {video_path.name}."
    )

    if not candidate_segments:
        empty_aggregate = aggregate([])
        return {
            "video_path": str(video_path),
            "candidate_segment_count": 0,
            "sample_fps": SAMPLE_FPS,
            "timestamped_results": [],
            "aggregate": _aggregate_metrics_to_dict(empty_aggregate),
        }

    sample_timestamps = generate_sample_timestamps(candidate_segments, fps=SAMPLE_FPS)
    frame_samples = sample_frames(video_path, sample_timestamps)

    sample_results = []
    failed_reads = 0
    for frame_sample in frame_samples:
        if not frame_sample.success:
            failed_reads += 1
            continue
        faces = detect_faces(frame_sample.frame)
        poses = detect_poses(frame_sample.frame)
        instance = select_candidate_instance(faces, poses)
        classification = classify_sample(instance)
        sample_results.append(
            SampleResult(
                timestamp=frame_sample.timestamp,
                num_faces=len(faces),
                visibility=classification,
            )
        )

    if failed_reads:
        print(f"[VISUAL] {failed_reads} sample timestamp(s) had unreadable frames and were skipped.")

    metrics = aggregate(sample_results)

    return {
        "video_path": str(video_path),
        "candidate_segment_count": len(candidate_segments),
        "sample_fps": SAMPLE_FPS,
        "timestamped_results": [_sample_result_to_dict(s) for s in sample_results],
        "aggregate": _aggregate_metrics_to_dict(metrics),
    }


# ---------------------------------------------------------------------------
# pipeline.py integration helpers - pure functions over
# run_visual_presence_analysis()'s output, kept here so they're
# independently unit-testable without needing pipeline.py's heavier
# stage-1..11 dependencies importable.
# ---------------------------------------------------------------------------

def summarize_visual_metrics(analysis_result: dict) -> dict:
    """Flatten run_visual_presence_analysis()'s "aggregate" block into a
    flat dict suitable for a final report's candidate_metrics.visual.
    Percentages are 0-100 (not 0-1 fractions). None rates (no scored
    samples) pass through as None, not 0.0 or "N/A"."""
    agg = analysis_result["aggregate"]

    def _pct(rate):
        return None if rate is None else round(rate * 100, 1)

    return {
        "face_visibility_pct": _pct(agg["full_visibility_rate"]),
        "presence_pct": _pct(agg["presence_rate"]),
        "partial_visibility_pct": _pct(agg["partial_visibility_rate"]),
        "head_posture_score": "N/A",  # not modeled by this module - head-to-chest presence only
        "total_samples": agg["total_samples"],
        "scored_samples": agg["scored_samples"],
        "uncertain_samples": agg["uncertain_samples"],
        "face_loss_event_count": agg["face_loss_event_count"],
        "longest_continuous_absence_sec": agg["longest_continuous_absence_seconds"],
        "multiple_face_events": agg["multiple_face_events"],
        "absence_runs": agg["absence_runs"],
    }


def bucket_visual_results_by_chunk(analysis_result: dict, chunk_start: float, chunk_end: float) -> dict:
    """Slice run_visual_presence_analysis()'s whole-video, segment-first
    "timestamped_results" down to one chunk's [chunk_start, chunk_end) time
    window and compute that chunk's own full-visibility rate - for a
    per-chunk report timeline that predates this module's segment-first
    design and still expects one number per chunk.

    Samples with classification "uncertain" are excluded from the rate.
    Returns {"face_visibility_pct": float 0-100, "n_samples": int} when the
    chunk has at least one scoreable sample, or
    {"face_visibility_pct": "N/A", "n_samples": 0} when it has none.
    """
    samples = [
        s for s in analysis_result.get("timestamped_results", [])
        if chunk_start <= s["timestamp"] < chunk_end and s["classification"] != UNCERTAIN_STATUS
    ]
    if not samples:
        return {"face_visibility_pct": "N/A", "n_samples": 0}

    full_visible = sum(1 for s in samples if s["classification"] == FULLY_VISIBLE_STATUS)
    return {
        "face_visibility_pct": round((full_visible / len(samples)) * 100, 1),
        "n_samples": len(samples),
    }
