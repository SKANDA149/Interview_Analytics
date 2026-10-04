# Paper 1 / Paper 2 Differentiation Audit

**Paper 1 (submitted):** *Speaker-Attributed Fluency Metrics on CPU: Runtime, Memory and
Diarization-Error Characterization of an Offline Interview Speech Pipeline*

**Paper 2 (planned):** VAD-gated selective visual inference (title frozen separately)

## Basis of this audit

Paper 1's *actual experimental artefacts* were read, not a description of them:
`research/results/analysis_report.txt`, `research/results/analysis_report_wide.txt`,
`research/results/audit_report.md`. What Paper 1 actually does, from those files:

- A **perturbation / dose-response study**. Two synthetic error operators — `role_swap` and
  `missed_speech` — are injected into reference diarization at severities 0, 0.10, 0.25, 0.50.
- Downstream **fluency metrics** are recomputed at each severity: WPM, Silence %, long-pause
  count, longest pause, average pause, filler count, `nlp_score`.
- Results are reported as **% distortion versus the severity-0 baseline**, with
  distortion-per-unit-severity and linearity checks per operator.
- Scale: 36 aggregated conditions, 180 runs, 3 seeds, recomputation verified 0 mismatches.
- Its audit found and corrected an artifact: the aligner's nearest-neighbour fallback
  re-attributed deleted-segment words, mechanically inflating WPM at severity 0.50.

**Decisive structural fact discovered during this audit:** Paper 1 operates on
`data/input/sample.mp4` (1088.7 s of audio, 2,498 words, reference diarization covering 813.7 s).
Paper 2 operates on `research_visual_gating/data/video1_infosys_h264.mp4` (1528.267 s).
**The two papers use entirely disjoint recordings.** No datum is shared.

---

## Overlap audit table

| Dimension | Paper 1 | Paper 2 | Overlap Risk | Resolution |
|---|---|---|---|---|
| **Research question** | How do diarization/attribution errors propagate into speaker-attributed fluency metrics? | Does VAD gating select visually useful frames when the frame budget is matched? | **NONE** | Different questions entirely — error propagation vs. scheduling-signal utility |
| **Hypothesis** | Attribution error severity distorts fluency metrics measurably and operator-specifically | Speech activity carries information about candidate visibility usable for frame selection | **NONE** | Disjoint |
| **Data** | `sample.mp4` — 1088.7 s audio, 2,498 words, reference diarization | `video1_infosys_h264.mp4` — 1528.267 s video, 7,642-frame grid | **NONE** | Disjoint recordings; state this explicitly in Paper 2 §Method |
| **Modality** | Audio only (speech, transcript, diarization) | Audio **as a control signal only** + video as the analysed modality | **LOW** | Paper 2 never analyses speech *content*; VAD output is used solely as a binary schedule |
| **Target component** | Diarization + transcription + fluency metric computation | YuNet face detection scheduling | **NONE** | Different pipeline stages, different models |
| **Dependent variables** | WPM, Silence %, pause statistics, filler count, nlp_score | Interval-existence recall, temporal-coverage recall, detector invocations | **NONE** | No dependent variable is shared |
| **Metrics** | % distortion vs. baseline; distortion-per-unit-severity; linearity | Recall metrics on detector-defined intervals; mutual information; invocation counts | **NONE** | Disjoint metric families |
| **Experimental design** | Dose-response perturbation, 3 seeds, 36 conditions, stochastic operators | Budget-matched sampling comparison, 13 conditions × 3 repeats, deterministic selection | **LOW** | Both are controlled studies on a CPU pipeline; the designs share nothing beyond that generic property |
| **Failure mode studied** | Attribution error → metric distortion; aligner fallback artifact | Gate misses multi-frame visual events; blind samplers miss only single-frame flicker | **NONE** | Different failure objects |
| **Contribution** | Characterization of how attribution error degrades fluency measurement | Characterization of a scheduling signal's utility under matched budget, in a decode-bound regime | **NONE** | Distinct |
| **Novelty claim** | Diarization-error → fluency-metric propagation on CPU | Measured audio–visual coupling; metric dissociation; decode-bound cost ceiling | **NONE** | Distinct |
| **Practical implication** | How much attribution error a fluency pipeline can tolerate | Whether to implement audio gating for a visual detector (answer: not in this regime) | **NONE** | Distinct engineering decisions |
| *Shared context (acceptable)* | Interview analytics; CPU/offline; same repository; Silero VAD present somewhere in both stacks | same | **ACCEPTABLE** | Shared project context is normal and not self-overlap |

---

## The five questions

**1. Is Paper 2 scientifically distinct from Paper 1?**
**Yes, unambiguously.** Different recording, different modality under study, different pipeline
component, different dependent variables, different metrics, different failure mode, different
contribution. The only shared elements are the project context and the fact that both run on CPU —
neither of which is a research claim.

**2. Is there any duplicated experiment?**
**No.** Paper 1 runs a stochastic dose-response perturbation over diarization; Paper 2 runs a
deterministic budget-matched sampling comparison over video frames. No condition, operator or
run is reused.

**3. Is there any reused result that could create self-overlap?**
**One hazard exists and must be actively managed.** `research/visual_selection_experiment.py` and
`research/results/visual_selection_pilot.json` sit inside **Paper 1's folder** but are the
**withdrawn** `sample.mp4` visual-gating pilot — the invalid Paper 2 precursor (any-face saturation,
no stable candidate identity, float-timestamp interval fragmentation). Resolution:

- These files are **historical provenance only**. They are not modified and not cited.
- **No number from them appears in Paper 2.** Paper 2's results derive solely from
  `results/video1_infosys_checkpointed/`.
- Because they live under `research/`, a reader with repository access could mistake them for
  current work. Paper 2's artefact/reproducibility appendix should state plainly that
  `research_visual_gating/results/video1_infosys_checkpointed/` is the sole source of reported
  results.

Beyond that: no runtime, memory, or metric value from Paper 1 is reused in Paper 2.

**4. Is there any terminology that makes them appear to be the same paper?**
**Yes — four specific collisions, all fixable by wording.**

| Risky phrase | Why it reads like Paper 1 | Required Paper 2 phrasing |
|---|---|---|
| "CPU runtime and memory characterization of an interview pipeline" | Near-verbatim Paper 1 subtitle | "detector-invocation cost of selective visual inference" |
| "speech pipeline" / "speech analysis" | Paper 1's object of study | "acoustic activity as a scheduling signal" |
| "silence" / "pauses" | Paper 1 dependent variables | "VAD-silent frames" or "non-speech grid frames" — never "pauses" |
| "candidate" without qualification | Paper 1 means an attributed *speaker*; Paper 2 means a *spatial region* | "the candidate region of interest" / "candidate visibility" on first use, and define it as spatial |

Additional standing rule: Paper 2 must never use *diarization*, *speaker attribution*, *DER*,
*WPM*, *fluency*, *embedding*, or *turn-taking* as descriptors of its own method — only, if
strictly necessary, to say what it does **not** do.

**5. Does Paper 2 need an explicit differentiation paragraph?**
**Yes.** Not because the overlap is real, but because the two papers come from the same author,
the same repository and the same application domain, and Paper 1 is already submitted. A reviewer
or an editor checking for salami-slicing needs the distinction made for them rather than inferred.
One short paragraph, placed at the end of the Introduction:

> This work is independent of our prior study of speaker-attributed fluency metrics, which
> characterises how diarization errors propagate into speech-derived measurements. That work
> analyses speech content on a different recording; the present work uses acoustic activity only
> as a binary scheduling signal, performs no speaker attribution or speech-metric computation, and
> studies frame selection for a visual detector. The two share an application domain and a CPU
> deployment constraint, and nothing else: no data, no metric, and no experimental condition.

**This paragraph is mandatory, and the claim it makes is true** — the disjoint-recording fact
makes it verifiable rather than rhetorical.

---

## Verdict

# PAPER 1 DIFFERENTIATION: PASS

Conditional on two mechanical actions, neither of which requires new work:

1. Include the differentiation paragraph above in the Introduction.
2. Apply the four terminology substitutions, and state in the artefact appendix that
   `results/video1_infosys_checkpointed/` is the sole source of reported results — explicitly
   excluding the withdrawn `research/results/visual_selection_pilot.json`.
