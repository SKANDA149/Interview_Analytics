# PAPER 2 — FINAL IEEE READINESS AND GAP ANALYSIS

Scope boundary maintained throughout: no speaker attribution, diarization, DER, WPM/fluency,
embeddings, OCR, or semantic scoring. Paper 1 is not extended by anything below.

---

## 1. Executive conclusion

**Readiness state: B — ALMOST READY, ONE SPECIFIC ANALYSIS REQUIRED.** The required work is
**not** a second recording and **not** any new inference run. It is a re-analysis of data already
frozen on disk, which I prototyped during this gap analysis and which produced a decisive result.

Two findings drive this conclusion.

**Finding 1 — the paper is missing its mechanism, and the mechanism is measurable from existing
data.** The study currently reports *that* VAD gating loses to blind uniform sampling on
interval-existence recall and wins on temporal coverage. It does not explain *why*, and therefore
cannot say when the result would differ. Computing the coupling between speech activity and
candidate visibility on the frozen Recording-1 data answers this directly:

> Mutual information I(visible ; VAD-active) = **0.00896 bits**, against H(visible) = 0.40752 bits
> — speech carries **2.20 %** of the information about whether the candidate is on camera.
> P(visible | VAD-active) = 0.9402 vs P(visible | VAD-silent) = 0.8730, against a base rate of
> 0.9185.

In this recording the VAD gate is, informationally, **a near-blind sampler with an unhelpful
temporal structure**. That single number converts the headline result from an anecdote into a
mechanism with predictive content: VAD gating can only beat blind sampling where speech and
visibility are actually coupled, and the degree of coupling is measurable *a priori* on any
recording. This is what makes an n=1 study defensible; without it, n=1 is indefensible.

**Finding 2 — the novelty claim as currently conceived is substantially pre-empted.** A delegated
literature search surfaced **arXiv:2608.22359, "Pre-Decoding Acoustic Triage for Budgeted
Vision-Language Captioning of Untrimmed Egocentric Video" (August 2026)**, reported to compare an
audio-first gate against uniform *and* random baselines at matched budget, with the random arm
explicitly justified as controlling for the temporal prior, and an interval-intersection coverage
metric. **I independently verified that this paper exists with that exact title** (arXiv listing
plus four aggregator mirrors). **I could not verify its internal details** — the fetch proxy
rate-limited every full-text attempt. Those details are therefore *subagent-reported and
unconfirmed*, and confirming them is a blocking action item, because if accurate they kill the
claim "first to evaluate audio gating against budget-matched blind controls."

What survives is a coherent and, in my judgement, more interesting paper: a **training-free,
CPU-only negative result with a measured mechanistic explanation**, positioned as the counterpoint
to trained acoustic triage.

---

## 2. Current validated evidence

### 2.1 Verified against source files (not taken from the prompt)

I re-read `runs.jsonl` and `reference_frame_results_v1i.json` directly. **Every number quoted in
your prompt reproduces exactly.**

- 39 timed runs; 13 conditions × exactly 3 repeats; zero failures.
- Frame budgets exact: A 7642 / B 5170 / C 6315 / D 6815 / E 7221, with F_* and R_* matching their
  VAD counterpart to the frame.
- All 13 conditions' existence and coverage recall values match the prompt to 4 decimals.
- Frame selection deterministic: `(processed_frames, existence, coverage)` identical across all 3
  repeats of every condition, zero exceptions.
- Runtime means match to 0.01 s.
- Reference grid: 7642 frames, **7019 present (91.85 %)**, 623 absent.
- Reference intervals: **145**, of which **28 are exactly single-frame (0.2 s)**; median interval
  duration 1.0 s; longest 665.6 s.
- VAD: 588 raw speech intervals, 1029.3 s of speech (67.4 % of duration), selecting 5170 grid
  frames (67.65 %).

### 2.2 A provenance hazard to fix before writing

Your prompt cites "1404/1529 = 91.82 % detected, 125 absent, 57 absence intervals". Those are from
the **1-FPS recalibration sweep**, not the 5-FPS pilot grid. The pilot grid gives 7019/7642 =
91.85 % and **145** visibility intervals, not 57. The two are consistent (they agree on the
visibility rate to 0.03 pp) but they are different granularities of different artefacts. **The
manuscript must not mix them in the same table or sentence** — a reviewer who notices "57
intervals" in the setup and "145 intervals" in the results will lose confidence in the whole
paper.

### 2.3 New analysis produced during this gap analysis

Speech–visibility coupling (§1) plus a missed-interval duration breakdown at the tightest budget
(5170 frames):

| Strategy | Intervals missed | Median missed duration | Max missed duration | Of which single-frame |
|---|---|---|---|---|
| VAD (padding 0) | 24 | 0.6 s | 2.2 s | 9 |
| Uniform (matched) | ~9 | 0.2 s | 0.2 s | 9 |
| Random (matched) | 11 | 0.2 s | 0.6 s | 9 |

Two consequences, both important:

1. **VAD's failures are qualitatively worse, not just more numerous.** Blind samplers miss almost
   exclusively single-frame blips; VAD additionally misses genuine multi-frame events up to 2.2 s
   long. "Existence recall 0.8345 vs 0.9517" understates the difference in kind.
2. **Uniform's entire measured shortfall at this budget consists of single-frame intervals** — and
   the blind manual validation found *all 28* single-frame intervals visually UNCERTAIN, with 0
   confirmable as a visible face. So uniform's "misses" are almost entirely events whose reality a
   human could not confirm. This materially softens how the 0.9517-vs-1.0 gap should be described.

**Reconstruction caveat, stated plainly:** my independent re-implementation reproduced VAD
(0.8345) and random (0.9241) exactly, but gave uniform 0.9379 against the recorded 0.9517. My
uniform reconstruction is therefore *not* the production `select_frames_matched_uniform`. The
uniform row above is indicative, not exact, and Phase 1 must recompute it with the production
function. The VAD row is exact.

---

## 3. Scientific strengths

These are real and should not be undersold:

- **The matched-budget control design is the right experiment.** Isolating "does the speech signal
  inform frame choice?" from "does processing fewer frames hurt?" is precisely the confound most
  selective-inference papers leave open.
- **Determinism and auditability.** Frame selection is fully deterministic; an independent
  re-implementation reproduced every reported figure; 10/10 audit checks passed. This is above the
  median for the venue class.
- **Intellectual honesty already built in.** The reference is correctly labelled detector-defined
  visual availability rather than ground truth; the sequential-decode caveat blocks the tempting
  false claim that 32 % fewer detector calls means 32 % less wall-clock; a prior invalid pilot was
  withdrawn rather than quietly reused.
- **Blind human validation of the reference** (133 frames, sealed key, independent labeller) is
  unusual at this scale of study and directly answers the circularity objection.
- **The result is a negative one, reported as such.** Reviewers reward this when the experiment is
  clean, and this one is.

---

## 4. Critical weaknesses

Rated Critical / Important / Optional. Every entry names the specific fix.

### C1 — No mechanism (CRITICAL)
*Why it's a weakness:* the paper reports an outcome with no explanatory variable. The first
reviewer question — "why does VAD lose, and when would it win?" — currently has no answer, which
makes the finding look like an idiosyncrasy of one video.
*Fix:* the coupling analysis prototyped above, formalised: I(visible;VAD), conditional
probabilities, and the missed-interval duration distributions, per budget.
*New recording needed:* **No.** Pure re-analysis of frozen data.
*Effort:* 2–4 hours including figures.
*Value:* **Highest of any remaining work.** It converts n=1 from a fatal flaw into a scoped design,
and it is what makes the negative result interesting rather than merely true.

### C2 — Novelty claim pre-empted (CRITICAL)
*Why:* arXiv:2608.22359 (Aug 2026) appears to publish the matched-budget audio-gating evaluation
design. Claiming it as novel risks desk-level embarrassment.
*Fix:* verify that paper's internals (see §5), then re-position as the training-free/CPU-only
counterpoint. Drop the methodology-novelty claim; keep the negative result + mechanism.
*New recording:* No. *Effort:* 3–5 hours reading and repositioning. *Value:* protects the paper
from its single largest reviewer risk.

### C3 — n=1 generalizability (IMPORTANT, not critical *if* C1 is done)
*Why:* one 25-minute recording, one layout, one candidate. The comparison paper reportedly uses
247 Ego4D clips.
*Fix:* either (a) accept and scope explicitly as a case study, leaning on C1's mechanism to carry
generality; or (b) add one recording with *deliberately different coupling* — see §6.
*New recording:* only for (b). *Effort:* (a) free; (b) ~2 days plus data acquisition.
*Value:* (a) sufficient for workshop/short-paper tier; (b) required for full-conference tier.

### C4 — Statistical strength is thin and partly vacuous (IMPORTANT)
*Why:* n=3 repeats characterise timing jitter only — the recall metrics are *deterministic*, so
they have no variance and no error bars are possible. Reporting "3 repeats" next to recall numbers
invites a reviewer to think variance was measured when it cannot be. Separately, the four budgets
come from four padding values, so budget and padding are confounded by construction.
*Fix:* state explicitly that recall is deterministic and repeats bound only runtime variance; and
either acknowledge the padding/budget confound or add matched controls at budgets chosen
independently of padding.
*New recording:* No. *Effort:* 1 hour (statement) or ~4 hours (extra budget points).
*Value:* removes an easy, credibility-damaging objection.

### C5 — Compute-cost measurement doesn't support a cost claim (IMPORTANT)
*Why:* wall-clock differences between strategies at equal budget are within run-to-run noise (e.g.
R_B 51.17 s > F_B 48.45 s despite identical frame counts), and sequential decode dominates. Peak
RSS is flat at ~107 MB across all 13 conditions. So the paper's "CPU cost" axis currently measures
almost nothing.
*Fix:* report **detector invocations** as the primary cost unit (exact, deterministic,
defensible), demote wall-clock to a secondary observation, and report the decode/detect split so
readers can see what fraction of runtime is even addressable by gating.
*New recording:* No. *Effort:* 2–3 hours (the decode/detect split needs one instrumented run).
*Value:* high — it makes the cost axis honest and rescues the title's "CPU cost" framing.

### C6 — Single-frame intervals contaminate the headline metric (IMPORTANT)
*Why:* 28 of 145 reference intervals (19.3 %) are single-frame and human-unconfirmable, and they
constitute nearly all of blind sampling's measured misses. Existence recall is therefore partly a
measurement of detector flicker.
*Fix:* report existence recall both on all 145 intervals and on the 117 multi-frame intervals as a
sensitivity analysis.
*New recording:* No. *Effort:* 1–2 hours. *Value:* high; pre-empts a sharp reviewer question and
likely *strengthens* the VAD-vs-uniform gap, since VAD's extra misses are the multi-frame ones.

### C7 — The 200 ms merge is inert (OPTIONAL, disclosure only)
Already documented in the audit: at a 0.2 s grid the merge never bridges a single absent frame
(0 of 61). Disclose in a footnote; do not change it. *Effort:* 15 minutes.

### C8 — Reproducibility packaging (OPTIONAL but cheap)
Code, frozen configs, seeds (20260913 for matched-random) and the audit script exist but are not
packaged. A short artefact appendix plus a seed table is ~2 hours and is disproportionately
rewarded by reviewers.

---

## 5. Literature / novelty assessment

**Verification discipline applied:** I treated the delegated search as a lead, not a finding.
I independently confirmed **arXiv:2608.22359** exists with the exact reported title via the arXiv
listing and four independent mirrors. I **could not** verify its baselines, metric definition, or
trained-vs-training-free status — the fetch proxy returned HTTP 429 on every attempt at the
abstract and HTML full text. **Those specifics remain unconfirmed and must not be relied upon
until read directly.**

Reported landscape, with overlap risk:

| Work | Year | Overlap risk | Relationship |
|---|---|---|---|
| Pre-Decoding Acoustic Triage (arXiv:2608.22359) | 2026 | **HIGH** (if details confirm) | Reportedly the same matched-budget audio-gate evaluation design + interval-intersection metric. Trained gate, GPU, VLM captioning vs our training-free, CPU, face detection. |
| Wi-Filter (Sensors 25(3):701) | 2025 | MEDIUM | Cheap non-visual side channel (WiFi CSI) gating visual analytics on edge; no matched-budget blind control. |
| Event-camera-driven AV VAD (Savran et al.) | 2018 | MEDIUM | Inverse gate (vision gates audio); counts *invocations* not speedup; uses gate-open padding — anticipates our padding sweep in spirit. |
| Listen to Look (CVPR 2020) | 2020 | MEDIUM | Canonical "audio previews where to spend visual compute". Means "audio guides visual compute" is not novel at all. |
| Reducto (SIGCOMM 2020) | 2020 | LOW-MED | Cheap visual gate → heavy detector; the systems lineage we sit in. |
| Adaptive Keyframe Sampling (CVPR 2025) | 2025 | MEDIUM | Fixed-frame-budget selection vs uniform, with coverage as an explicit objective. |
| Audio-Guided Keyframe Selection (ACM ICIPICCE 2025) | 2025 | **UNKNOWN** | Fetch returned 403; title alone makes it a must-read. Unverified. |

**Novelty claims that must be dropped or narrowed:**

- **DROP** "first to compare audio/VAD gating against budget-matched blind controls" — pending
  C2 verification, this is almost certainly false as of Aug 2026.
- **DROP** "novel interval-existence recall metric" — standard in temporal action localisation.
- **DROP** "novel use of audio to direct visual compute" — prior art to at least CVPR 2020.
- **NARROW** the matched-budget methodology claim to its *instantiation*: training-free, zero-tuning
  VAD gate on a CPU-only face-detection workload.
- **KEEP** the metric **dissociation** — that the two standard retention metrics rank the same
  policies in *opposite* directions appears unaddressed. Claim the dissociation, not the metrics.
- **KEEP and lead with** the **negative result plus measured coupling mechanism**. Nothing found
  reports that a training-free audio gate is *worse than blind uniform* at event hitting, still
  less explains it via measured audio–visual independence.

---

## 6. Required additional experiment(s)

**Ranked by (validity impact × reviewer-objection closure) ÷ cost. The single highest-value item
requires no new data and no new inference.**

### THE ONE REQUIRED ANALYSIS — "Coupling and Failure-Mode Characterisation"

Everything below runs on already-frozen files (`reference_frame_results_v1i.json`,
`vad_raw_intervals.json`, `runs.jsonl`) plus the existing production selection functions. **No
YuNet, no VAD, no new recording, no protocol change.**

1. **Speech–visibility coupling.** I(visible;VAD), H(visible), P(visible|active),
   P(visible|silent), reported as the paper's explanatory variable. *(Prototyped: 2.20 % of
   entropy.)*
2. **Missed-interval duration distributions** per strategy per budget, using the **production**
   `select_frames_matched_uniform` (my reconstruction diverged — see §2.3).
3. **Multi-frame sensitivity analysis** — existence recall recomputed on the 117 multi-frame
   intervals (C6).
4. **Cost re-basing** — detector invocations as primary cost; one instrumented run for the
   decode-vs-detect split (C5).
5. **Deterministic-metric statement** + padding/budget confound disclosure (C4).

Effort: **1–2 focused days.** Value: closes C1, C4, C5, C6 — four of the six non-optional
weaknesses — and supplies the paper's explanatory spine.

### NOT REQUIRED: the second recording — and the honest answer to your two questions

> *Is the current n=1 experiment defensible as a carefully scoped methodological case study?*

**Yes — conditional on the coupling analysis being done.** With a measured mechanism, n=1 stops
being "we looked at one video and something happened" and becomes "we characterise a trade-off,
identify the recording property that governs it, and measure that property." The mechanism is what
transfers, not the recording. Without the coupling analysis, n=1 is **not** defensible, because
nothing distinguishes the result from an artefact.

> *Is n=1 sufficient for a conventional/general IEEE conference claim?*

**No.** A general claim about "VAD-gated selective visual inference" requires showing the
trade-off direction holds across recordings — and, ideally, *flips* where coupling is strong. One
video cannot support a general method claim, and if arXiv:2608.22359's scale (reportedly 247
clips) is accurate, the contrast will be stark.

**If you do pursue a second recording, the coupling analysis changes what to look for.** Do not
seek "a different interview." Seek a recording with **deliberately higher speech–visibility
coupling** — e.g. a candidate who leaves frame during their own thinking pauses, or a layout where
the camera view is tied to turn-taking. That is a *hypothesis test* of the mechanism (prediction:
VAD's existence-recall deficit shrinks or reverses as I(visible;VAD) rises), not a repetition. One
such recording is worth more than three arbitrary ones. Note the prior constraints still bind: no
re-encodes, no chunks, stable candidate ROI, no active-speaker switching, meaningful absence
periods — and `sample.mp4` is disqualified (100 % face-present saturation, 545/545 probes).

---

## 7. Claim audit

### SUPPORTED CLAIMS

| Claim | What justifies it |
|---|---|
| At four matched budgets on this recording, uniform > random > VAD on interval-existence recall | Verified in `runs.jsonl`, all four budgets, deterministic, independently re-derived |
| At the same budgets, VAD > random ≈ uniform on temporal-coverage recall | Same; gap is consistent but small (e.g. 0.6925 vs 0.6762) |
| VAD padding trades compute against retention monotonically on coverage | Verified: 0.6925 → 0.8417 → 0.9045 → 0.9541 across 0/250/500/1000 ms |
| VAD gating reduces detector invocations by up to 32.35 % at padding 0 | Exact frame counts, deterministic |
| In this recording, speech carries ~2 % of the information about candidate visibility | New analysis; I = 0.00896 of H = 0.40752 bits |
| VAD's missed intervals are longer than blind samplers' | New analysis; VAD median 0.6 s / max 2.2 s vs uniform 0.2 s (VAD figures exact) |
| Peak memory is condition-invariant at ~107 MB | All 13 conditions within a <1 % band |
| The reference is detector-defined visual availability, not human ground truth | Blind validation: 0/28 single-frame detections human-confirmable |

### NOT YET SUPPORTED

| Claim | What's missing |
|---|---|
| "VAD gating generalizes to interview recordings" | n=1; no second recording |
| "The trade-off direction is a property of VAD gating" | Mechanism identified but not tested on a contrasting-coupling recording |
| "Uniform sampling is the better choice for this pipeline" | Depends on which metric the downstream task needs — not established |
| "Selective inference yields meaningful CPU savings" | Wall-clock deltas are within noise; needs the decode/detect split (C5) |
| "The approach is robust" | No perturbation, threshold-sensitivity, or cross-layout testing |
| "We are first to use matched-budget blind controls for audio gating" | Likely false (arXiv:2608.22359); verification pending |

### CLAIMS WE MUST AVOID

- ❌ **"VAD reduces total pipeline runtime by 32 %."** Decode is sequential and dominates; measured
  wall-clock differences are inside run-to-run noise. This is the single most dangerous
  available overclaim.
- ❌ **"VAD preserves visual information."** It preserves *time coverage* while losing *events* —
  saying "information" unqualified inverts the actual finding.
- ❌ **"The detector provides ground truth."** Blind validation explicitly refuted this.
- ❌ **"VAD is better/worse than uniform"** unqualified. It is metric-dependent, and stating it
  one-sidedly in either direction is unsupported.
- ❌ **"The method is superior / robust / general."** None of the three is tested.
- ❌ Any claim of methodological first-ness in audio-gated visual inference.

---

## 8. Final contribution statement

Framing chosen on evidence: **D (trade-off characterisation), delivered as E (a scoped
methodological case study)**, with B (empirical CPU study) as supporting material. **Not A** — one
recording cannot support a general method. **Not C as the novelty** — the controlled
VAD-vs-uniform/random comparison is reportedly pre-empted by arXiv:2608.22359; it remains our
*method*, but it is no longer our *contribution*.

> **Primary contribution.** A controlled demonstration that a training-free, zero-tuning speech
> VAD gate is *worse* than budget-matched blind uniform sampling at hitting distinct visual
> events, while being *better* at covering visible time — together with a measured explanation:
> in this recording speech and candidate visibility are nearly independent
> (I = 0.00896 bits, 2.2 % of H(visible)), so the gate behaves as a blind sampler with an
> unfavourable clustered temporal structure. The mechanism is measurable *a priori* on any
> recording, which turns a single-video result into a stated precondition for when audio gating
> can help at all.
>
> **Secondary contribution.** A measurement caution: interval-existence recall and
> temporal-coverage recall rank the same sampling policies in opposite directions, so reporting
> either alone yields an incomplete and potentially reversed conclusion about a selective-inference
> policy.
>
> **Experimental contribution.** A fully deterministic, independently audited, CPU-only evaluation
> harness (13 conditions × 3 repeats, exact budget matching, frozen configuration, fixed seeds),
> with the detection reference subjected to blind human validation and reported honestly as
> detector-defined visual availability rather than ground truth.

---

## 9. IEEE readiness state

# STATE B — ALMOST READY; ONE SPECIFIC ANALYSIS REQUIRED

Qualified by target venue:

- **Workshop / short paper / case-study track:** State B. Complete the coupling analysis and the
  literature repositioning and it is submittable.
- **Full general IEEE conference track:** effectively **State C**, because the n=1 limitation is
  disqualifying for a general claim and closing it requires acquiring a new recording with
  contrasting coupling. This is a scope decision, not a research failure — choose the target
  first, then execute.

---

## 10. Minimum work remaining

**To submit as a scoped case study (recommended):**

1. Coupling + failure-mode analysis on frozen data (§6, items 1–5) — **1–2 days**
2. Verify arXiv:2608.22359 internals and reposition novelty — **0.5–1 day**
3. Fix the 1-FPS / 5-FPS provenance hazard (§2.2) — **1 hour**
4. Figures and tables from existing + new analysis — **1 day**
5. Manuscript — **3–5 days**
6. Reproducibility appendix and final audit — **0.5 day**

**Total: roughly 7–10 working days, with zero new expensive experiments.**

**Additional, only if targeting a general conference claim:** acquire one recording with
deliberately higher speech–visibility coupling, re-run the frozen 52-invocation protocol, and test
the mechanism's prediction. **+3–4 days plus data acquisition**, and it requires the device
workspace restored or an explicit decision to accept that runtime metrics would come from
different hardware than Recording 1's.

---

## 11. Exact next-step execution plan

### PHASE 1 — Coupling and failure-mode analysis *(no new experiment)*
- **Touch:** new `research_visual_gating/coupling_analysis.py`; read-only access to
  `reference_frame_results_v1i.json`, `vad_raw_intervals.json`, `runs.jsonl`; **import** the
  production `select_frames_matched_uniform` / `select_frames_random` rather than re-implementing
  (my reconstruction diverged on uniform).
- **Produce:** `COUPLING_AND_FAILURE_MODES.md` + `coupling_results.json` — I(visible;VAD),
  conditional probabilities, per-budget missed-interval duration distributions, multi-frame-only
  sensitivity recall, detector-invocation cost table.
- **Reuse:** all frozen pilot data; the existing audit script's verification idioms.
- **MUST NOT change:** VAD threshold, YuNet threshold, 5-FPS grid, ROI, padding values, matching
  procedure, seed 20260913, or any file under `results/video1_infosys_checkpointed/`.
- **Effort:** 1–2 days.

### PHASE 2 — Analysis consolidation
- **Touch:** `PAPER_RESULTS_TABLES.md` (extend, don't overwrite).
- **Produce:** revised Table 3 with a multi-frame-only column; new cost table keyed on detector
  invocations; new coupling table.
- **MUST NOT change:** any existing verified value. Add columns, never edit cells.
- **Effort:** 0.5 day.

### PHASE 3 — Figures
- **Produce:** (i) existing recall-vs-budget figures, regenerated; (ii) **new**: missed-interval
  duration distribution by strategy — this is the paper's money figure, it shows *how* VAD fails,
  not just *that* it does; (iii) coupling visualisation (visibility rate under speech vs silence
  against base rate).
- **Reuse:** `make_figures.py`.
- **Effort:** 1 day.

### PHASE 4 — Literature verification and repositioning ⚠️ *do this before writing a word*
- **Verify directly:** arXiv:2608.22359 (baselines, metric, trained/training-free, GPU/CPU) and
  ACM 10.1145/3768184.3768216 (403 on fetch — try institutional access).
- **Produce:** `RELATED_WORK_POSITIONING.md` with the narrowed novelty statement.
- **MUST NOT do:** cite either paper's contents until read in full.
- **Effort:** 0.5–1 day.

### PHASE 5 — Manuscript
- Structure follows §8: negative result up front, mechanism as the explanatory spine, metric
  dissociation as the measurement caution, limitations stated plainly (n=1, detector-defined
  reference, sequential-decode cost ceiling, padding/budget confound).
- **MUST NOT:** reuse any withdrawn `sample.mp4` numbers; preserve the historical invalid reports
  untouched for provenance.
- **Effort:** 3–5 days.

### PHASE 6 — Reproducibility and final audit
- Re-run the independent audit against final tables; package configs, seeds, frozen parameters;
  artefact appendix.
- **Effort:** 0.5 day.

---

**Do not begin Phase 5 before Phase 4 completes.** The single largest risk to this paper is not a
missing experiment — it is writing a novelty claim that a 2026 preprint has already invalidated.
