# Coupling and Failure-Mode Analysis — Paper 2, Phase 1

All results below come from the **frozen** Paper 2 data and the **production** selection,
reference and recall functions, imported and executed — never re-implemented. Machine-readable
companion: `coupling_results.json`.

**Functions imported (authoritative):** `gating.select_frames_vad_gated`,
`gating.select_frames_matched_uniform`, `offline_recompute.select_frames_random`
(`RANDOM_SEED = 20260913`), `padding.dilate_and_merge`, `frame_grid.build_frame_grid`,
`visual_events.build_reference_intervals`, `visual_events.interval_existence_recall`,
`visual_events.temporal_coverage_recall`. **Functions re-implemented: none.**

**Nothing was changed:** VAD threshold 0.5 / min-speech 250 ms / min-silence 100 ms / speech-pad
0 ms; YuNet 0.6; 5-FPS grid; ROI; padding values; matching methodology; random seed; reference
construction. No frozen result file and no historical report was modified.

**Correction to the gap analysis, recorded for provenance.** The prior document reported uniform
missing "~9" intervals at budget 5170, from my own reconstruction. The production
`select_frames_matched_uniform` gives **7**. The production implementation is authoritative and
the estimate is superseded. Root cause: production uses `np.linspace(0, n-1, target_count)` with
`int(round(p))` and de-duplication; my reconstruction used `round(k * n/target)`. The VAD and
random figures were unaffected (they reproduced exactly).

---

## 1A — Speech–visibility coupling

### Definitions and alignment (exact)

- **VAD-active frame.** A grid timestamp `t` for which
  `is_within_any_interval(t, dilate_and_merge(raw_vad, 0 ms, duration))` is True. This is
  *identical by construction* to condition B's selected set, so "VAD-active" and "processed under
  condition B" are the same 5,170 frames — not an approximation of it.
- **Visible frame.** The frozen Condition-A per-frame YuNet output `present == True` at that same
  grid index. This is **detector-defined visual availability**, not human ground truth.
- **Alignment.** Index-aligned. `reference_frame_results_v1i.json` holds exactly one record per
  grid frame in grid order (7,642 records for 7,642 grid frames, asserted at load).
- **Projection onto the grid.** VAD intervals are continuous-time; they are projected onto the
  5-FPS grid by **inclusive containment** (`iv.start <= t <= iv.end`), which is the production
  rule in `padding.is_within_any_interval`.
- **Interpolation: none.** No resampling, no nearest-neighbour assignment, no smoothing.
- **Rounding: one place only** — `build_frame_grid` constructs timestamps as `round(i * 0.2, 3)`
  (index multiplication, not accumulated addition, to avoid float drift). No rounding occurs in
  the coupling computation itself.

### Verification against the gap analysis

| Quantity | Computed (production) | Expected | Status |
|---|---|---|---|
| H(visible) | 0.40752 bits | 0.40752 | **MATCH** |
| I(visible ; VAD) | 0.00896 bits | 0.00896 | **MATCH** |
| I / H | 2.20 % | 2.20 % | **MATCH** |
| P(visible \| VAD-active) | 0.9402 | 0.9402 | **MATCH** |
| P(visible \| VAD-silent) | 0.8730 | 0.8730 | **MATCH** |
| P(visible) | 0.9185 | 0.9185 | **MATCH** |

All six match. Counts: 7,642 grid frames = 5,170 VAD-active + 2,472 VAD-silent; 7,019 visible.

### Reading

Speech activity carries **2.20 % of the information** about whether the candidate is on camera.
Conditioning on speech moves the visibility probability from a 0.9185 base rate to 0.9402 (active)
or 0.8730 (silent) — a 6.7-point spread on a heavily saturated variable. In this recording the VAD
gate is, informationally, **very nearly a blind sampler**; what distinguishes it from the blind
controls is not the information it carries but the *clustered temporal structure* it imposes.

**Scope discipline.** This explains the observed recording. It does **not** demonstrate that the
result generalises. See "What this does and does not establish" below.

---

## 1B — Missed-interval analysis (all budgets, production selectors)

**Duration convention.** Production `ReferenceInterval.duration = end_ts - start_ts`, so a
single-frame interval has duration **0.0 s** and a k-frame interval has duration `(k-1) x 0.2` s.
The gap analysis quoted *frame spans* (single-frame = 0.2 s). Spans are reported here for
continuity; `coupling_results.json` carries both.

Reference set: **145 intervals** (28 single-frame, 117 multi-frame), identical at every budget.

| Budget | Strategy | Existence recall | Missed | Median span | Max span | Single-frame | Multi-frame |
|---|---|---|---|---|---|---|---|
| 5170 | VAD | 0.8345 | 24 | 0.5 s | 2.2 s | 9 (37.5 %) | 15 (62.5 %) |
| 5170 | **uniform** | 0.9517 | **7** | 0.2 s | 0.2 s | 7 (**100 %**) | 0 (0 %) |
| 5170 | random | 0.9241 | 11 | 0.2 s | 0.6 s | 9 (81.8 %) | 2 (18.2 %) |
| 6315 | VAD | 0.9034 | 14 | 0.3 s | 2.2 s | 7 (50.0 %) | 7 (50.0 %) |
| 6315 | **uniform** | 0.9655 | 5 | 0.2 s | 0.2 s | 5 (**100 %**) | 0 (0 %) |
| 6315 | random | 0.9517 | 7 | 0.2 s | 0.6 s | 5 (71.4 %) | 2 (28.6 %) |
| 6815 | VAD | 0.9379 | 9 | 0.4 s | 2.2 s | 4 (44.4 %) | 5 (55.6 %) |
| 6815 | **uniform** | 0.9793 | 3 | 0.2 s | 0.2 s | 3 (**100 %**) | 0 (0 %) |
| 6815 | random | 0.9655 | 5 | 0.2 s | 0.6 s | 4 (80.0 %) | 1 (20.0 %) |
| 7221 | VAD | 0.9793 | 3 | 0.4 s | 0.6 s | 1 (33.3 %) | 2 (66.7 %) |
| 7221 | **uniform** | 1.0000 | **0** | — | — | — | — |
| 7221 | random | 0.9862 | 2 | 0.2 s | 0.2 s | 2 (100 %) | 0 (0 %) |

### The central failure-mode finding

**Uniform sampling never misses a multi-frame interval at any tested budget.** At all four
budgets, 100 % of uniform's misses are single-frame intervals — including at the tightest budget,
where it processes only 67.65 % of frames. VAD, by contrast, misses multi-frame intervals at every
budget (62.5 %, 50.0 %, 55.6 %, 66.7 % of its misses), with missed spans reaching 2.2 s.

So the VAD-vs-uniform existence gap is not a matter of degree. The two strategies fail in
**qualitatively different ways**: uniform's residual error is confined to the irreducible
single-frame flicker, while VAD additionally discards genuine, multi-frame visual events.

---

## 1C — Multi-frame sensitivity analysis

Presented as a **sensitivity analysis**. The all-145-interval metric remains primary and is not
deleted. 145 intervals = 28 single-frame + 117 multi-frame.

| Budget | VAD (all → multi) | Uniform (all → multi) | Random (all → multi) |
|---|---|---|---|
| 5170 | 0.8345 → **0.8718** | 0.9517 → **1.0000** | 0.9241 → **0.9829** |
| 6315 | 0.9034 → **0.9402** | 0.9655 → **1.0000** | 0.9517 → **0.9829** |
| 6815 | 0.9379 → **0.9573** | 0.9793 → **1.0000** | 0.9655 → **0.9915** |
| 7221 | 0.9793 → **0.9829** | 1.0000 → **1.0000** | 0.9862 → **1.0000** |

**Does the qualitative ordering change? No.** Uniform > random > VAD holds at every budget under
both definitions. The ordering is robust to excluding the human-unconfirmable single-frame
detections.

**What does change is the interpretation, and it sharpens considerably.** Restricted to intervals
a human could plausibly confirm, **uniform sampling achieves perfect existence recall at every
budget** — it never misses a real visual event, even while skipping a third of all frames. VAD
still misses 12.8 % of real events at the tightest budget. The honest statement of the headline
result is therefore stronger than "0.9517 vs 0.8345": it is *blind uniform sampling loses nothing
that matters, while the speech gate loses real events.*

---

## 1D — Cost re-basing on detector invocations

**Primary cost unit: detector invocations.** Exact, deterministic, hardware-independent.

| Condition | Available 5-FPS frames | Detector invocations | Skipped | % skipped | Wall (s, secondary) |
|---|---|---|---|---|---|
| A | 7642 | 7642 | 0 | 0.00 % | 52.35 |
| B | 7642 | 5170 | 2472 | 32.35 % | 46.24 |
| C | 7642 | 6315 | 1327 | 17.36 % | 49.17 |
| D | 7642 | 6815 | 827 | 10.82 % | 51.02 |
| E | 7642 | 7221 | 421 | 5.51 % | 53.07 |

Matched controls process identical counts by construction (F_B/R_B = 5170, F_C/R_C = 6315,
F_D/R_D = 6815, F_E/R_E = 7221) and therefore have identical invocation cost to their VAD
counterpart.

### Instrumentation audit

The frozen `runs.jsonl` carries only aggregate timing (`wall_time_s`, `cpu_seconds`) plus duration
and coverage fields. **There are no per-stage counters**, so the decode / detect / bookkeeping
split **cannot be recovered retrospectively** from the pilot data.

### Minimum new instrumentation (performed)

A micro-benchmark over the first 2,000 grid frames (12,026 decoded frames): one decode-only
sequential pass, one decode+YuNet-on-ROI pass, frozen config, nothing redesigned.

| Component | Time | Share |
|---|---|---|
| Decode / frame acquisition | 18.61 s | **81.6 %** |
| YuNet inference (2,000 calls) | 4.20 s | **18.4 %** |
| Per detector call | 2.098 ms | — |

**Consequence, and this is the paper's most important cost statement:** gating can only ever
address the **18.4 %** detector share. At the maximum observed skip rate (32.35 %, condition B),
the theoretical best total-runtime saving is **6.0 %**. This is why the measured wall-clock spread
between conditions is dominated by noise — and it is the quantitative reason the paper must say
*selective visual inference / detector-invocation reduction*, never "32 % fewer frames means 32 %
faster".

**Hardware caveat, stated plainly.** This micro-benchmark ran in the analysis container, **not**
the machine that produced the pilot's `wall_time_s`. It establishes the ratio and order of
magnitude, not the pilot's own split. Re-measuring on the pilot machine is the one outstanding
work item (see the readiness conclusion).

---

## 1E — Statistical design, stated precisely

**Verified from the frozen runs:** across all 13 conditions × 3 timed repeats,
`processed_frames`, `interval_existence_recall` and `temporal_coverage_recall` each take **exactly
one distinct value per condition**. Only wall-clock and CPU time vary.

Therefore:

1. **Frame selection and both recall metrics are deterministic.** Given the recording, the frozen
   parameters and the seed, they are reproduced exactly on every run.
2. **The three repeats measure runtime variability only.** They are not replicates of the
   retention measurement.
3. **Recall metrics have zero repeat variance.** Error bars on recall are not merely small — they
   are *undefined* under this design. Any figure showing them would be fabricating a quantity.
4. **No significance testing is applicable or performed.** With deterministic metrics on a single
   recording there is no sampling distribution to test against. Reporting a p-value here would be
   meaningless.

### The padding/budget confound, stated explicitly

The four VAD conditions vary padding (0 / 250 / 500 / 1000 ms) **and** processed-frame budget
(5170 / 6315 / 6815 / 7221) simultaneously, because the budget is a deterministic consequence of
the padding. Within the VAD arm, **padding and budget are perfectly confounded** and their effects
cannot be separated by this design.

What this does *not* damage: the matched controls are defined by budget alone, so every
**VAD-vs-control comparison at a fixed budget remains clean** — that is the paper's central
comparison and it is unaffected.

What this *does* forbid: any claim attributing an effect to *padding as such* rather than to the
budget it induces. "Padding improves coverage recall" must be phrased as "larger padding yields a
larger budget, and the larger budget improves coverage recall."

---

## What this analysis does and does not establish

**Establishes (for `video1_infosys_h264.mp4`):** speech and candidate visibility are nearly
independent (I/H = 2.20 %); the VAD gate's failures are qualitatively worse than blind sampling's
(multi-frame vs single-frame); blind uniform sampling loses no real event at any tested budget;
the addressable cost share is 18.4 %, capping achievable saving at ~6 %.

**Does not establish:** that any of this generalises. The coupling figure **explains the observed
recording**; it does not **demonstrate generalization across recordings**. Those are different
claims and the paper must not blur them. A second recording with deliberately different coupling
would test whether the mechanism predicts — that remains untested, and the mechanism's predictive
value is therefore a hypothesis, not a result.
