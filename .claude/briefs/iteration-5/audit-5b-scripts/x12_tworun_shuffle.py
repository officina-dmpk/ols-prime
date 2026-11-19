"""Audit 5b, X12: TWO-RUN (both sigmas, runs 1..8, both schedules) and SHUFFLE (8 twins) from the registered seed keys,
through a SeriesView of the whole perturbed series, against the module's windowed flags. Development seeds 51118/51119,
degraded synthetic bars. No data read."""
import sys, zlib
import numpy as np
from olsprime.bench import adversary as adv, detectors as det, twins as tw

TABLE, N = sys.argv[1], int(sys.argv[2])
cfg = det.DetectorConfig(population_seed=51118, two_run_seed=51119, placement="quantile", n=N)
bars = det.synthetic_pairs(degrade=True)
b = det.build_benches(bars, cfg)
leaks = adv.generate(N, 51118, placement="quantile", table_path=TABLE)
extras = {p: det.extra_quantities(x, i) for i, (p, x) in enumerate(bars.items())}
full = {p: adv.SeriesView({**adv.quantities(x), **extras[p]}) for p, x in bars.items()}
def moved(a, c):
    both = ~np.isnan(a) & ~np.isnan(c)
    return (np.where(both, np.abs(a - c), 0.0) > 1e-9) | (np.isnan(a) != np.isnan(c))
def flag(leak, orig, view, p, t):
    sc = b.schedules[p].scored
    rows = np.arange(t - 10, t + 1); rows = rows[sc[rows]]
    run = leak.outputs(view)
    out = False
    for k in orig:
        x = np.broadcast_to(np.asarray(orig[k], float), (bars[p].height,))[rows]
        y = np.broadcast_to(np.asarray(run[k], float), (bars[p].height,))[rows]
        out |= bool(moved(x, y).any())
    return out
# every perturbed series once
two = {}
for j, c in enumerate(b.cuts):
    p, t, sid = c["pair"], c["index"], {"h1": 1, "long": 2}[c["schedule"]]
    for r, (sigma, run) in enumerate([(s, q) for s in (0.1, 1.0) for q in range(1, 9)]):
        z = np.random.default_rng([51119, zlib.crc32(p.encode("ascii")), sid, c["k"], run]).standard_normal((10, 9))
        out, _ = det.two_run_bars(bars[p], t, sigma, z)
        two[(j, r)] = adv.SeriesView({**adv.quantities(out), **extras[p]})
assert b.two_run_runs == [(s, q) for s in (0.1, 1.0) for q in range(1, 9)]
shf = {}
for j, c in enumerate(b.shuffle.cuts):
    p, t = c["pair"], c["index"]
    for k in range(8):
        out = tw.shuffle_after(bars[p], t, np.random.default_rng([20261030, zlib.crc32(p.encode("ascii")), c["k"], k]))
        shf[(j, k)] = adv.SeriesView({**adv.quantities(out), **extras[p]})
bad = {"TWO-RUN": 0, "SHUFFLE": 0}; units = {"TWO-RUN": 0, "SHUFFLE": 0}
for leak in leaks:
    orig = {p: leak.outputs(full[p]) for p in bars}
    g2 = det.judge_window(leak, b.two_run).cut_flags
    gs = det.judge_window(leak, b.shuffle).cut_flags
    for (j, r), view in two.items():
        c = b.cuts[j]; units["TWO-RUN"] += 1
        bad["TWO-RUN"] += int(flag(leak, orig[c["pair"]], view, c["pair"], c["index"]) != bool(g2[j, r]))
    for (j, k), view in shf.items():
        c = b.shuffle.cuts[j]; units["SHUFFLE"] += 1
        bad["SHUFFLE"] += int(flag(leak, orig[c["pair"]], view, c["pair"], c["index"]) != bool(gs[j, k]))
print("units", units, "disagreements", bad)
