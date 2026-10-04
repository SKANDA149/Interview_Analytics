"""
research/analyze_results.py

Analysis pass over research/results/experiment_results.json -- computes
what the paper's Results section needs:
  1) per-operator, per-metric dose-response table (value + % distortion vs
     severity-0 baseline)
  2) cross-operator comparison: which operator produces the steepest
     distortion per unit of severity (headline finding)
  3) linearity check: does each metric degrade roughly linearly with
     severity, or does it jump/threshold?

No fabrication: everything below is computed directly from the JSON
produced by research/run_experiment.py --full. If that file doesn't exist
yet, this script tells you to run the experiment first rather than
inventing numbers.
"""
import json
import os
import sys

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results", "experiment_results.json")

METRIC_LABELS = {
    "words_per_minute": "WPM",
    "silence_ratio_pct": "Silence %",
    "total_long_pauses": "Long pauses (count)",
    "longest_pause_sec": "Longest pause (s)",
    "average_pause_sec": "Avg pause (s)",
    "total_filler_words": "Filler count",
}


def load_results():
    if not os.path.exists(RESULTS_PATH):
        print(f"[ANALYZE] Missing {RESULTS_PATH} -- run research/run_experiment.py --full first.")
        sys.exit(1)
    with open(RESULTS_PATH) as f:
        return json.load(f)


def group_by_operator(data):
    grouped = {}
    for c in data["conditions"]:
        grouped.setdefault(c["operator"], []).append(c)
    for op in grouped:
        grouped[op].sort(key=lambda c: c["severity"])
    return grouped


def print_dose_response_tables(grouped):
    for op, conditions in grouped.items():
        print(f"\n=== {op} : dose-response ===")
        header = f"{'severity':>9} | " + " | ".join(f"{METRIC_LABELS[k]:>18}" for k in METRIC_LABELS) + " | nlp_score"
        print(header)
        print("-" * len(header))
        for c in conditions:
            row = f"{c['severity']:>9.2f} | "
            row += " | ".join(f"{c['metrics'][k]:>18}" for k in METRIC_LABELS)
            row += f" | {c['nlp_semantic_score']}"
            print(row)


def print_distortion_tables(grouped):
    for op, conditions in grouped.items():
        print(f"\n=== {op} : % distortion vs severity-0 baseline ===")
        header = f"{'severity':>9} | " + " | ".join(f"{METRIC_LABELS[k]:>18}" for k in METRIC_LABELS)
        print(header)
        print("-" * len(header))
        for c in conditions:
            row = f"{c['severity']:>9.2f} | "
            cells = []
            for k in METRIC_LABELS:
                d = c["distortion_vs_baseline"].get(k)
                cells.append(f"{d*100:>+17.1f}%" if d is not None else f"{'n/a':>18}")
            row += " | ".join(cells)
            print(row)


def cross_operator_comparison(grouped, metric_key="words_per_minute"):
    print(f"\n=== Cross-operator comparison: distortion in {METRIC_LABELS[metric_key]} at each severity ===")
    severities = sorted({c["severity"] for conds in grouped.values() for c in conds})
    header = f"{'severity':>9} | " + " | ".join(f"{op:>15}" for op in grouped)
    print(header)
    print("-" * len(header))
    for sev in severities:
        row = f"{sev:>9.2f} | "
        cells = []
        for op, conditions in grouped.items():
            match = next((c for c in conditions if c["severity"] == sev), None)
            d = match["distortion_vs_baseline"].get(metric_key) if match else None
            cells.append(f"{d*100:>+14.1f}%" if d is not None else f"{'n/a':>15}")
        row += " | ".join(cells)
        print(row)

    print("\nSteepest distortion-per-unit-severity (excluding severity 0):")
    for op, conditions in grouped.items():
        nonzero = [c for c in conditions if c["severity"] > 0]
        if not nonzero:
            continue
        rates = []
        for c in nonzero:
            d = c["distortion_vs_baseline"].get(metric_key)
            if d is not None:
                rates.append(abs(d) / c["severity"])
        if rates:
            avg_rate = sum(rates) / len(rates)
            print(f"  {op:<15} avg |distortion|/severity = {avg_rate:.3f}")


def linearity_check(grouped, metric_key="words_per_minute"):
    print(f"\n=== Linearity check: {METRIC_LABELS[metric_key]} distortion vs severity ===")
    for op, conditions in grouped.items():
        points = [(c["severity"], c["distortion_vs_baseline"].get(metric_key)) for c in conditions]
        points = [(s, d) for s, d in points if d is not None]
        if len(points) < 3:
            print(f"  {op}: not enough points")
            continue
        # simple successive-slope check
        slopes = []
        for i in range(1, len(points)):
            s0, d0 = points[i - 1]
            s1, d1 = points[i]
            if s1 - s0 == 0:
                continue
            slopes.append((d1 - d0) / (s1 - s0))
        if not slopes:
            continue
        max_s, min_s = max(slopes), min(slopes)
        spread = (max_s - min_s) / (abs(max_s) + 1e-9) if max_s != 0 else 0
        verdict = "roughly linear" if spread < 0.6 else "threshold-like / non-linear jump"
        print(f"  {op:<15} successive slopes = {[round(s,3) for s in slopes]} -> {verdict}")


def main():
    data = load_results()
    grouped = group_by_operator(data)
    print_dose_response_tables(grouped)
    print_distortion_tables(grouped)
    for metric_key in ("words_per_minute", "silence_ratio_pct", "total_filler_words"):
        cross_operator_comparison(grouped, metric_key)
        linearity_check(grouped, metric_key)


if __name__ == "__main__":
    main()
