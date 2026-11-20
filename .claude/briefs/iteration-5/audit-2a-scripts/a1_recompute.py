"""Audit phase 2a, A1: every number of detectors.json that verdicts.jsonl determines, recomputed by a reader written
for this pass (no olsprime import), and written as one table: JSON path, the value of the run, mine, agree.

It never stops on a disagreement: every row is collected, and the disagreements are listed at the end.
It reads two files of a finished run folder and no bar. The cut-date bootstrap is reproduced with the seed that the
header of the file records (the same stream on the stored verdicts; nothing is drawn on bars).

Run:  python a1_recompute.py RUN_FOLDER OUT.tsv
"""
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

folder, out_path = Path(sys.argv[1]), Path(sys.argv[2])
res = json.loads((folder / "detectors.json").read_text(encoding="utf-8"))
M = res["metrics"]
with open(folder / "verdicts.jsonl", encoding="utf-8") as fh:
    header = json.loads(fh.readline())
    recs = [json.loads(line) for line in fh]
F = header["fields"]
n = len(recs)
col = {name: [r[i] for r in recs] for i, name in enumerate(F)}
assert col["id"] == list(range(n)) and header["leaks"] == n and header["format"] == "olsprime-detector-verdicts/1"

ROWS = []  # (path, run value, mine, verdict)


def same(a, b, tol):
    if isinstance(a, bool) or isinstance(b, bool) or isinstance(a, str) or isinstance(b, str) or a is None or b is None:
        return a == b
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k], tol) for k in a)
    if isinstance(a, int) and isinstance(b, int):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    return False


def row(path, run_value, mine, tol=1e-9):
    ROWS.append((path, run_value, mine, "agree" if same(run_value, mine, tol) else "DISAGREE"))


def mine_only(path, mine):
    ROWS.append((path, "(not in the run)", mine, "mine only"))


def read_only(path, run_value, why):
    ROWS.append((path, run_value, f"(not recomputable: {why})", "read"))


# --- the decoder: bit i of a vector is bit (i mod 8) of byte (i div 8), from the English text of the header ---------
def decode(hexes, layout):
    present = [h is not None for h in hexes]
    total = sum(e["cuts"] * e["runs"] for e in layout)
    nbytes = (total + 7) // 8
    raw = np.zeros((len(hexes), nbytes), dtype=np.uint8)
    for i, h in enumerate(hexes):
        if h is not None:
            b = bytes.fromhex(h)
            assert len(b) == nbytes, (i, len(b), nbytes)
            raw[i] = np.frombuffer(b, dtype=np.uint8)
    pos = np.arange(nbytes * 8)
    bits = (np.right_shift(raw[:, pos // 8], (pos % 8).astype(np.uint8)) & 1).astype(bool)
    assert not bits[:, total:].any(), "padding bits set"
    out, seen = {}, 0
    for e in layout:
        assert e["offset"] == seen, "layout offsets are not contiguous"
        out[e["key"]] = bits[:, e["offset"] : e["offset"] + e["cuts"] * e["runs"]].reshape(len(hexes), e["cuts"], e["runs"])
        seen += e["cuts"] * e["runs"]
    return out, np.array(present)


FL, _ = decode(col["flags"], header["layout"]["flags"])
FN, _ = decode(col["finite"], header["layout"]["finite"])
MR, has_mirror = decode(col["mirror"], header["layout"]["mirror"])
labels = {e["key"]: e["run_labels"] for e in header["layout"]["flags"]}


# --- the registered variants, from PROTOCOL section 2 (the list of the header is then compared) ----------------------
def variants(src):
    def pick(key, wanted):
        return src[key][:, :, [labels[key].index(w) for w in wanted]].any(axis=2)

    v = {}
    for s, sfx in (("h1", ""), ("long", "@long")):
        v["FI" + sfx] = pick(f"FI@{s}", ["x3", "/3"])
        v["FI x3" + sfx] = pick(f"FI@{s}", ["x3"])
        v["FI /3" + sfx] = pick(f"FI@{s}", ["/3"])
        for d in ("TRUNC-0", "TRUNC-1"):
            for c in "GMP":
                v[f"{d}/{c}{sfx}"] = pick(f"{d}/{c}@{s}", ["truncated"])
        for sig in ("0.1", "1"):
            for k in (1, 2, 8):
                v[f"TWO-RUN s{sig} r{k}{sfx}"] = pick(f"TWO-RUN@{s}", [f"s{sig}-r{r}" for r in range(1, k + 1)])
    for k in (1, 2, 8):
        v[f"SHUFFLE k{k}"] = pick("SHUFFLE@h1", [f"twin-{j}" for j in range(k)])
    for c in "GMP":
        v[f"RETILE/{c}@ends"] = pick(f"RETILE/{c}@ends", ["tile"])
        v[f"ENDS/{c}@ends"] = pick(f"ENDS/{c}@ends", ["truncated"])
    v["TRUNC-0"], v["TWO-RUN"], v["SHUFFLE"] = v["TRUNC-0/G"], v["TWO-RUN s0.1 r2"], v["SHUFFLE k8"]
    return v


V, VF = variants(FL), variants(FN)
row("verdicts.jsonl header.variants (names)", sorted(header["variants"]), sorted(V))
bad = [name for name, spec in header["variants"].items()
       if not np.array_equal(FL[spec["key"]][:, :, [labels[spec["key"]].index(w) for w in spec["runs"]]].any(axis=2), V.get(name))]
row("verdicts.jsonl header.variants (definitions that differ from PROTOCOL section 2)", 0, len(bad))
row("verdicts.jsonl header.config == detectors.json config", True, header["config"] == res["config"])

ANY = {k: x.any(axis=1) for k, x in V.items()}
ANYF = {k: x.any(axis=1) for k, x in VF.items()}
RATE = {k: x.mean(axis=1) for k, x in V.items()}
const = np.array(col["constant_h1_cuts"], dtype=bool)
const_both = np.array(col["constant_both_schedules"], dtype=bool)
inv = np.array(col["placement_invariant"], dtype=bool)
fam = np.array(col["family"])
pos = np.array(col["position"])
designed = np.array(col["designed"])
DEN = {"all": np.ones(n, bool), "not-constant": ~const, "designed-no": designed == "no"}
Z = 1.959963984540054


def wilson(k, m):
    if m == 0:
        return None, None
    centre = (k + Z * Z / 2) / (m + Z * Z)
    half = Z * math.sqrt(k * (m - k) / m + Z * Z / 4) / (m + Z * Z)
    return centre - half, centre + half


def share_row(path, got, k, m):
    lo, hi = wilson(k, m)
    mine = {"count": int(k), "n": int(m), "share": (k / m if m else None), "wilson95": [lo, hi]}
    row(path, {x: got.get(x) for x in mine}, mine)


def newcombe(a, b, c, d):
    m = a + b + c + d
    p1, p2 = (a + b) / m, (a + c) / m
    l1, u1 = wilson(a + b, m)
    l2, u2 = wilson(a + c, m)
    den = (a + b) * (c + d) * (a + c) * (b + d)
    A = a * d - b * c
    if den == 0:
        phi = 0.0
    elif A > m / 2:
        phi = (A - m / 2) / math.sqrt(den)
    elif A >= 0:
        phi = 0.0
    else:
        phi = A / math.sqrt(den)
    dl, du, el, eu = p1 - l1, u1 - p1, p2 - l2, u2 - p2
    lo = p1 - p2 - math.sqrt(max(0.0, dl * dl - 2 * phi * dl * eu + eu * eu))
    hi = p1 - p2 + math.sqrt(max(0.0, du * du - 2 * phi * du * el + el * el))
    return {"difference": p1 - p2, "ci95": [lo, hi], "n": m, "psi": phi}


def table(x, y):
    return {"a": int((x & y).sum()), "b": int((x & ~y).sum()), "c": int((~x & y).sum()), "d": int((~x & ~y).sum())}


def mcnemar(b, c):
    """Exact two-sided conditional p as a Fraction: min(1, 2 P(X <= min(b, c))), X ~ Bin(b + c, 1/2)."""
    m = b + c
    if m == 0:
        return Fraction(1)
    tail = sum(math.comb(m, i) for i in range(min(b, c) + 1))
    return min(Fraction(1), Fraction(2 * tail, 2**m))


def log10_fraction(fr):
    return math.log10(fr.numerator) - math.log10(fr.denominator) if fr > 0 else float("-inf")


def p_row(path, got, b, c):
    fr = mcnemar(b, c)
    mine = float(fr)
    ok = (got == mine) or (mine > 0 and abs(got - mine) <= 1e-6 * mine)
    ROWS.append((path, got, f"{mine!r} (log10 p = {log10_fraction(fr):.1f})", "agree" if ok else "DISAGREE"))


def mean_ci(x):
    x = np.asarray(x, dtype=float)
    m = float(x.mean())
    se = float(x.std(ddof=1) / math.sqrt(x.size))
    return {"n_leaks": int(x.size), "mean": m, "ci95": [m - Z * se, m + Z * se]}


def cell_row(path, got, x, y, with_table=True):
    t = table(x, y)
    mine = newcombe(**t)
    if with_table:
        mine["table"] = t
    row(path, {k: got.get(k) for k in mine}, mine)
    mine["table"] = t
    return mine


def pair_block(base, got, x, y):
    t = table(ANY[x], ANY[y])
    row(f"{base}.table", got["table"], t)
    row(f"{base}.b", got["b"], t["b"])
    row(f"{base}.c", got["c"], t["c"])
    row(f"{base}.newcombe", got["newcombe"], newcombe(**t))
    p_row(f"{base}.mcnemar_exact_p", got["mcnemar_exact_p"], t["b"], t["c"])
    row(f"{base}.per_cut_rate_difference", got["per_cut_rate_difference"], mean_ci(RATE[x] - RATE[y]))


# --- 1. any-cut shares, mean per-cut rates, sensitivity, families, positions: every variant, three denominators ----
names = [k for k in V if "@" not in k or k.endswith("@ends")]
row("metrics.detectors (variant names)", sorted(M["detectors"]), sorted(names))
families = sorted(set(fam))
strata = {"inside": pos == "inside", "outside": pos == "outside", "other": (pos != "inside") & (pos != "outside")}
for k in sorted(names):
    for d, m in DEN.items():
        share_row(f"metrics.detectors[{k}].any_cut[{d}]", M["detectors"][k]["any_cut"][d], int(ANY[k][m].sum()), int(m.sum()))
        row(f"metrics.detectors[{k}].mean_per_cut_rate[{d}]", M["detectors"][k]["mean_per_cut_rate"][d], mean_ci(RATE[k][m]))
        share_row(f"metrics.ignores_outputs_that_turn_missing[{k}][{d}]", M["ignores_outputs_that_turn_missing"][k][d], int(ANYF[k][m].sum()), int(m.sum()))
        for f in families:
            mm = m & (fam == f)
            share_row(f"metrics.detectors[{k}].by_family[{d}][{f}]", M["detectors"][k]["by_family"][d][f], int(ANY[k][mm].sum()), int(mm.sum()))
        for s, sm in strata.items():
            mm = m & sm
            share_row(f"metrics.detectors[{k}].by_position[{d}][{s}]", M["detectors"][k]["by_position"][d][s], int(ANY[k][mm].sum()), int(mm.sum()))
    row(f"metrics.detectors[{k}].cuts", M["detectors"][k]["cuts"], int(V[k].shape[1]))

# --- the long schedule: "all" is in the run; the two other denominators are mine only (PROTOCOL, N9) -------------------
for k in sorted(x for x in V if x.endswith("@long")):
    share_row(f"metrics.long_schedule[{k}].any_cut", M["long_schedule"][k]["any_cut"], int(ANY[k].sum()), n)
    row(f"metrics.long_schedule[{k}].mean_per_cut_rate", M["long_schedule"][k]["mean_per_cut_rate"], mean_ci(RATE[k]))
    for d in ("not-constant", "designed-no"):
        m = DEN[d]
        lo, hi = wilson(int(ANY[k][m].sum()), int(m.sum()))
        mine_only(f"long_schedule[{k}].any_cut[{d}]", {"count": int(ANY[k][m].sum()), "n": int(m.sum()), "share": float(ANY[k][m].mean()), "wilson95": [lo, hi]})

# --- first-m-cuts curves ------------------------------------------------------------------------------------------
h1 = header["cuts"]["h1"]
order = sorted(range(len(h1)), key=lambda j: (h1[j]["open_time"], header["pairs"].index(h1[j]["pair"])))
row("metrics.h1_cut_order", M["h1_cut_order"], [h1[j]["open_time"][:10] + " " + h1[j]["pair"] for j in order])
for k in ("FI", "TRUNC-0", "TWO-RUN", "SHUFFLE", "TRUNC-1/G"):
    for d, m in DEN.items():
        for c in M["first_m_cuts"][k][d]:
            mm_ = c["m"]
            share_row(f"metrics.first_m_cuts[{k}][{d}][m={mm_}]", c, int(V[k][:, order[:mm_]].any(axis=1)[m].sum()), int(m.sum()))

# --- conventions and their sentence -----------------------------------------------------------------------------------
for det, key in (("TRUNC-0", "TRUNC-0/{}"), ("TRUNC-1", "TRUNC-1/{}"), ("RETILE", "RETILE/{}@ends")):
    for d, m in DEN.items():
        for c in "GMP":
            share_row(f"metrics.conventions[{det}][{d}][{c}]", M["conventions"][det][d][c], int(ANY[key.format(c)][m].sum()), int(m.sum()))
for d, m in DEN.items():
    s = {c: float(ANY[f"TRUNC-0/{c}"][m].mean()) for c in "GMP"}
    row(f"metrics.conventions.sentence[{d}]", M["conventions"]["sentence"][d], {"X": min(s.values()), "Y": max(s.values()), "G_to_M": sorted([s["G"], s["M"]])})

# --- pairs (section 4.7) and equal run counts (section 4.8) --------------------------------------------------------------
PRIMARY = ["FI", "TRUNC-0", "TWO-RUN", "SHUFFLE"]
expected_pairs = {f"{x} - {y}": (x, y) for i, x in enumerate(PRIMARY) for y in PRIMARY[i + 1 :]}
expected_pairs["TRUNC-1/G - TRUNC-0 (one-bar date shift)"] = ("TRUNC-1/G", "TRUNC-0")
row("metrics.pairs (names)", sorted(M["pairs"]), sorted(expected_pairs))
for name, (x, y) in expected_pairs.items():
    if name in M["pairs"]:
        pair_block(f"metrics.pairs[{name}]", M["pairs"][name], x, y)
equal = {"FI x3 - TRUNC-0": ("FI x3", "TRUNC-0"), "TWO-RUN s0.1 r1 - TRUNC-0": ("TWO-RUN s0.1 r1", "TRUNC-0"), "SHUFFLE k1 - TRUNC-0": ("SHUFFLE k1", "TRUNC-0"),
         "FI - TWO-RUN s0.1 r2": ("FI", "TWO-RUN s0.1 r2"), "FI - SHUFFLE k2": ("FI", "SHUFFLE k2")}
row("metrics.equal_run_counts (names)", sorted(M["equal_run_counts"]), sorted(equal))
for name, (x, y) in equal.items():
    if name in M["equal_run_counts"]:
        pair_block(f"metrics.equal_run_counts[{name}]", M["equal_run_counts"][name], x, y)

# --- the union, its misses, and what each detector misses of it ---------------------------------------------------
union = ANY["FI"] | ANY["TRUNC-0"] | ANY["TWO-RUN"] | ANY["SHUFFLE"]
long4 = ANY["FI@long"] | ANY["TRUNC-0/G@long"] | ANY["TRUNC-1/G@long"] | ANY["TWO-RUN s0.1 r2@long"]
urows = {"primary": union, "with TRUNC-1": union | ANY["TRUNC-1/G"], "with RETILE": union | ANY["RETILE/G@ends"], "with sigma 1": union | ANY["TWO-RUN s1 r2"],
         "over both schedules": union | long4 | ANY["TRUNC-1/G"], "under convention M": ANY["FI"] | ANY["TRUNC-0/M"] | ANY["TWO-RUN"] | ANY["SHUFFLE"]}
row("metrics.union (names)", sorted(M["union"]), sorted(urows))
for name, u in urows.items():
    share_row(f"metrics.union[{name}]", M["union"][name], int(u.sum()), n)
um = M["union_misses"]
miss = ~union
row("metrics.union_misses.count", um["count"], int(miss.sum()))
row("metrics.union_misses.constant_h1_cuts", um["constant_h1_cuts"], int((miss & const).sum()))
row("metrics.union_misses.constant_both_schedules", um["constant_both_schedules"], int((miss & const_both).sum()))
secondary = {"TRUNC-1": ANY["TRUNC-1/G"], "RETILE": ANY["RETILE/G@ends"], "sigma 1": ANY["TWO-RUN s1 r2"], "long schedule": long4, "convention M": ANY["TRUNC-0/M"]}
for name, s in secondary.items():
    row(f"metrics.union_misses.caught_by_a_secondary_arm[{name}]", um["caught_by_a_secondary_arm"].get(name), int((miss & s).sum()))
row("metrics.union_misses.by_family", um["by_family"], {f: int((miss & (fam == f)).sum()) for f in um["by_family"]})
mine_only("union misses caught by no secondary arm", int((miss & ~np.any(list(secondary.values()), axis=0)).sum()))
mine_only("union misses caught by no secondary arm other than convention M", int((miss & ~np.any([v_ for k_, v_ in secondary.items() if k_ != "convention M"], axis=0)).sum()))
mine_only("union misses that are not constant at the compared rows of the 16 cuts", int((miss & ~const).sum()))
for d in PRIMARY:
    share_row(f"metrics.missed_by_detector_among_union[{d}]", M["missed_by_detector_among_union"][d], int((union & ~ANY[d]).sum()), int(union.sum()))

# --- H15 ---------------------------------------------------------------------------------------------------------
h = M["h15"]
dec = cell_row("metrics.h15.deciding_cell (table, difference, ci95, psi, n)", h["deciding_cell"], ANY["TRUNC-0"], ANY["FI"])
p_row("metrics.h15.deciding_cell.mcnemar_exact_p", h["deciding_cell"]["mcnemar_exact_p"], dec["table"]["b"], dec["table"]["c"])
L, U = 100 * dec["ci95"][0], 100 * dec["ci95"][1]
point = 100 * dec["difference"]
row("metrics.h15.difference_points", h["difference_points"], point)
row("metrics.h15.ci95_points", h["ci95_points"], [L, U])
sign = "above FI" if L > 0 else "below FI" if U < 0 else "not separated from FI"
margin = None if sign == "above FI" else "within 1 point" if L > -1 else "by more than 1 point" if U < -1 else "1-point margin not resolved"
prior = "holds" if sign == "above FI" else "fails" if sign == "below FI" else "not refuted" if L > -1 else "undecided"
row("metrics.h15.sign", h["sign"], sign)
row("metrics.h15.margin", h["margin"], margin)
row("metrics.h15.prior", h["prior"], prior)
qm = cell_row("metrics.h15.qualifier.cells[convention M]", h["qualifier"]["cells"]["convention M"], ANY["TRUNC-0/M"], ANY["FI"])
qn = cell_row("metrics.h15.qualifier.cells[not-constant denominator]", h["qualifier"]["cells"]["not-constant denominator"], ANY["TRUNC-0"][~const], ANY["FI"][~const])
trig = [name for name, q in (("convention M", qm), ("not-constant denominator", qn))
        if (q["ci95"][0] > 0 or q["ci95"][1] < 0) and point != 0 and q["difference"] != 0 and (q["difference"] > 0) != (point > 0)]
row("metrics.h15.qualifier.triggered_by", h["qualifier"]["triggered_by"], trig)
row("metrics.h15.qualifier.convention_dependent", h["qualifier"]["convention_dependent"], bool(trig))
row("metrics.h15.words", h["words"], "convention-dependent" if trig else None)
cell_row("metrics.h15.beside[convention P]", h["beside"]["convention P"], ANY["TRUNC-0/P"], ANY["FI"])
row("metrics.h15.beside.mean_per_cut_rate_difference", h["beside"]["mean_per_cut_rate_difference"], mean_ci(RATE["TRUNC-0"] - RATE["FI"]))
for name, q in (("convention M", qm), ("not-constant denominator", qn)):
    lo, hi = 100 * q["ci95"][0], 100 * q["ci95"][1]
    mine_only(f"the labels of H15 read on the qualifier cell [{name}] (never deciding)",
              ("above FI" if lo > 0 else "below FI" if hi < 0 else "not separated from FI") + "; "
              + ("within 1 point" if lo > -1 else "by more than 1 point" if hi < -1 else "1-point margin not resolved"))
# two other intervals for the deciding cell, as a sanity check of method 10 (never registered)
t = dec["table"]
se = math.sqrt(t["b"] + t["c"] - (t["b"] - t["c"]) ** 2 / n) / n
mine_only("deciding cell, Wald interval for paired proportions, points", [100 * (dec["difference"] - Z * se), 100 * (dec["difference"] + Z * se)])
rng_ = np.random.default_rng(424242)
dvec = ANY["TRUNC-0"].astype(float) - ANY["FI"].astype(float)
boots = np.array([dvec[rng_.integers(0, n, n)].mean() for _ in range(4000)])
mine_only("deciding cell, percentile bootstrap over leaks (4000 resamples, my seed), points", [float(100 * np.percentile(boots, 2.5)), float(100 * np.percentile(boots, 97.5))])
mine_only("deciding cell split by constancy: TRUNC-0 caught, FI caught, leaks, among the leaks constant at the compared rows of the 16 cuts",
          [int(ANY["TRUNC-0"][const].sum()), int(ANY["FI"][const].sum()), int(const.sum())])
mine_only("distance of the upper limit of the deciding interval from -1 point", U + 1)

# --- the cut-date bootstrap -------------------------------------------------------------------------------------------
boot, cfg = M["cut_date_bootstrap"], header["config"]
long_cuts = header["cuts"]["long"]
dates = np.array([c["open_time"][:10] for c in long_cuts])
uniq = np.unique(dates)
per_pair = {p: sorted({c["open_time"][:10] for c in long_cuts if c["pair"] == p}) for p in header["pairs"]}
row("metrics.cut_date_bootstrap.dates", boot["dates"], int(uniq.size))
row("long schedule: every pair holds the same dates", True, all(x == list(uniq) for x in per_pair.values()))


def spread(seed, subsets):
    rng = np.random.default_rng(seed)
    diffs = np.empty(subsets)
    tr, fi = V["TRUNC-0/G@long"], V["FI@long"]
    for s in range(subsets):
        cols = np.isin(dates, rng.choice(uniq, size=cfg["bootstrap_dates"], replace=False))
        diffs[s] = 100.0 * (tr[:, cols].any(axis=1).mean() - fi[:, cols].any(axis=1).mean())
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return float(lo), float(hi), diffs


lo, hi, diffs = spread(cfg["bootstrap_seed"], cfg["bootstrap_subsets"])
row("metrics.cut_date_bootstrap.percentiles_points", boot["percentiles_points"], [lo, hi])
row("metrics.cut_date_bootstrap.spread_points", boot["spread_points"], hi - lo)
row("metrics.cut_date_bootstrap.wider_than_margin", boot["wider_than_margin"], bool(hi - lo > 1.0))
row("metrics.cut_date_bootstrap.subsets / dates_per_subset", [boot["subsets"], boot["dates_per_subset"]], [cfg["bootstrap_subsets"], cfg["bootstrap_dates"]])
mine_only("cut-date bootstrap: min, median, max of the 2000 differences, points", [float(diffs.min()), float(np.median(diffs)), float(diffs.max())])
mine_only("cut-date bootstrap: share of the 2000 subsets with a difference below 0, below -1 point", [float((diffs < 0).mean()), float((diffs < -1).mean())])
lo2, hi2, d2 = spread(97531, 20000)
mine_only("cut-date bootstrap with another seed (97531, 20000 subsets): percentiles, spread, points", [lo2, hi2, hi2 - lo2])
mine_only("long schedule, all 64 dates: TRUNC-0 minus FI, any cut, points", 100.0 * (ANY["TRUNC-0/G@long"].mean() - ANY["FI@long"].mean()))

# --- the placement-invariant subset, the descriptive counts, the replications -----------------------------------------
for name, m in (("invariant", inv), ("complement", ~inv)):
    sub = M["placement_invariant_subset"][name]
    row(f"metrics.placement_invariant_subset[{name}].leaks", sub["leaks"], int(m.sum()))
    share_row(f"metrics.placement_invariant_subset[{name}].FI_any_cut", sub["FI_any_cut"], int(ANY["FI"][m].sum()), int(m.sum()))
    q = cell_row(f"metrics.placement_invariant_subset[{name}].TRUNC-0_minus_FI", sub["TRUNC-0_minus_FI"], ANY["TRUNC-0"][m], ANY["FI"][m], with_table=False)
    mine_only(f"placement-invariant subset [{name}]: the 2x2 table of TRUNC-0 against FI", q["table"])
share_row("metrics.descriptive.constant_h1_cuts", M["descriptive"]["constant_h1_cuts"], int(const.sum()), n)
share_row("metrics.descriptive.constant_both_schedules", M["descriptive"]["constant_both_schedules"], int(const_both.sum()), n)
read_only("metrics.descriptive.distinct_expressions", M["descriptive"]["distinct_expressions"], "the expressions are not in verdicts.jsonl")
share_row("metrics.replications[FI any cut]", M["replications"]["FI any cut"], int(ANY["FI"].sum()), n)
share_row("metrics.replications[SHUFFLE any cut]", M["replications"]["SHUFFLE any cut"], int(ANY["SHUFFLE"].sum()), n)

# --- mirror asymmetry (section 4.9) ---------------------------------------------------------------------------------------
w = np.flatnonzero(has_mirror)
two_cols = [labels["TWO-RUN@h1"].index(x) for x in ("s0.1-r1", "s0.1-r2")]
mlabels = {e["key"]: e["run_labels"] for e in header["layout"]["mirror"]}
row("mirror layout: the run labels equal those of the flags for each key", True, all(mlabels[k] == labels[k] for k in mlabels))
for name, key, cols in (("FI", "FI@h1", None), ("TRUNC-0", "TRUNC-0/G@h1", None), ("TRUNC-1", "TRUNC-1/G@h1", None), ("RETILE", "RETILE/G@ends", None),
                        ("TWO-RUN", "TWO-RUN@h1", two_cols), ("SHUFFLE", "SHUFFLE@h1", None)):
    own, mir = FL[key][w], MR[key][w]
    if cols is not None:
        own, mir = own[:, :, cols], mir[:, :, cols]
    oc, mc = own.any(axis=2), mir.any(axis=2)
    got = M["mirror_asymmetry"][name]
    row(f"metrics.mirror_asymmetry[{name}].leaks", got["leaks"], int(w.size))
    share_row(f"metrics.mirror_asymmetry[{name}].any_cut", got["any_cut"], int((oc.any(axis=1) != mc.any(axis=1)).sum()), int(w.size))
    for j in range(oc.shape[1]):
        share_row(f"metrics.mirror_asymmetry[{name}].per_cut[{j}]", got["per_cut"][j], int((oc[:, j] != mc[:, j]).sum()), int(w.size))

# --- the per-leak strings of detectors.json --------------------------------------------------------------------------
wrong = 0
for i, leak in enumerate(M["leaks"]):
    for d in PRIMARY:
        wrong += leak[d] != "".join("X" if x else "." for x in V[d][i])
    wrong += (leak["invariant"] != bool(inv[i])) + (leak["constant_h1_cuts"] != bool(const[i])) + (leak["family"] != fam[i]) + (leak["id"] != i)
row("metrics.leaks (per-leak strings and tags that differ from verdicts.jsonl)", 0, int(wrong))

# --- identities the file can show on its own -------------------------------------------------------------------------
A = res["assertions"]
for c in "GMP":
    row(f"assertion 2.4 (RETILE equals windowed TRUNC-0): (leak, end) cells where RETILE/{c} differs from ENDS/{c}", 0, int((FL[f"RETILE/{c}@ends"] != FL[f"ENDS/{c}@ends"]).sum()))
    row(f"the same under the sensitivity rule, {c}", 0, int((FN[f"RETILE/{c}@ends"] != FN[f"ENDS/{c}@ends"]).sum()))
row("finite within flags: raw cells set under the sensitivity rule and not under the catch rule of H1", 0, int(sum(int((FN[k] & ~FL[k]).sum()) for k in FL)))
pa = res["reported"]["p_assertion"]
for part, keys in (("TRUNC-0", ("TRUNC-0/P@h1", "TRUNC-0/P@long")), ("TRUNC-1", ("TRUNC-1/P@h1", "TRUNC-1/P@long")), ("ENDS", ("ENDS/P@ends",))):
    row(f"reported.p_assertion: {part}/P cells not flagged (the exception cuts, since none is flagged inside and none missed outside)",
        pa[f"p-exception-cuts:{part}"] - pa[f"p-flagged-inside-the-exception:{part}"] + pa[f"p-not-flagged-outside-the-exception:{part}"],
        int(sum(int((~FL[k]).sum()) for k in keys)))
mine_only("leaks by designed tag", {x: int((designed == x).sum()) for x in sorted(set(designed))})
mine_only("leaks by family", {f: int((fam == f).sum()) for f in families})
mine_only("leaks by output", {x: col["output"].count(x) for x in sorted(set(col["output"]))})
mine_only("constant leaks caught by TRUNC-0/G, TRUNC-0/M, FI, SHUFFLE, TWO-RUN, then the number of constant leaks",
          [int(ANY[k][const].sum()) for k in ("TRUNC-0/G", "TRUNC-0/M", "FI", "SHUFFLE", "TWO-RUN")] + [int(const.sum())])

# --- reported.classes and the controls: read from detectors.json, checked for the registered equalities ---------------
C = res["reported"]["classes"]
for name, block in C.items():
    if "under P" in name:
        for det, v_ in block.items():
            row(f"reported.classes[{name}][{det}]: flagged == cuts - cannot_flag_last_row", v_["flagged"], v_["cuts"] - v_["cannot_flag_last_row"])
    elif name.startswith("M2 FI"):
        read_only(f"reported.classes[{name}]", block, "the verdicts of the hand-written classes are not in verdicts.jsonl")
    else:
        read_only(f"reported.classes[{name}]", block, "reported only; the count ORs every run column of the raw key")
for name, a in A.items():
    read_only(f"assertions[{name}]", {k: v for k, v in a.items() if k in ("pass", "violations")}, "the count of an assertion")
read_only("gates", res["gates"], "the 50-leak gates")
read_only("reported.honest_twins", res["reported"]["honest_twins"], "the verdicts of the twins are not in verdicts.jsonl")
read_only("all_pass", res["all_pass"], "the flag of the run")
rs = M["read_split"]
bad_split = 0
for d, block in rs.items():
    for k, v_ in block.items():
        bad_split += v_["through_a_missing_read"]["count"] + v_["through_a_changed_value"]["count"] != v_["flagged_rows"]
        if k.startswith(("TRUNC", "RETILE")):
            bad_split += v_["through_a_changed_value"]["count"] != 0
row("metrics.read_split: rows whose two parts do not sum to flagged_rows, or truncation rows with a changed-value catch (internal consistency only)", 0, int(bad_split))

TAB, NL = chr(9), chr(10)
lines = [TAB.join(("path", "run", "mine", "verdict"))] + [TAB.join(json.dumps(x, sort_keys=True) if not isinstance(x, str) else x for x in r) for r in ROWS]
out_path.write_text(NL.join(lines) + NL, encoding="utf-8")
counts = {v: sum(1 for r in ROWS if r[3] == v) for v in ("agree", "DISAGREE", "mine only", "read")}
print(folder.name, counts, "rows:", len(ROWS))
for r in ROWS:
    if r[3] == "DISAGREE":
        print("DISAGREE", r[0], "| run:", json.dumps(r[1])[:300], "| mine:", json.dumps(r[2])[:300])
