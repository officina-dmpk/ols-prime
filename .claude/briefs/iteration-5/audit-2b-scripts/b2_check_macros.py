"""Audit 2b, B2: every macro that main.tex uses, checked against the source its comment names.

Usage: python b2_check_macros.py <repo root> <used-macros.tsv from B1> <out.tsv>

Three kinds of check, each with its own code (nothing is imported from paper/make_numbers.py):

- "mine": a macro read from a detectors.json path is compared with the value that audit 2a
  recomputed from verdicts.jsonl (the "mine" column of its table), found by the map below
  from the JSON path to the row name of the table. The unit (share x 100, points as stored,
  integer, p-value) is decided here from the name of the key, never fitted to the macro.
- "json": where the table of the audit has no recomputed value (rows it only read, the repair
  statistics of TWO-RUN, the case study), the JSON file is read again by the walk and format below.
- "line": a macro read from a line of RESULTS.md, PROTOCOL.md, HYPOTHESES.md or the findings of
  audit 2a: the "matched" fragment must occur on the cited line of the cited file, and the raw
  text of the macro inside that fragment. This shows the source exists as cited; whether the
  sentence that uses the macro means what the source says was read by eye (findings file).

Reads docs, the two tables and the findings of audit 2a, and three JSON files named below; no bar,
no per-leak file, nothing under runs/vault. A backslash is written \x5c in patterns.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

root, used_path, out_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
BRIEFS = root / ".claude" / "briefs" / "iteration-5"
JSONS = {
    "runs/2026-11-19-detectors-confirmatory/detectors.json": "conf",
    "runs/2026-11-19-detectors-descriptive/detectors.json": "desc",
    "runs/2026-11-19-casestudy/casestudy.json": "case",
}
TABLES = {"conf": BRIEFS / "audit-2a-scripts" / "table-confirmatory.tsv",
          "desc": BRIEFS / "audit-2a-scripts" / "table-descriptive.tsv"}

_json: dict[str, object] = {}
_table: dict[str, dict[str, tuple[str, str, str]]] = {}


def load_json(rel: str) -> object:
    if "vault" in rel:
        raise SystemExit("refused: " + rel)
    if rel not in _json:
        _json[rel] = json.loads((root / rel).read_text(encoding="utf-8"))
    return _json[rel]


def table(run: str) -> dict[str, tuple[str, str, str]]:
    if run not in _table:
        rows = {}
        for line in TABLES[run].read_text(encoding="utf-8").splitlines()[1:]:
            c = line.split("\t")
            rows[c[0]] = (c[1], c[2], c[3])
        _table[run] = rows
    return _table[run]


def row_and_rest(p: list[str]) -> tuple[str, list[str]] | None:
    """The map of this script from a detectors.json path to the row name of the audit table."""
    if p[:2] == ["metrics", "detectors"] and p[3] in ("any_cut", "mean_per_cut_rate"):
        return f"metrics.detectors[{p[2]}].{p[3]}[{p[4]}]", p[5:]
    if p[:2] == ["metrics", "h15"]:
        if p[2] in ("difference_points", "ci95_points"):
            return f"metrics.h15.{p[2]}", p[3:]
        if p[2] == "deciding_cell" and p[3] == "mcnemar_exact_p":
            return "metrics.h15.deciding_cell.mcnemar_exact_p", []
        if p[2] == "deciding_cell":
            return "metrics.h15.deciding_cell (table, difference, ci95, psi, n)", p[3:]
        if p[2] == "qualifier" and p[3] == "cells":
            return f"metrics.h15.qualifier.cells[{p[4]}]", p[5:]
        if p[2] == "beside" and p[3] == "mean_per_cut_rate_difference":
            return "metrics.h15.beside.mean_per_cut_rate_difference", p[4:]
        if p[2] == "beside":
            return f"metrics.h15.beside[{p[3]}]", p[4:]
    if p[:2] == ["metrics", "placement_invariant_subset"]:
        return f"metrics.placement_invariant_subset[{p[2]}].{p[3]}", p[4:]
    if p[:2] == ["metrics", "cut_date_bootstrap"]:
        if p[2] == "subsets":
            return "metrics.cut_date_bootstrap.subsets / dates_per_subset", ["0"]
        if p[2] == "dates_per_subset":
            return "metrics.cut_date_bootstrap.subsets / dates_per_subset", ["1"]
        return f"metrics.cut_date_bootstrap.{p[2]}", p[3:]
    if p[:2] == ["metrics", "union"]:
        return f"metrics.union[{p[2]}]", p[3:]
    if p[:2] == ["metrics", "union_misses"]:
        if p[2] == "caught_by_a_secondary_arm":
            return f"metrics.union_misses.caught_by_a_secondary_arm[{p[3]}]", p[4:]
        return f"metrics.union_misses.{p[2]}", p[3:]
    if p[:2] == ["metrics", "missed_by_detector_among_union"]:
        return f"metrics.missed_by_detector_among_union[{p[2]}]", p[3:]
    if p[:2] in (["metrics", "pairs"], ["metrics", "equal_run_counts"]):
        return f"metrics.{p[1]}[{p[2]}].{p[3]}", p[4:]
    if p[:2] == ["metrics", "mirror_asymmetry"]:
        return f"metrics.mirror_asymmetry[{p[2]}].{p[3]}", p[4:]
    if p[:2] == ["metrics", "ignores_outputs_that_turn_missing"]:
        return f"metrics.ignores_outputs_that_turn_missing[{p[2]}][{p[3]}]", p[4:]
    if p[:3] == ["metrics", "conventions", "sentence"]:
        return f"metrics.conventions.sentence[{p[3]}]", p[4:]
    if p[:2] == ["metrics", "descriptive"]:
        return f"metrics.descriptive.{p[2]}", p[3:]
    return None


def walk(obj: object, rest: list[str]) -> object:
    for step in rest:
        obj = obj[int(step)] if isinstance(obj, list) else obj[step]  # type: ignore[index]
    return obj


INTS = ("count", "leaks", "b", "c", "subsets", "dates_per_subset", "dates", "evaluated", "bars", "n_boot",
        "hours", "direction_hours", "lags", "SHUFFLE", "TWO-RUN", "predicted_flagged", "flagged",
        "constant_h1_cuts", "constant_both_schedules")


def unit_of(path: list[str]) -> str:
    """Decided from the names in the path, before the value of the macro is looked at."""
    last = path[-1] if not path[-1].isdigit() else path[-2]
    if last in INTS or "caught_by_a_secondary_arm" in path:
        return "int"
    if last in ("difference_points", "ci95_points", "percentiles_points", "spread_points"):
        return "points"
    if last == "mcnemar_exact_p":
        return "p"
    if last in ("share", "wilson95", "mean", "ci95", "difference", "X", "Y", "G_to_M", "share_left"):
        return "x100"
    return "as-is"


def number(text: str) -> float:
    t = text.replace(",", "").lstrip("<")
    m = re.fullmatch(r"([-+]?[0-9.]+)x10\^\{(-?[0-9]+)\}", t)
    if m:
        return float(m.group(1)) * 10 ** int(m.group(2))
    m = re.fullmatch(r"10\^\{(-?[0-9]+)\}", t)
    if m:
        return 10.0 ** int(m.group(1))
    return float(t)


def decimals(text: str) -> int:
    t = text.replace(",", "").lstrip("+-")
    return len(t.split(".")[1]) if "." in t else 0


def agrees(shown: str, source: object, unit: str) -> bool:
    if unit == "int":
        return isinstance(source, int) and not isinstance(source, bool) and int(shown.replace(",", "")) == source
    x = float(source)  # type: ignore[arg-type]
    if unit == "p":
        if shown.startswith("<"):
            return x < number(shown)
        if "x10" in shown:
            return abs(number(shown) - x) <= 0.05 * 10 ** math.floor(math.log10(x)) * 1.0000001
        return abs(number(shown) - x) <= 0.5 * 10 ** -decimals(shown) * 1.0000001
    if unit == "x100":
        x *= 100
    return abs(number(shown) - x) <= 0.5 * 10 ** -decimals(shown) * 1.0000001


results = []
for line in used_path.read_text(encoding="utf-8").splitlines()[1:]:
    name, shown, raw, lines, src = line.split("\t")
    first = src.split(" || ")[0]
    kind, verdict, detail = "?", "NOT CHECKED", ""
    m = re.match(r"(runs/[^ ]+\.json) : (.*)$", first)
    if m:
        rel, path = m.group(1), m.group(2).split(" / ")
        run = JSONS[rel]
        unit = unit_of(path)
        mapped = row_and_rest(path) if run in TABLES else None
        source, kind = None, "json"
        if mapped and mapped[0] in table(run):
            run_col, mine_col, v = table(run)[mapped[0]]
            if v in ("agree", "DISAGREE"):
                text = re.sub(r" \(log10 p = [-0-9.]+\)$", "", mine_col)
                try:
                    source, kind = walk(json.loads(text), mapped[1]), "mine"
                    detail = f"table row <{mapped[0]}> ({v})"
                except (ValueError, KeyError, IndexError, TypeError):
                    source = None
        if source is None:
            source = walk(load_json(rel), path)
            detail = "read again from " + rel
        verdict = "agree" if agrees(shown, source, unit) else "DISAGREE"
        detail += f"; unit {unit}; source {source!r}"
    elif ".tsv:" in first:
        mt = re.match(r"(.*\.tsv):(\d+), row .(.*)., column .(\w+).(?:, element \[(\d+)\])?$", first)
        rel, lineno, row, column, element = mt.groups()
        cells = (root / rel).read_text(encoding="utf-8").splitlines()[int(lineno) - 1].split("\t")
        value = json.loads(cells[{"run": 1, "mine": 2}[column]])
        if element is not None:
            value = value[int(element)]
        kind = "audit table"
        size = abs(abs(number(shown)) - abs(float(value))) <= 0.5 * 10 ** -decimals(shown) * 1.0000001
        ok = cells[0] == row and cells[3] == "mine only" and size
        verdict = "agree" if ok else "DISAGREE"
        detail = f"{rel}:{lineno} ({cells[3]}); source {value!r}"
    else:
        ml = re.match(r"(\S+):(\d+), (?:row|line)", first)
        matched = [s for s in src.split(" || ") if s.startswith("matched: ")]
        if ml and matched:
            rel, lineno = ml.group(1), int(ml.group(2))
            text = (root / rel).read_text(encoding="utf-8").splitlines()[lineno - 1]
            frag = matched[0][len("matched: "):]
            ascii_line = "".join(c if ord(c) < 128 else f"<U+{ord(c):04X}>" for c in text)
            kind = "line"
            verdict = "agree" if frag in ascii_line and raw in frag else "DISAGREE"
            detail = f"{rel}:{lineno}"
    results.append((name, shown, kind, verdict, lines, detail))

with out_path.open("w", encoding="utf-8") as fh:
    fh.write("macro\tshown\tcheck\tverdict\tlines of main.tex\tdetail\n")
    for r in results:
        fh.write("\t".join(r) + "\n")

print("macros used in main.tex:", len(results))
for (kind, verdict), n in sorted(Counter((r[2], r[3]) for r in results).items()):
    print(f"  {kind:12s} {verdict:12s} {n}")
for r in results:
    if r[3] != "agree":
        print("  !!", r)
