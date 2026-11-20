"""Audit 5b, X3: an independent scalar re-implementation of PROTOCOL §2.5 against det.two_run_bars.
Synthetic bars only; TWO-RUN development seed 51119; no data read."""
import math, zlib, sys
import numpy as np
from olsprime.bench import detectors as det

COLS = ("open", "high", "low", "close", "volume", "quote_volume", "taker_buy_base_volume", "taker_buy_quote_volume", "trades")

def ref_bar(row, z, sigma):
    o, h, lo, c, v, q, tb, tq, tr = (float(row[k]) for k in COLS)
    f = [math.exp(sigma * float(x)) for x in z]
    f_open, f_high, f_low, f_close, f_vol, f_quote, f_tb, f_tq, f_tr = f
    o2, c2 = o * f_open, c * f_close
    uw = math.log(h / max(o, c)); lw = math.log(min(o, c) / lo)
    uw2, lw2 = uw * f_high, lw * f_low
    h2 = max(o2, c2) * math.exp(uw2); lo2 = min(o2, c2) * math.exp(-lw2)
    if v > 0:
        v2 = v * f_vol
        vwap = q / v * f_quote
        clipped = min(max(vwap, lo2), h2)
        q2 = v2 * clipped
        tb2 = min(tb * f_tb, v2); tq2 = min(tq * f_tq, q2)
        tr2 = max(float(np.rint(tr * f_tr)), 1.0)
    else:
        v2, q2, tb2, tq2, tr2 = v, q, tb, tq, tr
    return (o2, h2, lo2, c2, v2, q2, tb2, tq2, tr2)

bars = det.synthetic_pairs(degrade=True)
bad = 0; checked = 0; zero_vol_nonzero = 0
rng = np.random.default_rng(99)
for pair, b in bars.items():
    arr = {k: b[k].cast(float).to_numpy() for k in COLS}
    zv = (arr["volume"] == 0)
    zero_vol_nonzero += int((zv & ((arr["quote_volume"] != 0) | (arr["taker_buy_base_volume"] != 0) | (arr["taker_buy_quote_volume"] != 0) | (arr["trades"] != 0))).sum())
    n = b.height
    cuts = list(rng.integers(300, n - 2, size=40)) + [n - 2, n - 5, n - 11]
    for k, t in enumerate(cuts):
        t = int(t)
        for run in (1, 2, 5, 8):
            z = det.two_run_z(51119, pair, 2, k, run)
            zref = np.random.default_rng([51119, zlib.crc32(pair.encode("ascii")), 2, k, run]).standard_normal((10, 9))
            assert np.array_equal(z, zref)
            for sigma in (0.1, 1.0):
                out, st = det.two_run_bars(b, t, sigma, z)
                got = {k_: out[k_].cast(float).to_numpy() for k_ in COLS}
                rows = range(t + 1, min(t + 11, n))
                for i, r in enumerate(rows):
                    want = ref_bar({k_: arr[k_][r] for k_ in COLS}, z[i], sigma)
                    for k_, w in zip(COLS, want):
                        g = got[k_][r]
                        checked += 1
                        if not (g == w or abs(g - w) <= 4e-16 * abs(w)):
                            bad += 1
                            if bad < 10: print("MISMATCH", pair, t, run, sigma, r, k_, g, w)
                outside = np.ones(n, bool); outside[t + 1 : t + 11] = False
                for k_ in COLS:
                    assert np.array_equal(got[k_][outside], arr[k_][outside])
print("values checked", checked, "mismatches beyond 2 ulp", bad, "| zero-volume bars with a nonzero other column:", zero_vol_nonzero)
