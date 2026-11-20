# Audit pass 5b — wave 3's code, before any official run (iteration 5)

- **Agent:** `leakage-auditor` (fable), 2026-11-19. Read-only. The orchestrator wrote this file from the agent's report, condensed, and kept every replacement text verbatim.
- **Object:** the working tree on `6044037`, uncommitted. Code digest `8607e7c4edb6c3dd30d332871958d185df0fa4308a9c3994e8811e70837a7c19` (`provenance.code_digest`, 88 files). The tree did not move during the audit.
- **Verdict: GO with fixes.** No Blocker; 4 Major, 12 Minor, 5 Nits.
  - The GO covers the tree above. It does not cover a fix to the run path (`detectors.py`, `detector_stats.py`, `adversary.py`). Such a fix needs pass **5b-bis**, a re-look at the diff only, and the development digest reproduced on Windows at the frozen commit.
  - Fixes to tests or text alone need no re-look.
- **Scripts:** copied to `audit-5b-scripts/`. They were run from the session scratchpad, so their paths may point there.
  - X3: TWO-RUN's repair. X4: FI on M2. X5: Newcombe. X6 and X6b: the population metrics and the qualifier. X9: the conventions. X10: the goldens. X11: truncation. X12: TWO-RUN and SHUFFLE wiring.
  - `mutate*.py` and `run_muts.sh`: the mutants.
  - The scratch copy of `table.json` was deleted.

## Opening checks

1. **The registered text against 5a-bis: clean.**
   - F1, F2, F6 and F7 are verbatim.
   - F3, F4 and F5 are carried through.
   - Every Minor m1 to m11 is carried.
2. **The text the orchestrator wrote beyond the verbatim parts.** Two inherited defects, both in §3.3: FI's rule on M2 (Minor 5) and M1 under P (Minor 6).
   - §3.4 calls item 3's verdicts "identities of IEEE arithmetic or of the code". M2's are not: they depend on the bars.
   - §4.14, §4.15 and §1.7's `table_path` match the code.
3. **The development digest, reproduced on Windows:** `e03f78b187c1f7a7b62681a6c16214f7bd79d7f13b58459521cacb731ad9bc48`, with numpy 2.5.4, CPython 3.12.10 and Windows AMD64. `table.json` hashes to `527e01ba…`.
4. **Seeds and contacts: clean.**
   - 20261118, 20261119 and 20261120 appear only as constants (`detectors.py:61-63`).
   - `--synthetic` refuses them.
   - Every caller of the generator keeps the default or threads the placement.
   - No `detectors.json` or `casestudy.json` exists anywhere that was checked.
5. **Stop rule: enforced** (`detectors.py:1519-1559`), and tested on files, stdout and stderr.

## Major

- **M1. The platform pin is enforced by nothing in the run path.**
  - A clean clone run from WSL2 reads the same `table.json` through `/mnt/c`, passes the table check, and draws a population that is not the registered one. Nothing refuses.
  - **Fix:**
    - before any work on real bars, `run` regenerates seed 51118, n = 10,000, `quantile`, and refuses unless `development_digest` equals a registered constant;
    - `detectors.json` and `run.json` record `platform.system()`, `platform.machine()`, the Python version and `numpy.__version__`;
    - the dated line of ruling 1 below.
- **M2. The CLI accepts the one-shot seed in any combination.** One typo (`--placement h1-bands`, a wrong `--two-run-seed`, no `--bootstrap-seed`, another `--n`) would reveal most of the confirmatory verdicts on the wrong design: 8,316 of 10,000 leaks are placement-invariant.
  - **Fix:** if `--seed` is 20261118, refuse unless all of these hold:
    - `--placement` is `quantile`;
    - the two-run seed is 20261119;
    - the bootstrap seed is 20261120;
    - n is 10,000;
    - `--synthetic` is absent.
  - Refuse 20261119 and 20261120 in any other role.
- **M3. The tests do not fail on most wrong detectors.** Of 16 planted mutants, 4 were killed. The mutants were chosen where the auditor expected a gap, so this is not a rate for the suite.
  - **Killed:** TRUNC-0 one bar late; RETILE's input a single tile; TRUNC-1 equal to TRUNC-0 (through metadata only); P with Kleene AND.
  - **Survived:**
    - TRUNC-1 as v1's arm (5a-bis F4's defect coming back);
    - TWO-RUN with volume unperturbed, with the wrong wick factor, with runs 3–8 reusing run 2;
    - the long schedule with id 1;
    - `Colour` under M read as G;
    - FI's ×3 and ÷3 swapped;
    - H15's cell on TRUNC-1;
    - the union without SHUFFLE;
    - the catch threshold at 1e-6;
    - the twin check without the bit rule;
    - FI's M2 rule as "every cut".
  - Today's code is right on every survivor but the last, shown by the independent scripts X3, X6, X6b, X9, X11 and X12, or by reading.
  - **Fix (tests only), before the freeze.** Turn the scripts into tests:
    - X3: §2.5 bar by bar, all nine columns, both σ;
    - X12: TWO-RUN and SHUFFLE from the registered seed keys, all 16 runs, both schedules;
    - X11: truncation on really truncated bars under G, M and P, and "TRUNC-1 flags a reach-1 leak";
    - X9: every node type under the three conventions;
    - X6 and X6b: every metric of `summarize` recomputed from the flags;
    - `_moved` at 0.9e-9 and 1.1e-9;
    - a twin that differs by one bit.
- **M4. Phase 2 cannot recompute most numbers from the run's JSON.** `leaks` stores only the four primary detectors' cut strings. H15's two qualifier cells are computed and dropped; only `triggered_by` is written.
  - **Fix:**
    - write both qualifier cells (table, difference, interval) under `h15.qualifier`;
    - write per-leak verdict strings for every registered variant, with the `designed` and `position` tags, in one compact file written only when every assertion passes.

## Minor

5. **FI's registered rule on M2 is wrong in its "unless" half** (`PROTOCOL.md:577`; `detectors.py:887-889`, `:912-915`). It is 5a-bis's own wording.
   - **Cause:** the ×3 run sets bar t+1's low to `max(1.5 × the highest high of bars t−90..t, 3 × high[t+1])` (`perturb.py:294`). So FI also flags when the window's high exceeds about 4/3 of `close[t]`.
   - **Evidence (X4):** 24 of 40 engineered cases were flagged where the rule says no.
   - **Fix:** assert "flagged" only at cuts where `high[t+1] ≥ 2/3 · close[t]`, count the others as "not predicted", and add a test on engineered bars.
6. **M1 under P.** "Never, for every detector" cannot hold under P. On synthetic bars, P flags M1 at 16 of 16, 128 of 128 and 28 of 28 cuts.
   - **Fix:** a dated line: "never" holds under G and M; under P the truncation detectors flag M1 at every cut. Assert "every cut" under P.
7. **§4.4's sensitivity** ("ignores outputs that turn missing") is computed nowhere. Implement it, or log it as dropped, before the freeze.
8. **§4.6's denominators** are applied to the any-cut share and the mean rate only, not to families, strata, the curve, the split or the conventions. Implement, or log.
9. **§4.11's "long schedule" class** is built from the union over both schedules, which includes TRUNC-1 at H1's cuts (`detectors.py:1398-1399`). Use `FI@long | TRUNC-0/G@long | TRUNC-1/G@long | TWO-RUN s0.1 r2@long`.
10. **The read split has no row for TWO-RUN's primary arm** (`detectors.py:1049-1052`). Add σ = 0.1, runs 1–2.
11. **§4.15 can vanish from an official run:** `--bootstrap-seed` is optional, and nothing asserts 64 distinct dates. Add the assertion. M2's guard covers the confirmatory run.
12. **The official command lines are written nowhere.** Fix them in a dated line, including which TWO-RUN and bootstrap seeds the descriptive run uses.
13. **§1.3's "byte for byte" cannot hold literally for `adversary.json`:** its `provenance` block holds the commit and the code digest. Define the comparison (every key but `provenance`) before wave 4.
14. **Zero-volume bars in TWO-RUN** keep their original values. Raise `RepairFailed` if a zero-volume bar has a non-zero quote volume, taker volume or trade count.
15. **The "independent" prediction of §3.2 shares the evaluator and the bench;** it has its own comparison only. Acceptable, since "run for run" needs the runs. State it wherever §3.2 is reported.
16. **The case study's three choices**, to log before the one real call (ruling 2).

## Nits

- `can_flag` is counted once per control kind and over every cut of the bench, not over H1's 16.
- `share(k, 0)` writes NaN into the JSON. It is unreachable at n = 10,000.
- `test_detectors.py:444` tries only the smallest forbidden seed in each slot.
- `quantile_table.py` keeps its own copy of `build_table`, the same function.
- The digest CLI prints the 12-digit digest beside the exact one. Label it "diagnostic, not registered".

## Rulings

1. **Machine dependence.** §1.7 is sound as a pin only with the platform named. The numpy version does not fix `exp`, and "the machine that holds `table.json`" does not choose the C runtime.
   - The 2026-11-19 line exceeds §1.7 in letter, not in substance. It is accepted, and must be completed.
   - The 12-digit digest may stay as an unregistered diagnostic. It never pins anything and never admits a run on another platform.
   - **Dated line to add, verbatim:**
     > The frozen commit is `<sha>`. On it, on Windows 11 (AMD64), CPython 3.12.10, numpy 2.5.4, the development digest is `e03f78b1…bc48`; pass 5b reproduced it on the wave-3 tree (code digest `8607e7c4…`). The exact digest, hence the exact population of a seed, depends on the platform's `exp`. The three official runs are made in that environment, and `run` refuses unless the development digest reproduces. `table.json` can be read from WSL2; WSL2 is not the machine of the official run. The WSL2 digest and the 12-digit digest are diagnostics and pin nothing.
2. **The authors' narrowings.**
   - **M1 under G and M only:** an inconsistency in the registered text (Minor 6).
   - **FI's M2 rule, on M2 only:** faithful (in X4 the mirror's verdict equalled M2's in all 40 cases), but the rule itself is defective (Minor 5).
   - **Zero-volume bars:** faithful where the values are 0 (Minor 14).
   - **§4.4 at row level:** faithful (Minor 10).
   - **Controls not run through RETILE:** faithful.
   - **Newcombe's ψ, taken from Fagerland et al.:** immaterial, at most 0.001 point at n = 10,000, and 0.003 on an extreme table. It matters only if a limit falls within 0.003 point of 0 or −1. The 1998 paper was not re-read.
   - **The bootstrap spread as the 97.5th minus the 2.5th percentile:** faithful; log it.
   - **The case study:**
     - the regressors are payoffs, not signal levels: a deviation from the brief's wording, consistent with "Nagel's control". Log it, and say that it is attribution after the fact, because the payoff contains the realized return;
     - the signal definitions were fixed by the agent: log them as fixed before the real call;
     - HAC with a Bartlett kernel and 168 lags: faithful; log it.
   - **Linux pools and ruff:** no finding while the official runs are on Windows.
3. **Would the tests fail on a wrong detector?**
   - Yes for TRUNC-0, RETILE and convention P.
   - For TRUNC-1, only through a metadata assertion.
   - Not for TWO-RUN's law or wiring, convention M outside `Cmp`, or anything in `summarize`.

## Clean

- **The generator, default placement:** the goldens are confirmed against the committed code.
- **The generator, `quantile`:** three call sites thread the placement, one uniform draw each, as §1.3 says.
- **TWO-RUN's repair:** 59,760 values against a scalar rewrite of §2.5, 0 beyond 2 ulp.
- **Conventions G, M and P:** 62.6 million cells, 0 differences.
- **Truncation on really truncated bars:** 103,680 units, 0 disagreements.
- **TWO-RUN and SHUFFLE wiring:** 0 disagreements.
- **The assertions:** 400 development leaks, every assertion with 0 violations.
- **Every metric of `summarize`** equals the auditor's recomputation.
- **Exact McNemar** equals `scipy.stats.binomtest`.
- **The case study:**
  - its digest constants match the committed text;
  - its bars go through `load_klines`, cut to `known_at < DEVELOPMENT.end`;
  - its signals are past-only.
- **The seal:** real bars reach the detectors only through `load_klines`. The allowlist gained no rule.

## Not covered by any run

- The 50-leak gates; the pass is the authors' run.
- The properties of the real bars: no real cut with a next-day high below two thirds of the close, a close above twice the previous one, or a zero-volume bar.
- WSL2, which the auditor did not run.
- `adversary.json`'s platform: inferred as Windows.
- `fwd_return`'s horizon: taken from the case study's docstring.
- `cargo test`, ruff.

## Contacts

- **Read:** the briefs, `docs/PROTOCOL.md`, `docs/HYPOTHESES.md` and `docs/ITERATIONS.md:590-606`.
- **`runs/`:**
  - hashed `table.json`, loaded it for seed 51118 only, and copied it to scratch (the copy is deleted);
  - read `2026-10-29-h1-adversary/run.json`, the first 600 bytes of its log, and the top-level keys and provenance of `adversary.json`.
- No bars, no `data/`, no vault, no `series.npz`.
- **Seeds executed:** 51118, 51119, 20261029 (the generator only), the scratch seeds 4242 and 99, and the code's own seeds, on synthetic bars.

## Bolder next step (auditor)

A planted-bug control for the bench: `tests/test_detector_mutants.py` applies each mutant above to a temporary copy and requires the suite to kill it. The kill count is reported in `docs/RESULTS.md` beside the detectors' rates. Today it is 4 of 16.

## Disposition (orchestrator, 2026-11-19)

Per Abdou's instruction, the session stops after pass 5b. No fix is applied in this session; every finding is **logged, open**, to be fixed in the next session before the freeze:

- **Run path:** M1, M2, M4, and Minors 5, 6, 9, 10, 11 and 14. These need pass 5b-bis on the diff, and the digest reproduced at the frozen commit.
- **Tests only:** M3, and the mutant test of the bolder step.
- **Text only:**
  - ruling 1's dated line, once the commit exists;
  - Minors 6, 7, 8, 12, 13, 15 and 16;
  - the case study's choices.
- **Nits:** with the fixes.
