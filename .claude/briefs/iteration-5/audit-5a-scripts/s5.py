"""Scratch, SYNTHETIC BARS ONLY: TRUNC-0 under the two comparison conventions, and the negation asymmetry."""
import sys
import numpy as np
src = open(sys.argv[1], encoding="utf-8").read().split("leaks = adv.generate")[0]
exec(src)
leaks = adv.generate(4000, 424242)
single = [l for l in leaks if l.expr.binary and not isinstance(l.expr, adv.Logic)]
tb0 = B["TRUNC0"]
f_any = t_any = neg_diff_trunc = neg_diff_fi = const0 = const1 = 0
per_f = per_t = 0.0
for l in single:
    j = l.reach()[1]
    x = np.asarray(l.expr.evaluate(h1.view), dtype=bool)[:C]
    live = np.zeros((C, adv.COMPARED), bool); live[:, adv.COMPARED - j:] = True
    m = live & h1.scored
    cf = (x & m).any(axis=1)      # missing comparison counts as false: flagged where the original is 1
    ct = (~x & m).any(axis=1)     # missing comparison counts as true (or the leak is written negated): flagged where the original is 0
    f_any += cf.any(); t_any += ct.any(); per_f += cf.mean(); per_t += ct.mean()
    neg_diff_trunc += cf.any() != ct.any()
    allrows = x[h1.scored]
    const0 += (not allrows.any()); const1 += bool(allrows.all())
n = len(single)
print("single binary leaks:", n)
print("TRUNC-0 any-cut: missing-is-false", round(f_any / n, 4), "| missing-is-true", round(t_any / n, 4), "| missing-propagates 1.0")
print("TRUNC-0 per-cut: missing-is-false", round(per_f / n, 4), "| missing-is-true", round(per_t / n, 4), "| missing-propagates 1.0")
print("any-cut verdict differs between a leak and its negation:", round(neg_diff_trunc / n, 4), "(FI, TWO-RUN, SHUFFLE: 0 by construction, |1-a - (1-b)| = |a-b|)")
print("constant at the compared rows: value 0:", const0, " value 1:", const1)
