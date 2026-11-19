"""Audit 5b, X9: conventions G, M, P written again from PROTOCOL §2 ("Three conventions"), against adv.evaluate_under,
on the truncation bench (degraded synthetic bars), development population 51118 (quantile). No data read."""
import sys
import numpy as np
from olsprime.bench import adversary as adv, detectors as det

TABLE, N = sys.argv[1], int(sys.argv[2])
cfg = det.DetectorConfig(population_seed=51118, two_run_seed=51119, placement="quantile", n=N, two_run_runs=1, sigmas=(0.1,))
b = det.build_benches(det.synthetic_pairs(degrade=True), cfg)
view = b.trunc.view
shape = (b.trunc.n_cuts * 2, adv.COMPARED)

def val(e):  # value nodes: floats, NaN where missing
    if isinstance(e, adv.Const): return np.full(shape, e.c)
    if isinstance(e, adv.At): return np.array(view.at(e.q, e.o), float)
    if isinstance(e, adv.Agg):
        st = np.stack([view.at(e.q, o) for o in range(e.lo, e.hi + 1)])
        return {"max": np.max, "min": np.min, "mean": np.mean, "sum": np.sum}[e.op](st, axis=0)
    if isinstance(e, adv.TrailMean): return np.mean(np.stack([view.at(e.q, -o) for o in range(e.w)]), axis=0)
    raise TypeError(type(e))

def atom(truth, missing, conv):  # an atomic predicate: (bool where defined), missing mask -> tri-state float
    out = np.where(truth, 1.0, 0.0)
    if conv == "G": return np.where(missing, 0.0, out)
    if conv == "M": return np.where(missing, 1.0, out)
    return np.where(missing, np.nan, out)

def tri(e, conv):  # binary nodes: 1.0, 0.0 or NaN (P only)
    with np.errstate(invalid="ignore"):
        if isinstance(e, adv.Cmp):
            a, c = val(e.lhs), val(e.rhs)
            return atom(a > e.margin * c if e.op == ">" else a < e.margin * c, np.isnan(a) | np.isnan(c), conv)
        if isinstance(e, adv.Same):
            x, y = view.at("green", e.o), view.at("green", e.r)
            return atom(x == y, np.isnan(x) | np.isnan(y), conv)
        if isinstance(e, adv.Colour):
            x = view.at(e.colour, e.o)
            return atom(x > 0.5, np.isnan(x), conv)
        if isinstance(e, adv.Pattern):
            body, up, lo = (view.at(q, e.o) for q in ("body", "upper_wick", "lower_wick"))
            long_, short = (lo, up) if e.kind == "hammer" else (up, lo)
            p1 = atom(long_ >= e.a * body, np.isnan(long_) | np.isnan(body), conv)
            p2 = atom(short <= body, np.isnan(short) | np.isnan(body), conv)
            return np.where(np.isnan(p1) | np.isnan(p2), np.nan, ((p1 == 1) & (p2 == 1)).astype(float))
        if isinstance(e, adv.Cell):
            body, col = view.at("body", e.o), view.at(e.colour, e.o)
            p1 = atom(col > 0.5, np.isnan(col), conv)
            p2 = atom(body < e.c if e.size == "small" else body > e.c, np.isnan(body), conv)
            return np.where(np.isnan(p1) | np.isnan(p2), np.nan, ((p1 == 1) & (p2 == 1)).astype(float))
        if isinstance(e, adv.Logic):
            x, y = tri(e.a, conv), tri(e.b, conv)
            f = {"AND": lambda p, q: p & q, "OR": lambda p, q: p | q, "XOR": lambda p, q: p ^ q}[e.op]
            return np.where(np.isnan(x) | np.isnan(y), np.nan, f(x == 1, y == 1).astype(float))
    raise TypeError(type(e))

def cont(e, conv):
    with np.errstate(all="ignore"):
        if isinstance(e, adv.WSum):
            parts = [tri(p, conv) if p.binary else cont(p, conv) for p in (e.a, e.b)]
            return e.w1 * parts[0] + e.w2 * parts[1]
        if isinstance(e, adv.LogRatio):
            x, y = cont(e.a, conv), cont(e.b, conv)
            return np.where((x > 0) & (y > 0), np.log(x / y), np.nan)
        if isinstance(e, adv.Rel):
            return cont(e.a, conv) / cont(e.b, conv) - 1.0
        if isinstance(e, adv.Raw):
            return cont(e.a, conv)
    return val(e)

leaks = adv.generate(N, 51118, placement="quantile", table_path=TABLE)
kinds, bad, cells = {}, 0, 0
for leak in leaks:
    for node in det._walk(leak.expr):
        kinds[type(node[1]).__name__] = kinds.get(type(node[1]).__name__, 0) + 1
    for conv in ("G", "M", "P"):
        got = np.broadcast_to(np.asarray(adv.evaluate_under(leak.expr, view, conv), float), shape)
        want = tri(leak.expr, conv) if leak.expr.binary else cont(leak.expr, conv)
        want = np.where(np.isfinite(want), want, np.nan) if not leak.expr.binary else want
        got = np.where(np.isfinite(got), got, np.nan)
        cells += got.size
        diff = ~((got == want) | (np.isnan(got) & np.isnan(want)))
        if diff.any():
            bad += 1
            if bad <= 5: print("DIFF", leak.id, conv, leak.render(), int(diff.sum()))
print("node kinds:", kinds)
print(f"{N} leaks x 3 conventions, {cells} cells compared, leaks x conventions that differ: {bad}")
