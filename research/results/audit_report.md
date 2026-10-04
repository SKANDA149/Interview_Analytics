# Pre-writing audit of experimental results

Audit performed before any paper drafting, to check what was actually
measured rather than what was assumed. Two findings invalidated headline
claims from the first analysis pass; both were fixed or reclassified.

## Verified sound

- The 18 (later 36) aggregated conditions recompute exactly from the raw
  per-seed runs: 0 mismatches, 90/90 (later 180/180) runs present.
- Both operators produce byte-identical output at severity 0, so a shared
  baseline was harmless; baselines are now computed per policy regardless.
- Three consecutive full runs produced identical numbers; the analysis
  script re-run produced a zero-byte diff. No hidden nondeterminism.
- Reference data untouched: `data/diarization/segments.json` mtime predates
  all harness work. `full_transcript.json` is additive, not an overwrite.
- Baseline attribution is clean: only 4 of 2498 words fall outside every
  reference diarization segment.
- Reference diarization covers 813.7s of 1088.7s of audio (74.7%);
  the uncovered remainder is essentially non-speech (see the 4-word figure
  above), but the coverage figure should be stated in the paper.

## FINDING 1 - the missed_speech WPM result was an artifact of the aligner

`missed_speech` deletes candidate segments, leaving words in time ranges
covered by no segment. The aligner's nearest-neighbour fallback reassigned
most of them back to CANDIDATE: at severity 0.50, 835 words (33.4% of the
transcript) had zero overlapping segment and 624 were recovered to
CANDIDATE. The word-count numerator therefore stayed high while the
duration denominator halved, inflating WPM mechanically.

Measured both ways (seed 42):

| condition | fallback WPM | strict WPM |
|---|---|---|
| missed_speech 0.00 | 180.4 | 180.1 |
| missed_speech 0.10 | 197.9 | 180.2 |
| missed_speech 0.25 | 232.3 | 180.6 |
| missed_speech 0.50 | 314.9 | 176.8 |

The original claim ("missed_speech dominates WPM distortion, ~20x steeper
than role_swap") does not survive a change of attribution policy. Across
the full 5-seed grid the distortion slope is +1.3873 (R^2=0.979) under
fallback and -0.0146 (R^2=0.647, i.e. flat) under strict.

Resolution: attribution policy is now an explicit, reported parameter
(`fallback` / `strict`), both are run, and the divergence between them is
reported as the finding rather than one of them being presented as the
result. role_swap is unaffected - it never creates unattributed regions, so
both policies agree to within 0.5%, and every role_swap fluency result is
policy-independent.

## FINDING 2 - the content score was measuring noise, then was found truncated

(a) The ideal answer inherited from `pipeline.py` is about DATA STRUCTURES,
while the recording is a self-introduction and motivation interview. Zero
topical overlap; baseline score 5.73% was the cosine noise floor between
unrelated texts. Replaced with a topic-matched reference answer stated
verbatim in `downstream_metrics.DEFAULT_IDEAL_ANSWER` (written once, not
tuned against the resulting score). Baseline rose to 51.47%.

(b) With real signal present, a second problem surfaced: the score is
frozen at exactly 51.47 (std 0.0000) across five different seeds at four
different severities, despite total candidate word counts varying by
20-100 words. The score changes if and only if the FIRST ~200 words change:

| condition | distinct first-200-word prefixes (5 seeds) | score |
|---|---|---|
| missed_speech 0.05-0.20 | 1 | 51.47 +/- 0.0000 |
| missed_speech 0.25 | 2 | 51.438 +/- 0.0716 |
| missed_speech 0.50 | 3 | 51.296 +/- 0.4411 |
| role_swap 0.05 | 4 | 50.61 +/- 1.7174 |
| role_swap 0.20 / 0.50 | 5 | large variance |

`all-MiniLM-L6-v2` has a 256 word-piece limit and sentence-transformers
truncates silently past it, so the content score evaluates roughly the
first 12% of a 1633-word answer and discards the rest.

CONFIRMED DIRECTLY (not inferred). On the project venv:

    SentenceTransformer('all-MiniLM-L6-v2').max_seq_length  ->  256

So the mechanism is established from the model configuration itself, and
the prefix-correlation table above is independent empirical corroboration
of its downstream effect.

Resolution: the semantic metric is REMOVED from the dose-response results.
The truncation is reported instead as a defect of the pipeline under study.
The correlation table above is the evidence, pinned by
`test_semantic_score_only_reflects_transcript_head`.

## Minor

- `total_long_pauses` has a baseline mean of 0, so its relative distortion
  is undefined and it was silently excluded from all linearity analysis.
  Now reported as absolute counts: role_swap 0 -> 2.0 across severities,
  missed_speech 0 at every severity under both policies. Long-pause
  sensitivity is a role_swap-only phenomenon.
- The `strict/missed_speech` semantic rise (51.47 -> 56.74 at severity
  0.30) is ~1.1 sigma at n=5 and is NOT significant. It must not be
  reported as corruption improving content.
- Filler-count slope is itself policy-sensitive under missed_speech
  (-0.3969 fallback vs -1.0147 strict); role_swap is identical under both.
