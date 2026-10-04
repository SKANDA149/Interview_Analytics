# IEEE Readiness After Attempted Replication

Written after Experiment 2 stopped at its suitability gate. See
`results/sample_mp4/SECOND_RECORDING_RECALIBRATION.md` for the screen that produced the stop.
Recording 1's pilot, audit and manual validation are unchanged.

## What the attempted replication actually established

The replication was not run, so nothing was learned about whether Recording 1's trade-off
generalises. What *was* learned is about the corpus, not the phenomenon:

1. The local project data contains exactly **one** interview recording suitable for this
   experiment's design — the one already used. The only other distinct recording
   (`sample.mp4`) is an active-speaker-switched multi-party call with a fully saturated
   face-visibility signal (545/545 sparse probes face-present, 0 transitions).
2. The experiment's design has a **previously undocumented scope condition**: it requires a
   recording in which candidate visibility is spatially stable *and* causally independent of
   speech. Recording 1 satisfies this because its candidate appears in a fixed self-view
   thumbnail whose occupancy is driven by where the candidate is sitting, not by who is talking.
   Active-speaker-switched recordings — a very common conferencing mode — violate both conditions
   at once.

Point 2 is worth carrying into the paper regardless of whether a replication ever happens. It
sharpens the contribution's stated applicability from the vague "interview recordings" to the
specific "recordings with a persistent, spatially fixed candidate view," and it explains *why*
that restriction exists rather than just asserting it.

## Effect on readiness

Unchanged from the pre-replication assessment. The single-recording limitation that capped the
general-conference score is still in place, because no second recording was run.

| Target | Score | Change |
|---|---|---|
| Workshop / case-study paper | **7/10** | unchanged |
| General IEEE conference paper | **4/10** | unchanged |

The failed screen neither strengthens nor weakens the existing evidence. It does slightly improve
the *framing* available to the paper (the scope condition above is a real, now-documented insight),
while confirming that closing the n=1 gap requires acquiring new data, not re-analysing what is
already on disk.

## Options, with honest costs

- **Draft the scoped case-study paper now.** The evidence package (pilot + independent audit +
  blind manual validation) is complete and internally consistent at this tier. The n=1 scope and
  the newly-identified layout precondition both go in the limitations section, stated plainly.
- **Acquire one suitable second recording, then re-run Experiment 2.** This requires user
  approval to source new data, and needs the device workspace restored (or an explicit decision to
  accept that Recording 2's runtime metrics would come from different hardware than Recording 1's,
  making only the deterministic metrics cross-comparable). This is the only path that materially
  moves the general-conference score.
- **Do nothing further on replication.** Defensible, but leaves the general-conference ambition
  permanently out of reach for this study.

No recommendation is being made here beyond what the prior assessment already concluded: the
evidence supports a scoped case-study paper now, and a general-conference claim requires data that
does not currently exist locally.
