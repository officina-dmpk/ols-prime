"""Audit phase 2a, A5: the three factor builders of bench/casestudy.py on synthetic hourly bars (no real bar).

1. Closes after bar t are changed: every position at or before t must be bit-identical.
2. Each position is rebuilt by a scalar loop from the text of the dated line (PROTOCOL, 2026-11-19 after pass 5b).
3. The cut of load_bars: a bar whose known_at is at or after DEVELOPMENT.end does not survive the filter.
4. A gap in the grid makes the windows that span it missing (never silently bridged).

Run from python/:  python ../.claude/briefs/iteration-5/audit-2a-scripts/a5_builders.py
"""
import math
from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl

from olsprime.bench import casestudy as cs
from olsprime.protocol import DEVELOPMENT

rng = np.random.default_rng(5)
N = 600
cfg = cs.CaseStudyConfig()


def frame(close, start=datetime(2024, 12, 20, tzinfo=UTC), drop=()):
    keep = [i for i in range(len(close)) if i not in drop]
    opens = [start + timedelta(hours=i) for i in keep]
    return pl.DataFrame({"symbol": ["XUSDT"] * len(keep), "open_time": opens, "close": [float(close[i]) for i in keep],
                         "known_at": [o + timedelta(hours=1) - timedelta(milliseconds=1) for o in opens]},
                        schema_overrides={"open_time": pl.Datetime("ms", "UTC"), "known_at": pl.Datetime("ms", "UTC")})


close = 100 * np.exp(np.cumsum(0.01 * rng.standard_normal(N)))
close[300:420] = close[299]  # a flat stretch: v_t = 0 on part of it
bars = frame(close)
base = {name: b(bars, cfg) for name, b in cs.FACTOR_BUILDERS.items()}

# 1. future invariance, at every tenth t
worst = 0
for t in range(0, N - 1, 10):
    moved = close.copy()
    moved[t + 1 :] *= np.exp(rng.standard_normal(N - t - 1))
    for name, b in cs.FACTOR_BUILDERS.items():
        got = b(frame(moved), cfg)
        same = np.array_equal(got[: t + 1], base[name][: t + 1], equal_nan=True)
        worst += not same
print("1. future invariance: builders x cuts that moved at or before t:", worst)

# 2. the formulas, by a scalar loop
wrong = {"reversal": 0, "momentum": 0, "vol_timed_momentum": 0}
defined = {"reversal": 0, "momentum": 0, "vol_timed_momentum": 0}
for t in range(N):
    r = lambda s: math.log(close[s] / close[s - 1])  # noqa: E731
    exp = {}
    exp["reversal"] = -r(t) if t >= 1 else math.nan
    exp["momentum"] = math.log(close[t - 1] / close[t - 25]) if t >= 25 else math.nan
    if t >= 90:
        v = sum(r(s) ** 2 for s in range(t - 89, t + 1)) / 90
        m = exp["momentum"]
        exp["vol_timed_momentum"] = (0.0 if v == 0 else m / (24 * v)) if not math.isnan(m) else math.nan
    else:
        exp["vol_timed_momentum"] = math.nan
    for name in wrong:
        got = float(base[name][t])
        if math.isnan(exp[name]) != math.isnan(got) or (not math.isnan(got) and abs(got - exp[name]) > 1e-9 * max(1.0, abs(exp[name]))):
            wrong[name] += 1
        defined[name] += not math.isnan(got)
print("2. positions that differ from the scalar rebuild:", wrong, "| defined:", defined, "| zero-variance positions:", int((base["vol_timed_momentum"] == 0).sum()))

# 3. the cut of load_bars, as its filter is written
last = frame(close, start=datetime(2024, 12, 31, 12, tzinfo=UTC))[:30]
kept = last.filter(pl.col("known_at") < DEVELOPMENT.end)
print("3. DEVELOPMENT.end:", DEVELOPMENT.end, "| last bar kept opens", kept["open_time"][-1], "| bars at or after the end kept:",
      int((kept["open_time"] >= DEVELOPMENT.end).sum()), "| kept", kept.height, "of", last.height)

# 4. a missing hour
gap = frame(close, drop=(200,))
g = {name: b(gap, cfg) for name, b in cs.FACTOR_BUILDERS.items()}
idx = 200  # the row after the gap (the bar that was index 201)
print("4. after a missing hour: reversal defined at the next bar:", bool(np.isfinite(g["reversal"][idx])),
      "| momentum defined within 25 bars:", int(np.isfinite(g["momentum"][idx : idx + 25]).sum()),
      "| volatility-timed defined within 90 bars:", int(np.isfinite(g["vol_timed_momentum"][idx : idx + 89]).sum()))
