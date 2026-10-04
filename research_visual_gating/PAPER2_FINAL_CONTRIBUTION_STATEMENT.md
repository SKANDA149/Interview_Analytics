# Paper 2 — Final Contribution Statement (FROZEN)

Supersedes the contribution section of `FINAL_CONTRIBUTION_FREEZE.md`. Wording corrected for the
independence/weak-coupling distinction and for the withdrawn ~6 % figure.

---

## Final title (FROZEN)

# Does Voice Activity Inform Visual Availability? A Budget-Matched Study of Speech-Gated Face Detection on CPU

### Is "Inform" scientifically appropriate? **Yes — and it is the correct choice over "Predict".**

The measured mutual information is **I = 0.00896 bits, strictly greater than zero**. Voice activity
therefore *does* carry information about detector-defined visual availability — just very little
(2.20 % of the target's entropy). "Inform" asserts exactly that and nothing more: that an
information relationship exists and was quantified.

"Predict" would be wrong. Predictive validity requires demonstrating that the relationship holds
out-of-sample, which this study explicitly did not test (n = 1). The earlier draft title used
"Predict"; that was an overclaim and the change to "Inform" is correct.

The question form is also doing real work: it permits the honest answer — *"yes, but barely"* —
which a declarative title could not carry without either overstating or understating.

### Alternatives considered

1. *"How Much Does Voice Activity Tell Us About Visual Availability? …"* — most explicitly
   quantitative, but wordy and the colloquial "tell us" weakens it.
2. *"Does Voice Activity Indicate Visual Availability? …"* — near-equivalent to "Inform";
   "indicate" leans marginally toward a decision rule rather than an information relationship.
3. *"Speech-Gated Face Detection on CPU: A Budget-Matched Retention and Cost Study"* — safest
   possible, but loses the question that organises the paper.

**None is safer than the current title on any axis that matters.** Title frozen as stated. One
requirement travels with it: because the title does not say "single recording", the **abstract must
say so within its first two sentences**.

---

## A. One-sentence contribution

On a single CPU-only interview recording, we show that a training-free voice-activity gate retains
fewer distinct detector-defined visual events than budget-matched blind uniform sampling while
covering slightly more visible time, and we measure the audio–visual coupling (2.20 % of the
target's entropy) and the detector-invocation accounting that frame how far such a gate can help
at all.

## B. Contribution paragraph

Voice activity is an appealing control signal for scheduling an expensive visual detector, because
it costs almost nothing to compute. We test that intuition on a CPU-only interview pipeline by
comparing a training-free Silero VAD gate against uniform and random sampling controls that process
exactly the same number of frames, and find the comparison is metric-dependent: at every tested
budget the gate retains fewer of the distinct detector-defined visibility intervals and slightly
more of the visible time than blind sampling, so the two standard retention metrics rank the same
policies in opposite directions. On this recording the gate carries little information about its
target — 0.00896 bits against 0.40752 bits of target entropy, or 2.20 % — which is weak coupling
rather than independence, and is consistent with the gate behaving close to a blind sampler whose
selections are temporally clustered. Gating reduced detector invocations by up to 32.35 %, but
because the recording is decoded in full under every condition, invocation reduction and runtime
reduction are distinct quantities and the reported runtimes show no proportional saving.

---

## Classification of every major idea

### OBSERVED (measured, recomputed from raw data this session)

| Idea | Value |
|---|---|
| Uniform > random > VAD on existence recall at all four budgets | 0.9517 / 0.9241 / 0.8345 at 5170; pattern holds at 6315, 6815, 7221 |
| VAD > random ≈ uniform on coverage recall at all four budgets | 0.6925 vs 0.6769 / 0.6762 at 5170 (margin ≈ 0.016) |
| The two metrics rank the policies in opposite directions | Both metric sets, identical conditions and data |
| Uniform achieves existence recall 1.0000 on the 117 multi-frame intervals at every budget | Multi-frame sensitivity analysis |
| 100 % of uniform's misses are single-frame at every budget; VAD's are 62.5 / 50.0 / 55.6 / 66.7 % multi-frame | Missed-interval composition |
| Longest interval VAD missed: 2.2 s frame-span | Missed-interval spans |
| I = 0.00896 bits, H = 0.40752 bits, I/H = 2.20 %; P(visible) 0.9185, P(vis\|active) 0.9402, P(vis\|silent) 0.8730 | Coupling analysis |
| Detector invocations reduced by up to 32.35 % (5,170 of 7,642) | Frame counts |
| Peak memory condition-invariant at ≈107 MB | All 13 conditions, <1 % spread |
| Reported runtimes show no proportional saving; equal-budget spread (48.45 s vs 51.17 s) is comparable to between-policy differences | Pilot hardware |
| 0 of 28 isolated single-frame detections confirmable under blind human review; 32 of 50 on the independent random stratum | Manual validation |

### SUPPORTED INTERPRETATION (consistent with the evidence; not proven by it)

- The retention behaviour is **consistent with** weak measured coupling combined with temporally
  clustered gate selection.
- The failure asymmetry is **consistent with** evenly spaced selection bounding the maximum
  unsampled gap while clustered selection does not.
- The absence of proportional runtime saving **follows from** decode being invariant across
  conditions by construction — this one is architectural and is the strongest of the three.
- The 28 isolated detections are **best interpreted as** visually ambiguous events of uncertain
  status, not as confirmed detector errors.

### HYPOTHESIS (stated as such; never as a result)

- Measuring audio–visual coupling before deployment **may** indicate whether a speech gate can
  help on a given recording.
- On a recording with substantially stronger coupling, the gate's existence-recall deficit **may**
  shrink or reverse.
- The observed ordering **may** hold on recordings with similar layout and visibility base rate.

### NOT CLAIMABLE

- That the results generalise beyond this recording.
- That the coupling measure has predictive validity.
- That speech and visual availability are independent (**I > 0**; this is weak coupling).
- That 2.20 % is characteristic of interview recordings.
- That padding has an effect separable from the budget it induces.
- That gating produces any total-runtime saving, at any percentage.
- That the auxiliary 81.6 / 18.4 split describes the evaluated system.
- Any methodological first-ness (pre-empted by arXiv:2608.22359).
- That the detector reference constitutes ground truth.
- Any statistical significance, confidence interval, or error bar on a retention metric.

---

**Scope discipline, restated.** The coupling measurement explains **this recording**. It does not
substitute for cross-recording validation, and the paper must never let those two things blur. What
transfers is the *method of measuring coupling*; what does not transfer is the *value it took here*.
