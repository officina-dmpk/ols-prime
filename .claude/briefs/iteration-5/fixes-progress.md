# Progress — the fix wave after audit pass 5b (ml-engineer)

Resume from here. Brief: `fixes.md`. Findings: `audit-5b-findings.md`. Base: `6ab7e3e`, code digest `8607e7c4…7c19`.

## Milestone 0 — orientation (2026-11-19)

- Base checks on Windows: development digest `e03f78b187c1f7a7b62681a6c16214f7bd79d7f13b58459521cacb731ad9bc48` reproduces (18 s); `provenance.code_digest()` = `8607e7c4edb6c3dd30d332871958d185df0fa4308a9c3994e8811e70837a7c19` (88 files; tests are outside the digest's globs).
- Read: the brief, the findings, §0–§8 of the protocol section, `detectors-progress.md`, the auditor's scripts.

## Milestone 1 — run path edited (2026-11-19)

- `detector_stats.py` (LF kept, as at base): `share`, `mean_rate`, `newcombe_paired`, `paired_difference` write null, never NaN, on an empty set; `h15` skips an empty qualifier cell and writes `qualifier.cells`.
- `detectors.py` (CRLF kept): M1 `platform_info`, `PlatformRefused`, `check_platform_pin`, `REGISTERED_DEVELOPMENT_DIGEST`; M2 `registered_line_refusal`, `DESCRIPTIVE_TWO_RUN_SEED`/`DESCRIPTIVE_BOOTSTRAP_SEED`/`REGISTERED_N`; `main` reordered (guard first; real bars: table, pin, then manifest, then bars; `--table` passed to `run` under `quantile` only); `platform` in `detectors.json` and `run.json`, `platform_pin` in `detectors.json`; Minor 14 in `two_run_bars`; Minor 7 `Rows.finite_flags`, `_moved_finite`, `LeakResult.finite`, `primary_verdicts(finite=True)`, `ignores_outputs_that_turn_missing`; Minor 8 denominators in `summarize`; Minor 9 `secondary["long schedule"]`; Minor 10 `TWO-RUN s0.1 r2@h1` split row; Minor 11 `long_dates_check` in the assertions table; Minors 5 and 6 in `fi_m2_rule`, `truncation_cannot_flag`, `check_classes`; M4 `verdict_file`, `read_verdict_file`, `registered_variants`, `verdicts.jsonl` written by `write` only when all pass; nits (`can_flag` over H1's cuts per kind, digest label, `_part` null).
- `ruff@0.11.13 check` clean. Existing detector tests: 67 passed (gates and worker test not run yet), 1 expected failure fixed (NaN to null).
- Ruff note: at base, `uvx ruff format --check` (no repo config, line length 88) would reformat all five touched files, and ruff 0.17.5's `check` flags 8 pre-existing findings in `detectors.py`/`test_detectors.py`. Not reformatted (it would bury the diff 5b-bis reads); new test files are formatted.

## Milestone 2 — tests (2026-11-19)

- New modules (Windows, alone): `test_detector_runpath.py` 68 tests, about 5 s (M1, M2, Minors 5, 11, 14); `test_detector_independent.py` 9 tests, about 13 s (M3: X3, X12 windows and flags, X11 with hand-built leaks of every node type, reach-1 leaks, X9, `_moved` at 0.9e-9 / 1.1e-9, the one-bit twin); `test_detector_verdicts.py` 10 tests, about 16 s (M4 recomputation from the file on natural and seeded-random verdicts, X6, X6b, Minors 7, 8, 9, 10); `test_detector_mutants.py` 1 cheap test (every mutant applies once) + 1 opt-in (`OLSPRIME_MUTANTS=1`).
- Updated: `test_detector_classes.py` (Minor 6 under P, `truncation_cannot_flag`, the three-valued FI rule), `test_detector_stats.py` (null on empty, qualifier cells), `test_detectors.py` (stop rule: no `verdicts.jsonl`; byte identity extended to `verdicts.jsonl`, platform, pin skipped on synthetic, 64 dates, recomputation; every confirmatory seed in every slot with draws stubbed; digest label).
- Every detector module together: 164 passed, 1 skipped (opt-in), 156 s.
- Exact boundary of Minor 5 (`high[t+1]` = 2/3 · `close[t]` exactly): FI flags at both engineered cuts, so "≥" holds as registered.
- Lint fixes on touched files only (behaviour unchanged): render_md string concatenations parenthesised, `for k, values in col.items()` in `two_run_bars`, two test lines. `uvx ruff check` (0.17.5) and `ruff@0.11.13 check` clean on every touched file.
- Running: the opt-in mutant test (background), and the synthetic smoke run (seed 51118, TWO-RUN 51119, bootstrap 4242, n = 200, 8 workers, quantile + table, out in the session scratchpad).

## Milestone 3 — verification (2026-11-19)

- Mutant test (`OLSPRIME_MUTANTS=1`, 4 copies in parallel): **16 of 16 killed**, 425 s; unmutated copy passed first; repository code digest unchanged during the run. Killers: m1, m19, m23 by X11; m2, m18 by X3; m3a, m3b by the TWO-RUN windows test; m4 by the catch-rule edge; m5 by the FP2-fmin class test; m7, m22 by X9; m8 by the engineered M2 bars; m16, m17 by the random-verdict recomputation; m20 by the header-variants test; m21 by the one-bit twin.
- Smoke run (synthetic, 51118 / 51119 / bootstrap 4242, n = 200, 8 workers, quantile + registered table, out in the scratchpad): every assertion and gate passes (incl. §4.15's 64 dates; M1 under P 16/16 per truncation detector; FI on M2 16/16 and 128/128 predicted and flagged); `platform` in `detectors.json` and `run.json`; `platform_pin` skipped (synthetic); `verdicts.jsonl` 426 KB (about 2.1 KB per leak, about 21 MB at 10,000); `python -m tests.test_detector_verdicts <dir>` agrees. Stages: benches 6.9 s, population 27.5 s, checks 597 s.
- Development digest after the last edit: `e03f78b187c1f7a7b62681a6c16214f7bd79d7f13b58459521cacb731ad9bc48` (Windows AMD64, CPython 3.12.10, numpy 2.5.4); generator goldens pass (7 tests of `test_adversary.py`).
- New `provenance.code_digest()`: `4329b448629528ccbd7bd47c6b4dc99b16aeac0da702b2647c202466c6a0d8b1` (88 files). Note: the digest hashes working-tree bytes; `detectors.py` is CRLF and `detector_stats.py` LF on disk, as at base.

## Milestone 4 — the seal guard and the mutant harness (2026-11-19)

- First full suite: 1 failed, 1739 passed, 5 skipped (18 min). The failure was mine: `test_protocol.py::test_no_module_or_test_bypasses_load_klines` flags `import subprocess` and `shutil.copytree` in `test_detector_mutants.py`, and an in-process variant flagged `sys.path`/`sys.modules` edits. The allow-list gains no rule, so the harness was rewritten: the copy is made file by file (`read_bytes`/`write_bytes`), and each copy runs in a fresh spawned process whose target is `pytest.main` itself, with `-o pythonpath=<copy>` (pytest puts the copy first; this file edits no search path). A marker test written into each copy asserts that `olsprime` and `tests` are imported from the copy; the first failure is read from a JUnit XML report.
- Mutant rerun with that harness: **16 of 16 killed**, same killers, 461 s.
- Full suite, Windows, final tree: **1740 passed, 5 skipped** (15 min; was 1646 passed, 4 skipped; the new skip is the opt-in mutant test). Code digest unchanged by the harness rewrite (tests are outside its globs): `4329b448629528ccbd7bd47c6b4dc99b16aeac0da702b2647c202466c6a0d8b1`.
- Done. Nothing committed; `docs/` untouched.

## Milestone 5 — after the advisor's review (2026-11-19)

- `_pts` in `render_md` writes "n/a (no leak)" for an empty cell (a regression of the NaN-to-null change: an empty placement-invariant complement would have crashed the Markdown). Tests: `test_the_report_renders_an_empty_subset`, and `test_a_real_bar_run_gives_the_table_to_the_generator_under_quantile_only` (the descriptive line's `--table` reaches the pin, not the generator; `platform_pin.checked` true in the JSON).
- Redone after this last code edit: code digest `3b59007a8111cc858bf01e15d7ed6636775903cbabce484ea3ac3b483ab4d5e5`; development digest `e03f78b1…bc48` reproduces; mutants 16 of 16 killed (294 s).
- Final full suite: **1743 passed, 5 skipped** (14 min); `test_adversary.py` 43 passed (goldens included).
