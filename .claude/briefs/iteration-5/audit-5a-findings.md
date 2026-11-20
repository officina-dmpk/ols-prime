# Audit pass 5a — findings on `prereg-draft.md` (iteration 5)

- **Agent:** `leakage-auditor`, 2026-11-18. Read-only: this file was not written to the repository; the orchestrator places it at `.claude/briefs/iteration-5/audit-5a-findings.md`.
- **Object:** `.claude/briefs/iteration-5/prereg-draft.md`. Line numbers below are that file's.
- **Read:** `audit.md`, `prereg.md`, `reading-papers.md`, `misses-findings.md`, `detectors.md`, `paper.md`, `resume-2.md`, iteration 5 of `docs/ITERATIONS.md`, `docs/PROTOCOL.md` (Leakage tests, The adversary, H1's blind spots), all of `bench/adversary.py`, `twins.py`, `perturb.py`, and `invariance.py`, `eval/splits.py`, `pipeline.py` where the cuts, the comparison and the folds are made.
- **Ran:** `pytest tests/test_adversary.py tests/test_twins.py` (44 passed, no cache written). Scratch scripts in the temp directory only, on `bench.synthetic` bars with the throwaway population seed 424242. Never seed 20261118, never 51118, never `data/`. Two recorded outputs were read for counts: `runs/2026-10-29-h1-adversary/adversary.json` and `runs/2026-10-30-twins/twins.json`.
- **Sources read verbatim, 2026-11-18** (plain fetches into empty scratch folders, grep only):
  - Fonseca's HTML: the two sentences quoted in §0.3 are exact, and "perturb" occurs 11 times. §0.3 holds.
  - Causify's HTML: Theorem 4.24 (input window [t - 2τ + 1, t], outputs on [t - τ + 1, t]) and Remark 4.25's four steps, "up to numerical precision". §0.4 holds for Causify.
  - freqtrade `develop`, `optimize/analysis/lookahead.py` (SHA-256 `25b02b2d4f6e4317d8855b01976a3fef112e56280b7a33954634ed4dc51e2cca`) and `trim_dataframe`. §0.4's sentence is accurate, but the TRUNC-1 arm built from it is not freqtrade's check (M2).
- **Synthetic rates below are not forecasts for the real bars.** They serve only for what holds whatever the bars: identities, structural zeros and predictions that fail.

## Verdict

**Register with fixes.** The design is sound: one fresh population, shared cuts, one catch rule, paired tests, controls with predicted verdicts. The fresh seed is untouched. But two results would be misread as drafted (B1, B2), one arm is not what its name says (M2), and several definitions would give different flags in two honest implementations. B1, B2 and M1 to M10 must be fixed in the text, not logged. **A re-read of the fixed text by this agent is a condition of registration**, because the fixes rewrite D1 and D2.

## Blockers

### B1. The finite-only rule does not separate "catches through a missing bar", and D2 is half identity, half false
- **Where:** §4.2 (line 49), D2 (line 60), §6 "the share of catches that rests on a missing value" (line 67). Code: `adversary.py:437-440` (`Cmp.evaluate`), `:1145-1147` (catch rule).
- **Failure.** Under truncation, **every** catch comes from a missing bar: nothing else changes. A continuous leak turns NaN, a change of missingness. A binary leak goes through NaN, then a false comparison, then output 0: a **finite** move of 1. The finite-only rule removes the first kind only. It would report about 11 % of TRUNC-0's catches as "through a missing value" when the true share is 100 %. §6's sentence cannot be supported.
- **D2 itself.**
  - (ii) "under the finite-only rule TRUNC-0's share falls below FI's" is fixed by the family weights, not by the bars. 11.1 % of leaks have a continuous node and are all lost to the rule. FI loses nothing: in iteration 3, 0 of its 138,966 catches were missing-only.
  - (i) "most of TRUNC-0's catches beyond FI are continuous leaks turning NaN" contradicts the same record: FI caught 943 of 943 continuous leaks, so TRUNC-0's extra catches can only be binary.
- **Evidence (synthetic, 4,000 leaks).** TRUNC-0 lost exactly 422 catches to the rule (10.55 %), all `exp_return` or continuous `probs`. Of its 35 catches beyond FI, 0 were missing-only.
- **Fix.**
  1. Replace metric 2 by a **read-based** split, the same for every detector. Propagate a mask "some read is missing or undefined" through each expression (the OR over its reads; `RecordingView` lists them). A catch at a row is *through a missing read* when the mask differs between the two runs there, whatever the output did; otherwise it is *through a changed value*. Assert that TRUNC-0, TRUNC-1 and RETILE have 100 % of the first kind.
  2. Keep the finite-only rule if wanted, under its true name: "ignores outputs that turn missing".
  3. Drop D2 as worded. B2's convention test replaces it.

### B2. TRUNC's rate is the polarity of the NaN convention, and constant leaks can decide D1
- **Where:** §0.1 (line 9), §2.2 to 2.4 (lines 27-29), D1 (line 59), §6. Code: `adversary.py:297-305`, `:370-372` (`Agg`: `np.max`, `min`, `mean`, `sum` propagate NaN), `:437-440`.
- **Failure.** At row t every leak reads a bar after t (`draw_leak` asserts a reach of 1 at least), and row t is scored at every H1 cut. So truncation removes a read of every leak at every cut. Whether it **flags** the leak depends on one thing: does the original output differ from what the convention writes there? For a single binary leak, TRUNC-0 flags a cut **iff the original output is 1 at a live scored row** (rows t-j+1..t for a reach j).
  - `x[s+1] > c` with a high `c` (constant 0) is never flagged. Its mirror `x[s+1] < c` (constant 1) is flagged at every cut. Same read, same leak.
  - If a comparison with a missing value counted as true, the two verdicts would swap.
  - If a missing value propagated to the output (polars' own rule: a comparison with null is null), TRUNC-0 would flag the whole population at every cut.
- **Why it can decide D1.** In the descriptive population, 1,172 of 10,000 leaks are constant at the compared rows of the 16 cuts (`twins.json`, flag `constant`). 1,025 of them are single binary comparisons, with operators split 501 `<` and 492 `>`. FI catches 870 of those 1,025. TRUNC-0 will catch exactly those whose constant is 1, about half. My inference from these recorded counts, not a measurement: TRUNC-0's any-cut share there is near or below 95 %, against FI's 97.95 %. The gap would be made of leaks that carry no information at the compared rows, split by a coin on the operator. D1's prior would then fail for a reason that is a convention, and no planned output would show it.
- **Evidence (synthetic).**
  - The identity held for 3,001 of 3,001 single binary leaks.
  - Their TRUNC-0 any-cut share: 90.9 % (missing is false), 92.9 % (missing is true), 100 % (missing propagates).
  - Mirror twins, the operator of the comparison flipped, on 2,628 single comparisons: TRUNC-0's verdict differs from the mirror's at some cut for all 2,628, and its any-cut verdict for 416 (15.8 %); TRUNC-1's any-cut verdict for 291. FI: 0 at any cut. SHUFFLE: 0 any-cut (35 at some cut, exact ties). TWO-RUN σ = 0.1: 1 any-cut (148 at some cut, 144 of them `wick_ratio`, see M5).
  - Negating the **output** changes nothing for any detector, TRUNC included: |(1-a) - (1-b)| = |a - b| (0 of 1,500). The asymmetry is in the comparison, not in the output.
  - Propagation: all 3,000 leaks flagged at every cut on the plain synthetic bars. With 3 % of bars given a zero upper wick, 2,945 at every cut and 3,000 at one cut at least: the exceptions already have an undefined read (`wick_ratio`) on the original bars.
- **Fix.**
  1. Register TRUNC-0, TRUNC-1 and RETILE under **three conventions**: the generator's (primary); the mirrored one (a comparison with a missing value is true, which equals flipping every comparison's operator); and propagation, with the assertion "flagged at every cut, unless the original bars already give an undefined read at every scored row where truncation removes one". Report the range, and fix now the sentence the paper will use: "truncation's rate lies between X and Y depending on how a missing bar is read".
  2. Register a **second denominator** for every share: the leaks not constant at the compared rows of the 16 cuts on the original bars. That flag depends on the population and the bars, not on any detector.
  3. §0.1: "a binary leak returns 0" is wrong for `Logic` (OR and XOR can return 1). Say "never NaN".

### D1, one text to register (it merges the amendments of B2, M3 and M9)
- **The deciding cell, one only.** TRUNC-0 against FI; the 16 shared cuts; the share caught at one cut at least; all 10,000 leaks; the generator's convention. Statistic: Newcombe's 95 % interval of TRUNC-0 minus FI, against a smallest difference of interest of 1 point.
  - lower bound above 0: "TRUNC-0 above FI";
  - lower bound above -1 point: "TRUNC-0 not below FI" (the prior holds);
  - upper bound below -1 point: "TRUNC-0 below FI" (the prior fails);
  - otherwise: "not separated".
- **One registered qualifier.** If the difference has the opposite sign, with an interval that excludes 0, under the mirrored convention or on the non-constant denominator, the verdict is reported with the words "convention-dependent" and the paper claims no direction.
- **Reported beside it, never deciding:** the mean per-cut rates and their paired difference, the propagation convention, the curve over the first m cuts, the comparisons at equal run counts, and the exact McNemar p-value.

## Major

### M1. TWO-RUN's seed collides with the population's streams, is shared by the two pairs, and puts the fresh seed in development
- **Where:** lines 30 and 72; `adversary.py:932` (`default_rng([seed, i])`).
- **Failure.**
  - Checked on numpy 2.5.4: `default_rng([a, b])` and `default_rng([a, b, 0])` give the same stream. If the run index starts at 0, `[20261118, cut, 0]` **is** the stream that draws leak number `cut` of the confirmatory population.
  - The recorded cuts have the same row indices on both pairs (502, 1048, 1233, 1597, 1994, 2100, 2143, 2664; the 64 long cuts too). A seed without the pair gives both pairs the same `z`.
  - "cut" is not defined (row index or ordinal), and σ is not in the seed.
  - TWO-RUN has no development seed, so wave 3 would run with 20261118, against §1.1's "its first use is the official run".
- **Fix.** A seed of its own, for example `default_rng([20261119, crc32(pair), schedule_id, k, sigma_id, run + 1])`: `k` the cut's ordinal in its schedule, a fixed length, no trailing zero. Development seed 51119. Say whether the two σ share `z` (in my reading they did, and 5 of 4,000 leaks were then caught at σ = 0.1 only).

### M2. TRUNC-1 is not freqtrade's check, and it cannot catch a one-bar-ahead leak
- **Where:** line 28 ("TRUNC-1 (freqtrade's slice) … Same compared rows").
- **Read verbatim.** `analyze_indicators` compares `full_df.loc[cut_df.index]` with `cut_df`: **every kept row, the last ones included**. `compared_dt` is used by `report_signal` only, the check that the trade's date is reproduced. `to_dt` is the date plus one candle ("since it won't buy on the last candle"), and `trim_dataframe` keeps `date <= stopdt`. I did not trace `load_bt_data` to confirm that it trims the end through that function.
- **Failure.** freqtrade's indicator comparison is therefore a truncation compared up to the slice's own last row: TRUNC-0 at a cut one bar later. The draft keeps the "+1 candle" but compares rows t-10..t only, which drops row t+1, the one row where a read at `s + 1` is missing. So TRUNC-1 as drafted cannot flag any leak whose largest future offset is 1: 26.2 % of the population (5,244 of 20,000 draws; Wilson 25.6 to 26.8 %), the canonical look-ahead (`close[s+1] > close[s]`) among them. Its ceiling is about 74 % before any bar is read. Synthetic: 0 caught of 1,053.
- **Fix.** Choose one and say so:
  - the faithful arm: compare the scored rows up to t+1. It is then TRUNC-0 at the cut t+1, a ninth date per pair and not a second mechanism; or
  - the drafted arm, renamed (for example TRUNC-LAG, "ours"), with the structural zero registered as an assertion, a second denominator (reach of 2 at least) and descriptive pairwise tests only.
  - In both cases the paper makes no claim about "freqtrade's rate". Do not assume TRUNC-1's flags lie inside TRUNC-0's: per (leak, cut) they did not for 50 XOR combinations of 4,000 leaks.

### M3. The only confirmatory metric saturates
- **Where:** §2 (line 24), §4 (lines 47-55).
- **Failure.** "Caught at one of 16 cuts at least" compresses per-cut differences. Iteration 3: FI 97.95 % any-cut, 86.85 % per cut. Synthetic, any-cut then per cut: FI 98.1 % and 86.8 %; TRUNC-0 92.3 % and 66.6 %; TWO-RUN σ = 0.1 83.4 % and 41.9 %. The any-cut share favours a detector that flags by chance at each cut; the per-cut rate favours FI, whose bar t+1 is designed. Registering one alone picks a side, and "nothing else is reported as confirmatory" then bars the other.
- **Fix.** Register both, as the adversary does: the any-cut share (Wilson) and the mean per-cut rate (normal interval over leaks; the paired difference of per-leak rates). Add the curve "caught at one of the first m cuts at least", m = 1, 2, 4, 8, 16, in the bench's fixed cut order. Their role in D1 is fixed above.

### M4. Unequal numbers of re-executions per cut
- **Where:** line 24: "a difference between two detectors comes from what each changes, not from where it looks".
- **Failure.** Per cut, FI makes 2 perturbed runs, SHUFFLE 8, TWO-RUN 1 and TRUNC 1. A paired test of FI against TWO-RUN confounds the perturbation law with the run count, and SHUFFLE's share is an 8-run share.
- **Fix.** Report each detector by run count: FI with ×3 alone, ÷3 alone and both; SHUFFLE with its first 1, 2 and 8 twins; TWO-RUN with 1, 2 (for example `z` and `-z`) and 8 runs. Make the paired comparisons at equal counts, and give the runs per cut in every table.

### M5. TWO-RUN's bar repair is under-specified and degenerate
- **Where:** line 30.
- **Loose.** Not fixed: the shape and order of the draws (by bar or by column, in which column order); whether every later bar is drawn or only t+1..t+10; the rounding of `trades`; zero-volume bars (H1 keeps their zeros, "trades ≥ 1" would not); and the VWAP, which is not repaired and can leave [low, high].
- **Degenerate.** "high = max of the four prices" after four independent factors sets the upper wick to exactly 0 whenever the perturbed high is not the largest: 55 % of later bars on synthetic bars, at σ = 0.1 and at σ = 1.0. `wick_ratio` is then undefined in 83 % of later bars (0 % originally). 5.1 % of leaks read a future `wick_ratio`: TWO-RUN's verdict on them comes from an undefined value, not from the perturbation law.
- **Fix.** Write the recipe at code level: one `standard_normal((m, 9))` over all m later bars, columns in `PERTURBED_COLUMNS` order; perturb open and close; rebuild each wick from the original log-wick times its own factor (as `perturb.py:427-430` does), so that a positive wick stays positive; keep a zero-volume bar's zeros; `np.rint`, then at least 1 where there is volume; say what happens to the VWAP. Run `perturb._check_valid` on the result.

### M6. The cancelled controls: predictions wrong in three places, construction loose in four
- **Where:** §3.2 (lines 39-42), D3 (line 61).
- **Wrong.**
  1. "FI, TWO-RUN, SHUFFLE never flag them" fails wherever `v` is undefined in one run only. Synthetic, 2,711 FP1 controls: TWO-RUN flagged 119, because of M5's zero wicks. With 3 % of bars given a zero upper wick, FI flagged 73 and SHUFFLE 111. All through `wick_ratio`.
  2. "not where it feeds a comparison whose other branch is unchanged": a cancelled term inside a `Cmp` makes the comparison false, so a binary control **is** flagged, with a finite move. TRUNC-0 flagged 2,413 of the 2,711 controls; on the 2,210 simplest ones, 1,742 of its 1,979 flags survived the finite-only rule.
  3. FP2 depends on which `min`. With `np.minimum`, FP2 had exactly FP1's flags for every detector. With `np.fmin`, no detector flagged anything. Python's `min` depends on the argument order.
- **Loose.** Which `v` when a leak has several future nodes (17.2 % of leaks); which operand; inside an `Agg` or on its result. And 9.3 % of leaks have no `At` or `Agg` future node at all (colour, same-colour, hammer, star, cell): they have no control.
- **Fix, tested.**
  - **Construction:** `v` is the future node of largest reach, the first in lhs, rhs, a, b order. The control is the twin with the node at `v`'s place replaced by itself plus `v - v` (an `Agg`: on its result).
  - **Prediction, as code that shares nothing with the detectors:** the control equals the twin with that node made missing wherever `v` is undefined. On synthetic bars this matched the control's flags cut for cut for 2,711 of 2,711 controls (every root type: `Cmp`, `Logic`, `WSum`, `LogRatio`, `Rel`, `Raw`), for each of six detectors, on both bar sets.
  - **In words, for a single comparison or a single continuous function:** flagged at a scored row iff `v` is defined in one run and not in the other, and the **twin's** output there is true (binary) or defined (continuous). 2,277 of 2,277, same scope. Inside AND, OR, XOR and weighted sums the other part can absorb the change: only the code rule applies.
  - Register FP2 in both variants, `np.minimum` and `np.fmin`, with their different predictions. Report how many controls are built and how many can be flagged at all.

### M7. The fresh seed is protected by its number only, not by the bars
- **Where:** §1.1 (line 17).
- **Failure.** Leaks are independent draws of one distribution. A development run of seed 51118 on the **real** bars and cuts estimates every confirmatory rate, to about ±1 point at 2,000 leaks, before registration and before the code is frozen. σ, τ, K or the repair could then be tuned. The draft allows it; only the plan table of `docs/ITERATIONS.md` says "synthetic bars".
- **Fix.** In the registered text: before audit pass 5b's GO, no detector other than FI and SHUFFLE runs on real bars with any population of this generator. The descriptive and the confirmatory runs use one frozen commit. If the descriptive run shows a bug, the fix is logged and the confirmatory run is reported as run after a code change.

### M8. The `quantile` population is not pinned, and its effect is overstated
- **Where:** §1.3 (line 19), §0.5 (line 13). Code: `adversary.py:755-764`, `:839`, `:857-861`.
- **Not pinned.** The draft does not say when the table is computed (wave 3 is on synthetic bars, so at the official run). Also open: the row filter (`open_time` or `known_at` before 2019-01-01); the interpolation method; NaN and exact zeros (an atom at 0 gives `upper_wick[s+1] < 0`, never true); a grid of levels or the raw sorted values; how many draws `_threshold` consumes; and whether a `Cell`'s boundary stays `SMALL_BODY` (47 % of cells use H1's 0.01). Until the code exists, `generate(10_000, 20261118)` is not a function of n and the seed.
- **Overstated.**
  - Threshold comparisons on the six quantities are about 1,080 per 10,000 leaks. In iteration 3, FI missed 16 leaks with an `outside` threshold and 25 with a taker-share threshold. The placement moves FI's any-cut share by less than half a point.
  - Ties to H1 that stay and that §0.5 does not list: margin 1 with probability 0.7 (71 % of non-threshold comparisons); offset 1 with weight 0.4; `k = 0` half the time for fill and close location, the two quantities H1 pushes against bar t alone; `SMALL_BODY`.
  - Natural quantiles of body and range probably fall **inside** H1's bands more often than half the time. If so the placement favours FI. This is an expectation, not a measurement: I read no bar.
- **Fix.**
  - Compute the table now, as a logged read of pre-2019 bars through the seal. Register its SHA-256, its method, and the share of the levels [0.02, 0.98] that lands inside each band.
  - Specify the draw: one `rng.uniform(0.02, 0.98)` in place of the band draws, nothing else changed. Decide `SMALL_BODY`.
  - Reword §0.5 and §1.3: "one tie removed; these remain".
  - Pin the implementation without touching the fresh seed: register the digest of the rendered **development** population (seed 51118, the registered table). A digest of the confirmatory population would be a first use of seed 20261118: if wanted, it must be a deliberate, logged step after 5b, expressions only.
- **For pass 5b:** adding `placement` to `AdversaryConfig` changes `_config_json` (`adversary.py:1507`) and breaks both the byte identity of `adversary.json` and the write-back check at `twins.py:399`. Keep it out of the config.

### M9. D1 has no decision rule, and no power statement
- **Where:** D1 (line 59), §4.4 (line 51).
- **Failure.** The prior is one-sided ("at least as many"), the test two-sided, and "the claim made is the interval" names no threshold. No outcome is mapped to a verdict. `prereg.md` asked for a power argument; there is none.
- **Fix.** The consolidated D1 text above. Power, to copy in: with 3 % of discordant leaks, the paired difference has a half-width near 0.34 point and a difference of 0.49 point is detected with 80 % power; with 8 %, 0.55 and 0.79. So n = 10,000 is enough for a 1-point margin. State that the nine other pairwise tests are descriptive, and that every interval is conditional on these bars and on 8 cut dates shared by two pairs.

### M10. RETILE is TRUNC-0 on another schedule, and its "prediction" cannot be checked
- **Where:** line 29, §6.
- **Failure.** For a fit-free function whose past reach (189) fits in a tile, a tile's run is the full run with the bars after the tile's end removed. The "registered prediction" is an identity of the implementation, and TRUNC-0 is not scheduled at the tile ends, so no planned output could test it. The paper could not present re-tiling as a distinct mechanism on this population. On the project's own models (expanding-window fits, `min_train_rows = 365`), a two-tile window would change every honest output.
- **Fix.**
  - Implement RETILE by really slicing the bars to [e - 2τ + 1, e] and evaluating through `SeriesView`; compare every row of the tile; run the windowed TRUNC-0 at the same ends; **assert** equality.
  - Register the ends. Anchor row 502 (2019-01-01), `e = 502 + m·τ - 1`. τ = 256: 8 ends per pair, 2019-09-13 to 2024-08-09. τ = 365: 6 ends per pair, 2019-12-31 then 30 or 29 December of each year. 28 in all; none is an H1 cut (2021-12-30 is one bar before H1's 2021-12-31).
  - Say that the last, partial tile ends with the series and cannot flag.
  - Add to §6: no claim that re-tiling or truncation applies to fitted models, nor that RETILE is independent of TRUNC-0.

## Minor

- **m1. Metric 6 is degenerate.** SHUFFLE is in the union, so a leak caught by no detector is unchanged under SHUFFLE by definition, and the class "other" is empty. Class the union's misses by constancy (both cut sets named) and by whether a secondary arm catches them.
- **m2. Known rates presented as confirmatory.** On the descriptive population FI catches 97.95 %, SHUFFLE moves 9,688 of 10,000, and their discordant counts are 169 and 62. On the fresh population these are replications: say so. `designed: no` is not comparable across the two placements; say where `cell` goes.
- **m3. Fonseca's classes.**
  - M2's verdict under truncation is its polarity (`>` never flagged, `<` always): register both.
  - M3 is ambiguous on the point that decides it. A quantity recomputed from each run's bars is caught by every perturbing detector; one frozen from the original bars is caught by none. Register the frozen one as M3.
  - M1 needs a row index, which `view.at` does not give.
  - SHUFFLE's M2 prediction needs a look at closes of the test period: log it as a contact.
- **m4. No equivalence gate for the new detectors.** The adversary stops when its fast path disagrees with H1's own path on 50 leaks. Keep that gate for FI on the fresh population and extend it: TRUNC through `LeakModel` on really truncated bars (row t survives, since test rows keep null labels: `eval/splits.py`), TWO-RUN and SHUFFLE through `inv.outputs`.
- **m5. Taker-share and wick-ratio thresholds** keep draws that ignore the bars. A share threshold far from the realised shares gives a constant leak, whose TRUNC verdict is B2's coin. Put them on the quantile table, or state the reason.
- **m6. Honest twins.** Say that the assertion covers both rules (the catch rule and a single bit), every schedule and RETILE, and name the cut set of "constant".
- **m7. Secondary schedule.** Define TWO-RUN's seeds there, and say which detectors enter "the union over both schedules". The 128 long cuts are 64 dates shared by both pairs.
- **m8. Metric 5.** The Wilson interval's denominator is not given.
- **m9. Levels in [0.02, 0.98]** never give a threshold beyond the pre-2019 range: add it to the generator's "never produced" list.
- **m10. SHUFFLE and the cuts: clean, with three notes.**
  - The twin seeds are keyed to the ordinal of an H1 cut. SHUFFLE therefore exists at H1's 16 cuts only; a long or a RETILE schedule would need new seeds, since the ordinals would collide.
  - The twin bars are exactly those of iteration 4's run (same seed, cuts and bars). Nothing about them is new; only the population is.
  - A shuffled bar can be the very bar a leak compares with. Both `>` and `<` are then false: 35 of 2,628 comparisons showed it at some cut on synthetic bars, and no any-cut verdict changed.
- **m11. §0's header** says "checked in the code or the source", while §0.4 says "summarising fetch". Both sources are now read verbatim (top of this file); update the header and cite the freqtrade digest.

## Nit

- "16 cuts" are 8 dates on two pairs with the same row indices. The cut of 2019-01-01 has one scored compared row.
- Name Newcombe's method (method 10, 1998). Report the number of distinct expressions among the 10,000.
- §7 omits the cut seed 20261027, the perturbation seeds 7 and 11 and the equivalence seed 3.
- §0.1 credits `SeriesView.at` and `_window` with a NaN "outside a run's input". The code does that at the series' ends only; the run's input is the new convention.

## Clean (checked; no need to re-check)

- **§0.1, §0.2, §0.5 against the code.** `SeriesView.at` and `_window` give NaN outside the series. `Cmp`, `Same`, `Colour`, `Pattern`, `Cell` give false on NaN. `Agg`, `LogRatio`, `Rel`, `Raw`, `WSum` propagate it, and `outputs` nulls the probabilities. The catch rule is `adversary.py:1147`. The compared rows are t-10..t, masked by `Bench.scored`. `BANDS`, `PUSH`, the 90-bar window and the `designed` tag are as described.
- **§0.3 and §0.4,** verbatim, as listed at the top.
- **The prefix property.** `draw_leak(seed, i)` has its own stream: a run of n' leaks is the first n'.
- **The fresh seed.** 20261118 and 51118 appear only in this folder's briefs, and the newest entry of `runs/` is dated 2026-10-31. This audit used neither seed.
- **Honest twins.** They read bars at or before s only. None of 800 was flagged by any of the six emulated detectors.
- **SHUFFLE's definition.** K = 8, seed 20261030, `[seed, crc32(pair), k, j]`, as registered; its four-part seeds do not collide with each other.
- **RETILE's past coverage.** The deepest past read is 189 (k ≤ 180, a window of 10 at most). The first scored row is 502, at least 365.
- **No vault or validation contact** in the plan: `development_bars`, pre-2019 bars for the table, every read through the seal.
- **Dropping the union and the twin-rate hypotheses** is right, for the reasons the draft gives.
- **n = 10,000** is enough for the paired test (M9's numbers).
- **`misses-findings.md`** matches the code and the two JSON files.

## One bolder check for the bench

**The mirror twin: a test of the detectors themselves.** For every comparison leak, also score its mirror, the same reads with the operator flipped. A detector whose verdict differs between a leak and its mirror is reading a convention, not the leak. Report each detector's mirror asymmetry with a Wilson interval, at each cut and over the 16. Assert 0 at the rows where every read is defined in both runs and the two sides are not equal. On synthetic bars, per cut: FI 0 of 2,628; TRUNC-0 2,628 of 2,628. It turns B2 from a caveat into a measured property that any future detector must report.
