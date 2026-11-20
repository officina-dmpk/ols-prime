"""Scratch, SYNTHETIC BARS ONLY: the mirror twin (the comparison operator flipped), per detector."""
import sys
from dataclasses import replace as dc_replace
from collections import Counter
import numpy as np
src = open(sys.argv[1], encoding="utf-8").read().split("leaks = adv.generate")[0]
exec(src)
leaks = [l for l in adv.generate(4000, 424242) if isinstance(l.expr, adv.Cmp)]
print("single comparisons:", len(leaks))
for name, bench in B.items():
    diff_any = diff_cut = 0; q = Counter()
    for l in leaks:
        m = dc_replace(l, expr=dc_replace(l.expr, op="<" if l.expr.op == ">" else ">"))
        a, b = eval_rule(l, bench), eval_rule(m, bench)
        diff_cut += (a != b).any(); d = a.any() != b.any(); diff_any += d
        if (a != b).any():
            q[l.tag["quantity"]] += 1
    print(f"  {name:9s} any-cut verdict differs from the mirror: {diff_any} ({diff_any/len(leaks):.4f}) | differs at some cut: {diff_cut} | by quantity: {dict(q.most_common(3))}")
# and the negated OUTPUT: identical verdicts for every detector (|(1-a)-(1-b)| = |a-b|), TRUNC included
neg_diff = 0
for l in leaks[:1500]:
    x = np.asarray(l.expr.evaluate(B["TRUNC0"].view), dtype=np.float64)
    c = B["TRUNC0"].n_cuts
    a, b = x[:c], x[c:]
    f1 = ((np.abs(a - b) > 1e-9) & B["TRUNC0"].scored).any(axis=1)
    f2 = ((np.abs((1 - a) - (1 - b)) > 1e-9) & B["TRUNC0"].scored).any(axis=1)
    neg_diff += not np.array_equal(f1, f2)
print("negated output under TRUNC0: verdict differs for", neg_diff, "of 1500 (the output negation changes nothing)")
