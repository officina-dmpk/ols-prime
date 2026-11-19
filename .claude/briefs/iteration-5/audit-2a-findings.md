# Audit phase 2a — wave 4's numbers and the case study, before any row enters `docs/RESULTS.md` (iteration 5)

- **Agent:** `leakage-auditor` (fable), 2026-11-19. Read-only. Written by the auditor.
- **Object:** the outputs of wave 4 (`runs/2026-11-19-*`), the `wave4.py` that ran (`f12b9b5`), the case study's one real call (`runs/2026-11-19-casestudy/`), and the two dated lines of `docs/PROTOCOL.md` that log them. The code is the frozen one: `code_digest()` gives `3b59007a8111cc858bf01e15d7ed6636775903cbabce484ea3ac3b483ab4d5e5` (88 files), and `git diff b71ba65 -- python crates` is empty.
- **Verdict: GO with fixes.** No Blocker, no Major; 5 Minor, 8 Nits. Every fix is text: no number is wrong, and nothing needs a rerun.
  - **The numbers can enter `docs/RESULTS.md`.** My reader recomputed 2,804 rows of the two `detectors.json` from the two `verdicts.jsonl`; 2,795 agree. The 9 others are one explained difference (Nit 3: the run clips a normal interval at 1).
  - **The descriptive run reproduces iterations 3 and 4 leak by leak** (script A2): FI's 160,000 cut verdicts and its 10,000 long-schedule counts equal `runs/2026-10-29-h1-adversary/adversary.json`; SHUFFLE's 160,000 counts of moving twins equal `runs/2026-10-30-twins/twins.json`; both constancy flags and the four tags agree. This shows no drift since those runs, and that the per-leak columns decode as the header says. It is not an independent implementation: the detectors' FI runs on the adversary's own bench and is asserted equal to its fast path inside the run, and SHUFFLE reuses iteration 4's twin bars.
  - **The Minors are sentences.** H15's labels stand as the run wrote them. Four things beside them decide how the paper may word them (Minors 1 to 3), and one reported count is not what §3.3 names (Minor 4).
- **Scripts and tables:** `.claude/briefs/iteration-5/audit-2a-scripts/` (A1 to A8, under "Commands"), with the two full tables `table-confirmatory.tsv` and `table-descriptive.tsv`: 1,473 rows each, with the JSON path, the run's value, mine and the verdict.

## Minor

1. **H15's cell compares one run of TRUNC-0 with two runs of FI; at one run per cut the direction depends on which FI run** (`metrics.equal_run_counts`, `metrics.detectors["FI /3"]`; text only).
   - **Confirmatory run.** FI's ×3 run alone catches 93.58 %, its ÷3 run alone 96.28 %, TRUNC-0 94.82 %.
     - `metrics.equal_run_counts["FI x3 - TRUNC-0"]`: −1.24 points, Newcombe [−1.67, −0.82], b = 171, c = 295. TRUNC-0 is **above** FI's ×3 run.
     - FI ÷3 alone minus TRUNC-0, mine only (the run does not write this pair): +1.46 points [+1.00, +1.92], b = 347, c = 201.
   - **Descriptive run.** The same pattern: ×3 alone −0.60 [−1.10, −0.10], ÷3 alone +1.92 [+1.38, +2.47] (mine only).
   - **Why it matters.** §5 lists the equal-count comparisons "beside it, never deciding", and §4.8 registers ×3 alone only. A sentence "truncation catches fewer leaks than future invariance" with H15's cell alone would be read as a property of the mechanism. §6 forbids "FI is better or worse than truncation in general".
   - **Fix (paper and `RESULTS.md` row).** State H15's labels with the run counts, and put both one-run pairs beside them. Name the ÷3 pair as computed in audit phase 2a from `verdicts.jsonl`, not registered.
2. **The registered sentence "H15's verdict is date-dependent" fires, and read alone it says more than the bootstrap shows** (`metrics.cut_date_bootstrap`; `detectors.md`, H15 section; text only).
   - **It fires.** 2.5th and 97.5th percentiles −6.38 and −2.95 points, spread 3.43 > 1 (descriptive: −7.90 and −4.73, spread 3.17). Reproduced from the stored verdicts with the header's seed; another seed with 20,000 subsets gives −6.35 and −2.93.
   - **What moves is the size, not the labels.** On each of the 2,000 registered subsets I computed Newcombe's interval and read H15's two labels: "below FI" and "by more than 1 point" in 2,000 of 2,000, in both runs. The smallest gap of any subset is −2.51 points (descriptive: −4.42).
   - **Two facts to put beside it.** The subsets are drawn from the long schedule, not from H1's dates. On all 64 dates (128 cuts) TRUNC-0 minus FI is −2.00 points [−2.34, −1.68], mine only, against −3.75 on H1's 8 dates: more cuts close the gap, since both any-cut shares rise.
   - **Fix (paper).** Keep the registered sentence, as §4.15 binds it, and add what it covers: the size of the difference depends on the dates; its sign and the 1-point label did not change in any subset.
3. **"By more than 1 point" is the label of one cell: all leaks, convention G. Most of the gap sits in the leaks that are constant at the compared rows** (`metrics.h15`; text only).
   - **The qualifier does not fire,** as the run says: under convention M −3.35 [−3.78, −2.93], on the not-constant denominator −1.08 [−1.32, −0.87]; both have the deciding cell's sign.
   - **But the margin label is not stable.** On the not-constant denominator the interval straddles −1: H15's rule would read "1-point margin not resolved" there. Under M on the not-constant leaks it is −0.74 [−0.94, −0.58], "within 1 point" (mine only).
   - **Where the gap is.** Of the 818 leaks constant at H1's compared rows, FI catches 682 and TRUNC-0 406: 276 of the net 375 leaks of the deciding cell. On a constant binary leak, truncation's verdict is the convention's (pass 5a, B2), while FI's perturbed bars move it.
   - **Convention P reverses the sign by construction:** +1.43 [+1.21, +1.68], reported beside, never deciding (§5). On the not-constant leaks: +0.08 [+0.02, +0.16].
   - **Fix (paper).** Give the label with its cell, and the not-constant cell and P beside it. The registered sentence of §4.5 already carries the range 94.82 % to 100 %.
4. **`reported.classes["M2 …"]["TWO-RUN"]` counts every one of TWO-RUN's 16 runs, both σ, not "TWO-RUN (σ = 0.1)" as §3.3 names it** (`detectors.py:1034`; `PROTOCOL.md` §3.3; text only).
   - **The count.** `v[k].any(axis=1)` over the raw key `TWO-RUN`, whose 16 columns are σ = 0.1 runs 1 to 8 and σ = 1.0 runs 1 to 8. Confirmatory: 14 of 16 cuts and 116 of 128; descriptive, with TWO-RUN seed 29119: 15 of 16 and 117 of 128.
   - **Why it cannot be the primary arm.** M2 is `close[s+1] > 2 · close[s]`. Only row `t` reads a perturbed bar, and flipping it needs a factor near 2 on `close[t+1]`. At σ = 0.1 that is a draw near 7 standard deviations. At σ = 1.0 one run does it with probability about 0.24, and eight runs with about 0.89: 14.3 of 16 cuts, as observed.
   - **Consequence.** "TWO-RUN flags M2 at 14 of 16 cuts" would be attributed to the registered arm (σ = 0.1, 2 runs), which almost surely flags it at none. The per-run verdicts of the hand-written classes are in no output, so the σ = 0.1 count cannot be recomputed without a new contact.
   - **Fix (text).** Either the paper does not quote this count, or it says "by any of TWO-RUN's 16 runs (σ = 0.1 and 1.0, 8 runs each)". Add one sentence to the next dated line of `PROTOCOL.md`. SHUFFLE's count (6 of 16, equal in both runs) is as registered: 8 twins.
5. **The case study: two sentences its numbers do not allow, and one they force** (`runs/2026-11-19-casestudy/casestudy.json`; exploratory, test months; text only).
   - **"The known strategies explain none of the difference" is not what "share left ≈ 1" shows.** The intercept keeps 102.3 % of `matrix-select − climatology-panel` and 100.5 % of `enc-ols − enc-softmax` because `explained = Σ β · mean(payoff)` is small: +0.000241 against a mean difference of −0.010526, and +0.000014 against −0.002687. A payoff mean enters, not a loading (means: reversal 6.8e-6, momentum 6.5e-6, volatility-timed momentum 0.0114 against a standard deviation of 0.749; the JSON gives no interval on them, so I do not call them zero). The loadings are not zero: for `matrix-select − climatology-panel`, R² is 0.118, with momentum at t = +6.25 and volatility-timed momentum at t = +7.47. The dated line already calls the regression "an attribution after the fact"; the sentence must also say that the difference co-moves with the momentum payoffs, and that the intercept barely moves because the fitted payoffs' contribution to the mean is +0.000241.
   - **The split answers the first reading, against us, and the paper has to say so.** For `matrix-select`, all of the log-loss gain over climatology is the move part: +0.01156 [+0.00963, +0.01369] of a total of +0.01053; the direction part is −0.00104 [−0.00254, +0.00036]. Its skill on "direction given a move" is below climatology: Brier skill −0.0051 [−0.0089, −0.0013], log-loss skill −0.0065 [−0.0104, −0.0028]. For the two encoder arms the direction skill is not separated from 0 (`enc-ols` −0.0008 [−0.0027, +0.0011]; `enc-softmax` +0.0007 [−0.0010, +0.0023]). The edge of `enc-ols` over `enc-softmax` is in the move part too (+0.00986 against +0.00683; direction parts −0.00015 and +0.00020). On these months, the 0.013 Brier skill is skill at saying whether a move comes, not which way.
   - **No year may be singled out.** The split gives 126 intervals (3 arms, 7 periods, 6 quantities) at 95 % each, with no adjustment, on months already scored: about 6 would exclude 0 by chance alone. The yearly rows describe the spread; a sentence such as "in 2021 the direction skill is positive" is not available.
   - **Fix (paper).** Word the three points as above, each with "exploratory, test months".

## Nits

- **N1. "The stderr of every step holds no warning"** (`PROTOCOL.md:1140`). Each of the three detector steps wrote 26,700 lines "fold YYYY-MM skipped: no test row" to stderr, through `log.warning` (`eval/splits.py:125`). They are expected and exactly accounted for: the TRUNC-0 gate runs H1's own path on really truncated bars, 100 units (50 leaks × 2 pairs) at 8 cuts, and the folds after each cut have no test row: 71 + 54 + 47 + 36 + 22 + 19 + 18 + 0 = 267 per unit. No traceback and no `RepairFailed`: true. Reword the sentence.
- **N2. `mcnemar_exact_p` is 0.0 in four pairs of each run** (`FI - TWO-RUN`, `TWO-RUN - SHUFFLE`, `FI - TWO-RUN s0.1 r2`, `TWO-RUN s0.1 r1 - TRUNC-0`), and `detectors.md` prints "0". It is a float underflow: the exact values, from integer arithmetic, lie between 10^-470 and 10^-327 (the tables give each log10). The paper writes "p < 10^-300", never "p = 0".
- **N3. The normal interval of a mean per-cut rate is clipped to [0, 1]** (`adversary._mean_rate`). Nine rows of the confirmatory run differ from my unclipped value for that reason only, all under convention P, where the rate is within 2e-5 of 1: `metrics.detectors[k].mean_per_cut_rate[d]` for k in `TRUNC-0/P`, `RETILE/P@ends`, `ENDS/P@ends` and the three denominators. Mean and lower limit agree. A normal interval at a rate of 0.99999 means little: give those rows without an interval.
- **N4. Wilson limits at the boundary carry float noise:** a lower limit of 8.5e-22 where the count is 0, an upper limit of 0.9999999999999999 where the share is 1 (`metrics.read_split`, `metrics.mirror_asymmetry`). Rounding hides it; do not copy the raw digits.
- **N5. `predicted_flagged` is the number of predicted cuts, not of cuts predicted and flagged** (`detectors.py:1032`: `int(predicted.sum())`). That every one of them was flagged is the assertion of line 1031, whose count is inside `assertions["§3.3 …"].by_class["M2"]`. The dated line's "16 of 16 and 128 of 128 predicted, and flagged" is right, for that reason and not from the key. See step 3.
- **N6. `reported.controls.can_be_flagged` rests on `detectors.py:1208` as read.** I could not make a probe separate "at H1's 16 cuts" from "at every cut of the bench": 0 of 150 leaks on degraded synthetic bars and 0 of 3,000 on plain ones have a control that the two counts treat differently (A7, A7b). The line is right by reading. If the paper quotes the count (296 of 9,050 controls under FI and under TWO-RUN, 472 under SHUFFLE, 9,050 under truncation, per kind), it uses §3.2's words: "`v` is missing or undefined at some compared row in some run", the original run included. TWO-RUN's 296 with 0 flags is that definition, not a miss.
- **N7. The case study's contact line can be more exact on two points** (`PROTOCOL.md:1144-1157`, uncommitted). The seal cuts at the vault's start, not at the validation year's: `load_klines` returned the 2025 hourly bars of the 233 pairs too, and `load_bars` dropped them (`known_at < DEVELOPMENT.end`) before anything was computed. "Cut to `known_at < 2025-01-01`" is true of what reached the signals; say that the 2025 rows were read and dropped. And `runs/2026-11-19-casestudy.log` holds no command line: the command is known from the dated line and from `config.json`'s two input paths.
- **N8. The label is on the top-level keys of the case study's JSON, not on every key** (`casestudy.py:619-637`; the brief's step 4 says "every key"). The module's docstring says top-level keys, and pass 5b read it so. A number copied from a nested key, such as `skill_split.arms[...]`, travels without its label: each `docs/RESULTS.md` row and each sentence taken from it must write "exploratory, test months" by hand.

## The five steps of the brief

### 1. The numbers, recomputed from `verdicts.jsonl`

- **The reader (A1)** imports nothing from `olsprime`. It decodes the three bit vectors from the header's English text by index arithmetic (bit `i` is bit `i mod 8` of byte `i div 8`), builds the 42 variants from §2 and then compares them with the header's own list, and uses its own Wilson, Newcombe (method 10, the continuity-corrected ψ), exact McNemar (integer binomial sums) and bootstrap. It never stops: every row is written.
- **Result:** 1,473 rows per run. Confirmatory: 1,393 agree, 9 differ (N3), 49 are mine only, 22 are read from `detectors.json` and cannot be recomputed. Descriptive: 1,402 agree, 0 differ, 49 mine only, 22 read. Counts are compared exactly, floats at 1e-9, p-values at a relative 1e-6.
- **Two older readers agree as well:** pass 5b-bis's Y3 (1,012 shares and cells per run, "Y3 OK" on both) and `python -m tests.test_detector_verdicts` (both folders).
- **The denominators are the run's own columns.** "Not constant", `designed: no` and the placement-invariant subset are built from the flags and tags that `verdicts.jsonl` stores for each leak. Every share on them is recomputed given those flags. On the descriptive run the constancy flags and the tags equal iteration 3's and iteration 4's for every leak (A2); on the confirmatory run, and for `placement_invariant` in both, nothing outside the run witnesses them.
- **What the file cannot give,** and is therefore read, not recomputed: the honest twins' verdicts (0 flags under each of the 9 bench keys, 10,000 twins evaluated, in both runs), the read split (row level; its parts sum, and no truncation row has a changed-value catch), the count of distinct expressions (8,434 and 8,533), the assertions, the gates, the controls and TWO-RUN's repair statistics.
  - **The twins' assertion covers what §3.1 lists** (`detectors.py:1181-1187`): `judge_all` on the twin gives FI, TWO-RUN (16 runs, both σ), SHUFFLE (8 twins), the truncation bench under G, M and P (TRUNC-0, TRUNC-1 and the 28 ends, both schedules) and RETILE under G, M and P; a flag or a single changed bit anywhere counts.
  - **On the descriptive population** the replay gives a second witness for FI: H1's own adversary reports "twins caught 0, bit violations 0".
- **Identities shown from the file alone:** RETILE equals ENDS at each of the 28 ends for every leak, under G, M and P, under both rules (0 differing cells of 280,000 per convention); no cell is set under the sensitivity rule and not under H1's rule; the cells that convention P does not flag number exactly the exception cuts of `reported.p_assertion` (TRUNC-0: 69 and 71; TRUNC-1: 190 and 204; ENDS: 5 and 4).
- **The two runs share the bars:** their cut lists and bit layouts are equal, the 16 cuts and 128 long cuts are those of iteration 3's `adversary.json`, and every class count that draws nothing is equal in both (M1, FI on M2, SHUFFLE on M2). TWO-RUN's M2 counts differ with its seed, as they should.

### 2. `wave4.py` as run, against its log

- **The file.** `git diff f12b9b5 -- .claude/briefs/iteration-5/wave4.py` is empty: the working tree holds the file that spent the seed. I read it whole (183 lines), not the diff alone.
- **The log, line by line** (`runs/2026-11-19-wave4.log`, 16 lines):
  - step 0 logged the platform (Windows AMD64, Python 3.12.10), HEAD `f12b9b5c…` and the code digest `3b59007a…`; the refusals for another platform or digest come before any child process;
  - step 0b ran the `digest` command, which printed `e03f78b1…bc48` (`…-wave4-pin.out`), before the replay read a bar;
  - the replay, the descriptive run, the confirmatory run and its rerun follow in that order, each START with the registered options in the dated line's order, each END with exit 0.
- **Stop conditions, as coded.** After each of the four steps, `checked` stops on a non-zero exit, on a missing or unreadable output, and on an output whose `provenance` does not record step 0's commit and code digest. Steps 2 and 3 also stop unless `all_pass`. The replay stops on any difference outside `provenance`. The rerun's verdict is the byte comparison of every file but `run.json`, with the file lists compared first.
  - `checked` logs nothing when it passes, so the log has no line saying that the provenance was checked. I checked it in the outputs: all four record `f12b9b5c9dbab6913cbfd7b2752df6e4235c595e`, `3b59007a…` over 88 files, and the manifest digest `0ee7ac0f…`.
  - The rerun's `all_pass` is not tested by itself; byte equality with the first run covers it.
- **The byte comparison of the rerun, redone:** `detectors.json`, `detectors.md` and `verdicts.jsonl` have the same SHA-256 in both folders; the two `run.json` differ (654.0 s with 8 workers, 986.5 s with 4).
- **Every SHA-256 of a file that the two dated lines cite, recomputed, all equal** (the data manifest digest `0ee7ac0f…` is the exception: I compared it across the recorded outputs and did not recompute it, since that means hashing `data/`):
  - `2026-11-19-wave4.log` `29ba4fb1…5cd4`; the replay's `adversary.json` `a5b71eb4…fcc0`;
  - descriptive `detectors.json` `0b4b06f4…b911` and `verdicts.jsonl` `f34327db…6a3d`;
  - confirmatory `detectors.json` `09f9470e…2cdb`, `detectors.md` `98a050ee…1f9f`, `verdicts.jsonl` `96375610…a38d`;
  - `2026-11-19-casestudy.log` `125ad5d3…f5da`; `casestudy.json` `8d87294b…bcac`, `casestudy.md` `7b308f10…9653`, `config.json` `ecc38cf2…4277`, `run.json` `36e24c7b…ea0c`;
  - `table.json` `527e01ba…3c43`; the two `series.npz` `691e7ea7…b843` and `e8381799…4249`.
- **Also reproduced now:** the code digest `3b59007a…` (88 files), and the development digest `e03f78b1…bc48` by the `digest` command (seed 51118, no bar read).
- **The `.out` files.** Each detector step printed one line to stdout, the headline, after its gates: no rate and no per-leak line before them (§7.4). The stderr is N1's.

### 3. Minor 3 of pass 5b-bis, deferred: the five lines, the counts, and what rests on them

- **The five lines, re-read at the frozen code, are right.**
  - `detectors.py:1016`: under P, a cut that can flag and is not flagged, or a cut that cannot flag and is flagged, adds one.
  - `:1018`: that sum is the class's count of disagreements.
  - `:1031`: a cut where the rule predicts a flag and FI gives none adds one to M2's count.
  - `:1172`: the primary arm's read-split row takes the columns whose σ is the first one (0.1) and whose run number is 1 or 2.
  - `:1208`: `can_flag` is evaluated at `h1_rows_of[key]`, H1's 16 cuts of each bench.
- **Predicted against flagged, in both runs' `reported.classes`:** M1 under P is flagged at 16 of 16, 128 of 128 and 28 of 28 cuts for each truncation detector, with `cannot_flag_last_row` 0 everywhere; FI on M2 has 16 and 128 predicted cuts, 0 not predicted, 0 flagged where not predicted. The two runs give the same counts, as they must: these classes draw nothing.
- **Beyond the brief, three of the five mutants are now answered by behaviour** (A6, A7; synthetic bars, development seeds, the source untouched). I altered in memory the verdicts that `check_classes` reads, one plant at a time: a missed flag of M1 under P, two of them, a flag at a cut declared unable to flag, a flag of M1 under G, a missed FI flag on M2, three of them. Each time the class's count moved by exactly the planted number, no other count moved, and `pass` became false: 6 of 6. For line 1172, over 150 leaks, the code's row equals my sum over the runs labelled σ = 0.1, 1 and 2 (3,208 flagged rows) and is strictly below the 8-run row (13,137). In the real outputs the same row is 232,615 against 933,338 (24.9 %).
- **Does a registered sentence rest on a `check_classes` count that the two checks cannot verify?**
  - **"No cut whose truncation point is the series' last row" (`PROTOCOL.md:1142`): no.** It follows from the cut lists in the header of `verdicts.jsonl`: the largest truncation points are row 2665 (TRUNC-1 at H1's last cut), 2653 (the long schedule) and 2691 (RETILE's last end, 2024-12-29). That none of them is the series' last row is shown by the flags themselves: a truncation at the last row removes nothing and could flag no leak under any convention, yet under P only 5 of the 280,000 ENDS cells are unflagged, 69 of the 1,440,000 TRUNC-0 cells and 190 of the TRUNC-1 cells (descriptive: 4, 71, 204). The assertion of §2.3 counts the same thing by another path (0 on both schedules).
  - **"16 of 16 and 128 of 128 predicted, and flagged" (`PROTOCOL.md:1143`): partly.** "Predicted" is `fi_m2_rule` on the bars, which I may not read; on a market without a daily gap, `high[t+1] ≥ open[t+1] ≈ close[t]`, far above two thirds of `close[t]`, so 0 "not predicted" is what one expects. "And flagged" is line 1031's zero, not a stored verdict (N5). With A6's plants the line is shown to count. **Rated Nit:** the sentence is true, its evidence is an assertion and not a recomputation.
  - **TWO-RUN's and SHUFFLE's counts on M2: reported only,** and TWO-RUN's is not the arm §3.3 names (Minor 4).
  - **`can_be_flagged` (line 1208) is not a `check_classes` count,** but it is the one of the five I could verify only by reading (N6).

### 4. The case study

- **The inputs, by digest.** `runs/2026-10-30-report2-wsl/series.npz` hashes to `691e7ea7…b843` and `runs/2026-10-30-report3/series.npz` to `e8381799…4249`: the registered constants of `casestudy.py:116-117`, which `docs/RESULTS.md:23` and `docs/reports/report-3.md:171-172` carry in committed text. Both are regular files, not links. `report3.json` names Report n°2's series as its base.
- **The vault was not read. The evidence is of two kinds, neither of them a digest of the vault's copy** (I opened and hashed nothing under `runs/vault/`; git enumerated its entry names).
  - **By path.** The command line names two folders, and `config.json` records them (`..\runs\2026-10-30-report2-wsl`, `..\runs\2026-10-30-report3`). The only reader of a `series.npz` is `power.load_series`, which first resolves the path and refuses, before a byte is read, anything under `<runs>/vault` (`power.run_output`, `power.py:197-215`). Nothing else in `casestudy.py` opens a file but `load_klines` and the three outputs.
  - **By the seal's state.** Every output of 2026-11-19, the case study's `config.json` included, records the data manifest digest `0ee7ac0f…`, the one iteration 3 recorded with the vault sealed; `vault_open` and the vault tree's summary are part of the manifest's body (`manifest.py:114-116`), so an open vault would have changed it. `git status --ignored` shows `runs/vault/` as ignored content only: neither `OPEN` nor `ACCESS.log` exists, since `.gitignore` excepts both. Sealed, `load_klines` reads `data/` only.
  - **What I cannot say:** whether the copy's bytes equal one of the two registered files. If they do, the digest check alone could not tell the paths apart; the path guard does.
- **The cut.** `load_bars` keeps `known_at < DEVELOPMENT.end` (2025-01-01 00:00 UTC). On a synthetic frame the last bar kept opens at 2024-12-31 23:00 and none at or after the end survives (A5). Each scored row takes its positions at its own bar, found by `open_time`, and the run refuses unless that bar's `known_at` is the row's decision time (`casestudy.py:488-495`). The last scored hour is 2024-12-30 22:00. See N7 for the 2025 rows that were read and dropped.
- **The builders are past-only and are the registered formulas** (A5, synthetic bars). Changing every close after `t`, at 60 values of `t`, moves no position at or before `t`, bit for bit. A scalar rebuild from the dated line's text agrees at every bar: reversal `−r_t`; momentum `ln(c_{t−1} / c_{t−25})`; volatility-timed momentum `momentum / (24 · v_t)`, `v_t` the uncentred mean of the last 90 squared returns, 0 where `v_t = 0`. A missing hour makes every window that spans it missing; nothing is bridged. `casestudy.py` is unchanged since `6ab7e3e` (`git diff` empty).
- **The choices of the dated line, against what ran.** The regressors are payoffs (`hourly_payoffs`: position times the row's realized `fwd_return`, averaged over the hour's rows). `casestudy.json` records `hac: {kernel: bartlett, lags: 168}` in both regressions, and `config.json` `hac_lags` 168, `momentum_bars` 24, `volatility_bars` 90; `registered` is true. The Bartlett weight in the code is `1 − lag / 169`.
- **The labels.** Every top-level key of `casestudy.json` (6), `config.json` (4) and `run.json` (3) ends with "(exploratory, test months)"; so do the 5 headings and the 4 table headers of `casestudy.md`, and the line of payoff correlations. Nested keys do not repeat it (N8).
- **The numbers, recomputed from `casestudy.json` alone** (A4: 382 checks, 0 failed; no `series.npz` array was loaded).
  - **Each regression:** `t = estimate / hac_se`; `p` from Student's t with 50,626 − 4 degrees of freedom (− 2 for the single fits); `per_std = β · std`; `explained = Σ β · mean`; `mean_difference = intercept + explained`; `share_left = intercept / mean_difference`; for each single fit, `mean_difference = intercept + slope · mean`.
  - **The joint fit against the single fits,** through the normal equations: `slope_alone_j · std_j = Σ_k ρ_jk · β_k · std_k` holds for the three payoffs of both regressions; the three single fits imply the same variance of the difference; and the joint R² follows from them (0.0015 and 0.1175).
  - **The split:** every skill is `1 − arm / climatology` of the stored means; `total = move + direction` with `parts_gap` below 1e-12; the yearly means pool to the "all" row, weighted by hours (or by direction hours); hours, rows and moving rows sum over the years (50,626; 1,493,353; 841,592); every interval contains its estimate and has 2,000 resamples; the three arms imply one three-class climatology log-loss per period, and for "all" it is Report n°2's.
  - **The two analyses against each other:** the mean of `matrix-select − climatology-panel` is minus the arm's total gain, and the mean of `enc-ols − enc-softmax` is minus the difference of the two arms' total gains.
  - **Against the reports:** the three-class Brier skills equal the `bss` of `report2.json` and `report3.json` to the last digit: `matrix-select` 0.013035189797247937, `enc-ols` 0.010983203493732385, `enc-softmax` 0.007852451362825863.
  - **Not recomputable from the JSON:** the bootstrap intervals, the HAC standard errors, the payoffs themselves.

| `casestudy.json` path, under each key's "(exploratory, test months)" | the run | mine | |
|---|---|---|---|
| `factor_control["enc-ols - enc-softmax"].mean_difference`, `.mean_difference_hac_se` | −0.002687, 0.000522 | read | |
| `… .intercept`, `.explained`, `.share_left`, `.r2` | −0.002701, +0.000014, 1.0051, 0.0015 | the same from the coefficients and payoff means | agree |
| `… .coefficients` reversal, momentum, vol_timed_momentum: `t` | −2.688, +1.211, +1.520 | the same, and the p-values 0.0072, 0.2258, 0.1285 | agree |
| `factor_control["matrix-select - climatology-panel"].mean_difference`, `.mean_difference_hac_se` | −0.010526, 0.001264 | read | |
| `… .intercept`, `.explained`, `.share_left`, `.r2` | −0.010767, +0.000241, 1.0229, 0.1175 | the same | agree |
| `… .coefficients` reversal, momentum, vol_timed_momentum: `t` | −0.136, +6.251, +7.470 | the same | agree |
| `skill_split.arms["matrix-select"].all.move.brier_skill`, `.direction.brier_skill` | 0.0234 [0.0196, 0.0273]; −0.0051 [−0.0089, −0.0013] | estimates the same; intervals read | agree |
| `… .log_loss_gain.move`, `.direction`, `.total` | +0.01156 [0.00963, 0.01369]; −0.00104 [−0.00254, +0.00036]; +0.010526 | estimates and sum the same | agree |
| `skill_split.arms["enc-ols"].all.move.brier_skill`, `.direction.brier_skill` | 0.0196 [0.0156, 0.0236]; −0.0008 [−0.0027, +0.0011] | estimates the same | agree |
| `skill_split.arms["enc-softmax"].all.move.brier_skill`, `.direction.brier_skill` | 0.0136 [0.0101, 0.0168]; +0.0007 [−0.0010, +0.0023] | estimates the same | agree |
| `skill_split.arms[arm].all.three_class.brier_skill` | 0.0130, 0.0110, 0.0079 | the reports' `bss` | agree |

### 5. The replay

- **`runs/2026-11-19-h1-adversary-replay/adversary.json` equals iteration 3's outside `provenance`.** I parsed both and walked them key by key: 0 differences in the 14 other top-level keys. As bytes, the two files have the same length (5,841,751) and differ on three lines, all inside `provenance`: the file count (88 against 66), the code digest and the commit. Neither holds a NaN token.
- **The data manifest digest is the same,** `0ee7ac0f86bd46331ad4f1400e39b8d2df580698f2ebcb849626f8119434ec31`, in the replay, in iteration 3's file, in both detector runs and in the case study's `config.json`.
- `adversary.md` differs from iteration 3's on its two provenance lines only.
- The log's line is right: 9,795 of 10,000 caught, twins caught 0, bit violations 0.

## The table of recomputed numbers

The full tables are `audit-2a-scripts/table-confirmatory.tsv` and `table-descriptive.tsv`: 1,473 rows each. Below are the rows that become a row or a sentence, generated from them by A8. Shares are in percent with their Wilson interval, differences in points with Newcombe's interval (method 10) and the 2×2 table (a both, b first only, c second only, d neither). "agree" was decided on the raw values. "mine only" rows are computed in this audit from `verdicts.jsonl`, are not registered, and decide nothing.

**Any-cut shares, three denominators (Wilson 95 %)**

| JSON path | confirmatory: the run | mine | descriptive: the run | mine |
|---|---|---|---|---|
| `metrics.detectors[FI].any_cut[all]` | 9857/10000, 98.57 % [98.32, 98.78] | agree | 9795/10000, 97.95 % [97.65, 98.21] | agree |
| `metrics.detectors[FI].any_cut[not-constant]` | 9175/9182, 99.92 % [99.84, 99.96] | agree | 8816/8828, 99.86 % [99.76, 99.92] | agree |
| `metrics.detectors[FI].any_cut[designed-no]` | 8498/8641, 98.35 % [98.05, 98.59] | agree | 8490/8695, 97.64 % [97.30, 97.94] | agree |
| `metrics.detectors[FI x3].any_cut[all]` | 9358/10000, 93.58 % [93.08, 94.04] | agree | 9182/10000, 91.82 % [91.27, 92.34] | agree |
| `metrics.detectors[FI x3].any_cut[not-constant]` | 9084/9182, 98.93 % [98.70, 99.12] | agree | 8718/8828, 98.75 % [98.50, 98.97] | agree |
| `metrics.detectors[FI x3].any_cut[designed-no]` | 8004/8641, 92.63 % [92.06, 93.16] | agree | 7889/8695, 90.73 % [90.10, 91.32] | agree |
| `metrics.detectors[FI /3].any_cut[all]` | 9628/10000, 96.28 % [95.89, 96.63] | agree | 9434/10000, 94.34 % [93.87, 94.78] | agree |
| `metrics.detectors[FI /3].any_cut[not-constant]` | 9129/9182, 99.42 % [99.25, 99.56] | agree | 8725/8828, 98.83 % [98.59, 99.04] | agree |
| `metrics.detectors[FI /3].any_cut[designed-no]` | 8271/8641, 95.72 % [95.27, 96.13] | agree | 8142/8695, 93.64 % [93.11, 94.13] | agree |
| `metrics.detectors[TRUNC-0/G].any_cut[all]` | 9482/10000, 94.82 % [94.37, 95.24] | agree | 9242/10000, 92.42 % [91.88, 92.92] | agree |
| `metrics.detectors[TRUNC-0/G].any_cut[not-constant]` | 9076/9182, 98.85 % [98.61, 99.04] | agree | 8693/8828, 98.47 % [98.19, 98.71] | agree |
| `metrics.detectors[TRUNC-0/G].any_cut[designed-no]` | 8128/8641, 94.06 % [93.55, 94.54] | agree | 7952/8695, 91.45 % [90.85, 92.02] | agree |
| `metrics.detectors[TRUNC-0/M].any_cut[all]` | 9522/10000, 95.22 % [94.78, 95.62] | agree | 9366/10000, 93.66 % [93.17, 94.12] | agree |
| `metrics.detectors[TRUNC-0/M].any_cut[not-constant]` | 9107/9182, 99.18 % [98.98, 99.35] | agree | 8735/8828, 98.95 % [98.71, 99.14] | agree |
| `metrics.detectors[TRUNC-0/M].any_cut[designed-no]` | 8165/8641, 94.49 % [93.99, 94.95] | agree | 8071/8695, 92.82 % [92.26, 93.35] | agree |
| `metrics.detectors[TRUNC-0/P].any_cut[all]` | 10000/10000, 100.00 % [99.96, 100.00] | agree | 10000/10000, 100.00 % [99.96, 100.00] | agree |
| `metrics.detectors[TRUNC-0/P].any_cut[not-constant]` | 9182/9182, 100.00 % [99.96, 100.00] | agree | 8828/8828, 100.00 % [99.96, 100.00] | agree |
| `metrics.detectors[TRUNC-0/P].any_cut[designed-no]` | 8641/8641, 100.00 % [99.96, 100.00] | agree | 8695/8695, 100.00 % [99.96, 100.00] | agree |
| `metrics.detectors[TRUNC-1/G].any_cut[all]` | 9404/10000, 94.04 % [93.56, 94.49] | agree | 9224/10000, 92.24 % [91.70, 92.75] | agree |
| `metrics.detectors[TRUNC-1/G].any_cut[not-constant]` | 8981/9182, 97.81 % [97.49, 98.09] | agree | 8642/8828, 97.89 % [97.57, 98.17] | agree |
| `metrics.detectors[TRUNC-1/G].any_cut[designed-no]` | 8046/8641, 93.11 % [92.56, 93.63] | agree | 7927/8695, 91.17 % [90.55, 91.75] | agree |
| `metrics.detectors[TWO-RUN s0.1 r1].any_cut[all]` | 8084/10000, 80.84 % [80.06, 81.60] | agree | 7665/10000, 76.65 % [75.81, 77.47] | agree |
| `metrics.detectors[TWO-RUN s0.1 r1].any_cut[not-constant]` | 7996/9182, 87.08 % [86.38, 87.75] | agree | 7467/8828, 84.58 % [83.81, 85.32] | agree |
| `metrics.detectors[TWO-RUN s0.1 r1].any_cut[designed-no]` | 6868/8641, 79.48 % [78.62, 80.32] | agree | 6524/8695, 75.03 % [74.11, 75.93] | agree |
| `metrics.detectors[TWO-RUN s0.1 r2].any_cut[all]` | 8560/10000, 85.60 % [84.90, 86.27] | agree | 8185/10000, 81.85 % [81.08, 82.59] | agree |
| `metrics.detectors[TWO-RUN s0.1 r2].any_cut[not-constant]` | 8438/9182, 91.90 % [91.32, 92.44] | agree | 7962/8828, 90.19 % [89.55, 90.79] | agree |
| `metrics.detectors[TWO-RUN s0.1 r2].any_cut[designed-no]` | 7288/8641, 84.34 % [83.56, 85.09] | agree | 6993/8695, 80.43 % [79.58, 81.25] | agree |
| `metrics.detectors[TWO-RUN s0.1 r8].any_cut[all]` | 9150/10000, 91.50 % [90.94, 92.03] | agree | 8820/10000, 88.20 % [87.55, 88.82] | agree |
| `metrics.detectors[TWO-RUN s0.1 r8].any_cut[not-constant]` | 8933/9182, 97.29 % [96.94, 97.60] | agree | 8501/8828, 96.30 % [95.88, 96.67] | agree |
| `metrics.detectors[TWO-RUN s0.1 r8].any_cut[designed-no]` | 7827/8641, 90.58 % [89.95, 91.18] | agree | 7569/8695, 87.05 % [86.33, 87.74] | agree |
| `metrics.detectors[TWO-RUN s1 r2].any_cut[all]` | 9740/10000, 97.40 % [97.07, 97.69] | agree | 9638/10000, 96.38 % [96.00, 96.73] | agree |
| `metrics.detectors[TWO-RUN s1 r2].any_cut[not-constant]` | 9146/9182, 99.61 % [99.46, 99.72] | agree | 8739/8828, 98.99 % [98.76, 99.18] | agree |
| `metrics.detectors[TWO-RUN s1 r2].any_cut[designed-no]` | 8381/8641, 96.99 % [96.61, 97.33] | agree | 8341/8695, 95.93 % [95.49, 96.32] | agree |
| `metrics.detectors[SHUFFLE k1].any_cut[all]` | 9629/10000, 96.29 % [95.90, 96.64] | agree | 9297/10000, 92.97 % [92.45, 93.45] | agree |
| `metrics.detectors[SHUFFLE k1].any_cut[not-constant]` | 9130/9182, 99.43 % [99.26, 99.57] | agree | 8741/8828, 99.01 % [98.79, 99.20] | agree |
| `metrics.detectors[SHUFFLE k1].any_cut[designed-no]` | 8272/8641, 95.73 % [95.28, 96.14] | agree | 8007/8695, 92.09 % [91.50, 92.64] | agree |
| `metrics.detectors[SHUFFLE k2].any_cut[all]` | 9743/10000, 97.43 % [97.10, 97.72] | agree | 9454/10000, 94.54 % [94.08, 94.97] | agree |
| `metrics.detectors[SHUFFLE k2].any_cut[not-constant]` | 9164/9182, 99.80 % [99.69, 99.88] | agree | 8792/8828, 99.59 % [99.44, 99.71] | agree |
| `metrics.detectors[SHUFFLE k2].any_cut[designed-no]` | 8384/8641, 97.03 % [96.65, 97.36] | agree | 8157/8695, 93.81 % [93.29, 94.30] | agree |
| `metrics.detectors[SHUFFLE k8].any_cut[all]` | 9847/10000, 98.47 % [98.21, 98.69] | agree | 9688/10000, 96.88 % [96.52, 97.20] | agree |
| `metrics.detectors[SHUFFLE k8].any_cut[not-constant]` | 9179/9182, 99.97 % [99.90, 99.99] | agree | 8823/8828, 99.94 % [99.87, 99.98] | agree |
| `metrics.detectors[SHUFFLE k8].any_cut[designed-no]` | 8488/8641, 98.23 % [97.93, 98.49] | agree | 8388/8695, 96.47 % [96.06, 96.84] | agree |
| `metrics.detectors[RETILE/G@ends].any_cut[all]` | 9509/10000, 95.09 % [94.65, 95.50] | agree | 9320/10000, 93.20 % [92.69, 93.68] | agree |
| `metrics.detectors[RETILE/G@ends].any_cut[not-constant]` | 9032/9182, 98.37 % [98.09, 98.61] | agree | 8676/8828, 98.28 % [97.99, 98.53] | agree |
| `metrics.detectors[RETILE/G@ends].any_cut[designed-no]` | 8151/8641, 94.33 % [93.82, 94.80] | agree | 8029/8695, 92.34 % [91.76, 92.88] | agree |
| `metrics.detectors[RETILE/M@ends].any_cut[all]` | 9617/10000, 96.17 % [95.78, 96.53] | agree | 9443/10000, 94.43 % [93.96, 94.86] | agree |
| `metrics.detectors[RETILE/M@ends].any_cut[not-constant]` | 9133/9182, 99.47 % [99.30, 99.60] | agree | 8752/8828, 99.14 % [98.92, 99.31] | agree |
| `metrics.detectors[RETILE/M@ends].any_cut[designed-no]` | 8259/8641, 95.58 % [95.13, 95.99] | agree | 8147/8695, 93.70 % [93.17, 94.19] | agree |

**Sensitivity: ignores outputs that turn missing**

| JSON path | confirmatory: the run | mine | descriptive: the run | mine |
|---|---|---|---|---|
| `metrics.ignores_outputs_that_turn_missing[FI][all]` | 9857/10000, 98.57 % [98.32, 98.78] | agree | 9795/10000, 97.95 % [97.65, 98.21] | agree |
| `metrics.ignores_outputs_that_turn_missing[FI][not-constant]` | 9175/9182, 99.92 % [99.84, 99.96] | agree | 8816/8828, 99.86 % [99.76, 99.92] | agree |
| `metrics.ignores_outputs_that_turn_missing[FI][designed-no]` | 8498/8641, 98.35 % [98.05, 98.59] | agree | 8490/8695, 97.64 % [97.30, 97.94] | agree |
| `metrics.ignores_outputs_that_turn_missing[TRUNC-0/G][all]` | 8414/10000, 84.14 % [83.41, 84.84] | agree | 8254/10000, 82.54 % [81.78, 83.27] | agree |
| `metrics.ignores_outputs_that_turn_missing[TRUNC-0/G][not-constant]` | 8008/9182, 87.21 % [86.52, 87.88] | agree | 7705/8828, 87.28 % [86.57, 87.96] | agree |
| `metrics.ignores_outputs_that_turn_missing[TRUNC-0/G][designed-no]` | 7456/8641, 86.29 % [85.54, 87.00] | agree | 7358/8695, 84.62 % [83.85, 85.37] | agree |
| `metrics.ignores_outputs_that_turn_missing[TRUNC-0/M][all]` | 8455/10000, 84.55 % [83.83, 85.25] | agree | 8378/10000, 83.78 % [83.04, 84.49] | agree |
| `metrics.ignores_outputs_that_turn_missing[TRUNC-0/M][not-constant]` | 8040/9182, 87.56 % [86.87, 88.22] | agree | 7747/8828, 87.75 % [87.05, 88.42] | agree |
| `metrics.ignores_outputs_that_turn_missing[TRUNC-0/M][designed-no]` | 7494/8641, 86.73 % [85.99, 87.43] | agree | 7477/8695, 85.99 % [85.25, 86.71] | agree |
| `metrics.ignores_outputs_that_turn_missing[TRUNC-0/P][all]` | 0/10000, 0.00 % [0.00, 0.04] | agree | 0/10000, 0.00 % [0.00, 0.04] | agree |
| `metrics.ignores_outputs_that_turn_missing[TRUNC-0/P][not-constant]` | 0/9182, 0.00 % [0.00, 0.04] | agree | 0/8828, 0.00 % [0.00, 0.04] | agree |
| `metrics.ignores_outputs_that_turn_missing[TRUNC-0/P][designed-no]` | 0/8641, 0.00 % [0.00, 0.04] | agree | 0/8695, 0.00 % [0.00, 0.04] | agree |
| `metrics.ignores_outputs_that_turn_missing[TRUNC-1/G][all]` | 8335/10000, 83.35 % [82.61, 84.07] | agree | 8235/10000, 82.35 % [81.59, 83.08] | agree |
| `metrics.ignores_outputs_that_turn_missing[TRUNC-1/G][not-constant]` | 7912/9182, 86.17 % [85.45, 86.86] | agree | 7653/8828, 86.69 % [85.97, 87.38] | agree |
| `metrics.ignores_outputs_that_turn_missing[TRUNC-1/G][designed-no]` | 7373/8641, 85.33 % [84.56, 86.06] | agree | 7332/8695, 84.32 % [83.54, 85.07] | agree |
| `metrics.ignores_outputs_that_turn_missing[TWO-RUN s0.1 r2][all]` | 8560/10000, 85.60 % [84.90, 86.27] | agree | 8185/10000, 81.85 % [81.08, 82.59] | agree |
| `metrics.ignores_outputs_that_turn_missing[TWO-RUN s0.1 r2][not-constant]` | 8438/9182, 91.90 % [91.32, 92.44] | agree | 7962/8828, 90.19 % [89.55, 90.79] | agree |
| `metrics.ignores_outputs_that_turn_missing[TWO-RUN s0.1 r2][designed-no]` | 7288/8641, 84.34 % [83.56, 85.09] | agree | 6993/8695, 80.43 % [79.58, 81.25] | agree |
| `metrics.ignores_outputs_that_turn_missing[SHUFFLE k8][all]` | 9847/10000, 98.47 % [98.21, 98.69] | agree | 9688/10000, 96.88 % [96.52, 97.20] | agree |
| `metrics.ignores_outputs_that_turn_missing[SHUFFLE k8][not-constant]` | 9179/9182, 99.97 % [99.90, 99.99] | agree | 8823/8828, 99.94 % [99.87, 99.98] | agree |
| `metrics.ignores_outputs_that_turn_missing[SHUFFLE k8][designed-no]` | 8488/8641, 98.23 % [97.93, 98.49] | agree | 8388/8695, 96.47 % [96.06, 96.84] | agree |
| `metrics.ignores_outputs_that_turn_missing[RETILE/G@ends][all]` | 8442/10000, 84.42 % [83.70, 85.12] | agree | 8331/10000, 83.31 % [82.57, 84.03] | agree |
| `metrics.ignores_outputs_that_turn_missing[RETILE/G@ends][not-constant]` | 7965/9182, 86.75 % [86.04, 87.42] | agree | 7687/8828, 87.08 % [86.36, 87.76] | agree |
| `metrics.ignores_outputs_that_turn_missing[RETILE/G@ends][designed-no]` | 7480/8641, 86.56 % [85.83, 87.27] | agree | 7434/8695, 85.50 % [84.74, 86.22] | agree |

**Conventions: the registered sentence**

| JSON path | confirmatory: the run | mine | descriptive: the run | mine |
|---|---|---|---|---|
| `metrics.conventions.sentence[all]` | X 94.82 %, Y 100.00 %, G to M 94.82 % to 95.22 % | agree | X 92.42 %, Y 100.00 %, G to M 92.42 % to 93.66 % | agree |
| `metrics.conventions.sentence[not-constant]` | X 98.85 %, Y 100.00 %, G to M 98.85 % to 99.18 % | agree | X 98.47 %, Y 100.00 %, G to M 98.47 % to 98.95 % | agree |
| `metrics.conventions.sentence[designed-no]` | X 94.06 %, Y 100.00 %, G to M 94.06 % to 94.49 % | agree | X 91.45 %, Y 100.00 %, G to M 91.45 % to 92.82 % | agree |

**H15: the deciding cell, the labels, the qualifier, and what stands beside**

| JSON path | confirmatory: the run | mine | descriptive: the run | mine |
|---|---|---|---|---|
| `metrics.h15.deciding_cell (table, difference, ci95, psi, n)` | -3.75 [-4.20, -3.32] points; a 9412, b 70, c 445, d 73 | agree | -5.53 [-6.06, -5.02] points; a 9151, b 91, c 644, d 114 | agree |
| `metrics.h15.deciding_cell.mcnemar_exact_p` | 9.072e-68 | agree | 1.93e-103 | agree |
| `metrics.h15.difference_points` | -3.75 | agree | -5.53 | agree |
| `metrics.h15.ci95_points` | [-4.20, -3.32] | agree | [-6.06, -5.02] | agree |
| `metrics.h15.sign` | below FI | agree | below FI | agree |
| `metrics.h15.margin` | by more than 1 point | agree | by more than 1 point | agree |
| `metrics.h15.prior` | fails | agree | fails | agree |
| `metrics.h15.qualifier.cells[convention M]` | -3.35 [-3.78, -2.93] points; a 9450, b 72, c 407, d 71 | agree | -4.29 [-4.80, -3.80] points; a 9251, b 115, c 544, d 90 | agree |
| `metrics.h15.qualifier.cells[not-constant denominator]` | -1.08 [-1.32, -0.87] points; a 9072, b 4, c 103, d 3 | agree | -1.39 [-1.67, -1.15] points; a 8687, b 6, c 129, d 6 | agree |
| `metrics.h15.qualifier.triggered_by` | [] | agree | [] | agree |
| `metrics.h15.qualifier.convention_dependent` | false | agree | false | agree |
| `metrics.h15.words` | null | agree | null | agree |
| `metrics.h15.beside[convention P]` | +1.43 [+1.21, +1.68] points; a 9857, b 143, c 0, d 0 | agree | +2.05 [+1.79, +2.35] points; a 9795, b 205, c 0, d 0 | agree |
| `metrics.h15.beside.mean_per_cut_rate_difference` | -23.11 [-23.75, -22.47] points | agree | -22.81 [-23.49, -22.12] points | agree |
| `the labels of H15 read on the qualifier cell [convention M] (never deciding)` | not in the run | below FI; by more than 1 point | not in the run | below FI; by more than 1 point |
| `the labels of H15 read on the qualifier cell [not-constant denominator] (never deciding)` | not in the run | below FI; 1-point margin not resolved | not in the run | below FI; by more than 1 point |
| `deciding cell, Wald interval for paired proportions, points` | not in the run | [-4.19, -3.31] | not in the run | [-6.05, -5.01] |
| `deciding cell, percentile bootstrap over leaks (4000 resamples, my seed), points` | not in the run | [-4.18, -3.31] | not in the run | [-6.05, -5.00] |
| `deciding cell split by constancy: TRUNC-0 caught, FI caught, leaks, among the leaks constant at the compared rows of the 16 cuts` | not in the run | [406, 682, 818] | not in the run | [549, 979, 1172] |
| `distance of the upper limit of the deciding interval from -1 point` | not in the run | -2.319 | not in the run | -4.017 |

**Pairs (section 4.7) and equal run counts (section 4.8)**

| JSON path | confirmatory: the run | mine | descriptive: the run | mine |
|---|---|---|---|---|
| `metrics.pairs[FI - TRUNC-0].table` | {"a": 9412, "b": 445, "c": 70, "d": 73} | agree | {"a": 9151, "b": 644, "c": 91, "d": 114} | agree |
| `metrics.pairs[FI - TRUNC-0].newcombe` | +3.75 [+3.32, +4.20] points | agree | +5.53 [+5.02, +6.06] points | agree |
| `metrics.pairs[FI - TRUNC-0].mcnemar_exact_p` | 9.072e-68 | agree | 1.93e-103 | agree |
| `metrics.pairs[FI - TRUNC-0].per_cut_rate_difference` | +23.11 [+22.47, +23.75] points | agree | +22.81 [+22.12, +23.49] points | agree |
| `metrics.pairs[FI - TWO-RUN].table` | {"a": 8553, "b": 1304, "c": 7, "d": 136} | agree | {"a": 8178, "b": 1617, "c": 7, "d": 198} | agree |
| `metrics.pairs[FI - TWO-RUN].newcombe` | +12.97 [+12.32, +13.64] points | agree | +16.10 [+15.39, +16.83] points | agree |
| `metrics.pairs[FI - TWO-RUN].mcnemar_exact_p` | 0 | agree | 0 | agree |
| `metrics.pairs[FI - TWO-RUN].per_cut_rate_difference` | +42.55 [+41.85, +43.25] points | agree | +44.31 [+43.61, +45.02] points | agree |
| `metrics.pairs[FI - SHUFFLE].table` | {"a": 9802, "b": 55, "c": 45, "d": 98} | agree | {"a": 9626, "b": 169, "c": 62, "d": 143} | agree |
| `metrics.pairs[FI - SHUFFLE].newcombe` | +0.10 [-0.10, +0.30] points | agree | +1.07 [+0.78, +1.38] points | agree |
| `metrics.pairs[FI - SHUFFLE].mcnemar_exact_p` | 0.3682 | agree | 1.209e-12 | agree |
| `metrics.pairs[FI - SHUFFLE].per_cut_rate_difference` | +3.00 [+2.63, +3.36] points | agree | +5.89 [+5.44, +6.34] points | agree |
| `metrics.pairs[TRUNC-0 - TWO-RUN].table` | {"a": 8446, "b": 1036, "c": 114, "d": 404} | agree | {"a": 7980, "b": 1262, "c": 205, "d": 553} | agree |
| `metrics.pairs[TRUNC-0 - TWO-RUN].newcombe` | +9.22 [+8.59, +9.87] points | agree | +10.57 [+9.85, +11.30] points | agree |
| `metrics.pairs[TRUNC-0 - TWO-RUN].mcnemar_exact_p` | 1.461e-186 | agree | 8.931e-186 | agree |
| `metrics.pairs[TRUNC-0 - TWO-RUN].per_cut_rate_difference` | +19.44 [+18.70, +20.18] points | agree | +21.51 [+20.74, +22.27] points | agree |
| `metrics.pairs[TRUNC-0 - SHUFFLE].table` | {"a": 9399, "b": 83, "c": 448, "d": 70} | agree | {"a": 9096, "b": 146, "c": 592, "d": 166} | agree |
| `metrics.pairs[TRUNC-0 - SHUFFLE].newcombe` | -3.65 [-4.11, -3.21] points | agree | -4.46 [-4.99, -3.94] points | agree |
| `metrics.pairs[TRUNC-0 - SHUFFLE].mcnemar_exact_p` | 1.547e-61 | agree | 1.759e-64 | agree |
| `metrics.pairs[TRUNC-0 - SHUFFLE].per_cut_rate_difference` | -20.11 [-20.74, -19.48] points | agree | -16.91 [-17.61, -16.22] points | agree |
| `metrics.pairs[TWO-RUN - SHUFFLE].table` | {"a": 8556, "b": 4, "c": 1291, "d": 149} | agree | {"a": 8169, "b": 16, "c": 1519, "d": 296} | agree |
| `metrics.pairs[TWO-RUN - SHUFFLE].newcombe` | -12.87 [-13.54, -12.22] points | agree | -15.03 [-15.75, -14.33] points | agree |
| `metrics.pairs[TWO-RUN - SHUFFLE].mcnemar_exact_p` | 0 | agree | 0 | agree |
| `metrics.pairs[TWO-RUN - SHUFFLE].per_cut_rate_difference` | -39.55 [-40.20, -38.90] points | agree | -38.42 [-39.09, -37.75] points | agree |
| `metrics.pairs[TRUNC-1/G - TRUNC-0 (one-bar date shift)].table` | {"a": 9358, "b": 46, "c": 124, "d": 472} | agree | {"a": 9149, "b": 75, "c": 93, "d": 683} | agree |
| `metrics.pairs[TRUNC-1/G - TRUNC-0 (one-bar date shift)].newcombe` | -0.78 [-1.04, -0.53] points | agree | -0.18 [-0.44, +0.08] points | agree |
| `metrics.pairs[TRUNC-1/G - TRUNC-0 (one-bar date shift)].mcnemar_exact_p` | 1.834e-09 | agree | 0.1895 | agree |
| `metrics.pairs[TRUNC-1/G - TRUNC-0 (one-bar date shift)].per_cut_rate_difference` | +1.26 [+1.06, +1.45] points | agree | +1.08 [+0.89, +1.28] points | agree |
| `metrics.equal_run_counts[FI x3 - TRUNC-0].table` | {"a": 9187, "b": 171, "c": 295, "d": 347} | agree | {"a": 8885, "b": 297, "c": 357, "d": 461} | agree |
| `metrics.equal_run_counts[FI x3 - TRUNC-0].newcombe` | -1.24 [-1.67, -0.82] points | agree | -0.60 [-1.10, -0.10] points | agree |
| `metrics.equal_run_counts[FI x3 - TRUNC-0].mcnemar_exact_p` | 9.998e-09 | agree | 0.02098 | agree |
| `metrics.equal_run_counts[FI x3 - TRUNC-0].per_cut_rate_difference` | -9.55 [-10.17, -8.93] points | agree | -9.19 [-9.85, -8.52] points | agree |
| `metrics.equal_run_counts[TWO-RUN s0.1 r1 - TRUNC-0].table` | {"a": 7996, "b": 88, "c": 1486, "d": 430} | agree | {"a": 7508, "b": 157, "c": 1734, "d": 601} | agree |
| `metrics.equal_run_counts[TWO-RUN s0.1 r1 - TRUNC-0].newcombe` | -13.98 [-14.71, -13.26] points | agree | -15.77 [-16.57, -14.98] points | agree |
| `metrics.equal_run_counts[TWO-RUN s0.1 r1 - TRUNC-0].mcnemar_exact_p` | 0 | agree | 0 | agree |
| `metrics.equal_run_counts[TWO-RUN s0.1 r1 - TRUNC-0].per_cut_rate_difference` | -27.22 [-27.93, -26.51] points | agree | -29.27 [-29.99, -28.56] points | agree |
| `metrics.equal_run_counts[SHUFFLE k1 - TRUNC-0].table` | {"a": 9333, "b": 296, "c": 149, "d": 222} | agree | {"a": 8937, "b": 360, "c": 305, "d": 398} | agree |
| `metrics.equal_run_counts[SHUFFLE k1 - TRUNC-0].newcombe` | +1.47 [+1.06, +1.89] points | agree | +0.55 [+0.04, +1.06] points | agree |
| `metrics.equal_run_counts[SHUFFLE k1 - TRUNC-0].mcnemar_exact_p` | 2.862e-12 | agree | 0.03618 | agree |
| `metrics.equal_run_counts[SHUFFLE k1 - TRUNC-0].per_cut_rate_difference` | -2.92 [-3.51, -2.33] points | agree | -5.14 [-5.79, -4.50] points | agree |
| `metrics.equal_run_counts[FI - TWO-RUN s0.1 r2].table` | {"a": 8553, "b": 1304, "c": 7, "d": 136} | agree | {"a": 8178, "b": 1617, "c": 7, "d": 198} | agree |
| `metrics.equal_run_counts[FI - TWO-RUN s0.1 r2].newcombe` | +12.97 [+12.32, +13.64] points | agree | +16.10 [+15.39, +16.83] points | agree |
| `metrics.equal_run_counts[FI - TWO-RUN s0.1 r2].mcnemar_exact_p` | 0 | agree | 0 | agree |
| `metrics.equal_run_counts[FI - TWO-RUN s0.1 r2].per_cut_rate_difference` | +42.55 [+41.85, +43.25] points | agree | +44.31 [+43.61, +45.02] points | agree |
| `metrics.equal_run_counts[FI - SHUFFLE k2].table` | {"a": 9707, "b": 150, "c": 36, "d": 107} | agree | {"a": 9410, "b": 385, "c": 44, "d": 161} | agree |
| `metrics.equal_run_counts[FI - SHUFFLE k2].newcombe` | +1.14 [+0.88, +1.42] points | agree | +3.41 [+3.02, +3.82] points | agree |
| `metrics.equal_run_counts[FI - SHUFFLE k2].mcnemar_exact_p` | 9.629e-18 | agree | 4.2e-69 | agree |
| `metrics.equal_run_counts[FI - SHUFFLE k2].per_cut_rate_difference` | +16.37 [+15.94, +16.81] points | agree | +19.01 [+18.52, +19.51] points | agree |

**The union and its misses**

| JSON path | confirmatory: the run | mine | descriptive: the run | mine |
|---|---|---|---|---|
| `metrics.union[primary]` | 9954/10000, 99.54 % [99.39, 99.65] | agree | 9922/10000, 99.22 % [99.03, 99.37] | agree |
| `metrics.union[with TRUNC-1]` | 9954/10000, 99.54 % [99.39, 99.65] | agree | 9924/10000, 99.24 % [99.05, 99.39] | agree |
| `metrics.union[with RETILE]` | 9955/10000, 99.55 % [99.40, 99.66] | agree | 9927/10000, 99.27 % [99.08, 99.42] | agree |
| `metrics.union[with sigma 1]` | 9962/10000, 99.62 % [99.48, 99.72] | agree | 9953/10000, 99.53 % [99.38, 99.65] | agree |
| `metrics.union[over both schedules]` | 9967/10000, 99.67 % [99.54, 99.76] | agree | 9948/10000, 99.48 % [99.32, 99.60] | agree |
| `metrics.union[under convention M]` | 9951/10000, 99.51 % [99.35, 99.63] | agree | 9940/10000, 99.40 % [99.23, 99.53] | agree |
| `metrics.union_misses.count` | 46 | agree | 78 | agree |
| `metrics.union_misses.constant_h1_cuts` | 46 | agree | 76 | agree |
| `metrics.union_misses.constant_both_schedules` | 42 | agree | 68 | agree |
| `metrics.union_misses.caught_by_a_secondary_arm[TRUNC-1]` | 0 | agree | 2 | agree |
| `metrics.union_misses.caught_by_a_secondary_arm[RETILE]` | 1 | agree | 5 | agree |
| `metrics.union_misses.caught_by_a_secondary_arm[sigma 1]` | 8 | agree | 31 | agree |
| `metrics.union_misses.caught_by_a_secondary_arm[long schedule]` | 13 | agree | 26 | agree |
| `metrics.union_misses.caught_by_a_secondary_arm[convention M]` | 46 | agree | 78 | agree |
| `metrics.union_misses.by_family` | {"aggregates": 27, "combinations": 11, "continuous": 0, "levels": 0, "ratios": 8, "shapes": 0} | agree | {"aggregates": 36, "combinations": 11, "continuous": 0, "levels": 0, "ratios": 27, "shapes": 4} | agree |
| `union misses caught by no secondary arm` | not in the run | 0 | not in the run | 0 |
| `union misses caught by no secondary arm other than convention M` | not in the run | 28 | not in the run | 35 |
| `union misses that are not constant at the compared rows of the 16 cuts` | not in the run | 0 | not in the run | 2 |
| `metrics.missed_by_detector_among_union[FI]` | 97/9954, 0.97 % [0.80, 1.19] | agree | 127/9922, 1.28 % [1.08, 1.52] | agree |
| `metrics.missed_by_detector_among_union[TRUNC-0]` | 472/9954, 4.74 % [4.34, 5.18] | agree | 680/9922, 6.85 % [6.37, 7.37] | agree |
| `metrics.missed_by_detector_among_union[TWO-RUN]` | 1394/9954, 14.00 % [13.34, 14.70] | agree | 1737/9922, 17.51 % [16.77, 18.27] | agree |
| `metrics.missed_by_detector_among_union[SHUFFLE]` | 107/9954, 1.07 % [0.89, 1.30] | agree | 234/9922, 2.36 % [2.08, 2.68] | agree |

**The cut-date bootstrap**

| JSON path | confirmatory: the run | mine | descriptive: the run | mine |
|---|---|---|---|---|
| `metrics.cut_date_bootstrap.dates` | 64 | agree | 64 | agree |
| `metrics.cut_date_bootstrap.percentiles_points` | [-6.38, -2.95] | agree | [-7.90, -4.73] | agree |
| `metrics.cut_date_bootstrap.spread_points` | 3.43 | agree | 3.17 | agree |
| `metrics.cut_date_bootstrap.wider_than_margin` | true | agree | true | agree |
| `metrics.cut_date_bootstrap.subsets / dates_per_subset` | [2000, 8] | agree | [2000, 8] | agree |
| `cut-date bootstrap: min, median, max of the 2000 differences, points` | not in the run | [-7.64, -4.33, -2.51] | not in the run | [-9.59, -5.96, -4.42] |
| `cut-date bootstrap: share of the 2000 subsets with a difference below 0, below -1 point` | not in the run | [+1.00, +1.00] | not in the run | [+1.00, +1.00] |
| `cut-date bootstrap with another seed (97531, 20000 subsets): percentiles, spread, points` | not in the run | [-6.35, -2.93, +3.42] | not in the run | [-7.85, -4.72, +3.13] |
| `long schedule, all 64 dates: TRUNC-0 minus FI, any cut, points` | not in the run | -2 | not in the run | -3.62 |

**The placement-invariant subset, the counts, the replications**

| JSON path | confirmatory: the run | mine | descriptive: the run | mine |
|---|---|---|---|---|
| `metrics.placement_invariant_subset[invariant].leaks` | 8288 | agree | 8399 | agree |
| `metrics.placement_invariant_subset[invariant].FI_any_cut` | 8151/8288, 98.35 % [98.05, 98.60] | agree | 8249/8399, 98.21 % [97.91, 98.48] | agree |
| `metrics.placement_invariant_subset[invariant].TRUNC-0_minus_FI` | -3.68 [-4.18, -3.20] points | agree | -4.39 [-4.92, -3.89] points | agree |
| `placement-invariant subset [invariant]: the 2x2 table of TRUNC-0 against FI` | not in the run | {"a": 7778, "b": 68, "c": 373, "d": 69} | not in the run | {"a": 7815, "b": 65, "c": 434, "d": 85} |
| `metrics.placement_invariant_subset[complement].leaks` | 1712 | agree | 1601 | agree |
| `metrics.placement_invariant_subset[complement].FI_any_cut` | 1706/1712, 99.65 % [99.24, 99.84] | agree | 1546/1601, 96.56 % [95.56, 97.35] | agree |
| `metrics.placement_invariant_subset[complement].TRUNC-0_minus_FI` | -4.09 [-5.16, -3.18] points | agree | -11.49 [-13.34, -9.73] points | agree |
| `placement-invariant subset [complement]: the 2x2 table of TRUNC-0 against FI` | not in the run | {"a": 1634, "b": 2, "c": 72, "d": 4} | not in the run | {"a": 1336, "b": 26, "c": 210, "d": 29} |
| `metrics.descriptive.constant_h1_cuts` | 818/10000, 8.18 % [7.66, 8.73] | agree | 1172/10000, 11.72 % [11.10, 12.37] | agree |
| `metrics.descriptive.constant_both_schedules` | 477/10000, 4.77 % [4.37, 5.21] | agree | 765/10000, 7.65 % [7.15, 8.19] | agree |
| `metrics.descriptive.distinct_expressions` | 8434 | read, not recomputed | 8533 | read, not recomputed |
| `metrics.replications[FI any cut]` | 9857/10000, 98.57 % [98.32, 98.78] | agree | 9795/10000, 97.95 % [97.65, 98.21] | agree |
| `metrics.replications[SHUFFLE any cut]` | 9847/10000, 98.47 % [98.21, 98.69] | agree | 9688/10000, 96.88 % [96.52, 97.20] | agree |
| `leaks by designed tag` | not in the run | {"cell": 71, "no": 8641, "yes": 1288} | not in the run | {"cell": 58, "no": 8695, "yes": 1247} |
| `leaks by family` | not in the run | {"aggregates": 1457, "combinations": 1493, "continuous": 1021, "levels": 1981, "ratios": 1984, "shapes": 2064} | not in the run | {"aggregates": 1569, "combinations": 1486, "continuous": 943, "levels": 2033, "ratios": 2002, "shapes": 1967} |
| `leaks by output` | not in the run | {"exp_return": 1196, "probs": 1925, "target": 6879} | not in the run | {"exp_return": 1110, "probs": 1903, "target": 6987} |
| `constant leaks caught by TRUNC-0/G, TRUNC-0/M, FI, SHUFFLE, TWO-RUN, then the number of constant leaks` | not in the run | [406, 415, 682, 668, 122, 818] | not in the run | [549, 631, 979, 865, 223, 1172] |

**Mirror asymmetry, any cut**

| JSON path | confirmatory: the run | mine | descriptive: the run | mine |
|---|---|---|---|---|
| `metrics.mirror_asymmetry[FI].any_cut` | 0/6552, 0.00 % [0.00, 0.06] | agree | 0/6684, 0.00 % [0.00, 0.06] | agree |
| `metrics.mirror_asymmetry[TRUNC-0].any_cut` | 801/6552, 12.23 % [11.45, 13.04] | agree | 1141/6684, 17.07 % [16.19, 17.99] | agree |
| `metrics.mirror_asymmetry[TRUNC-1].any_cut` | 804/6552, 12.27 % [11.50, 13.09] | agree | 1097/6684, 16.41 % [15.54, 17.32] | agree |
| `metrics.mirror_asymmetry[RETILE].any_cut` | 667/6552, 10.18 % [9.47, 10.94] | agree | 1008/6684, 15.08 % [14.24, 15.96] | agree |
| `metrics.mirror_asymmetry[TWO-RUN].any_cut` | 0/6552, 0.00 % [0.00, 0.06] | agree | 0/6684, 0.00 % [0.00, 0.06] | agree |
| `metrics.mirror_asymmetry[SHUFFLE].any_cut` | 0/6552, 0.00 % [0.00, 0.06] | agree | 0/6684, 0.00 % [0.00, 0.06] | agree |

**The long schedule, any cut (the two other denominators are mine only)**

| JSON path | confirmatory: the run | mine | descriptive: the run | mine |
|---|---|---|---|---|
| `metrics.long_schedule[FI@long].any_cut` | 9916/10000, 99.16 % [98.96, 99.32] | agree | 9872/10000, 98.72 % [98.48, 98.92] | agree |
| `long_schedule[FI@long].any_cut[not-constant]` | not in the run | 9182/9182, 100.00 % [99.96, 100.00] | not in the run | 8826/8828, 99.98 % [99.92, 99.99] |
| `long_schedule[FI@long].any_cut[designed-no]` | not in the run | 8557/8641, 99.03 % [98.80, 99.21] | not in the run | 8567/8695, 98.53 % [98.25, 98.76] |
| `metrics.long_schedule[TRUNC-0/G@long].any_cut` | 9716/10000, 97.16 % [96.82, 97.47] | agree | 9510/10000, 95.10 % [94.66, 95.51] | agree |
| `long_schedule[TRUNC-0/G@long].any_cut[not-constant]` | not in the run | 9173/9182, 99.90 % [99.81, 99.95] | not in the run | 8810/8828, 99.80 % [99.68, 99.87] |
| `long_schedule[TRUNC-0/G@long].any_cut[designed-no]` | not in the run | 8357/8641, 96.71 % [96.32, 97.07] | not in the run | 8208/8695, 94.40 % [93.90, 94.86] |
| `metrics.long_schedule[TRUNC-0/M@long].any_cut` | 9676/10000, 96.76 % [96.39, 97.09] | agree | 9539/10000, 95.39 % [94.96, 95.78] | agree |
| `long_schedule[TRUNC-0/M@long].any_cut[not-constant]` | not in the run | 9166/9182, 99.83 % [99.72, 99.89] | not in the run | 8811/8828, 99.81 % [99.69, 99.88] |
| `long_schedule[TRUNC-0/M@long].any_cut[designed-no]` | not in the run | 8317/8641, 96.25 % [95.83, 96.63] | not in the run | 8238/8695, 94.74 % [94.25, 95.19] |
| `metrics.long_schedule[TRUNC-1/G@long].any_cut` | 9716/10000, 97.16 % [96.82, 97.47] | agree | 9507/10000, 95.07 % [94.63, 95.48] | agree |
| `long_schedule[TRUNC-1/G@long].any_cut[not-constant]` | not in the run | 9178/9182, 99.96 % [99.89, 99.98] | not in the run | 8817/8828, 99.88 % [99.78, 99.93] |
| `long_schedule[TRUNC-1/G@long].any_cut[designed-no]` | not in the run | 8357/8641, 96.71 % [96.32, 97.07] | not in the run | 8211/8695, 94.43 % [93.93, 94.90] |
| `metrics.long_schedule[TWO-RUN s0.1 r2@long].any_cut` | 9468/10000, 94.68 % [94.22, 95.10] | agree | 9164/10000, 91.64 % [91.08, 92.17] | agree |
| `long_schedule[TWO-RUN s0.1 r2@long].any_cut[not-constant]` | not in the run | 9156/9182, 99.72 % [99.59, 99.81] | not in the run | 8749/8828, 99.11 % [98.89, 99.28] |
| `long_schedule[TWO-RUN s0.1 r2@long].any_cut[designed-no]` | not in the run | 8110/8641, 93.85 % [93.33, 94.34] | not in the run | 7873/8695, 90.55 % [89.91, 91.14] |

**Classes, assertions, gates, twins (read from `detectors.json`)**

| JSON path | confirmatory: the run | mine | descriptive: the run | mine |
|---|---|---|---|---|
| `assertion 2.4 (RETILE equals windowed TRUNC-0): (leak, end) cells where RETILE/G differs from ENDS/G` | 0 | agree | 0 | agree |
| `assertion 2.4 (RETILE equals windowed TRUNC-0): (leak, end) cells where RETILE/M differs from ENDS/M` | 0 | agree | 0 | agree |
| `assertion 2.4 (RETILE equals windowed TRUNC-0): (leak, end) cells where RETILE/P differs from ENDS/P` | 0 | agree | 0 | agree |
| `finite within flags: raw cells set under the sensitivity rule and not under the catch rule of H1` | 0 | agree | 0 | agree |
| `reported.p_assertion: TRUNC-0/P cells not flagged (the exception cuts, since none is flagged inside and none missed outside)` | 69 | agree | 71 | agree |
| `reported.p_assertion: TRUNC-1/P cells not flagged (the exception cuts, since none is flagged inside and none missed outside)` | 190 | agree | 204 | agree |
| `reported.p_assertion: ENDS/P cells not flagged (the exception cuts, since none is flagged inside and none missed outside)` | 5 | agree | 4 | agree |
| `reported.classes[M1 ends under P][ENDS/P]: flagged == cuts - cannot_flag_last_row` | 28 | agree | 28 | agree |
| `reported.classes[M1 ends under P][RETILE/P]: flagged == cuts - cannot_flag_last_row` | 28 | agree | 28 | agree |
| `reported.classes[M1 h1 under P][TRUNC-0/P]: flagged == cuts - cannot_flag_last_row` | 16 | agree | 16 | agree |
| `reported.classes[M1 h1 under P][TRUNC-1/P]: flagged == cuts - cannot_flag_last_row` | 16 | agree | 16 | agree |
| `reported.classes[M1 long under P][TRUNC-0/P]: flagged == cuts - cannot_flag_last_row` | 128 | agree | 128 | agree |
| `reported.classes[M1 long under P][TRUNC-1/P]: flagged == cuts - cannot_flag_last_row` | 128 | agree | 128 | agree |
| `reported.classes[M2 FI h1]` | {"flagged_where_not_predicted": 0, "not_predicted": 0, "predicted_flagged": 16} | read, not recomputed | {"flagged_where_not_predicted": 0, "not_predicted": 0, "predicted_flagged": 16} | read, not recomputed |
| `reported.classes[M2 FI long]` | {"flagged_where_not_predicted": 0, "not_predicted": 0, "predicted_flagged": 128} | read, not recomputed | {"flagged_where_not_predicted": 0, "not_predicted": 0, "predicted_flagged": 128} | read, not recomputed |
| `reported.classes[M2 h1]` | {"SHUFFLE": 6, "TWO-RUN": 14} | read, not recomputed | {"SHUFFLE": 6, "TWO-RUN": 15} | read, not recomputed |
| `reported.classes[M2 long]` | {"TWO-RUN": 116} | read, not recomputed | {"TWO-RUN": 117} | read, not recomputed |
| `reported.classes[M2 mirror h1]` | {"SHUFFLE": 6, "TWO-RUN": 14} | read, not recomputed | {"SHUFFLE": 6, "TWO-RUN": 15} | read, not recomputed |
| `reported.classes[M2 mirror long]` | {"TWO-RUN": 116} | read, not recomputed | {"TWO-RUN": 117} | read, not recomputed |
| `assertions[row kernel equals the adversary's fast path (FI)]` | {"pass": true, "violations": 0} | read, not recomputed | {"pass": true, "violations": 0} | read, not recomputed |
| `assertions[§2 P: TRUNC-0 flags every cut but the exception]` | {"pass": true, "violations": 0} | read, not recomputed | {"pass": true, "violations": 0} | read, not recomputed |
| `assertions[§2 P: binary roots missing exactly where the OR mask is set]` | {"pass": true, "violations": 0} | read, not recomputed | {"pass": true, "violations": 0} | read, not recomputed |
| `assertions[§2.3 TRUNC-1's row t + 1 exists and is scored at every cut]` | {"pass": true, "violations": 0} | read, not recomputed | {"pass": true, "violations": 0} | read, not recomputed |
| `assertions[§2.4 RETILE equals windowed TRUNC-0 at the ends]` | {"pass": true, "violations": 0} | read, not recomputed | {"pass": true, "violations": 0} | read, not recomputed |
| `assertions[§2.5 TWO-RUN's repair checks]` | {"pass": true, "violations": 0} | read, not recomputed | {"pass": true, "violations": 0} | read, not recomputed |
| `assertions[§3.1 honest twins never flagged]` | {"pass": true, "violations": 0} | read, not recomputed | {"pass": true, "violations": 0} | read, not recomputed |
| `assertions[§3.2 cancelled controls follow the prediction (H1's cuts)]` | {"pass": true, "violations": 0} | read, not recomputed | {"pass": true, "violations": 0} | read, not recomputed |
| `assertions[§3.3 Fonseca's classes give their registered verdicts]` | {"pass": true, "violations": 0} | read, not recomputed | {"pass": true, "violations": 0} | read, not recomputed |
| `assertions[§4.15 the long schedule holds 64 dates, shared by both pairs]` | {"pass": true, "violations": 0} | read, not recomputed | {"pass": true, "violations": 0} | read, not recomputed |
| `assertions[§4.4 truncation catches go through a missing read]` | {"pass": true, "violations": 0} | read, not recomputed | {"pass": true, "violations": 0} | read, not recomputed |
| `assertions[§4.9 a single-Cmp leak and its mirror are flagged together]` | {"pass": true, "violations": 0} | read, not recomputed | {"pass": true, "violations": 0} | read, not recomputed |
| `gates` | {"fi": {"mismatches": 0, "pass": true, "twin_violations": 0, "units": 220}, "h1_path": {"cuts_per_pair": null, "mismatches": {"SHUFFLE": 0, "TRUNC-0": 0, "TWO-RUN": 0}, "pass": true, "units": 100}, "leaks": 50, "pass": true} | read, not recomputed | {"fi": {"mismatches": 0, "pass": true, "twin_violations": 0, "units": 220}, "h1_path": {"cuts_per_pair": null, "mismatches": {"SHUFFLE": 0, "TRUNC-0": 0, "TWO-RUN": 0}, "pass": true, "units": 100}, "leaks": 50, "pass": true} | read, not recomputed |
| `reported.honest_twins` | {"constant_at_h1_compared_rows": {"count": 1220, "n": 10000, "share": 0.122, "wilson95": [0.11573005680977742, 0.12856024595845406]}, "evaluated": 10000} | read, not recomputed | {"constant_at_h1_compared_rows": {"count": 1626, "n": 10000, "share": 0.1626, "wilson95": [0.15549751567049636, 0.16996160643003616]}, "evaluated": 10000} | read, not recomputed |
| `all_pass` | true | read, not recomputed | true | read, not recomputed |

**Every row that differs (confirmatory run; the descriptive run has none)**

| JSON path | the run: mean, ci95 | mine: ci95 |
|---|---|---|
| `metrics.detectors[ENDS/P@ends].mean_per_cut_rate[all]` | 0.9999821428571429, [0.9999611451099248, 1.0] | [0.9999611451099248, 1.000003140604361] |
| `metrics.detectors[ENDS/P@ends].mean_per_cut_rate[not-constant]` | 0.9999805520117, [0.999957683812098, 1.0] | [0.999957683812098, 1.000003420211302] |
| `metrics.detectors[ENDS/P@ends].mean_per_cut_rate[designed-no]` | 0.9999793344024337, [0.999955034606629, 1.0] | [0.999955034606629, 1.0000036341982383] |
| `metrics.detectors[RETILE/P@ends].mean_per_cut_rate[all]` | 0.9999821428571429, [0.9999611451099248, 1.0] | [0.9999611451099248, 1.000003140604361] |
| `metrics.detectors[RETILE/P@ends].mean_per_cut_rate[not-constant]` | 0.9999805520117, [0.999957683812098, 1.0] | [0.999957683812098, 1.000003420211302] |
| `metrics.detectors[RETILE/P@ends].mean_per_cut_rate[designed-no]` | 0.9999793344024337, [0.999955034606629, 1.0] | [0.999955034606629, 1.0000036341982383] |
| `metrics.detectors[TRUNC-0/P].mean_per_cut_rate[all]` | 0.99999375, [0.9999815002250967, 1.0] | [0.9999815002250967, 1.0000059997749033] |
| `metrics.detectors[TRUNC-0/P].mean_per_cut_rate[not-constant]` | 0.999993193204095, [0.999979852129271, 1.0] | [0.999979852129271, 1.0000065342789188] |
| `metrics.detectors[TRUNC-0/P].mean_per_cut_rate[designed-no]` | 0.9999927670408517, [0.9999785907014195, 1.0] | [0.9999785907014195, 1.0000069433802838] |

## Sentences

Every sentence below is about one seeded generator (10,000 leaks, seed 20261118, placement `quantile`), BTCUSDT and ETHUSDT daily bars, H1's 16 cuts (8 dates), H1's catch rule and convention G unless named. §6's "may not" list still applies to each.

### The paper may state these as they are

- **Any-cut shares:** FI 98.57 % [98.32, 98.78]; TRUNC-0 94.82 % [94.37, 95.24]; TWO-RUN (σ = 0.1, 2 runs) 85.60 % [84.90, 86.27]; SHUFFLE (8 twins) 98.47 % [98.21, 98.69]; TRUNC-1 94.04 % [93.56, 94.49]; RETILE at its 28 ends 95.09 % [94.65, 95.50], equal to truncation at those ends for every leak.
- **H15, with its cell named:** TRUNC-0 minus FI is −3.75 points, Newcombe 95 % [−4.20, −3.32] (b = 70, c = 445; exact McNemar p = 9.1e-68). Sign "below FI"; margin "by more than 1 point"; the prior "at least as many" fails. The qualifier is not triggered. No limit lies within 0.003 point of 0 or of −1 (the upper limit is 2.32 points below −1).
- **The registered sentence of §4.5:** "truncation's rate lies between 94.82 % and 100.00 % depending on how a missing bar is read" (G to M: 94.82 % to 95.22 %).
- **The sensitivity:** ignoring outputs that turn missing, TRUNC-0 falls to 84.14 % and to 0 % under P; FI, TWO-RUN and SHUFFLE do not change.
- **The union:** 99.54 % [99.39, 99.65]. Its 46 misses are all constant at H1's compared rows (42 on both schedules); the long schedule catches 13 of them, σ = 1.0 catches 8, RETILE 1, TRUNC-1 none.
- **Missed by one detector among the union's 9,954 catches:** FI 97, SHUFFLE 107, TRUNC-0 472, TWO-RUN 1,394.
- **FI against SHUFFLE:** +0.10 point [−0.10, +0.30], p = 0.37: not separated, with 2 runs per cut against 8 twins.
- **TRUNC-1 against TRUNC-0, the one-bar date shift:** −0.78 point [−1.04, −0.53]; 170 leaks change their any-cut verdict (b = 46, c = 124).
- **Mirror asymmetry:** 0 of 6,552 single-comparison leaks for FI, TWO-RUN and SHUFFLE; 801 (12.23 %) for TRUNC-0, 804 for TRUNC-1, 667 (10.18 %) for RETILE.
- **The controls:** no honest twin flagged, by any detector, of 10,000 (an assertion of the run; not recomputable from the per-leak file).
- **The replications, named as such:** FI 98.57 % here against 97.95 % on the `h1-bands` population; SHUFFLE 98.47 % against 96.88 %. And: the descriptive run gives iteration 3's FI verdicts and iteration 4's twin counts again, leak by leak.
- **TWO-RUN's law, as §2.5 asks:** at σ = 0.1 the median body of the perturbed bars goes from 0.0164 to 0.0983 and the median fill from 0.42 to 0.80; the VWAP clip binds on 57.7 % of them, the taker caps on none (`reported.two_run_repair`, read).

### The paper must word these differently

- **"Truncation catches fewer leaks than future invariance."** Say: with one run per cut against FI's two, on all leaks, under convention G. Beside it: TRUNC-0 is 1.24 points above FI's ×3 run alone and 1.46 points below its ÷3 run alone (the second computed in this audit); −1.08 [−1.32, −0.87] on the leaks that are not constant, where the 1-point margin is not resolved; +1.43 [+1.21, +1.68] under convention P; 276 of the net 375 leaks are constant at the compared rows (Minors 1 and 3).
- **"H15's verdict is date-dependent."** Keep the registered sentence, then: the 2.5th and 97.5th percentiles of the difference are −6.38 and −2.95 points across 2,000 subsets of 8 of the long schedule's 64 dates (smallest and largest: −7.64 and −2.51); its sign and its 1-point label are the same in every subset (Minor 2).
- **"TWO-RUN flags M2 at 14 of 16 cuts."** Not the registered arm: any of 16 runs, both σ (Minor 4).
- **"p = 0."** Write "p < 10^-300" (N2).
- **"The factors explain none of the edge" or "the edge is not momentum."** Say: an attribution after the fact; the intercept keeps 102 % and 100.5 % of the two mean differences because the payoffs' fitted contribution to the mean is small (+0.000241 against −0.010526; +0.000014 against −0.002687); `matrix-select`'s difference co-moves with the momentum payoffs (R² 0.12) (Minor 5).
- **"A Brier skill of 0.013" without its split.** On these months it is skill on "move or no move": `matrix-select`'s direction skill is below climatology, the encoders' is not separated from 0, and the edge of `enc-ols` over `enc-softmax` is in the move part (Minor 5). Exploratory, test months.
- **Any single year of the split** (Minor 5).
- **"16 of 16 predicted and flagged", "296 controls can be flagged".** True; say that the first is an assertion of the run and the second §3.2's definition (N5, N6).
- **"The stderr holds no warning."** It holds 26,700 expected log lines per detector step (N1).

## Clean: checked and found right, so nobody re-checks it blindly

- **Leakage across the two runs:** the confirmatory seed was drawn once (step 3) and once more for the identity rerun the dated line registers; the descriptive run used its own seeds (20261029, 29119, 29120). One frozen code for all four steps, recorded in each output.
- **The stop rule (§7.4):** `verdicts.jsonl` exists in all three detector folders with `all_pass` true; stdout carries one line per step, after the gates.
- **The registered variants:** the 42 names of the file's header are §2's, column for column.
- **The statistics:** Wilson, Newcombe method 10 (ψ as registered), the exact McNemar test, the normal interval of a mean rate, the paired mean difference, the first-m curve in date-then-pair order, the cut-date bootstrap (64 dates shared by both pairs, 8 per subset, 2,000 subsets, the 2.5th and 97.5th percentiles). Two other intervals for the deciding cell give the same reading: Wald [−4.19, −3.31], a bootstrap over leaks [−4.18, −3.31].
- **H15's labels and qualifier,** applied by my own reading of `docs/HYPOTHESES.md`.
- **The denominators, given the run's own flags:** 10,000; 9,182 not constant (818 constant); 8,641 `designed: no` (1,288 `yes`, 71 `cell`). Descriptive: 8,828 and 8,695. `constant_h1_cuts`, `designed` and `placement_invariant` are columns of `verdicts.jsonl`: the not-constant cell, "276 of 375" and the invariant subset are recomputed from them, not re-derived. Only the descriptive run has an outside witness, and only for the constancy flags and the tags (iterations 3 and 4, A2); `placement_invariant` has none in either run.
- **Time handling in the case study:** hourly grid flags, `known_at` against the decision time, the half-open cut at 2025-01-01 00:00 UTC, UTC calendar years.
- **Numerics in the case study:** the regression's identities hold to 1e-10 in the stored values; the split's parts sum to 2e-17.

## Not checked

- **The bars.** Nothing here reads a real bar: the M2 rule's inputs, a zero-volume bar, the last row of the series are known only through the run's counts and the header's cut lists.
- **The row-level read split, the distinct expressions, the controls' flags, the gates and the twins:** read from `detectors.json`; the per-leak file does not hold them.
- **The case study's bootstrap intervals and HAC standard errors:** not recomputed (that needs the `series.npz` arrays and the bars: a new contact). The HAC code was read; the bootstrap is Report n°2's function, audited in iteration 3.
- **`detectors.md` and `casestudy.md` digit by digit.** The brief asks for the numbers from the files. I read both; the lines I quote agree with the JSON.
- **The full suite, the mutants, ruff, `cargo test`, Kani:** not re-run. The code digest is the one pass 5b-bis ran them on. `tests/test_casestudy.py` was not run either.
- **Line 1208 by behaviour** (N6), and the 21-mutant table (deferred by Abdou's rule).
- **The data manifest digest:** compared across six recorded outputs, not recomputed (it hashes `data/`).
- **The per-leak flags that define the denominators** (`constant_h1_cuts`, `designed`, `placement_invariant`) on the confirmatory population: no outside witness; see "Clean".
- **Newcombe's 1998 paper:** still not re-read; my rewrite is the method 10 of pass 5b.
- **`docs/ITERATIONS.md`, `resume-5.md`, `CLAUDE.md`, the agent files:** their uncommitted edits were not audited beyond `git diff --stat` (text only; nothing under `python/` or `crates/`).

## Contacts

- **Real bars: none.** No read of `data/`, no `load_klines`, no registered line, no `adversary`, no `casestudy`.
- **The vault and the validation year: not opened.** I opened, read and hashed nothing under `runs/vault/`, and ran no `ls` on it. `git status` (plain and `--ignored`) walks the folder to classify its entry names, and `git check-ignore` tests paths against `.gitignore`: that is how I know that neither `OPEN` nor `ACCESS.log` exists.
- **Seeds 20261118 and 20261119: not drawn.** They appear in my scripts nowhere. **Seed 20261120** (and 29120 for the descriptive run) was read from each file's header and used to reproduce the cut-date bootstrap on the stored verdicts: the same stream on the same flags, no bar. My own seeds: 97531 and 424242 (bootstraps on stored verdicts), 5 (synthetic closes).
- **Seeds executed on synthetic bars:** 51118 and 51119 (A6, A7, A7b), and 51118 for the `digest` command.
- **`runs/`, read only:** the four folders of wave 4, their five `.out` files and the log; `2026-11-19-casestudy/` and its log; `2026-10-29-h1-adversary/adversary.json`, `adversary.md` and `run.json`; `2026-10-30-twins/twins.json`; `report2.json` of `2026-10-30-report2-wsl/` and `report3.json` of `2026-10-30-report3/`; `2026-11-18-quantile-table/table.json`. The two `series.npz` were hashed, never loaded.
- **Written:** this file; `audit-2a-scripts/` (nine scripts and the two tables); scratch outputs in the session's scratchpad. Python wrote its bytecode caches under `python/`, which git ignores; the code digest is unchanged after the audit's runs.
- **Not mine:** while I worked, `.claude/briefs/iteration-5/paper.md` changed and `paper-draft-1.md` and `paper/` appeared in the working tree. I did not write or read them; they are phase 2b's object.

## Commands

All from `C:\Users\abdou\ols-prime\python`, with `uv run --no-sync`. Scripts are in `.claude/briefs/iteration-5/audit-2a-scripts/`.

- `git status --short`, `git log --oneline`, `git diff --stat` between `b71ba65`, `f12b9b5`, `1088aac` and the working tree, `git diff --quiet` on `python crates`, on `wave4.py` and on `casestudy.py`, `git show f12b9b5:.claude/briefs/iteration-5/wave4.py`, `git ls-files runs`, `git check-ignore -v`, `git status --short --ignored runs`. No command that rewrites the tree.
- `sha256sum` on the files listed under step 2.
- `python -c "from olsprime.bench.provenance import code_digest; …"`, before and after.
- `python -m olsprime.bench.detectors digest --seed 51118 --placement quantile --n 10000 --table ../runs/2026-11-18-quantile-table/table.json`.
- `python ../.claude/briefs/iteration-5/audit-5b-bis-scripts/y3_verdicts.py <folder>` and `python -m tests.test_detector_verdicts <folder>`, on both detector folders.
- **A1,** `a1_recompute.py <folder> <out.tsv>`: the reader and the table of one run; no `olsprime` import.
- **A2,** `a2_external.py ../runs`: the descriptive run against iteration 3's `adversary.json` and iteration 4's `twins.json`, leak by leak; the two detector runs against each other.
- **A3,** `a3_beside.py <folder>`: the pairs at one run per cut with FI ÷3, the gap by denominator, convention and family, H15's labels on each registered cut-date subset, single dates. Its output is quoted in Minors 1 to 3; it imports A1.
- **A4,** `a4_casestudy.py ../runs`: 382 checks on `casestudy.json`, its labels, and the two reports' JSON.
- **A5,** `a5_builders.py`: the three factor builders on synthetic hourly bars.
- **A6,** `a6_classes_probe.py`: six planted verdicts through `check_classes`, synthetic bars.
- **A7,** `a7_split_canflag_probe.py 150` and **A7b,** `a7b_canflag_probe.py 3000`: lines 1172 and 1208, synthetic bars.
- **A8,** `a8_headline.py <scripts folder>`, with `PYTHONUTF8=1`: the Markdown tables of this file, from the two full tables.

## Bolder check

None. The per-leak file already carries what the Minors needed, and every number they add is in the tables above as "mine only". A new check that would need the bars or a seed is not worth a contact before the paper.
