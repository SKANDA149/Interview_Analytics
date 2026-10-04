# Paper 2 — Final Figure and Table Data Audit

Every planned figure and table, with its exact data source, values, axes, units and labels. No
figure or table may imply universal superiority, runtime saving, ground truth, or predictive
validity. **No error bars appear anywhere on a retention metric** — the metrics are deterministic
functions of a fixed grid and a fixed selection rule; there is no sampling distribution to draw
from.

Grid provenance for every figure below: **5 FPS, 7,642 frames.** No 1-FPS quantity appears in any
figure or table.

---

## Figure 1 — Interval-existence recall vs frame budget

- **Source:** `runs.jsonl` + `reference_frame_results_v1i.json`, recomputed in `redteam_verify.py`.
- **x-axis:** processed frames (detector invocations), categorical at 5170, 6315, 6815, 7221.
- **y-axis:** interval-existence recall, dimensionless, range [0.80, 1.00].
- **Series:** VAD-gated, budget-matched uniform, budget-matched random (3 lines, marker per point).
- **Values:** VAD 0.8345 / 0.9034 / 0.9379 / 0.9793; uniform 0.9517 / 0.9655 / 0.9793 / 1.0000;
  random 0.9241 / 0.9517 / 0.9655 / 0.9862.
- **Caption must state:** single recording; recall is over the 145 detector-defined intervals;
  x-axis is invocations, not time.
- **Error bars:** none. **Prohibited implication:** that uniform is universally better — caption
  must point forward to Figure 2.

## Figure 2 — Temporal-coverage recall vs frame budget

- **Source:** as Figure 1.
- **Axes:** same x; y = temporal-coverage recall, [0.65, 1.00].
- **Values:** VAD 0.6925 / 0.8417 / 0.9045 / 0.9541; uniform 0.6762 / 0.8262 / 0.8914 / 0.9461;
  random 0.6769 / 0.8276 / 0.8919 / 0.9446.
- **Caption must state:** the ordering is the reverse of Figure 1, and the VAD margin is small
  (≈0.016 at the tightest budget, narrowing thereafter).
- **Error bars:** none.

## Figure 3 — Missed-interval composition

- **Source:** missed-interval analysis over the 145 intervals (28 single-frame, 117 multi-frame).
- **Type:** grouped bar, 4 budgets × 3 strategies; y = number of missed intervals, split
  single-frame vs multi-frame by shading.
- **Values (total missed; % multi-frame):** 5170 — VAD 24 (62.5 %), uniform 7 (0.0 %), random 11
  (18.2 %); 6315 — 14 (50.0 %), 5 (0.0 %), 7 (28.6 %); 6815 — 9 (55.6 %), 3 (0.0 %), 5 (20.0 %);
  7221 — 3 (66.7 %), 0 (—), 2 (0.0 %).
- **Caption must state:** uniform's misses are exclusively single-frame at every budget; the
  interval-duration convention in use; the longest VAD-missed frame span is 2.2 s.
- **Prohibited implication:** that single-frame misses are unimportant — Figure 5 shows their status
  is unresolved.

## Figure 4 — Audio–visual coupling

- **Source:** `coupling_results.json`.
- **Type:** two-panel. Left: bar chart of P(visible) = 0.9185, P(visible | VAD-active) = 0.9402,
  P(visible | VAD-silent) = 0.8730, y-axis [0.80, 1.00] with the axis break made explicit.
  Right: H(visible) = 0.40752 bits vs I = 0.00896 bits, y in bits, **full scale from 0**.
- **Caption must state:** I > 0, so this is weak coupling and not independence; 2.20 % of target
  entropy; single recording.
- **Prohibited implication:** independence; and the left panel's truncated axis must be annotated so
  the 6.7-point conditional difference is not read as large.

## Figure 5 — Blind manual validation outcome

- **Source:** `manual_validation_annotations.csv`.
- **Type:** stacked bar, two strata.
- **Values:** isolated single-frame detections (n = 28) — YES 0, NO 0, UNCERTAIN 28; independent
  random timestamps (n = 50) — YES 32, NO 0, UNCERTAIN 18.
- **Caption must state:** 134 role-instances over 133 unique frames, one annotator, blind to
  detector output, condition, VAD state and interval membership; the result characterises visual
  ambiguity, **not** detector error rate.
- **Prohibited implication:** that the 28 are confirmed detector errors (0 were rejected).

## Table 1 — Experimental conditions

- **Source:** `runs.jsonl`, `vad_raw_intervals.json`.
- **Columns:** condition ID; strategy; padding (ms); processed frames; skipped frames; skipped %.
- **Values:** A 7642 / 0 / 0 %; B 5170 / 2472 / 32.35 %; C 6315 / 1327 / 17.36 %; D 6815 / 827 /
  10.82 %; E 7221 / 421 / 5.51 %; F_B–F_E and R_B–R_E match B–E exactly by construction.
- **Footnote must state:** matched controls equal the gated budgets exactly; padding and budget are
  confounded by construction.

## Table 2 — Retention summary

- All twelve existence and coverage values from Figures 1–2, plus multi-frame existence recall
  (VAD 0.8718 / 0.9402 / 0.9573 / 0.9829; uniform 1.0000 at all four; random 0.9829 / 0.9829 /
  0.9915 / 1.0000).
- **Footnote:** hits + misses = 145 and recall = hits/145 verified for all twelve.

## Table 3 — Cost

- **Columns:** condition; detector invocations; invocation reduction %; mean wall-clock (s, 3
  repeats, pilot hardware); peak RSS (MB).
- **Values:** wall-clock 52.35 / 46.24 / 49.17 / 51.02 / 53.07 s; RSS ≈107 MB throughout.
- **Mandatory caption sentence:** invocation reduction is not a runtime reduction; the equal-budget
  wall-clock spread (48.45–51.17 s) is comparable to between-policy differences, and the recording
  is decoded in full under every condition.
- **Prohibited:** any "% faster" column, any speedup ratio, the withdrawn ≈6 % figure.

## Table 4 — Frozen configuration

- Silero VAD threshold 0.5, min-speech 250 ms, min-silence 100 ms, speech-pad 0 ms; YuNet
  `face_detection_yunet_2023mar.onnx` at 0.6; grid 5 FPS; ROI (1075, 560, 205×160); seed 20260913;
  `GAP_MERGE_SECONDS` 0.200 with a footnote that it is **inert** at a 0.2 s grid (0 of 61
  single-frame gaps bridged).

## Supplementary only

- 1-FPS ROI pre-check, headed *"1 FPS ROI pre-check (not the analysis grid)"*.
- Second-recording screening (545/545 probes face-present), labelled as screening on a different
  recording.
- Auxiliary decode/detect split (81.6 % / 18.4 %, 2.098 ms per call) with its non-pilot-hardware
  caveat stated in the caption itself, not only in the text.

---

## Cross-cutting checks

| Check | Result |
|---|---|
| Every figure value traceable to a named raw file | YES |
| Any 1-FPS number in a main figure or table | NO |
| Any error bar, CI or p-value on a retention metric | NO |
| Any figure implying universal superiority | NO — Figures 1 and 2 are adjacent and cross-referenced |
| Any figure implying runtime saving | NO — Table 3 carries the mandatory caption |
| Any figure implying ground truth | NO — "detector-defined" appears in Figures 1–3 and 5 captions |
| Any figure implying predictive validity | NO — Figure 4 is descriptive, caption says single recording |
| Units stated on every axis | YES (frames, dimensionless recall, bits, seconds, MB) |
| Strategy and budget labels match `runs.jsonl` condition IDs | YES |

**FIGURE-TABLE DATA CLEAN = YES.**
