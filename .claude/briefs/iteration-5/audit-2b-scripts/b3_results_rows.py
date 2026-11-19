"""Audit 2b, B3: the numbers of the rows of 2026-11-19 in docs/RESULTS.md.

Usage: python b3_results_rows.py <repo root>

Every number printed in a row is looked up, by absolute value, in three sets built here:
(1) every number of the two tables of audit 2a (both columns), as a share x 100, as points and
as stored, rounded to 0, 1, 2, 3 and 4 decimals; (2) the same for every number of casestudy.json;
(3) every number on the dated lines of 2026-11-19 in docs/PROTOCOL.md and in the Minors of the
findings of audit 2a. A number found nowhere is printed, to be read by hand. This catches a typo;
it does not show that a number sits beside the right label (that was read by eye).
Reads no bar and no per-leak file.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
briefs = root / ".claude" / "briefs" / "iteration-5"
known: set[str] = set()


def add(x: float) -> None:
    for scale in (1.0, 100.0):
        for d in range(0, 7):
            known.add(f"{abs(x) * scale:.{d}f}")


def collect(obj: object) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            collect(v)
    elif isinstance(obj, list):
        for v in obj:
            collect(v)


NUM = re.compile(r"(?<![\w.])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:e-?\d+)?")
for name in ("table-confirmatory.tsv", "table-descriptive.tsv"):
    for line in (briefs / "audit-2a-scripts" / name).read_text(encoding="utf-8").splitlines()[1:]:
        for cell in line.split("\t")[1:3]:
            try:
                collect(json.loads(re.sub(r" \(log10 p = [-0-9.]+\)$", "", cell)))
            except ValueError:
                for tok in NUM.findall(cell):
                    add(float(tok.replace(",", "")))
collect(json.loads((root / "runs/2026-11-19-casestudy/casestudy.json").read_text(encoding="utf-8")))
text_known: set[str] = set()
for path, keep in ((root / "docs/PROTOCOL.md", lambda s: s.lstrip().startswith("- 2026-11-19") or s.startswith("  ")),
                   (briefs / "audit-2a-findings.md", lambda s: True)):
    for line in path.read_text(encoding="utf-8").splitlines():
        if keep(line):
            text_known.update(t.replace(",", "") for t in NUM.findall(line))

rows = [l for l in (root / "docs/RESULTS.md").read_text(encoding="utf-8").splitlines() if l.startswith("| 2026-11-19")]
print("rows of 2026-11-19:", len(rows))
for row in rows:
    cells = [c.strip() for c in row.split("|")[1:-1]]
    toks = NUM.findall(row)
    missing = []
    for tok in toks:
        t = tok.replace(",", "")
        if "e" in t:
            ok = t in text_known or any(abs(float(t) - float(k)) <= 0.06 * float(t) for k in text_known if "e-" in k)
        else:
            ok = t in known or t in text_known
        if not ok:
            missing.append(tok)
    print(f"- {cells[1][:60]}: {len(toks)} numbers, {len(missing)} found nowhere: {missing}")
