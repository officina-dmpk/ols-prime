# Draft — Leak detectors measured against each other (iteration 5)

- **Status:** draft for audit pass 5a, written 2026-11-18 by the orchestrator. Nothing here is registered. After 5a, the fixed text goes to `docs/PROTOCOL.md` (new section of the same name) and the hypotheses to `docs/HYPOTHESES.md`, with dated change-log lines, and is committed before any detector touches the confirmatory population.
- **Inputs:** `prereg.md` (the brief), `reading-papers.md`, `misses-findings.md`, `python/olsprime/bench/adversary.py` (leak expressions, `WindowView`, `evaluate_fast`), `twins.py`, `invariance.py`, `perturb.py`.
- **What is measured:** each detector's catch rate on one generated population of leaks, its flags on honest controls, and how the detectors overlap. Not a ranking of detectors in general: the rates describe this generator.

## 0. Facts the design rests on (checked in the code or the source, 2026-11-18)

1. **A missing bar.** A leak reads a row outside the series, or outside a run's input, as NaN (`SeriesView.at`, `_window`). A comparison with NaN is false (`Cmp.evaluate`), so a **binary** leak returns 0, not NaN, where its future read is missing. A value node (`At`, `Agg`, continuous families) propagates NaN, so a **continuous** leak's output turns missing. H1's catch rule counts a move above 1e-9 **or** a change of missingness (`evaluate_fast`).
2. **Compared rows.** Only rows `t - 10 .. t` can read a bar after `t` (`FUTURE_REACH = 10`); the rows scored by H1 among them are compared (`Bench.scored`).
3. **Fonseca, arXiv 2607.04958 §8.3, read verbatim in the browser on 2026-11-18:** the two-run detector "re-executes the pipeline on perturbed future data at sampled epochs and flags a change"; the tiling detector "compares outputs across shifted data windows". The text gives no perturbation law, no epoch rule, no run count and no tolerance (all 11 occurrences of "perturb" in the HTML checked). So no "default" two-run detector exists to copy: ours is defined here, and the paper says so.
4. **freqtrade** (`lookahead.py`, read through a summarising fetch): the slice keeps the start and ends one candle after the date checked; indicators at the kept rows are compared exactly, NaN equal to NaN. **Causify DataFlow** (arXiv 2512.23977, Remark 4.25, Theorem 4.24, summarised): tiles of length τ ≥ L, each computed on a two-tile input window, compared with the full run "up to numerical precision".
5. **The generator's ties to H1.** Half of the thresholds on body, wicks, range, fill and close location are drawn inside H1's bands (`BANDS`); the `designed` tag, the 90-bar reference window and the margin position (`PUSH`) also follow H1.

## 1. Populations

1. **Confirmatory population.** `generate(10_000, seed=20261118)` with threshold placement `quantile` (item 3). Seed 20261118 has never been run; its first use is the official run after audit pass 5b. Any run of n' leaks is the first n' of the population, so development and throughput runs use seed 51118 only, never reported.
2. **Descriptive population.** The 10,000 leaks of seed 20261029, placement `h1-bands`, as run in iteration 3. Its H1 rates are known and its misses were studied: every number on it is descriptive.
3. **Threshold placement `quantile`** (new, opt-in argument of `generate`; the default stays `h1-bands`, and a test shows that seed 20261029 reproduces its saved JSON byte for byte). A threshold on body, upper wick, lower wick, range, fill or close location is the empirical quantile, at a level drawn uniform on [0.02, 0.98], of that quantity over the **pooled** BTCUSDT and ETHUSDT daily bars **before the first test month** (2019-01). The quantile table is computed once, written to the run folder with its digest, and its read is logged in the change log as a contact with the training bars. Taker-share and wick-ratio thresholds keep their H1-independent draws. Margins keep their draw (1 with probability 0.7, else log-uniform on [1/4, 4]); the `position` tag is still recorded.
4. **Bars.** BTCUSDT and ETHUSDT daily, H1's interval and folds, every read through the seal, as the adversary.

## 2. Detectors

All detectors share **one cut schedule in the primary analysis: H1's 16 cuts** (8 per pair, `invariance.choose_cuts` with H1's seed), the same compared rows (§0.2) and **H1's catch rule** (§0.1). So a difference between two detectors comes from what each changes, not from where it looks. A leak is **caught by a detector** if it is caught at one cut at least.

1. **FI (future invariance).** H1's perturbation, ×3 and ÷3 at each cut, exactly as `bench/invariance.py` and the adversary run it. Caught if either direction moves an output.
2. **TRUNC-0.** The run's input ends at bar `t`: every bar after `t` is absent (NaN in the window). Compared rows: §0.2.
3. **TRUNC-1** (freqtrade's slice). The input ends at bar `t + 1`. Same compared rows.
4. **RETILE** (Causify's protocol). Tile lengths τ ∈ {256, 365} bars, each tiling anchored at the pair's first scored row. A tile's outputs are computed on the two-tile input window (the previous tile and this one), which covers every past read (189 ≤ 256). A row is compared with the full run; only the last 10 rows of a tile can differ. RETILE has **its own schedule** (the tile ends that fall inside the scored rows), so it is reported beside the others and enters the union, but **not** the paired comparisons with FI. Registered prediction: at a tile end `e`, RETILE flags exactly what TRUNC-0 flags at a cut at `e` (the same input ends at `e`).
5. **TWO-RUN** (ours, after Fonseca's §8.3 class). At each cut, every value of every bar after `t` (open, high, low, close, volume, quote volume, trades, taker base and quote volumes) is multiplied by an independent factor `exp(σ z)`, `z` standard normal, then each bar is made valid again: high = max of the four prices, low = min, taker volumes capped at their totals, trades rounded to an integer ≥ 1. Primary σ = 0.1; secondary σ = 1.0. Seed `[20261118, cut, run]`. One perturbed run per cut and σ.
6. **SHUFFLE** (the future-shuffle twins of `bench/twins.py` as a detector). K = 8 twins per cut, seed 20261030, as registered for H1's blind spots. Caught if any twin moves an output.
7. **UNION.** Caught by any of 1, 2, 3, 5 (primary σ), 6. RETILE and the secondary σ are reported with and without it.

**Secondary schedule (Fonseca's M1, sampled epochs).** FI, TRUNC-0, TRUNC-1 and TWO-RUN also run on the adversary's long schedule (64 cuts per pair), and the union over both schedules is reported. This keeps the brief's "sampled dates" (committed 2026-11-18) as a secondary analysis; the primary uses H1's cuts so that coverage is held equal. Deviation logged with its date.

## 3. Controls (predicted verdicts, registered; not pooled into any rate)

1. **Past-only honest twins** (`Leak.twin`). They read bars ≤ s only, so no detector of §2 can move them except RETILE with a too-short input window. Any flag is a bench bug: an assertion, not a hypothesis. The share constant at the compared rows is reported.
2. **Cancelled controls, FP1 and FP2 after Fonseca, generated.** For each leak `L` with a value node `v` of a future read (`At` or `Agg` at an offset ≥ 1):
   - **FP1:** `twin(L)` evaluated with `v − v` added to one of its value operands (a future read that cancels);
   - **FP2:** `twin(L)` with `min(x, x + 0 · v)` in place of one value operand `x`.
   - Predicted verdicts: FI, TWO-RUN, SHUFFLE never flag them (finite futures cancel bit for bit, since `v − v = 0` and `0 · v = 0` for finite `v`). TRUNC-0, TRUNC-1 and RETILE flag them wherever the cancelled read is missing at a compared row and the operand is a value (NaN propagates), and not where it feeds a comparison whose other branch is unchanged. Reported: the flags per detector, against the prediction, row by row. A disagreement with the prediction is a finding to explain, not a rate.
3. **Fonseca's classes, hand-written on our bars** (written and committed before any detector runs on them, each with its predicted verdict per detector, as tests): M1 (`close[s+1] > close[s]` gated to rows that avoid the 16 cuts' compared rows), M2 (`close[s+1] > 2 · close[s]`, a threshold the ×3 perturbation flips but σ = 0.1 does not), M3 (a future close re-stamped to row `s`: `close[s+1]` stored as a quantity of bar `s`, read at offset 0), FP1, FP2. FP2b needs declared availability metadata that our bars do not carry: not rebuilt, stated.

## 4. Metrics (fixed now; nothing else is reported as confirmatory)

For each detector on the confirmatory population, with n = 10,000:
1. the share caught, with its Wilson 95 % interval; per family and per `position` stratum (`inside`, `outside`, other);
2. the same share under a **finite-only rule** (sensitivity): a catch needs a move above 1e-9 between two finite outputs; a change of missingness alone does not count. Reported for every detector; it separates catches through a missing bar from catches through a changed value;
3. the share of `designed: no` leaks caught (a second denominator, fixed now beside "all leaks");
4. for every pair of detectors among FI, TRUNC-0, TRUNC-1, TWO-RUN (σ = 0.1), SHUFFLE: the 2×2 table, the discordant counts b and c, the difference of shares with Newcombe's 95 % interval for paired proportions, and the exact two-sided McNemar p-value;
5. for each detector: the number of leaks caught by the union and missed by it, with a Wilson interval;
6. the leaks caught by no detector, classed as in H1's blind spots (constant at the compared rows of the 16 cuts, unchanged under SHUFFLE, other), with both constancy definitions of `misses-findings.md` stated.

No adjusted score and no "best detector" chosen after the run.

## 5. Hypotheses (draft; numbered at registration)

- **D1, truncation against future invariance.** Prior: TRUNC-0 catches at least as many leaks as FI. Test: exact two-sided McNemar on the 16 cuts, p < 0.05; the direction, b, c and the interval are reported either way. With n = 10,000 a p-value will be small for any real difference, so the claim made is the interval of the difference, not the p-value.
- **D2, what truncation's advantage rests on.** Prior: most of TRUNC-0's catches beyond FI are catches through a missing value (continuous leaks turning NaN), so under the finite-only rule TRUNC-0's share falls below FI's. Reported: both shares under both rules and their paired difference.
- **D3, controls.** No past-only twin is flagged by any detector (an assertion). The cancelled controls follow their predicted verdicts.

Dropped from the brief's draft, with the reason: "the union beats the best single detector" (the union contains every detector, and the best is chosen after the run, so the test reduces to a few extra catches; replaced by metric 5); "no detector flags more than 0.1 % of the honest twins" (no perturbation detector can flag a past-only twin; replaced by the assertion and the cancelled controls).

## 6. What the paper may and may not claim from these outputs

- May: the catch rates of these detectors on this generator, with intervals; their overlap; the share of catches that rests on a missing value; the controls' verdicts; that our two-run arm is our definition.
- May not: a rate over "all leaks"; that FI is better or worse than truncation in general; any comparison with Fonseca's 18/33 and 33/33 (another corpus, another language).

## 7. Variants and seeds

No strategy variant: the count of `docs/RESULTS.md` stays at 21. Seeds: population 20261118, development 51118, two-run 20261118 (stream per cut and run), twins 20261030, long schedule as in iteration 3.
