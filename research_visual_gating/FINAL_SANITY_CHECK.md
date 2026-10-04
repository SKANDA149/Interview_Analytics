# Paper 2 — Final Sanity Check (Adversarial Red Team)

Conducted on the premise instructed: **assume the paper is wrong.** The task was to find the
reasons a skeptical IEEE reviewer would reject it, not to confirm the work.

---

## 1. Independent recomputation from raw data

`redteam_verify.py` recomputed every reported number from `runs.jsonl`,
`reference_frame_results_v1i.json` and `vad_raw_intervals.json` using the **production** selection,
reference-construction and recall functions (imported, never reimplemented), with explicit
arithmetic identity assertions.

| Identity | Result |
|---|---|
| processed + skipped = 7,642 | holds for all conditions |
| visible (7,019) + absent (623) = 7,642 | holds |
| single-frame (28) + multi-frame (117) = 145 | holds |
| hits + misses = 145, recall = hits/145 | holds for all 12 strategy×budget cells |
| matched controls process exactly the gated budget | exact equality, all four |
| manual-validation strata sum (28, 50; 134 rows / 133 unique frames) | holds |
| determinism across 13 conditions × 3 repeats | confirmed |

**Zero discrepancies.** No reported value originated from a report rather than from data.

## 2. Errors found and fixed this pass

**Catch #1 — factual error in interpretation.** Several documents described speech and visual
availability as "independent" or "nearly independent". This is wrong: I = 0.00896 bits is strictly
greater than zero, and P(visible | active) = 0.9402 exceeds P(visible | silent) = 0.8730 by 6.7
points. A reviewer would have caught this immediately, and it would have undermined the paper's own
coupling analysis — if the variables were independent, measuring I would be pointless. Corrected
throughout to **weak coupling**. The title's verb "Inform" is correct precisely because I > 0.

**Catch #2 — live internal contradiction.** `COUPLING_AND_FAILURE_MODES.md` still asserted the
≈6 % saving ceiling as established, contradicting `FINAL_COST_MEASUREMENT.md`, which withdrew that
figure because it derives from a non-pilot-hardware micro-benchmark. Corrected by surgical edit with
a logged "Superseded wording" note. The historical
`PAPER2_FINAL_IEEE_READINESS_AND_GAP_ANALYSIS.md` retains the old wording and was deliberately
**left unmodified as provenance**; it is explicitly superseded.

**Catch #3 — no leakage elsewhere.** All occurrences of "novel", "first", "ground truth", "speedup"
and the 1-FPS figures were located and inspected. Every one sits inside a prohibition or a
definition. No document mixes 1-FPS and 5-FPS quantities as the same measurement.

## 3. The strongest reviewer objections, stated at full force

1. **n = 1.** The entire empirical contribution rests on one recording, and the one attempt at a
   second recording was abandoned at screening. This is not a limitation — it is the paper's
   defining constraint, and no amount of analysis inside the single recording repairs it.
2. **Pre-emption.** arXiv:2608.22359 materially pre-empts the methodological framing. What remains
   is the budget-matched blind-control design and the metric dissociation.
3. **The headline result is negative.** The proposed gate loses to blind uniform sampling on the
   metric most readers will consider primary, and produces no runtime saving.
4. **The reference is not ground truth.** Retention is measured against the detector's own output;
   blind human review could confirm none of the 28 isolated detections either way.
5. **The coverage-recall advantage is small.** ≈0.016 at the tightest budget, narrowing after.
6. **Padding and budget are confounded** by construction, so padding has no separable effect.

None of these is answerable with the data in hand. All six are stated in the paper.

## 4. What survives the objections

- The **budget-matched blind-control design** is sound and is the methodological core. Because the
  controls process exactly the same frames from the same grid, the comparison isolates the value of
  the gating *signal* from the value of processing *fewer frames*. That separation is what most
  informal claims about gating omit.
- The **metric dissociation** is a real, reproducible, exactly-verified observation: two standard
  retention metrics rank the same three policies in opposite directions on identical data. It is
  a genuine caution for anyone reporting a single retention number.
- The **decode-bound cost finding** is architectural, not incidental: when the recording is decoded
  in full, invocation reduction cannot become runtime reduction. This generalises by construction,
  not by induction, and it is the paper's most transferable statement.
- The **coupling measurement procedure** transfers even though its value does not.

## 5. Is the paper honest about what it does not show?

Yes, and the mechanisms are concrete rather than rhetorical: a frozen claim table that marks 15
statements REMOVE; an aggregated prohibition list; a mandatory abstract sentence naming the single
recording within two sentences; a figure audit forbidding error bars and speedup columns; an
explicit hypothesis section; and a pre-emption citation placed in the Introduction rather than
buried.

## 6. Reviewer verdict

A skeptical reviewer would not call this a strong paper. It is a small, negative, single-recording
result with a pre-empted framing. But the question posed is narrower: **is the paper wrong, or
overclaiming?**

# NO — the paper is not wrong and does not overclaim.

Every reported number was independently recomputed and reconciles exactly. The two errors found were
interpretive, were found by this check rather than by a reviewer, and are fixed. The claims that
would have been indefensible have been removed rather than hedged. What remains is a modest,
correctly scoped, honestly negative result.

**The appropriate venue framing is a short/workshop-length contribution or a measurement-and-caution
paper, not a full-length methods paper.** That is a scope judgement, not a defect.

**Red-team status: PASS.**
