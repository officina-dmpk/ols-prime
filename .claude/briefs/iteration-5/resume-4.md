# Resume 4 — iteration 5 after wave 3, during audit pass 5b

- **Written:** 2026-11-19, by the orchestrator of iteration 5's third session. Updated at the end of the session (see "State at the end").
- **Abdou's instruction for this session** (relayed by the preparation session): stop once wave 3 and audit pass 5b are done. No official run on real data, no contact with seed 20261118, no wave 4, no paper. Ask Abdou before any commit; push nothing. Abdou also asked that the PC be shut down when everything is finished.
- **Branch** `iteration-5`, last commit `6044037`. Nothing of wave 3 is committed. Never `git add -A`: `.claude/worktrees/` and two iteration-4 drafts stay untracked on purpose.

## Wave 3, done (uncommitted)

- **Briefs updated to the registered design:** `detectors.md`, `case-study.md` (wave-3 scope: fakes only), `audit.md` (pass 5b's opening checks).
- **Detectors** (`ml-engineer`; progress log `detectors-progress.md`):
  - new `bench/detectors.py`, `bench/detector_stats.py`;
  - new tests `test_detectors.py`, `test_detector_classes.py` (written before any detector ran on the classes), `test_detector_stats.py`;
  - `bench/adversary.py`: `placement` / `table_path`, `build_table`, `load_table`, conventions G/M/P; `test_adversary.py` (appended).
- **Case study** (`ml-engineer`): new `bench/casestudy.py`, `tests/test_casestudy.py`. `power.load_series` got `report_file=` (default unchanged), so both reports' `series.npz` go through the one reader; the allowlist's `power.py` reasons were reworded, with no new rule; `test_power.py` got one test. It was never called on a real `series.npz`.
- **Orchestrator's checks:**
  - every caller of `generate` and `draw_leak` either keeps the default or threads `placement` and `table_path`;
  - 20261118, 20261119 and 20261120 appear only as constants in `detectors.py`;
  - the golden generator digests (Windows, pre-edit) still match;
  - the development digest reproduced on Windows: `e03f78b1…`.
- **Change-log line added** to `docs/PROTOCOL.md` (2026-11-19): the development digest. Its commit is still to be named, by a later dated line.

## Open findings to settle

1. **The digests depend on the machine.** Windows CRT against glibc: `exp` and `log` differ by one ulp. Consequences:
   - the WSL2 development digest is `0f806cd3…`;
   - the generator goldens differ in WSL2 too;
   - the agent added a 12-digit "portable" digest (`200809fd…` for 51118 `quantile`), which is not registered;
   - the official runs must happen on Windows, where `table.json` is, or the protocol must be amended. Pass 5b rules on this.
2. **Narrowings the detectors agent made** (its report, §6), for 5b to judge:
   - M1 is asserted under G and M only (under P a gated comparison turns missing);
   - FI's rule on M2 is asserted for M2 only, not for its mirror;
   - zero-volume bars keep their original values;
   - §4.4 is counted at row level;
   - the controls do not run through RETILE;
   - Newcombe's ψ is taken from Fagerland et al.'s package, not from the 1998 paper;
   - the bootstrap spread is read as the 97.5th minus the 2.5th percentile.
3. **The case study's choices** for 5b:
   - it regresses on factor payoffs, not on signal levels;
   - it fixed the signal definitions itself;
   - its HAC uses a Bartlett kernel with 168 lags.
4. **Process pools on Linux:**
   - a `fork` pool hung, so the detectors use `spawn`;
   - the adversary's own CLI pool may hang the same way, untested.
5. **Ruff is not in the environment.** The new files are clean under `uvx ruff check`.

## State at the end (2026-11-19)

- **Full Python suite on Windows, final tree:** 1,646 passed, 4 skipped. `cargo` was not run, since no crate changed.
- **Audit pass 5b: GO with fixes.** No Blocker; 4 Major, 12 Minor, 5 Nits. The findings are in `audit-5b-findings.md` and the scripts in `audit-5b-scripts/`.
  - The GO covers code digest `8607e7c4…`.
  - Every finding is logged as open. Per Abdou's instruction, none was fixed in this session.
- **Uncommitted:**
  - `docs/PROTOCOL.md`: the 2026-11-19 digest line;
  - the wave-3 code and tests;
  - `power.py`, `allowlist.py`, `test_power.py`;
  - the briefs `detectors.md`, `case-study.md`, `audit.md`, `detectors-progress.md`, `resume-4.md`, `audit-5b-findings.md`, `audit-5b-scripts/`.
- No official run was made. Seed 20261118 was not touched. Nothing was pushed.

## Next steps

1. **Ask Abdou** whether to commit wave 3 as audited, at code digest `8607e7c4…`, before the fixes. This gives a citable base for 5b-bis's diff. Stage by name; never `git add -A`.
2. **Fix wave** (`ml-engineer`, one agent), on `audit-5b-findings.md`'s disposition:
   - run path first: M1 (the platform pin, `run` refuses unless the development digest reproduces; record the platform), M2 (the guard on the one-shot seed), M4 (qualifier cells and per-leak verdicts in the JSON), and Minors 5, 9, 10, 11 and 14;
   - then the tests of M3 (from the X scripts), and the mutant test.
3. **Text, by the orchestrator** (dated change-log lines):
   - Minors 6, 7, 8, 12, 13, 15 and 16;
   - the case study's choices (payoff regressors as attribution after the fact; signal definitions; HAC with a Bartlett kernel and 168 lags);
   - ruling 1's line, verbatim, once the frozen commit exists.
4. **Pass 5b-bis** (`leakage-auditor`, fable): the diff since the audited tree only, and the digest reproduced on Windows at the frozen commit.
5. Then wave 4 on Windows, not WSL2, after Abdou's go-ahead:
   - the descriptive run;
   - the confirmatory run;
   - its byte-identity rerun.
   - After that, the case study's one real call (logged contact), the rows, audit phase 2, and the paper.
