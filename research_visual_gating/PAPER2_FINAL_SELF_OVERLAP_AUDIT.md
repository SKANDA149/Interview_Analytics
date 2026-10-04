# Paper 2 — Final Self-Overlap Audit (vs submitted Paper 1)

Second pass, conducted adversarially: *"Could a reviewer who has already seen Paper 1 reasonably
read Paper 2 as a follow-up, extension, or repackaging?"*

## Structural evidence (verified, not asserted)

| Check | Result |
|---|---|
| Shared recording? | **No.** Paper 1: `sample.mp4`, 1088.7 s audio, 2,498 words. Paper 2: `video1_infosys_h264.mp4`, 1528.267 s. Disjoint. |
| Shared experimental condition? | **No.** Paper 1: `role_swap` / `missed_speech` at severities 0/0.10/0.25/0.50. Paper 2: A, B–E, F_B–F_E, R_B–R_E at four frame budgets. No overlap. |
| Shared dependent variable? | **No.** Paper 1: WPM, Silence %, pause count/length, filler count, nlp_score. Paper 2: interval-existence recall, temporal-coverage recall, detector invocations, mutual information. |
| Shared numerical result reused? | **No.** No Paper 1 figure, table or value appears in Paper 2's evidence base. |
| Shared conclusion presented as Paper 2 evidence? | **No.** |
| Shared model? | Silero VAD appears in both stacks — in Paper 1 as part of the speech pipeline, in Paper 2 **only** as a binary frame scheduler. Acceptable shared infrastructure. |

## Section-by-section reviewer simulation

| Section | Could it read as Paper 1? | Resolution |
|---|---|---|
| **Title** | No. Frozen title contains *visual availability*, *face detection*, *budget-matched*. Contains no Paper 1 vocabulary. Earlier working title *did* collide via "CPU … Interview … Pipeline" — that title is withdrawn. | Clear |
| **Abstract** | Risk if it opens on "interview pipeline on CPU". | Must open on the **visual** question; audio appears only as the gating signal |
| **Introduction** | Moderate risk — both motivate from offline interview analytics on CPU | **Mandatory differentiation paragraph** (already drafted) placed as the final paragraph |
| **Motivation** | Low | Frame as *detector invocation cost*, never as *speech pipeline cost* |
| **Terminology** | **Highest risk area** — four collisions identified | Substitution table below, mandatory |
| **Methods** | No. YuNet, ROI, frame grid, matched budgets have no Paper 1 counterpart | Clear |
| **Metrics** | No. Disjoint metric families | Clear |
| **Results** | No | Clear |
| **Conclusion** | Low risk if it avoids "speech pipeline" phrasing | Conclude on frame selection and detector cost |

## Mandatory terminology substitutions

| Forbidden in Paper 2 | Required substitute | Why |
|---|---|---|
| "silence", "pauses", "pause analysis" | **"VAD-silent frames"**, "non-speech grid frames" | Paper 1 dependent variables |
| "speech pipeline", "speech analysis" | **"acoustic activity as a scheduling signal"** | Paper 1's object of study |
| "CPU runtime and memory characterization of an interview pipeline" | **"detector-invocation cost of selective visual inference"** | Near-verbatim Paper 1 subtitle |
| "candidate" unqualified | **"candidate region of interest"** on first use, defined spatially | Paper 1 means an attributed *speaker*; Paper 2 means a *region* |

Also prohibited as descriptors of Paper 2's own method: *diarization*, *speaker attribution*,
*DER*, *speaker embeddings*, *WPM*, *fluency*, *turn-taking*, *transcript*. They may appear only
in the differentiation paragraph, stating what Paper 2 does **not** do.

## One residual hazard (managed, not eliminated)

`research/visual_selection_experiment.py` and `research/results/visual_selection_pilot.json` — the
**withdrawn** `sample.mp4` visual pilot — sit inside **Paper 1's** directory. A reviewer with
repository access could mistake them for current Paper 2 work, or for evidence that Paper 2 grew
out of Paper 1's codebase.

**Required mitigation, in the artefact appendix:** state that
`research_visual_gating/results/video1_infosys_checkpointed/` is the **sole** source of reported
results, and that `research/` contains Paper 1's experiment plus a withdrawn early pilot retained
only for provenance.

## Verdict

# PASS

Paper 2 is scientifically distinct from Paper 1 on every dimension that matters: different
recording, different modality under study, different pipeline stage, different dependent variables,
different metrics, different failure mode, different contribution. The shared elements — interview
domain, CPU deployment, the presence of Silero VAD somewhere in both stacks — are context, not
claims.

**PASS is conditional on three mechanical actions**, none requiring new work:

1. Include the differentiation paragraph in the Introduction.
2. Apply the four terminology substitutions throughout.
3. Add the artefact-appendix sentence naming the sole results directory.

Without action 2 in particular, an Introduction written in casual language could drift into Paper 1
territory within a paragraph. The substitutions are not stylistic preferences; they are the
mechanism by which this PASS is maintained in the written text.
