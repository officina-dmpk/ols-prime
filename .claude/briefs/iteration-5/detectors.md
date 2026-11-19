# Brief — the detector benchmark (wave 3 build, wave 4 runs)

- **Agent:** `ml-engineer` (opus, high).
- **Updated 2026-11-18** to the registered design, after the registration commit `6044037`. The design is `docs/PROTOCOL.md`, section "Leak detectors measured against each other (iteration 5)" (below, "§n" means that section's part n), and H15 in `docs/HYPOTHESES.md`. Where this brief and the section disagree, the section is normative: stop and report the disagreement instead of choosing.
- **Motto:** we should be more ambitious in how hard we try to make our own detector lose, never in what we claim when it wins.

## Ownership (wave 3)

- **Writes:**
  - new `python/olsprime/bench/detectors.py`, and, if it grows past about 1,500 lines, one sibling module `bench/detector_stats.py` for §4's statistics;
  - new `python/tests/test_detectors.py` (and `test_detector_stats.py` if split);
  - `python/olsprime/bench/adversary.py` and `python/tests/test_adversary.py`, for these changes only:
    - `placement` and `table_path` keyword arguments of `generate` and `draw_leak` (§1.3, §1.7), **outside** `AdversaryConfig`;
    - `build_table` moved from `.claude/briefs/iteration-5/quantile_table.py` (same function, same output bytes), and the table loader that checks the registered digest;
    - evaluation under conventions M and P (§2, "Three conventions"), as an opt-in parameter: G stays the default, and the default path must stay bit for bit what it is today.
  - A progress log, `.claude/briefs/iteration-5/detectors-progress.md`: what is done, what is next, the test count. Update it at each milestone, so that a stopped run resumes from it.
- **Read-only:** `bench/invariance.py`, `bench/twins.py`, `bench/perturb.py`, `bench/synthetic.py`, everything under `docs/`, `runs/`, `data/`. If one of them must change, stop and report: the orchestrator decides.
- **Not yours:** `bench/casestudy.py` and its tests (another agent, in parallel). Never `git add`, never commit.

## Data and seeds in wave 3 (§7.1)

- **Synthetic bars only** (`bench.synthetic.synthetic_bars`). No call to `load_klines`, `development_bars` on real data, or the vault. The one exception: a test that hashes `runs/2026-11-18-quantile-table/table.json` where the file exists (§1.4), and skips otherwise.
- **Seeds you may execute:** population 51118 (both placements), TWO-RUN 51119, and the existing seeds of the code (20261029 for the generator only, see "Byte identity"; 20261027, 7, 11, 20261030, 3) on synthetic bars.
- **Seeds you must never execute:** 20261118 (the confirmatory population), 20261119 (TWO-RUN's confirmatory seed), 20261120 (the cut-date bootstrap). They appear only as named constants, never as a default argument that a test reaches, never in a test. A grep test asserts that no test file contains them.
- **Synthetic bars long enough for the registered schedules.** `twins.synthetic_pairs()` uses 560 days: too short for H1's cut rows (502 to 2664), the long schedule and τ = 365 tiles. Build the detectors' synthetic pairs to span the real dates (2017-08-17 to the end of the development period, as `development_bars` defines it), with folds from the same code, so that scored rows start at row 502. Assert in a test that the 16 cuts, the 64 long cuts per pair and the 28 RETILE ends exist on them. On synthetic bars the cut rows come from `choose_cuts` and need not equal §2's real-bar rows; that equality is checked in wave 4, never by reading real bars now.

## Byte identity

- Golden digests of the generator, computed by the orchestrator at `6044037` before any edit, bar-free: SHA-256 over leaks `0 .. 9,999`, one line per leak, `repr(leak.expr) + "\t" + leak.output + "\t" + repr(leak.tags) + "\n"`, UTF-8 (numpy 2.5.4, Python 3.12.10, Windows):
  - seed 20261029, default placement: `f0f74ccedbeb6d0752eda58426d6914d1c26c29f66c7be8264934490f43ba602`;
  - seed 51118, default placement: `ac601a089ed529b8dbf666bb28c9e308e404d4fdf99ed298549297757632922b`.
- Tests pin both after your change (default placement, and `placement="h1-bands"` given explicitly). This is the bar-free half of §1.3's byte identity.
- The bar half, `adversary.json` of `runs/2026-10-29-h1-adversary/` reproduced byte for byte, is a real-bars run: it belongs to wave 4's descriptive run (`experiment-runner`), not to you. Make it possible: `python -m olsprime.bench.adversary` with no new argument must behave as today.
- `twins.py:399`'s write-back check must still pass: `_config_json` and `AdversaryConfig` are unchanged. The existing tests of `test_adversary.py` and `test_twins*` must pass untouched.

## Build

1. **The generator under `quantile`** (§1.3, §1.4, §1.7): exactly the code-level draw of §1.3, one `rng.uniform(0.02, 0.98)` per `_threshold` call. `generate(..., placement="quantile")` requires `table_path`, checks the bytes against `527e01ba7028fb5666e694fcadd5b22d2fdea31718d96e53d98a29e383183c43` and refuses on a mismatch; it never rebuilds the table. Tests:
   - `_threshold` consumes exactly one draw under `quantile` (compare the generator's state after the call with one `uniform` draw);
   - on seed 51118, every leak drawn with no `_threshold` call has identical `repr(expr)`, output and tags under both placements; report how many of 10,000 (§1.6 counts 8,258 on a neutral seed);
   - a wrong table digest is refused; a missing `table_path` with `quantile` is refused;
   - `build_table` on a fixed synthetic input gives pinned bytes and digest; on the real `table.json` where present, the digest is the registered one.
   - **The development digest function** (§1.7): `development_digest(leaks) -> str`, the hash above, plus a CLI entry that prints it with the numpy version for seed 51118, n = 10,000, `quantile`, the registered table. You compute it where the table exists (it is outside git; on Windows at `runs/2026-11-18-quantile-table/table.json`) and write it in your report and the progress log. The orchestrator registers it; you do not touch `docs/`.
2. **Each detector as a pure function** with the registered definition (§2): FI (reusing `bench/perturb.py` and the adversary's fast path; never re-implement H1), TRUNC-0, TRUNC-1 (TRUNC-0 at `t + 1`, one code path), RETILE (really slicing the bars, §2.4), TWO-RUN (the draws and the repair of §2.5 to the letter), SHUFFLE (`bench/twins.py`'s twins, seed 20261030), on H1's 16 cuts and, for FI, TRUNC-0, TRUNC-1 and TWO-RUN, the long schedule. The catch rule is H1's (§0.1). Run counts per §2.7; every alternative count of §4.8 computable.
3. **Conventions G, M, P** on atomic predicates (§2), applied to both runs of a comparison, for TRUNC-0, TRUNC-1 and RETILE only.
4. **Controls** (§3): honest twins, FP1, FP2-min, FP2-fmin built as §3.2 says, with the prediction written as code that shares nothing with the detectors; Fonseca's classes M1 to M3 with their verdicts per detector and schedule, written as tests **before** any detector runs on them (commit order is the orchestrator's; write the test file for the classes first and say so in the progress log).
5. **Metrics** (§4.1 to §4.15): Wilson, the normal interval over leaks, Newcombe's method 10 for paired proportions, the exact two-sided McNemar p-value, the first-m-cuts curve in §4.3's order, the read split of §4.4, the three denominators of §4.6, the mirror asymmetry of §4.9, the union and its misses, the placement-invariant subset, and the cut-date bootstrap (seed passed as an argument; tests use another seed). H15's two labels, the prior and the qualifier as a pure function of the numbers, with a test for each label and each branch of the prior (§5).
6. **The stop rule as code** (§7.4): the CLI evaluates every assertion and gate first and writes only pass or fail and counts; it writes no rate and no per-leak verdict unless all pass. A test plants a failing assertion and checks that no rate reaches the output files.
7. **Outputs:** `detectors.json` (sorted keys, recording `placement` and the table digest, §1.7) and `detectors.md`, the registered metrics only. Two runs give byte-identical JSON (precedent `runs/2026-10-30-twins-2/`), tested on synthetic bars with a small n.

## Assertions as tests (every one of §3.4, plus the gates)

Each is a test on synthetic bars and a check the CLI runs before writing any rate:
- [ ] §3.1: no detector flags a past-only twin, under every convention, schedule, σ, run count and both rules;
- [ ] §3.2: the cancelled controls' flags equal the independent prediction, run for run;
- [ ] §3.3: Fonseca's M1, M2 (both mirrors, G and M), M3, FP1, FP2 give their registered verdicts; FI on M2 follows its registered rule;
- [ ] §2, P: under P, TRUNC-0 flags every leak at every cut except as the registered exception says; binary roots: output missing exactly where the OR mask is set;
- [ ] §4.4: 100 % of TRUNC-0's, TRUNC-1's and RETILE's catches are through a missing read, with the per-read rule (not the OR mask);
- [ ] §4.9: a single-`Cmp` leak and its mirror are flagged together wherever every read is defined in both runs and `a ≠ margin · b`;
- [ ] §2.4: RETILE's flags equal the windowed TRUNC-0 run at the 28 ends;
- [ ] §2.3: row `t + 1` exists and is scored at every cut of both schedules; cuts where it is the last row are counted;
- [ ] §2.5: TWO-RUN's repair checks (wick undefined iff undefined; `vwap'` in `[lo', h']` as constructed; stored columns at 1e-12; `_check_valid` on rows `t + 1 .. t + 10` only); the bind shares and the body and fill medians are reported;
- [ ] §4 gates: FI's fast path against H1's own path; TRUNC-0 through `LeakModel` on really truncated bars; TWO-RUN and SHUFFLE through `inv.outputs`; on 50 leaks (equivalence seed 3), here on the development population.

The planted-fooling tests of the original brief stay: for each detector, a leak built to escape it alone is missed by it and caught by another, so the union is tested.

## Throughput

On 200 leaks of seed 51118 (`quantile`, or `h1-bands` where the table is absent) on the long synthetic bars, measure each detector's wall time with 8 workers, and project the cost of n = 10,000 on both populations. Write it in the progress log and your report before any real run. The adversary's precedent: 3 min 15 s with 8 workers for 10,000 leaks under FI alone.

## Verification you run before reporting

```bash
cd python && uv run ruff check . && uv run ruff format --check . && uv run pytest
```

Also in WSL2 if you can reach it (the uv environment on the Linux disk); otherwise say so.

## Done when (wave 3)

All tests pass on Windows (and in WSL2, or the report says it was not run there); the progress log lists every checkbox above with its test name; the development digest and its numpy version are in the report; the throughput projection is written; no forbidden seed is executed; the report lists every file changed. Then the orchestrator verifies, registers the digest, and audit pass 5b reads the code.

## Runs (wave 4, `experiment-runner`, after 5b's GO)

- From a clean clone at the one frozen commit 5b passed (§7.3). Every read through the seal.
- First the descriptive run on seed 20261029 (`h1-bands`), with the byte-identity check of `adversary.json`; then the confirmatory run on 20261118 (`quantile`); then a second confirmatory run for byte identity. Each in its own folder under `runs/`. Stop rule as §7.4.
- Rows for `docs/RESULTS.md` drafted by `experiment-runner`, written by the orchestrator after audit phase 2.
