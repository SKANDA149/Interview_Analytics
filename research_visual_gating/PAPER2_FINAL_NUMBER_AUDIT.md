# Paper 2 — Final Number and Provenance Audit

**Method.** Every value below was **independently recomputed from raw data** this session using the
production selection/reference/recall functions, not read back from a report. Arithmetic identities
were checked explicitly (processed + skipped = total; hits + misses = 145; recall = hits/145;
visible + absent = total; single + multi = total; matched controls exactly equal). Script:
`redteam_verify.py`. **Result: all checks pass, zero discrepancies.**

Legend — STATUS: `VERIFIED` (recomputed from raw), `FROZEN-CONFIG` (declared parameter),
`AUXILIARY` (measured on non-pilot hardware), `WITHDRAWN` (must not appear).

---

## Recording

| Number | Source | Exact definition | Dataset / grid | Status | In paper? |
|---|---|---|---|---|---|
| 1528.267 s | `runs.jsonl` `video_duration_s` | Container duration | video1_infosys_h264.mp4 | VERIFIED | YES |
| 1280×720 | ffprobe | Frame dimensions | same | VERIFIED | YES |
| 30 fps CFR | ffprobe | Container frame rate (**not** the analysis grid) | same | VERIFIED | YES |
| h264 | ffprobe | Video codec | same | VERIFIED | YES |
| 45,848 | ffprobe | Total decoded frames | same | VERIFIED | Optional |

## 5-FPS analysis grid

| Number | Source | Exact definition | Status | In paper? |
|---|---|---|---|---|
| **7,642** | `build_frame_grid(1528.267, 5)` | Grid timestamps at `round(i·0.2, 3)`, i = 0…7641 | VERIFIED (= `total_grid_frames` in all 39 runs) | YES |
| 0.2 s | derived | Grid step | VERIFIED | YES |

## Reference (detector-defined visual availability)

| Number | Source | Exact definition | Status | In paper? |
|---|---|---|---|---|
| **7,019** | `reference_frame_results_v1i.json` | Grid frames with Condition-A YuNet `present == True` | VERIFIED | YES |
| **623** | same | Grid frames with `present == False` | VERIFIED (7019 + 623 = 7642 ✓) | YES |
| **91.85 %** | derived | 7019 / 7642 — **5-FPS grid figure** | VERIFIED | YES |
| **145** | `build_reference_intervals` | Maximal runs of consecutive present grid frames (index adjacency) | VERIFIED | YES |
| **28** | derived | Intervals with `duration == 0.0` (span one grid frame) | VERIFIED | YES |
| **117** | derived | Intervals with `duration > 0.0` | VERIFIED (28 + 117 = 145 ✓) | YES |
| 0.200 s | `GAP_MERGE_SECONDS` | Merge parameter; **inert at this grid** (0 of 61 single-frame gaps bridged) | FROZEN-CONFIG | YES, as footnote |

**Interval-duration convention — must be stated once in the paper.** Production
`ReferenceInterval.duration = end_ts − start_ts`. A single-frame interval therefore has
**duration 0.0 s**, and a k-frame interval has duration (k−1)·0.2 s. Where the paper quotes a
*frame span* instead (single-frame = 0.2 s), it must say so. Both conventions appear in
`coupling_results.json`; **the paper must pick one and label it.** Recommended: report *frame
span*, as it is more intuitive, and state the conversion.

## VAD configuration and budgets

| Number | Source | Exact definition | Status | In paper? |
|---|---|---|---|---|
| 0.5 / 250 ms / 100 ms / 0 ms | `vad_raw_intervals.json` `frozen_params` | Silero threshold, min-speech, min-silence, speech-pad | FROZEN-CONFIG | YES |
| **588** | same | Raw speech intervals returned by Silero | VERIFIED | YES |
| **1029.3 s** | same | Total raw speech duration (67.4 % of recording) | VERIFIED | YES |
| **5,170 / 6,315 / 6,815 / 7,221** | `select_frames_vad_gated` at padding 0/250/500/1000 ms | Grid frames inside dilated+merged speech intervals | VERIFIED — all four reproduce exactly | YES |

## Retention — all values recomputed from raw

Existence recall = fraction of the **145** reference intervals containing ≥1 processed timestamp.
Coverage recall = fraction of reference-positive grid points processed.

| Budget | Strategy | Existence | Coverage | Multi-frame (117) | Status |
|---|---|---|---|---|---|
| 5170 | VAD | 0.8345 | 0.6925 | 0.8718 | VERIFIED |
| 5170 | Uniform | 0.9517 | 0.6762 | **1.0000** | VERIFIED |
| 5170 | Random | 0.9241 | 0.6769 | 0.9829 | VERIFIED |
| 6315 | VAD | 0.9034 | 0.8417 | 0.9402 | VERIFIED |
| 6315 | Uniform | 0.9655 | 0.8262 | **1.0000** | VERIFIED |
| 6315 | Random | 0.9517 | 0.8276 | 0.9829 | VERIFIED |
| 6815 | VAD | 0.9379 | 0.9045 | 0.9573 | VERIFIED |
| 6815 | Uniform | 0.9793 | 0.8914 | **1.0000** | VERIFIED |
| 6815 | Random | 0.9655 | 0.8919 | 0.9915 | VERIFIED |
| 7221 | VAD | 0.9793 | 0.9541 | 0.9829 | VERIFIED |
| 7221 | Uniform | 1.0000 | 0.9461 | **1.0000** | VERIFIED |
| 7221 | Random | 0.9862 | 0.9446 | 1.0000 | VERIFIED |

All twelve `hits + misses = 145` and `recall = hits/145` identities hold exactly.

### Missed-interval composition (% of a strategy's misses that are multi-frame)

| Budget | VAD | Uniform | Random |
|---|---|---|---|
| 5170 | 62.5 % (24 missed) | **0.0 %** (7 missed) | 18.2 % (11 missed) |
| 6315 | 50.0 % (14) | **0.0 %** (5) | 28.6 % (7) |
| 6815 | 55.6 % (9) | **0.0 %** (3) | 20.0 % (5) |
| 7221 | 66.7 % (3) | — (0 missed) | 0.0 % (2) |

Maximum VAD missed frame-span: **2.2 s** — VERIFIED. All values VERIFIED.

## Cost

| Number | Source | Exact definition | Status | In paper? |
|---|---|---|---|---|
| 7642 / 5170 / 6315 / 6815 / 7221 | `runs.jsonl` | **Detector invocations** (YuNet calls) | VERIFIED | YES — primary cost unit |
| 0 / 2472 / 1327 / 827 / 421 | derived | Skipped invocations (total − processed) | VERIFIED | YES |
| 0 / **32.35** / 17.36 / 10.82 / 5.51 % | derived | Skipped ÷ 7642 | VERIFIED | YES |
| 52.35 / 46.24 / 49.17 / 51.02 / 53.07 s | `runs.jsonl` | Mean wall-clock, 3 repeats, **pilot hardware** | VERIFIED | YES — secondary only |
| ≈107 MB | `runs.jsonl` | Peak RSS, all 13 conditions, <1 % spread | VERIFIED | YES — one line |
| 81.6 % / 18.4 % | `decode_detect_split.json` | Decode vs YuNet share | **AUXILIARY — non-pilot hardware** | Only with caveat |
| 2.098 ms | same | Per detector call | **AUXILIARY** | Only with caveat |
| **≈6 %** | derived from auxiliary | "Max theoretical total saving" | **WITHDRAWN** | **NO** |

## Coupling

| Number | Exact definition | Status | In paper? |
|---|---|---|---|
| **0.9185** | P(visible) = 7019/7642 | VERIFIED | YES |
| **0.9402** | P(visible \| VAD-active), n = 5170 | VERIFIED | YES |
| **0.8730** | P(visible \| VAD-silent), n = 2472 | VERIFIED | YES |
| **0.40752 bits** | H(visible), binary entropy of P = 0.9185 | VERIFIED | YES |
| **0.00896 bits** | I(visible ; VAD-active) = H(visible) − conditional entropy | VERIFIED | YES |
| **2.20 %** | I / H | VERIFIED | YES |
| 5170 / 2472 | VAD-active / VAD-silent grid frames (sum = 7642 ✓) | VERIFIED | YES |

**Interpretive correction logged.** I = 0.00896 bits is **strictly greater than zero**, and the two
conditional probabilities differ by 6.7 points. The correct description is **weak coupling**, never
*independence* or *near-independence*. One occurrence of "nearly independent" was found in
`COUPLING_AND_FAILURE_MODES.md` and corrected this pass; a second occurrence survives in the
historical `PAPER2_FINAL_IEEE_READINESS_AND_GAP_ANALYSIS.md`, which is **left unmodified as
provenance** and is superseded by this audit.

## Manual validation

| Number | Source | Exact definition | Status | In paper? |
|---|---|---|---|---|
| **134** | `manual_validation_annotations.csv` | Role-instances (rows) | VERIFIED | YES |
| **133** | same | Unique physical frames judged | VERIFIED | YES |
| **84 / 83** | same | Stratum-1 role-instances / unique frames (one frame serves two roles) | VERIFIED | YES |
| **28** | same | Distinct single-frame reference intervals, one "center" row each | VERIFIED | YES |
| **50** | same | Stratum-2 independent random timestamps | VERIFIED | YES |
| centers: **0 / 0 / 28** | same | YES / NO / UNCERTAIN on the 28 isolated detections (sum = 28 ✓) | VERIFIED | YES |
| random: **32 / 0 / 18** | same | YES / NO / UNCERTAIN on the 50 (sum = 50 ✓) | VERIFIED | YES |

---

## Numbers that MUST NOT appear

| Number | Why |
|---|---|
| ≈6 % max saving | Derived from non-pilot hardware |
| 11.7 % (A − B wall-clock) | Inside run-to-run noise; not a saving |
| "32.35 % faster" in any form | Invocations ≠ runtime |
| 1404 / 1529 / 91.82 % / 57 | 1-FPS pre-check — must never be presented as the 5-FPS result (see `PROVENANCE_FINALIZATION.md`) |
| Any value from the withdrawn `sample.mp4` pilot | Invalidated |
| Any p-value, CI or error bar on recall | Deterministic metrics, no sampling distribution |

**NUMBERS CLEAN = YES.** Zero unreconciled values; two interpretive corrections logged above.
