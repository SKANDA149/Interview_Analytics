"""
PHASE 1 — Coupling and failure-mode analysis for Paper 2.

Uses ONLY frozen Paper 2 data and the PRODUCTION frame-selection / reference /
recall functions, imported (never re-implemented):
  research_visual_gating.gating.select_frames_vad_gated
  research_visual_gating.gating.select_frames_matched_uniform
  research_visual_gating.offline_recompute.select_frames_random  (RANDOM_SEED=20260913)
  research_visual_gating.padding.dilate_and_merge
  research_visual_gating.frame_grid.build_frame_grid
  research_visual_gating.visual_events.build_reference_intervals
  research_visual_gating.visual_events.interval_existence_recall
  research_visual_gating.visual_events.temporal_coverage_recall

Changes nothing: no VAD/YuNet threshold, no grid, no ROI, no padding value,
no matching methodology, no seed, no reference construction. Writes only new
files; overwrites no frozen result and no historical report.
"""
import sys, json, math, statistics
sys.path.insert(0, ".")

from research_visual_gating.gating import select_frames_vad_gated, select_frames_matched_uniform
from research_visual_gating.padding import dilate_and_merge, Interval
from research_visual_gating.frame_grid import build_frame_grid
from research_visual_gating.visual_events import (
    build_reference_intervals, interval_existence_recall, temporal_coverage_recall,
)
from research_visual_gating.offline_recompute import select_frames_random, RANDOM_SEED

P = ("/mnt/user-data/uploads/interview_visual/Interview_Analytics/"
     "research_visual_gating/results/video1_infosys_checkpointed/")
PADDINGS = [("B", 0), ("C", 250), ("D", 500), ("E", 1000)]

# ---------------- load frozen inputs ----------------
runs = [json.loads(l) for l in open(P + "runs.jsonl") if l.strip()]
DURATION = runs[0]["video_duration_s"]                      # 1528.267
raw = json.load(open(P + "vad_raw_intervals.json"))
vad_raw = [Interval(start=d["start"], end=d["end"]) for d in raw["intervals"]]
# stored as [ts, layout_state, present, conf, n_faces]; build_reference_intervals
# wants (ts, present, conf)
ref_raw = json.load(open(P + "reference_frame_results_v1i.json"))
frame_results = [(r[0], bool(r[2]), float(r[3])) for r in ref_raw]
frame_results.sort(key=lambda r: r[0])

grid = build_frame_grid(DURATION)
N = len(grid)
assert N == runs[0]["total_grid_frames"] == 7642, (N, runs[0]["total_grid_frames"])

ref_intervals = build_reference_intervals(frame_results)
present_flags = [fr[1] for fr in frame_results]
assert len(present_flags) == N

# production per-condition processed_frames (mean over 3 timed repeats), exactly
# as the pilot computed each control's target_count
counts = {}
for r in runs:
    counts.setdefault(r["condition"], []).append(r["processed_frames"])
BUDGET = {c: round(sum(v) / len(v)) for c, v in counts.items()}

out = {
    "provenance": {
        "video_duration_s": DURATION,
        "total_grid_frames": N,
        "random_seed": RANDOM_SEED,
        "frozen_vad_params": raw.get("frozen_params"),
        "production_functions_imported": [
            "select_frames_vad_gated", "select_frames_matched_uniform",
            "select_frames_random", "dilate_and_merge", "build_frame_grid",
            "build_reference_intervals", "interval_existence_recall",
            "temporal_coverage_recall",
        ],
        "reimplemented_functions": [],
    }
}

# ============ 1A — speech/visibility coupling ============
# VAD-active frame := a grid timestamp t for which is_within_any_interval(t, S0)
# is True, where S0 = dilate_and_merge(raw_vad, padding_ms=0, duration). This is
# EXACTLY condition B's selection rule (select_frames_vad_gated), so "VAD-active"
# and "processed under condition B" are the same set by construction.
s0 = dilate_and_merge(vad_raw, 0, DURATION)
vad_idx = set(select_frames_vad_gated(grid, s0))
n_act = len(vad_idx)

# Visible frame := the frozen Condition-A per-frame detector output present==True
# at that same grid index. No interpolation, no rounding, no re-detection: the
# reference file has exactly one record per grid frame, in grid order.
n_vis = sum(present_flags)
vis_act = sum(1 for i in range(N) if i in vad_idx and present_flags[i])
vis_sil = n_vis - vis_act

p_base = n_vis / N
p_act = vis_act / n_act
p_sil = vis_sil / (N - n_act)

def H(p):
    return 0.0 if p in (0.0, 1.0) else -(p * math.log2(p) + (1 - p) * math.log2(1 - p))

pa = n_act / N
H_vis = H(p_base)
I = H_vis - (pa * H(p_act) + (1 - pa) * H(p_sil))

out["coupling"] = {
    "definition_vad_active": ("grid timestamp inside dilate_and_merge(raw_vad, 0ms, duration); "
                              "identical to condition B's select_frames_vad_gated set"),
    "definition_visible": ("frozen Condition-A YuNet present==True at that grid index "
                           "(detector-defined visual availability, not human ground truth)"),
    "alignment": ("index-aligned: reference file holds exactly one record per grid frame in grid "
                  "order; VAD intervals are projected onto the 5-FPS grid by inclusive "
                  "timestamp containment (iv.start <= t <= iv.end). No interpolation. The only "
                  "rounding is frame_grid.build_frame_grid's round(i*0.2, 3) when the grid is built."),
    "n_grid_frames": N,
    "n_vad_active": n_act,
    "n_vad_silent": N - n_act,
    "n_visible": n_vis,
    "P_visible": round(p_base, 4),
    "P_visible_given_vad_active": round(p_act, 4),
    "P_visible_given_vad_silent": round(p_sil, 4),
    "H_visible_bits": round(H_vis, 5),
    "I_visible_vad_bits": round(I, 5),
    "I_over_H_pct": round(100 * I / H_vis, 2),
}

TARGETS = [("I", round(I, 5), 0.00896), ("H", round(H_vis, 5), 0.40752),
           ("I/H %", round(100 * I / H_vis, 2), 2.20),
           ("P(vis|act)", round(p_act, 4), 0.9402),
           ("P(vis|sil)", round(p_sil, 4), 0.8730),
           ("P(vis)", round(p_base, 4), 0.9185)]
print("=== 1A COUPLING VERIFICATION (production-function based) ===")
ok = True
for name, got, want in TARGETS:
    match = abs(got - want) < 1e-4
    ok &= match
    print(f"  {name:12s} got {got:<10} expected {want:<10} {'MATCH' if match else '*** MISMATCH ***'}")
out["coupling"]["verification_vs_gap_analysis"] = "ALL MATCH" if ok else "MISMATCH"
if not ok:
    print("\nSTOPPING: coupling values differ from the gap analysis. Investigate before proceeding.")
    sys.exit(1)

# ============ 1B — missed-interval analysis, production selectors ============
def ts_set(indices):
    return {grid[i] for i in indices}

def stats(intervals):
    d = sorted(iv.duration for iv in intervals)
    if not d:
        return {"n_missed": 0, "min_s": None, "max_s": None, "median_s": None,
                "mean_s": None, "n_single_frame": 0, "pct_single_frame": None,
                "n_multi_frame": 0, "pct_multi_frame": None, "durations_s": []}
    single = sum(1 for x in d if x == 0.0)   # duration 0.0 == single-frame interval
    return {
        "n_missed": len(d),
        "min_s": round(min(d), 3), "max_s": round(max(d), 3),
        "median_s": round(statistics.median(d), 3), "mean_s": round(statistics.mean(d), 3),
        "n_single_frame": single, "pct_single_frame": round(100 * single / len(d), 1),
        "n_multi_frame": len(d) - single, "pct_multi_frame": round(100 * (len(d) - single) / len(d), 1),
        "durations_s": d,
    }

# NOTE ON DURATION CONVENTION: production ReferenceInterval.duration = end_ts -
# start_ts, so a single-frame interval has duration 0.0 s (not 0.2 s) and an
# interval spanning k frames has duration (k-1)*0.2 s. The gap analysis quoted
# frame-span durations (single-frame = 0.2 s). Both are reported below.
def span_s(iv):
    return round(iv.duration + 0.2, 3)

print("\n=== 1B MISSED-INTERVAL ANALYSIS (all budgets, production selectors) ===")
out["missed_intervals"] = {}
for cond, pad in PADDINGS:
    T = BUDGET[cond]
    sv = dilate_and_merge(vad_raw, pad, DURATION)
    sel = {
        "VAD": select_frames_vad_gated(grid, sv),
        "uniform": select_frames_matched_uniform(grid, T),
        "random": select_frames_random(grid, T, RANDOM_SEED),
    }
    rec = {}
    print(f"\n-- budget {T} frames (condition {cond}, padding {pad} ms) --")
    for name, idx in sel.items():
        assert len(idx) == T, (name, len(idx), T)
        r = interval_existence_recall(ts_set(idx), ref_intervals)
        st = stats(r["missed_intervals"])
        st["existence_recall"] = r["recall"]
        st["n_reference_intervals"] = r["n_intervals"]
        st["n_hit"] = r["n_hit"]
        st["missed_frame_span_s"] = sorted(span_s(iv) for iv in r["missed_intervals"])
        rec[name] = st
        sp = st["missed_frame_span_s"]
        print(f"  {name:8s} recall {r['recall']:.4f}  missed {st['n_missed']:2d}  "
              f"span median {statistics.median(sp) if sp else 0:.1f}s max {max(sp) if sp else 0:.1f}s  "
              f"single-frame {st['n_single_frame']} ({st['pct_single_frame']}%)" if st["n_missed"] else "  (none missed)")
    out["missed_intervals"][str(T)] = {"condition": cond, "padding_ms": pad, "strategies": rec}

# ============ 1C — multi-frame sensitivity ============
single_ivs = [iv for iv in ref_intervals if iv.duration == 0.0]
multi_ivs = [iv for iv in ref_intervals if iv.duration > 0.0]
print(f"\n=== 1C MULTI-FRAME SENSITIVITY ===")
print(f"reference: {len(ref_intervals)} total = {len(single_ivs)} single-frame + {len(multi_ivs)} multi-frame")
out["multi_frame_sensitivity"] = {
    "n_total_intervals": len(ref_intervals),
    "n_single_frame": len(single_ivs),
    "n_multi_frame": len(multi_ivs),
    "note": "Sensitivity analysis only. The all-interval metric is retained as primary.",
    "budgets": {},
}
for cond, pad in PADDINGS:
    T = BUDGET[cond]
    sv = dilate_and_merge(vad_raw, pad, DURATION)
    row = {}
    for name, idx in [("VAD", select_frames_vad_gated(grid, sv)),
                      ("uniform", select_frames_matched_uniform(grid, T)),
                      ("random", select_frames_random(grid, T, RANDOM_SEED))]:
        t = ts_set(idx)
        row[name] = {"all_145": interval_existence_recall(t, ref_intervals)["recall"],
                     "multi_frame_117": interval_existence_recall(t, multi_ivs)["recall"]}
    out["multi_frame_sensitivity"]["budgets"][str(T)] = row
    print(f"  budget {T}: " + "  ".join(
        f"{k} {v['all_145']:.4f}->{v['multi_frame_117']:.4f}" for k, v in row.items()))

# ============ 1D — cost re-basing on detector invocations ============
print("\n=== 1D DETECTOR-INVOCATION COST ===")
cost = {}
for c in ["A", "B", "C", "D", "E", "F_B", "F_C", "F_D", "F_E", "R_B", "R_C", "R_D", "R_E"]:
    pf = BUDGET[c]
    cost[c] = {
        "total_available_5fps_frames": N,
        "detector_invocations": pf,
        "skipped_detector_invocations": N - pf,
        "pct_skipped": round(100 * (N - pf) / N, 2),
        "wall_time_s_mean": round(sum(r["wall_time_s"] for r in runs if r["condition"] == c) / 3, 2),
    }
out["detector_invocation_cost"] = cost
out["detector_invocation_cost_caveat"] = (
    "Detector invocations are the primary, exact, deterministic cost unit. Skipped "
    "invocations MUST NOT be described as equivalent total pipeline speedup: the video is "
    "decoded sequentially in full for every condition, so decode cost is invariant to gating.")
for c in ["A", "B", "C", "D", "E"]:
    v = cost[c]
    print(f"  {c:3s} invocations {v['detector_invocations']:5d}  skipped {v['skipped_detector_invocations']:5d} "
          f"({v['pct_skipped']:5.2f}%)  wall {v['wall_time_s_mean']}s")

# instrumentation availability for decode/detect split
fields = sorted(runs[0].keys())
timing_fields = [f for f in fields if any(k in f for k in ("time", "sec", "_s", "cpu", "decode", "detect"))]
out["instrumentation_audit"] = {
    "available_timing_fields": timing_fields,
    "can_separate_decode_vs_detect": False,
    "reason": ("runs.jsonl records only aggregate wall_time_s / cpu_time_s / peak RSS per run. "
               "No per-stage counters for decode, YuNet inference, or selection bookkeeping exist, "
               "so the decode-vs-detect split cannot be recovered from frozen data."),
}
print("\n  timing fields present:", timing_fields)

# ============ 1E — statistical wording ============
det = {}
for c in BUDGET:
    rs = [r for r in runs if r["condition"] == c]
    det[c] = {
        "processed_frames_unique": len({r["processed_frames"] for r in rs}),
        "existence_recall_unique": len({r["interval_existence_recall"] for r in rs}),
        "coverage_recall_unique": len({r["temporal_coverage_recall"] for r in rs}),
        "wall_time_unique": len({r["wall_time_s"] for r in rs}),
    }
all_det = all(v["existence_recall_unique"] == 1 and v["coverage_recall_unique"] == 1
              and v["processed_frames_unique"] == 1 for v in det.values())
out["statistical_design"] = {
    "frame_selection_and_recall_are_deterministic": all_det,
    "evidence": ("across all 13 conditions x 3 timed repeats, processed_frames, "
                 "interval_existence_recall and temporal_coverage_recall each take exactly ONE "
                 "distinct value per condition; only wall/CPU time vary."),
    "repeats_measure": "runtime variability only",
    "recall_repeat_variance": "zero by construction; error bars on recall are not defined",
    "padding_budget_confound": (
        "The four VAD conditions vary padding (0/250/500/1000 ms) AND processed-frame budget "
        "(5170/6315/6815/7221) simultaneously, because budget is a deterministic consequence of "
        "padding. Padding and budget are therefore perfectly confounded within the VAD arm and "
        "their effects cannot be separated by this design. The matched controls are unaffected: "
        "they are defined by budget alone, so VAD-vs-control comparisons AT A FIXED BUDGET remain "
        "clean. What cannot be claimed is any statement attributing a VAD effect to padding per se."),
    "significance_testing": ("Not applicable and not performed. Recall metrics have no sampling "
                             "distribution here (deterministic, single recording)."),
}
print(f"\n=== 1E DESIGN === deterministic selection/recall verified: {all_det}")

with open("coupling_results.json", "w") as f:
    json.dump(out, f, indent=2)
print("\nwrote coupling_results.json")
