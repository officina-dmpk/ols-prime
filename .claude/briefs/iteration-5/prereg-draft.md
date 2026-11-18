# Draft — Leak detectors measured against each other (iteration 5)

- **Status:** draft v3, written 2026-11-18 by the orchestrator of iteration 5's second session: v1 (commit `8473776`), fixed for audit pass 5a (`audit-5a-findings.md`) into v2, then for pass 5a-bis (`audit-5a-bis-findings.md`, register with fixes, no Blocker) into v3, adopting its replacement texts verbatim. Nothing here is registered. Next, the text goes to `docs/PROTOCOL.md` (new section of the same name) and the hypotheses to `docs/HYPOTHESES.md`, with dated change-log lines, and is committed before any detector touches the confirmatory population.
- **Inputs:** `prereg.md` (the brief), `reading-papers.md`, `misses-findings.md`, `audit-5a-findings.md`, `python/olsprime/bench/adversary.py` (leak expressions, `SeriesView`, `WindowView`, `RecordingView`, `evaluate_fast`), `twins.py`, `invariance.py`, `perturb.py`.
- **What is measured:** each detector's catch rate on one generated population of leaks, its flags on honest and cancelled controls, how the detectors overlap, and how much each verdict depends on a convention. Not a ranking of detectors in general: the rates describe this generator, these bars and these cut dates.
- **The disposition of every finding of pass 5a** is the table at the end (§9).

## 0. Facts the design rests on (checked in the code, or read verbatim in the source, 2026-11-18)

1. **A missing bar.** `SeriesView.at` and `_window` give NaN for a row outside the series. Making a row outside **a run's input** missing is new in this iteration: truncation and re-tiling do it (§2). A comparison with NaN is false (`Cmp.evaluate`; `Same`, `Colour`, `Pattern` and `Cell` likewise), so a **binary** leak is never NaN: where a future read is missing it returns a finite value, 0 for a single comparison and possibly 1 under `Logic` (OR, XOR). A value node (`At`, `Agg`, `LogRatio`, `Rel`, `Raw`, `WSum`) propagates NaN, so a **continuous** leak's output turns missing. H1's catch rule (`adversary.py:1147`) counts a move above 1e-9 **or** a change of missingness.
2. **Compared rows.** Only rows `t - 10 .. t` can read a bar after `t` (`FUTURE_REACH = 10`); the rows scored by H1 among them are compared (`Bench.scored`). At every cut row `t` is scored, and every leak reads a bar after its row (`draw_leak` asserts a future reach of 1 at least), so every detector that removes or changes bar `t + 1` touches a read of every leak at every cut.
3. **Fonseca, arXiv 2607.04958 §8.3, read verbatim on 2026-11-18** (orchestrator, browser pane; auditor, plain fetch): the two-run detector "re-executes the pipeline on perturbed future data at sampled epochs and flags a change"; the tiling detector "compares outputs across shifted data windows". The text gives no perturbation law, no epoch rule, no run count and no tolerance (all 11 occurrences of "perturb" checked). No "default" two-run detector exists to copy: ours is defined here, and the paper says so.
4. **freqtrade**, `develop`, `freqtrade/optimize/analysis/lookahead.py`, read verbatim by the auditor on 2026-11-18 (SHA-256 `25b02b2d4f6e4317d8855b01976a3fef112e56280b7a33954634ed4dc51e2cca`), with `trim_dataframe`: the slice ends one candle after the date checked (`to_dt`, "since it won't buy on the last candle"); `analyze_indicators` compares `full_df.loc[cut_df.index]` with `cut_df`, that is **every kept row, the slice's last row included**, NaN equal to NaN; `compared_dt` serves only `report_signal`. Not traced: whether `load_bt_data` trims the end through `trim_dataframe`. **Causify DataFlow**, arXiv 2512.23977, read verbatim by the auditor: Theorem 4.24 (input window `[t − 2τ + 1, t]`, outputs on `[t − τ + 1, t]`) and Remark 4.25 (tiles of length τ ≥ L, compared with the full run "up to numerical precision").
5. **The generator's ties to H1.** The default placement draws half of the thresholds on body, wicks, range, fill and close location inside H1's bands (`BANDS`). The `quantile` placement (§1.3) replaces the draw by H1's bands with a draw by the pre-2019 bars; the overlap remains (§1.5). **These ties remain** in both placements, and are stated wherever a rate is read: the `designed` tag and the 90-bar reference window; the margin position (`PUSH`), with margin 1 drawn with probability 0.7; future offset 1 drawn with weight 0.4; `k = 0` half the time for fill and close location, the two quantities H1 pushes against bar `t` alone; the cell boundary `SMALL_BODY` (H1's 0.01) half the time.

## 1. Populations and the quantile table

1. **Confirmatory population.** `generate(10_000, seed=20261118, placement="quantile")`. Seed 20261118 has never been run. Its first use is the official run after audit pass 5b's GO. A run of n' leaks is the first n' of the population (`draw_leak(seed, i)` has its own stream), so development and throughput runs use seed **51118** only, never reported.
2. **Descriptive population.** The 10,000 leaks of seed 20261029, placement `h1-bands`, as run in iteration 3. Its FI rates are known (97.95 % any-cut, 86.85 % per cut) and its misses were studied: every number on it is descriptive.
3. **Threshold placement `quantile`.** A new, opt-in keyword argument of `generate` and `draw_leak`; the default stays `h1-bands`, and a test shows that seed 20261029 reproduces its saved JSON byte for byte. `placement` is **not** a field of `AdversaryConfig`, so that `_config_json` (`adversary.py:1507`), the byte identity of `adversary.json` and the write-back check of `twins.py:399` are unchanged.
   - **The draw, at code level.** Under `quantile`, `_threshold(rng, q)` for every `q` in the table (item 4) consumes exactly one draw, `level = rng.uniform(0.02, 0.98)`, and returns `float(np.quantile(table[q], level, method="linear"))`, in place of the band draws (for the six banded quantities) or of the H1-independent uniform draws (taker shares on [0.05, 0.95], `wick_ratio` on [−2, 2]). The `position` tag is `_band_position(q, c)` for the six banded quantities, and unchanged for the others ("window-dependent", "none"). Nothing else in the generator changes: margins, offsets, operators, families, and the cell boundary, which stays `SMALL_BODY` with probability 0.5 and otherwise calls `_threshold(rng, "body")`, hence the table.
   - Under `quantile`, the `designed` tag keeps its definition. A `designed: no` share is therefore **not comparable** between the two placements, and the `cell` value of the tag stays a third class (it is neither `yes` nor `no`).
4. **The quantile table** (decided before any bar was read for it; computed on 2026-11-18, item 5).
   - **Bars:** BTCUSDT and ETHUSDT daily, read through `protocol.load_klines(pair, "1d", caller="iteration-5 quantile table")` and `invariance.development_bars`, then the rows with `open_time < 2019-01-01 00:00 UTC`: every bar of the training period before the first test month, none of them a scored row (the first scored row, 2019-01-01, is row 502).
   - **Quantities:** `body`, `upper_wick`, `lower_wick`, `range`, `fill`, `close_location`, `taker_base_share`, `taker_quote_share`, `wick_ratio`, as `adversary.quantities` computes them. The two taker shares and `wick_ratio` go on the table too (pass 5a, m5): their current draws ignore the bars, and a threshold far from the realised values gives a constant leak, whose truncation verdict is the convention's (B2).
   - **Values kept:** the finite values of both pairs, pooled. For `body`, `upper_wick`, `lower_wick` and `range`, only the strictly positive ones: an atom at 0 would give thresholds such as `upper_wick[s+1] < 0`, never true.
   - **Stored:** for each quantity, the sorted kept values as float64. Serialised as JSON with sorted keys, each value written with `repr`, no spaces; SHA-256 of those bytes. The table is written to `runs/2026-11-18-quantile-table/table.json` (outside git: it derives from Binance data) and its digest registered here. The code that builds it is `.claude/briefs/iteration-5/quantile_table.py`; wave 3 moves the same function into `bench/adversary.py`. Tests pin the builder on a fixed synthetic input, and check that `table.json` hashes to the registered digest where the file is present; `generate` itself only loads the registered bytes (§1.7).
   - **Method:** `np.quantile(values, level, method="linear")` (numpy's default, Hyndman and Fan type 7).
   - **Consequence, added to the generator's "never produced" list (pass 5a, m9):** a threshold beyond the 2nd or the 98th percentile of the pre-2019 values of its quantity.
5. **The table as computed, 2026-11-18 20:32 UTC** (a contact with the training bars, logged in the change log). The choices of item 4 that shape the table (bars, rows, quantities, values kept, storage, method) and the draw of item 3 were written before the read and not changed after it; the later edits of items 3, 4 and 7, after pass 5a-bis, add only pinning and wording.
   - **Rows:** 502 per pair, 2017-08-17 to 2018-12-31. **Values kept:** 1,004 for body, range, fill, close location and both taker shares; 997 upper wicks, 994 lower wicks (the others are 0); 987 wick ratios.
   - **SHA-256 of `table.json`:** `527e01ba7028fb5666e694fcadd5b22d2fdea31718d96e53d98a29e383183c43`. The run folder also holds `summary.json` (the numbers of this item).
   - **Thresholds reachable** (the 2nd and 98th percentiles): body 0.00093 to 0.147; upper wick 0.00104 to 0.0725; lower wick 0.00091 to 0.134; range 0.0150 to 0.261; fill 0.022 to 0.921; close location 0.059 to 0.964; taker base share 0.298 to 0.596; taker quote share 0.296 to 0.596; wick ratio −3.66 to 2.91.
   - **Share of levels in [0.02, 0.98] whose quantile falls inside H1's band** (a grid of 960,001 levels): body 84.2 %, upper wick 39.7 %, lower wick 31.5 %, range 100 %, fill 67.5 %, close location 55.4 %. Under `h1-bands` each is 50 % by construction.
6. **What this means for the reading of FI's rate.** The `quantile` placement replaces the draw by H1's bands, not the overlap with them: natural thresholds fall inside the bands more often than half the time for body, range, fill and close location, and less often for the wicks. It is a placement by the bars, not one neutral to FI. The levels, the table and the draw were not changed after the read, and stay as they are. The `position` strata cannot isolate the placement (on a neutral seed, 4,815 of 10,000 leaks are tagged `inside`, only 520 of them thresholds). So a **placement-invariant subset** is registered: the leaks drawn with no `_threshold` call, whose expressions are identical under both placements (8,258 of 10,000 on a neutral seed). FI's share and H15's difference are reported on it and on its complement, never deciding (§4.14).
7. **Pinning the implementation without the fresh seed.** The digest registered for the generator is that of the **development** population: seed 51118, n = 10,000, `placement="quantile"`, the registered table. It is the SHA-256 of one line per leak, in order, holding `repr(leak.expr)`, the output and the tags (not `render()`, which rounds thresholds to four digits). The numpy version is recorded beside it. `generate(..., placement="quantile")` loads the registered bytes of `table.json` and refuses to run on a digest mismatch; it never rebuilds the table (`np.log` can differ by an ulp between machines).
   - That digest needs wave 3's code. It is added by a dated change-log line before audit pass 5b's GO, and that line adds only the digest, the commit and the numpy version. If the line and item 3 disagree, item 3 is normative. Pass 5b reproduces the digest on the machine of the official run.
   - A digest of the confirmatory population would be a first use of seed 20261118: if ever wanted, it is a deliberate, logged step after 5b, expressions only.
   - The new run's JSON records `placement` and the table's digest (they are outside `AdversaryConfig`).
   - **How `generate` gets the table.** A `table_path` argument, required with `placement="quantile"`; the bytes are checked against the registered digest before use. `table.json` stays outside git (it derives from Binance data; committing it is Abdou's licence decision), and `quantile_table.py` rebuilds it, checked by the same digest. Tests that need the real table skip where it is absent, so GitHub Actions run the synthetic tests only; the official runs happen on the machine that holds it.
8. **Bars.** BTCUSDT and ETHUSDT daily, H1's interval and folds, every read through the seal (`development_bars`), as the adversary.

## 2. Detectors

**Shared ground.** All detectors of the primary analysis share one cut schedule, **H1's 16 cuts**: 8 dates, the same row indices on both pairs (502, 1048, 1233, 1597, 1994, 2100, 2143, 2664), chosen by `invariance.choose_cuts` with seed 20261027. The cut of 2019-01-01 has one scored compared row. FI, TRUNC-0, TWO-RUN and SHUFFLE share the compared rows (§0.2); TRUNC-1 and RETILE are truncation at other dates (items 3 and 4). All share H1's catch rule (§0.1). A leak is **caught by a detector at a cut** if some compared row is flagged; **caught** if caught at one cut at least. The detectors do **not** make the same number of re-executions per cut (§4.8): every table gives the runs per cut, and every comparison is also reported at equal counts.

1. **FI (future invariance).** H1's perturbation, ×3 and ÷3 at each cut, exactly as `bench/invariance.py` and the adversary run it (perturbation seed 7). Caught at a cut if either direction moves an output. Two runs per cut; reported also with ×3 alone and ÷3 alone.
2. **TRUNC-0.** The run's input ends at bar `t`: every bar after `t` is missing (NaN in the window). Compared rows: §0.2. One run per cut (truncation is deterministic).
3. **TRUNC-1, freqtrade's indicator comparison.** The input ends at bar `t + 1`, and the compared rows are the scored rows among `t − 9 .. t + 1`, the slice's last row included, as `analyze_indicators` does. **It is TRUNC-0 run at the cut `t + 1`, one code path:** the same mechanism one bar later, a date-shift replicate, not a second mechanism. Like RETILE, it is a secondary row of the union and stays out of §4.7's pairs; it is reported against TRUNC-0 as the one-bar date shift. Its flags are **not** assumed to lie inside TRUNC-0's (at a different date, XOR combinations differ).
   - **Asserted:** row `t + 1` exists and is scored at every cut of both schedules. The cuts where `t + 1` is the series' last row are counted; they cannot flag.
   - The paper makes no claim about "freqtrade's rate": we rebuild its comparison on our expressions, not its tool. Not traced: freqtrade's `load_bt_data`.
   - *Deviation from v1, dated 2026-11-18:* v1 compared rows `t − 10 .. t` only, which drops row `t + 1`, the one row where a read at `s + 1` is missing; that arm could not catch a leak of future reach 1 (26.2 % of draws). The brief's "truncation ending one bar later" is kept; its compared rows are corrected to freqtrade's.
4. **RETILE, Causify's protocol.** Implemented by **really slicing** the bars to the input window `[e − 2τ + 1, e]` and evaluating through `SeriesView`, then comparing every scored row of the tile `[e − τ + 1, e]` with the full run.
   - Tile lengths τ ∈ {256, 365} bars, anchored at the first scored row 502 (2019-01-01): ends `e = 502 + m·τ − 1` that fall inside the scored rows. τ = 256: m = 1..8, 8 ends per pair, 2019-09-13 to 2024-08-09. τ = 365: m = 1..6, 6 ends per pair, 2019-12-31 then 30 or 29 December of each year. **28 ends in all.** None is an H1 cut (2021-12-30 is one bar before H1's 2021-12-31). The last, partial tile ends with the series and cannot flag.
   - The deepest past read is 189 bars (`k ≤ 180` and a window of 10 at most), and 2τ − τ = τ ≥ 256 > 189, so a tile's past reads are all inside its input window.
   - **Asserted, not predicted:** at each end `e`, RETILE's flags equal those of the windowed TRUNC-0 run at a cut at `e`, which wave 3 runs at the 28 ends for that purpose. For a fit-free function whose past reach fits in the window, this is an identity of the implementation. RETILE is therefore reported as truncation on another schedule, beside the others, never in the paired comparisons with FI, and in the union only as a secondary row (item 8).
5. **TWO-RUN (ours, after Fonseca's §8.3 class).** At each cut, the bars `t + 1 .. t + 10` (the only later bars the compared rows can read) are perturbed and the outputs compared.
   - **Draws:** `rng = np.random.default_rng([20261119, crc32(pair), schedule_id, k, run])`, where `crc32` is `zlib.crc32` of the pair's name in ASCII, `schedule_id` is 1 for H1's cuts and 2 for the long schedule, `k` is the cut's ordinal in its schedule (0-based), and `run` = 1, 2, …, 8 (never 0, so that no seed ends in a trailing zero and none equals the population's `[seed, i]` streams, which also use another first element). `z = rng.standard_normal((10, 9))`: rows are the bars `t + 1 .. t + 10`, columns follow `PERTURBED_COLUMNS` (open, high, low, close, volume, quote volume, taker buy base, taker buy quote, trades). Development seed **51119** in place of 20261119.
   - **The two σ share `z`** (common random numbers): the σ = 1.0 run is the σ = 0.1 run with ten times the log-perturbation. Primary σ = 0.1; secondary σ = 1.0.
   - `z` of shape `(10, 9)` is always drawn; rows past the series' end are discarded.
   - **Repair, at code level** (σ the scale, `f_j = exp(σ · z[:, j])`):
     1. `o' = o · f_open`, `c' = c · f_close`;
     2. each wick in log units, as `perturb._candle` computes it, `uw = log(h / max(o, c))`, `lw = log(min(o, c) / lo)`, is multiplied by its own factor (no offset is added, unlike `perturb.py:427-430`): `uw' = uw · f_high`, `lw' = lw · f_low`; then `h' = max(o', c') · exp(uw')`, `lo' = min(o', c') · exp(−lw')`. A positive wick stays positive and a zero wick stays zero. **Asserted in code:** `wick_ratio` is undefined in a perturbed bar iff it was undefined in the original one;
     3. on a bar with volume: `v' = v · f_volume`; the VWAP `quote / volume` is multiplied by `f_quote` and clipped to `[lo', h']`, giving `vwap'`, then `quote' = v' · vwap'`; `tb' = min(tb · f_taker_base, v')`, `tq' = min(tq · f_taker_quote, quote')`; `trades' = max(np.rint(trades · f_trades), 1)`. The taker VWAP is not repaired (stated). On a zero-volume bar, every volume, quote volume, taker volume and trade count stays 0;
     4. **Checks:** the assertion that `vwap'` lies in `[lo', h']` is made on `vwap'` as constructed, before `quote' = v' · vwap'`; any check on the stored columns uses the relative tolerance 1e-12 of `_check_valid`. `perturb._check_valid` runs on rows `t + 1 .. t + 10` only (it would otherwise judge stored bars after `t + 10`, which FI never judges).
   - **Reported per σ, on the perturbed bars:** the share of bars where the VWAP clip, the taker base cap and the taker quote cap bind; the median body and the median fill before and after. The law blows up the body (synthetic bars, σ = 0.1: median body 0.019 to 0.096, median fill 0.46 to 0.81; σ = 1.0: median body 0.93), and the paper says so.
   - **Runs:** 2 runs per cut in the primary analysis (equal to FI's), reported also with 1 run (run 1) and 8 runs.
6. **SHUFFLE (the future-shuffle twins of `bench/twins.py` as a detector).** K = 8 twins per cut, seed 20261030, `[seed, crc32(pair), k, j]`, as registered for H1's blind spots. Caught at a cut if any twin moves an output. Its seeds are keyed to the ordinal of an H1 cut: SHUFFLE exists at H1's 16 cuts only, and its twin bars are exactly those of iteration 4's run (same seed, cuts and bars). Reported also with its first 1 and 2 twins.
7. **Run counts per cut, primary:** FI 2, TRUNC-0 1, TRUNC-1 1, TWO-RUN 2, SHUFFLE 8.
8. **UNION.** Caught by any of FI, TRUNC-0, TWO-RUN (σ = 0.1, 2 runs), SHUFFLE (8 twins), on H1's 16 cuts, under the generator's convention. Secondary rows: the union with TRUNC-1, with RETILE, with σ = 1.0, with the long schedule (below), and under the mirrored convention.

**Three conventions for a missing read (TRUNC-0, TRUNC-1, RETILE).** Defined on **atomic predicates**, the element-wise comparisons inside binary nodes: the one comparison of `Cmp`, the equality of `Same`, the `> 0.5` of `Colour`, the two comparisons of `Pattern` and of `Cell`. A convention applies to **both** runs of a comparison, the original included.
- **G, the generator's (primary):** an atomic predicate with a missing operand is false.
- **M, mirrored:** an atomic predicate with a missing operand is true. For a leak whose root is a single `Cmp`, M's verdict equals G's verdict on the mirror leak (§4.9) except at exact ties `a = margin · b`; for other expressions no equivalence is claimed.
- **P, propagation (strict):** an atomic predicate with a missing operand is missing, and so is any node with a missing operand (`Logic`, `&` inside `Pattern` and `Cell`, the output). Kleene logic (missing AND false = false) is not used. For a leak with a binary root, P makes the output missing exactly where the OR mask "some read is missing or undefined" is set (the OR over the leak's reads of `isnan`); for continuous roots it need not, since `LogRatio` and `Rel` give a missing output from defined reads at a zero level. **Assertion:** under P, a leak is flagged by TRUNC-0 at every cut, unless the original output is already missing at every scored compared row where truncation removes a read.
- FI, TWO-RUN and SHUFFLE run under G only: they change values and keep a bar present. Their read mask still changes where a perturbation makes a read undefined (§4.4).

**Secondary schedule (Fonseca's sampled epochs).** FI (perturbation seed 11), TRUNC-0, TRUNC-1 and TWO-RUN (`schedule_id` 2) also run on the adversary's long schedule: 64 cuts per pair, 64 dates shared by both pairs, long cut seed 20261030. SHUFFLE has no seeds there and does not run. "The union over both schedules" is the union of those four detectors over the 16 + 128 cuts, plus SHUFFLE over the 16. It keeps the brief's "sampled dates" (committed 2026-11-18) as a secondary analysis; the primary uses H1's cuts so that the dates are held equal. Deviation logged with its date.

## 3. Controls (predicted verdicts, registered; never pooled into any rate)

1. **Past-only honest twins** (`Leak.twin`). They read bars ≤ s only, so no detector can move them: FI, TRUNC-0, TRUNC-1, TWO-RUN (both σ, 8 runs), SHUFFLE (8 twins), RETILE; under the three conventions; on both schedules; under both rules (H1's catch rule and a single changed bit). **Any flag is a bench bug: an assertion, not a hypothesis.** The share of twins constant at the compared rows of H1's 16 cuts on the original bars is reported.
2. **Cancelled controls FP1 and FP2, after Fonseca, generated.**
   - **Construction.** For a leak `L`, `v` is its future node of largest reach (`At` or `Agg` at a positive offset; for an `Agg`, its result), the first in a depth-first walk in `lhs, rhs, a, b` order on ties. The controls run under every detector, on H1's 16 cuts, and for the truncation detectors under conventions G, M and P, each with the prediction made under the same convention. The control is `twin(L)` with the node at `v`'s place, `w`, replaced by:
     - **FP1:** `w + (v − v)`;
     - **FP2-min:** `np.minimum(w, w + 0 · v)`;
     - **FP2-fmin:** `np.fmin(w, w + 0 · v)`.
   - Leaks with no `At` or `Agg` future node (colour, same-colour, hammer, star, cell: about 9.3 % in the synthetic draw) have no control. Reported: how many controls are built, and how many can be flagged at all (those where `v` is missing or undefined at some compared row in some run).
   - **Prediction, as code that shares nothing with the detectors:** a control's flags equal those of `twin(L)` with the node at `w`'s place made missing wherever `v` is undefined, run for run. For FP1 and FP2-min the prediction is that rule. For FP2-fmin it is: no detector flags anything (`fmin` ignores the NaN). In words, for a single comparison or a single continuous function: flagged at a scored row iff `v` is defined in one run and not in the other, and the twin's output there is true (binary) or defined (continuous). Inside `Logic` and `WSum` the other part can absorb the change; only the code rule applies.
   - Consequences, stated so that nobody reads them as detector failures: FI, TWO-RUN and SHUFFLE flag a control where a perturbation makes `v` undefined (through `wick_ratio`); the truncation detectors flag binary controls too, with a finite move (a cancelled term inside a `Cmp` makes it false).
   - Reported: the flags per detector against the prediction, cut by cut. A disagreement is a finding to explain, not a rate.
3. **Fonseca's classes, hand-written on our bars**, written and committed with their predicted verdicts as tests before any detector runs on them. Each class gets one verdict per detector and schedule: "every cut", "never" or "not predicted".
   - **M1:** `close[s+1] > close[s]`, gated by a boolean row mask computed once from the row index and passed at construction, since `view.at` gives no row index. The mask is false on every row that any detector compares on the schedule at hand (rows `t − 10 .. t + 1` of each cut, which covers TRUNC-1), true elsewhere. Predicted: "never" for every detector on that schedule.
   - **M2:** `close[s+1] > 2 · close[s]` and its mirror `close[s+1] < 2 · close[s]`.
     - TRUNC-0 under G: the first "never", the mirror "every cut". Under M the two swap. Both registered.
     - FI: predicted by a rule, flagged at a cut unless bar `t + 1`'s high is below two thirds of bar `t`'s close. The rule is registered now and checked against the run's output; it is not evaluated on the real bars before the run (that would be a contact).
     - TWO-RUN (σ = 0.1) and SHUFFLE: "not predicted" (SHUFFLE's would need a look at closes of the test period); reported only.
   - **M3:** a future close re-stamped to row `s`: `close[s+1]` **frozen** from the original bars and stored as a quantity of bar `s`, read at offset 0. Predicted: "never", for every detector (each run reads the same frozen column). The recomputed variant, caught by every perturbing detector, is not M3.
   - **FP1, FP2:** as in item 2, on `close`, with item 2's prediction.
   - FP2b needs declared availability metadata that our bars do not carry: not rebuilt, stated.
4. **Bench assertions, never hypotheses.** Item 1, item 2's code-level prediction, item 3's verdicts, P's assertion (§2), the read-split assertion (§4.4), the mirror assertion (§4.9), RETILE's equality with TRUNC-0, TRUNC-1's row `t + 1`, and TWO-RUN's checks are identities of IEEE arithmetic or of the code: a failure is a bug, never evidence. They are registered here and not in `docs/HYPOTHESES.md`, and they follow the stop rule of §7.

## 4. Metrics (fixed now)

Computed for each detector on the confirmatory population, n = 10,000, under convention G unless said otherwise.

1. **The any-cut share:** caught at one of the 16 cuts at least, with its Wilson 95 % interval. Per family and per `position` stratum (`inside`, `outside`, other).
2. **The mean per-cut rate:** the mean over leaks of the share of the 16 cuts at which the leak is caught, with a normal 95 % interval over leaks; between two detectors, the paired difference of per-leak rates with its normal interval.
3. **The first-m-cuts curve:** caught at one of the first m cuts at least, m = 1, 2, 4, 8, 16, with the 16 cuts ordered by date, then by pair (BTCUSDT before ETHUSDT).
4. **Through a missing read or through a changed value.** For each `(quantity, offset)` read that `RecordingView` lists, `isnan` of that read is taken in each run. A catch at a row is **through a missing read** when at least one read is missing in one run and not in the other there, whatever the output did; otherwise it is **through a changed value**. The two shares of each detector's catches are reported. (The OR mask over the reads serves convention P only, §2.) **Asserted:** 100 % of TRUNC-0's, TRUNC-1's and RETILE's catches are through a missing read. The v1 "finite-only rule" is kept as a sensitivity under its true name, "ignores outputs that turn missing", and is never read as the split above.
5. **Conventions.** TRUNC-0, TRUNC-1 and RETILE are reported under G, M and P, with P's assertion. The paper's sentence is fixed now: "truncation's rate lies between X and Y depending on how a missing bar is read", X and Y the smallest and largest of TRUNC-0's any-cut shares under G, M and P; the G-to-M range is given beside it.
6. **Denominators,** for every share above: all 10,000 leaks; the leaks **not constant** at the compared rows of H1's 16 cuts on the original bars (`twins.py`'s `constant` flag: the same output, bit for bit, at every compared row of H1's cuts), a property of the population and the bars, not of any detector; and the `designed: no` leaks (`cell` excluded).
7. **Pairwise,** for every pair among FI, TRUNC-0, TWO-RUN (σ = 0.1, 2 runs), SHUFFLE (8 twins): the 2×2 table of any-cut verdicts, the discordant counts b and c, the difference of shares with Newcombe's 95 % interval for paired proportions (method 10, 1998), and the exact two-sided McNemar p-value. Only TRUNC-0 against FI decides anything (H15); the other five pairs are descriptive. TRUNC-1 against TRUNC-0 is reported in the same form, as the one-bar date shift.
8. **Equal run counts.** Each detector by runs per cut: FI with ×3 alone, ÷3 alone, and both; TWO-RUN with 1, 2 and 8 runs; SHUFFLE with its first 1, 2 and 8 twins; TRUNC with its one run. Paired comparisons at equal counts: FI ×3 alone, TWO-RUN 1 run and SHUFFLE 1 twin against TRUNC-0; FI (2) against TWO-RUN (2) and SHUFFLE (first 2). Every table gives the runs per cut.
9. **Mirror asymmetry, a measured property of each detector** (pass 5a's bolder check, adopted). The mirror of a leak whose root expression is a single `Cmp` (under either binary output) is the same leak with the operator flipped (`>` ↔ `<`), same reads, same margin, same output mapping; built deterministically, no seed. For each detector, the share of such leaks whose verdict differs from its mirror's, at each cut and over the 16 (any-cut), with Wilson intervals. **Asserted:** at every compared row where every read is defined in both runs and `a ≠ margin · b` in both runs, a leak and its mirror are flagged together. The mirror asymmetry describes a detector; it never decides H15. It is distinct from convention M, though for single comparisons the two meet (§2).
10. **The union.** For each detector, the number of leaks caught by the union and missed by the detector, with a Wilson interval whose denominator is the number of leaks caught by the union.
11. **The union's misses,** classed by constancy at the compared rows (two definitions, both named: H1's 16 cuts, as `twins.py`; both schedules, as the adversary's own flag) and by whether a secondary arm catches them (TRUNC-1, RETILE, σ = 1.0, the long schedule, convention M). SHUFFLE is in the union, so "unchanged under SHUFFLE" is not a class.
12. **Descriptive counts:** the number of distinct expressions among the 10,000; the share of the 10,000 constant at the compared rows (both definitions).
13. **Replications.** On the fresh population, FI's share and SHUFFLE's are replications of iteration 3's (97.95 %) and iteration 4's (9,688 of 10,000 moved) on another placement, and are reported as such, not as new findings.
14. **The placement-invariant subset** (§1.6): FI's any-cut share and H15's difference, on the subset and on its complement, with their intervals. Never deciding.
15. **The cut-date bootstrap** (the bolder check of pass 5a-bis, never deciding). TRUNC-0 and FI on the long schedule's 64 dates (planned in §2). 2,000 subsets of 8 dates drawn without replacement, the same dates on both pairs, seed 20261120. Reported: the 2.5th and 97.5th percentiles of the any-cut difference (TRUNC-0 minus FI) across subsets, beside H15's Newcombe interval. If that spread is wider than the 1-point margin, the paper says that H15's verdict is date-dependent.

No adjusted score and no "best detector" chosen after the run.

**Equivalence gates** (pass 5a, m4): as in iteration 3, FI's fast path must agree with H1's own path on 50 leaks (equivalence seed 3) of the fresh population. Extended: TRUNC-0 through `LeakModel` on really truncated bars (row `t` survives, since test rows keep null labels, `eval/splits.py`); TWO-RUN and SHUFFLE through `inv.outputs`. On the same 50 leaks. They follow the stop rule of §7.

## 5. Hypotheses (numbered at registration)

- **H15, truncation against future invariance (the auditor's consolidated text, adopted).** Prior: TRUNC-0 catches at least as many leaks as FI.
  - **The deciding cell, one only:** TRUNC-0 against FI; H1's 16 shared cuts; the any-cut share; all 10,000 leaks; convention G. Statistic: Newcombe's 95 % interval (method 10) of TRUNC-0's share minus FI's, [L, U] in points, against a smallest difference of interest of 1 point. Two labels are reported:
    - **Sign:** L > 0: "above FI"; U < 0: "below FI"; otherwise "not separated from FI".
    - **Margin, when the sign is not "above":** L > −1: "within 1 point"; U < −1: "by more than 1 point"; otherwise "1-point margin not resolved".
    - **The prior** ("at least as many") holds if the sign is "above"; is not refuted if the sign is "not separated" and L > −1; fails if the sign is "below"; is undecided otherwise.
  - **One registered qualifier.** If the difference has the sign opposite to the deciding cell's point difference, with an interval that excludes 0, under convention M or on the not-constant denominator, the verdict is reported with the words "convention-dependent", and the paper claims no direction.
  - **Reported beside it, never deciding:** the mean per-cut rates and their paired difference; convention P; the first-m-cuts curve; the comparisons at equal run counts (§4.8); the exact McNemar p-value; the placement-invariant subset (§4.14); the cut-date bootstrap (§4.15); TRUNC-1 against TRUNC-0, the one-bar date shift (on synthetic bars it changed the any-cut verdict of 57 of 4,000 leaks, of the order of the 1-point margin).
  - **Power.** With 3 % of leaks discordant, the paired difference's 95 % half-width is near 0.34 point and a difference of 0.49 point is detected with 80 % power; with 8 % discordant, 0.55 and 0.79 point. n = 10,000 is enough for a 1-point margin. Every interval is conditional on these bars and on 8 cut dates shared by two pairs.
`docs/HYPOTHESES.md` gets H15 only. The controls of §3 (v1's D3) are bench assertions, registered in §3.4: their clauses are identities of IEEE arithmetic or of the code, so a failure is a bug, not evidence.

Dropped, with the reason:
- From v1: **D2** ("TRUNC-0's advantage rests on catches through a missing value, and under the finite-only rule its share falls below FI's"). Every truncation catch is through a missing read by construction (now an assertion, §4.4), and the finite-only rule removes continuous leaks only, so D2's second half was fixed by the family weights, and its first half contradicted iteration 3's record (FI caught 943 of 943 continuous leaks). The convention test (§4.5) and the mirror asymmetry (§4.9) replace it.
- From the brief: "the union beats the best single detector" (the union contains every detector and the best is chosen after the run; replaced by §4.10); "no detector flags more than 0.1 % of the honest twins" (no detector can flag a past-only twin; replaced by the honest-twin assertion and the cancelled controls, §3).

## 6. What the paper may and may not claim from these outputs

- **May:** the catch rates of these detectors on this generator and these bars, with intervals; their overlap; the dependence of truncation's rate on the convention for a missing bar, as the registered sentence; each detector's mirror asymmetry; the controls' verdicts; that our two-run arm is our definition, and that its law inflates bodies; H15's two labels, with its qualifier if triggered, and the cut-date spread beside them.
- **May not:** a rate over "all leaks"; that FI is better or worse than truncation in general; that FI's rate on this population is free of H1's bands (§1.6); that re-tiling is a mechanism independent of truncation on this population; that re-tiling or truncation, as run here, applies to fitted models (a two-tile input window would change every honest output of an expanding-window fit, `min_train_rows = 365`); "freqtrade's rate" or "Causify's rate"; any comparison with Fonseca's 18/33 and 33/33 (another corpus, another language).

## 7. Order of work and contact with the real bars

1. **Before 5b's GO, no detector runs on real bars with a `quantile` population. FI and SHUFFLE run on real bars only with seed 20261029, `h1-bands`, as already run.** No new detector runs on real bars at all before 5b's GO. Wave 3 builds and tests every detector on `bench.synthetic` bars, with seed 51118 and TWO-RUN seed 51119.
2. The development-population digest (§1.7) is added by a dated change-log line before 5b's GO.
3. The descriptive run (seed 20261029) and the confirmatory run (seed 20261118) use **one frozen commit**, the one 5b passed. If the descriptive run shows a bug, the fix is logged, re-audited, and the confirmatory run is reported as run after a code change.
4. **The stop rule.** Every assertion and gate is evaluated first, on the descriptive run and then on the confirmatory run, and writes only pass or fail and counts. No rate or per-leak verdict is written or printed until all pass. A failure stops the run; the fix is logged and re-audited; the next run is reported as run after a stopped attempt.
5. Contacts already made with the real bars for this design: the auditor read two recorded outputs for counts (`runs/2026-10-29-h1-adversary/adversary.json`, `runs/2026-10-30-twins/twins.json`); the orchestrator computed the quantile table from the pre-2019 bars (§1.5). Both are logged.

## 8. Variants and seeds

No strategy variant: the count of `docs/RESULTS.md` stays at 21. Seeds:
- population: confirmatory 20261118, development 51118, descriptive 20261029;
- TWO-RUN: 20261119, development 51119;
- SHUFFLE twins: 20261030 (`[seed, crc32(pair), k, j]`);
- H1's cuts: 20261027; H1's perturbation: 7;
- long schedule: cut seed 20261030 (another role than the twins' 20261030; the two streams have different lengths and keys), perturbation seed 11;
- equivalence gate: 3;
- cut-date bootstrap: 20261120.

## 9. Disposition of audit pass 5a's findings

| Finding | Disposition | Where |
|---|---|---|
| B1 finite-only rule, D2 | Fixed: read-based split, assertion of 100 % for the truncation detectors, finite-only rule renamed, D2 dropped | §4.4, §5 (dropped), §6 |
| B2 polarity of the NaN convention | Fixed: conventions G, M, P with P's assertion; registered sentence; not-constant denominator; §0.1 "never NaN" | §2 (conventions), §4.5, §4.6, §0.1 |
| D1 consolidated text | Adopted verbatim in substance as H15 | §5 |
| M1 TWO-RUN seed | Fixed: own seed 20261119 with pair, schedule, ordinal, run ≥ 1; development 51119; σ share `z` | §2.5, §8 |
| M2 TRUNC-1 | Fixed: the faithful arm (compared rows up to `t + 1`), stated as TRUNC-0 one bar later; v1's deviation dated; no freqtrade-rate claim | §2.3, §6 |
| M3 saturating metric | Fixed: any-cut share and mean per-cut rate, first-m-cuts curve; roles in H15 fixed | §4.1-4.3, §5 |
| M4 unequal run counts | Fixed: runs per cut in every table, reports at 1, 2, 8 runs, comparisons at equal counts | §2.7, §4.8 |
| M5 TWO-RUN repair | Fixed: code-level recipe, wicks from their own log factor, zero-volume bars, VWAP clipped, `_check_valid` | §2.5 |
| M6 cancelled controls | Fixed: construction rule, code-level prediction, FP2 under `np.minimum` and `np.fmin`, counts of controls built and flaggable | §3.2 |
| M7 fresh seed protected by bars | Fixed: no new detector on real bars before 5b's GO; one frozen commit for both runs | §7 |
| M8 quantile population | Fixed: table computed now, method, filter, zeros, SHA-256, band shares; one draw; `SMALL_BODY` kept and listed; §0.5 reworded; `placement` out of the config; development digest. **Open question to 5a-bis:** the development digest needs wave-3 code; is a dated change-log line before 5b's GO acceptable? | §0.5, §1.3-1.7 |
| M9 decision rule, power | Fixed: H15's rule and power statement; the other pairs descriptive | §5, §4.7 |
| M10 RETILE | Fixed: real slicing, 28 ends registered, asserted equality with windowed TRUNC-0; no independence or fitted-model claim | §2.4, §6 |
| m1 metric 6 degenerate | Fixed: classes by constancy and by secondary arms | §4.11 |
| m2 known rates | Fixed: replications stated; `designed: no` not comparable; `cell` a third class | §4.13, §1.3, §4.6 |
| m3 Fonseca's classes | Fixed: M2 both polarities; M3 frozen; M1 with a row mask; SHUFFLE's M2 not predicted, so no contact | §3.3 |
| m4 equivalence gates | Fixed: kept for FI and extended to TRUNC-0, TWO-RUN, SHUFFLE | §4, end |
| m5 share and wick-ratio thresholds | Fixed: on the quantile table | §1.4 |
| m6 honest twins scope | Fixed: every detector, convention, schedule and both rules; cut set of "constant" named | §3.1 |
| m7 secondary schedule | Fixed: TWO-RUN's seeds there; union over both schedules defined; 64 shared dates | §2 (secondary schedule) |
| m8 metric 5 denominator | Fixed: leaks caught by the union | §4.10 |
| m9 levels never beyond the range | Fixed: added to "never produced" | §1.4 |
| m10 SHUFFLE and the cuts | Fixed: H1's cuts only; same twin bars as iteration 4; ties noted under the mirror assertion's conditions | §2.6, §4.9 |
| m11 §0 header | Fixed: header and freqtrade digest | §0 |
| Nit: 16 cuts are 8 dates | Fixed | §2 (shared ground) |
| Nit: Newcombe's method; distinct expressions | Fixed | §4.7, §4.12 |
| Nit: seeds omitted | Fixed | §8 |
| Nit: §0.1 "outside a run's input" | Fixed | §0.1 |

## 10. Disposition of audit pass 5a-bis's findings

| Finding | Disposition | Where |
|---|---|---|
| F1 read split per read | Fixed, verbatim; OR mask kept for P only | §4.4, §2 (P) |
| F2 H15's labels | Fixed, verbatim: sign, margin, prior | §5 |
| F3 VWAP assertion | Fixed: on `vwap'` as constructed, 1e-12 on stored columns, `_check_valid` on t + 1 .. t + 10, binding shares reported | §2.5 |
| F4 TRUNC-1 carried through | Fixed: one code path, row t + 1 asserted, secondary row of the union, out of the pairs, date-shift report, M1's mask to t + 1 | §2 (shared ground), §2.3, §2.8, §3.3, §4.7, §4.11 |
| F5 development digest | Fixed: n, `repr`, numpy version, table loaded by bytes and digest-checked | §1.4, §1.7 |
| F6 FI early estimate | Fixed, verbatim | §7.1 |
| F7 stop rule | Fixed, verbatim | §7.4 |
| m1 §1.6 binds nothing | Fixed: wording of §0.5, placement-invariant subset, "may not" | §0.5, §1.6, §4.14, §6 |
| m2 P's wording | Fixed | §2 (P) |
| m3 H16, Fonseca's verdicts | Fixed: assertions in §3.4, H15 only in HYPOTHESES; verdicts per class and detector; FI's M2 rule (checked against the run, not evaluated before it) | §3.3, §3.4, §5 |
| m4 TWO-RUN's recipe | Fixed | §2.5 |
| m5 body blow-up | Fixed: stated and reported | §2.5, §6 |
| m6 provenance | Fixed | §1.7 |
| m7 cut order | Fixed: by date, then pair | §4.3 |
| m8 controls' conventions, node order | Fixed | §3.2 |
| m9 "opposite sign" | Fixed | §5 |
| m10 quantile contact | Logged in the registration's change-log line, with "not verifiable" for `method="linear"` and "run once" | change log |
| m11 standing promises | Logged in the registration's change-log line: the extreme-shape cut and H14 dated as not run in iteration 5 so far | change log |
| Bolder check | Adopted: cut-date bootstrap, never deciding, seed 20261120 | §4.15, §8 |
