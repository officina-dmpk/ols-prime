"""Audit 2b, B1: macros used against macros defined, digits typed in the prose, and a rendering.

Usage: python b1_macros_and_digits.py <main.tex> <numbers.tex> <out-dir>
Reads the two files, writes rendered.txt, used-macros.tsv and digits.txt into <out-dir>.
Reads nothing under runs/ or data/. A backslash is written \x5c in every pattern below.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BS = chr(92)
main_path, num_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out_dir.mkdir(parents=True, exist_ok=True)

# --- the macros, with the source comment above each ---------------------------------------------
defs: dict[str, tuple[str, str, str]] = {}  # name -> (value, raw, where)
where = ""
block: list[str] = []
for line in num_path.read_text(encoding="ascii").splitlines():
    if line.startswith("%"):
        block.append(line[1:].strip())
        continue
    m = re.match(r"\x5cnewcommand\{\x5cNum([A-Za-z]+)\}\{(.*)\}  % raw: (.*)$", line)
    if m:
        if block:
            where = " || ".join(block)
            block = []
        defs[m.group(1)] = (m.group(2), m.group(3), where)
    elif not line.strip():
        block = []


def plain(value: str) -> str:
    v = value.replace(BS + "textminus{}", "-").replace(BS + "ldots{}", "...")
    v = re.sub(r"\x5censuremath\{(.*)\}$", lambda m: m.group(1), v)
    v = re.sub(r"\x5ctexttt\{(.*)\}$", lambda m: m.group(1), v)
    return v.replace(BS + "times ", "x")


def strip_comment(line: str) -> tuple[str, str]:
    m = re.search(r"(?<!\x5c)%", line)
    return (line, "") if m is None else (line[: m.start()], line[m.start():])


lines = main_path.read_text(encoding="utf-8").splitlines()
used: dict[str, list[int]] = {}
rendered, digits = [], []
in_doc = False
for n, line in enumerate(lines, 1):
    body, comment = strip_comment(line)
    if BS + "begin{document}" in body:
        in_doc = True
    for m in re.finditer(r"\x5cNum([A-Za-z]+)", body):
        used.setdefault(m.group(1), []).append(n)
    text = re.sub(r"\x5cNum([A-Za-z]+)(\{\})?",
                  lambda m: "<<" + (plain(defs[m.group(1)][0]) if m.group(1) in defs else "UNDEFINED:" + m.group(1)) + ">>",
                  body)
    rendered.append(f"{n:5d}  {text}")
    if not in_doc:
        continue
    # digits typed by hand: drop the macros, then what is an identifier by construction
    bare = re.sub(r"\x5cNum[A-Za-z]+(\{\})?", "", body)
    bare = re.sub(r"\x5c(label|cref|Cref|ref|cite|citep|citet|input|bibliography|bibliographystyle|usepackage)\{[^}]*\}", "", bare)
    bare = re.sub(r"\x5c(code|path|url|texttt)\{[^{}]*\}", "", bare)
    bare = re.sub(r"\x5c(begin|end)\{[^}]*\}(\[[^\]]*\])?(\{[^}]*\})?", "", bare)
    bare = re.sub(r"\x5csetlength\{[^}]*\}\{[^}]*\}", "", bare)
    bare = re.sub(r"\x5c\x5c\[\d+pt\]", "", bare)
    bare = re.sub(r"p\{[\d.]+cm\}", "", bare)
    if re.search(r"\d", bare):
        digits.append(f"{n:5d}  {bare.strip()}")

(out_dir / "rendered.txt").write_text("\n".join(rendered) + "\n", encoding="utf-8")
(out_dir / "digits.txt").write_text("\n".join(digits) + "\n", encoding="utf-8")
with (out_dir / "used-macros.tsv").open("w", encoding="utf-8") as fh:
    fh.write("macro\tvalue\traw\tlines\tsource\n")
    for name in sorted(used):
        value, raw, src = defs.get(name, ("UNDEFINED", "", ""))
        fh.write(f"{name}\t{plain(value)}\t{raw}\t{','.join(map(str, used[name]))}\t{src}\n")

undefined = sorted(set(used) - set(defs))
unused = sorted(set(defs) - set(used))
print(f"defined {len(defs)}; used (distinct) {len(used)}; undefined {len(undefined)}; defined and unused {len(unused)}")
print("undefined:", undefined)
print(f"lines of the document body with a hand-typed digit: {len(digits)}")
