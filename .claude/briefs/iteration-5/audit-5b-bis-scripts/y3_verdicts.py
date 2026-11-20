"""Pass 5b-bis, Y3: verdicts.jsonl decoded by the English description in its header, with no olsprime import, and the
numbers of detectors.json recomputed from it (a finished synthetic run of the final tree; reads no bar).

Checked: the deciding cell of H15 and both qualifier cells (table, difference, Newcombe method 10 written again), the
any-cut shares and the sensitivity under the three denominators, the family and position tables, the first-m curve,
the union, its misses and the long-schedule class, the placement-invariant subset, the cut-date bootstrap, the
sentence of the conventions, and the per-leak strings of detectors.json.

Run:  python y3_verdicts.py RUN_FOLDER      (any Python with numpy; no olsprime import)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

folder = Path(sys.argv[1])
result = json.loads((folder / "detectors.json").read_text(encoding="utf-8"))
M = result["metrics"]
lines = (folder / "verdicts.jsonl").read_text(encoding="utf-8").splitlines()
header = json.loads(lines[0])
assert header["format"] == "olsprime-detector-verdicts/1" and header["leaks"] == len(lines) - 1
assert header["config"] == result["config"], "the config of the header is not the config of the run"
F = header["fields"]


def bits_of(hexed, layout):
    raw = bytes.fromhex(hexed)
    out = {}
    for e in layout:
        a = np.zeros((e["cuts"], e["runs"]), dtype=bool)
        for cut in range(e["cuts"]):
            for run in range(e["runs"]):
                i = e["offset"] + cut * e["runs"] + run
                a[cut, run] = (raw[i // 8] >> (i % 8)) & 1  # packbits, little bit order
        out[e["key"]] = a
    total = sum(e["cuts"] * e["runs"] for e in layout)
    assert len(raw) == (total + 7) // 8 and all(not (raw[i // 8] >> (i % 8)) & 1 for i in range(total, 8 * len(raw)))
    return out


rows = []
for line in lines[1:]:
    rec = dict(zip(F, json.loads(line), strict=True))
    rec["flags"] = bits_of(rec["flags"], header["layout"]["flags"])
    rec["finite"] = bits_of(rec["finite"], header["layout"]["finite"])
    rec["mirror"] = None if rec["mirror"] is None else bits_of(rec["mirror"], header["layout"]["mirror"])
    rows.append(rec)
n = len(rows)
assert [r["id"] for r in rows] == list(range(n))
labels = {e["key"]: e["run_labels"] for e in header["layout"]["flags"]}
shape = {e["key"]: (e["cuts"], e["runs"]) for e in header["layout"]["flags"]}
assert shape["FI@h1"] == (16, 2) and shape["FI@long"] == (128, 2) and shape["TWO-RUN@h1"] == (16, 16) and shape["SHUFFLE@h1"] == (16, 8)
assert shape["TRUNC-0/G@h1"] == (16, 1) and shape["RETILE/G@ends"] == (28, 1) and len(header["cuts"]["h1"]) == 16
assert len(header["cuts"]["long"]) == 128 and len(header["cuts"]["ends"]) == 28


def var(key, wanted, part="flags"):  # (leaks, cuts): OR over the named runs
    cols = [labels[key].index(w) for w in wanted]
    return np.stack([r[part][key][:, cols].any(axis=1) for r in rows])


def registered(part="flags"):  # the registered variants, written from the protocol (section 2), not from the header
    v = {}
    for s, sfx in (("h1", ""), ("long", "@long")):
        v["FI" + sfx] = var(f"FI@{s}", ["x3", "/3"], part)
        v["FI x3" + sfx] = var(f"FI@{s}", ["x3"], part)
        v["FI /3" + sfx] = var(f"FI@{s}", ["/3"], part)
        for d in ("TRUNC-0", "TRUNC-1"):
            for c in "GMP":
                v[f"{d}/{c}{sfx}"] = var(f"{d}/{c}@{s}", ["truncated"], part)
        for sig in ("0.1", "1"):
            for k in (1, 2, 8):
                v[f"TWO-RUN s{sig} r{k}{sfx}"] = var(f"TWO-RUN@{s}", [f"s{sig}-r{r}" for r in range(1, k + 1)], part)
    for k in (1, 2, 8):
        v[f"SHUFFLE k{k}"] = var("SHUFFLE@h1", [f"twin-{j}" for j in range(k)], part)
    for c in "GMP":
        v[f"RETILE/{c}@ends"] = var(f"RETILE/{c}@ends", ["tile"], part)
        v[f"ENDS/{c}@ends"] = var(f"ENDS/{c}@ends", ["truncated"], part)
    v["TRUNC-0"], v["TWO-RUN"], v["SHUFFLE"] = v["TRUNC-0/G"], v["TWO-RUN s0.1 r2"], v["SHUFFLE k8"]
    return v


v, vf = registered(), registered("finite")
for name, spec in header["variants"].items():  # the variants named by the header must say the same
    assert np.array_equal(var(spec["key"], spec["runs"]), v[name]), name
assert set(header["variants"]) == set(v)
anyc = {k: x.any(axis=1) for k, x in v.items()}
const = np.array([bool(r["constant_h1_cuts"]) for r in rows])
const_both = np.array([bool(r["constant_both_schedules"]) for r in rows])
inv = np.array([bool(r["placement_invariant"]) for r in rows])
fam = np.array([r["family"] for r in rows])
pos = np.array([r["position"] for r in rows])
den = {"all": np.ones(n, bool), "not-constant": ~const, "designed-no": np.array([r["designed"] == "no" for r in rows])}
Z = 1.959963984540054
checks = 0


def wilson(k, m):
    p = k / m
    d = 1 + Z * Z / m
    mid, half = (p + Z * Z / (2 * m)) / d, Z * math.sqrt(p * (1 - p) / m + Z * Z / (4 * m * m)) / d
    return mid - half, mid + half


def newcombe(a, b, c, d):
    m = a + b + c + d
    p1, p2 = (a + b) / m, (a + c) / m
    l1, u1 = wilson(a + b, m)
    l2, u2 = wilson(a + c, m)
    dd = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    A = a * d - b * c
    phi = 0.0 if dd == 0 else (A - m / 2) / dd if A > m / 2 else 0.0 if A >= 0 else A / dd
    dl, du, el, eu = p1 - l1, u1 - p1, p2 - l2, u2 - p2
    return p1 - p2, p1 - p2 - math.sqrt(dl * dl - 2 * phi * dl * eu + eu * eu), p1 - p2 + math.sqrt(du * du - 2 * phi * du * el + el * el)


def close(x, y, tol=1e-12):
    return (x is None and y is None) or (x is not None and y is not None and abs(x - y) <= tol)


def same_share(got, k, m, where):
    global checks
    checks += 1
    assert got["count"] == k and got["n"] == m, (where, got, k, m)
    if m:
        lo, hi = wilson(k, m)
        assert close(got["share"], k / m) and close(got["wilson95"][0], lo, 1e-9) and close(got["wilson95"][1], hi, 1e-9), where
    else:
        assert got["share"] is None and got["wilson95"] == [None, None], where


def same_cell(got, x, y, where):
    global checks
    checks += 1
    t = {"a": int((x & y).sum()), "b": int((x & ~y).sum()), "c": int((~x & y).sum()), "d": int((~x & ~y).sum())}
    if "table" in got:
        assert got["table"] == t, (where, got["table"], t)
    th, lo, hi = newcombe(**t)
    assert close(got["difference"], th) and close(got["ci95"][0], lo, 1e-9) and close(got["ci95"][1], hi, 1e-9), (where, got, th, lo, hi)
    return th, lo, hi


h = M["h15"]
th, lo, hi = same_cell(h["deciding_cell"], anyc["TRUNC-0"], anyc["FI"], "deciding")
assert "table" in h["deciding_cell"]
cells = h["qualifier"]["cells"]
assert set(cells) == {"convention M", "not-constant denominator"} and all("table" in c for c in cells.values())
qm = same_cell(cells["convention M"], anyc["TRUNC-0/M"], anyc["FI"], "qualifier M")
qn = same_cell(cells["not-constant denominator"], anyc["TRUNC-0"][~const], anyc["FI"][~const], "qualifier not-constant")
sign = "above FI" if lo > 0 else "below FI" if hi < 0 else "not separated from FI"
trig = [name for name, (qt, ql, qh) in (("convention M", qm), ("not-constant denominator", qn))
        if (ql > 0 or qh < 0) and th != 0 and qt != 0 and (qt > 0) != (th > 0)]
assert h["sign"] == sign and h["qualifier"]["triggered_by"] == trig and h["qualifier"]["convention_dependent"] == bool(trig)
print(f"H15 deciding {100*th:+.2f} [{100*lo:+.2f}, {100*hi:+.2f}] sign {sign!r}; qualifier M {100*qm[0]:+.2f} [{100*qm[1]:+.2f}, {100*qm[2]:+.2f}], "
      f"not-constant {100*qn[0]:+.2f} [{100*qn[1]:+.2f}, {100*qn[2]:+.2f}]; triggered {trig}")
same_cell(h["beside"]["convention P"], anyc["TRUNC-0/P"], anyc["FI"], "beside P")

names = [k for k in v if "@" not in k or k.endswith("@ends")]
assert set(M["detectors"]) == set(names) == set(M["ignores_outputs_that_turn_missing"])
families = sorted(set(fam))
strata = {"inside": pos == "inside", "outside": pos == "outside", "other": ~np.isin(pos, ["inside", "outside"])}
for k in names:
    for d, m in den.items():
        same_share(M["detectors"][k]["any_cut"][d], int(anyc[k][m].sum()), int(m.sum()), (k, d))
        same_share(M["ignores_outputs_that_turn_missing"][k][d], int(vf[k].any(axis=1)[m].sum()), int(m.sum()), ("finite", k, d))
        assert set(M["detectors"][k]["by_family"][d]) == set(families)
        for f in families:
            same_share(M["detectors"][k]["by_family"][d][f], int(anyc[k][m & (fam == f)].sum()), int((m & (fam == f)).sum()), (k, d, f))
        assert set(M["detectors"][k]["by_position"][d]) == set(strata)
        for s, sm in strata.items():
            same_share(M["detectors"][k]["by_position"][d][s], int(anyc[k][m & sm].sum()), int((m & sm).sum()), (k, d, s))
        mr = M["detectors"][k]["mean_per_cut_rate"][d]
        assert close(mr["mean"], float(v[k][m].mean(axis=1).mean()) if m.any() else None, 1e-12), (k, d)
    assert not (vf[k] & ~v[k]).any(), k  # a finite move above 1e-9 is a catch under the rule of H1 too
print("any-cut, sensitivity, families, positions, mean rates: agree for", len(names), "variants x 3 denominators;", {d: int(m.sum()) for d, m in den.items()})

h1 = header["cuts"]["h1"]
order = sorted(range(16), key=lambda j: (h1[j]["open_time"], header["pairs"].index(h1[j]["pair"])))
assert header["pairs"] == ["BTCUSDT", "ETHUSDT"]
for k in ("FI", "TRUNC-0", "TWO-RUN", "SHUFFLE", "TRUNC-1/G"):
    for d, m in den.items():
        curve = M["first_m_cuts"][k][d]
        assert [c["m"] for c in curve] == [1, 2, 4, 8, 16]
        for c in curve:
            same_share(c, int(v[k][:, order[: c["m"]]].any(axis=1)[m].sum()), int(m.sum()), ("curve", k, d, c["m"]))
for det_, key in (("TRUNC-0", "TRUNC-0/{}"), ("TRUNC-1", "TRUNC-1/{}"), ("RETILE", "RETILE/{}@ends")):
    for d, m in den.items():
        for c in "GMP":
            same_share(M["conventions"][det_][d][c], int(anyc[key.format(c)][m].sum()), int(m.sum()), ("conv", det_, d, c))
for d, m in den.items():
    s = [float(anyc[f"TRUNC-0/{c}"][m].mean()) for c in "GMP"]
    sent = M["conventions"]["sentence"][d]
    assert close(sent["X"], min(s)) and close(sent["Y"], max(s)) and sent["G_to_M"] == sorted(s[:2]), d
print("first-m curves and conventions (three denominators): agree")

union = anyc["FI"] | anyc["TRUNC-0"] | anyc["TWO-RUN"] | anyc["SHUFFLE"]
long4 = anyc["FI@long"] | anyc["TRUNC-0/G@long"] | anyc["TRUNC-1/G@long"] | anyc["TWO-RUN s0.1 r2@long"]
same_share(M["union"]["primary"], int(union.sum()), n, "union")
same_share(M["union"]["over both schedules"], int((union | long4 | anyc["TRUNC-1/G"]).sum()), n, "union both")
um = M["union_misses"]
assert um["count"] == int((~union).sum()) and um["caught_by_a_secondary_arm"]["long schedule"] == int((~union & long4).sum())
assert um["caught_by_a_secondary_arm"]["TRUNC-1"] == int((~union & anyc["TRUNC-1/G"]).sum())
assert um["constant_h1_cuts"] == int((~union & const).sum()) and um["constant_both_schedules"] == int((~union & const_both).sum())
for d_ in ("FI", "TRUNC-0", "TWO-RUN", "SHUFFLE"):
    same_share(M["missed_by_detector_among_union"][d_], int((union & ~anyc[d_]).sum()), int(union.sum()), ("missed", d_))
for name, m in (("invariant", inv), ("complement", ~inv)):
    sub = M["placement_invariant_subset"][name]
    assert sub["leaks"] == int(m.sum())
    same_share(sub["FI_any_cut"], int(anyc["FI"][m].sum()), int(m.sum()), ("subset", name))
    if m.any():
        same_cell(sub["TRUNC-0_minus_FI"], anyc["TRUNC-0"][m], anyc["FI"][m], ("subset cell", name))
print("union", int(union.sum()), "misses", um["count"], "long-schedule class", um["caught_by_a_secondary_arm"]["long schedule"],
      "| invariant subset", int(inv.sum()), "of", n)

boot = M["cut_date_bootstrap"]
cfg = header["config"]
if boot is not None:
    dates = np.array([c["open_time"][:10] for c in header["cuts"]["long"]])
    uniq = np.unique(dates)
    per_pair = {p: sorted({c["open_time"][:10] for c in header["cuts"]["long"] if c["pair"] == p}) for p in header["pairs"]}
    assert len(uniq) == 64 and all(x == list(uniq) for x in per_pair.values())
    rng = np.random.default_rng(cfg["bootstrap_seed"])
    diffs = []
    for _ in range(cfg["bootstrap_subsets"]):
        cols = np.isin(dates, rng.choice(uniq, size=cfg["bootstrap_dates"], replace=False))
        assert cols.sum() == 16
        diffs.append(100.0 * (v["TRUNC-0/G@long"][:, cols].any(axis=1).mean() - v["FI@long"][:, cols].any(axis=1).mean()))
    lo_, hi_ = np.percentile(diffs, [2.5, 97.5])
    assert close(boot["percentiles_points"][0], float(lo_), 1e-9) and close(boot["percentiles_points"][1], float(hi_), 1e-9)
    assert close(boot["spread_points"], float(hi_ - lo_), 1e-9) and boot["wider_than_margin"] == bool(hi_ - lo_ > 1.0)
    print(f"cut-date bootstrap: {lo_:+.2f} to {hi_:+.2f} points over {len(diffs)} subsets of {cfg['bootstrap_dates']} of {len(uniq)} dates: agrees")
for i, leak in enumerate(M["leaks"]):
    for d_ in ("FI", "TRUNC-0", "TWO-RUN", "SHUFFLE"):
        assert leak[d_] == "".join("X" if x else "." for x in v[d_][i]), (i, d_)
    assert leak["invariant"] == bool(inv[i]) and leak["constant_h1_cuts"] == bool(const[i]) and leak["family"] == fam[i]
with_m = [r for r in rows if r["mirror"] is not None]
for name, key, cols in (("FI", "FI@h1", None), ("TRUNC-0", "TRUNC-0/G@h1", None), ("RETILE", "RETILE/G@ends", None), ("SHUFFLE", "SHUFFLE@h1", None),
                        ("TWO-RUN", "TWO-RUN@h1", [labels["TWO-RUN@h1"].index(x) for x in ("s0.1-r1", "s0.1-r2")])):
    own = np.stack([(r["flags"][key] if cols is None else r["flags"][key][:, cols]).any(axis=1) for r in with_m])
    mir = np.stack([(r["mirror"][key] if cols is None else r["mirror"][key][:, cols]).any(axis=1) for r in with_m])
    same_share(M["mirror_asymmetry"][name]["any_cut"], int((own.any(axis=1) != mir.any(axis=1)).sum()), len(with_m), ("mirror", name))
print("per-leak strings of detectors.json and the mirror asymmetry (", len(with_m), "single comparisons ): agree")
print("NaN tokens in detectors.json:", (folder / "detectors.json").read_text(encoding="utf-8").count("NaN"))
print("shares and cells checked:", checks, "| Y3 OK")
