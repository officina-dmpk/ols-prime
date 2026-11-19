"""Audit 5b, X6: every assertion on a larger development sample (seed 51118, quantile, the registered table; TWO-RUN 51119)
on degraded synthetic bars, and the metrics of summarize() recomputed from the per-leak flags by other code. No data read."""
import sys, math, json
import numpy as np
from olsprime.bench import adversary as adv, detectors as det, detector_stats as ds

TABLE = sys.argv[1]; N = int(sys.argv[2])
cfg = det.DetectorConfig(population_seed=51118, two_run_seed=51119, placement="quantile", n=N, bootstrap_seed=4242)
bars = det.synthetic_pairs(degrade=True)
b = det.build_benches(bars, cfg)
leaks = det._draw(cfg, TABLE, range(N))
assert leaks == adv.generate(N, 51118, placement="quantile", table_path=TABLE)
results = [det.process_leak(l, b) for l in leaks]
tot = {}
for r in results:
    for k, x in r.violations.items(): tot[k] = tot.get(k, 0) + x
print("violations:", tot)
classes = det.check_classes(b)
print("classes:", classes["disagreements"], "| reported:", json.dumps(classes["reported"])[:600])
print("FI directions:", b.fi.directions, "| two-run runs:", b.two_run_runs[:3], "...", "| last-row cuts:", b.last_row_cuts)
m = det.summarize(leaks, results, b, cfg)

# --- independent recomputation -------------------------------------------------------------------
F = lambda key: np.stack([r.flags[key] for r in results])
fi = F("FI@h1"); t0 = F("TRUNC-0/G@h1"); t0m = F("TRUNC-0/M@h1"); t0p = F("TRUNC-0/P@h1"); t1 = F("TRUNC-1/G@h1"); tw_ = F("TWO-RUN@h1"); sh = F("SHUFFLE@h1")
assert fi.shape[1:] == (16, 2) and t0.shape[1:] == (16, 1) and tw_.shape[1:] == (16, 16) and sh.shape[1:] == (16, 8), (fi.shape, t0.shape, tw_.shape, sh.shape)
prim = [j for j, (s, r) in enumerate(b.two_run_runs) if s == 0.1 and r in (1, 2)]
assert prim == [0, 1]
aFI, aT0, aTW, aSH = fi.any((1, 2)), t0.any((1, 2)), tw_[:, :, prim].any((1, 2)), sh.any((1, 2))
chk = []
def same(name, got, want):
    ok = (got == want) if not isinstance(want, float) else abs(got - want) < 1e-12
    chk.append(ok); print(("ok  " if ok else "BAD ") + name, got, want)
D = m["detectors"]
same("FI any-cut", D["FI"]["any_cut"]["all"]["count"], int(aFI.sum()))
same("TRUNC-0 any-cut", D["TRUNC-0"]["any_cut"]["all"]["count"], int(aT0.sum()))
same("TWO-RUN any-cut", D["TWO-RUN"]["any_cut"]["all"]["count"], int(aTW.sum()))
same("SHUFFLE any-cut", D["SHUFFLE"]["any_cut"]["all"]["count"], int(aSH.sum()))
same("FI x3 any-cut", D["FI x3"]["any_cut"]["all"]["count"], int(fi[:, :, list(b.fi.directions).index("x3")].any(1).sum()))
same("TRUNC-0/M", D["TRUNC-0/M"]["any_cut"]["all"]["count"], int(t0m.any((1, 2)).sum()))
same("TRUNC-1/G", D["TRUNC-1/G"]["any_cut"]["all"]["count"], int(t1.any((1, 2)).sum()))
same("TWO-RUN s0.1 r8", D["TWO-RUN s0.1 r8"]["any_cut"]["all"]["count"], int(tw_[:, :, :8].any((1, 2)).sum()))
same("TWO-RUN s1 r2", D["TWO-RUN s1 r2"]["any_cut"]["all"]["count"], int(tw_[:, :, 8:10].any((1, 2)).sum()))
same("SHUFFLE k2", D["SHUFFLE k2"]["any_cut"]["all"]["count"], int(sh[:, :, :2].any((1, 2)).sum()))
same("mean rate FI", D["FI"]["mean_per_cut_rate"]["all"]["mean"], float(fi.any(2).mean(1).mean()))
h = m["h15"]
n = N
a_, b_, c_, d_ = int((aT0 & aFI).sum()), int((aT0 & ~aFI).sum()), int((~aT0 & aFI).sum()), int((~aT0 & ~aFI).sum())
same("H15 point (TRUNC-0 minus FI), points", h["difference_points"], 100.0 * ((a_ + b_) / n - (a_ + c_) / n))
ref = ds.newcombe_paired(a_, b_, c_, d_)
same("H15 interval", [round(x, 12) for x in h["ci95_points"]], [round(100 * x, 12) for x in ref["ci95"]])
same("H15 table", h["deciding_cell"]["table"], {"a": a_, "b": b_, "c": c_, "d": d_})
# constant flags, by other code: the original outputs at the scored compared rows of H1's cuts
h1 = b.rows("h1")
const = []
for l in leaks:
    outs = l.outputs(b.fi.view)
    ok = True
    for arr in outs.values():
        x = np.broadcast_to(np.asarray(arr, float), (b.fi.n_cuts * 3, adv.COMPARED))[: b.fi.n_cuts][h1]
        v = x[b.fi.scored[h1]]
        ok &= bool(np.all(v.view(np.uint64) == v.view(np.uint64)[0]))
    const.append(ok)
const = np.array(const)
same("constant at H1 cuts", m["descriptive"]["constant_h1_cuts"]["count"], int(const.sum()))
same("not-constant denominator FI", D["FI"]["any_cut"]["not-constant"], ds.share(int(aFI[~const].sum()), int((~const).sum())))
des = np.array([l.tag["designed"] for l in leaks])
same("designed-no denominator TRUNC-0", D["TRUNC-0"]["any_cut"]["designed-no"]["n"], int((des == "no").sum()))
union = aFI | aT0 | aTW | aSH
same("union", m["union"]["primary"]["count"], int(union.sum()))
same("union misses", m["union_misses"]["count"], int((~union).sum()))
for name, x in (("FI", aFI), ("TRUNC-0", aT0), ("TWO-RUN", aTW), ("SHUFFLE", aSH)):
    same("missed by " + name, m["missed_by_detector_among_union"][name]["count"], int((union & ~x).sum()))
p = m["pairs"]["FI - TRUNC-0"]
same("pair FI - TRUNC-0 b,c", (p["b"], p["c"]), (int((aFI & ~aT0).sum()), int((~aFI & aT0).sum())))
# the first-m curve: by date, then BTCUSDT before ETHUSDT
cuts = [b.cuts[i] for i in h1]
order = sorted(range(16), key=lambda j: (cuts[j]["open_time"], 0 if cuts[j]["pair"] == "BTCUSDT" else 1))
for e in m["first_m_cuts"]["TRUNC-0"]:
    same(f"first-{e['m']} TRUNC-0", e["count"], int(t0[:, order[: e['m']], 0].any(1).sum()))
print("cut order:", m["h1_cut_order"])
# the bootstrap, by other code with the same draws
fl, tl = F("FI@long").any(2), F("TRUNC-0/G@long")[:, :, 0]
lr = b.rows("long"); dates = np.array([b.cuts[i]["open_time"][:10] for i in lr]); uniq = np.unique(dates)
print("long-schedule unique dates:", uniq.size, "cuts:", lr.size)
rng = np.random.default_rng(4242); diffs = []
for _ in range(2000):
    pick = set(rng.choice(uniq, size=8, replace=False).tolist())
    cols = np.array([d in pick for d in dates])
    diffs.append(100 * (tl[:, cols].any(1).mean() - fl[:, cols].any(1).mean()))
same("bootstrap percentiles", [round(x, 10) for x in m["cut_date_bootstrap"]["percentiles_points"]], [round(float(x), 10) for x in np.percentile(diffs, [2.5, 97.5])])
inv_ = np.array([det._no_threshold(51118, l.id) for l in leaks])
same("invariant subset size", m["placement_invariant_subset"]["invariant"]["leaks"], int(inv_.sum()))
cs = m["conventions"]["sentence"]
same("X..Y", (cs["X"], cs["Y"]), (min(aT0.mean(), t0m.any((1,2)).mean(), t0p.any((1,2)).mean()), max(aT0.mean(), t0m.any((1,2)).mean(), t0p.any((1,2)).mean())))
print("ALL OK" if all(chk) else "SOME BAD", "| any-cut shares: FI", aFI.mean(), "TRUNC-0 G/M/P", aT0.mean(), t0m.any((1,2)).mean(), t0p.any((1,2)).mean(), "TWO-RUN", aTW.mean(), "SHUFFLE", aSH.mean())
print("read split:", {k: (v["flagged_rows"], v["through_a_missing_read"]["count"]) for k, v in m["read_split"].items()})
print("qualifier:", h["qualifier"], "| secondary catches of the union's misses:", m["union_misses"]["caught_by_a_secondary_arm"])
rep = det.reported_counts(results, b, classes)
print("controls:", rep["controls"]["built"], rep["controls"]["can_be_flagged"], "| p:", rep["p_assertion"])
print("two-run stats:", json.dumps(rep["two_run_repair"])[:900])
