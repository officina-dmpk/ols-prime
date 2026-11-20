"""Audit phase 2a, A7: the two other lines of Minor 3 (pass 5b-bis), on synthetic degraded bars, development seeds.

- detectors.py:1172, the read-split row of the primary TWO-RUN arm: it must be the sum over the runs labelled
  sigma 0.1, run 1 and run 2, and strictly below the 8-run row over the leaks tried;
- detectors.py:1208, can_flag: counted over the 16 cuts of H1, not over every cut of the bench.

The source is not changed. Reads no real bar.
Run from python/:  python ../.claude/briefs/iteration-5/audit-2a-scripts/a7_split_canflag_probe.py [N]
"""
import sys

import numpy as np

from olsprime.bench import adversary as adv
from olsprime.bench import detectors as det

n = int(sys.argv[1]) if len(sys.argv) > 1 else 150
cfg = det.DetectorConfig(population_seed=51118, two_run_seed=51119)
b = det.build_benches(det.synthetic_pairs(degrade=True), cfg)
leaks = adv.generate(n, seed=51118)
h1 = b.rows("h1")
runs = list(b.two_run_runs)
print("two_run_runs:", runs[:3], "...", runs[-1], "| H1 rows:", len(h1), "| cuts of the FI bench:", b.fi.n_cuts)
want = [j for j, (s, k) in enumerate(runs) if abs(s - 0.1) < 1e-12 and k in (1, 2)]
eight = [j for j, (s, k) in enumerate(runs) if abs(s - 0.1) < 1e-12]
row_r2 = row_8 = mine_r2 = mine_8 = 0
can = {"h1": 0, "every cut": 0, "code": 0}
for leak in leaks:
    res = det.process_leak(leak, b)
    row_r2 += res.split["TWO-RUN s0.1 r2@h1"][0]
    row_8 += res.split["TWO-RUN s0.1@h1"][0]
    r = det.judge_window(leak, b.two_run)
    mine_r2 += int(r.flags[h1][:, want].sum())
    mine_8 += int(r.flags[h1][:, eight].sum())
    if det.predicted_unit(leak) is not None:
        can["h1"] += det.control_can_flag(leak, b.fi, h1)
        can["every cut"] += det.control_can_flag(leak, b.fi, None)
        can["code"] += res.counts.get("controls-can-flag:FP1:FI", 0)
print("read split, primary arm: code", row_r2, "| runs 1 and 2 of sigma 0.1:", mine_r2, "| 8-run row: code", row_8, "mine", mine_8,
      "| equal:", row_r2 == mine_r2 and row_8 == mine_8, "| strictly below:", row_r2 < row_8)
print("can_flag for FP1 under FI over", n, "leaks: code", can["code"], "| at the 16 cuts:", can["h1"], "| at every cut:", can["every cut"],
      "| code equals the 16-cut count:", can["code"] == can["h1"], "| the two counts differ:", can["h1"] != can["every cut"])
