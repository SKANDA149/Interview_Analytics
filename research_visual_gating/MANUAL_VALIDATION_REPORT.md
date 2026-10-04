# Manual Visual Validation — Experiment 1 Report

Frozen inputs used, unchanged: the completed 13-condition pilot (`runs.jsonl`, 39 timed runs),
its shared reference (`reference_frame_results_v1i.json`, 145 reference intervals, 28 of them
exactly single-frame / 19.3%), and the audit finding that the 200ms interval-merge is
numerically inert at this recording's 5 FPS grid (never bridges a single absent frame). None of
that was rerun or altered by this experiment.

## Sample construction

Two strata drawn from the existing 7,642-frame reference, no new YuNet/VAD inference:

- **Stratum 1** — all 28 single-frame reference intervals, each shown as 3 views (the detected
  frame itself, plus its immediate 5-FPS grid neighbors before/after) = 84 role-instances.
  One pair of role-instances coincides on the same physical frame (ref_index 4608 is
  simultaneously SF09's "next" neighbor and SF10's "prev" neighbor — those two single-frame
  intervals are separated by exactly one absent grid frame, itself an instance of the
  "single-gap" pattern the audit already documented as never bridged). That frame was shown
  once; its judgment is counted for both roles. Result: **83 unique frame images** covering
  **84 role-instances**.
- **Stratum 2** — 50 timestamps drawn uniformly at random over [0, 1528.267s) with
  `random.Random(20260914)` (a seed distinct from the pilot's matched-random seed, 20260913),
  each snapped to the nearest 5-FPS grid index by arithmetic only (no detector field
  consulted). 0 collisions with stratum 1 occurred; no redraws were needed.
- Presentation order shuffled with a third, distinct seed (20260915); sample IDs S001–S133
  assigned in that shuffled order.
- **Total: 133 unique frames, 134 specified role-instances.**

## Blinding

The published viewer showed each sample only an anonymous `sample_id`, a ROI crop
(1075, 560, 205×160) of the exact video frame, and blind controls (Present / Not present /
Uncertain, plus a context-interpretation question shown only for stratum-1 frames). It never
loaded or referenced `reference_frame_results_v1i.json`, `runs.jsonl`, YuNet confidence, the
original present/absent label, interval identity, condition labels, or VAD state. The
sample→detector mapping was kept sealed in a private file, not committed to the repository or
shown to the labeler, until this join was performed after labeling was reported complete.

## Annotation counts

All 133 unique frames received a judgment (134/134 role-instances covered, counting the shared
frame twice). No `NO` responses were recorded anywhere in the 134-judgment set.

| Group | n | YES | NO | UNCERTAIN |
|---|---|---|---|---|
| (A) Isolated single-frame detections (centers only) | 28 | 0 (0.0%) | 0 (0.0%) | 28 (100.0%) |
| (B) Independent random sample | 50 | 32 (64.0%) | 0 (0.0%) | 18 (36.0%) |
| Supplementary: all 84 stratum-1 role-instances (center+neighbors) | 84 | 0 | 0 | 84 (100.0%) |

| (C) Context interpretation, 84 stratum-1 role-instances | n | % |
|---|---|---|
| Genuine appearance | 84 | 100.0% |
| Detector noise | 0 | 0.0% |
| Uncertain | 0 | 0.0% |

**Primary comparison** (human YES-rate, no significance test — this is a small validity check,
not a hypothesis-testing study): 0.0% (28 isolated detections) vs. 64.0% (50 random sample), a
64.0-point gap. UNCERTAIN is reported separately throughout and is not collapsed into YES or NO
anywhere in this analysis.

## Do isolated single-frame detections look disproportionately noisy?

Reported exactly as observed, in both directions at once, because the two axes disagree:

- On **presence** (the direct, per-frame YES/NO/UNCERTAIN question), the 28 isolated detections
  scored 0% YES against 64% YES on the random baseline — a large, one-directional gap. The
  labeler could not confidently confirm a visible candidate face in *any* of the 28 flagged
  frames or their neighbors.
- On **context interpretation** — a judgment about whether the surrounding pattern looks like a
  genuine brief appearance versus a detector artifact — the labeler called all 84 role-instances
  "genuine appearance," 0% "detector noise."

Taken together this does not cleanly confirm the audit's original H1 (single-frame detections
are disproportionately detector noise/false positives) — a "noise" verdict would need low
context-genuineness, and that never happened here. But it does not confirm H0 either (that
these detections are visually confirmable, ordinary events) — 0% YES is a stark result. The
honest reading is: **isolated single-frame detections are consistently visually ambiguous
(motion-blurred, partial, or borderline) rather than either clearly real or clearly spurious**,
which is a different (and more specific) finding than "disproportionately noisy," and one this
sample size (n=28) cannot resolve further without a larger or differently-designed check.

## Is the detector-defined reference acceptable?

Acceptable as a **detector-defined visual-availability signal**, not as ground truth for
"the candidate was clearly visible." Across the whole reference set only 28/145 intervals
(19.3%) are single-frame, and it is specifically that subset — not the reference set generally
— that this experiment shows is visually ambiguous under independent review. The reference set's
majority (multi-frame intervals, sustained appearances) was not resampled here and remains
unchallenged by this experiment.

## Does this materially affect the completed pilot's conclusions?

No change to any reported number, and the core comparative finding (matched-blind sampling wins
existence recall at every tested budget; VAD wins coverage recall at every tested budget) does
not depend on whether the 28 single-frame intervals represent genuine appearances — it depends
only on which frames YuNet flagged as present, which every condition in the pilot was scored
against identically and symmetrically. What changes is the *interpretive framing*: describing
the reference as "ground-truth candidate visibility" is no longer defensible; describing it as
"YuNet's detector-defined visual availability, corrected for the known single-frame-detection
ambiguity" is.

## Remaining limitations

- n=28 for the isolated-detection stratum is small; the 0% YES-rate is a strong signal but the
  exact rate has wide uncertainty at this sample size (no significance test was run, per the
  protocol, so this is a descriptive observation, not a statistically bounded one).
- Single labeler, single pass — no inter-rater agreement number is available from this
  experiment.
- Zero `NO` responses across all 134 judgments is itself notable: it suggests the ROI crop
  and/or judgment criteria made confident negatives hard to render, which may explain why
  ambiguous frames defaulted to UNCERTAIN rather than NO. This should be treated as a property
  of this instrument/sample, not evidence that the video never has clearly-absent frames.
- The context-interpretation axis and the presence axis point in different directions for the
  same 84 frames; this experiment cannot say which axis a reader should weight more without a
  follow-up (out of scope here per the stopping rule).

FINAL RECOMMENDATION:
B

EXPERIMENT 1 STRENGTHENED THE STUDY:
MIXED

The check did what it was designed to do: it replaced an untested assumption ("the reference set
is candidate-visibility ground truth") with a measured, honestly-reported result. That result is
double-edged — it rules out treating the reference as verified ground truth (0% of the 28
flagged single-frame events were independently confirmed as clearly visible), which weakens the
strongest possible claim the paper could have made, but it also does not support the harsher
reading that these are simply detector noise (the same frames were rated "genuine appearance"
100% of the time), so the pilot's core comparative findings stand. Net effect: the paper is more
defensible with this evidence than without it, provided it now frames the reference explicitly
as detector-defined visual availability rather than ground truth, per recommendation B.
