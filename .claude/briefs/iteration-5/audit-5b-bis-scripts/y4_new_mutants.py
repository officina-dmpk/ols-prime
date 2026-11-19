"""Pass 5b-bis, Y4: five new mutants, planted in the code the fix wave added, on temporary copies of python/.

The repository is never written: the harness of tests/test_detector_mutants.py is imported and reused as it is
(file-by-file copy to a scratch folder, pytest.main in a fresh spawned process, the marker test, the JUnit report),
with another table of mutants. The detector test modules run against each copy. A survivor shows a new assertion or
metric whose wiring no test checks. Synthetic bars and development seeds only, as in those tests.

Run from python/:  uv run --no-sync python ../.claude/briefs/iteration-5/audit-5b-bis-scripts/y4_new_mutants.py SCRATCH_DIR
"""
import multiprocessing
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest

NEW = {
    # Minor 6: the assertion of M1 under P counts nothing
    "n1_m1_under_p_never_counted": ("DET", '        bad[f"M1 {schedule} under P"] = wrong\n', '        bad[f"M1 {schedule} under P"] = 0\n'),
    # Minor 5: FI on M2 is never asserted, even where the rule predicts a flag
    "n2_fi_on_m2_never_counted": ("DET", "                count += int((predicted & ~fi).sum())\n", "                count += 0\n"),
    # Minor 10: the read-split row of the primary arm of TWO-RUN takes all 8 runs
    "n3_split_primary_arm_is_8_runs": ("DET", "if s == b.two_run_runs[0][0] and k <= 2]  # §4.4, Minor 10", "if s == b.two_run_runs[0][0] and k <= 8]  # §4.4, Minor 10"),
    # nit: can_flag counted over every cut of the bench again
    "n4_can_flag_over_every_cut": ("DET", "can_flag = {key: control_can_flag(leak, bench, h1_rows_of[key])", "can_flag = {key: control_can_flag(leak, bench)"),
    # Minor 6: a flag at a cut that cannot flag is never a disagreement, and a missed flag is never one either
    "n5_m1_under_p_missed_flags_not_counted": ("DET", "wrong += int((~flagged & ~cannot).sum() + (flagged & cannot).sum())", "wrong += int((flagged & cannot).sum())"),
}


def main(scratch: Path) -> int:
    import tests.test_detector_mutants as tm
    from olsprime.bench import provenance
    from olsprime.paths import REPO_ROOT

    assert REPO_ROOT.resolve() not in scratch.resolve().parents and not scratch.exists(), "a new scratch folder outside the repository"
    before = provenance.code_digest()
    tm.MUTANTS = {name: (tm.DET, old, new) for name, (_, old, new) in NEW.items()}
    for name, (rel, old, new) in tm.MUTANTS.items():
        assert tm._source(rel).count(old) == 1 and old != new, name
    copies = {name: tm._mutate(scratch / "mut", name) for name in tm.MUTANTS}
    spawn = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=3, mp_context=spawn, max_tasks_per_child=1) as pool:
        futures = {name: pool.submit(pytest.main, tm._args(copy, scratch / f"tmp-{name}")) for name, copy in copies.items()}
        codes = {name: int(f.result()) for name, f in futures.items()}
    for name, code in codes.items():
        first = tm._first_failure(scratch / f"tmp-{name}.xml")
        verdict = "killed  " if code == 1 and "test_the_copy_is_what_runs" not in first else "SURVIVED" if code == 0 else f"exit {code}"
        print(f"{verdict} {name}: {first}")
    assert provenance.code_digest() == before, "the repository moved"
    print("repository code digest unchanged:", before["sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
