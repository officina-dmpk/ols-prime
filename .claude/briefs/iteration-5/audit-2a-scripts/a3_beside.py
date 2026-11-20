"""Audit phase 2a, A3: numbers beside H15 that the run does not write (mine only): the equal-run-count pairs with
FI /3 alone, the label of every cut-date subset, the gap by family and by constancy. Reads verdicts.jsonl only.

Run:  python a3_beside.py RUN_FOLDER
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

here = Path(__file__).resolve().parent
sys.argv = [sys.argv[0], sys.argv[1], str(Path(sys.argv[1]) / ".." / ".." / ".claude" / "briefs" / "iteration-5" / "audit-2a-scripts" / "a3-scratch.tsv")]
spec = importlib.util.spec_from_file_location("a1", here / "a1_recompute.py")
a1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a1)  # runs A1 again on the folder; its table goes to a3-scratch.tsv
ANY, V, const, fam, n = a1.ANY, a1.V, a1.const, a1.fam, a1.n


def cell(x, y):
    t = a1.table(x, y)
    c = a1.newcombe(**t)
    return t, round(100 * c["difference"], 3), [round(100 * v, 3) for v in c["ci95"]]


print("-- one run per cut against TRUNC-0 (x minus TRUNC-0, points)")
for x in ("FI x3", "FI /3", "TWO-RUN s0.1 r1", "SHUFFLE k1", "FI"):
    print("  ", x, cell(ANY[x], ANY["TRUNC-0"]))
print("-- TRUNC-0 minus FI by denominator and convention (points)")
for name, m in (("all", np.ones(n, bool)), ("not constant", ~const), ("constant", const)):
    for conv in "GMP":
        print("  ", name, conv, cell(ANY[f"TRUNC-0/{conv}"][m], ANY["FI"][m]))
print("-- TRUNC-0 minus FI by family, convention G, all leaks")
for f in sorted(set(fam)):
    print("  ", f, int((fam == f).sum()), cell(ANY["TRUNC-0"][fam == f], ANY["FI"][fam == f]))
print("-- TRUNC-1/G against FI and against TRUNC-0")
print("  ", cell(ANY["TRUNC-1/G"], ANY["FI"]), cell(ANY["TRUNC-1/G"], ANY["TRUNC-0"]))
print("-- long schedule, all 64 dates: TRUNC-0/G minus FI")
print("  ", cell(ANY["TRUNC-0/G@long"], ANY["FI@long"]))

# every subset of the registered cut-date bootstrap, with the labels of H15 read on it
cfg = a1.cfg
rng = np.random.default_rng(cfg["bootstrap_seed"])
labels = {}
for _ in range(cfg["bootstrap_subsets"]):
    cols = np.isin(a1.dates, rng.choice(a1.uniq, size=cfg["bootstrap_dates"], replace=False))
    t = a1.table(V["TRUNC-0/G@long"][:, cols].any(axis=1), V["FI@long"][:, cols].any(axis=1))
    c = a1.newcombe(**t)
    lo, hi = 100 * c["ci95"][0], 100 * c["ci95"][1]
    sign = "above FI" if lo > 0 else "below FI" if hi < 0 else "not separated"
    margin = "within 1 point" if lo > -1 else "by more than 1 point" if hi < -1 else "not resolved"
    labels[(sign, margin)] = labels.get((sign, margin), 0) + 1
print("-- labels of H15 on each of the", cfg["bootstrap_subsets"], "registered subsets:", labels)
# each single long date (both pairs): the difference at 2 cuts
single = [100 * (V["TRUNC-0/G@long"][:, a1.dates == d].any(axis=1).mean() - V["FI@long"][:, a1.dates == d].any(axis=1).mean()) for d in a1.uniq]
print("-- single dates (2 cuts): min, median, max of the difference:", round(min(single), 2), round(float(np.median(single)), 2), round(max(single), 2),
      "| dates with a positive difference:", int(sum(s > 0 for s in single)), "of", len(single))
h1 = a1.header["cuts"]["h1"]
for d in sorted({c["open_time"][:10] for c in h1}):
    cols = np.array([c["open_time"][:10] == d for c in h1])
    print("   H1 date", d, round(100 * (V["TRUNC-0"][:, cols].any(axis=1).mean() - V["FI"][:, cols].any(axis=1).mean()), 2))
