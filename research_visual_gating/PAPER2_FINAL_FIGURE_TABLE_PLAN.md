# Paper 2 — Final Figure and Table Plan

Principle applied: **every artefact must answer a question no other artefact answers.** Candidates
that merely restate a table were cut. Result: **4 main figures, 4 main tables**, 2 figures and 1
table demoted to supplementary.

---

## Main-paper figures

### Figure 1 — Pipeline and sampling schematic *(MAIN)*
- **Why needed:** the reader cannot evaluate "budget-matched" without seeing that all four
  policies draw from one shared grid, and that decode happens regardless of selection. This single
  point carries both the fairness argument and the cost ceiling.
- **Generated from:** no data — schematic. Must show: audio → Silero VAD → interval dilation;
  video → sequential decode (marked *always full*) → 5-FPS grid of 7,642; four selectors drawing
  subsets; ROI crop (1075, 560, 205×160) → YuNet.
- **Placement:** MAIN. This is the most load-bearing figure in the paper.

### Figure 2 — Interval-existence recall vs processed-frame budget *(MAIN)*
- **Why needed:** the primary result.
- **Generated from:** budgets 5170/6315/6815/7221; VAD 0.8345/0.9034/0.9379/0.9793; uniform
  0.9517/0.9655/0.9793/1.0000; random 0.9241/0.9517/0.9655/0.9862; anchor at (7642, 1.0000).
- **Constraints:** three lines, markers at the four measured budgets. **No error bars** (metrics
  are deterministic). If the y-axis is restricted, state the range in the caption.
- **Placement:** MAIN.

### Figure 3 — Temporal-coverage recall vs processed-frame budget *(MAIN)*
- **Why needed:** the dissociation only exists if both metrics are shown. Cutting this would
  reduce the paper to a one-sided negative result and misrepresent the finding.
- **Generated from:** VAD 0.6925/0.8417/0.9045/0.9541; uniform 0.6762/0.8262/0.8914/0.9461;
  random 0.6769/0.8276/0.8919/0.9446.
- **Constraints:** same axes and styling as Figure 2 so the reversal is visually immediate. The
  caption must state the margins are small (≈0.016 at the tightest budget).
- **Placement:** MAIN. **Best presented side-by-side with Figure 2 as a two-panel figure** — the
  dissociation is the point, and separating the panels weakens it.

### Figure 4 — Missed-interval composition by policy *(MAIN)*
- **Why needed:** the failure-mode asymmetry is the paper's most distinctive empirical finding and
  is invisible in the recall numbers alone.
- **Generated from:** at each budget, missed counts split single-frame vs multi-frame —
  VAD 24 (9/15), 14 (7/7), 9 (4/5), 3 (1/2); uniform 7 (7/0), 5 (5/0), 3 (3/0), 0; random
  11 (9/2), 7 (5/2), 5 (4/1), 2 (2/0). Missed spans: VAD max 2.2 s; uniform max 0.2 s.
- **Constraints:** stacked bars per policy per budget, single-frame vs multi-frame. The
  "uniform column is entirely single-frame at every budget" pattern must be legible at a glance.
- **Placement:** MAIN.

---

## Supplementary figures

### Figure S1 — Speech–visibility coupling *(SUPPLEMENTARY)*
- **Why demoted:** the coupling result is three numbers (0.9185 / 0.9402 / 0.8730 and I/H = 2.20 %).
  A figure adds no information a sentence does not carry, and a bar chart of three near-identical
  bars risks *visually overstating* a 6.7-point spread. The number belongs in the text and Table 3;
  the figure belongs in supplementary for readers who want the distribution.
- **Generated from:** P(visible)=0.9185, P(visible|VAD-active)=0.9402, P(visible|VAD-silent)=0.8730,
  H=0.40752 bits, I=0.00896 bits.
- **Constraint:** y-axis must start at 0, not 0.85, or it manufactures an apparent effect.

### Figure S2 — Cost decomposition *(SUPPLEMENTARY)*
- **Why demoted:** the decode/detect split was measured on **different hardware** than the reported
  runtimes. Putting it in the main paper as a figure gives it a prominence the measurement does not
  earn, and invites exactly the speedup misreading the paper must avoid. Table 4 carries the exact,
  hardware-independent invocation counts in the main text; this figure is context only.
- **Generated from:** decode 81.6 % / detect 18.4 %, 2.098 ms per call.
- **Constraint:** caption must open with the hardware caveat, and the figure must carry **no**
  derived saving percentage.

---

## Main-paper tables

### Table 1 — Experimental configuration *(MAIN)*
- **Why:** reproducibility; every frozen parameter in one place.
- **Contents:** recording (1528.267 s, 1280×720, h264 30 fps); ROI (1075, 560, 205×160); grid
  (5 FPS, 7,642 frames); Silero VAD (0.5 / 250 ms / 100 ms / 0 ms); YuNet
  (`face_detection_yunet_2023mar.onnx`, 0.6); padding values; random seed 20260913;
  `GAP_MERGE_SECONDS` 0.200; reference 145 intervals (28 single / 117 multi).

### Table 2 — Conditions and frame budgets *(MAIN)*
- **Why:** demonstrates *exact* budget matching, which is the design's whole validity claim.
- **Contents:** 13 conditions; processed frames 7642/5170/6315/6815/7221; % of grid; skip %; the
  F_*/R_* rows showing identical counts to their VAD counterpart.

### Table 3 — Retention results *(MAIN)*
- **Why:** the full result set; supports Figures 2–4.
- **Contents:** per budget per policy — existence recall (all 145), existence recall (multi-frame
  117), coverage recall, missed count, % of misses that are multi-frame. Coupling row appended as a
  footnote or a small adjacent panel.

### Table 4 — Cost accounting *(MAIN)*
- **Why:** the honest cost statement.
- **Contents:** detector invocations, skipped invocations, % skipped, wall-clock mean, CPU-seconds
  mean, peak RSS per condition. **Header must state invocations are the cost unit.** Peak RSS may be
  collapsed to one line ("≈107 MB, condition-invariant, <1 % spread") to save space.

---

## Supplementary table

### Table S1 — Literature comparison *(SUPPLEMENTARY, with a 3-row summary in MAIN)*
- **Why split:** the full ten-column novelty matrix is too wide for a two-column IEEE layout, but
  the Jalayer et al. comparison is too important to hide. Put a compact three-row version in
  Related Work (ours / Jalayer et al. / Listen to Look, columns: gate, workload, budget-matched,
  CPU-GPU, coverage metric) and the full matrix in supplementary.

---

## Artefacts explicitly NOT included

| Candidate | Why cut |
|---|---|
| Wall-clock vs recall scatter (old Figure 3) | Invites reading run-to-run noise as a compute-retention frontier. The noise demonstration belongs in one sentence, not a figure. |
| Padding trade-off figure (old Figure 4) | Padding and budget are perfectly confounded; a padding-on-the-x-axis figure would imply a separable padding effect the design cannot support. Table 2 carries the same numbers safely. |
| AUC / single-number retention-efficiency summary | Collapses the dissociation into one score — the exact error the paper's secondary contribution warns against. |
| Per-frame recall figure | A restatement of skip percentage; the production code documents this. |
| Manual-validation figure | 133 judgments summarise in two sentences; a figure would over-weight a supporting contribution. |

**Totals: 4 main figures (one of which is a two-panel), 4 main tables, 2 supplementary figures,
1 supplementary table.** Comfortably within a 6–8 page IEEE limit.
