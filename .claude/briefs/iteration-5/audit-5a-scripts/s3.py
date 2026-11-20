"""Scratch, SYNTHETIC BARS ONLY, neutral seed 424242. A reading of the drafted detectors, to test structural claims.
Nothing here reads data/ or uses seed 20261118 or 51118. Rates on synthetic bars are NOT predictions for real bars."""
from dataclasses import replace
import numpy as np, polars as pl
from olsprime.bench import adversary as adv, twins as tw, invariance as inv
from olsprime.bench.perturb import PERTURBED_COLUMNS

N, SEED = 4000, 424242
bars = tw.synthetic_pairs()
cfg = replace(adv.AdversaryConfig(), h1=tw.SYNTHETIC_H1, long_cuts=0)
tcfg = tw.TwinsConfig(adversary=cfg)
tb = tw.build(bars, tcfg)
h1 = tb.h1
C = h1.n_cuts
print("cuts:", C, [(c["pair"][:3], c["index"], c["kind"][:6]) for c in h1.cuts])
print("scored compared rows per cut:", h1.scored.sum(axis=1).tolist())
T = adv.PAST_REACH  # window position of the cut row

def orig_block():
    return {q: h1.view.w[q][:C].copy() for q in adv.QUANTITY_NAMES}

def bench_from(blocks, names):
    stacked = {q: np.concatenate([b[q] for b in blocks]) for q in adv.QUANTITY_NAMES}
    return adv.Bench(adv.WindowView(stacked), h1.cuts, h1.scored, tuple(names), h1.h1_cuts)

def trunc(extra):
    b = orig_block()
    for q in b:
        b[q][:, T + 1 + extra:] = np.nan
    return b

def two_run_bars(df, cut, sigma, rng):
    n = df.height; m = n - cut - 1
    z = rng.standard_normal((m, len(PERTURBED_COLUMNS)))
    col = {c: df[c].cast(pl.Float64).to_numpy().copy() for c in PERTURBED_COLUMNS}
    for i, c in enumerate(PERTURBED_COLUMNS):
        col[c][cut + 1:] *= np.exp(sigma * z[:, i])
    p = np.stack([col[c][cut + 1:] for c in ("open", "high", "low", "close")])
    col["high"][cut + 1:] = p.max(axis=0); col["low"][cut + 1:] = p.min(axis=0)
    col["taker_buy_base_volume"][cut + 1:] = np.minimum(col["taker_buy_base_volume"][cut + 1:], col["volume"][cut + 1:])
    col["taker_buy_quote_volume"][cut + 1:] = np.minimum(col["taker_buy_quote_volume"][cut + 1:], col["quote_volume"][cut + 1:])
    col["trades"][cut + 1:] = np.maximum(np.rint(col["trades"][cut + 1:]), 1.0)
    return df.with_columns([pl.Series(c, np.rint(v).astype(np.int64) if c == "trades" else v, dtype=df.schema[c]) for c, v in col.items()])

def two_run(sigma):
    blk = {q: [] for q in adv.QUANTITY_NAMES}
    zero_uw = []
    for c in h1.cuts:
        rng = np.random.default_rng([999, 1 if c["pair"] == "BTCUSDT" else 2, c["k"], 7])
        p = two_run_bars(bars[c["pair"]], c["index"], sigma, rng)
        w = adv._window(adv.quantities(p), c["index"])
        zero_uw.append(np.mean(w["upper_wick"][T + 1:] == 0))
        for name in blk:
            blk[name].append(w[name])
    return {k: np.stack(v) for k, v in blk.items()}, float(np.mean(zero_uw))

t0, t1 = trunc(0), trunc(1)
tr01, zw01 = two_run(0.1)
tr10, zw10 = two_run(1.0)
print("TWO-RUN: share of the 10 later bars with upper wick exactly 0 after the repair: sigma 0.1 ->", round(zw01, 2), ", sigma 1.0 ->", round(zw10, 2))
wr = tr01["wick_ratio"][:, T + 1:]
print("TWO-RUN sigma 0.1: share of later bars whose wick_ratio is NaN:", round(float(np.isnan(wr).mean()), 2), "(original:", round(float(np.isnan(orig_block()["wick_ratio"][:, T+1:]).mean()), 2), ")")

B = {
    "FI": h1,
    "TRUNC0": bench_from([orig_block(), t0], ["trunc0"]),
    "TRUNC1": bench_from([orig_block(), t1], ["trunc1"]),
    "TWORUN.1": bench_from([orig_block(), tr01], ["s0.1"]),
    "TWORUN1": bench_from([orig_block(), tr10], ["s1.0"]),
    "SHUFFLE": tb.twins,
}

def eval_rule(leak, bench, finite_only=False):
    c, d = bench.n_cuts, len(bench.directions)
    caught = np.zeros(c, bool)
    for arr in leak.outputs(bench.view).values():
        arr = np.broadcast_to(np.asarray(arr, dtype=np.float64), (c * (1 + d), adv.COMPARED))
        a = arr[:c]
        for j in range(d):
            b = arr[c * (1 + j): c * (2 + j)]
            both = ~np.isnan(a) & ~np.isnan(b)
            change = np.where(both, np.abs(a - b), 0.0)
            moved = change > inv.CAUGHT_ABOVE
            if not finite_only:
                moved = moved | (np.isnan(a) != np.isnan(b))
            caught |= (moved & bench.scored).any(axis=1)
    return caught

leaks = adv.generate(N, SEED)
reach = np.array([l.reach()[1] for l in leaks])
des = np.array([l.tag["designed"] for l in leaks]); out = np.array([l.output for l in leaks])
R = {k: np.stack([eval_rule(l, b) for l in leaks]) for k, b in B.items()}
F = {k: np.stack([eval_rule(l, b, True) for l in leaks]) for k, b in B.items()}
chk = np.stack([adv.evaluate_fast(l, h1).caught.any(axis=1) for l in leaks[:500]])
assert np.array_equal(chk, R["FI"][:500])
for k, b in B.items():
    assert not any(eval_rule(l.honest_twin(), b).any() for l in leaks[:800]), k
print()
print("rates on SYNTHETIC bars (structure only):")
print("detector   any-cut  per-cut  finite-only-any  designed-no-any  reach1-any")
for k in B:
    a = R[k].any(axis=1)
    print(f"{k:9s} {a.mean():8.4f} {R[k].mean():8.4f} {F[k].any(axis=1).mean():16.4f} {a[des=='no'].mean():16.4f} {a[reach==1].mean():11.4f}")
fi, tr = R["FI"].any(axis=1), R["TRUNC0"].any(axis=1)
print()
print("D1 any-cut: TRUNC0 only", int((tr & ~fi).sum()), ", FI only", int((fi & ~tr).sum()))
beyond = tr & ~fi
miss_only = tr & ~F["TRUNC0"].any(axis=1)
print("D2 reading (i): TRUNC0 catches beyond FI =", int(beyond.sum()), "; of them caught through missingness only =", int((beyond & miss_only).sum()))
print("D2 reading (ii): finite-only TRUNC0", round(float(F["TRUNC0"].any(axis=1).mean()), 4), "vs FI", round(float(F["FI"].any(axis=1).mean()), 4),
      "; TRUNC0 catches lost to the rule:", int(miss_only.sum()), "=", round(float(miss_only.mean()), 4), "; by output", dict(zip(*np.unique(out[miss_only], return_counts=True))))
single = [i for i, l in enumerate(leaks) if l.expr.binary and not isinstance(l.expr, adv.Logic)]
agree = 0
for i in single:
    l = leaks[i]; j = l.reach()[1]
    x = np.asarray(l.expr.evaluate(h1.view), dtype=bool)[:C]
    live = np.zeros((C, adv.COMPARED), bool); live[:, adv.COMPARED - j:] = True
    pred = (x & live & h1.scored).any(axis=1)
    agree += np.array_equal(pred, R["TRUNC0"][i])
print()
print("polarity identity on", len(single), "single binary leaks: TRUNC0 flags a cut iff the original output is 1 at a live scored row -> holds for", agree)
gt = [i for i in single if isinstance(leaks[i].expr, adv.Cmp) and isinstance(leaks[i].expr.rhs, adv.Const)]
ops = np.array([leaks[i].expr.op for i in gt])
for name in ("FI", "TRUNC0", "TWORUN.1", "SHUFFLE"):
    a = R[name].any(axis=1)[gt]
    print("  threshold leaks (", len(gt), "):", name, "any-cut by op: gt", round(float(a[ops == ">"].mean()), 3), " lt", round(float(a[ops == "<"].mean()), 3))
print("  row t scored at every cut:", bool(h1.scored[:, -1].all()), "-> under a missing-propagates convention TRUNC0 flags every leak at every cut")
print()
print("TRUNC1 on reach==1 leaks: caught", int(R["TRUNC1"][reach == 1].any(axis=1).sum()), "of", int((reach == 1).sum()))
print("TRUNC1 flags subset of TRUNC0 flags, per (leak, cut):", bool((~R["TRUNC1"] | R["TRUNC0"]).all()))
print("caught at sigma 0.1 but not at sigma 1.0 (same z):", int((R["TWORUN.1"].any(axis=1) & ~R["TWORUN1"].any(axis=1)).sum()))
