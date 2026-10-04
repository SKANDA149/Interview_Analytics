# Final Contribution Summary — VAD-Gated Selective Visual Inference (video1_infosys_h264.mp4)

Synthesized only from completed, frozen evidence: the 13-condition pilot (`runs.jsonl`, 39 timed
runs), its independent audit (`RESEARCH_AUDIT_PILOT.md`), the results tables
(`PAPER_RESULTS_TABLES.md`), the paper-worthiness assessment (`PAPER_WORTHINESS_ASSESSMENT.md`),
and the manual visual validation (`MANUAL_VALIDATION_REPORT.md`). No new computation was run to
produce this document.

## 1. Core research question

For a CPU-only, single-camera interview-recording pipeline, does gating an expensive per-frame
visual face detector (YuNet) by a cheap, training-free voice-activity signal (raw Silero VAD)
produce a favorable computation/information trade-off relative to budget-matched, detector-blind
uniform or random frame sampling — and, if so, along which axis (event-existence detection vs.
temporal-coverage completeness) does the advantage actually appear?

## 2. Main contribution

An empirical, budget-matched comparison showing that VAD-gated visual-inference scheduling does
not uniformly dominate blind sampling: it trades away event-existence recall for temporal-coverage
recall, consistently across every frame budget tested on this recording. The study also
identifies, quantifies, and independently validates a specific measurement caveat — a meaningful
minority of the detector-defined reference "events" are single-frame, visually ambiguous
detections — rather than treating the detector's output as unexamined ground truth.

## 3. Three key findings

1. At every one of the four tested frame budgets (5,170 to 7,221 of 7,642 grid frames),
   matched-blind uniform sampling achieved higher interval-existence recall than VAD-gating
   (e.g. 0.9517 vs. 0.8345 at the smallest budget), while VAD-gating achieved higher
   temporal-coverage recall than uniform or random sampling at every budget (e.g. 0.6925 vs.
   0.6762 at the smallest budget). AUC integration across the whole tested range confirms the
   same direction holds in aggregate, not just at the four sampled points (existence: uniform
   0.637 > random 0.622 > VAD 0.578; coverage: VAD 0.510 > random/uniform 0.500).
2. The VAD interval-merge parameter (200ms) is numerically inert at this recording's 5 FPS
   sampling grid — 0 of 61 real single-absent-frame gaps were bridged by it — which means the
   reference set's "145 intervals" figure includes 28 (19.3%) that are exactly single-frame,
   a fact that would not be obvious from the merge parameter's name or the pipeline's
   configuration alone.
3. Independent, blinded manual review of those 28 single-frame reference detections (Experiment
   1) found 0% could be confidently confirmed as a visible face (vs. 64% on an independent
   50-sample random baseline), while the same frames were still judged "genuine appearance"
   rather than "detector noise" — i.e., the reference set has a real, now-measured band of
   visual ambiguity, not simply detector error, and this cannot be waved off as a caveat without
   a number attached.

## 4. What is novel

**Genuinely distinctive**: the specific, budget-matched empirical demonstration — on a real
CPU-only interview pipeline — that a physiologically-motivated gating signal (voice activity)
trades event-detection recall for time-coverage recall relative to blind sampling, with the
direction of the trade-off holding at every tested budget rather than only on average; and the
step of independently, blindly validating the detector-defined reference set with a human
labeler and reporting the exact resulting numbers (0% vs. 64%) rather than a generic ground-truth
caveat.

**Already known / not novel on its own**: that a correlated, bursty sampling scheme (gating on
voice activity, which clusters in time) will tend to under-sample distinct rare events relative
to blind random or uniform sampling at equal budget is a fairly direct consequence of general
sampling and coverage theory — a reader familiar with detection-vs-coverage trade-offs would not
be surprised that *some* trade-off exists in this direction. The contribution is the concrete,
measured instantiation of that trade-off on this pipeline, not the qualitative existence of a
trade-off.

## 5. What we must not claim

- **Not** "VAD-gating is worse than random sampling" as a blanket statement — it wins outright on
  the coverage-recall axis at every budget; the honest claim is metric-dependent, not one-sided.
- **Not** that the reference set is validated ground truth for "the candidate was visible" —
  Experiment 1 explicitly rules this out for the single-frame subset (0% confirmed).
- **Not** generality across recordings or pipelines — this is a single recording
  (video1_infosys_h264.mp4, n=1); the planned second-recording replication (Experiment 2) was
  never run, so the trade-off's direction has not been checked against a different
  visibility base rate or camera layout.
- **Not** a compute/speed result — wall-clock and CPU differences between conditions at equal
  frame budgets were small relative to their measurement stdev (Table 2); this is a "which frames
  to spend visual inference on" (selective inference) result, not a "faster pipeline" result.
- **Not** statistical significance for the manual validation numbers — n=28 and n=50 with no
  significance test performed, by design; the 0%-vs-64% gap is a descriptive observation.

## 6. Paper positioning

Frame as a workshop / case-study-tier empirical methods paper, with the single-recording scope
and the validated reference caveat stated in the title itself rather than buried in limitations —
for example: *"Voice-Activity-Gated vs. Budget-Matched Blind Sampling for Selective Visual
Inference in a CPU-Only Interview Pipeline: A Single-Recording Case Study with an Independently
Validated Detection Reference."* No abstract drafted here, per scope.

## 7. Final strength

- Workshop / case-study paper: **7/10** — sound methodology, independently audited results,
  an honestly validated reference, and a real, non-obvious, direction-consistent finding; scoped
  correctly for this tier.
- General IEEE conference paper: **4/10** — held back primarily by the single-recording scope
  (no replication of the trade-off's direction) and secondarily by the now-explicit
  detector-defined (not ground-truth) reference, which narrows the strongest claim the paper can
  make even though it does not invalidate the comparative results.

## 8. Next decision

**A** — stop experimentation and draft a scoped (workshop/case-study-tier) paper.

Experiment 1 already answered the open validity question this study needed answered before
writing anything (recommendation B: frame the reference as detector-defined visual availability),
so option C (more validation) is not needed — repeating or expanding validation now would be
chasing certainty the stopping criteria already ruled out. Option B (one additional recording)
would be the right move only if the target is specifically a general-conference-tier claim of
generality; it is not required to produce a defensible, honestly-scoped case-study paper from
what already exists, and taking it on now would be new experimentation the current evidence
doesn't require. The pilot, audit, and validation together already form a complete, internally
consistent, non-overclaiming package at the case-study tier — the responsible next step is to
write that paper, not to keep collecting evidence for a claim (general conference-tier
generality) this study was never scoped to make.
