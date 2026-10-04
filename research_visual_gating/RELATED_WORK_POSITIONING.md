# Related-Work Positioning — Paper 2

## Verification status, stated first

**arXiv:2608.22359 was retrieved in full text.** WebFetch to arxiv.org was persistently
rate-limited (HTTP 429) from my own context; full text was obtained via a delegated retrieval, and
I then **independently re-verified the title, full author list, date and the complete abstract
verbatim through a second, unrelated host** (alphaxiv.org). The abstract I retrieved matches the
delegated retrieval **word for word**, which corroborates the fidelity of the quotes below.

- **Independently verified by me:** title, authors (Masoud Jalayer, Changyi Li, Yu Xiao), date
  (23 August 2026), and the complete abstract.
- **From delegated full-text retrieval, not personally re-read:** the section-level quotes
  (Eq. 2, the random-spans baseline sentence, hardware description, occupancy figures). These are
  marked *(full text)* below. If any single quote were to prove inaccurate the direction of the
  conclusion would not change, because the decisive facts are in the abstract I verified myself.

Paper metadata: arXiv:2608.22359, cs.CV, submitted 23 Aug 2026. Comments field: *"18 pages,
5 figures, 9 tables. Under review at IEEE BigData 2026, Industrial and Government Track."*

---

## What 2608.22359 actually does — the 18 questions

Quotes marked **[abstract, verified by me]** or *(full text)*.

| # | Question | Answer | Evidence |
|---|---|---|---|
| 1 | Audio gate deciding which segments get expensive visual processing | **YES** | **[abstract]** "We propose audio-first triage: select windows using the lightest modality, scored before any video frame is decoded" |
| 2 | Uniform sampling baseline | **YES** | **[abstract]** "surpasses uniform sampling through the mid-range on Ego4D over 247 clips" |
| 3 | Random sampling baseline | **YES** | *(full text, §4)* "Random spans places spans of matched length statistics at random, which controls for any generic temporal prior rather than for the score itself" |
| 4 | Matched compute budget | **YES** | **[abstract]** "cuts 9-20% of VLM calls at matched coverage"; *(full text §3.1)* "all methods are compared at matched ρ" |
| 5 | Budget definition | Number of VLM calls | *(full text §3.1)* "Cost(C) = \|C\|/M"; "For a budget ρ ∈ (0,1] we set K_max = ⌊ρM⌋" |
| 6 | Coverage metric | Interval-intersection indicator | *(full text §3.1, Eq. 2)* "Cov(C) = (1/N) Σ 𝕀[∃ C_j ∈ C : C_j ∩ A_i ≠ ∅]" |
| 7 | Equivalent to our interval-existence recall | **YES** | Same construction: fraction of annotated intervals receiving ≥1 retained sample |
| 8 | Gate trained or training-free | **TRAINED** | **[abstract]** "we **train the selector** to trigger once per action"; *(full text §3.3)* a 0.41 M-parameter dilated TCN with BCE loss over frozen BEATs features |
| 9 | GPU or CPU | **GPU** | *(full text §4)* "Each job is allocated one GPU, six CPU cores… scheduled across NVIDIA V100 / A100 / H100 nodes" |
| 10 | Visual task | VLM captioning | **[abstract]** "Vision-Language Captioning"; noun/verb naming |
| 11 | Datasets | EPIC-KITCHENS-100, Ego4D | **[abstract]** |
| 12 | Scale | 247 Ego4D clips; 24 EK-100 recordings, 3,392 actions | **[abstract]** "over 247 clips"; *(full text §4.1)* |
| 13 | Face detection | **NO** — generic VLM | *(full text)* no face-detection component |
| 14 | Temporal padding / dilation study | **PARTIAL** | *(full text §3.3)* "gaps below 0.6 s are closed"; min-span 0.15 s; call separation δ = 8 s. No symmetric padding sweep |
| 15 | CPU-only inference cost | **NO** | *(full text §4)* throughput reported in GPU-hours |
| 16 | Audio–visual statistical coupling (correlation / MI) | **NO** (indirect only) | *(full text §4.2)* correlates gain with *occupancy*, not with audio-visual coupling; explicitly: "Occupancy estimates headroom and no more: it says nothing about … whether they are **audible**" |
| 17 | Negative result — audio gating losing to uniform | **YES** | *(full text §4.3)* "Every off-the-shelf acoustic frontline sits well below uniform sampling, reaching 29 to 30 % of actions at 25 % of the calls against 41.0 %"; "at half the stream the sign reverses against uniform sampling on 20 recordings of 24" |
| 18 | Mechanism for success/failure | **YES** — occupancy/headroom | *(full text §1)* "every dataset we could measure sits between 85.1 and 99.3 % … which is why uniform sampling is a strong baseline here" |

---

## Novelty matrix

| Paper | Gate | Visual workload | Sampling baseline | Matched budget? | CPU/GPU | Training? | Coverage metric | Main overlap | Key difference |
|---|---|---|---|---|---|---|---|---|---|
| **Paper 2 (ours)** | Silero VAD, fixed params | YuNet face detection in fixed ROI | uniform + random | Yes, exact frame counts | **CPU-only** | **Training-free** | interval-existence **and** temporal-coverage | — | Decode-bound cost regime; MI coupling; metric dissociation |
| **Jalayer et al. 2026** (2608.22359) | Trained TCN on frozen BEATs | VLM captioning (Qwen3-VL-8B) | **uniform + random** | **Yes, matched ρ** | GPU | **Trained** (MIL objective) | interval-intersection only | Evaluation design, metric, off-the-shelf-gate negative result, headroom mechanism | Trained gate; GPU; decode is *skipped*, not fixed cost; 247 clips |
| Listen to Look (CVPR 2020) | Trained audio preview | Action recognition CNN | uniform/random clips | Matched FLOPs | GPU | Trained | accuracy, not coverage | "audio directs visual compute" | No coverage metric; no interval-existence |
| Reducto (SIGCOMM 2020) | Cheap visual differencing | Server-side DNN | filtering systems | Accuracy-target matched | Edge CPU + GPU backend | Threshold-tuned | accuracy | cheap gate → expensive detector | Visual gate, not audio; no random control |
| AKS (CVPR 2025) | Query-conditioned visual scorer | Video-LLM | uniform | Fixed frame budget | GPU | Trained | relevance + coverage objective | fixed-budget vs uniform | Requires decoding; no audio; no random arm |
| Wi-Filter (Sensors 2025) | WiFi CSI motion | Edge video analytics | static thresholds | No | Edge | Threshold | none | cheap **non-visual** gate | Not audio; no matched-budget blind control |
| Audio-Guided Keyframe Selection (ACM 2025, 10.1145/3768184.3768216) | Audio | Video description | **unverified** | **unverified** | unverified | unverified | unverified | audio→keyframe selection | **Paywalled; not retrieved. Must be read before submission.** |

---

## Contribution classification

Every proposed Paper 2 contribution, classified without hedging.

| Proposed contribution | Classification | Reason |
|---|---|---|
| Matched-budget blind (uniform + random) controls for an audio gate | **NOT NOVEL** | Published in 2608.22359 with the random arm given the identical justification |
| Interval-existence recall as a retention metric | **NOT NOVEL** | Eq. 2 of 2608.22359; standard in temporal action localisation |
| "Audio can direct where visual compute is spent" | **NOT NOVEL** | Prior art to CVPR 2020 (Listen to Look) |
| A training-free/off-the-shelf audio gate underperforms uniform sampling | **NOT NOVEL** | 2608.22359 §4.3: "Every off-the-shelf acoustic frontline sits well below uniform sampling" |
| A base-rate/headroom explanation for why uniform is hard to beat | **NOT NOVEL** | 2608.22359 identifies occupancy (85.1–99.3 %) as exactly this |
| **Mutual-information coupling between the audio gate signal and the visual target, measured** | **SUPPORTED NOVELTY** | 2608.22359 explicitly disclaims this: occupancy "says nothing about … whether they are audible". We measure audibility-of-the-target directly (I/H = 2.20 %) |
| **Dissociation between interval-existence and temporal-coverage recall** (the two rank policies oppositely) | **SUPPORTED NOVELTY** | 2608.22359 reports coverage only; no source found reporting both and showing opposite rankings |
| **Selective inference under a decode-bound cost ceiling** (gating addresses only 18.4 % of runtime; ≤6 % achievable saving) | **SUPPORTED NOVELTY** | Structurally impossible in 2608.22359, whose saving comes precisely from *not decoding*: "Nothing outside the selected windows is decoded, which is where the saving is realized". Our pipeline cannot skip decode, so the cost ceiling is a different regime |
| Qualitative failure-mode separation (uniform misses only single-frame flicker; VAD misses multi-frame events) | **SUPPORTED NOVELTY** | Not found in any retrieved source |
| Blind human validation of a detector-defined reference | **SUPPORTED NOVELTY** (minor) | Not found; modest contribution on its own |
| Generalization of any of the above beyond one recording | **UNVERIFIED** | n=1 |
| Whether the coupling metric *predicts* gate performance on unseen recordings | **UNVERIFIED** | Requires a second recording with contrasting coupling; untested |

---

## 2B — The 2608.22359 decision

# A: 2608.22359 materially overlaps our central methodological contribution.

**Evidence.** The central methodological contribution as previously framed — evaluating an audio
gate against budget-matched uniform *and* random blind controls, scored by an interval-existence
coverage metric, and finding that an off-the-shelf audio gate loses to uniform — is present in
2608.22359 in all four of its parts:

1. *Matched-budget comparison:* "all methods are compared at matched ρ" *(full text §3.1)*.
2. *Both blind controls:* uniform **[abstract, verified]** and "Random spans … controls for any
   generic temporal prior rather than for the score itself" *(full text §4)*.
3. *The same metric:* "Cov(C) = (1/N) Σ 𝕀[∃ C_j ∈ C : C_j ∩ A_i ≠ ∅]" *(full text §3.1)* — our
   interval-existence recall.
4. *The same negative finding, in kind:* "Every off-the-shelf acoustic frontline sits well below
   uniform sampling" *(full text §4.3)*.

It also anticipates the *shape* of our explanation: they attribute uniform's strength to high
occupancy (85.1–99.3 %), which is structurally the same argument as our high visibility base rate
(91.85 %).

**This is a genuine and substantial hit, and it must not be softened.** Any framing that presents
the matched-budget evaluation design, the existence metric, or "training-free audio gating loses
to uniform" as this paper's contribution would be incorrect and, given the paper is under review
at IEEE BigData 2026, likely to be caught.

**What nonetheless survives as distinct** — narrower than before, but real:

- **A different cost regime.** Their saving exists *because* selection happens before decoding:
  "Nothing outside the selected windows is decoded, which is where the saving is realized." Our
  pipeline decodes sequentially regardless, so gating addresses only the 18.4 % detector share and
  ≤6 % of runtime. That is not a weaker version of their result; it is the opposite architectural
  case, and it is the regime most CPU-only offline pipelines actually sit in.
- **Measured audio–visual coupling.** They explicitly decline to measure whether events are
  *audible*; we measure exactly that, information-theoretically.
- **The metric dissociation.** They report coverage alone and so cannot observe that the two
  standard retention metrics invert the ranking.
- **Failure-mode structure.** Uniform's misses are 100 % single-frame at every budget; VAD's are
  majority multi-frame. Not reported anywhere retrieved.

**Consequences for the manuscript.** 2608.22359 must be cited as the anchor of related work, not
discovered by a reviewer. The honest positioning is: *they show a trained, objective-aligned audio
gate can beat uniform sampling when selection avoids decoding; we show that in a decode-bound
CPU pipeline a training-free gate cannot, quantify how little cost is even addressable, and
measure the audio–visual coupling that determines whether such a gate has anything to work with.*

**Outstanding literature item:** ACM 10.1145/3768184.3768216 ("Audio-Guided Keyframe Selection for
Video Description Generation", Wang et al., 2025) remains **paywalled and unread**. Its title is
close enough that it must be obtained through institutional access before submission. It is the
one remaining unquantified novelty risk.
