"""Audit 5b, X4: FI's registered rule on Fonseca's M2 at its boundary, on engineered synthetic bars. No data read."""
import numpy as np, polars as pl
from olsprime.bench import adversary as adv, detectors as det

cfg = adv.AdversaryConfig(long_cuts=0)
base = det.synthetic_pairs()
b0 = base["BTCUSDT"]
probe = adv.build_bench({"BTCUSDT": b0}, cfg)
cuts = [(c["k"], c["index"]) for c in probe.cuts]
print("cuts", cuts)
m2, m2m = det.class_m2(), det.class_m2(mirrored=True)
for k, t in cuts[:4]:
    for crash_window in (False, True):
        for r in (0.70, 0.667, 0.666, 0.60, 0.40):
            b = b0
            cols = {c: b[c].to_numpy().copy() for c in ("open", "high", "low", "close")}
            if crash_window:  # a tall bar 30 days earlier: the 90-bar window's high is 1.6 x close[t]
                s = t - 30
                cols["high"][s] = 1.6 * cols["close"][t]
            scale = r * cols["close"][t] / cols["high"][t + 1]
            for c in cols:
                cols[c][t + 1] *= scale
            b = b.with_columns([pl.Series(c, v) for c, v in cols.items()])
            bench = adv.build_bench({"BTCUSDT": b}, cfg)
            i = [j for j, c in enumerate(bench.cuts) if c["index"] == t][0]
            got = adv.evaluate_fast(m2, bench).caught[i]
            gotm = adv.evaluate_fast(m2m, bench).caught[i]
            rule = det.fi_m2_rule(b, t)
            wmax = float(cols["high"][max(0, t - 90) : t + 1].max() / cols["close"][t])
            flag = "" if bool(got.any()) == rule else "   <-- RULE DISAGREES"
            print(f"k={k} t={t} high[t+1]/close[t]={r:.3f} window max high/close[t]={wmax:.3f} FI(x3,/3)={got.tolist()} mirror={gotm.tolist()} rule={rule}{flag}")
