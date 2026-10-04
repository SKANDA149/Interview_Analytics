"""Plain assert-based tests for padding.py, matching this repo's existing
test style (interview_pipeline/tests/test_visual_presence.py)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from research_visual_gating.padding import dilate_and_merge, Interval, total_duration, is_within_any_interval
from research_visual_gating.vad import SpeechInterval

passed = 0
failed = 0

def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}")

print("test_padding.py")

# Zero padding: intervals unchanged (just clamped/converted)
ivs = [SpeechInterval(start=5.0, end=10.0)]
out = dilate_and_merge(ivs, 0, 100.0)
check("zero padding leaves bounds unchanged", out == [Interval(start=5.0, end=10.0)])

# Symmetric expansion
out = dilate_and_merge([SpeechInterval(start=5.0, end=10.0)], 250, 100.0)
check("250ms padding expands both sides", out[0].start == 4.75 and out[0].end == 10.25)

# Clamping at video start
out = dilate_and_merge([SpeechInterval(start=0.1, end=1.0)], 500, 100.0)
check("padding clamps at t=0", out[0].start == 0.0)

# Clamping at video end
out = dilate_and_merge([SpeechInterval(start=99.0, end=99.9)], 500, 100.0)
check("padding clamps at video duration", out[0].end == 100.0)

# Merging: two intervals that become adjacent/overlapping after padding
ivs = [SpeechInterval(start=1.0, end=2.0), SpeechInterval(start=2.6, end=3.0)]
out = dilate_and_merge(ivs, 250, 100.0)  # 2.0+0.25=2.25, 2.6-0.25=2.35 -> no touch
check("250ms padding: gap 0.6s stays separate", len(out) == 2)

out = dilate_and_merge(ivs, 500, 100.0)  # 2.0+0.5=2.5, 2.6-0.5=2.1 -> overlap -> merge
check("500ms padding: gap 0.6s now merges", len(out) == 1 and out[0].start == 0.5 and out[0].end == 3.5)

# Monotonicity of skip-pct proxy: total duration should be non-decreasing with padding
ivs = [SpeechInterval(start=10.0, end=12.0)]
durs = [total_duration(dilate_and_merge(ivs, p, 1000.0)) for p in [0, 250, 500, 1000]]
check("total padded duration is monotonically non-decreasing in padding_ms",
      all(durs[i] <= durs[i+1] for i in range(len(durs)-1)))

# is_within_any_interval inclusive on both ends
merged = [Interval(start=5.0, end=10.0)]
check("boundary start is 'within'", is_within_any_interval(5.0, merged))
check("boundary end is 'within'", is_within_any_interval(10.0, merged))
check("just outside is not 'within'", not is_within_any_interval(10.001, merged))

print(f"padding.py: {passed} passed, {failed} failed")
if failed:
    sys.exit(1)
