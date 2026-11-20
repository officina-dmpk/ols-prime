# Fix wave — iteration 5, after audit pass 5b

- **Written:** 2026-11-19, by the orchestrator of iteration 5's fourth session.
- **Owner:** `ml-engineer` (one agent). Progress log: `.claude/briefs/iteration-5/fixes-progress.md` (create it; update it at each milestone so that a stopped run can resume from it).
- **Base:** branch `iteration-5`, commit `6ab7e3e` (wave 3 as audited, code digest `8607e7c4edb6c3dd30d332871958d185df0fa4308a9c3994e8811e70837a7c19`).
- **Read first:** `audit-5b-findings.md` (the findings, by number), `docs/PROTOCOL.md` section "Leak detectors measured against each other (iteration 5)" (§ numbers below refer to it), `detectors-progress.md`, and the auditor's scripts in `audit-5b-scripts/` (X3, X4, X6, X6b, X9, X11, X12, `mutate.py`, `mutate2.py`, `run_muts.sh`).

## Goal

Fix every run-path finding of pass 5b, turn the auditor's independent scripts into tests, and add the planted-mutant test, so that the next commit can be frozen for the official runs. Pass 5b-bis will re-read **the diff only**, so keep the diff small, local and explained.

## Files

- **You own:** `python/olsprime/bench/detectors.py`, `python/olsprime/bench/detector_stats.py`, `python/tests/test_detectors.py`, `python/tests/test_detector_classes.py`, `python/tests/test_detector_stats.py`, new test files `python/tests/test_detector_*.py`, and `fixes-progress.md`.
- **Do not touch:** `docs/` (the orchestrator writes the dated protocol lines in parallel), `runs/`, `data/`, `python/pyproject.toml`, `python/uv.lock`, `python/tests/allowlist.py` (it gains no rule), `.claude/briefs/iteration-5/quantile_table.py` (a registered brief artifact; its duplicate of `build_table` stays, logged).
- **`bench/adversary.py`: avoid.** The generator's draw path must not change. If a fix seems to need `adversary.py`, stop and report first.

## Hard constraints

1. **No draw from seed 20261118, ever**: not in tests, smoke runs or mutants. The same for 20261119 and 20261120. The tests reference the module constants, never the literals (`test_no_test_file_holds_a_confirmatory_seed` must keep passing). The "accept" case of M2's guard is tested **on the pure predicate only**, never by running the CLI with those seeds.
2. **No real bars.** Every run is on `bench.synthetic` bars. The real `table.json` (`runs/2026-11-18-quantile-table/table.json`) may be read, as the existing tests and the digest command do.
3. **The generator goldens and the development digest must still reproduce at the end, on Windows:** `uv run python -m olsprime.bench.detectors digest --seed 51118 --placement quantile --table ../runs/2026-11-18-quantile-table/table.json` gives `e03f78b187c1f7a7b62681a6c16214f7bd79d7f13b58459521cacb731ad9bc48`. If either breaks, stop and report.
4. Output of smoke runs goes to your scratch folder, never to `runs/`.
5. No `git add`, no commit. The orchestrator commits.

## Run path (do these first)

**M1 — the platform pin.**
- New constant `REGISTERED_DEVELOPMENT_DIGEST = "e03f78b1…bc48"` (the full value above).
- A testable function, say `check_platform_pin(table_path, *, expected=REGISTERED_DEVELOPMENT_DIGEST, n=10_000)`, that regenerates seed `DEVELOPMENT_POPULATION_SEED`, `placement="quantile"`, the given table, and refuses (raises, nothing written) unless the digest equals `expected`.
- In `main`, on **real bars only**: check the table (`adv.load_table`) and the pin **before** `provenance.current_manifest()` and before `_load_development` reads any bar (today the bars load first). Synthetic runs skip the pin, so they keep passing on CI and WSL2.
- **`--table` becomes required on every real-bar run, whatever the placement**: the descriptive run is `h1-bands` and still needs the table for the pin.
- `detectors.json` and `run.json` both record `platform`: `platform.system()`, `platform.machine()`, `platform.python_version()`, `numpy.__version__`, on synthetic runs too.
- Tests: the refusal with an injected wrong `expected` and a small `n` (skipped where the table is absent); the full pin passes where the table is present **and** the platform is Windows AMD64 (skip elsewhere, with the reason).

**M2 — the guard on the registered command lines.** A pure predicate on the parsed arguments, returning a refusal reason or `None`, called by `main` before anything else:
- `--seed 20261118` (`CONFIRMATORY_POPULATION_SEED`): refuse unless `--placement quantile`, `--two-run-seed` = `CONFIRMATORY_TWO_RUN_SEED`, `--bootstrap-seed` = `CONFIRMATORY_BOOTSTRAP_SEED`, `--n 10000`, and no `--synthetic`.
- 20261119 and 20261120 are refused in any other role or combination.
- **The descriptive run is registered now too** (the orchestrator logs it in a dated line): `--seed 20261029` (`DESCRIPTIVE_POPULATION_SEED`) on real bars requires `--placement h1-bands`, `--two-run-seed 29119`, `--bootstrap-seed 29120`, `--n 10000`. Add `DESCRIPTIVE_TWO_RUN_SEED = 29119` and `DESCRIPTIVE_BOOTSTRAP_SEED = 29120`.
- **Real bars with any other population seed: refused** (§7: after 5b, the only real-bar runs are the descriptive and the confirmatory ones).
- Real-bar runs therefore always carry `--bootstrap-seed` (Minor 11).
- Tests: every forbidden seed in every slot (this also fixes the nit at `test_detectors.py:444`, which tried only the smallest), every single-argument deviation from each registered line, and the accept cases on the predicate only.

**M4 — phase 2 can recompute the numbers.**
- `h15.qualifier` holds both qualifier cells (convention M; the not-constant denominator), each with its 2×2 table, difference and Newcombe interval, beside `triggered_by`.
- One compact per-leak file, written **only when every assertion and gate passes** (extend the stop-rule test to check it is absent on a stop), deterministic (extend `test_two_runs_give_byte_identical_json` to it), one line per leak in id order: the leak's id, family, output, `designed`, `position`, placement-invariant flag, both constancy flags, and the cut-verdict bits of every registered variant on both schedules (every detector, arm, run count, convention, σ; FI ×3 and ÷3; the §4.4 sensitivity below). Choose the encoding (hex of the bit vectors is fine), document it at the top of the file or in a header line, and keep it to a few tens of MB at most.
- **Test:** recompute, from that file alone (plus `config`), every number of `metrics` that is a function of per-leak cut verdicts and tags: any-cut shares under every denominator, families and strata, the first-m-cuts curve, the mean per-cut rates, the pairs, the equal-run-count pairs, the union and its misses, H15's deciding cell and both qualifier cells, the placement-invariant subset, the mirror asymmetry if its bits are in the file, and the bootstrap. Numbers that need row-level data (the read split) stay JSON-only: say so in the file's header.

**Minor 5 — FI's rule on M2.** Three-valued: at cuts where `high[t+1] ≥ 2/3 · close[t]`, assert "flagged"; elsewhere "not predicted", counted and reported, never asserted. Test on engineered bars, from X4 (include cases the old rule got wrong). The rule is never evaluated on real bars outside the official run.

**Minor 6 — M1 under P.** Assert the registered replacement: under G and M, "never" for every detector; under P, the truncation detectors flag M1 at every cut of every schedule (every end for RETILE). If some cut cannot flag by construction (the series' last row), count it apart and tell me exactly which, so the protocol line matches the code word for word.

**Minor 9.** The long-schedule class of §4.11 is `FI@long | TRUNC-0/G@long | TRUNC-1/G@long | TWO-RUN σ0.1 r2@long`, not the union over both schedules.

**Minor 10.** The read split gets a row for TWO-RUN's primary arm (σ = 0.1, runs 1–2).

**Minor 11.** Assert 64 distinct dates, shared by both pairs, before the cut-date bootstrap runs.

**Minor 14.** `two_run_bars` raises `RepairFailed` if a zero-volume bar has a non-zero quote volume, taker base volume, taker quote volume or trade count. Test it.

**Minor 7 — §4.4's sensitivity, implement it.** For each detector, the any-cut share under the rule "ignores outputs that turn missing": a row counts only where both outputs are finite and move by more than `inv.CAUGHT_ABOVE`. Name it exactly that in the JSON and the Markdown, never "through a changed value". Test: recompute it independently from outputs on synthetic bars.

**Minor 8 — §4.6's denominators, implement them** for every share of §4.1–4.5: families, `position` strata, the first-m-cuts curve, the read split (restricted to the denominator's leaks) and the conventions, beside the any-cut share and the mean rate where they already are. Test by recomputation from the per-leak file (M4's test covers it).
- If 7 or 8 needs a change to how `process_leak` or `compare` computes flags beyond adding a field, stop and report before doing it: the orchestrator may log them as dropped instead.

**Nits.** `can_flag` counted over H1's 16 cuts, per control kind; `share(k, 0)` writes `null`, not NaN; the digest command labels the 12-digit digest "diagnostic, not registered".

## Tests (M3), then the mutants

Turn the auditor's scripts into tests, independent of the code under test (scalar rewrites, not calls into the same helpers):
- X3: §2.5's repair, bar by bar, all nine columns, both σ;
- X12: TWO-RUN and SHUFFLE from the registered seed keys, all 16 runs, both schedules (use the development TWO-RUN seed);
- X11: truncation on really truncated bars under G, M and P, and "TRUNC-1 flags a reach-1 leak";
- X9: every node type under the three conventions;
- X6 and X6b: every metric of `summarize` recomputed from the flags;
- `_moved` at 0.9e-9 and 1.1e-9;
- an honest twin that differs by one bit;
- Minor 5's engineered bars (X4).

Keep the default suite's run time reasonable: say how long each new module takes.

**The mutant test**, `tests/test_detector_mutants.py`:
- opt-in through an environment variable (for example `OLSPRIME_MUTANTS=1`), since `pyproject.toml` must not change; skipped otherwise, with the reason;
- applies each of the auditor's 16 mutants (`mutate.py`, `mutate2.py`; adapt the replaced strings to the fixed code, keeping each mutant's meaning) to a temporary copy of `python/`, never the repository, and runs the detector test modules against the copy, as `run_muts.sh` does;
- requires each mutant to be killed, and reports the kill count;
- checks at the end that `provenance.code_digest()` of the repository is unchanged.

If a mutant survives your new tests, say which and why. Do not weaken the mutant to kill it.

## Done criteria

1. `cd python && uv run pytest` green on Windows: give the counts (it was 1,646 passed, 4 skipped).
2. `OLSPRIME_MUTANTS=1` run of the mutant test: the kill count, out of 16.
3. `uvx ruff check` and `uvx ruff format --check` clean on every file you touched (the repository's configuration).
4. The development digest reproduces (`e03f78b1…bc48`), and the generator goldens pass.
5. One synthetic CLI smoke run (seed 51118, TWO-RUN 51119, a bootstrap seed of your choice, n = 200, 8 workers, `--placement quantile --table …`, output in scratch): every assertion passes, `platform` is recorded, the per-leak file exists, M4's recomputation agrees on it.
6. The new `provenance.code_digest()` value, and `git diff --stat` against `6ab7e3e`.
7. `fixes-progress.md` and a final report with, for each finding (M1, M2, M4, Minors 5–11, 14, nits, M3): what changed, where (file:line), and which test covers it. For Minors 5, 6, 7, 8 and the per-leak file, give the exact semantics in one or two sentences each, so the orchestrator can write the protocol lines to match the code.
