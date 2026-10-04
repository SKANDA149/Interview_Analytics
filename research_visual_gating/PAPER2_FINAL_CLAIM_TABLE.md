# Paper 2 — Final Claim Table

Every major claim the manuscript could make, classified. **SUPPORTED** / **SUPPORTED WITH
LIMITATION** / **HYPOTHESIS ONLY** / **REMOVE**. All evidence re-verified this session against the
frozen artefacts.

---

## Retention claims

| Claim | Status | Evidence | Allowed wording | Forbidden wording |
|---|---|---|---|---|
| Uniform > random > VAD on interval-existence recall at all four budgets | **SUPPORTED** | `runs.jsonl`; 0.9517/0.9241/0.8345 at 5170, pattern holds at 6315/6815/7221 | "On this recording, matched uniform sampling retained more distinct detector-defined intervals than VAD gating at every tested budget." | "VAD is worse than uniform" (unqualified); "significantly" |
| VAD > random ≈ uniform on temporal-coverage recall at all four budgets | **SUPPORTED WITH LIMITATION** | 0.6925 vs 0.6769/0.6762 at 5170; holds at all budgets. Margins are small (≈0.016) and the metric degenerates toward the budget fraction on a saturated recording | "VAD gating covered more visible time than either blind control at every budget, though the margin was small (≈0.016 at the tightest budget)." | Presenting the coverage win as substantial or decisive; omitting the margin |
| The two retention metrics rank the same policies in opposite directions | **SUPPORTED** | Both metric sets, same conditions, same data | "The two standard retention metrics rank these policies in opposite directions on identical data." | "We introduce" / "novel metric" |
| Uniform misses no multi-frame interval at any budget | **SUPPORTED** | `coupling_results.json` multi-frame sensitivity: uniform 1.0000 at 5170/6315/6815/7221 | "Restricted to the 117 multi-frame intervals, matched uniform sampling achieved existence recall of 1.0000 at every tested budget." | Presenting this as the primary metric in place of the all-145 figure |
| Uniform's misses are 100 % single-frame at every budget; VAD's are majority multi-frame | **SUPPORTED** | Missed-interval composition: uniform 7/5/3/0 all single-frame; VAD 62.5/50.0/55.6/66.7 % multi-frame | "The two policies fail differently: every interval uniform sampling missed was a single-frame detection, whereas the majority of VAD's misses spanned multiple frames (up to 2.2 s)." | "VAD fails catastrophically"; any causal claim about why |
| Uniform's fixed spacing guarantees a hit in any interval longer than the spacing | **HYPOTHESIS ONLY** | Geometric argument, not tested | "A plausible explanation is that evenly spaced selection bounds the maximum unsampled gap, whereas clustered selection does not." | Stating it as the demonstrated mechanism |

## Coupling claims

| Claim | Status | Evidence | Allowed wording | Forbidden wording |
|---|---|---|---|---|
| I(visible;VAD) = 0.00896 bits = 2.20 % of H(visible) on this recording | **SUPPORTED** | Computed with production selectors; six values verified | "On this recording, voice activity carried 0.00896 bits about candidate visibility, 2.20 % of the visibility signal's entropy." | Any phrasing implying this value is typical or transferable |
| The gate is informationally close to a blind sampler here | **SUPPORTED WITH LIMITATION** | I/H = 2.20 %; P(visible\|active) 0.9402 vs P(visible\|silent) 0.8730 vs base 0.9185 | "In this recording the gate carried little information about its target and behaved close to a blind sampler." | Generalising to other recordings or gate types |
| Weak coupling + temporal clustering explains the retention pattern | **SUPPORTED WITH LIMITATION** | Coupling measured; clustering follows from VAD interval structure; the link is inferential | "The observed behaviour is consistent with weak measured coupling combined with temporally clustered selection." | "Because of", "explains", "demonstrates that" |
| Coupling predicts when speech gating will help on other recordings | **HYPOTHESIS ONLY** | Untested; n=1 | "We hypothesise that measuring this coupling before deployment may indicate whether speech gating can help; testing this requires recordings with contrasting coupling." | Any present-tense claim that it predicts anything |
| 2.20 % is a property of interview recordings | **REMOVE** | No evidence | — | Entire claim |

## Cost claims

| Claim | Status | Evidence | Allowed wording | Forbidden wording |
|---|---|---|---|---|
| VAD gating reduces detector invocations by up to 32.35 % | **SUPPORTED** | Exact frame counts, deterministic, `runs.jsonl` | "VAD gating reduced YuNet invocations by 32.35 % at zero padding (5,170 of 7,642 grid frames)." | Converting this into a runtime figure |
| Invocation reduction did not produce proportional runtime reduction | **SUPPORTED** | Pilot-hardware runtimes; equal-budget spread (F_B 48.45 s vs R_B 51.17 s) exceeds several between-policy differences | "Reduced invocations did not yield proportional runtime reduction; at identical budgets, run-to-run variation was of the same order as between-policy differences." | Quoting A−B = 11.7 % as a saving |
| Peak memory is condition-invariant at ≈107 MB | **SUPPORTED** | All 13 conditions within a <1 % band | "Peak resident memory was condition-invariant at approximately 107 MB." | Presenting memory as a discriminating axis |
| Decode is ~82 % and detection ~18 % of processing time | **SUPPORTED WITH LIMITATION** | Auxiliary micro-benchmark, **separate hardware** from the reported runtimes | "An auxiliary micro-benchmark on separate hardware, using the same video, model, ROI and grid, attributed approximately 82 % of processing time to decoding and 18 % to detector inference." | Stating it as a property of the evaluated system; omitting the hardware caveat |
| Maximum achievable total saving is ≈6 % | **REMOVE** | Derived from the auxiliary split on non-pilot hardware | — | Entire figure, unless re-measured on the pilot machine |
| "VAD gating reduces total pipeline runtime by 32 %" | **REMOVE** | False | — | Entire claim, in every form |
| In a decode-bound pipeline, addressable cost is bounded by the detector's share | **SUPPORTED** | Architectural fact: decode is invariant across conditions by construction | "Because the recording is decoded in full under every condition, selective inference can only address the detector's share of processing cost." | Attaching a specific percentage from the auxiliary benchmark |

## Reference and validation claims

| Claim | Status | Evidence | Allowed wording | Forbidden wording |
|---|---|---|---|---|
| The reference is detector-defined visual availability, not ground truth | **SUPPORTED** | Blind validation: 0/28 isolated detections confirmable vs 32/50 random stratum | "We refer to the reference throughout as detector-defined visual availability." | "ground truth", "annotations", "labels" |
| Isolated single-frame detections are visually ambiguous | **SUPPORTED WITH LIMITATION** | 0/28 YES, 28/28 UNCERTAIN, 0/28 NO; single labeller, n=28 | "No isolated single-frame detection was confirmable as a visible face under blind review (0 of 28), though all were judged consistent with a genuine brief appearance rather than detector noise." | "are detector noise" / "are false positives" |
| The 200 ms merge is inert at a 0.2 s grid | **SUPPORTED** | 0 of 61 single-absent-frame gaps bridged | "At this grid spacing the 200 ms merge bridges no single-frame dropout (0 of 61)." | Presenting it as a bug or as corrected |

## Design and scope claims

| Claim | Status | Evidence | Allowed wording | Forbidden wording |
|---|---|---|---|---|
| Frame selection and both recall metrics are deterministic | **SUPPORTED** | One distinct value per condition across 3 repeats, all 13 conditions | "Selection and both retention metrics are deterministic; the three repeats bound runtime variability only." | Error bars on recall; "n=3" beside a recall value |
| Matched controls process exactly the same frame counts | **SUPPORTED** | Exact equality verified | "Controls process exactly the same number of frames as their matched VAD condition." | "approximately matched" |
| Padding effects are separable from budget effects | **REMOVE** | Perfectly confounded by construction | — | Any claim attributing an effect to padding as such |
| The results generalise beyond this recording | **REMOVE** | n=1 | — | Entire claim, in every form |
| The approach is robust / superior / general | **REMOVE** | Untested | — | All three words |

## Novelty claims

| Claim | Status | Evidence | Allowed wording | Forbidden wording |
|---|---|---|---|---|
| First to evaluate audio gating against budget-matched blind controls | **REMOVE** | arXiv:2608.22359 §3.1, §4 | — | Entire claim |
| Novel interval-existence recall metric | **REMOVE** | Their Eq. 2; standard in TAL | — | Entire claim |
| Novel use of audio to direct visual compute | **REMOVE** | Prior art to CVPR 2020 | — | Entire claim |
| Training-free audio gating underperforms uniform — as a new finding | **REMOVE** | Their off-the-shelf frontline ablation reports it | Permitted only as: "consistent with the off-the-shelf acoustic frontline results reported by Jalayer et al." | Presenting it as this paper's discovery |
| Measuring audio–visual coupling as the governing quantity | **SUPPORTED WITH LIMITATION** | They explicitly decline to measure audibility; we measure it. But only on one recording | "We measure this coupling directly, which prior work identifies as unaddressed by occupancy-based headroom estimates." | "We are the first"; implying the measure is validated as predictive |
| The existence/coverage dissociation | **SUPPORTED WITH LIMITATION** | Not found in retrieved literature; single recording | "To our knowledge these two retention metrics have not previously been reported side by side for the same policies; on this recording they disagree in direction." | "Novel metric"; dropping "to our knowledge" |
| No prior work performs audio-guided keyframe selection with blind controls | **REMOVE** | ACM 10.1145/3768184.3768216 unread (403) | — | Entire claim until that paper is read |

---

## Summary

| Status | Count |
|---|---|
| SUPPORTED | 11 |
| SUPPORTED WITH LIMITATION | 8 |
| HYPOTHESIS ONLY | 2 |
| REMOVE | 10 |

Ten claims must be removed outright. Seven of those ten are novelty or generality claims — which
is the honest shape of this paper: **strong on what it measured, weak on what it can claim to have
invented.**
