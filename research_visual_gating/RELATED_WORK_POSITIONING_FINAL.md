# Related-Work Positioning — FINAL

Supersedes `RELATED_WORK_POSITIONING.md`, which is preserved unchanged. This file adds the closed
ACM item and states the four required verdict categories explicitly.

## Verification record

- **arXiv:2608.22359** — Jalayer, Li & Xiao, *"Pre-Decoding Acoustic Triage for Budgeted
  Vision-Language Captioning of Untrimmed Egocentric Video"*, 23 Aug 2026, cs.CV. Comments field:
  *"18 pages, 5 figures, 9 tables. Under review at IEEE BigData 2026, Industrial and Government
  Track."* Full text retrieved. **Title, authors, date and complete abstract independently
  re-verified by me through a second, unrelated host**, matching word for word. Section-level
  quotes come from the full-text retrieval and are marked *(full text)*.

- **ACM 10.1145/3768184.3768216** — *"Audio-Guided Keyframe Selection for Video Description
  Generation"*, Wang et al., Proc. 2025 2nd Int. Conf. on Image Processing, Intelligent Control and
  Computer Engineering. **Retrieval attempted again this session; ACM DL returned HTTP 403
  (paywall). Full text remains unread.** Nothing about its baselines, budget matching, metrics, or
  hardware is asserted below. **This is the one residual, unquantified novelty risk, and it must be
  obtained through institutional access before submission.** It is *not* treated as prior art for
  any specific claim, because title-only inference is not evidence — but neither is it cleared.

---

## 1. Aspects ALREADY ESTABLISHED in prior literature

These must be presented as method inherited from prior work, never as Paper 2 contributions.

| Aspect | Established by | Evidence |
|---|---|---|
| Using audio to decide where to spend visual compute | Listen to Look (CVPR 2020); Jalayer et al. 2026 | Six years of prior art |
| Budget-matched comparison of an audio gate against **uniform** sampling | Jalayer et al. 2026 | *(full text §3.1)* "all methods are compared at matched ρ" |
| A **random** control justified as isolating the signal from the temporal prior | Jalayer et al. 2026 | *(full text §4)* "Random spans … controls for any generic temporal prior rather than for the score itself" |
| Interval-existence / interval-intersection coverage as the retention metric | Jalayer et al. 2026; standard in temporal action localisation | *(full text §3.1, Eq. 2)* "Cov(C) = (1/N) Σ 𝕀[∃ C_j ∈ C : C_j ∩ A_i ≠ ∅]" |
| **Off-the-shelf audio gates underperforming uniform sampling** | Jalayer et al. 2026 | *(full text §4.3)* "Every off-the-shelf acoustic frontline sits well below uniform sampling, reaching 29 to 30 % of actions at 25 % of the calls against 41.0 %" |
| A base-rate / headroom explanation for uniform's strength | Jalayer et al. 2026 | *(full text §1)* occupancy "between 85.1 and 99.3 % … which is why uniform sampling is a strong baseline here" |
| Counting model invocations rather than wall-clock as the cost unit | Jalayer et al. 2026; Savran et al. 2018 (event-camera AV VAD) | Invocation-based costing is established practice |
| Cheap non-visual side-channel gating expensive visual analytics on constrained hardware | Wi-Filter (Sensors 2025) | Same architectural template, different modality |

## 2. Aspects that REMAIN DISTINCT

| Aspect | Why it survives |
|---|---|
| **Decode-bound cost regime** | Jalayer et al.'s saving exists *because* selection precedes decoding — *(full text §3.5)* "Nothing outside the selected windows is decoded, which is where the saving is realized." Our pipeline decodes sequentially regardless, so gating addresses only the detector's share. This is the opposite architectural case, not a weaker instance of it. |
| **Measured audio–visual coupling** | Jalayer et al. explicitly decline this — *(full text §4.2)* occupancy "says nothing about how long events run, whether they cluster, or whether they are **audible**." We measure audibility-of-the-target directly: I = 0.00896 bits, 2.20 % of H(visible). |
| **Existence/coverage metric dissociation** | They report coverage alone, so cannot observe that the two standard retention metrics rank identical policies in opposite directions. No retrieved source reports both side by side. |
| **Failure-mode asymmetry** | Uniform's misses are 100 % single-frame at every budget; the gate's are majority multi-frame. Not found in any retrieved source. |
| **Training-free gate as the subject** | In Jalayer et al., off-the-shelf frontlines are an *ablation* against their trained selector; here the training-free gate is the object of study, in a deployment setting where training a gate is not an option. |
| **Blind human validation of the detection reference** | Not found in any retrieved source; minor but genuine. |

## 3. Aspects only WEAKLY DIFFERENTIATED

State these with care; do not lean on them.

| Aspect | Why the differentiation is weak |
|---|---|
| "Our gate is training-free, theirs is trained" | True and material, but their off-the-shelf ablation already covers the training-free case empirically. Our version is a *deeper* treatment of a case they *sampled*, not a new phenomenon. |
| "Our workload is face detection, theirs is VLM captioning" | A workload substitution, not a conceptual difference. A reviewer may fairly call it an instantiation detail. |
| "CPU-only versus GPU" | Only matters *because* it produces the decode-bound regime. Stated alone it is a deployment detail; it must always be stated together with the decode-cost consequence, or it reads as thin. |
| "Symmetric padding sweep" | They study gap-closing (0.6 s), minimum span (0.15 s) and inter-call separation (δ = 8 s) — different mechanisms, but the same family of temporal-dilation controls. And our padding is confounded with budget, limiting what we can say about it anyway. |
| "Interview domain rather than egocentric" | Domain change only. Carries no independent scientific weight. |

## 4. Claims to REMOVE COMPLETELY

- **"First/novel in comparing audio gating against budget-matched blind controls."** Directly false.
- **"Novel interval-existence recall metric."** It is their Eq. 2 and standard in TAL.
- **"Novel use of audio to direct visual compute."** Prior art to CVPR 2020.
- **"We show that training-free audio gating underperforms uniform sampling"** *stated as a new
  finding*. Permitted only as corroboration: "consistent with the off-the-shelf frontline ablation
  reported by Jalayer et al."
- **"We identify why uniform sampling is a strong baseline."** Their occupancy argument precedes
  ours. Only the *measurement instrument* (mutual information on the gate-vs-target pair) is ours.
- **Any claim that the coupling value or the observed ordering generalises.** Unverified, n = 1.
- **Any cost claim derived from the container-measured decode/detect split** (see
  `FINAL_COST_MEASUREMENT.md`).

---

## Required citation posture

arXiv:2608.22359 must be cited **in the Introduction, not only in Related Work**, as the immediate
predecessor whose method this paper adopts. Discovering it in review would be far worse than
foregrounding it. The honest one-line positioning:

> Jalayer et al. show that a *trained*, objective-aligned acoustic gate can beat uniform sampling
> when selection happens before decoding; we ask what remains of that premise when the gate is
> training-free and decoding cannot be skipped, and we measure the audio–visual coupling that
> determines whether such a gate has anything to work with.

**Outstanding blocking-adjacent item:** obtain ACM 10.1145/3768184.3768216. Until read, the
manuscript should avoid asserting that no prior work performs audio-guided keyframe selection with
blind controls, since that specific paper is unexamined.
