"""Scratch 5a-bis: no bars at all. Neutral seed 424242. Which leaks call _threshold (the only draws the quantile placement changes)?"""
import numpy as np
from collections import Counter
from olsprime.bench import adversary as adv
calls = []
orig = adv._threshold
def spy(rng, q):
    calls.append(q); return orig(rng, q)
adv._threshold = spy
N = 10000
per = Counter(); n_any = 0; banded = 0; pos = Counter(); tags = Counter()
for i in range(N):
    calls.clear()
    l = adv.draw_leak(424242, i)
    if calls:
        n_any += 1
        if any(q in adv.BANDS for q in calls): banded += 1
        for q in calls: per[q] += 1
    pos[l.tag["position"]] += 1
    if l.tag["reference"] == "threshold": tags[(l.tag["position"])] += 1
print("leaks with at least one _threshold call:", n_any, "of", N, "; with a banded one:", banded)
print("calls by quantity:", dict(per))
print("position tag over all leaks:", dict(pos))
print("position tag among reference == threshold:", dict(tags))
# rendering precision: what adversary.json stores
l = next(l for l in adv.generate(300, 424242) if isinstance(l.expr, adv.Cmp) and isinstance(l.expr.rhs, adv.Const))
print("render:", l.render(), "| repr:", repr(l.expr))
import numpy
print("numpy", numpy.__version__)
