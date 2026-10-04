# Paper 2 — Manuscript Blueprint

**No prose is written here.** Each subsection specifies question, data, artefact, permitted claim,
forbidden claim. Title frozen: *"Does Voice Activity Predict Visual Availability? A Budget-Matched
Study of Speech-Gated Face Detection on CPU"*.

---

## 1. Abstract

- **Question answered:** what was tested, what was found, on how much data.
- **Data:** headline figures only — 13 conditions, 7,642-frame grid, budgets 5170–7221, existence
  0.8345 vs 0.9517 at the tightest budget, coverage 0.6925 vs 0.6762, I/H = 2.20 %, 32.35 %
  invocation reduction.
- **Artefact:** none.
- **Permitted:** "on a single 25-minute interview recording" **must appear within the first two
  sentences**; metric-dependent framing; invocation reduction.
- **Forbidden:** any runtime-saving percentage; any generality; the word "novel"; "ground truth".

## 2. Introduction

- **Question:** why gate visual inference on speech, and why test it against matched blind controls?
- **Data:** none (motivation); cite Jalayer et al. 2026 **here**, not only in Related Work.
- **Artefact:** none.
- **Permitted:** framing as an empirical question; explicit statement that the matched-budget design
  follows prior work; the mandatory Paper 1 differentiation paragraph (verbatim from
  `PAPER1_PAPER2_DIFFERENTIATION.md`) as the final paragraph.
- **Forbidden:** "first to", "we propose a method", any implication of a general technique.

## 3. Related Work

- **Question:** what is established, and where does this sit?
- **Data:** `RELATED_WORK_POSITIONING_FINAL.md` §1–§3.
- **Artefact:** Table 5 (literature comparison).
- **Permitted:** the eight established aspects attributed to their sources; the six distinct aspects
  stated plainly; explicit acknowledgement that off-the-shelf audio gates underperforming uniform
  is a corroboration of Jalayer et al., not a discovery.
- **Forbidden:** any first-ness; any assertion about ACM 10.1145/3768184.3768216's content (unread).

## 4. Research Question / Hypotheses

- **Question:** the formal statement — at matched frame budget, does VAD selection retain more
  detector-defined visual availability than budget-matched blind selection?
- **Data:** none.
- **Artefact:** none.
- **Permitted:** two separately stated hypotheses, one per retention metric, each falsifiable;
  explicit statement that the metrics may disagree.
- **Forbidden:** a directional hypothesis presented post hoc as if pre-registered; any hypothesis
  about generalization.

## 5. Experimental Method

### 5.1 Video and candidate ROI
- **Q:** what recording, what spatial region, why fixed?
- **Data:** `video1_infosys_h264.mp4`, 1528.267 s, 1280×720, h264 30 fps CFR; ROI (1075, 560,
  205×160); recalibration-verified spatial stability.
- **Artefact:** Table 1; Figure 1 (pipeline schematic showing ROI).
- **Permitted:** ROI is fixed and recording-specific; stability was verified.
- **Forbidden:** mixing the **1-FPS recalibration sweep** (1404/1529 = 91.82 %, 57 absence
  intervals) with the **5-FPS pilot grid** (7019/7642 = 91.85 %, 145 intervals). If the
  recalibration sweep is mentioned at all, label it explicitly as a 1-FPS pre-check.

### 5.2 VAD configuration
- **Q:** exactly what gate?
- **Data:** Silero VAD ONNX, threshold 0.5, min-speech 250 ms, min-silence 100 ms, speech-pad 0 ms;
  588 raw speech intervals, 1029.3 s (67.4 %).
- **Artefact:** Table 1.
- **Permitted:** training-free, zero-tuning, frozen across all conditions.
- **Forbidden:** describing it as speaker-aware, or as "speech analysis".

### 5.3 YuNet configuration
- **Q:** exactly what detector?
- **Data:** `face_detection_yunet_2023mar.onnx`, confidence 0.6, applied to the ROI crop.
- **Artefact:** Table 1.
- **Permitted:** frozen, off-the-shelf, CPU.
- **Forbidden:** identity/recognition language of any kind.

### 5.4 5-FPS frame grid
- **Q:** what is the shared selection universe?
- **Data:** 7,642 timestamps, `round(i·0.2, 3)`, index multiplication to avoid float drift.
- **Artefact:** Table 1.
- **Permitted:** every condition selects a subset of one identical grid.
- **Forbidden:** implying the grid was tuned.

### 5.5 VAD-gated sampling
- **Q:** how do padding values produce budgets?
- **Data:** `dilate_and_merge` at 0/250/500/1000 ms → 5170/6315/6815/7221 frames.
- **Artefact:** Table 2.
- **Permitted:** budget is a deterministic consequence of padding; **state the padding/budget
  confound here**, not only in Limitations.
- **Forbidden:** attributing any effect to padding independent of budget.

### 5.6 Matched uniform sampling
- **Q:** how is the blind control constructed?
- **Data:** `select_frames_matched_uniform`, `np.linspace(0, n−1, target)` with rounding,
  de-duplication and deterministic shortfall fill; exact counts.
- **Artefact:** Table 2.
- **Permitted:** exact budget equality; full determinism.
- **Forbidden:** calling it "random"; implying approximate matching.

### 5.7 Matched random sampling
- **Q:** why a second blind control?
- **Data:** `select_frames_random`, seed 20260913, sampling without replacement.
- **Artefact:** Table 2.
- **Permitted:** isolates the value of the signal from the value of even spacing — **cite Jalayer
  et al. for this justification**.
- **Forbidden:** claiming this control design as a contribution.

### 5.8 Detector-defined reference
- **Q:** what counts as a visual event, and how trustworthy is it?
- **Data:** Condition A's exhaustive output; 7,019 present frames; 145 intervals (28 single-frame,
  117 multi-frame); index-based adjacency; `GAP_MERGE_SECONDS = 0.200`; blind validation of 133
  frames with 0/28 isolated detections confirmable vs 32/50 on the random stratum.
- **Artefact:** Table 1; validation numbers inline.
- **Permitted:** "detector-defined visual availability"; the merge is inert at 0.2 s (0 of 61
  single-frame gaps bridged) — disclose in a footnote.
- **Forbidden:** "ground truth", "annotation", "labels" for the reference.

### 5.9 Metrics
- **Q:** what is being retained, and under which definition?
- **Data:** `interval_existence_recall`, `temporal_coverage_recall` definitions.
- **Artefact:** none (equations inline).
- **Permitted:** both metrics defined formally and kept separate throughout; cite Eq. 2 of Jalayer
  et al. as the source of the existence formulation.
- **Forbidden:** combining them into a single score; claiming either metric as novel.

### 5.10 Computational cost measurement
- **Q:** what is the cost unit, and what is it not?
- **Data:** invocations per condition; skip percentages; `wall_time_s` / `cpu_seconds` / peak RSS
  from pilot hardware; auxiliary split flagged as separate hardware.
- **Artefact:** Table 4.
- **Permitted:** exactly the four allowed wordings in `FINAL_COST_MEASUREMENT.md`; deterministic
  metrics statement (3 repeats bound runtime variance only).
- **Forbidden:** every item in that file's forbidden list; error bars on recall.

---

## 6. Results

### 6.1 Frame budgets
- **Q:** what did each condition actually process?
- **Data:** 7642 / 5170 / 6315 / 6815 / 7221; controls exact-matched.
- **Artefact:** Table 2.
- **Permitted:** exact equality of matched budgets.
- **Forbidden:** describing budgets as "approximately" matched.

### 6.2 Existence recall
- **Q:** which policy retains more distinct events at equal budget?
- **Data:** VAD 0.8345/0.9034/0.9379/0.9793; uniform 0.9517/0.9655/0.9793/1.0000; random
  0.9241/0.9517/0.9655/0.9862.
- **Artefact:** Figure 2; Table 3.
- **Permitted:** uniform > random > VAD at all four budgets, on this recording.
- **Forbidden:** "VAD is worse" without the metric qualifier; significance language.

### 6.3 Temporal coverage
- **Q:** which policy covers more visible time at equal budget?
- **Data:** VAD 0.6925/0.8417/0.9045/0.9541; uniform 0.6762/0.8262/0.8914/0.9461; random
  0.6769/0.8276/0.8919/0.9446.
- **Artefact:** Figure 3; Table 3.
- **Permitted:** VAD > random ≈ uniform at all four budgets; **state the margins are small**
  (≈0.016 at the tightest) and that coverage degenerates toward the budget fraction on a saturated
  recording (the production code documents this limitation).
- **Forbidden:** presenting the coverage win as large or decisive.

### 6.4 Multi-frame sensitivity
- **Q:** does the ordering survive removing human-unconfirmable single-frame detections?
- **Data:** 117 multi-frame intervals; uniform 1.0000 at all four budgets; VAD
  0.8718/0.9402/0.9573/0.9829; random 0.9829/0.9829/0.9915/1.0000.
- **Artefact:** Table 3 (added columns).
- **Permitted:** the ordering is unchanged; uniform misses no multi-frame interval at any budget.
- **Forbidden:** replacing the primary all-145 metric with this one — it is a sensitivity analysis.

### 6.5 Failure-mode analysis
- **Q:** what kind of events does each policy lose?
- **Data:** at 5170 — VAD 24 missed (62.5 % multi-frame, max span 2.2 s), uniform 7 (100 %
  single-frame), random 11 (81.8 % single-frame); same pattern at all budgets.
- **Artefact:** Figure 4; Table 3.
- **Permitted:** the failures are qualitatively different, not merely more numerous.
- **Forbidden:** asserting the geometric explanation (fixed spacing guarantees a hit) as proven —
  it is a supported interpretation.

### 6.6 Audio–visual coupling
- **Q:** how much does the gate signal actually say about the target?
- **Data:** I = 0.00896 bits, H = 0.40752 bits, 2.20 %; P(visible) = 0.9185;
  P(visible|active) = 0.9402; P(visible|silent) = 0.8730.
- **Artefact:** Figure 5.
- **Permitted:** on this recording the gate is informationally close to blind; this is *consistent
  with* the observed ordering.
- **Forbidden:** "2.20 % is typical of interviews"; "coupling predicts performance"; any causal
  claim stronger than "consistent with".

### 6.7 Computational cost
- **Q:** what did gating actually save?
- **Data:** invocations and skip percentages; runtime means with the equal-budget noise
  demonstration (F_B 48.45 s vs R_B 51.17 s).
- **Artefact:** Table 4; Figure 6.
- **Permitted:** invocation reduction up to 32.35 %; runtime differences dominated by run-to-run
  variation; auxiliary split only with the hardware caveat.
- **Forbidden:** any speedup figure.

---

## 7. Discussion

- **Q:** what does this mean for someone deciding whether to gate?
- **Data:** synthesis; no new numbers.
- **Artefact:** none.
- **Permitted:** the metric-dissociation caution; the decode-bound ceiling argument; coupling as a
  *proposed* pre-deployment check, explicitly labelled a hypothesis; the practical recommendation
  that in this regime uniform sampling is simpler and retains more events.
- **Forbidden:** turning the hypothesis into a finding; recommending the method for other settings.

## 8. Limitations

- **Q:** what cannot be concluded?
- **Data:** the eight limitations in `FINAL_CONTRIBUTION_FREEZE.md` §F.
- **Artefact:** none.
- **Permitted:** all eight, stated plainly, including n=1, detector-defined reference,
  deterministic metrics, padding/budget confound, hardware caveat, single labeller, single layout,
  inert merge.
- **Forbidden:** burying n=1; implying the coupling analysis mitigates it.

## 9. Conclusion

- **Q:** what is learned?
- **Data:** none new.
- **Artefact:** none.
- **Permitted:** the frozen one-sentence contribution; the metric caution; the cost-unit correction.
- **Forbidden:** future-work framing that implies the hypothesis is nearly confirmed; any
  generality; any first-ness.

---

## Cross-cutting drafting rules

1. Every results sentence names the recording or says "on this recording".
2. The reference is always "detector-defined visual availability".
3. "VAD-silent frames" — never "pauses" or "silence" (Paper 1 collision).
4. No error bars on recall anywhere; state determinism once in §5.10 and once in §8.
5. Jalayer et al. cited in Introduction, Related Work, §5.7 and §5.9.
6. No number from the withdrawn `sample.mp4` pilot appears anywhere.
