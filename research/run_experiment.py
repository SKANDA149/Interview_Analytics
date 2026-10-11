"""
research/run_experiment.py

Experiment runner for the diarization-error-tolerance study.
Grid: {role_swap, missed_speech} x {0, 10, 25, 50}% x recording(s).

For each recording directory, expects:
  <rec_dir>/diarization/segments.json   (reference role-labelled segments)
  <rec_dir>/outputs/full_transcript.json (Whisper words: {"words": [...]})

Usage:
  python research/run_experiment.py --smoke
      Runs ONE recording (the default local `data/` dir), severities
      [0.0, 0.25] only, skipping NLP scoring, and prints a summary.
      This is the smoke test required before the full grid.

  python research/run_experiment.py --full
      Runs the full grid (all SEVERITIES) with NLP scoring enabled,
      for every recording directory passed via --recordings, or the
      single default `data/` directory if none given. Writes results
      to research/results/experiment_results.json.

  python research/run_experiment.py --full --recordings data data2 data3 ...
      Run the full grid across multiple recording directories.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "interview_pipeline", "src"))

from diarization import DiarizationSegment
from research.perturbation import OPERATORS, SEVERITIES, role_swap, missed_speech
from research.downstream_metrics import compute_metrics

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")

METRIC_KEYS = [
    "words_per_minute",
    "silence_ratio_pct",
    "total_long_pauses",
    "longest_pause_sec",
    "average_pause_sec",
    "total_filler_words",
]


def load_recording(rec_dir):
    seg_path = os.path.join(rec_dir, "diarization", "segments.json")
    words_path = os.path.join(rec_dir, "outputs", "full_transcript.json")
    with open(seg_path) as f:
        raw_segs = json.load(f)
    segments = [DiarizationSegment(**item) for item in raw_segs]
    with open(words_path) as f:
        transcript = json.load(f)
    words = transcript.get("words", [])
    return segments, words


def distortion(baseline_value, value):
    """Relative distortion vs. severity-0 baseline. Returns None if baseline is 0."""
    if baseline_value in (0, 0.0):
        return None
    return round((value - baseline_value) / baseline_value, 4)


def run_grid(rec_dir, severities, seed, run_nlp, nlp_config=None):
    segments, words = load_recording(rec_dir)
    results = {"recording": os.path.basename(os.path.abspath(rec_dir)), "conditions": []}

    baseline_metrics = None
    for op_name, op_fn in OPERATORS.items():
        for severity in severities:
            t0 = time.time()
            corrupted = op_fn(segments, severity, seed=seed)
            metrics = compute_metrics(corrupted, words, nlp_config=nlp_config, run_nlp=run_nlp)
            elapsed = round(time.time() - t0, 3)

            if severity == 0.0 and baseline_metrics is None:
                baseline_metrics = metrics

            entry = {
                "operator": op_name,
                "severity": severity,
                "seed": seed,
                "elapsed_sec": elapsed,
                "metrics": {k: metrics[k] for k in METRIC_KEYS},
                "nlp_overall_score": metrics["nlp"]["overall_score"] if metrics.get("nlp") else None,
                "distortion_vs_baseline": {},
            }
            if baseline_metrics is not None:
                for k in METRIC_KEYS:
                    entry["distortion_vs_baseline"][k] = distortion(baseline_metrics[k], metrics[k])
            results["conditions"].append(entry)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Run minimal 1-recording smoke test (no NLP, 2 severities).")
    parser.add_argument("--full", action="store_true", help="Run the full grid with NLP scoring.")
    parser.add_argument("--recordings", nargs="*", default=None, help="Recording directories (each containing diarization/ and outputs/). Defaults to ./data")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not args.smoke and not args.full:
        parser.error("Pass --smoke or --full")

    recordings = args.recordings if args.recordings else [os.path.join(REPO_ROOT, "data")]

    if args.smoke:
        rec_dir = recordings[0]
        print(f"[SMOKE TEST] recording={rec_dir} severities=[0.0, 0.25] nlp=OFF")
        result = run_grid(rec_dir, severities=[0.0, 0.25], seed=args.seed, run_nlp=False)
        for entry in result["conditions"]:
            print(f"  {entry['operator']:14s} severity={entry['severity']:.2f} "
                  f"wpm={entry['metrics']['words_per_minute']} "
                  f"silence%={entry['metrics']['silence_ratio_pct']} "
                  f"long_pauses={entry['metrics']['total_long_pauses']} "
                  f"fillers={entry['metrics']['total_filler_words']} "
                  f"({entry['elapsed_sec']}s)")
        out_path = os.path.join(REPO_ROOT, "research", "results", "smoke_test_results.json")
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"[SMOKE TEST] wrote {out_path}")
        return

    if args.full:
        all_results = []
        for rec_dir in recordings:
            print(f"[FULL] recording={rec_dir} severities={SEVERITIES} nlp=ON")
            result = run_grid(rec_dir, severities=SEVERITIES, seed=args.seed, run_nlp=True)
            all_results.append(result)
        out_path = os.path.join(REPO_ROOT, "research", "results", "experiment_results.json")
        with open(out_path, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"[FULL] wrote {out_path}")


if __name__ == "__main__":
    main()
