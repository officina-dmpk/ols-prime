"""Wave 4 of iteration 5: the official runs, unattended, on Windows (docs/PROTOCOL.md, change log of 2026-11-19).

Run from ``python/``::

    uv run --no-sync python ../.claude/briefs/iteration-5/wave4.py --frozen-digest <code digest> [--date YYYY-MM-DD]

Steps, each only if every step before it passed; the first failure stops the script (§7.3, §7.4):

0. the code digest equals the frozen one, and the platform is Windows AMD64;
1. §1.3's replay: H1's adversary on seed 20261029 again; its ``adversary.json`` must equal iteration 3's on every
   top-level key but ``provenance`` (parsed, ``provenance`` removed, re-serialised with sorted keys, bytes compared);
2. the descriptive run (seed 20261029): exit code 0 and ``all_pass``;
3. the confirmatory run (seed 20261118): exit code 0 and ``all_pass``;
4. its identity rerun, ``--workers 4``: every output file but ``run.json`` equal byte for byte.

Each step's start and end (UTC) go to ``runs/<date>-wave4.log``, for the change log's list of contacts. The detectors'
own CLI refuses any other real-bar run, checks the platform pin before it reads a bar, and holds every rate back until
all its assertions pass.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parents[3] / "python"
RUNS = PYTHON_DIR.parent / "runs"
TABLE = "../runs/2026-11-18-quantile-table/table.json"
SAVED_ADVERSARY = RUNS / "2026-10-29-h1-adversary" / "adversary.json"


def log(path: Path, line: str) -> None:
    stamped = f"{datetime.now(UTC).isoformat(timespec='seconds')} {line}"
    print(stamped, flush=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(stamped + "\n")


def run(logf: Path, name: str, args: list[str]) -> int:
    log(logf, f"START {name}: python {' '.join(args)}")
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}  # a piped child on Windows would write cp1252
    proc = subprocess.run([sys.executable, *args], cwd=PYTHON_DIR, env=env, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")  # fmt: skip
    (RUNS / f"{logf.stem}-{name}.out").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr, encoding="utf-8")
    log(logf, f"END {name}: exit {proc.returncode}; {proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else '(no stdout)'}")
    return proc.returncode


def without_provenance(path: Path) -> bytes:
    d = json.loads(path.read_text(encoding="utf-8"))
    d.pop("provenance", None)
    return json.dumps(d, indent=2, sort_keys=True, default=str).encode("utf-8")


def all_pass(out: Path) -> bool:
    return bool(json.loads((out / "detectors.json").read_text(encoding="utf-8")).get("all_pass"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frozen-digest", required=True)
    ap.add_argument("--date", default=f"{datetime.now(UTC):%Y-%m-%d}")
    a = ap.parse_args()
    logf = RUNS / f"{a.date}-wave4.log"
    sys.path.insert(0, str(PYTHON_DIR))
    from olsprime.bench.provenance import code_digest

    digest = code_digest()["sha256"]
    log(logf, f"platform {platform.system()} {platform.machine()} Python {platform.python_version()}; code digest {digest}")
    if digest != a.frozen_digest:
        log(logf, f"STOP: the code digest is not the frozen one ({a.frozen_digest})")
        return 2
    if (platform.system(), platform.machine()) != ("Windows", "AMD64"):
        log(logf, "STOP: the official runs are made on Windows AMD64 only")
        return 2

    replay = RUNS / f"{a.date}-h1-adversary-replay"
    if run(logf, "adversary-replay", ["-m", "olsprime.bench.adversary", "--n", "10000", "--workers", "8", "--out", str(replay)]) != 0:
        log(logf, "STOP: the adversary replay failed")
        return 1
    if without_provenance(replay / "adversary.json") != without_provenance(SAVED_ADVERSARY):
        log(logf, "STOP: the replay's adversary.json differs from iteration 3's outside provenance (§1.3)")
        return 1
    log(logf, "OK §1.3: adversary.json equals iteration 3's on every key but provenance")

    common = ["-m", "olsprime.bench.detectors", "run", "--n", "10000", "--table", TABLE]
    descriptive = RUNS / f"{a.date}-detectors-descriptive"
    rc = run(logf, "descriptive", [*common, "--seed", "20261029", "--placement", "h1-bands", "--two-run-seed", "29119",
                                   "--bootstrap-seed", "29120", "--workers", "8", "--out", str(descriptive)])  # fmt: skip
    if rc != 0 or not all_pass(descriptive):
        log(logf, "STOP: the descriptive run did not pass every assertion and gate; the confirmatory run is not made (§7.3)")
        return 1

    confirmatory = [*common, "--seed", "20261118", "--placement", "quantile", "--two-run-seed", "20261119", "--bootstrap-seed", "20261120"]
    first = RUNS / f"{a.date}-detectors-confirmatory"
    rc = run(logf, "confirmatory", [*confirmatory, "--workers", "8", "--out", str(first)])
    if rc != 0 or not all_pass(first):
        log(logf, "STOP: the confirmatory run did not pass every assertion and gate (§7.4)")
        return 1

    rerun = RUNS / f"{a.date}-detectors-confirmatory-rerun"
    rc = run(logf, "confirmatory-rerun", [*confirmatory, "--workers", "4", "--out", str(rerun)])
    names = sorted(p.name for p in first.iterdir() if p.name != "run.json")
    same = rc == 0 and names == sorted(p.name for p in rerun.iterdir() if p.name != "run.json") and all(
        (first / n).read_bytes() == (rerun / n).read_bytes() for n in names
    )
    log(logf, f"{'OK' if same else 'MISMATCH'} identity rerun: {', '.join(names)} compared byte for byte")
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
