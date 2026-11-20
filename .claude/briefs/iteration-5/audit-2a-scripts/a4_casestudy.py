"""Audit phase 2a, A4: what casestudy.json lets one recompute, the labels, and the cross-checks with the JSON reports
of Reports 2 and 3. Reads JSON and Markdown outputs only: no series.npz array, no bar, no olsprime import.

Run:  python a4_casestudy.py RUNS_DIR
"""
import json
import math
import sys
from pathlib import Path

from scipy import stats as st

runs = Path(sys.argv[1])
folder = runs / "2026-11-19-casestudy"
TAG = " (exploratory, test months)"
cs = json.loads((folder / "casestudy.json").read_text(encoding="utf-8"))
checks, bad = 0, []


def ok(cond, what):
    global checks
    checks += 1
    if not cond:
        bad.append(what)


def near(a, b, tol=1e-12):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


# labels
for name in ("casestudy.json", "config.json", "run.json"):
    keys = list(json.loads((folder / name).read_text(encoding="utf-8")))
    ok(all(k.endswith(TAG) for k in keys), f"{name}: a top-level key without the label: {keys}")
md = (folder / "casestudy.md").read_text(encoding="utf-8").splitlines()
heads = [x for x in md if x.startswith("#")]
tables = [md[i] for i in range(len(md) - 1) if md[i].startswith("|") and md[i + 1].startswith("|---")]
ok(all("exploratory, test months" in x for x in heads), f"a heading without the label: {heads}")
ok(all("exploratory, test months" in x for x in tables), "a table header without the label")
print("headings", len(heads), "tables", len(tables), "| top-level keys of casestudy.json:", len(cs))

cfg, inp, split, control = (cs[k + TAG] for k in ("config", "inputs", "skill_split", "factor_control"))
ok(cfg == {"hac_lags": 168, "min_year_hours": 100, "momentum_bars": 24, "volatility_bars": 90}, "config")
ok(cs["registered" + TAG] is True, "registered")
T = inp["hours"]

# the factor control
for name, c in control.items():
    ok(c["hac"] == {"kernel": "bartlett", "lags": 168} and c["hours"] == T, f"{name}: hac or hours")
    means = {f: c["payoffs"][f]["mean"] for f in c["payoffs"]}
    sds = {f: c["payoffs"][f]["std"] for f in c["payoffs"]}
    fs = ["reversal", "momentum", "vol_timed_momentum"]
    explained = sum(c["coefficients"][f]["estimate"] * means[f] for f in fs)
    ok(near(c["explained"], explained), f"{name}: explained")
    ok(near(c["mean_difference"], c["intercept"] + explained, 1e-10), f"{name}: mean = intercept + explained")
    ok(near(c["share_left"], c["intercept"] / c["mean_difference"]), f"{name}: share_left")
    ok(c["intercept"] == c["coefficients"]["intercept"]["estimate"], f"{name}: intercept twice")
    for coef, v in c["coefficients"].items():
        ok(near(v["t"], v["estimate"] / v["hac_se"]), f"{name}.{coef}: t")
        ok(near(v["p"], 2 * st.t.sf(abs(v["t"]), df=T - 4), 1e-9), f"{name}.{coef}: p")
        if coef in sds:
            ok(near(v["per_std"], v["estimate"] * sds[coef]), f"{name}.{coef}: per_std")
    var_d = []
    for j, f in enumerate(fs):
        one = c["alone"][f]
        ok(near(one["t"], one["estimate"] / one["hac_se"]), f"{name}.alone.{f}: t")
        ok(near(one["p"], 2 * st.t.sf(abs(one["t"]), df=T - 2), 1e-9), f"{name}.alone.{f}: p")
        ok(near(one["share_left"], one["intercept"] / c["mean_difference"]), f"{name}.alone.{f}: share_left")
        ok(near(c["mean_difference"], one["intercept"] + one["estimate"] * means[f], 1e-10), f"{name}.alone.{f}: mean = intercept + slope x mean")
        # normal equations: slope_alone_j sd_j = sum_k rho_jk beta_k sd_k
        rhs = sum(c["payoff_correlation"][j][k] * c["coefficients"][g]["per_std"] for k, g in enumerate(fs))
        ok(near(one["estimate"] * sds[f], rhs, 1e-8), f"{name}.alone.{f}: slope against the joint fit and the correlations ({one['estimate'] * sds[f]} vs {rhs})")
        var_d.append((one["estimate"] * sds[f]) ** 2 / one["r2"])
    ok(max(var_d) / min(var_d) - 1 < 1e-6, f"{name}: the three single fits imply three variances of the difference {var_d}")
    r2 = sum(c["coefficients"][f]["per_std"] * c["alone"][f]["estimate"] * sds[f] for f in fs) / var_d[0]
    ok(near(c["r2"], r2, 1e-6), f"{name}: joint R2 {c['r2']} vs {r2}")
    print(name, "| mean", round(c["mean_difference"], 6), "intercept", round(c["intercept"], 6), "share left", round(c["share_left"], 4), "R2", round(c["r2"], 4),
          "| mean / HAC se:", round(c["mean_difference"] / c["mean_difference_hac_se"], 2), "| sd of the difference", round(math.sqrt(var_d[0]), 5))

# the split
P = split["periods"]
years = [p for p in P if p != "all"]
for key in ("hours", "direction_hours", "rows", "moving_rows"):
    ok(sum(P[y][key] for y in years) == P["all"][key], f"periods: {key} does not sum")
ok(P["all"]["rows"] == inp["rows"] and P["all"]["hours"] == T, "periods: all against inputs")
for p in P.values():
    ok(near(p["share_moving"], p["moving_rows"] / p["rows"]), "share_moving")
    ok(p["last_hour"] < "2025-01-01" and p["first_hour"] >= "2019-01-01", "an hour outside 2019-2024")
clim3 = {}
for arm, by in split["arms"].items():
    for period, e in by.items():
        ok("too_few_hours" not in e, f"{arm} {period}: too few hours")
        for target in ("move", "direction"):
            t = e[target]
            for metric, base in (("brier", "brier_skill"), ("log_loss", "log_loss_skill")):
                ok(near(t[base]["estimate"], 1 - t[metric] / t[metric + "_climatology"], 1e-10), f"{arm} {period} {target} {metric}: skill")
                ok(t[base]["low"] <= t[base]["estimate"] <= t[base]["high"] and t[base]["n_boot"] == 2000, f"{arm} {period} {target} {metric}: interval")
        g = e["log_loss_gain"]
        ok(near(g["move"]["estimate"], e["move"]["log_loss_climatology"] - e["move"]["log_loss"], 1e-10), f"{arm} {period}: move gain")
        ok(abs(g["total"] - g["move"]["estimate"] - g["direction"]["estimate"]) < 1e-12 and g["parts_gap"] < 1e-12, f"{arm} {period}: parts")
        ok((e["hours"], e["direction_hours"], e["rows"], e["moving_rows"]) == tuple(P[period][k] for k in ("hours", "direction_hours", "rows", "moving_rows")), f"{arm} {period}: counts")
        clim3.setdefault(period, []).append(g["total"] / e["three_class"]["log_loss_skill"])
    for target, wkey in (("move", "hours"), ("direction", "direction_hours")):
        for metric in ("brier", "log_loss", "brier_climatology", "log_loss_climatology"):
            pooled = sum(P[y][wkey] * by[y][target][metric] for y in years) / P["all"][wkey]
            ok(near(by["all"][target][metric], pooled, 1e-10), f"{arm} {target} {metric}: the years do not pool to all")
for period, vals in clim3.items():
    ok(max(vals) / min(vals) - 1 < 1e-9, f"{period}: the arms imply different three-class climatology log-losses {vals}")

# the two analyses against each other, and against the reports
A = split["arms"]
ok(near(-control["matrix-select - climatology-panel"]["mean_difference"], A["matrix-select"]["all"]["log_loss_gain"]["total"], 1e-10), "matrix-select: gain against the mean difference")
ok(near(-control["enc-ols - enc-softmax"]["mean_difference"], A["enc-ols"]["all"]["log_loss_gain"]["total"] - A["enc-softmax"]["all"]["log_loss_gain"]["total"], 1e-9), "enc: gains against the mean difference")
r2j = json.loads((runs / "2026-10-30-report2-wsl" / "report2.json").read_text(encoding="utf-8"))
r3j = json.loads((runs / "2026-10-30-report3" / "report3.json").read_text(encoding="utf-8"))
for arm, rep in (("matrix-select", r2j), ("enc-ols", r3j), ("enc-softmax", r3j)):
    ok(near(A[arm]["all"]["three_class"]["brier_skill"], rep["arms"][arm]["bss"]["estimate"]), f"{arm}: three-class Brier skill against its report")
    print(arm, "three-class Brier skill", A[arm]["all"]["three_class"]["brier_skill"], "| report:", rep["arms"][arm]["bss"]["estimate"])
ok(near(clim3["all"][0], r2j["arms"]["climatology-panel"]["log_loss"]["estimate"], 1e-9), f"climatology log-loss {clim3['all'][0]} against Report 2")
ok(r2j["series"]["sha256"] == inp["report2_series_sha256"] and r3j["series"]["sha256"] == inp["report3_series_sha256"] and r3j["report2"]["series_sha256"] == inp["report2_series_sha256"], "digests")
print("checks:", checks, "| failed:", len(bad))
for b in bad:
    print("FAILED", b)
