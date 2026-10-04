# Provenance Finalization — 1-FPS vs 5-FPS

## The two measurements, permanently separated

Two visibility measurements exist for the same recording. They agree closely, which is precisely
why they are dangerous: a reader who notices both will assume one is a typo unless the paper is
explicit.

| | **1-FPS recalibration sweep** | **5-FPS pilot grid** |
|---|---|---|
| Purpose | ROI stability pre-check, run *before* the pilot | The experiment itself |
| Sampling rate | 1 FPS | 5 FPS |
| Total samples | 1,529 | **7,642** |
| Detected visible | 1,404 | **7,019** |
| Absent | 125 | **623** |
| Visible fraction | 91.82 % | **91.85 %** |
| Interval count | 57 *absence* intervals | **145 visibility intervals** |
| Source | recalibration report | `reference_frame_results_v1i.json` |

**The interval counts are not comparable at all** — 57 counts *absence* intervals at 1 FPS; 145
counts *visibility* intervals at 5 FPS. They measure different objects at different resolutions.
Placing them near one another without labels would be a serious error.

## Audit result

Every current document was searched for accidental mixing. **No document treats the two as the
same quantity.** All four occurrences of the 1-FPS figures are inside explicit warnings not to mix
them (`FINAL_CONTRIBUTION_FREEZE.md`, `IEEE_READINESS_UPDATED.md`,
`PAPER2_FINAL_IEEE_READINESS_AND_GAP_ANALYSIS.md`, `PAPER2_MANUSCRIPT_BLUEPRINT.md`). No
historical document required modification.

## Authoritative quantities by manuscript section

### Method
- Recording: 1528.267 s, 1280×720, h264, 30 fps CFR.
- Analysis grid: **5 FPS, 7,642 frames**. Every condition selects a subset of this one grid.
- ROI (1075, 560, 205×160), YuNet 0.6, Silero 0.5 / 250 / 100 / 0 ms.
- **The 1-FPS sweep may be mentioned once**, only as: *"ROI spatial stability was pre-checked with a
  coarse 1 FPS sweep before the experiment; all reported results use the 5 FPS grid."* No 1-FPS
  count may appear in a results table.

### Main Results
- **5-FPS grid only, without exception.** 7,642 grid frames; 7,019 visible (91.85 %); 623 absent;
  145 reference intervals (28 single-frame, 117 multi-frame).
- All retention, coupling and cost values from `runs.jsonl` / `coupling_results.json`.
- **Forbidden in Results:** 1404, 1529, 91.82 %, 125, 57.

### Supplementary
- The 1-FPS recalibration sweep may appear in full, clearly headed *"1 FPS ROI pre-check (not the
  analysis grid)"*, for reproducibility.
- The `sample.mp4` screening result (545/545 probes face-present, 100 % saturation) may appear as
  the documented reason a second recording was rejected — labelled as a **screening** result on a
  **different recording**, never as a Paper 2 measurement.
- Full literature matrix; auxiliary decode/detect benchmark with its hardware caveat.

## Withdrawn data — must never appear anywhere

The original `sample.mp4` visual pilot is **withdrawn**: multi-participant active-speaker
switching, any-face presence saturated, no stable candidate identity, and a float-timestamp
interval-construction defect that fragmented continuous presence. Its artefacts
(`research/visual_selection_experiment.py`, `research/results/visual_selection_pilot.json`) remain
on disk **for provenance only**. No number from them enters Paper 2.

**PROVENANCE CLEAN = YES.**
