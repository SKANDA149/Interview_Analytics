# Updated IEEE Readiness Conclusion — Paper 2

Supersedes the readiness section of `PAPER2_FINAL_IEEE_READINESS_AND_GAP_ANALYSIS.md`. That
document and all historical reports are preserved unchanged for provenance.

Inputs: `COUPLING_AND_FAILURE_MODES.md`, `coupling_results.json`, `RELATED_WORK_POSITIONING.md`.

---

## What changed since the gap analysis

**Phase 1 delivered more than expected.** All six coupling values reproduced exactly using the
production selectors. Two corrections and two new findings:

- *Correction:* uniform misses **7** intervals at budget 5170, not the "~9" I estimated. Production
  is authoritative.
- *New:* **uniform sampling never misses a multi-frame interval at any budget** (100 % of its
  misses are single-frame flicker, all four budgets). Restricted to the 117 multi-frame intervals,
  uniform achieves **perfect existence recall at every budget**, while VAD still misses 12.8 % at
  the tightest.
- *New:* decode is **81.6 %** of runtime, YuNet **18.4 %**. Gating can address only that 18.4 %;
  maximum achievable total saving at the 32.35 % skip rate is **~6 %**.

**Phase 4 delivered worse news than expected.** arXiv:2608.22359 (Jalayer et al., 23 Aug 2026,
under review at IEEE BigData 2026) materially overlaps the central methodological contribution —
matched-budget uniform *and* random controls, the identical interval-existence metric, and the
finding that off-the-shelf audio gates lose to uniform. Decision **A**, stated in full in
`RELATED_WORK_POSITIONING.md`.

---

## Part 3 — Reassessment

**1. Strongest defensible contribution.** A characterisation of selective visual inference in a
**decode-bound CPU pipeline**: gating addresses only 18.4 % of runtime (≤6 % achievable saving),
a training-free speech gate loses real multi-frame events that blind uniform sampling never loses,
and the audio–visual coupling that would have to exist for the gate to help is measured and found
to be 2.20 % of the target's entropy.

**2. Strongest defensible novelty claim.** Not the evaluation design and not the negative result —
both are pre-empted. What survives: *measuring* audio–visual coupling as the quantity that governs
whether an audio gate can help (2608.22359 explicitly declines to, saying occupancy "says nothing
about … whether they are audible"), the **metric dissociation** (existence and coverage rank
policies oppositely), and the **decode-bound cost ceiling** as a regime distinct from
skip-decode architectures.

**3. Strongest defensible practical claim.** For an offline CPU pipeline that must decode
sequentially, audio gating of a cheap per-frame detector is **not worth implementing**: it can
recover at most ~6 % of runtime and it costs real visual events relative to uniform sampling,
which is simpler and strictly better on event retention at equal budget. That is a genuinely
useful negative engineering result.

**4. What remains unsupported.** Generalization beyond one recording; that the coupling metric
*predicts* gate performance on unseen recordings; robustness to threshold/layout perturbation;
that padding *per se* has any effect separable from the budget it induces; and any claim of
methodological first-ness.

**5. Does the coupling analysis genuinely add explanatory value?** Yes, but narrowly and with one
caveat. It converts "VAD lost" into "VAD had almost no information to work with (I/H = 2.20 %),
and its clustered temporal structure then cost it real events." It also supplies a quantity
measurable *before* running anything. The caveat: 2608.22359 already argues base-rate headroom
explains uniform's strength, so the *shape* of the explanation is not new — the direct measurement
of audio-to-visual-target information is.

**6. Does the result remain interesting after the literature overlap?** Partially. As "training-free
audio gating loses to uniform" — no, that is now a known result on far more data. As "in a
decode-bound CPU regime the entire selective-inference premise is capped at ~6 %, and here is the
coupling measurement that tells you in advance whether a gate can help" — yes, modestly, for a
systems/short-paper audience.

**7. Is n=1 acceptable only as a case study?** Yes, and now more firmly than before. With a
comparator evaluating 247 clips and 24 recordings, a single-recording study cannot make any
general claim. **The coupling analysis does not solve this.** It explains the observed recording;
it does not demonstrate generalization across recordings. Those are different claims and I will
not let them blur: what generalises is the *method of measuring coupling*, not the *value* it took
here.

**8. Single highest-value additional experiment.** One recording with **deliberately higher
speech–visibility coupling**, run through the frozen protocol, testing the prediction that VAD's
existence-recall deficit shrinks as I/H rises. This is the only experiment that would convert the
coupling metric from a description into a validated predictor — which is the sole surviving claim
with real reach. It is *not* required for a case-study submission.

---

## Part 4 — Final decision

**EXPERIMENTALLY READY: YES.** Phase 1 is complete on frozen data using production selectors; all
targets verified; failure modes, sensitivity, cost re-basing and design limitations documented.

**LITERATURE READY: YES.** The blocking verification is done. The answer is unfavourable, but it
is established rather than suspected, and one residual item is named.

**MANUSCRIPT READY: NO.** The contribution must be rebuilt around what survives decision A. The
previously planned framing is no longer available, and writing before that re-scoping is settled
would produce a paper whose central claim is refuted by a citation.

# STATE B — ONE SPECIFIC ITEM REMAINING

### Minimum required work

**The one item: commit to the re-scoped contribution, and re-measure the decode/detect split on
the pilot machine.** These are one item because they are the same decision — the decode-bound cost
ceiling becomes the paper's primary contribution, so the number carrying it must be measured on
the same hardware as the rest of the study rather than in the analysis container.

- Re-run the two-pass micro-benchmark (`decode_detect_split.py`, unchanged) on the pilot machine.
  Effort: ~15 minutes once the device workspace is available. It is currently blocked by the
  reported Windows-update failure of the local workspace.
- Adopt the contribution statement in Part 3 items 1–3 as the paper's spine, demoting the
  matched-budget design from "contribution" to "method, following Jalayer et al."

**Not required, and deliberately excluded:** a second recording (valuable but optional for a
case-study target), extra budget points to break the padding/budget confound (disclosure suffices),
threshold-sensitivity sweeps (no claim depends on them).

**Recommended target venue:** workshop / short-paper / industrial track. A general IEEE conference
claim is not available: the methodological novelty is pre-empted and n=1 stands.

---

# NOT YET READY

**What remains, in full:**

1. **Re-measure the decode/detect split on the pilot hardware** (~15 min; blocked on the device
   Linux workspace, which currently fails to start). The container measurement — decode 81.6 %,
   detect 18.4 %, ≤6 % achievable saving — establishes the ratio but is on different hardware than
   the pilot's `wall_time_s`, and this number is now the paper's primary contribution.
2. **Commit to the re-scoped contribution** (Part 3, items 1–3), demoting the matched-budget
   evaluation design and the bare negative result to "method/context, following Jalayer et al."
3. **Obtain and read ACM 10.1145/3768184.3768216** ("Audio-Guided Keyframe Selection for Video
   Description Generation", 2025) through institutional access. Paywalled; the last unquantified
   novelty risk.
4. **Fix the 1-FPS / 5-FPS provenance hazard** before drafting — the recalibration sweep (1404/1529,
   57 absence intervals) and the pilot grid (7019/7642, 145 intervals) must never appear as the
   same quantity.

Items 2 and 4 are writing decisions and cost nothing but care. Item 1 is a 15-minute measurement
blocked on tooling. Item 3 depends on library access. **None requires a new experiment, and none
requires a second recording.**
