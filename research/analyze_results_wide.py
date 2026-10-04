"""
research/analyze_results_wide.py

Analysis over research/results/experiment_results_wide.json (9 severities x
5 seeds, aggregated to mean+std). This is the paper-grade version:
- dose-response tables with mean +/- std (real run-to-run noise, not fabricated)
- cross-operator distortion comparison at each severity
- linearity check via linear regression R^2 (fit distortion ~ severity)
"""
import json
import os
import sys

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results", "experiment_results_wide.json")

METRIC_LABELS = {
    "words_per_minute": "WPM",
    "silence_ratio_pct": "Silence %",
    "total_long_pauses": "Long pauses",
    "total_short_pauses": "Short pauses",
    "longest_pause_sec": "Longest pause (s)",
    "average_pause_sec": "Avg pause (s)",
    "total_filler_words": "Filler count",
    "total_speech_duration_sec": "Speech duration (s)",
}


def load_results():
    if not os.path.exists(RESULTS_PATH):
        print(f"[ANALYZE] Missing {RESULTS_PATH} -- run research/run_experiment.py --full-wide first.")
        sys.exit(1)
    with open(RESULTS_PATH) as f:
        return json.load(f)


def group_by_operator(data):
    """Key by (policy, operator) when the results carry a policy field."""
    grouped = {}
    for c in data["conditions"]:
        key = f"{c['policy']}/{c['operator']}" if "policy" in c else c["operator"]
        grouped.setdefault(key, []).append(c)
    for op in grouped:
        grouped[op].sort(key=lambda c: c["severity"])
    return grouped


def linreg_r2(xs, ys):
    """Simple OLS slope + R^2 for distortion ~ severity."""
    n = len(xs)
    if n < 3:
        return None, None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    if ss_xx == 0:
        return None, None
    slope = ss_xy / ss_xx
    intercept = mean_y - slope * mean_x
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    if ss_tot == 0:
        return slope, 1.0
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res / ss_tot
    return round(slope, 4), round(r2, 4)


def print_dose_response(grouped):
    for op, conditions in grouped.items():
        print(f"\n=== {op}: dose-response (mean +/- std across {conditions[0]['n_seeds']} seeds) ===")
        header = f"{'sev':>5} | " + " | ".join(f"{METRIC_LABELS[k]:>16}" for k in METRIC_LABELS) + " | nlp_score"
        print(header)
        print("-" * len(header))
        for c in conditions:
            row = f"{c['severity']:>5.2f} | "
            cells = []
            for k in METRIC_LABELS:
                m = c["metrics"][k]
                cells.append(f"{m['mean']:>7.2f}+/-{m['std']:<6.2f}" if m['mean'] is not None else "n/a")
            row += " | ".join(cells)
            nlp = c["nlp_semantic_score"]
            row += f" | {nlp['mean']}+/-{nlp['std']}" if nlp["mean"] is not None else " | n/a"
            print(row)


def cross_operator_and_linearity(grouped):
    for metric_key, label in METRIC_LABELS.items():
        print(f"\n=== {label}: cross-operator distortion & linearity (R^2 of distortion ~ severity) ===")
        for op, conditions in grouped.items():
            xs, ys = [], []
            for c in conditions:
                d = c["distortion_vs_baseline_mean"].get(metric_key)
                if d is not None:
                    xs.append(c["severity"])
                    ys.append(d)
            slope, r2 = linreg_r2(xs, ys)
            if slope is None:
                print(f"  {op:<22} insufficient data")
                continue
            verdict = "linear (good fit)" if (r2 is not None and r2 >= 0.85) else "non-linear / noisy"
            print(f"  {op:<22} slope={slope:>+8.4f}  R^2={r2}  -> {verdict}")

    print("\n=== NLP semantic score: NOT A VALID DOSE-RESPONSE (see audit_report.md) ===")
    print("    all-MiniLM-L6-v2 truncates at 256 word-pieces (~200 words), so this")
    print("    score reflects only ~12% of a ~1633-word answer. Corruption past the")
    print("    opening sentences is invisible to it. Reported for transparency only;")
    print("    excluded from the paper's content-sensitivity claims.")
    for op, conditions in grouped.items():
        vals = [(c["severity"], c["nlp_semantic_score"]["mean"]) for c in conditions if c["nlp_semantic_score"]["mean"] is not None]
        print(f"  {op}: " + ", ".join(f"{s:.2f}->{v:.2f}" for s, v in vals))


def absolute_long_pauses(grouped):
    """total_long_pauses has a baseline mean of 0, so its RELATIVE distortion
    is undefined and it is excluded from every ratio-based analysis. Report
    it as absolute counts instead so it is not silently lost."""
    print("\n=== Long pauses: ABSOLUTE counts (relative distortion undefined, baseline = 0) ===")
    for op, conditions in grouped.items():
        vals = ", ".join(f"{c['severity']:.2f}->{c['metrics']['total_long_pauses']['mean']:.2f}"
                         for c in conditions)
        print(f"  {op:<22} {vals}")


def main():
    data = load_results()
    grouped = group_by_operator(data)
    print_dose_response(grouped)
    cross_operator_and_linearity(grouped)
    absolute_long_pauses(grouped)


if __name__ == "__main__":
    main()
