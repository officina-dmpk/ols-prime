"""Audit 5b, X6b: H15's two qualifier cells and the mirror asymmetry, recomputed beside summarize(). Development seeds,
degraded synthetic bars. No data read."""
import sys
from dataclasses import replace
import numpy as np
from olsprime.bench import adversary as adv, detectors as det, detector_stats as ds

TABLE, N = sys.argv[1], int(sys.argv[2])
cfg = det.DetectorConfig(population_seed=51118, two_run_seed=51119, placement="quantile", n=N)
b = det.build_benches(det.synthetic_pairs(degrade=True), cfg)
leaks = adv.generate(N, 51118, placement="quantile", table_path=TABLE)
results = [det.process_leak(l, b) for l in leaks]
seen = {}
real = ds.h15
def spy(deciding, qualifiers, margin=ds.MARGIN_POINTS):
    seen["deciding"], seen["qualifiers"] = deciding, qualifiers
    return real(deciding, qualifiers, margin)
ds.h15 = spy
m = det.summarize(leaks, results, b, cfg)
F = lambda key: np.stack([r.flags[key] for r in results])
aFI, aT0, aT0M = F("FI@h1").any((1, 2)), F("TRUNC-0/G@h1").any((1, 2)), F("TRUNC-0/M@h1").any((1, 2))
h1 = b.rows("h1")
const = []
for l in leaks:
    ok = True
    for arr in l.outputs(b.fi.view).values():
        x = np.broadcast_to(np.asarray(arr, float), (b.fi.n_cuts * 3, adv.COMPARED))[: b.fi.n_cuts][h1]
        v = x[b.fi.scored[h1]].view(np.uint64)
        ok &= bool(np.all(v == v[0]))
    const.append(ok)
const = np.array(const)
def cell(x, y):
    t = ds.paired_table(x, y)
    return ds.newcombe_paired(t["a"], t["b"], t["c"], t["d"])
print("deciding      ", seen["deciding"] == cell(aT0, aFI), seen["deciding"]["difference"], seen["deciding"]["ci95"])
print("convention M  ", seen["qualifiers"]["convention M"] == cell(aT0M, aFI), seen["qualifiers"]["convention M"]["ci95"])
print("not-constant  ", seen["qualifiers"]["not-constant denominator"] == cell(aT0[~const], aFI[~const]), seen["qualifiers"]["not-constant denominator"]["ci95"], "n", int((~const).sum()))
print("keys written under h15:", sorted(m["h15"]), "| qualifier:", m["h15"]["qualifier"])
# mirror asymmetry, the mirror built here; FI through the adversary's own fast path
cmp_ = [l for l in leaks if isinstance(l.expr, adv.Cmp)]
dFI = dT0 = 0
for l in cmp_:
    mir = replace(l, expr=adv.Cmp(l.expr.lhs, "<" if l.expr.op == ">" else ">", l.expr.margin, l.expr.rhs))
    dFI += int(adv.evaluate_fast(l, b.fi).caught[h1].any() != adv.evaluate_fast(mir, b.fi).caught[h1].any())
    t0 = b.trunc_parts["TRUNC-0"][h1]
    dT0 += int(det.judge_window(l, b.trunc, "G").cut_flags[t0].any() != det.judge_window(mir, b.trunc, "G").cut_flags[t0].any())
ma = m["mirror_asymmetry"]
print("mirror leaks", len(cmp_), ma["FI"]["leaks"], "| FI any-cut differs", dFI, ma["FI"]["any_cut"]["count"], "| TRUNC-0", dT0, ma["TRUNC-0"]["any_cut"]["count"])
