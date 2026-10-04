import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from research_visual_gating.frame_grid import build_frame_grid
from research_visual_gating.gating import select_frames_vad_gated, select_frames_matched_uniform
from research_visual_gating.padding import Interval

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

print("test_frame_grid_and_gating.py")

grid = build_frame_grid(10.0, fps=5)
check("grid has expected count (10s @5fps = 51 points incl t=0 and t=10)", len(grid) == 51)
check("grid starts at 0.0", grid[0] == 0.0)
check("grid ends at 10.0", grid[-1] == 10.0)
check("grid spacing is 0.2s", all(round(grid[i+1]-grid[i], 3) == 0.2 for i in range(len(grid)-1)))

# VAD gating: select only indices within intervals
grid2 = build_frame_grid(5.0, fps=5)  # 26 points: 0.0, 0.2, ..., 5.0
ivs = [Interval(start=1.0, end=2.0)]
idx = select_frames_vad_gated(grid2, ivs)
selected_ts = [grid2[i] for i in idx]
check("VAD-gated selects exactly the in-interval timestamps",
      selected_ts == [1.0, 1.2, 1.4, 1.6, 1.8, 2.0])

# empty interval list -> no frames selected
check("no speech intervals -> zero frames selected", select_frames_vad_gated(grid2, []) == [])

# full-video interval -> all frames selected
idx_all = select_frames_vad_gated(grid2, [Interval(start=0.0, end=5.0)])
check("interval spanning whole video selects all grid points", len(idx_all) == len(grid2))

# Matched uniform sampling: must return exactly target_count indices
grid3 = build_frame_grid(100.0, fps=5)  # 501 points
for target in [10, 50, 100, 250]:
    idx_u = select_frames_matched_uniform(grid3, target)
    check(f"matched uniform target_count={target} returns exactly that many indices",
          len(idx_u) == target)
    check(f"matched uniform target_count={target} indices are unique and sorted",
          idx_u == sorted(set(idx_u)))

# target_count spans full grid width (first/last index used) for a reasonably large count
idx_u = select_frames_matched_uniform(grid3, 100)
check("matched uniform spans from near-start to near-end of grid",
      idx_u[0] <= 5 and idx_u[-1] >= len(grid3) - 6)

# target_count >= grid size -> returns whole grid
idx_full = select_frames_matched_uniform(grid3, len(grid3) + 10)
check("target_count >= grid size returns whole grid", idx_full == list(range(len(grid3))))

# target_count == 0
check("target_count == 0 returns empty", select_frames_matched_uniform(grid3, 0) == [])

print(f"frame_grid+gating: {passed} passed, {failed} failed")
if failed:
    sys.exit(1)
