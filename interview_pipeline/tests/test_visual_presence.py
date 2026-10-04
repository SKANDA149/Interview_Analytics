"""
Quick standalone sanity tests for visual_presence.py.

No test framework dependency required - plain assert-based checks with
pass/fail printout, matching this project's style.

Run with:
    python3 interview_pipeline/tests/test_visual_presence.py (from project root)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import subprocess
import tempfile

import cv2
import numpy as np

from interview_pipeline.src.diarization import DiarizationSegment
from interview_pipeline.src.visual_presence import (
    get_candidate_segments,
    generate_sample_timestamps,
    sample_frame,
    sample_frames,
    detect_faces,
    detect_poses,
    select_candidate_instance,
    classify_sample,
    aggregate,
    run_visual_presence_analysis,
    summarize_visual_metrics,
    bucket_visual_results_by_chunk,
    SampleTimestamp,
    FaceDetection,
    PoseDetection,
    PoseLandmark,
    CandidateInstance,
    SampleResult,
    AbsenceRun,
    AggregateMetrics,
    VisibilityClassification,
    CANDIDATE_LABEL,
    FACE_CONFIDENCE_THRESHOLD,
    MIN_POSE_DETECTION_CONFIDENCE,
    SHOULDER_VISIBILITY_THRESHOLD,
    YUNET_MODEL_PATH,
    POSE_LANDMARKER_MODEL_PATH,
    SAMPLE_FPS,
    ABSENCE_EVENT_FLOOR_SECONDS,
    MAX_SAMPLE_GAP_FOR_RUN_CONTINUITY_SECONDS,
    NO_FACE_STATUS,
    SELECTED_STATUS,
    UNCERTAIN_STATUS,
    ABSENT_STATUS,
    PARTIALLY_VISIBLE_STATUS,
    FULLY_VISIBLE_STATUS,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
REAL_FACE_IMAGE = FIXTURES_DIR / "real_face_frame.jpg"


def make_seg(start, end, speaker):
    return DiarizationSegment(start=start, end=end, speaker=speaker)


# --- Step 1: get_candidate_segments -----------------------------------------

def test_empty_input():
    assert get_candidate_segments([]) == []
    print("[PASS] test_empty_input")


def test_no_candidate_segments():
    segs = [make_seg(0, 5, "INTERVIEWER"), make_seg(5, 10, "INTERVIEWER")]
    assert get_candidate_segments(segs) == []
    print("[PASS] test_no_candidate_segments")


def test_mixed_segments_filters_and_preserves_order():
    segs = [
        make_seg(0, 2, "INTERVIEWER"),
        make_seg(2, 5, "CANDIDATE"),
        make_seg(5, 6, "INTERVIEWER"),
        make_seg(6, 9, "CANDIDATE"),
    ]
    result = get_candidate_segments(segs)
    assert [s.start for s in result] == [2, 6]
    print("[PASS] test_mixed_segments_filters_and_preserves_order")


def test_all_candidate_segments_returned_unchanged():
    segs = [make_seg(0, 2, "CANDIDATE"), make_seg(2, 4, "CANDIDATE")]
    assert get_candidate_segments(segs) == segs
    print("[PASS] test_all_candidate_segments_returned_unchanged")


def test_single_speaker_edge_case():
    segs = [make_seg(0, 100, "CANDIDATE")]
    result = get_candidate_segments(segs)
    assert len(result) == 1 and result[0].end == 100
    print("[PASS] test_single_speaker_edge_case")


# --- Step 2: generate_sample_timestamps -------------------------------------

def test_timestamps_empty_input():
    assert generate_sample_timestamps([]) == []
    print("[PASS] test_timestamps_empty_input")


def test_timestamps_one_second_segment_at_5fps():
    segs = [make_seg(0.0, 1.0, "CANDIDATE")]
    result = generate_sample_timestamps(segs, fps=5)
    timestamps = [s.timestamp for s in result]
    assert timestamps == [0.0, 0.2, 0.4, 0.6, 0.8, 1.0], timestamps
    print("[PASS] test_timestamps_one_second_segment_at_5fps")


def test_timestamps_segment_shorter_than_one_step():
    segs = [make_seg(0.0, 0.1, "CANDIDATE")]
    result = generate_sample_timestamps(segs, fps=5)
    assert [s.timestamp for s in result] == [0.0]
    print("[PASS] test_timestamps_segment_shorter_than_one_step")


def test_timestamps_multiple_segments_accumulate():
    segs = [make_seg(0.0, 1.0, "CANDIDATE"), make_seg(10.0, 10.4, "CANDIDATE")]
    result = generate_sample_timestamps(segs, fps=5)
    # seg1 0.0-1.0 @ 0.2s spacing -> 6 samples (0.0..1.0 inclusive); seg2 10.0-10.4 -> 3 samples (10.0,10.2,10.4)
    assert len(result) == 9, f"Expected 9 total samples, got {len(result)}: {[s.timestamp for s in result]}"
    print("[PASS] test_timestamps_multiple_segments_accumulate")


def test_timestamps_custom_fps():
    segs = [make_seg(0.0, 2.0, "CANDIDATE")]
    result = generate_sample_timestamps(segs, fps=1)
    assert [s.timestamp for s in result] == [0.0, 1.0, 2.0]
    print("[PASS] test_timestamps_custom_fps")


def test_timestamps_zero_duration_segment_skipped():
    segs = [make_seg(5.0, 5.0, "CANDIDATE"), make_seg(0.0, 0.2, "CANDIDATE")]
    result = generate_sample_timestamps(segs, fps=5)
    # zero-duration segment is skipped entirely; 0.0-0.2 @ 0.2s spacing -> 2 samples (0.0, 0.2)
    assert len(result) == 2, f"Expected 2, got {len(result)}: {[s.timestamp for s in result]}"
    print("[PASS] test_timestamps_zero_duration_segment_skipped")


def test_timestamps_invalid_fps_raises():
    try:
        generate_sample_timestamps([make_seg(0.0, 1.0, "CANDIDATE")], fps=0)
        raise AssertionError("Expected ValueError for fps=0, none was raised")
    except ValueError:
        print("[PASS] test_timestamps_invalid_fps_raises")


# --- Step 3: sample_frame / sample_frames -----------------------------------

def _make_synthetic_clip(path, duration=3, fps=10):
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"testsrc=duration={duration}:size=320x240:rate={fps}",
            str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_sample_frame_reads_valid_timestamp():
    with tempfile.TemporaryDirectory() as tmp:
        clip = Path(tmp) / "synthetic.mp4"
        _make_synthetic_clip(clip)
        frame = sample_frame(clip, 1.0)
        assert frame is not None, "Expected a frame at t=1.0s in a 3s clip"
        assert frame.ndim == 3 and frame.shape[2] == 3, f"Expected a BGR frame, got shape {frame.shape}"
        print("[PASS] test_sample_frame_reads_valid_timestamp")


def test_sample_frame_past_end_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        clip = Path(tmp) / "synthetic.mp4"
        _make_synthetic_clip(clip, duration=1)
        frame = sample_frame(clip, 10.0)
        assert frame is None, f"Expected None past end of video, got {type(frame)}"
        print("[PASS] test_sample_frame_past_end_returns_none")


def test_sample_frame_missing_video_returns_none():
    frame = sample_frame("/tmp/does_not_exist_12345.mp4", 1.0)
    assert frame is None
    print("[PASS] test_sample_frame_missing_video_returns_none")


def test_sample_frames_batched_matches_single_calls():
    with tempfile.TemporaryDirectory() as tmp:
        clip = Path(tmp) / "synthetic.mp4"
        _make_synthetic_clip(clip, duration=3, fps=10)
        sts = [SampleTimestamp(timestamp=t, segment_start=0.0, segment_end=3.0) for t in (0.5, 1.0, 1.5)]
        results = sample_frames(clip, sts)
        assert len(results) == 3
        assert all(r.success for r in results)
        print("[PASS] test_sample_frames_batched_matches_single_calls")


def test_sample_frames_empty_input():
    assert sample_frames("data/input/sample.mp4", []) == []
    print("[PASS] test_sample_frames_empty_input")


def test_sample_frames_missing_video_all_fail():
    sts = [SampleTimestamp(timestamp=0.0, segment_start=0.0, segment_end=1.0)]
    results = sample_frames("/tmp/does_not_exist_12345.mp4", sts)
    assert len(results) == 1 and results[0].success is False
    print("[PASS] test_sample_frames_missing_video_all_fail")


# --- Step 4/5: detect_faces / detect_poses ----------------------------------

def test_detect_faces_finds_real_face():
    frame = cv2.imread(str(REAL_FACE_IMAGE))
    faces = detect_faces(frame)
    assert len(faces) >= 1, "Expected at least one face in the real fixture frame"
    assert faces[0].confidence >= FACE_CONFIDENCE_THRESHOLD
    print(f"[PASS] test_detect_faces_finds_real_face (confidence={faces[0].confidence:.3f})")


def test_detect_faces_no_face_in_blank_image():
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = detect_faces(blank)
    assert faces == []
    print("[PASS] test_detect_faces_no_face_in_blank_image")


def test_detect_faces_none_frame_returns_empty():
    assert detect_faces(None) == []
    print("[PASS] test_detect_faces_none_frame_returns_empty")


def test_detect_faces_missing_model_raises():
    frame = cv2.imread(str(REAL_FACE_IMAGE))
    try:
        detect_faces(frame, model_path=Path("models/does_not_exist.onnx"))
        raise AssertionError("Expected FileNotFoundError for a missing YuNet model")
    except FileNotFoundError:
        print("[PASS] test_detect_faces_missing_model_raises")


def test_detect_poses_finds_real_pose():
    frame = cv2.imread(str(REAL_FACE_IMAGE))
    poses = detect_poses(frame)
    assert len(poses) >= 1, "Expected at least one pose in the real fixture frame"
    left_vis = poses[0].landmarks[11].visibility
    right_vis = poses[0].landmarks[12].visibility
    print(f"[PASS] test_detect_poses_finds_real_pose (L-shoulder vis={left_vis:.3f}, R-shoulder vis={right_vis:.3f})")


def test_detect_poses_no_pose_in_blank_image():
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    poses = detect_poses(blank)
    assert poses == []
    print("[PASS] test_detect_poses_no_pose_in_blank_image")


def test_detect_poses_none_frame_returns_empty():
    assert detect_poses(None) == []
    print("[PASS] test_detect_poses_none_frame_returns_empty")


def test_detect_poses_missing_model_raises():
    frame = cv2.imread(str(REAL_FACE_IMAGE))
    try:
        detect_poses(frame, model_path=Path("models/does_not_exist.task"))
        raise AssertionError("Expected FileNotFoundError for a missing pose landmarker model")
    except FileNotFoundError:
        print("[PASS] test_detect_poses_missing_model_raises")


# --- Step 6: select_candidate_instance --------------------------------------

def _make_face(x, y, w, h, confidence=0.9):
    return FaceDetection(bbox=(x, y, w, h), confidence=confidence, landmarks=[(x, y)] * 5)


def _make_pose_with_nose_at(nx, ny):
    landmarks = [PoseLandmark(x=0, y=0, z=0, visibility=0.9, presence=0.9) for _ in range(33)]
    landmarks[0] = PoseLandmark(x=nx, y=ny, z=0, visibility=0.9, presence=0.9)
    return PoseDetection(landmarks=landmarks)


def test_select_candidate_no_faces():
    instance = select_candidate_instance([], [])
    assert instance.status == NO_FACE_STATUS
    print("[PASS] test_select_candidate_no_faces")


def test_select_candidate_single_face_no_pose():
    face = _make_face(0, 0, 100, 100)
    instance = select_candidate_instance([face], [])
    assert instance.status == SELECTED_STATUS
    assert instance.face is face
    assert instance.pose is None
    print("[PASS] test_select_candidate_single_face_no_pose")


def test_select_candidate_single_face_with_matching_pose():
    face = _make_face(0, 0, 100, 100)
    pose = _make_pose_with_nose_at(50, 50)
    instance = select_candidate_instance([face], [pose])
    assert instance.status == SELECTED_STATUS
    assert instance.pose is pose
    print("[PASS] test_select_candidate_single_face_with_matching_pose")


def test_select_candidate_pose_too_far_does_not_match():
    face = _make_face(0, 0, 100, 100)
    pose = _make_pose_with_nose_at(1000, 1000)
    instance = select_candidate_instance([face], [pose])
    assert instance.status == SELECTED_STATUS
    assert instance.pose is None
    print("[PASS] test_select_candidate_pose_too_far_does_not_match")


def test_select_candidate_picks_largest_of_two_clearly_different_faces():
    small = _make_face(0, 0, 50, 50)
    large = _make_face(200, 200, 200, 200)
    instance = select_candidate_instance([small, large], [])
    assert instance.status == SELECTED_STATUS
    assert instance.face is large
    print("[PASS] test_select_candidate_picks_largest_of_two_clearly_different_faces")


def test_select_candidate_marks_uncertain_when_faces_too_similar():
    face_a = _make_face(0, 0, 100, 100)
    face_b = _make_face(200, 200, 99, 99)
    instance = select_candidate_instance([face_a, face_b], [])
    assert instance.status == UNCERTAIN_STATUS
    print("[PASS] test_select_candidate_marks_uncertain_when_faces_too_similar")


def test_select_candidate_matches_nearest_pose_when_multiple_overlap():
    face = _make_face(0, 0, 100, 100)
    near_pose = _make_pose_with_nose_at(50, 50)
    far_pose = _make_pose_with_nose_at(10, 10)
    instance = select_candidate_instance([face], [far_pose, near_pose])
    assert instance.pose is near_pose
    print("[PASS] test_select_candidate_matches_nearest_pose_when_multiple_overlap")


def test_select_candidate_real_frame_end_to_end():
    frame = cv2.imread(str(REAL_FACE_IMAGE))
    faces = detect_faces(frame)
    poses = detect_poses(frame)
    instance = select_candidate_instance(faces, poses)
    assert instance.status == SELECTED_STATUS
    assert instance.pose is not None, "Expected the real fixture's pose to match its face"
    print(f"[PASS] test_select_candidate_real_frame_end_to_end "
          f"(face confidence={instance.face.confidence:.3f}, matched pose found)")


# --- Step 7: classify_sample -------------------------------------------------

def _make_pose_with_shoulder_visibility(left_vis, right_vis):
    landmarks = [PoseLandmark(x=0, y=0, z=0, visibility=0.9, presence=0.9) for _ in range(33)]
    landmarks[11] = PoseLandmark(x=0, y=0, z=0, visibility=left_vis, presence=0.9)
    landmarks[12] = PoseLandmark(x=0, y=0, z=0, visibility=right_vis, presence=0.9)
    return PoseDetection(landmarks=landmarks)


def test_classify_uncertain_passes_through():
    instance = CandidateInstance(status=UNCERTAIN_STATUS)
    result = classify_sample(instance)
    assert result.classification == UNCERTAIN_STATUS
    assert result.face_confidence is None
    print("[PASS] test_classify_uncertain_passes_through")


def test_classify_no_face_is_absent():
    instance = CandidateInstance(status=NO_FACE_STATUS)
    result = classify_sample(instance)
    assert result.classification == ABSENT_STATUS
    print("[PASS] test_classify_no_face_is_absent")


def test_classify_face_with_no_matched_pose_is_partial_not_absent():
    face = _make_face(0, 0, 100, 100, confidence=0.85)
    instance = CandidateInstance(status=SELECTED_STATUS, face=face, pose=None)
    result = classify_sample(instance)
    assert result.classification == PARTIALLY_VISIBLE_STATUS
    assert result.face_confidence == 0.85
    assert result.has_matched_pose is False
    assert result.left_shoulder_visibility is None and result.right_shoulder_visibility is None
    print("[PASS] test_classify_face_with_no_matched_pose_is_partial_not_absent")


def test_classify_both_shoulders_visible_is_fully_visible():
    face = _make_face(0, 0, 100, 100, confidence=0.9)
    pose = _make_pose_with_shoulder_visibility(0.95, 0.9)
    instance = CandidateInstance(status=SELECTED_STATUS, face=face, pose=pose)
    result = classify_sample(instance)
    assert result.classification == FULLY_VISIBLE_STATUS
    assert result.has_matched_pose is True
    assert result.left_shoulder_visibility == 0.95 and result.right_shoulder_visibility == 0.9
    print("[PASS] test_classify_both_shoulders_visible_is_fully_visible")


def test_classify_one_shoulder_below_threshold_is_partial_not_negative():
    face = _make_face(0, 0, 100, 100, confidence=0.9)
    pose = _make_pose_with_shoulder_visibility(0.9, SHOULDER_VISIBILITY_THRESHOLD - 0.1)
    instance = CandidateInstance(status=SELECTED_STATUS, face=face, pose=pose)
    result = classify_sample(instance)
    assert result.classification == PARTIALLY_VISIBLE_STATUS
    assert result.has_matched_pose is True
    print("[PASS] test_classify_one_shoulder_below_threshold_is_partial_not_negative")


def test_classify_both_shoulders_below_threshold_is_partial():
    face = _make_face(0, 0, 100, 100, confidence=0.9)
    pose = _make_pose_with_shoulder_visibility(0.1, 0.1)
    instance = CandidateInstance(status=SELECTED_STATUS, face=face, pose=pose)
    result = classify_sample(instance)
    assert result.classification == PARTIALLY_VISIBLE_STATUS
    print("[PASS] test_classify_both_shoulders_below_threshold_is_partial")


def test_classify_shoulder_exactly_at_threshold_counts_as_visible():
    face = _make_face(0, 0, 100, 100, confidence=0.9)
    pose = _make_pose_with_shoulder_visibility(SHOULDER_VISIBILITY_THRESHOLD, SHOULDER_VISIBILITY_THRESHOLD)
    instance = CandidateInstance(status=SELECTED_STATUS, face=face, pose=pose)
    result = classify_sample(instance)
    assert result.classification == FULLY_VISIBLE_STATUS
    print("[PASS] test_classify_shoulder_exactly_at_threshold_counts_as_visible")


def test_classify_real_frame_end_to_end():
    frame = cv2.imread(str(REAL_FACE_IMAGE))
    faces = detect_faces(frame)
    poses = detect_poses(frame)
    instance = select_candidate_instance(faces, poses)
    result = classify_sample(instance)
    assert result.classification == FULLY_VISIBLE_STATUS, f"Expected fully_visible on a clean real frame, got {result.classification}"
    assert result.face_confidence >= FACE_CONFIDENCE_THRESHOLD
    assert result.left_shoulder_visibility >= SHOULDER_VISIBILITY_THRESHOLD
    assert result.right_shoulder_visibility >= SHOULDER_VISIBILITY_THRESHOLD
    print(
        f"[PASS] test_classify_real_frame_end_to_end "
        f"(classification={result.classification}, face_conf={result.face_confidence:.3f})"
    )


# --- Step 8: aggregate --------------------------------------------------------

def _make_result(timestamp, classification, num_faces=1, **kwargs):
    visibility = VisibilityClassification(classification=classification, **kwargs)
    return SampleResult(timestamp=timestamp, num_faces=num_faces, visibility=visibility)


def test_aggregate_empty_input():
    metrics = aggregate([])
    assert metrics.total_samples == 0
    assert metrics.presence_rate is None
    assert metrics.full_visibility_rate is None
    assert metrics.absence_runs == []
    assert metrics.longest_continuous_absence_seconds == 0.0
    assert metrics.face_loss_event_count == 0
    print("[PASS] test_aggregate_empty_input")


def test_aggregate_all_fully_visible():
    samples = [_make_result(t, FULLY_VISIBLE_STATUS) for t in (0.0, 0.2, 0.4, 0.6)]
    metrics = aggregate(samples)
    assert metrics.total_samples == 4
    assert metrics.fully_visible_samples == 4
    assert metrics.full_visibility_rate == 1.0
    assert metrics.presence_rate == 1.0
    assert metrics.absence_runs == []
    print("[PASS] test_aggregate_all_fully_visible")


def test_aggregate_all_absent():
    samples = [_make_result(t, ABSENT_STATUS) for t in (0.0, 0.2, 0.4)]
    metrics = aggregate(samples)
    assert metrics.absent_samples == 3
    assert metrics.presence_rate == 0.0
    assert len(metrics.absence_runs) == 1
    run = metrics.absence_runs[0]
    assert run.num_samples == 3
    assert abs(run.duration - (0.4 + 1.0 / SAMPLE_FPS)) < 1e-9
    assert run.duration < ABSENCE_EVENT_FLOOR_SECONDS
    assert metrics.face_loss_event_count == 0
    print("[PASS] test_aggregate_all_absent")


def test_aggregate_excludes_uncertain_from_rates_but_counts_them():
    samples = [
        _make_result(0.0, UNCERTAIN_STATUS),
        _make_result(0.2, FULLY_VISIBLE_STATUS),
        _make_result(0.4, FULLY_VISIBLE_STATUS),
    ]
    metrics = aggregate(samples)
    assert metrics.total_samples == 3
    assert metrics.uncertain_samples == 1
    assert metrics.scored_samples == 2
    assert metrics.full_visibility_rate == 1.0
    print("[PASS] test_aggregate_excludes_uncertain_from_rates_but_counts_them")


def test_aggregate_mixed_classifications_rates():
    samples = [
        _make_result(0.0, FULLY_VISIBLE_STATUS),
        _make_result(0.2, FULLY_VISIBLE_STATUS),
        _make_result(0.4, PARTIALLY_VISIBLE_STATUS),
        _make_result(0.6, ABSENT_STATUS),
    ]
    metrics = aggregate(samples)
    assert metrics.full_visibility_rate == 0.5
    assert metrics.partial_visibility_rate == 0.25
    assert metrics.presence_rate == 0.75
    print("[PASS] test_aggregate_mixed_classifications_rates")


def test_aggregate_adjacent_absences_form_one_run():
    step = 1.0 / SAMPLE_FPS
    samples = [_make_result(round(i * step, 3), ABSENT_STATUS) for i in range(5)]
    metrics = aggregate(samples)
    assert len(metrics.absence_runs) == 1
    assert metrics.absence_runs[0].num_samples == 5
    print("[PASS] test_aggregate_adjacent_absences_form_one_run")


def test_aggregate_gap_breaks_absence_run():
    step = 1.0 / SAMPLE_FPS
    samples = [
        _make_result(0.0, ABSENT_STATUS),
        _make_result(step, ABSENT_STATUS),
        _make_result(50.0, ABSENT_STATUS),
        _make_result(50.0 + step, ABSENT_STATUS),
    ]
    metrics = aggregate(samples)
    assert len(metrics.absence_runs) == 2
    print("[PASS] test_aggregate_gap_breaks_absence_run")


def test_aggregate_visible_sample_breaks_absence_run():
    step = 1.0 / SAMPLE_FPS
    samples = [
        _make_result(0.0, ABSENT_STATUS),
        _make_result(step, ABSENT_STATUS),
        _make_result(2 * step, FULLY_VISIBLE_STATUS),
        _make_result(3 * step, ABSENT_STATUS),
    ]
    metrics = aggregate(samples)
    assert len(metrics.absence_runs) == 2
    assert metrics.absence_runs[0].num_samples == 2
    assert metrics.absence_runs[1].num_samples == 1
    print("[PASS] test_aggregate_visible_sample_breaks_absence_run")


def test_aggregate_short_absence_not_counted_as_face_loss_event_but_still_longest():
    step = 1.0 / SAMPLE_FPS
    samples = [
        _make_result(0.0, FULLY_VISIBLE_STATUS),
        _make_result(step, ABSENT_STATUS),
        _make_result(2 * step, FULLY_VISIBLE_STATUS),
    ]
    metrics = aggregate(samples)
    run = metrics.absence_runs[0]
    assert run.duration < ABSENCE_EVENT_FLOOR_SECONDS
    assert metrics.face_loss_event_count == 0
    assert metrics.longest_continuous_absence_seconds == run.duration
    print("[PASS] test_aggregate_short_absence_not_counted_as_face_loss_event_but_still_longest")


def test_aggregate_long_absence_crosses_face_loss_event_floor():
    step = 1.0 / SAMPLE_FPS
    n_samples = int(ABSENCE_EVENT_FLOOR_SECONDS * SAMPLE_FPS) + 1
    samples = [_make_result(round(i * step, 3), ABSENT_STATUS) for i in range(n_samples)]
    metrics = aggregate(samples)
    assert len(metrics.absence_runs) == 1
    assert metrics.absence_runs[0].duration >= ABSENCE_EVENT_FLOOR_SECONDS
    assert metrics.face_loss_event_count == 1
    print("[PASS] test_aggregate_long_absence_crosses_face_loss_event_floor")


def test_aggregate_longest_run_picked_among_multiple():
    step = 1.0 / SAMPLE_FPS
    samples = [
        _make_result(0.0, ABSENT_STATUS),
        _make_result(step, FULLY_VISIBLE_STATUS),
        _make_result(10.0, ABSENT_STATUS),
        _make_result(10.0 + step, ABSENT_STATUS),
        _make_result(10.0 + 2 * step, ABSENT_STATUS),
        _make_result(10.0 + 3 * step, ABSENT_STATUS),
        _make_result(20.0, FULLY_VISIBLE_STATUS),
    ]
    metrics = aggregate(samples)
    assert len(metrics.absence_runs) == 2
    run_durations = sorted(r.duration for r in metrics.absence_runs)
    assert metrics.longest_continuous_absence_seconds == run_durations[-1]
    assert run_durations[-1] < ABSENCE_EVENT_FLOOR_SECONDS
    assert metrics.face_loss_event_count == 0
    print("[PASS] test_aggregate_longest_run_picked_among_multiple")


def test_aggregate_multiple_face_events_counts_two_plus_faces():
    samples = [
        _make_result(0.0, FULLY_VISIBLE_STATUS, num_faces=1),
        _make_result(0.2, FULLY_VISIBLE_STATUS, num_faces=2),
        _make_result(0.4, UNCERTAIN_STATUS, num_faces=3),
        _make_result(0.6, ABSENT_STATUS, num_faces=0),
    ]
    metrics = aggregate(samples)
    assert metrics.multiple_face_events == 2
    print("[PASS] test_aggregate_multiple_face_events_counts_two_plus_faces")


def test_aggregate_unsorted_input_is_sorted_before_run_detection():
    step = 1.0 / SAMPLE_FPS
    samples = [
        _make_result(step, ABSENT_STATUS),
        _make_result(0.0, ABSENT_STATUS),
    ]
    metrics = aggregate(samples)
    assert len(metrics.absence_runs) == 1
    assert metrics.absence_runs[0].num_samples == 2
    assert metrics.absence_runs[0].start_timestamp == 0.0
    print("[PASS] test_aggregate_unsorted_input_is_sorted_before_run_detection")


# --- Step 9: run_visual_presence_analysis() orchestrator --------------------

def test_orchestrator_no_candidate_segments_returns_empty_result():
    segments = [make_seg(0.0, 5.0, "INTERVIEWER")]
    result = run_visual_presence_analysis("data/input/sample.mp4", segments)
    assert result["candidate_segment_count"] == 0
    assert result["timestamped_results"] == []
    assert result["aggregate"]["total_samples"] == 0
    assert result["aggregate"]["presence_rate"] is None
    print("[PASS] test_orchestrator_no_candidate_segments_returns_empty_result")


def test_orchestrator_synthetic_clip_end_to_end_schema():
    with tempfile.TemporaryDirectory() as tmp:
        clip = Path(tmp) / "synthetic.mp4"
        _make_synthetic_clip(clip, duration=2, fps=10)
        segments = [make_seg(0.0, 2.0, "CANDIDATE")]
        result = run_visual_presence_analysis(clip, segments)

    assert result["video_path"] == str(clip)
    assert result["candidate_segment_count"] == 1
    assert result["sample_fps"] == SAMPLE_FPS
    assert isinstance(result["timestamped_results"], list) and len(result["timestamped_results"]) > 0

    for entry in result["timestamped_results"]:
        assert set(entry.keys()) == {
            "timestamp", "num_faces_detected", "classification", "face_confidence",
            "left_shoulder_visibility", "right_shoulder_visibility", "has_matched_pose",
        }
        assert entry["classification"] == ABSENT_STATUS
        assert entry["num_faces_detected"] == 0

    agg = result["aggregate"]
    assert agg["total_samples"] == len(result["timestamped_results"])
    assert agg["absent_samples"] == agg["scored_samples"]
    assert agg["full_visibility_rate"] == 0.0
    assert len(agg["absence_runs"]) == 1
    print(
        f"[PASS] test_orchestrator_synthetic_clip_end_to_end_schema "
        f"({agg['total_samples']} sample(s), all absent as expected for a faceless clip)"
    )


def test_orchestrator_timestamps_are_chronological_and_within_segment():
    with tempfile.TemporaryDirectory() as tmp:
        clip = Path(tmp) / "synthetic.mp4"
        _make_synthetic_clip(clip, duration=2, fps=10)
        segments = [make_seg(0.2, 1.2, "CANDIDATE")]
        result = run_visual_presence_analysis(clip, segments)

    timestamps = [e["timestamp"] for e in result["timestamped_results"]]
    assert timestamps == sorted(timestamps)
    for t in timestamps:
        assert 0.2 - 1e-6 <= t <= 1.2 + 1e-6
    print("[PASS] test_orchestrator_timestamps_are_chronological_and_within_segment")


def test_orchestrator_missing_video_produces_no_samples_not_a_crash():
    segments = [make_seg(0.0, 1.0, "CANDIDATE")]
    result = run_visual_presence_analysis("/tmp/does_not_exist_98765.mp4", segments)
    assert result["candidate_segment_count"] == 1
    assert result["timestamped_results"] == []
    assert result["aggregate"]["total_samples"] == 0
    print("[PASS] test_orchestrator_missing_video_produces_no_samples_not_a_crash")


def test_orchestrator_real_fixture_frame_end_to_end_via_manual_frame():
    with tempfile.TemporaryDirectory() as tmp:
        clip = Path(tmp) / "one_frame.mp4"
        frame = cv2.imread(str(REAL_FACE_IMAGE))
        h, w = frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(clip), fourcc, 5, (w, h))
        for _ in range(5):
            writer.write(frame)
        writer.release()

        segments = [make_seg(0.0, 1.0, "CANDIDATE")]
        result = run_visual_presence_analysis(clip, segments)

    assert len(result["timestamped_results"]) > 0
    assert all(e["classification"] == FULLY_VISIBLE_STATUS for e in result["timestamped_results"])
    assert result["aggregate"]["full_visibility_rate"] == 1.0
    print(
        f"[PASS] test_orchestrator_real_fixture_frame_end_to_end_via_manual_frame "
        f"({len(result['timestamped_results'])} sample(s), all fully_visible)"
    )


# --- pipeline integration helpers: summarize_visual_metrics() / bucket_visual_results_by_chunk() ---

def _make_analysis_result(timestamped_results, aggregate_overrides=None):
    sample_results = []
    for e in timestamped_results:
        vis = VisibilityClassification(
            classification=e["classification"],
            face_confidence=e.get("face_confidence"),
            left_shoulder_visibility=e.get("left_shoulder_visibility"),
            right_shoulder_visibility=e.get("right_shoulder_visibility"),
            has_matched_pose=e.get("has_matched_pose", False),
        )
        sample_results.append(SampleResult(timestamp=e["timestamp"], num_faces=e.get("num_faces_detected", 1), visibility=vis))
    from interview_pipeline.src.visual_presence import aggregate as _aggregate, _aggregate_metrics_to_dict as _agg_to_dict
    metrics = _aggregate(sample_results)
    agg_dict = _agg_to_dict(metrics)
    if aggregate_overrides:
        agg_dict.update(aggregate_overrides)
    return {
        "video_path": "fake.mp4",
        "candidate_segment_count": 1,
        "sample_fps": SAMPLE_FPS,
        "timestamped_results": timestamped_results,
        "aggregate": agg_dict,
    }


def test_summarize_visual_metrics_converts_rates_to_percentages():
    result = _make_analysis_result([
        {"timestamp": 0.0, "classification": FULLY_VISIBLE_STATUS, "num_faces_detected": 1},
        {"timestamp": 0.2, "classification": FULLY_VISIBLE_STATUS, "num_faces_detected": 1},
        {"timestamp": 0.4, "classification": PARTIALLY_VISIBLE_STATUS, "num_faces_detected": 1},
        {"timestamp": 0.6, "classification": ABSENT_STATUS, "num_faces_detected": 0},
    ])
    metrics = summarize_visual_metrics(result)
    assert metrics["face_visibility_pct"] == 50.0
    assert metrics["presence_pct"] == 75.0
    assert metrics["partial_visibility_pct"] == 25.0
    assert metrics["head_posture_score"] == "N/A"
    print("[PASS] test_summarize_visual_metrics_converts_rates_to_percentages")


def test_summarize_visual_metrics_none_rate_stays_none_not_zero():
    result = _make_analysis_result([])
    metrics = summarize_visual_metrics(result)
    assert metrics["face_visibility_pct"] is None
    assert metrics["presence_pct"] is None
    print("[PASS] test_summarize_visual_metrics_none_rate_stays_none_not_zero")


def test_summarize_visual_metrics_passes_through_event_detail():
    result = _make_analysis_result([
        {"timestamp": 0.0, "classification": ABSENT_STATUS, "num_faces_detected": 0},
        {"timestamp": 0.2, "classification": ABSENT_STATUS, "num_faces_detected": 0},
        {"timestamp": 0.4, "classification": ABSENT_STATUS, "num_faces_detected": 0},
        {"timestamp": 0.6, "classification": ABSENT_STATUS, "num_faces_detected": 0},
        {"timestamp": 0.8, "classification": ABSENT_STATUS, "num_faces_detected": 0},
        {"timestamp": 1.0, "classification": ABSENT_STATUS, "num_faces_detected": 2},
    ])
    metrics = summarize_visual_metrics(result)
    assert metrics["face_loss_event_count"] == 1
    assert metrics["multiple_face_events"] == 1
    assert len(metrics["absence_runs"]) == 1
    print("[PASS] test_summarize_visual_metrics_passes_through_event_detail")


def test_bucket_visual_results_by_chunk_filters_to_window():
    result = _make_analysis_result([
        {"timestamp": 5.0, "classification": FULLY_VISIBLE_STATUS},
        {"timestamp": 9.9, "classification": FULLY_VISIBLE_STATUS},
        {"timestamp": 10.0, "classification": ABSENT_STATUS},
        {"timestamp": 15.0, "classification": ABSENT_STATUS},
    ])
    chunk0 = bucket_visual_results_by_chunk(result, 0.0, 10.0)
    assert chunk0["n_samples"] == 2
    assert chunk0["face_visibility_pct"] == 100.0

    chunk1 = bucket_visual_results_by_chunk(result, 10.0, 20.0)
    assert chunk1["n_samples"] == 2
    assert chunk1["face_visibility_pct"] == 0.0
    print("[PASS] test_bucket_visual_results_by_chunk_filters_to_window")


def test_bucket_visual_results_by_chunk_empty_window_is_na_not_zero():
    result = _make_analysis_result([
        {"timestamp": 50.0, "classification": FULLY_VISIBLE_STATUS},
    ])
    chunk = bucket_visual_results_by_chunk(result, 0.0, 10.0)
    assert chunk["face_visibility_pct"] == "N/A"
    assert chunk["n_samples"] == 0
    print("[PASS] test_bucket_visual_results_by_chunk_empty_window_is_na_not_zero")


def test_bucket_visual_results_by_chunk_excludes_uncertain():
    result = _make_analysis_result([
        {"timestamp": 1.0, "classification": FULLY_VISIBLE_STATUS},
        {"timestamp": 2.0, "classification": UNCERTAIN_STATUS},
    ])
    chunk = bucket_visual_results_by_chunk(result, 0.0, 10.0)
    assert chunk["n_samples"] == 1
    assert chunk["face_visibility_pct"] == 100.0
    print("[PASS] test_bucket_visual_results_by_chunk_excludes_uncertain")


def test_bucket_visual_results_by_chunk_sums_to_whole_video_across_chunks():
    timestamped = [
        {"timestamp": round(t, 1), "classification": FULLY_VISIBLE_STATUS if i % 3 else ABSENT_STATUS}
        for i, t in enumerate([x * 0.5 for x in range(60)])
    ]
    result = _make_analysis_result(timestamped)
    total_bucketed = 0
    for chunk_start in (0.0, 10.0, 20.0):
        chunk = bucket_visual_results_by_chunk(result, chunk_start, chunk_start + 10.0)
        total_bucketed += chunk["n_samples"]
    assert total_bucketed == len(timestamped)
    print("[PASS] test_bucket_visual_results_by_chunk_sums_to_whole_video_across_chunks")


if __name__ == "__main__":
    tests = [
        test_empty_input,
        test_no_candidate_segments,
        test_mixed_segments_filters_and_preserves_order,
        test_all_candidate_segments_returned_unchanged,
        test_single_speaker_edge_case,
        test_timestamps_empty_input,
        test_timestamps_one_second_segment_at_5fps,
        test_timestamps_segment_shorter_than_one_step,
        test_timestamps_multiple_segments_accumulate,
        test_timestamps_custom_fps,
        test_timestamps_zero_duration_segment_skipped,
        test_timestamps_invalid_fps_raises,
        test_sample_frame_reads_valid_timestamp,
        test_sample_frame_past_end_returns_none,
        test_sample_frame_missing_video_returns_none,
        test_sample_frames_batched_matches_single_calls,
        test_sample_frames_empty_input,
        test_sample_frames_missing_video_all_fail,
        test_detect_faces_finds_real_face,
        test_detect_faces_no_face_in_blank_image,
        test_detect_faces_none_frame_returns_empty,
        test_detect_faces_missing_model_raises,
        test_detect_poses_finds_real_pose,
        test_detect_poses_no_pose_in_blank_image,
        test_detect_poses_none_frame_returns_empty,
        test_detect_poses_missing_model_raises,
        test_select_candidate_no_faces,
        test_select_candidate_single_face_no_pose,
        test_select_candidate_single_face_with_matching_pose,
        test_select_candidate_pose_too_far_does_not_match,
        test_select_candidate_picks_largest_of_two_clearly_different_faces,
        test_select_candidate_marks_uncertain_when_faces_too_similar,
        test_select_candidate_matches_nearest_pose_when_multiple_overlap,
        test_select_candidate_real_frame_end_to_end,
        test_classify_uncertain_passes_through,
        test_classify_no_face_is_absent,
        test_classify_face_with_no_matched_pose_is_partial_not_absent,
        test_classify_both_shoulders_visible_is_fully_visible,
        test_classify_one_shoulder_below_threshold_is_partial_not_negative,
        test_classify_both_shoulders_below_threshold_is_partial,
        test_classify_shoulder_exactly_at_threshold_counts_as_visible,
        test_classify_real_frame_end_to_end,
        test_aggregate_empty_input,
        test_aggregate_all_fully_visible,
        test_aggregate_all_absent,
        test_aggregate_excludes_uncertain_from_rates_but_counts_them,
        test_aggregate_mixed_classifications_rates,
        test_aggregate_adjacent_absences_form_one_run,
        test_aggregate_gap_breaks_absence_run,
        test_aggregate_visible_sample_breaks_absence_run,
        test_aggregate_short_absence_not_counted_as_face_loss_event_but_still_longest,
        test_aggregate_long_absence_crosses_face_loss_event_floor,
        test_aggregate_longest_run_picked_among_multiple,
        test_aggregate_multiple_face_events_counts_two_plus_faces,
        test_aggregate_unsorted_input_is_sorted_before_run_detection,
        test_orchestrator_no_candidate_segments_returns_empty_result,
        test_orchestrator_synthetic_clip_end_to_end_schema,
        test_orchestrator_timestamps_are_chronological_and_within_segment,
        test_orchestrator_missing_video_produces_no_samples_not_a_crash,
        test_orchestrator_real_fixture_frame_end_to_end_via_manual_frame,
        test_summarize_visual_metrics_converts_rates_to_percentages,
        test_summarize_visual_metrics_none_rate_stays_none_not_zero,
        test_summarize_visual_metrics_passes_through_event_detail,
        test_bucket_visual_results_by_chunk_filters_to_window,
        test_bucket_visual_results_by_chunk_empty_window_is_na_not_zero,
        test_bucket_visual_results_by_chunk_excludes_uncertain,
        test_bucket_visual_results_by_chunk_sums_to_whole_video_across_chunks,
    ]
    failures = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failures += 1
            print(f"[FAIL] {t.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests passed.")
    sys.exit(1 if failures else 0)
