"""Pass 5b-bis, Y2b: a scratch copy of wave4.py carrying the guards this pass asks for, to show that Y2 still runs
on a fixed wave4.py. It is a sketch for the orchestrator, not the fix: the repository file is read, never written.

Guards added to the copy: refuse when the log or an output folder of the date exists (Minor 1); log HEAD, and after
each step require the commit and the code digest recorded in the output to be those of step 0 (Major 1); run the
digest command before the replay and require the registered development digest (N5).

Run from python/:
    uv run --no-sync python ../.claude/briefs/iteration-5/audit-5b-bis-scripts/y2b_guarded_copy.py SCRATCH_FILE
"""
import sys
from pathlib import Path

from olsprime.paths import REPO_ROOT

src = (REPO_ROOT / ".claude" / "briefs" / "iteration-5" / "wave4.py").read_text(encoding="utf-8")
dst = Path(sys.argv[1]).resolve()
assert REPO_ROOT.resolve() not in dst.parents, "the copy goes to scratch, never to the repository"


def patch(text: str, anchor: str, new: str, *, before: bool = False) -> str:
    assert text.count(anchor) == 1, anchor
    return text.replace(anchor, new + anchor if before else anchor + new)


out = patch(src, '    logf = RUNS / f"{a.date}-wave4.log"\n', '''    folders = ("h1-adversary-replay", "detectors-descriptive", "detectors-confirmatory", "detectors-confirmatory-rerun")
    taken = [p.name for p in (logf, *(RUNS / f"{a.date}-{f}" for f in folders)) if p.exists()]
    if taken:
        print(f"STOP: {', '.join(taken)} exist already: an earlier attempt of this date. Take another --date and report the attempt (7.4)")
        return 2
''')
out = patch(out, "    from olsprime.bench.provenance import code_digest\n", "    from olsprime.bench.provenance import git_commit\n    from olsprime.bench.detectors import REGISTERED_DEVELOPMENT_DIGEST\n")
out = patch(out, '''        log(logf, "STOP: the official runs are made on Windows AMD64 only")
        return 2
''', '''    commit = git_commit()
    log(logf, f"HEAD {commit}")

    def unchanged(folder: Path, name: str) -> bool:
        p = json.loads((folder / name).read_text(encoding="utf-8")).get("provenance", {})
        ok = p.get("git_commit") == commit and p.get("code", {}).get("sha256") == digest
        if not ok:
            log(logf, f"STOP: {folder.name}/{name} records another commit or code digest than step 0 (7.3)")
        return ok

    pin = ["-m", "olsprime.bench.detectors", "digest", "--seed", "51118", "--placement", "quantile", "--table", TABLE]
    printed = (RUNS / f"{logf.stem}-pin.out").read_text(encoding="utf-8").split() if run(logf, "pin", pin) == 0 else []
    if printed[:1] != [REGISTERED_DEVELOPMENT_DIGEST]:
        log(logf, "STOP: the development digest does not reproduce here; no bar was read")
        return 2
''')
out = patch(out, '    common = ["-m", "olsprime.bench.detectors", "run"', '    if not unchanged(replay, "adversary.json"):\n        return 1\n', before=True)
out = patch(out, "    confirmatory = [*common,", '    if not unchanged(descriptive, "detectors.json"):\n        return 1\n', before=True)
out = patch(out, '    rerun = RUNS / f"{a.date}-detectors-confirmatory-rerun"\n', '    if not unchanged(first, "detectors.json"):\n        return 1\n', before=True)
out = patch(out, "    names = sorted(p.name for p in first.iterdir()", '    if rc == 0 and not unchanged(rerun, "detectors.json"):\n        return 1\n', before=True)
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(out, encoding="utf-8", newline="\n")
print("written", dst, "|", len(out.splitlines()), "lines against", len(src.splitlines()))
