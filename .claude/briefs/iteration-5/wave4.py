"""Wave 4 of iteration 5: the official runs, unattended, on Windows (docs/PROTOCOL.md, change log of 2026-11-19).

Run from ``python/``::

    uv run --no-sync python ../.claude/briefs/iteration-5/wave4.py --frozen-digest <code digest> [--date YYYY-MM-DD]

Steps, each only if every step before it passed; the first failure stops the script (§7.3, §7.4):

0. nothing of an earlier attempt exists for this date (the log, the ``.out`` files, the four output folders): a second
   attempt takes another ``--date`` and leaves the first one's files where they are (pass 5b-bis, Minor 1);
   the platform is Windows AMD64; the code digest equals the frozen one; HEAD is logged;
0b. the ``digest`` command reproduces the registered development digest, before any bar is read (pass 5b-bis, N5);
1. §1.3's replay: H1's adversary on seed 20261029 again; its ``adversary.json`` must equal iteration 3's on every
   top-level key but ``provenance`` (parsed, ``provenance`` removed, re-serialised with sorted keys, bytes compared);
2. the descriptive run (seed 20261029): exit code 0 and ``all_pass``;
3. the confirmatory run (seed 20261118): exit code 0 and ``all_pass``;
4. its identity rerun, ``--workers 4``: every output file but ``run.json`` equal byte for byte.

After steps 1 to 4, the output's ``provenance`` must record step 0's commit and code digest, or the script stops
(pass 5b-bis, Major 1): nothing is committed, and nothing under the digest's globs is edited, while it runs.

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
from typing import Any

PYTHON_DIR = Path(__file__).resolve().parents[3] / "python"
RUNS = PYTHON_DIR.parent / "runs"
TABLE = "../runs/2026-11-18-quantile-table/table.json"
SAVED_ADVERSARY = RUNS / "2026-10-29-h1-adversary" / "adversary.json"


def log(path: Path, line: str) -> None:
    stamped = f"{datetime.now(UTC).isoformat(timespec='seconds')} {line}"
    print(stamped, flush=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(stamped + "\n")


def run(logf: Path, name: str, args: list[str]) -> tuple[int, str]:
    log(logf, f"START {name}: python {' '.join(args)}")
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}  # a piped child on Windows would write cp1252
    proc = subprocess.run([sys.executable, *args], cwd=PYTHON_DIR, env=env, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")  # fmt: skip
    (RUNS / f"{logf.stem}-{name}.out").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr, encoding="utf-8")
    log(logf, f"END {name}: exit {proc.returncode}; {proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else '(no stdout)'}")
    return proc.returncode, proc.stdout


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def without_provenance(d: dict[str, Any]) -> bytes:
    d = {k: v for k, v in d.items() if k != "provenance"}
    return json.dumps(d, indent=2, sort_keys=True, default=str).encode("utf-8")


def provenance_moved(d: dict[str, Any], commit: str | None, digest: str) -> str | None:
    """None when the output records step 0's commit and code digest; otherwise what moved (pass 5b-bis, Major 1)."""
    prov = d.get("provenance") or {}
    got_commit, got_digest = prov.get("git_commit"), (prov.get("code") or {}).get("sha256")
    if got_commit != commit or got_digest != digest:
        return f"the output records commit {got_commit} and code digest {got_digest}, not step 0's {commit} and {digest}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frozen-digest", required=True)
    ap.add_argument("--date", default=f"{datetime.now(UTC):%Y-%m-%d}")
    a = ap.parse_args()
    logf = RUNS / f"{a.date}-wave4.log"
    replay = RUNS / f"{a.date}-h1-adversary-replay"
    descriptive = RUNS / f"{a.date}-detectors-descriptive"
    first = RUNS / f"{a.date}-detectors-confirmatory"
    rerun = RUNS / f"{a.date}-detectors-confirmatory-rerun"

    # Step 0: an earlier attempt of this date is never run over (pass 5b-bis, Minor 1). Nothing is written here.
    earlier = [p for p in (logf, replay, descriptive, first, rerun) if p.exists()] + sorted(RUNS.glob(f"{logf.stem}-*.out"))
    if earlier:
        print(f"REFUSED: an earlier attempt of {a.date} left {', '.join(p.name for p in earlier)}; "
              "a new attempt takes another --date, and is reported as run after a stopped attempt (§7.4)", flush=True)  # fmt: skip
        return 2

    sys.path.insert(0, str(PYTHON_DIR))
    from olsprime.bench.detectors import REGISTERED_DEVELOPMENT_DIGEST
    from olsprime.bench.provenance import code_digest, git_commit

    digest, commit = code_digest()["sha256"], git_commit()
    log(logf, f"platform {platform.system()} {platform.machine()} Python {platform.python_version()}; HEAD {commit}; code digest {digest}")
    if (platform.system(), platform.machine()) != ("Windows", "AMD64"):
        log(logf, "STOP: the official runs are made on Windows AMD64 only")
        return 2
    if digest != a.frozen_digest:
        log(logf, f"STOP: the code digest is not the frozen one ({a.frozen_digest})")
        return 2

    # Step 0b: the development digest, before any bar is read (pass 5b-bis, N5). The command prints; we compare.
    rc, out = run(logf, "pin", ["-m", "olsprime.bench.detectors", "digest", "--seed", "51118", "--placement", "quantile",
                                "--n", "10000", "--table", TABLE])  # fmt: skip
    printed = out.split()[0] if out.split() else ""
    if rc != 0 or printed != REGISTERED_DEVELOPMENT_DIGEST:
        log(logf, f"STOP: the development digest is {printed or '(none)'}, not the registered {REGISTERED_DEVELOPMENT_DIGEST}")
        return 2
    log(logf, "OK the development digest reproduces")

    def checked(name: str, rc: int, path: Path) -> dict[str, Any] | None:
        """The step's output, or None after a logged STOP: exit code, file present, provenance unmoved."""
        if rc != 0:
            log(logf, f"STOP: {name} exited {rc}")
            return None
        d = load_json(path)
        if d is None:
            log(logf, f"STOP: {name} exited 0 but {path.name} is missing or unreadable")
            return None
        moved = provenance_moved(d, commit, digest)
        if moved is not None:
            log(logf, f"STOP: {name}: {moved} (§7.3: one frozen commit for every run)")
            return None
        return d

    # Step 1: §1.3's replay.
    rc, _ = run(logf, "adversary-replay", ["-m", "olsprime.bench.adversary", "--n", "10000", "--workers", "8", "--out", str(replay)])
    got = checked("the adversary replay", rc, replay / "adversary.json")
    if got is None:
        return 1
    saved = load_json(SAVED_ADVERSARY)
    if saved is None or without_provenance(got) != without_provenance(saved):
        log(logf, "STOP: the replay's adversary.json differs from iteration 3's outside provenance (§1.3)")
        return 1
    log(logf, "OK §1.3: adversary.json equals iteration 3's on every key but provenance; data manifest digest "
              f"{(got.get('provenance') or {}).get('manifest_digest')} (iteration 3: {(saved.get('provenance') or {}).get('manifest_digest')})")  # fmt: skip

    # Step 2: the descriptive run, the registered line as the dated line writes it.
    rc, _ = run(logf, "descriptive", ["-m", "olsprime.bench.detectors", "run", "--seed", "20261029", "--placement", "h1-bands",
                                      "--two-run-seed", "29119", "--bootstrap-seed", "29120", "--n", "10000", "--table", TABLE,
                                      "--workers", "8", "--out", str(descriptive)])  # fmt: skip
    d = checked("the descriptive run", rc, descriptive / "detectors.json")
    if d is None or not d.get("all_pass"):
        log(logf, "STOP: the descriptive run did not pass every assertion and gate; the confirmatory run is not made (§7.3)")
        return 1
    log(logf, "OK the descriptive run passed every assertion and gate")

    # Step 3: the confirmatory run.
    confirmatory = ["-m", "olsprime.bench.detectors", "run", "--seed", "20261118", "--placement", "quantile", "--two-run-seed", "20261119",
                    "--bootstrap-seed", "20261120", "--n", "10000", "--table", TABLE]  # fmt: skip
    rc, _ = run(logf, "confirmatory", [*confirmatory, "--workers", "8", "--out", str(first)])
    d = checked("the confirmatory run", rc, first / "detectors.json")
    if d is None or not d.get("all_pass"):
        log(logf, "STOP: the confirmatory run did not pass every assertion and gate (§7.4)")
        return 1
    log(logf, "OK the confirmatory run passed every assertion and gate")

    # Step 4: the identity rerun.
    rc, _ = run(logf, "confirmatory-rerun", [*confirmatory, "--workers", "4", "--out", str(rerun)])
    if checked("the identity rerun", rc, rerun / "detectors.json") is None:
        return 1
    names = sorted(p.name for p in first.iterdir() if p.name != "run.json")
    same = names == sorted(p.name for p in rerun.iterdir() if p.name != "run.json") and all(
        (first / n).read_bytes() == (rerun / n).read_bytes() for n in names
    )
    log(logf, f"{'OK' if same else 'STOP: MISMATCH in the'} identity rerun: {', '.join(names)} compared byte for byte")
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
