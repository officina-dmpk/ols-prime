"""Audit phase 2a, A7b: detectors.py:1208 on synthetic bars without degradation, where undefined reads are rare: leaks
whose control can be flagged at some cut of the FI bench but at none of the 16 cuts of H1 are searched first, then
process_leak must count them as "cannot be flagged". Development seed; no real bar; the source is not changed.

Run from python/:  python ../.claude/briefs/iteration-5/audit-2a-scripts/a7b_canflag_probe.py [N]
"""
import sys

from olsprime.bench import adversary as adv
from olsprime.bench import detectors as det

n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
cfg = det.DetectorConfig(population_seed=51118, two_run_seed=51119)
b = det.build_benches(det.synthetic_pairs(), cfg)
h1 = b.rows("h1")
found = []
for leak in adv.generate(n, seed=51118):
    if det.predicted_unit(leak) is None:
        continue
    at_h1, anywhere = det.control_can_flag(leak, b.fi, h1), det.control_can_flag(leak, b.fi, None)
    if anywhere and not at_h1:
        found.append(leak)
print("leaks whose control can be flagged under FI at some cut but at none of the 16:", len(found), "of", n)
wrong = 0
for leak in found[:12]:
    code = det.process_leak(leak, b).counts.get("controls-can-flag:FP1:FI", 0)
    wrong += code != 0
    print("  leak", leak.id, "| the count of the code:", code, "(0 expected)")
print("leaks counted as able to flag though no cut of H1 allows it:", wrong)
