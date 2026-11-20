# Audit pass 5b-bis — the fix wave's diff, before the frozen commit is named (iteration 5)

- **Agent:** `leakage-auditor` (fable), 2026-11-19. Read-only. Written by the auditor.
- **Object:** `git diff 6ab7e3e b71ba65` on branch `iteration-5`, and nothing else. The working tree equalled `b71ba65` throughout (`git status` showed untracked files only).
- **Verdict: GO with fixes.** No Blocker; 1 Major, 3 Minor, 9 Nits.
  - **The run path gets a plain GO.** `python/olsprime/bench/detectors.py` and `detector_stats.py` at `b71ba65` need no change. `b71ba65` can be named the frozen commit, code digest `3b59007a8111cc858bf01e15d7ed6636775903cbabce484ea3ac3b483ab4d5e5` (see Minor 2 for what that digest pins).
  - **Before wave 4 starts:** Major 1 and Minor 1, two guards in `wave4.py`, and Minor 2's sentence in the line that names the frozen commit. Major 1 is the one case found where `wave4.py` exits 0 though §7.3 says stop.
  - **No further re-look is needed** if the fixes touch only `wave4.py`, tests and text, on one condition: after the edit, `audit-5b-bis-scripts/y2_wave4_dry.py` runs to its last line on the edited file, and its scenarios L and M print "refused at the start" and "stopped". It drives every branch of `main()` with a fake `subprocess.run` and spawns nothing. I ran it on today's `wave4.py` and on a scratch copy that carries the three guards (`y2b_guarded_copy.py` writes that copy; it is a sketch, not the fix): it completes on both.
  - A change to `python/olsprime/` would change the code digest and would need another look at its diff.
- **Scripts:** `.claude/briefs/iteration-5/audit-5b-bis-scripts/` (Y1 to Y4 and Y2b, described under "Commands").

## Facts reproduced

- **Code digest at `b71ba65`:** `3b59007a…d5e5`, 88 files.
- **Development digest:** `e03f78b187c1f7a7b62681a6c16214f7bd79d7f13b58459521cacb731ad9bc48` on Windows AMD64, CPython 3.12.10, numpy 2.5.4; also under `wave4.py`'s environment (`PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`). It reads no bar.
- **Full suite:** 1743 passed, 5 skipped, 18 min 46 s under load.
- **Mutant test** (`OLSPRIME_MUTANTS=1`): 16 of 16 killed, 7 min 44 s. Each kill is one failed assertion in a behavioural test (JUnit: `failures="1" errors="0"`), never a collection error or the marker test. The unmutated copy passed first, and the repository's code digest was unchanged.

## Major

1. **`wave4.py` checks the code digest once, at step 0, and never checks or logs HEAD; yet both are recorded in every output** (`wave4.py:74-81`, `:109-112`; `provenance.py:67-69`).
   - **Scenario M, an exit 0 where §7.3 says stop.** A file under `python/olsprime/` is edited or merely re-saved between two steps: an editor that rewrites line endings is enough, since the digest hashes working-tree bytes (Minor 2). The descriptive and the confirmatory runs then record two code digests. `wave4.py` compares neither with step 0's, the rerun shares the later code, and the script exits 0. §7.3 asks for one frozen commit for both runs. Phase 2 would see it in the two `provenance` blocks, but after the confirmatory seed is spent.
   - **Scenario A, a false stop.** The orchestrator commits anything between the confirmatory run and its rerun. `detectors.json` and `detectors.md` then differ by one line, step 4 reports MISMATCH and exits 1. The dated line's "the `provenance` blocks are equal by construction" (`PROTOCOL.md:1099`) holds only if HEAD and `data/` do not move during wave 4.
   - **Scenario B, the expected path, not an edge case.** Both earlier passes were committed together with their wave. If the commit that carries this file and the line naming the frozen commit is made before wave 4, HEAD is that later commit when the runs start, and every official output records it, not `b71ba65`.
   - **Evidence.** Y2, scenario M: exit 0 after four steps on today's `wave4.py`; exit 1 at step 3 on the guarded sketch. Scenario A was observed: see "Identity across worker counts" below.
   - **Fix (`wave4.py` and text).** Log `provenance.git_commit()` at step 0. After each step, read the output's `provenance` and stop unless its commit and its code digest are those of step 0; this covers the HEAD re-read too. In the line that names the frozen commit, say which commit the outputs record (the frozen one, or a later one that changes no file under the digest's globs), and that nothing is committed or edited under `python/` while wave 4 runs.

## Minor

1. **`wave4.py` can be launched twice on one date, and the second launch runs the confirmatory line again over the first outputs** (`wave4.py:83-108`; `detectors.py:1957-1971`).
   - **Scenario.** The identity rerun mismatches, or the script is stopped by hand after step 3. A relaunch the same day repeats all four steps, runs seed 20261118 a second time, and overwrites `detectors.json`, `verdicts.jsonl` and the `.out` files in place. Nothing in `wave4.py` or in the CLI knows that the seed was already spent, and §7.4 asks that the next run be reported as run after a stopped attempt.
   - **A second effect.** `write` never removes an older `verdicts.jsonl`. If the second attempt stops, the first attempt's per-leak file stays beside a stopped `detectors.json`, where the dated line says it is "absent otherwise".
   - **Evidence (Y2).** Scenario L: with both confirmatory folders already present, `main()` exits 0 after four steps and says nothing. Scenario G3: a stale passing `detectors.json` is read as the new run's verdict when the new run exits 0 without writing; the CLI cannot do that today, since exit 0 follows `write`.
   - **Fix (`wave4.py` only).** Refuse to start if the log or any of the four output folders exists; a second attempt takes another `--date` or a suffix, and the first attempt's files stay. Removing a stale `verdicts.jsonl` in `write` would be a run-path change: not now.
2. **The code digest pins this working tree, not the commit** (`provenance.py:41-52`; text only).
   - **Cause.** `code_digest` hashes working-tree bytes. The index holds LF everywhere (`.gitattributes`: `* text=auto`), and this working tree holds CRLF in 64 of the 88 hashed files and LF in the other 24.
   - **Evidence.** The same files hashed in memory with other line endings: all LF, as a Linux or GitHub clone gives, `3778cfcadb7d9cca4355b95d60896856ce6e1fcc9b23bd69671acb87c9c072c3`; all CRLF, as a fresh Windows clone with `core.autocrlf=true` gives, `77851c2e9d1ffeafa11f50350ad5453d7e816075e79f5efe72b97167d37e14aa`. No clone of `b71ba65` gives `3b59007a…`.
   - **Consequence.** `wave4.py`'s step 0 is sound on this machine. But a reader of the paper cannot check the recorded digest from the public commit, and phase 2 cannot either.
   - **Fix (text).** In the line that names the frozen commit: the commit SHA is the identity; `3b59007a…` is the digest of the Windows working tree with its mixed line endings; `3778cfca…` is what an LF clone reproduces. Normalising line endings inside `code_digest` is a change for a later iteration, not for the freeze.
3. **Five mutants planted in the fix wave's own code all survive the detector tests** (Y4; tests only).
   - The 16 old mutants are killed, but they were chosen at pass 5b, before this code existed. Each survivor below ran all 166 tests of the six detector modules on a temporary copy, with 0 failures.
   - `n1`: the assertion of M1 under P counts nothing (`detectors.py:1018`, `= wrong` replaced by `= 0`).
   - `n5`: a missed flag under P is not a disagreement (`detectors.py:1016`).
   - `n2`: FI on M2 is never asserted, even where the rule predicts a flag (`detectors.py:1031`).
   - `n3`: the read-split row of TWO-RUN's primary arm takes all 8 runs (`detectors.py:1172`, `k <= 2` replaced by `k <= 8`). The test at `test_detector_verdicts.py:595-598` asserts `0 < primary <= the 8-run row`, which the wrong code satisfies with equality.
   - `n4`: `can_flag` is counted over every cut of the bench again (`detectors.py:1208`).
   - **Why it matters.** `test_m1_under_p_is_flagged_by_truncation_at_every_cut` and `test_m2_under_fi_follows_its_registered_rule` check the verdicts on synthetic bars; nothing checks that `check_classes` counts a disagreement. `test_fonsecas_classes_pass_on_the_degraded_bars` (`test_detectors.py:291`) asserts only that it passes. On the real bars these two assertions are what stops the run.
   - **Today's code is right on all five,** by reading and by the smoke runs' counts (16 of 16, 128 of 128, 28 of 28 under P; 16 and 128 predicted and flagged).
   - **Fix (tests only, no re-look).** Feed `check_classes` verdicts with one planted miss under P, one planted flag at a cut that cannot flag, and one FI miss at a predicted cut, and require one disagreement each; compare the primary arm's row with a sum over runs 1 and 2 taken from `judge_window`, and require it to be strictly below the 8-run row; give `control_can_flag` a leak whose `v` is undefined at a long-schedule cut only. Then add `n1` to `n5` to the mutant table: 21 mutants.

## Nits

- **N1. "`run` loads the registered table…"** (`PROTOCOL.md:1101`). The pin and the guard live in `main`, the `run` command (`detectors.py:2025-2048`). The function `detectors.run()` called from Python has neither. Write "the `run` command".
- **N2. "`provenance`, which holds the commit and the code digest"** (`PROTOCOL.md:1096`). It also holds `manifest_digest`; iteration 3's is `0ee7ac0f…`. `wave4.py` drops it with the rest. Log both manifest digests in the OK line: a difference is a fact for the list of contacts, not a stop.
- **N3. The NaN-to-null change went beyond its nit.** The nit named `share(k, 0)`. The fix also changed `mean_rate`, `newcombe_paired`, `paired_difference`, `_part` and the conventions' sentence, and added a rule to H15: an empty qualifier cell cannot trigger (`detector_stats.py:170-171`). None is reachable at n = 10,000. `render_md` handles a null share or cell (`_pct`, `_pts`), but not a null mean difference: `detectors.py:1921` formats it with `:+.2f`, which fails only on a population of no leak. The dated line does not mention the change: add one sentence. `paired_difference` over one leak still writes NaN limits (`detector_stats.py:108`), also unreachable.
- **N4. Two log lines of `wave4.py` mislead.** A step that exits 0 without its output file ends in a traceback, not a STOP line (Y2, scenarios D2 and G; fail-safe, and unreachable through the CLIs). When the rerun's exit code is not 0, the log still says "MISMATCH … compared byte for byte" though nothing was compared (`wave4.py:110-113`).
- **N5. The replay reads the bars before any platform check but `platform.system()`.** Step 1 runs H1's adversary, which has no pin; the pin first acts in step 2. Not a new contact (§7.1 allows this run). A step 0b can run the `digest` command and compare the digest it prints with `REGISTERED_DEVELOPMENT_DIGEST` (the command prints, it does not compare): 5 seconds, no bar read, and a wrong environment stops before the first read.
- **N6. `write` puts `verdicts.jsonl` and `detectors.json` on disk before it renders the Markdown** (`detectors.py:1968-1970`). A rendering error after the gate would leave a folder without `detectors.md` and `run.json`, and exit 1. I found no format site that a `null` can reach on the two registered lines. Log it; rendering first is a run-path change for later.
- **N7. The mutant harness goes round two patterns of the seal's scanner instead of asking for a rule.** `fixes-progress.md` (milestone 4) says so: `import subprocess` and `shutil.copytree` were flagged, so the copy is made with `read_bytes`/`write_bytes` and the runs go through `ProcessPoolExecutor` with `pytest.main`. The allow-list gained no rule, as asked, and the harness copies `python/` only, never `data/`. But the scanner's intent is bypassed, and the same route is open to any test. Log it; a later iteration either names the allowance or widens the scanner.
- **N8. `recompute` is not a reader written from the header.** It decodes through `det.read_verdict_file` and labels H15 through `ds.h15` (`test_detector_verdicts.py:107-114`, `:260`). Its aggregation is its own, and the round-trip test covers the decoder. Y3, which imports nothing from `olsprime` and decodes from the header's English text, agrees on 1,012 shares and cells at n = 200 and at n = 10,000. It could become a test.
- **N9. Two small gaps between text and code.** `metrics.long_schedule` keeps its shares under "all leaks" only, while §4.6 says "every share above"; the dated line's list of paths omits it, so the two agree, and the per-leak file lets phase 2 compute them. `wave4.py` passes the registered options in another order than the dated line writes them; the options and values are the same (Y2).

## The five checks, in order

1. **Each finding of pass 5b against its fix: done as asked, with the exceptions above.**
   - **M1.** `main` checks the table, then the pin, then the manifest, then the bars (`detectors.py:2043-2050`); a refused table or pin exits 2 before anything is read or written. `platform` is in `detectors.json` and `run.json`, on synthetic runs too; `platform_pin` is in `detectors.json`.
   - **M2 (Y1).** 365,568 combinations of population seed, TWO-RUN seed, bootstrap seed, placement, n, synthetic and table went through `registered_line_refusal`. On real bars exactly the two registered lines are accepted, each only with a table. A confirmatory seed is accepted nowhere but in its own slot of the confirmatory line. The `digest` command refuses all three.
   - **M4 (Y3).** Both qualifier cells and the deciding cell carry their 2x2 table. `verdicts.jsonl` is written only after the gate (`detectors.py:1848-1856`, `:1965-1968`), is absent on a stop (tested), and is byte-identical across worker counts (tested at n = 6; see below at n = 200). From the file alone, with my own decoder and my own Newcombe, I recomputed H15's three cells and its labels, every any-cut share and sensitivity share of the 27 variants under the three denominators, the family and position tables, the curves, the conventions and their sentence, the union, its misses and the long-schedule class, the placement-invariant subset, the cut-date bootstrap, the mirror asymmetry and the per-leak strings.
   - **Minors 5, 6, 7, 8, 9, 10, 11, 14 and the nits:** each does what its finding asked. Minor 6's exception for a truncation point on the last row is more than the finding asked; it is needed, structural, and written in the dated line. The stop rule still holds: the new `reported` fields (`M2 FI …`, the counts under P) are written only after every check passes, and a stopped run writes counts of disagreements only.
   - **Nothing else moved.** Only `detectors.py` and `detector_stats.py` changed under `python/olsprime/`. `two_run_bars`' loop was rewritten for the linter with the same effect.
2. **The new tests are independent enough, and the mutant test is sound.**
   - X3, X12, X11, X9, the catch rule's edge and the one-bit twin are scalar rewrites with their own seed keys, their own truncation and their own catch rule. X11 shares the convention evaluator with the code, as my script did; X9 rewrites that evaluator.
   - The 16 mutants are pass 5b's, string for string; `m8` is adapted to the three-valued rule with its meaning kept.
   - Limits: Minor 3, N7 and N8.
3. **The dated line of 2026-11-19 after pass 5b matches the code,** read sentence by sentence: the replaced predictions and their JSON keys, the sensitivity's rule and name, the six JSON paths of the denominators, the four command lines (Y2 parsed them out of `PROTOCOL.md` and compared them with what `wave4.py` runs), seeds 29119 and 29120 (constants, used by no run or test draw), the comparison of Minor 13, the header and the three bit vectors of the per-leak file, and the case study's choices against `casestudy.py`, which the diff does not touch. Exceptions: Major 1's "equal by construction", N1 and N2.
4. **Digest, draw path, allow-list, seeds: clean.**
   - The development digest reproduces at `b71ba65`.
   - `adversary.py`, `test_adversary.py` and `tests/allowlist.py` are not in the diff; the goldens pass in the full suite.
   - The three confirmatory seeds appear as literals only at `detectors.py:63-65` and in `wave4.py`. Tests reach them through the constants, on the predicate or with every draw stubbed to fail.
   - No `detectors.json` or `verdicts.jsonl` exists in the repository, and `runs/` holds no detector, replay or wave-4 output.
5. **`wave4.py`: it stops where the protocol says stop, with one exception** (Y2, 22 scenarios through `main()`, nothing spawned).
   - **Order.** Code digest and platform, then the replay, then the descriptive run, then the confirmatory run, then its rerun. A wrong digest calls nothing and exits 2.
   - **The replay.** A non-zero exit or a difference outside `provenance` stops before the descriptive run. The comparison is the dated line's: parsed, `provenance` removed, re-serialised with sorted keys and an indent of 2, bytes compared. The saved run was made with `--n 10000 --workers 8` (`runs/2026-10-29-h1-adversary/run.json`), and the adversary's CLI takes no seed or placement: its defaults are seed 20261029 and `h1-bands`.
   - **The descriptive run.** Exit 1 (stopped), exit 2 (refused) and exit 0 with `all_pass` false each stop before the confirmatory run. The exit code is tested before the file is read, so a stale passing file cannot rescue a failed run.
   - **The confirmatory run and its rerun.** The same three stops. The rerun fails on a different `detectors.json`, a different `verdicts.jsonl`, an extra file, a missing file or a non-zero exit.
   - **The lines.** The three detector lines pass `registered_line_refusal`; the rerun is the confirmatory line with `--workers 4`; the four output folders are distinct; `--table` resolves from `python/`.
   - **The exception is Major 1's scenario M:** code that moves between two steps gives an exit 0. I found no other way for it to exit 0 where the protocol says stop. Its other weak points are on the safe side: Minor 1, Major 1's scenario A, N4, N5.

## Identity across worker counts, with the real gates

The tests compare 1 worker with 2 at n = 6, gates stubbed. I ran the orchestrator's synthetic line again at `b71ba65` with `--workers 4` (n = 200, seeds 51118 and 51119, bootstrap 4242, `quantile`), and compared it with the orchestrator's 8-worker run in `smoke-200`:
- `verdicts.jsonl`: byte-identical (426,397 bytes).
- `detectors.json` and `detectors.md`: one line differs in each, the Git commit (`6ab7e3ed…` in the first, `b71ba654…` in mine). HEAD moved between the two runs. This is Major 1, scenario A, observed.

## Not checked

- **The real-bar path of `main`** past the guard: exercised only by the tests' stubs (table, pin, manifest, bars in that order). No registered line was run, by rule.
- **The bars' properties** that pass 5b listed: a real cut whose next-day high is below two thirds of the close, a zero-volume bar, a cut whose `t + 1` is the last row. Minor 14's refusal and Minor 6's `cannot_flag_last_row` are tested on synthetic or fake inputs only.
- **WSL2 and Linux.** The pin's refusal on another platform is tested with an injected wrong digest, not on another platform.
- **The code digest of `6ab7e3e`** (`8607e7c4…`): not recomputed, since no checkout was allowed. Minor 2 applies to it as well.
- **`cargo test`, Kani, ruff:** not run; the diff touches no Rust file.
- **The 50-leak gates on real bars:** the gates passed in three synthetic runs (n = 200 twice, n = 10,000 once).
- **`docs/ITERATIONS.md`'s added lines** beyond the counts I reproduced (1,743 passed, 5 skipped; 16 of 16; `3b59007a…`). Its two "candidate" next steps are marked unregistered and were not audited.
- **Newcombe's 1998 paper:** still not re-read; my rewrite is the same method 10 as at pass 5b.

## Contacts

- **Real bars: none.** No read of `data/`, no vault, no `series.npz`. No descriptive, confirmatory or adversary command line was run.
- **Seeds 20261118, 20261119, 20261120: never drawn.** They were reached only through the module's constants, on `registered_line_refusal`, and as text parsed from `PROTOCOL.md` and from `wave4.py`'s argument lists (Y2, nothing spawned). My scripts hold none of them as a literal.
- **Seeds executed:** 51118 and 51119, bootstrap 4242, on synthetic bars; the tests' own seeds.
- **`runs/`, read only:** `2026-11-18-quantile-table/table.json` (the digest command, the tests, one synthetic run); `2026-10-29-h1-adversary/run.json`; the top-level keys, the `provenance` block and `config.seed`/`config.n` of `2026-10-29-h1-adversary/adversary.json`. Nothing was written to `runs/`.
- **The orchestrator's scratch folder, read only:** `smoke-200/`, `smoke-10000/` and their logs.
- **Written:** this file; `audit-5b-bis-scripts/`; scratch outputs under the session's scratchpad (`audit5bbis/`).
- **The test suite reads no real bar:** `tests/conftest.py` points the data root, the runs folder and the vault at empty temporary folders for every test.

## Commands

All from `C:\Users\abdou\ols-prime\python`, with `uv run --no-sync`. Scratch is `<scratchpad>\audit5bbis\`.

- `git diff 6ab7e3e b71ba65` (whole, and per file into scratch), `git diff --stat`, `git diff --name-only`, `git status --short`, `git rev-parse HEAD`, `git ls-files --eol`, `git config --get core.autocrlf`, `git grep` at `b71ba65`. No command that rewrites the tree.
- `python -c "from olsprime.bench.provenance import code_digest; print(code_digest())"`.
- `python -m olsprime.bench.detectors digest --seed 51118 --placement quantile --table ../runs/2026-11-18-quantile-table/table.json`, twice: plain, and with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`.
- `pytest -q -p no:cacheprovider`: 1743 passed, 5 skipped.
- `OLSPRIME_MUTANTS=1 pytest -q -p no:cacheprovider tests/test_detector_mutants.py -rA --basetemp=<scratch>\mutants-tmp`: 2 passed, 16 of 16 killed; the JUnit reports of the 17 copies were read.
- `python -m olsprime.bench.detectors run --synthetic --seed 51118 --two-run-seed 51119 --bootstrap-seed 4242 --n 200 --placement quantile --table ../runs/2026-11-18-quantile-table/table.json --workers 4 --out <scratch>\smoke-200-w4`: exit 0, every assertion and gate passed, 969 s. Then `cmp` and `diff` against `smoke-200`.
- An in-memory rehash of the 88 files of `code_digest` with LF and with CRLF line endings (Minor 2); nothing written.
- **Y1,** `y1_guard_grid.py`: the guard over 365,568 argument combinations, on the predicate only.
- **Y2,** `y2_wave4_dry.py <scratch>\w4dry [path of a wave4.py]`: `wave4.py` loaded by path, `subprocess.run` replaced by a fake, `RUNS` and `SAVED_ADVERSARY` repointed to scratch; 22 scenarios; the command lines compared with `PROTOCOL.md`'s. Run on the repository's file and on the guarded sketch.
- **Y2b,** `y2b_guarded_copy.py <scratch>\wave4_guarded.py`: writes to scratch a copy of `wave4.py` with the three guards (Minor 1, Major 1, N5). The repository's file is read, never written.
- **Y3,** `y3_verdicts.py <run folder>`: `verdicts.jsonl` decoded from its header's description with no `olsprime` import, `detectors.json` recomputed; on `smoke-200` and on `smoke-10000`.
- **Y4,** `y4_new_mutants.py <scratch>\newmut`: five new mutants on temporary copies, through the repository's own harness imported as it is; 5 of 5 survived; repository code digest unchanged.

## Bolder next step (auditor)

**Measure the platform, instead of only refusing it.** The pin says that another platform draws another population; nobody knows yet whether it gives other rates. The per-leak file now makes that a diff:
- run the synthetic line (seed 51118, n = 10,000, `quantile`) once on Windows and once in WSL2, where the pin is skipped and `table.json` is readable through `/mnt/c`;
- compare the two `verdicts.jsonl` leak by leak: how many of the 10,000 leaks change an any-cut verdict, per detector, and how many change H15's cell;
- report the count in `docs/RESULTS.md` beside the digests, as a property of the bench on synthetic bars, never as a rate on real bars.

It costs no contact with the real bars and no confirmatory seed, and it turns "the population depends on the platform's `exp`" into a number the paper can state. If the count is zero, the paper can say that the platform changes the digest and no verdict on synthetic bars; if it is not, the paper says how many.
