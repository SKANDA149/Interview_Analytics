# Paper 2 — Final Claim Table (CLEAN)

**This file is the single claim authority for manuscript drafting.** Any sentence in the manuscript
must map to a row marked SUPPORTED or SUPPORTED WITH LIMITATION here, or be a HYPOTHESIS row written
explicitly in hypothesis voice. Rows marked REMOVE must not appear in any form, including softened
or hedged rephrasings.

Status vocabulary:

- **SUPPORTED** — recomputed from raw data this session; may be stated flatly.
- **SUPPORTED WITH LIMITATION** — true as measured, but must carry the stated qualifier in the same
  sentence or the immediately adjacent one.
- **HYPOTHESIS ONLY** — must be written as a hypothesis or future-work item; never as a result.
- **REMOVE** — must not appear.

Evidence keys: `runs.jsonl` (R), `reference_frame_results_v1i.json` (F), `vad_raw_intervals.json`
(V), `coupling_results.json` (C), `manual_validation_annotations.csv` (M),
`decode_detect_split.json` (D), literature matrix (L).

---

## 1. Retention claims (R1–R7)

| # | Claim | Status | Evidence | Required qualifier |
|---|---|---|---|---|
| R1 | At all four matched budgets, budget-matched uniform sampling achieves higher interval-existence recall than the VAD gate (0.9517 vs 0.8345 at 5,170; 0.9655/0.9034; 0.9793/0.9379; 1.0000/0.9793) | SUPPORTED | R, F | "on this recording" |
| R2 | Random sampling also exceeds the VAD gate on existence recall at all four budgets | SUPPORTED | R, F | "on this recording" |
| R3 | The VAD gate achieves higher temporal-coverage recall than both controls at all four budgets (0.6925 vs 0.6762/0.6769 at 5,170) | SUPPORTED WITH LIMITATION | R, F | margin is ≈0.016 at the tightest budget and narrows further; must be called *slight* |
| R4 | The two standard retention metrics rank the same policies in opposite directions | SUPPORTED | R, F | this is the paper's central empirical observation; state as observed on one recording |
| R5 | Uniform sampling attains existence recall 1.0000 on the 117 multi-frame intervals at every budget; 100 % of its misses are single-frame intervals | SUPPORTED | F | must accompany the interval-duration convention statement |
| R6 | 50–67 % of the VAD gate's misses are multi-frame intervals; the longest missed span is 2.2 s | SUPPORTED | F | "frame-span convention" must be named |
| R7 | The retention gap narrows monotonically as budget increases and closes at 7,221 frames | SUPPORTED | R | descriptive only; no trend fitting, no extrapolation |

## 2. Coupling claims (C1–C6)

| # | Claim | Status | Evidence | Required qualifier |
|---|---|---|---|---|
| C1 | I(visible ; VAD-active) = 0.00896 bits against H(visible) = 0.40752 bits, i.e. 2.20 % of target entropy | SUPPORTED | C | exact values; no rounding to "≈0" |
| C2 | P(visible) = 0.9185; P(visible \| active) = 0.9402; P(visible \| silent) = 0.8730 | SUPPORTED | C, F | |
| C3 | Voice activity and detector-defined visual availability are **weakly coupled** on this recording | SUPPORTED | C | the word is *weak*; **never** "independent" or "nearly independent" — I > 0 |
| C4 | The weak coupling is consistent with the gate behaving close to a temporally clustered blind sampler | SUPPORTED WITH LIMITATION | C, R | must be written as *consistent with*, not *because* |
| C5 | Mutual information between a cheap gating signal and detector availability is measurable before deployment and costs only a VAD pass | SUPPORTED | C, V | method-level claim; makes no claim about what the value will be elsewhere |
| C6 | 2.20 % is characteristic of interview recordings | REMOVE | — | n = 1 |

## 3. Cost claims (K1–K8)

| # | Claim | Status | Evidence | Required qualifier |
|---|---|---|---|---|
| K1 | Gating reduces YuNet detector invocations by 32.35 / 17.36 / 10.82 / 5.51 % at padding 0/250/500/1000 ms | SUPPORTED | R | unit is **invocations**, stated in the same sentence |
| K2 | Detector invocations are the primary reported cost unit | SUPPORTED | R | definitional; declare in Methods |
| K3 | Reported wall-clock times show no proportional saving; the equal-budget spread (48.45 s vs 51.17 s) is comparable to between-policy differences | SUPPORTED | R | must appear wherever K1 appears |
| K4 | No total-runtime saving is claimed, at any percentage | SUPPORTED | R | stated as an explicit negative result |
| K5 | The absence of runtime saving follows from the recording being decoded in full under every condition | SUPPORTED | R | architectural consequence of the design; strongest of the interpretive claims |
| K6 | Peak memory is condition-invariant at ≈107 MB (<1 % spread across 13 conditions) | SUPPORTED | R | one line only |
| K7 | An auxiliary micro-benchmark splits per-frame cost 81.6 % decode / 18.4 % detect (2.098 ms per call) | SUPPORTED WITH LIMITATION | D | **non-pilot hardware**; must be labelled auxiliary and must not be used to characterise the evaluated system |
| K8 | Maximum achievable total saving is ≈6 % | REMOVE | — | derived from non-pilot hardware; formally withdrawn |

## 4. Reference and validation claims (V1–V5)

| # | Claim | Status | Evidence | Required qualifier |
|---|---|---|---|---|
| V1 | The reference is 145 detector-defined visibility intervals over a 7,642-frame 5-FPS grid; 7,019 visible (91.85 %), 623 absent | SUPPORTED | F | |
| V2 | The reference is **detector-defined availability**, not ground truth | SUPPORTED | F, M | must appear in Abstract, Methods and Limitations |
| V3 | Under blind human review, 0 of 28 isolated single-frame detections were confirmable (28/28 UNCERTAIN); on an independent random stratum 32 of 50 were confirmed and 0 rejected | SUPPORTED | M | report all three counts; the 0-NO result is as important as the 0-YES |
| V4 | The 28 isolated detections are best interpreted as visually ambiguous events of uncertain status | SUPPORTED WITH LIMITATION | M | **not** "detector errors"; the annotation could not resolve them either way |
| V5 | The manual validation establishes detector error rates | REMOVE | — | 134 role-instances, single annotator, no adjudication; it characterises ambiguity, not error rate |

## 5. Design and scope claims (D1–D6)

| # | Claim | Status | Evidence | Required qualifier |
|---|---|---|---|---|
| D1 | All conditions process exactly the same number of frames from the same grid, so budget is controlled by construction | SUPPORTED | R | this is the design's main strength; state it early |
| D2 | All parameters (Silero 0.5/250/100/0 ms; YuNet 0.6; 5-FPS grid; ROI; seed 20260913) were frozen before the experiment and never varied | SUPPORTED | V, R | |
| D3 | Results are from a single recording (1528.267 s, 1280×720, h264) | SUPPORTED | R | **must appear within the first two sentences of the abstract** |
| D4 | A second recording was screened and rejected before the pilot (545/545 probes face-present — saturated, no discriminative headroom) | SUPPORTED WITH LIMITATION | screening log | a **screening** result on a different recording; never presented as a Paper 2 measurement or as a failed replication |
| D5 | Padding has an effect separable from the budget it induces | REMOVE | — | padding and budget are confounded by construction |
| D6 | Results generalise beyond this recording | REMOVE | — | n = 1 |

## 6. Novelty and positioning claims (N1–N8)

| # | Claim | Status | Evidence | Required qualifier |
|---|---|---|---|---|
| N1 | Prior work on audio-driven visual scheduling exists and is cited, including arXiv:2608.22359 | SUPPORTED | L | independently verified via a second host |
| N2 | arXiv:2608.22359 materially pre-empts the methodological framing of speech-gated selective visual inference | SUPPORTED | L | must be cited in the Introduction, not buried in Related Work |
| N3 | Any claim of being first, novel, or the first to propose speech-gated visual scheduling | REMOVE | L | pre-empted |
| N4 | The specific contribution is the **budget-matched blind-control comparison** plus the **metric dissociation**, which the pre-empting work does not report | SUPPORTED WITH LIMITATION | L | phrase as "to our knowledge, not reported in the work we surveyed" — never as absolute novelty |
| N5 | One cited item (ACM DOI 10.1145/3768184.3768216) could not be retrieved | SUPPORTED | L | cite by metadata only; make no claim about its contents |
| N6 | This work is distinct from the authors' Paper 1 (different recording, modality, stage, dependent variables, metrics) | SUPPORTED | Paper 1 artefacts | differentiation paragraph mandatory in the Introduction |
| N7 | The negative runtime result is itself a useful contribution for CPU-only edge deployment | SUPPORTED WITH LIMITATION | R | frame as a measurement-methodology caution, not as a general law |
| N8 | Coupling measurement is a validated pre-deployment screening procedure | HYPOTHESIS ONLY | C | predictive validity was never tested |

---

## Additional HYPOTHESIS ONLY rows

| # | Statement | Required voice |
|---|---|---|
| H1 | On a recording with substantially stronger audio–visual coupling, the gate's existence-recall deficit may shrink or reverse | "we hypothesise"; future work |
| H2 | The observed ordering may hold on recordings with similar layout and visibility base rate | "we hypothesise"; future work |

## Tally

| Status | Count |
|---|---|
| SUPPORTED | 14 |
| SUPPORTED WITH LIMITATION | 8 |
| HYPOTHESIS ONLY | 2 (+ N8) |
| REMOVE | 15 (across this table and the aggregated prohibition list below) |

## Aggregated prohibition list (must never appear, in any wording)

1. "novel", "first", "we are the first" applied to the method.
2. "ground truth" applied to the detector reference.
3. "speedup", "faster", "X % faster" from invocation counts.
4. "~6 % maximum saving" or any figure derived from the auxiliary benchmark applied to the system.
5. "independent" / "nearly independent" for the audio–visual relationship (I > 0).
6. Any p-value, confidence interval, significance test or error bar on a retention metric.
7. The 1-FPS pre-check figures (1404, 1529, 91.82 %, 125, 57) in any results context.
8. Any value from the withdrawn `sample.mp4` visual pilot.
9. "replication failed" / "non-replication" for the screened-out second recording.
10. Paper 1 vocabulary as a descriptor of Paper 2's own method (diarization, DER, speaker
    attribution, embeddings, WPM, fillers, pause analysis, fluency, transcript).

**CLAIM TABLE STATUS: FROZEN.**
