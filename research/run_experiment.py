"""
research/run_experiment.py

Experiment runner: {role_swap, missed_speech} x {0,10,25,50}% severities,
against this project's single available recording (global-stitched Vosk
words + reference diarization segments).

Usage:
  python research/run_experiment.py --smoke
      1 recording, severities [0.0, 0.25], NLP off. Fast sanity check.
  python research/run_experiment.py --full
      Original grid (severities 0/10/25/50%, 1 seed), NLP on. Writes
      research/results/experiment_results.json.
  python research/run_experiment.py --full-wide
      Finer severity grid (0/5/10/15/20/25/30/40/50%) x 5 seeds per
      condition, NLP on. Computes per-metric mean/std across seeds for
      smoother dose-response curves and real run-to-run noise bands.
      Writes research/results/experiment_results_wide.json (aggregated)
      and research/results/experiment_results_wide_raw.json (every
      individual run, for full transparency / re-analysis).
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from research.global_alignment import load_reference_segments, load_global_words
from research.perturbation import OPERATORS, SEVERITIES
from research.downstream_metrics import compute_metrics

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
RESULTS_DIR = os.path.join(REPO_ROOT, "research", "results")

METRIC_KEYS = [
    "words_per_minute",
    "silence_ratio_pct",
    "total_long_pauses",
    "total_short_pauses",
    "longest_pause_sec",
    "average_pause_sec",
    "total_filler_words",
    "total_speech_duration_sec",
]

WIDE_SEVERITIES = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
WIDE_SEEDS = [42, 7, 123, 2024, 99]
POLICIES = ["fallback", "strict"]


def distortion(baseline_value, value):
    if baseline_value in (0, 0.0):
        return None
    return round((value - baseline_value) / baseline_value, 4)


def run_grid(severities, seed, run_nlp):
    segments = load_reference_segments()
    words = load_global_words()

    results = {"recording": "data (interview_visual)", "conditions": []}
    baseline_metrics = None

    for op_name, op_fn in OPERATORS.items():
        for severity in severities:
            t0 = time.time()
            corrupted = op_fn(segments, severity, seed=seed)
            metrics = compute_metrics(corrupted, words, run_nlp=run_nlp)
            elapsed = round(time.time() - t0, 3)

            if severity == 0.0 and baseline_metrics is None:
                baseline_metrics = metrics

            entry = {
                "operator": op_name,
                "severity": severity,
                "seed": seed,
                "elapsed_sec": elapsed,
                "metrics": {k: metrics[k] for k in METRIC_KEYS},
                "nlp_semantic_score": metrics["nlp"]["semantic_score"] if metrics.get("nlp") else None,
                "distortion_vs_baseline": {},
            }
            if baseline_metrics is not None:
                for k in METRIC_KEYS:
                    entry["distortion_vs_baseline"][k] = distortion(baseline_metrics[k], metrics[k])
            results["conditions"].append(entry)
    return results


def _mean_std(values):
    n = len(values)
    if n == 0:
        return None, None
    mean = sum(values) / n
    if n < 2:
        return round(mean, 4), 0.0
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return round(mean, 4), round(var ** 0.5, 4)


def run_grid_wide(severities, seeds, run_nlp, policies=("fallback",)):
    """
    Runs every (operator, severity, seed) combination and aggregates across
    seeds into per-metric mean/std -- gives smoother dose-response curves
    and real run-to-run noise bands (not fabricated: every value here comes
    from an actual compute_metrics() call).
    """
    segments = load_reference_segments()
    words = load_global_words()

    raw_runs = []
    aggregated = {
        "recording": "data (interview_visual)",
        "seeds": seeds,
        "policies": list(policies),
        "conditions": [],
    }

    for policy in policies:
        # Baseline is computed PER POLICY -- fallback and strict have
        # different severity-0 baselines, so sharing one would corrupt the
        # distortion ratios.
        baseline_means = None
        for op_name, op_fn in OPERATORS.items():
            for severity in severities:
                per_seed_metrics = []
                per_seed_nlp = []
                for seed in seeds:
                    t0 = time.time()
                    corrupted = op_fn(segments, severity, seed=seed)
                    metrics = compute_metrics(corrupted, words, run_nlp=run_nlp, policy=policy)
                    elapsed = round(time.time() - t0, 3)
                    per_seed_metrics.append(metrics)
                    if metrics.get("nlp"):
                        per_seed_nlp.append(metrics["nlp"]["semantic_score"])
                    raw_runs.append({
                        "policy": policy,
                        "operator": op_name, "severity": severity, "seed": seed,
                        "elapsed_sec": elapsed,
                        "metrics": {k: metrics[k] for k in METRIC_KEYS},
                        "nlp_semantic_score": metrics["nlp"]["semantic_score"] if metrics.get("nlp") else None,
                    })

                agg_metrics = {}
                for k in METRIC_KEYS:
                    mean, std = _mean_std([m[k] for m in per_seed_metrics])
                    agg_metrics[k] = {"mean": mean, "std": std}

                nlp_mean, nlp_std = _mean_std(per_seed_nlp) if per_seed_nlp else (None, None)

                entry = {
                    "policy": policy,
                    "operator": op_name,
                    "severity": severity,
                    "n_seeds": len(seeds),
                    "metrics": agg_metrics,
                    "nlp_semantic_score": {"mean": nlp_mean, "std": nlp_std},
                    "distortion_vs_baseline_mean": {},
                }

                if severity == 0.0 and baseline_means is None:
                    baseline_means = {k: agg_metrics[k]["mean"] for k in METRIC_KEYS}

                if baseline_means is not None:
                    for k in METRIC_KEYS:
                        entry["distortion_vs_baseline_mean"][k] = distortion(
                            baseline_means[k], agg_metrics[k]["mean"])

                aggregated["conditions"].append(entry)

    return aggregated, raw_runs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--full-wide", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not args.smoke and not args.full and not args.full_wide:
        parser.error("Pass --smoke, --full, or --full-wide")

    os.makedirs(RESULTS_DIR, exist_ok=True)

    if args.smoke:
        print("[SMOKE TEST] severities=[0.0, 0.25] nlp=OFF")
        result = run_grid(severities=[0.0, 0.25], seed=args.seed, run_nlp=False)
        for entry in result["conditions"]:
            print(f"  {entry['operator']:14s} severity={entry['severity']:.2f} "
                  f"wpm={entry['metrics']['words_per_minute']} "
                  f"silence%={entry['metrics']['silence_ratio_pct']} "
                  f"long_pauses={entry['metrics']['total_long_pauses']} "
                  f"fillers={entry['metrics']['total_filler_words']} "
                  f"({entry['elapsed_sec']}s)")
        out_path = os.path.join(RESULTS_DIR, "smoke_test_results.json")
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"[SMOKE TEST] wrote {out_path}")
        return

    if args.full:
        print(f"[FULL] severities={SEVERITIES} nlp=ON")
        result = run_grid(severities=SEVERITIES, seed=args.seed, run_nlp=True)
        out_path = os.path.join(RESULTS_DIR, "experiment_results.json")
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"[FULL] wrote {out_path}")

    if args.full_wide:
        print(f"[FULL-WIDE] severities={WIDE_SEVERITIES} seeds={WIDE_SEEDS} policies={POLICIES} nlp=ON")
        print(f"[FULL-WIDE] total runs = {len(POLICIES)} policies x {len(OPERATORS)} operators x "
              f"{len(WIDE_SEVERITIES)} severities x {len(WIDE_SEEDS)} seeds = "
              f"{len(POLICIES) * len(OPERATORS) * len(WIDE_SEVERITIES) * len(WIDE_SEEDS)}")
        t_start = time.time()
        aggregated, raw_runs = run_grid_wide(severities=WIDE_SEVERITIES, seeds=WIDE_SEEDS,
                                             run_nlp=True, policies=POLICIES)
        print(f"[FULL-WIDE] done in {time.time()-t_start:.1f}s")

        for c in aggregated["conditions"]:
            wpm = c["metrics"]["words_per_minute"]
            sil = c["metrics"]["silence_ratio_pct"]
            print(f"  [{c['policy']:8s}] {c['operator']:14s} severity={c['severity']:.2f} "
                  f"wpm={wpm['mean']}+/-{wpm['std']} "
                  f"silence%={sil['mean']}+/-{sil['std']} "
                  f"nlp={c['nlp_semantic_score']['mean']}+/-{c['nlp_semantic_score']['std']}")

        agg_path = os.path.join(RESULTS_DIR, "experiment_results_wide.json")
        raw_path = os.path.join(RESULTS_DIR, "experiment_results_wide_raw.json")
        with open(agg_path, "w") as f:
            json.dump(aggregated, f, indent=2)
        with open(raw_path, "w") as f:
            json.dump(raw_runs, f, indent=2)
        print(f"[FULL-WIDE] wrote {agg_path}")
        print(f"[FULL-WIDE] wrote {raw_path}")


if __name__ == "__main__":
    main()
