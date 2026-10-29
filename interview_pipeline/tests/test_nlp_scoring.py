"""Focused Phase 6.4 tests for honest semantic-evaluation availability."""
import csv
import json
from pathlib import Path

from interview_pipeline.src.nlp_scoring import (
    _fallback_keyword_similarity,
    evaluate_chunk_without_rubric,
    evaluate_response_against_rubric,
    not_evaluated_result,
)
from interview_pipeline.src.report_generator import generate_final_report


def _write_chunk(outputs_dir, content_analysis, *, chunk_id="chunk_000"):
    payload = {
        "chunk_id": chunk_id,
        "transcript": "synthetic transcript",
        "words": [{"word": "synthetic", "start": 0.0, "end": 0.5}],
        "speech_analysis": {
            "filler_count": 2,
            "long_pauses_count": 1,
            "total_silence_sec": 4.0,
            "words_per_minute": 60.0,
            "actual_chunk_duration_sec": 10.0,
            "active_speech_duration_sec": 6.0,
        },
        "visual_analysis": {"face_visibility_pct": 80.0},
        "content_analysis": content_analysis,
    }
    (outputs_dir / f"{chunk_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_fallback_keyword_similarity_has_no_artificial_bonus():
    assert _fallback_keyword_similarity("unrelated words", "reference rubric") == 0.0
    assert _fallback_keyword_similarity("reference", "reference rubric") == 50.0
    assert _fallback_keyword_similarity("reference rubric", "reference rubric") == 100.0


def test_default_pipeline_path_has_no_static_reference_answer():
    pipeline_source = (Path(__file__).parents[1] / "src" / "pipeline.py").read_text(encoding="utf-8")

    assert "Data structures are used to organize" not in pipeline_source
    assert "evaluate_technical_answer" not in pipeline_source
    assert "evaluate_chunk_without_rubric" in pipeline_source


def test_missing_rubric_is_explicitly_not_evaluated():
    result = evaluate_response_against_rubric("I would use a hash map.", None)

    assert result == not_evaluated_result()
    assert result["semantic_score"] is None
    assert result["scoring_status"] == "not_evaluated"
    assert result["scoring_reason"] == "No rubric provided"


def test_known_response_and_rubric_can_be_evaluated_without_claiming_quality(monkeypatch):
    # Keep the fixture offline and deterministic; this explicitly identified
    # response/rubric pair uses the transparent keyword-overlap fallback.
    monkeypatch.setattr("interview_pipeline.src.nlp_scoring.load_nlp_model", lambda: None)

    result = evaluate_response_against_rubric(
        "A hash map stores values by key.",
        "A hash map stores values by key.",
    )

    assert result["semantic_score"] == 100.0
    assert result["scoring_status"] == "evaluated"
    assert result["scoring_method"] == "keyword_reference_overlap"
    assert result["match_level"] == "Reference alignment"


def test_interviewer_chunk_is_not_mistaken_for_a_candidate_response():
    # The default pipeline state is deliberately speaker- and turn-agnostic:
    # neither an interviewer question nor a candidate chunk receives a score
    # unless a trusted response/rubric pairing is supplied externally.
    interviewer_question = "Could you explain how a hash map resolves collisions?"
    result = evaluate_chunk_without_rubric(interviewer_question)

    assert interviewer_question
    assert result["semantic_score"] is None
    assert result["scoring_status"] == "not_evaluated"


def test_unavailable_scores_are_reported_without_losing_other_metrics(tmp_path):
    outputs_dir = tmp_path / "outputs"
    reports_dir = tmp_path / "reports"
    outputs_dir.mkdir()
    _write_chunk(outputs_dir, not_evaluated_result())

    generate_final_report(outputs_dir, reports_dir, input_video_name="synthetic.mp4")

    report = json.loads((reports_dir / "final_report.json").read_text(encoding="utf-8"))
    metrics = report["overall_metrics"]
    assert metrics["average_semantic_score"] is None
    assert metrics["semantic_evaluation"] == {
        "status": "not_evaluated",
        "reason": "No rubric provided",
    }
    assert metrics["total_filler_words"] == 2
    assert metrics["average_active_chunk_wpm"] == 60.0
    assert metrics["average_face_visibility_pct"] == 80.0

    with (reports_dir / "interview_timeline.csv").open(encoding="utf-8", newline="") as csv_file:
        row = next(csv.DictReader(csv_file))
    assert row["Semantic_Score"] == "N/A"
    assert row["Semantic_Status"] == "not_evaluated"
    assert row["Semantic_Reason"] == "No rubric provided"


def test_historical_numeric_scores_remain_readable_as_legacy_similarity(tmp_path):
    outputs_dir = tmp_path / "outputs"
    reports_dir = tmp_path / "reports"
    outputs_dir.mkdir()
    _write_chunk(outputs_dir, {"semantic_score": 42.0, "match_level": "Poor"})

    generate_final_report(outputs_dir, reports_dir, input_video_name="historical.mp4")

    report = json.loads((reports_dir / "final_report.json").read_text(encoding="utf-8"))
    assert report["overall_metrics"]["average_semantic_score"] == 42.0
    assert report["overall_metrics"]["semantic_evaluation"]["status"] == "legacy_similarity"
