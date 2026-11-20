"""Scratch: structure of the generator's population (no data read). Neutral seed 424242, h1-bands placement."""
from collections import Counter
import numpy as np
from olsprime.bench import adversary as adv

N, SEED = 20000, 424242
leaks = adv.generate(N, SEED)

def nodes(e):
    out = [e]
    for name in ("lhs", "rhs", "a", "b"):
        if hasattr(e, name) and not isinstance(getattr(e, name), (int, float, str)):
            out += nodes(getattr(e, name))
    return out

def fut_value_nodes(e):
    return [x for x in nodes(e) if isinstance(x, (adv.At, adv.Agg)) and max(x.offsets()) >= 1]

reach = np.array([l.reach()[1] for l in leaks])
fam = np.array([l.family for l in leaks])
out = np.array([l.output for l in leaks])
des = np.array([l.tag["designed"] for l in leaks])
print("designed:", {k: round(v / N, 4) for k, v in Counter(des).items()})
print("output:", {k: round(v / N, 4) for k, v in Counter(out).items()})
print("max future offset == 1 (TRUNC-1 structurally blind):", round((reach == 1).mean(), 4))
for f in adv.FAMILIES:
    m = fam == f
    print(f"  {f:13s} n={m.sum():5d} reach1={np.mean(reach[m]==1):.3f} designed_yes={np.mean(des[m]=='yes'):.3f}")
print("reach distribution:", {int(k): round(v / N, 4) for k, v in sorted(Counter(reach.tolist()).items())})
# continuous value somewhere (output can turn NaN under a missing read)
def has_cont(e):
    return any(isinstance(x, (adv.LogRatio, adv.Rel, adv.Raw)) for x in nodes(e))
cont = np.array([has_cont(l.expr) for l in leaks])
print("leaks whose output can turn missing (a continuous node):", round(cont.mean(), 4), "| exp_return output:", round((out == 'exp_return').mean(), 4))
# cancelled controls: leaks with an At/Agg future value node
fv = np.array([len(fut_value_nodes(l.expr)) for l in leaks])
print("leaks with >=1 future At/Agg node (FP1/FP2 constructible):", round((fv >= 1).mean(), 4), "| with >=2 such nodes (which v? ambiguous):", round((fv >= 2).mean(), 4))
print("  none, by family:", dict(Counter(fam[fv == 0])))
# cells with SMALL_BODY
cells = [l for l in leaks if any(isinstance(x, adv.Cell) for x in nodes(l.expr))]
sb = sum(any(isinstance(x, adv.Cell) and x.c == adv.SMALL_BODY for x in nodes(l.expr)) for l in cells)
print("leaks with a Cell:", len(cells) / N, "of which boundary == SMALL_BODY:", sb / max(1, len(cells)))
# thresholds on the six quantile quantities, taker shares, wick ratio
thr = Counter()
for l in leaks:
    for x in nodes(l.expr):
        if isinstance(x, adv.Cmp) and isinstance(x.rhs, adv.Const) and isinstance(x.lhs, adv.At):
            thr[x.lhs.q] += 1
tot = sum(thr.values())
print("threshold comparisons (count, per 10,000 leaks):", {k: round(v * 10000 / N) for k, v in thr.most_common()})
six = sum(v for k, v in thr.items() if k in adv.BANDS)
print("  on the six band quantities:", round(six / tot, 3), "| taker shares:", round(sum(v for k, v in thr.items() if k in adv.SHARES) / tot, 3), "| wick_ratio:", round(thr['wick_ratio'] / tot, 3))
# leaks touching wick_ratio at a future offset
wr = sum(any(isinstance(x, adv.At) and x.q == 'wick_ratio' and x.o >= 1 for x in nodes(l.expr)) for l in leaks)
print("leaks reading a future wick_ratio:", wr / N)
# margin 1 share among comparisons with a margin
ms = [x.margin for l in leaks for x in nodes(l.expr) if isinstance(x, adv.Cmp) and not isinstance(x.rhs, adv.Const)]
print("non-threshold comparisons with margin == 1:", round(np.mean(np.array(ms) == 1.0), 3))
