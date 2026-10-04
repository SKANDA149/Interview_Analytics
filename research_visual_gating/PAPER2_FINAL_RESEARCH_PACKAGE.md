# Paper 2 — Final Research Package

Single entry point for manuscript drafting. All values here are recomputed-from-raw and cross-checked
against `PAPER2_FINAL_NUMBER_AUDIT.md`.

## 1. Final title (FROZEN)

**Does Voice Activity Inform Visual Availability? A Budget-Matched Study of Speech-Gated Face
Detection on CPU**

## 2. Final contribution (one sentence)

On a single CPU-only interview recording, a training-free voice-activity gate retains fewer distinct
detector-defined visual events than budget-matched blind uniform sampling while covering slightly
more visible time; we quantify the audio–visual coupling (2.20 % of target entropy) and the
detector-invocation accounting that bound how far such a gate can help.

## 3. What was measured

13 conditions × 3 repeats = 39 timed runs on `video1_infosys_h264.mp4` (1528.267 s, 1280×720, h264),
over a 5-FPS grid of 7,642 frames. One ungated reference pass (A) defines visual availability;
four VAD-gated conditions at padding 0/250/500/1000 ms; eight budget-matched blind controls
(uniform, random) processing exactly the gated frame counts. Retention measured by interval-existence
recall and temporal-coverage recall over 145 reference intervals. Coupling measured as mutual
information. Cost measured as detector invocations, with wall-clock and peak RSS as secondary.
Blind human validation over 134 role-instances.

## 4. Headline results

- Existence recall at 5,170 frames: uniform 0.9517 > random 0.9241 > VAD 0.8345. Ordering holds at
  all four budgets.
- Coverage recall at 5,170 frames: VAD 0.6925 > random 0.6769 ≈ uniform 0.6762. Ordering holds at
  all four budgets; margin ≈0.016 and narrowing.
- The two metrics rank the policies oppositely.
- I(visible ; VAD-active) = 0.00896 bits, H = 0.40752 bits, I/H = 2.20 % — weak coupling, not
  independence.
- Detector invocations reduced up to 32.35 %; no proportional runtime saving; peak memory invariant
  at ≈107 MB.
- Blind review: 0/28 isolated detections confirmable (0 YES, 0 NO, 28 UNCERTAIN); 32/50 confirmed on
  the independent random stratum.

## 5. What is claimable

See `PAPER2_FINAL_CLAIM_TABLE_CLEAN.md` — 14 SUPPORTED, 8 SUPPORTED WITH LIMITATION, 3 HYPOTHESIS
ONLY. That table, not this document, is the claim authority.

## 6. What is not claimable

Generalisation beyond this recording; predictive validity of the coupling measure; independence;
2.20 % as typical; separable padding effect; any runtime saving; any methodological first-ness;
ground-truth status for the reference; any significance statistic on a retention metric.

## 7. Provenance rules

5-FPS grid is the sole basis of all reported results. 1-FPS pre-check figures (1404, 1529, 91.82 %,
125, 57) are supplementary-only. The `sample.mp4` visual pilot is withdrawn; no number from it
enters the paper. The second recording appears only as a **screening** rejection, never as a failed
replication. Details in `PROVENANCE_FINALIZATION.md`.

## 8. Separation from Paper 1

Disjoint recording, modality, pipeline stage, dependent variables, metrics and contribution. Silero
VAD is shared infrastructure only. PASS conditional on three mechanical actions: differentiation
paragraph in the Introduction; four mandatory terminology substitutions; artefact-appendix sentence
naming the sole results directory. Details in `PAPER2_FINAL_SELF_OVERLAP_AUDIT.md`.

## 9. Literature position

arXiv:2608.22359 materially pre-empts the methodological framing and must be cited in the
Introduction. ACM DOI 10.1145/3768184.3768216 could not be retrieved and is cited by metadata only,
with no claim about its contents. No citation was invented. Details in
`RELATED_WORK_POSITIONING_FINAL.md`.

## 10. Figures and tables

5 figures, 4 tables, defined value-by-value in `PAPER2_FINAL_FIGURE_DATA_AUDIT.md`. No error bars on
retention metrics; no speedup column; no 1-FPS number in any main figure or table.

## 11. Artefacts

Sole results directory: `research_visual_gating/results/video1_infosys_checkpointed/`
(`runs.jsonl`, `reference_frame_results_v1i.json`, `vad_raw_intervals.json`,
`coupling_results.json`, `decode_detect_split.json`). Manual validation:
`manual_validation_annotations.csv`, `manual_validation_summary.json`. Verification:
`redteam_verify.py`. `research/` holds Paper 1's experiment plus a withdrawn early pilot, retained
for provenance only.

## 12. Honest venue assessment

A short-paper, workshop or measurement-and-caution contribution. The result is small, negative and
single-recording, and the framing is pre-empted. It is not a full-length methods paper, and it
should not be submitted as one.

## 13. Exact next step

Draft the **Abstract** first, in this order of sentences: (1) the question; (2) that this is a single
CPU-only interview recording; (3) the budget-matched blind-control design; (4) the metric
dissociation with both orderings; (5) the coupling value with the word *weak*; (6) invocation
reduction paired in the same sentence with the absence of runtime saving. Then the Introduction,
ending with the mandatory differentiation paragraph and containing the pre-emption citation. Every
sentence must map to a row in `PAPER2_FINAL_CLAIM_TABLE_CLEAN.md`.
