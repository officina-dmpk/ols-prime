"""Scratch 5a-bis, SYNTHETIC BARS ONLY, neutral seed 424242. No data/, no registered seed."""
import sys, zlib
from dataclasses import replace
import numpy as np, polars as pl
from scipy.special import expit
from olsprime.bench import adversary as adv, twins as tw, invariance as inv

MODE = sys.argv[1] if len(sys.argv) > 1 else "plain"
N, SEED = 4000, 424242

def degrade(b):
    out = {}
    for p, df in b.items():
        rng = np.random.default_rng(5 if p == "BTCUSDT" else 6)
        n = df.height
        o, c = df["open"].to_numpy(), df["close"].to_numpy()
        top, bot = np.maximum(o, c), np.minimum(o, c)
        hi, lo = df["high"].to_numpy().copy(), df["low"].to_numpy().copy()
        hit_u, hit_l = rng.random(n) < 0.02, rng.random(n) < 0.02
        hi = np.where(hit_u, top, hi); lo = np.where(hit_l, bot, lo)
        cols = [pl.Series("high", hi), pl.Series("low", lo)]
        if "zv" in MODE:
            z = rng.random(n) < 0.02
            for name in ("volume", "quote_volume", "taker_buy_base_volume", "taker_buy_quote_volume"):
                cols.append(pl.Series(name, np.where(z, 0.0, df[name].to_numpy())))
            cols.append(pl.Series("trades", np.where(z, 0, df["trades"].to_numpy()).astype(np.int64)))
        out[p] = df.with_columns(cols)
    return out

bars = tw.synthetic_pairs()
if MODE != "plain":
    bars = degrade(bars)
cfg = replace(adv.AdversaryConfig(), h1=tw.SYNTHETIC_H1, long_cuts=0)
C_list, scored_list, W0 = [], [], []
for pair, df in bars.items():
    from olsprime.bench import pipeline as pp
    from olsprime.data.binance_vision import Month
    h1 = cfg.h1
    frame = pp.build_frame(df, h1.interval, h1.h)
    folds = pp.make_folds(frame, h1.interval, h1.h, Month(*h1.start), Month(*h1.end))
    sc = np.zeros(df.height, bool); sc[adv.scored_rows(folds)] = True
    cuts = inv.choose_cuts(df, folds, seed=h1.cut_seed)
    q0 = adv.quantities(df)
    for k, cut in enumerate(cuts):
        C_list.append((pair, k, cut.index, df.height))
        rows = cut.index - adv.FUTURE_REACH + np.arange(adv.COMPARED)
        scored_list.append(np.where(rows >= 0, sc[np.clip(rows, 0, None)], False))
        W0.append(adv._window(q0, cut.index))
        # is row t+1 scored?
        if k == 0 and pair == "BTCUSDT":
            print("scored rows span:", int(np.flatnonzero(sc)[0]), int(np.flatnonzero(sc)[-1]), "height", df.height, "contiguous:", bool(sc[np.flatnonzero(sc)[0]:np.flatnonzero(sc)[-1]+1].all()))
C = len(C_list)
scored = np.stack(scored_list)
print("mode", MODE, "cuts", [(p[:3], i) for p, _, i, _ in C_list])
T = adv.PAST_REACH
orig = {q: np.stack([w[q] for w in W0]) for q in adv.QUANTITY_NAMES}
trunc = {q: v.copy() for q, v in orig.items()}
for q in trunc:
    trunc[q][:, T + 1:] = np.nan
view = adv.WindowView({q: np.concatenate([orig[q], trunc[q]]) for q in adv.QUANTITY_NAMES})

def reads_of(leak):
    rv = adv.RecordingView(view)
    leak.expr.evaluate(rv)
    return sorted(rv.reads)

def rule(a, b):
    both = ~np.isnan(a) & ~np.isnan(b)
    return ((np.where(both, np.abs(a - b), 0.0) > inv.CAUGHT_ABOVE) | (np.isnan(a) != np.isnan(b)))

def flags_G(leak):
    m = np.zeros((C, adv.COMPARED), bool)
    for arr in leak.outputs(view).values():
        arr = np.broadcast_to(np.asarray(arr, np.float64), (2 * C, adv.COMPARED))
        m |= rule(arr[:C], arr[C:])
    return m & scored

leaks = adv.generate(N, SEED)
