"""Audit 2b, B4: the secondary TWO-RUN arm beside the primary one (mine only, not registered).

Usage: python b4_two_run_secondary.py <run folder> <scratch.tsv>

Reads verdicts.jsonl (and detectors.json) of one detector run through the reader of audit 2a
(audit-2a-scripts/a1_recompute.py, which imports nothing from olsprime), as A3 does. No bar. A1
replays the bootstrap seed of the header on the stored verdicts; B4 draws nothing. Prints the any-cut shares of TWO-RUN by scale and run count, and the paired cells
against FI and TRUNC-0 at two runs per cut (one for TRUNC-0), in points, Newcombe method 10.
"""
import importlib.util
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
a1_path = here.parent / "audit-2a-scripts" / "a1_recompute.py"
spec = importlib.util.spec_from_file_location("a1", a1_path)
a1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a1)  # runs A1 on the folder; its table goes to the scratch path of argv[2]
ANY = a1.ANY


def cell(x, y):
    t = a1.table(x, y)
    c = a1.newcombe(**t)
    return t, round(100 * c["difference"], 2), [round(100 * v, 2) for v in c["ci95"]]


print("leaks:", a1.n)
for k in ("FI", "FI x3", "FI /3", "TRUNC-0", "SHUFFLE k1", "SHUFFLE k2", "SHUFFLE k8", "TWO-RUN s0.1 r1",
          "TWO-RUN s0.1 r2", "TWO-RUN s0.1 r8", "TWO-RUN s1 r1", "TWO-RUN s1 r2", "TWO-RUN s1 r8"):
    lo, hi = a1.wilson(int(ANY[k].sum()), a1.n)
    print(f"  {k:18s} {int(ANY[k].sum()):6d}  {100 * ANY[k].mean():6.2f} [{100 * lo:.2f}, {100 * hi:.2f}]")
print("-- pairs, first minus second, points [Newcombe 95 %], table a both, b first only, c second only, d neither")
for x, y in (("FI", "TWO-RUN s0.1 r2"), ("FI", "TWO-RUN s1 r2"), ("FI", "TWO-RUN s1 r8"), ("FI", "TWO-RUN s0.1 r8"),
             ("TWO-RUN s1 r2", "TRUNC-0"), ("TWO-RUN s1 r1", "TRUNC-0"), ("FI x3", "TWO-RUN s1 r1"),
             ("FI /3", "TWO-RUN s1 r1"), ("TWO-RUN s1 r2", "SHUFFLE k2")):
    print("  ", x, "-", y, cell(ANY[x], ANY[y]))
