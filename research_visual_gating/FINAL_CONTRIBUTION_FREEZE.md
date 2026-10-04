# Final Contribution Freeze — Paper 2

Frozen against: `coupling_results.json`, `COUPLING_AND_FAILURE_MODES.md`,
`RELATED_WORK_POSITIONING.md`, `FINAL_COST_MEASUREMENT.md`, `PAPER1_PAPER2_DIFFERENTIATION.md`,
`runs.jsonl`, `reference_frame_results_v1i.json`, `MANUAL_VALIDATION_REPORT.md`.

Every number below was re-verified this session against the frozen files.

---

## A. One-sentence contribution

On a single CPU-only interview recording, we show that a training-free voice-activity gate selects
frames *worse* than budget-matched blind uniform sampling for retaining distinct visual events
while selecting them *better* for covering visible time, and we measure the audio–visual coupling
(2.20 % of the visibility signal's entropy) and the detector's bounded share of pipeline cost that
together explain why.

## B. Contribution paragraph (3–4 sentences)

Speech activity is an attractive control signal for deciding when to run an expensive visual
detector, because it is nearly free to compute. We test that intuition directly on a CPU-only
interview pipeline by comparing a training-free Silero VAD gate against uniform and random
sampling controls that process exactly the same number of frames, and find the comparison is
metric-dependent: at every tested budget the gate retains less of the distinct visual events and
more of the visible time than blind sampling, and the two standard retention metrics therefore
rank the same policies in opposite directions. Measuring the coupling between the gate signal and
the detection target on this recording gives 0.00896 bits against 0.40752 bits of target entropy —
2.20 % — so the gate is informationally close to blind, and its distinctive behaviour comes from
the temporal clustering it imposes rather than from information it carries. Because the pipeline
decodes sequentially, gating reduces detector invocations by up to 32.35 % without a proportional
reduction in total runtime, which bounds what selective inference can deliver in this regime.

## C. Primary contribution

**A budget-matched characterisation of a training-free acoustic gate's retention behaviour in a
decode-bound CPU visual pipeline, with the governing quantity measured rather than assumed.**

Specifically: the existence/coverage dissociation, the failure-mode asymmetry (blind uniform
sampling's misses are 100 % single-frame flicker at every budget; the gate additionally loses
multi-frame events), and the measured audio–visual mutual information that explains both.

## D. Secondary contribution

**A measurement caution for selective-inference evaluation.** Interval-existence recall and
temporal-coverage recall rank the same sampling policies in opposite directions on the same data.
Reporting either alone yields an incomplete — and potentially sign-inverted — conclusion about a
selection policy. Prior work in this space reports interval-intersection coverage alone.

## E. Supporting contributions

1. **A cost-accounting correction for decode-bound pipelines.** Detector-invocation reduction and
   runtime reduction are not interchangeable when decoding is sequential and unavoidable; the
   paper reports invocations as the exact cost unit and declines to convert them into a speedup.
2. **A blind human validation of the detection reference.** 133 frames, sealed key, independent
   labeller; 0 of 28 isolated single-frame detections were confirmable as a visible face. The
   reference is reported as *detector-defined visual availability*, never as ground truth.
3. **A fully deterministic, independently audited evaluation harness.** 13 conditions × 3 repeats,
   exact budget matching, frozen configuration, fixed seed (20260913), reproduced from scratch by
   an independent re-implementation with zero discrepancies.

---

## The three epistemic levels

### OBSERVED

- On `video1_infosys_h264.mp4`, at all four matched budgets (5170/6315/6815/7221 of 7642 grid
  frames), VAD gating achieved **lower interval-existence recall** (0.8345 / 0.9034 / 0.9379 /
  0.9793) than matched uniform (0.9517 / 0.9655 / 0.9793 / 1.0000) and matched random (0.9241 /
  0.9517 / 0.9655 / 0.9862).
- At the same budgets, VAD achieved **higher temporal-coverage recall** than both controls
  (e.g. 0.6925 vs 0.6762 and 0.6769 at 5170).
- Restricted to the 117 multi-frame reference intervals, **uniform sampling achieved existence
  recall 1.0000 at every budget**; VAD did not (0.8718 / 0.9402 / 0.9573 / 0.9829).
- **100 % of uniform's missed intervals were single-frame at every budget.** VAD's misses were
  majority multi-frame (62.5 % / 50.0 % / 55.6 % / 66.7 %), with spans up to 2.2 s.
- On this recording, I(visible ; VAD-active) = **0.00896 bits** against H(visible) = **0.40752
  bits** (**2.20 %**); P(visible) = 0.9185, P(visible | VAD-active) = 0.9402,
  P(visible | VAD-silent) = 0.8730.
- VAD gating reduced detector invocations by up to **32.35 %**; wall-clock differences between
  strategies at identical budgets were of the same order as differences between strategies.
- Of 28 isolated single-frame detections, **0** were confirmable as a visible face under blind
  human review; 32 of 50 independently sampled timestamps were.

### SUPPORTED INTERPRETATION

- The retention behaviour is **consistent with** weak measured speech–visibility coupling combined
  with temporally clustered VAD selection: a gate carrying ~2 % of the target's information behaves
  close to a blind sampler, and its clustering then concentrates coverage while leaving whole
  events unsampled.
- The failure-mode asymmetry is **consistent with** uniform sampling's fixed spacing guaranteeing
  a sample inside any interval longer than that spacing, while a clustered selector offers no such
  guarantee.
- Because decoding is sequential, **the addressable share of pipeline cost is bounded by the
  detector's share**, which is why invocation reduction did not appear as proportional speedup.
- The reference set's single-frame intervals are **best interpreted as** detector flicker of
  uncertain visual status, given that no human could confirm any of them.

### HYPOTHESIS FOR FUTURE VALIDATION

- The coupling measure **may** predict when speech-gated visual sampling helps: on a recording
  where speech and candidate visibility are strongly coupled, the gate's existence-recall deficit
  **may** shrink or reverse. **This is untested.** One recording cannot establish it, and nothing
  in this paper demonstrates it.
- The observed qualitative ordering **may** hold on other recordings with similar layout and
  visibility base rate. **Untested.**
- Measuring coupling before deployment **may** be a useful pre-flight check for practitioners.
  **Proposed, not validated.**

---

## F. Explicit limitations

1. **n = 1 recording.** No generalization is demonstrated. The coupling analysis explains the
   observed recording; it does not demonstrate generalization across recordings.
2. **Detector-defined reference, not ground truth.** Blind validation found 0/28 isolated
   detections confirmable.
3. **Deterministic metrics.** The three repeats bound runtime variance only; recall metrics have
   no repeat variance and error bars on them are undefined. No significance test is applicable.
4. **Padding and budget are perfectly confounded** within the VAD arm. Budget-matched
   VAD-vs-control comparisons are unaffected; no claim about padding *per se* is available.
5. **The decode/detect split was measured on separate hardware** from the reported runtimes and is
   reported as auxiliary only (see `FINAL_COST_MEASUREMENT.md`).
6. **Single labeller, single pass** for the manual validation; no inter-rater agreement.
7. **One layout.** A fixed self-view thumbnail; an active-speaker-switched recording was screened
   and rejected as structurally incompatible, which itself bounds applicability.
8. **The 200 ms interval merge is numerically inert** at a 0.2 s grid (0 of 61 single-frame gaps
   bridged) — disclosed, not corrected.

## G. Claims that MUST NOT appear

- ❌ "VAD gating reduces runtime by 32 %" — or any conversion of skip rate into speedup.
- ❌ "Decode is 81.6 % of our pipeline" stated as a property of the evaluated system.
- ❌ "The detector provides ground truth."
- ❌ "VAD preserves visual information" unqualified — it preserves *time coverage* and loses *events*.
- ❌ "VAD is better/worse than uniform" unqualified — the result is metric-dependent.
- ❌ "The method generalizes to interviews" / "is robust" / "is superior."
- ❌ "2.20 % coupling" presented as a property of interview recordings generally.
- ❌ "First to compare audio gating against budget-matched blind controls" — pre-empted by
  arXiv:2608.22359.
- ❌ "Novel interval-existence recall metric" — pre-empted; standard in temporal action localisation.
- ❌ "The coupling measure predicts gate performance" — hypothesis, not result.
- ❌ Any statistical significance claim, or error bars on recall.
- ❌ Any number from the withdrawn `sample.mp4` pilot.
- ❌ Any mixing of the 1-FPS recalibration sweep (1404/1529, 57 absence intervals) with the 5-FPS
  pilot grid (7019/7642, 145 intervals).

---

# 6. Title audit

The working title — *"VAD-Gated Selective Visual Analysis: CPU Cost vs Information Loss in a
Multimodal Interview Pipeline"* — **fails** on three counts. "VAD-Gated Selective Visual Analysis"
names a method as though the paper contributes one; "CPU Cost" implies a validated cost saving
that the data does not support; "Multimodal Interview Pipeline" implies generality across
interviews from a single recording. It also collides with Paper 1's "CPU … Interview … Pipeline"
phrasing.

### Five candidates

**T1 — "Does Voice Activity Predict Visual Availability? A Budget-Matched Study of Speech-Gated
Face Detection on CPU"**
*Emphasises:* the empirical question and the matched-budget design.
*Implies:* a question was tested, not a method proposed.
*Risk:* low. "on CPU" is factual. Slight risk that "Predict" over-promises a predictive model;
mitigated because the question form makes the answer negative-capable.

**T2 — "Speech-Gated Frame Selection Loses Visual Events That Blind Sampling Retains: A
Single-Recording Case Study"**
*Emphasises:* the negative result and the failure mode.
*Implies:* a specific, falsifiable finding; "single-recording" caps generality in the title.
*Risk:* low on overclaiming, but states only the existence-recall half and hides the coverage win,
which would misrepresent the dissociation.

**T3 — "Existence or Coverage? Two Retention Metrics Disagree on Speech-Gated Visual Sampling"**
*Emphasises:* the secondary contribution — the metric dissociation.
*Implies:* a measurement-methodology paper.
*Risk:* low overclaim risk, but foregrounds the weaker contribution and buries the cost finding.

**T4 — "Selective Visual Inference in a Decode-Bound CPU Pipeline: Detector-Invocation Savings and
Their Retention Cost"**
*Emphasises:* the systems framing and the honest cost unit.
*Implies:* savings are in invocations, not runtime — exactly correct.
*Risk:* "savings" could still be read as speedup by a skimming reader; needs the abstract to
disambiguate immediately.

**T5 — "Acoustic Activity as a Frame-Selection Signal for CPU Face Detection: A Budget-Matched
Case Study with Measured Audio–Visual Coupling"**
*Emphasises:* signal utility, matched design, the coupling measurement, and case-study scope.
*Implies:* no method claim, no generality claim, no cost claim.
*Risk:* long, and slightly dry.

### Selected title (on defensibility alone)

# T1 — "Does Voice Activity Predict Visual Availability? A Budget-Matched Study of Speech-Gated Face Detection on CPU"

**Why.** It is the only candidate that (a) makes no method contribution claim, (b) makes no cost
claim at all — removing the most dangerous overclaim surface entirely, (c) makes no generality
claim, (d) carries no Paper 1 terminology collision, and (e) frames the work as a question, which
is the honest description of a study whose answer is largely negative. "Visual availability" is
also the exact term the reference is permitted to use, keeping the title consistent with the
ground-truth discipline.

**Required support:** the abstract must state "single recording" in its first two sentences, since
the title does not. If a subtitle slot is available, append ", on a single interview recording".

---

# 7. Final research story

**WHY.** Running a face detector on every frame of a long recording is wasteful when the subject is
usually in the same place and the expensive model is invoked thousands of times. Voice activity
detection is nearly free and already computed in many interview pipelines, which makes it an
appealing signal for deciding when the visual detector is worth running. The intuition is that
people are visible when they are engaged, and engagement is audible.

**QUESTION.** Does that intuition survive a fair test? Specifically: when the number of processed
frames is held exactly constant, does VAD select frames that retain more visual information than a
selector that ignores the audio entirely?

**EXPERIMENT.** Thirteen conditions on one 25-minute recording, all selecting from one shared
5-FPS grid of 7,642 frames. An always-on baseline; four VAD-gated conditions at 0/250/500/1000 ms
padding; and, for each, a uniform and a random control processing *exactly* the same number of
frames. Matching the budget is what isolates the question — it separates "does the audio signal
inform frame choice?" from "does processing fewer frames hurt?". Selection is deterministic; the
reference is the always-on condition's own detector output, blind-validated by a human and
reported as detector-defined visual availability rather than ground truth.

**RESULT.** The answer depends on which retention metric is asked. Blind uniform sampling retained
more *distinct visual events* than VAD at every budget (0.9517 vs 0.8345 at the tightest). VAD
retained more *visible time* than both controls at every budget (0.6925 vs 0.6762 and 0.6769).
The two standard metrics therefore rank the same three policies in opposite directions on
identical data.

**FAILURE MODE.** The two selectors do not merely differ in degree; they fail differently.
Restricted to multi-frame intervals — those a human could plausibly confirm — uniform sampling
achieved perfect existence recall at every budget, missing nothing real even while skipping a
third of all frames. Every interval uniform missed was a single-frame detector flicker. VAD
additionally lost genuine multi-frame events, up to 2.2 s long.

**MECHANISM.** Why would a signal chosen for its relevance lose to one that ignores the data?
Because on this recording the signal is barely relevant: the mutual information between voice
activity and candidate visibility is 0.00896 bits against 0.40752 bits of visibility entropy —
2.20 %. The subject sits in front of the camera whether or not anyone is speaking. A gate carrying
almost no information about its target behaves like a blind sampler, and a *clustered* blind
sampler is strictly worse than an evenly spaced one at guaranteeing a sample inside every interval.

**SYSTEM IMPLICATION.** Even where gating works, its benefit is bounded by what it can address.
Gating removed up to 32.35 % of detector invocations, but the pipeline decodes the video
sequentially under every condition, so decode cost is untouched. Invocation reduction and runtime
reduction are different quantities, and in a decode-bound pipeline the second is a small fraction
of the first.

**LIMITATION.** All of this is one recording, one layout, one subject. The coupling figure explains
*this* recording; it does not establish that the ordering, the mechanism, or the 2.20 % value
transfer. A recording where speech and visibility are genuinely coupled might reverse the result —
that is a hypothesis this study generates and cannot test.

**CONTRIBUTION.** What is learned despite that: a fair, budget-matched comparison shows a
training-free acoustic gate can be worse than ignoring the audio, and the reason is measurable in
advance rather than discoverable only after running the experiment. Two standard retention metrics
can disagree in sign, so reporting one is not enough. And in decode-bound pipelines, the honest
cost unit is detector invocations, not seconds.
