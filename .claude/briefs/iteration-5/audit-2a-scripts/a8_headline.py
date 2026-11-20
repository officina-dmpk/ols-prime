"""Audit phase 2a, A8: the rows of the two full tables that become rows or sentences, as Markdown.

Reads table-confirmatory.tsv and table-descriptive.tsv (written by A1) and prints one Markdown table per block:
JSON path, the value of the run, mine, agree. Shares in percent, differences in points, two decimals; the
comparison itself was made on the raw values (counts exactly, floats at 1e-9) and is copied from the full tables.

Run:  PYTHONUTF8=1 python a8_headline.py SCRIPTS_DIR   (UTF-8 output: the paths hold a section sign)
"""
import json
import sys
from pathlib import Path

here = Path(sys.argv[1])
T = {}
for run in ("confirmatory", "descriptive"):
    rows = {}
    for line in (here / f"table-{run}.tsv").read_text(encoding="utf-8").splitlines()[1:]:
        p, r, m, v = line.split(chr(9))
        rows[p] = (r, m, v)
    T[run] = rows


def val(s):
    try:
        return json.loads(s)
    except ValueError:
        return s


def pct(x):
    return f"{100 * x:.2f}"


def fmt(x):
    if isinstance(x, dict) and "count" in x:
        return f"{x['count']}/{x['n']}, {pct(x['share'])} % [{pct(x['wilson95'][0])}, {pct(x['wilson95'][1])}]"
    if isinstance(x, dict) and "difference" in x:
        t = x.get("table")
        tab = f"; a {t['a']}, b {t['b']}, c {t['c']}, d {t['d']}" if t else ""
        return f"{100 * x['difference']:+.2f} [{100 * x['ci95'][0]:+.2f}, {100 * x['ci95'][1]:+.2f}] points{tab}"
    if isinstance(x, dict) and "mean" in x:
        return f"{100 * x['mean']:+.2f} [{100 * x['ci95'][0]:+.2f}, {100 * x['ci95'][1]:+.2f}] points"
    if isinstance(x, dict) and "X" in x:
        return f"X {pct(x['X'])} %, Y {pct(x['Y'])} %, G to M {pct(x['G_to_M'][0])} % to {pct(x['G_to_M'][1])} %"
    if isinstance(x, float):
        return f"{x:.4g}"
    if isinstance(x, list) and x and all(isinstance(y, float) for y in x):
        return "[" + ", ".join(f"{y:+.2f}" for y in x) + "]"
    return json.dumps(x) if not isinstance(x, str) else x


def block(title, paths):
    print(f"**{title}**")
    print()
    print("| JSON path | confirmatory: the run | mine | descriptive: the run | mine |")
    print("|---|---|---|---|---|")
    for p in paths:
        cells = []
        for run in ("confirmatory", "descriptive"):
            r, m, v = T[run][p]
            if v == "agree":
                cells += [fmt(val(r)), "agree"]
            elif v == "mine only":
                cells += ["not in the run", fmt(val(m))]
            elif v == "read":
                cells += [fmt(val(r)), "read, not recomputed"]
            else:
                cells += [fmt(val(r)), "DISAGREE: " + fmt(val(m))]
        print(f"| `{p}` | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
    print()


dens = ("all", "not-constant", "designed-no")
names = ["FI", "FI x3", "FI /3", "TRUNC-0/G", "TRUNC-0/M", "TRUNC-0/P", "TRUNC-1/G", "TWO-RUN s0.1 r1", "TWO-RUN s0.1 r2", "TWO-RUN s0.1 r8", "TWO-RUN s1 r2",
         "SHUFFLE k1", "SHUFFLE k2", "SHUFFLE k8", "RETILE/G@ends", "RETILE/M@ends"]
block("Any-cut shares, three denominators (Wilson 95 %)", [f"metrics.detectors[{k}].any_cut[{d}]" for k in names for d in dens])
block("Sensitivity: ignores outputs that turn missing", [f"metrics.ignores_outputs_that_turn_missing[{k}][{d}]" for k in ("FI", "TRUNC-0/G", "TRUNC-0/M", "TRUNC-0/P", "TRUNC-1/G", "TWO-RUN s0.1 r2", "SHUFFLE k8", "RETILE/G@ends") for d in dens])
block("Conventions: the registered sentence", [f"metrics.conventions.sentence[{d}]" for d in dens])
keys = list(T["confirmatory"])
block("H15: the deciding cell, the labels, the qualifier, and what stands beside", [p for p in keys if p.startswith(("metrics.h15", "the labels of H15", "deciding cell", "distance of"))])
block("Pairs (section 4.7) and equal run counts (section 4.8)", [p for p in keys if p.startswith(("metrics.pairs[", "metrics.equal_run_counts[")) and not p.endswith((".b", ".c"))])
block("The union and its misses", [p for p in keys if p.startswith(("metrics.union[", "metrics.union_misses", "union misses", "metrics.missed_by"))])
block("The cut-date bootstrap", [p for p in keys if p.startswith(("metrics.cut_date_bootstrap", "cut-date bootstrap", "long schedule, all"))])
block("The placement-invariant subset, the counts, the replications", [p for p in keys if p.startswith(("metrics.placement_invariant", "placement-invariant", "metrics.descriptive", "metrics.replications", "leaks by", "constant leaks"))])
block("Mirror asymmetry, any cut", [p for p in keys if p.startswith("metrics.mirror_asymmetry") and p.endswith(".any_cut")])
block("The long schedule, any cut (the two other denominators are mine only)", [p for p in keys if "long_schedule[" in p and "any_cut" in p and p.split("[")[1].split("]")[0] in ("FI@long", "TRUNC-0/G@long", "TRUNC-0/M@long", "TRUNC-1/G@long", "TWO-RUN s0.1 r2@long")])
block("Classes, assertions, gates, twins (read from `detectors.json`)", [p for p in keys if p.startswith(("reported.", "assertions[", "gates", "all_pass", "assertion 2.4", "finite within"))])

# every row that differs, with the raw upper limits (the rounded form would hide the difference)
print("**Every row that differs (confirmatory run; the descriptive run has none)**")
print()
print("| JSON path | the run: mean, ci95 | mine: ci95 |")
print("|---|---|---|")
for p in keys:
    r, m, v = T["confirmatory"][p]
    if v == "DISAGREE":
        r, m = val(r), val(m)
        print(f"| `{p}` | {r['mean']!r}, {r['ci95']!r} | {m['ci95']!r} |")
assert not any(v == "DISAGREE" for _, _, v in T["descriptive"].values())
print()
