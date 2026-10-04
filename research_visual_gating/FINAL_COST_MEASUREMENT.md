# Final Cost-Measurement Decision — Paper 2

## Pilot machine availability: UNAVAILABLE (checked, not assumed)

A direct execution attempt was made this session. The device Linux workspace returned:

```
sandbox-helper: no Plan9 drive shares mounted under /mnt/.virtiofs-root/shared
[mnt/interview_visual failed to mount and cannot be reached from this shell]
A Windows update released September 8 prevents Claude's workspace from reaching your files.
```

File staging and committing still work; **command execution on the pilot machine does not**. The
micro-benchmark therefore **cannot** be re-run on the machine that produced the pilot's
`wall_time_s`, `cpu_seconds` and peak-RSS figures.

**No pilot-hardware split has been produced, and none is fabricated below.**

## What we actually have

| Measurement | Value | Where measured | Status |
|---|---|---|---|
| Decode / frame acquisition share | 81.6 % | Analysis container | **Auxiliary, not pilot hardware** |
| YuNet inference share | 18.4 % | Analysis container | **Auxiliary, not pilot hardware** |
| Per detector call | 2.098 ms | Analysis container | **Auxiliary, not pilot hardware** |
| Theoretical max total saving at 32.35 % skip | ≈ 6 % | Derived from the above | **Auxiliary** |
| Detector invocations per condition | 7642 / 5170 / 6315 / 6815 / 7221 | Frozen `runs.jsonl` | **Exact, hardware-independent** |
| Skip percentages | 32.35 / 17.36 / 10.82 / 5.51 % | Frozen `runs.jsonl` | **Exact, hardware-independent** |
| Wall-clock / CPU / peak RSS per condition | as reported | **Pilot machine** | **Valid, but aggregate only** |

The benchmark used the same video, the same YuNet model file, the same ROI (1075, 560, 205×160),
the same confidence threshold (0.6), the same 5-FPS grid and the same sequential-decode strategy.
Only the **hardware and OS** differ. That is enough to preserve the *ratio's plausibility* and
nowhere near enough to license quoting it as a property of the pilot system.

## Decision

**The decode/detect split is demoted from a result to a bounded auxiliary observation, and the
paper's cost claim is carried entirely by detector invocations, which are exact.**

Rationale: the paper's cost axis must not rest on a number measured on different hardware than
every other timing figure in the study. Detector invocations are deterministic, hardware-free, and
already sufficient to support the paper's actual argument — that gating reduces *detector work*,
not *pipeline runtime*.

## Exact wording permitted in the manuscript

**ALLOWED — primary cost claim (exact, frozen data):**

> VAD gating reduces YuNet invocations by 32.35 % at zero padding (5,170 of 7,642 grid frames
> processed), and by 17.36 %, 10.82 % and 5.51 % at 250 ms, 500 ms and 1000 ms padding
> respectively. Matched uniform and random controls process identical frame counts by construction.

**ALLOWED — the runtime caveat (supported by pilot-machine data):**

> Reduced detector invocations did not translate into proportional runtime reduction. The pipeline
> decodes the recording sequentially in full under every condition, so decode cost is invariant to
> gating. Measured wall-clock differences between strategies at identical frame budgets were of
> the same order as the differences between strategies (e.g. 48.45 s and 51.17 s for matched
> uniform and matched random at 5,170 frames), indicating that run-to-run variation, not sampling
> policy, dominates the wall-clock measurement at this scale.

**ALLOWED — the auxiliary split, only with the hardware caveat attached:**

> An auxiliary micro-benchmark on separate hardware, using the same video, model, ROI and grid,
> attributed approximately 82 % of processing time to decoding and 18 % to detector inference
> (≈2.1 ms per call). Because this measurement was not taken on the machine used for the reported
> runtimes, it is reported as an order-of-magnitude indication of where time is spent rather than
> as a measurement of the evaluated system, and no runtime-saving figure is derived from it in the
> results.

**ALLOWED — the qualitative systems conclusion (this is the defensible version of the finding):**

> In a pipeline where decoding is sequential and unavoidable, the addressable fraction of runtime
> is bounded by the detector's share of total processing. Selective inference reduces detector
> work; it does not reduce decode work. Practitioners should therefore size expectations against
> detector cost specifically, not against total pipeline time.

## Forbidden wording

- ❌ "Decode accounts for 81.6 % of our pipeline's runtime." — Not measured on the pilot system.
- ❌ "The maximum achievable saving is 6 %." — Derived from the auxiliary split; stating it as a
  property of this system launders unverified hardware into a headline number.
- ❌ "VAD gating reduces runtime by 32 %." — Categorically false; forbidden throughout.
- ❌ "VAD gating reduces runtime by 11.7 %" (from A = 52.35 s vs B = 46.24 s) — this difference is
  not separable from run-to-run noise, as the equal-budget control spread shows.
- ❌ Any per-call millisecond figure presented as a property of the evaluated system.
- ❌ Any speedup claim derived by multiplying a skip percentage by a detector share.

## If the pilot machine becomes available

Re-run `decode_detect_split.py` unchanged on the pilot machine. If it returns a materially similar
ratio, the auxiliary paragraph may be **promoted** to a measured result and the ≈6 % ceiling may
then be stated. Until then the wording above stands. This is a **presentation upgrade, not a
blocking dependency**: the paper is complete and defensible with the invocation-based cost claim
alone.
