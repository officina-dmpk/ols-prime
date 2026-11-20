# Evaluation protocol

Fixed before any model is trained. Any change gets a dated entry in the change log at the bottom.

## Data

- **Klines.** Spot klines from data.binance.vision, 1 h and 1 d, from August 2017.
  - Checksums are verified.
  - Timestamps are normalized to milliseconds UTC; spot files switched to microseconds on 2025-01-01.
- **Universe.** 20–30 USDT pairs, re-selected each month by trailing 30-day quote volume.
  - Only data available before that month is used.
  - Delisted pairs stay in the history.
  - Stablecoins and leveraged tokens are excluded.
- **Venue.** Binance serves for history only. Live trading targets a MiCA-authorized venue, and costs come from that venue's fee schedule.

## Splits

| Period | Use |
|---|---|
| 2017-08 → 2024-12 | development, walk-forward with monthly refits |
| 2025-01 → 2025-12 | validation and model selection |
| 2026-01 → 2026-10 | vault: opened once, at the end, for all final models together |

- Purge and embargo equal the label horizon h (1 day or 7 days).
- Everything estimated is fitted inside the fold: scalers, PCA, Gram matrices, thresholds, calibration.
- **The vault is sealed in code** (`python/olsprime/protocol.py`).
  - Every read of stored klines goes through `load_klines`, which drops each bar whose values are final at or after 2026-01-01 00:00 UTC. A test fails if any other module reads a Parquet file.
  - The vault opens only with two keys at once: the environment variable `OLSPRIME_OPEN_VAULT=1`, and a file `runs/vault/OPEN` written by hand at the final evaluation. Its first line is the date alone (ISO 8601) and the next lines are the ids of the final models. An empty file, or a first line that is not a date, keeps the vault shut with an error.
  - Each read with the vault open adds a line to `runs/vault/ACCESS.log`.
  - `OPEN` and `ACCESS.log` are the only files under `runs/` that git tracks, so the opening is recorded in the history.
- **The physical seal (iteration 3).** `python -m olsprime.vault` moves the vault months out of `data/` into a vault tree outside the repository (stage 1), then encrypts that tree to an age key held off this machine (stage 2). `docs/DATA.md` gives the stages, the stage reached and their limits. The two keys now also decide whether the vault tree is read at all.
  - **Sealed.** `load_klines` reads `data/` only, and never touches the vault tree.
  - **Both keys, stage 1.** `load_klines` also reads the pair's plaintext file in the vault tree, joins the two on `open_time` (the file in `data/` wins) and sorts.
  - **Both keys, stage 2.** The `.age` file is decrypted in memory with the identity file named by `OLSPRIME_VAULT_IDENTITY`. With no identity, or a wrong one, `VaultSealed` is raised and nothing opens, even with both keys forged.
  - Each part read is logged in `ACCESS.log`, the tree's part tagged `[vault tree]`. `olsprime.vault` refuses to run while the vault is open.

## Leakage tests (mandatory for every model)

- **Future invariance:** perturbing any data after t leaves every decision at or before t unchanged.
  - Every value of every later bar moves: prices, volumes, trades and taker shares. So does every ratio of two values of a bar. The run asserts this coverage. Only the time stamps stay.
  - Both directions run at every cut: the future multiplied by 3, and divided by 3.
  - Bar t + 1 is built, not drawn. In one run, each of the quantities below sits above bars t − 90 to t; in the other, below them:
    - prices, body, wicks and range, except the upper wick at odd cuts, which crosses bar t's only;
    - VWAP and taker VWAP;
    - volumes, trades and trade size;
    - taker shares.

    So a comparison between bar t + 1 and any of those bars flips in exactly one run.
  - Bar t + 1's candle takes opposite shapes in the two runs: small and filled by its body in one, large and dominated by one wick in the other. One run's candle is green and the other's red, and which is which alternates from cut to cut, so all four pairings of colour and size occur. Its fill (body over range) and its close location sit above bar t's in one run and below them in the other.
- **Cheater detection:** the bench must flag a deliberately leaking model, one that reads its own label.
- **Planted leaks:** the bench must also flag each of the following at exactly its predicted cuts:
  - models that compare one quantity of the next bar with the present: trades, quote volume, the two taker shares, range, body, each wick, fill, close location, VWAP, taker VWAP or trade size;
  - models that threshold the next bar's range, body or close location;
  - models that pick out a small red or a large green next bar;
  - models that use the next bar's range or VWAP as their forecast;
  - a model that compares the next close with an older one;
  - a return shifted the wrong way;
  - a scaler fitted on the whole test month, ahead of a ridge that does not rescale;
  - models fitted without the purge.

  A planted leak is caught at a cut only where an output moves by more than 10⁻⁹, turns missing or stops being missing. A change at the level of rounding carries no leak, so it never counts as a catch. An honest model, by contrast, must not differ by a single bit.
- **Positive control:** ridge fitted on labels shifted one bar early must beat climatology with a Brier skill score above 0.5. The pipeline must see a signal when there is one.
- **The limits.**
  - A model that reads the time stamps, such as a calendar learned from the future, passes the perturbation. Code review and the seal stop it, not this test.
  - Comparisons two or more bars ahead flip with high probability only, not by construction. So do comparisons with bars older than t − 90, the shape functions other than the fill, the close location and colour with size, such as the ratio of the two wicks, and their pairings with the colour. So does, at odd cuts, a comparison of bar t + 1's upper wick with a bar older than t.
  - A threshold on bar t + 1 flips by construction only inside the design's bands: a body between 0.4 % and 10 %, a range between 0.5 % and 50 %, a fill between 0.2 and 0.8, a close location between 0.25 and 0.75.
  - A cut where a quantity cannot cross is marked `?`, for example a taker share already at 1, or a bar without volume. The `?` is predicted from the original bars, before perturbing, and only for a declared reason. It is reported and left out of the verdict; it never counts as a pass. A failure to cross without a declared reason fails the test, and so does a control that is `?` at every cut.

**The adversary (iteration 3).** Beside the designed controls, H1 reports how many random leaks it catches.
- A seeded generator plants random leaks: functions of the next bars' levels, ratios and shapes, alone or combined, and compared with the past, with other future bars or with thresholds.
- Each leak runs through H1's own perturbation, at H1's cuts and at a longer schedule of cuts.
- The report gives the share caught with a 95 % Wilson interval, overall, per family and per cut, and the mean per-cut rate. It also gives the size of each catch and the list of misses.
  - The sizes describe the scale of the generator's outputs, not H1's sensitivity. So the report also gives an attenuation curve: the share caught when every leak's output is multiplied by ε ∈ {1, 10⁻², 10⁻⁴, 10⁻⁶, 10⁻⁸, 10⁻¹⁰}. It shows where the 10⁻⁹ rule stops catching weak leaks.
  - It names the families the generator never produces, such as fitted leaks, reads more than 10 bars ahead and leaks that read the time stamps.
- Every leak has an honest twin, the same expression moved into the past. A twin must never be caught: one catch is a bench bug. The report gives the share of twins that are constant at the compared rows, since a constant twin cannot be caught.
- The result is descriptive. It measures this generator's detection rate, not all leaks. H1's registered rule does not change.

## Matrix on hourly bars (iteration 3)

Fixed on 2026-10-29, before any Matrix run. It defines H2, H3 and H10–H12 for the development period.

**Panel.**
- Hourly bars of the universe members (`docs/DATA.md`), read through the seal, which keeps the vault out. 233 of the 274 members have a member month in the development period; the other 41 first join in 2025.
- The bars are cut to `known_at` < 2025-01-01 before any feature or label is computed. The validation year's bars are loaded and dropped there, so none reaches a feature, a label or a model, and a label that needs a 2025 bar is null.
- A row (pair, hour t) exists only in the months when the pair is a member of the universe. Membership is the rebalance at the first day of the month in which bar t opens, ranked on data before that month. A row's month is the month of its bar's open, even when a late close puts its decision time in the next month.
  - Rows from other months are neither entries nor queries.
  - A pair's months before it first joins would carry its later selection, a survivorship leak.
- Features: the 15 `FEATURE_COLUMNS`, computed on each pair's whole hourly history up to t, so their windows count hours.
- Labels: three classes over h = 24 bars (one day). Entry is at the open of t + 1 and exit at the open of t + 25. The threshold is max(0.5·σ̂·√24, 0.0024), with σ̂ = `f_vol_30`. A label is known at its exit bar's open.
- Test months: 2019-01 → 2024-12, as H9. Decisions are hourly.

**Matrix.**
- One pooled memory over all members.
  - An entry is (x, y): x holds the 15 features, y the one-hot class followed by `fwd_return`.
  - It is stamped with `label_known_at`.
  - A row with a null feature or label gives no entry.
- A readout at decision time d over window w uses the entries with d − w < time ≤ d. The windows are 30 days, 365 days and all history.
- Ridge in centred form, with a free intercept. Feature j gets the penalty ρ·n_w·σⱼ², where n_w is the window's entry count and σⱼ² the variance of feature j over the entries the fold's fit may use (see Folds). ρ ∈ {10⁻⁴, 10⁻³, 10⁻², 10⁻¹, 1, 10}. This is ridge on features standardized inside the fold, solved exactly from the statistics.
- Probabilities, for every arm: pₖ = max(ŷₖ, 10⁻³) / Σⱼ max(ŷⱼ, 10⁻³).
- A readout the solver refuses (an empty or singular window) falls back to the arm's climatology for that row. The count is reported.

**Folds.**
- Monthly refits, at 00:00 UTC on the first day of each test month.
- **σ.** The σⱼ² of a month M is the variance of feature j over the entries known by M's first instant minus 24 h. Every readout of a row of month M uses the σ of M, in the test months and in the months before them alike.
- **The prequential record.** Every candidate of every arm (each window with each ρ, each τ, each k) forecasts every row, at the row's own decision time and with the σ of the row's month. The record starts at the first month that has a σ, 2017-11. Rows decided before 2019-01 are never scored: they only build the record.
- **The selection rows** of a fit are the rows decided in the 365 days before it whose labels are known by the fit time minus 24 h (purge and embargo of h).
- A choice fitted at the fit time (σ, a window, ρ, stacking weights, a kernel width or k) uses only rows whose label is known by the fit time minus 24 h, and those rows' forecasts in the record. Every selection minimizes the mean log-loss of the record over the selection rows.
- **Defaults.** A selection, at a fit or at a decision of `matrix-adaptive`, that finds fewer than 1,000 rows to read takes a fixed default instead: the 365-day window, ρ = 10⁻², τ = √15, k = 200, and all of α on the 365-day window. The count of defaults is reported per arm.
- Matrix itself takes every entry once it is known, inside the test month too.

**Arms.** Each of the eight arms is one variant of the deflated Sharpe ratio, `climatology-panel` included: 8 variants, 18 in all with the 10 baselines of Report n°1. The grids inside an arm are fitted inside the fold, so they are not variants.

| Arm | Hypothesis | Definition |
|---|---|---|
| `climatology-panel` | reference | Class frequencies of the rows known at the fit. |
| `matrix-select` | H2, and the reference of H10–H12 | At each fit, the window and ρ with the lowest mean prequential log-loss over the selection rows. |
| `matrix-1y` | H3 | Window 365 days; ρ selected at each fit the same way. |
| `softmax-1y` | H3 | Nadaraya-Watson on the entries of the 365-day window, weights ∝ exp(−‖u_q − uᵢ‖²/(2τ²)), where u holds the 15 features divided by their fold σ, and τ ∈ {0.5, 1, 2}·√15 is selected at each fit. |
| `knn-1y` | H3 | The mean one-hot label of the k nearest entries of the 365-day window (Euclidean on u), ties broken by entry order, k ∈ {50, 200, 1000} selected at each fit. |
| `matrix-adaptive` | H10 | `matrix-select`'s window. At each decision time d, the ρ with the lowest mean prequential log-loss over the rows whose labels are known by d and whose decisions fall after d − 30 days. |
| `matrix-stack` | H11 | p = Σ_w α_w p_w over the three windows, each at its own selected ρ. α lies on the simplex, fitted at each fit on the prequential log-loss of the selection rows, on a grid of step 0.05. |
| `matrix-cusum` | H12 | `matrix-select`, refitted at the first fit and then only after a CUSUM alarm, instead of every month (detailed below). |

The CUSUM of `matrix-cusum`:
- **Input.** One value per day d, from the decisions of the bars that open at 00:00 UTC on d (decision time 00:59:59.999), so the daily labels do not overlap.
  - Each decision's recursive residual of the `fwd_return` readout, its realized `fwd_return` minus the forecast made at the decision time, is divided by its predictive standard deviation, σ̂·√(1 + 1/n_w + x̃ᵀ(M_xx + Λ)⁻¹x̃). Here x̃ is the query's features minus the window's means, M_xx the window's centred cross-products, and σ̂² the window's residual mean square at the decision time.
  - The day's raw value is the mean of these over members. It is divided by s, the standard deviation of the raw daily values over the days of the last fit's selection rows, recomputed with that fit's window, ρ and σ, as the fit reads its live days. The members' residuals move together, so the raw mean does not have unit variance: s gives back the unit variance that the threshold assumes.
- **Timing.** Day d's value is known with its labels, at the exit open, 01:00 UTC on d + 1, and it enters the CUSUM then. An alarm acts at the first 00:00 UTC after that instant. The arm refits there, on rows whose labels are known by the fit time minus 24 h, and the CUSUM restarts at 0.
  - A day's value is computed entirely with the fit in force at its decision time: its readouts, σ̂, leverage and s. The restarted CUSUM takes only the days decided after the refit, so the day decided just before it is left out.
- **Threshold.** A two-sided Page CUSUM with k = 0.5. Its threshold is set by simulation, before any result, to give an average run length of 365 days under independent N(0, 1) values. That is about 6 false alarms over the 2,191 test days, against 72 monthly fits.

If the exact kernel readouts cannot run over the 365-day window within the iteration, H3 runs at the 30-day window for all three of its arms. This fallback is fixed here, before any result.

**Scoring.**
- Scored rows are the test rows with a label and complete features. They are the same for every arm. The report gives the share of the test months' hours that are scored, and why the others are not.
- Each score is averaged over the scored rows of each decision hour. Every statistic is computed on these hourly series, so the dependence across pairs stays inside the hour. A reported mean is a mean over hours.
- Metrics: log-loss, Brier, Brier skill score against `climatology-panel`, expected calibration error.
- Diebold-Mariano runs on the hourly loss differences, two-sided, with the rectangular kernel, h − 1 = 23 lags and the Harvey-Leybourne-Newbold correction.
- Intervals: stationary block bootstrap of the hourly series, block length by Politis-White, 2,000 resamples, 95 % percentile.
  - For the Brier skill score, the arm's and climatology's hourly Brier series are resampled with the same blocks. Each resample gives 1 − mean(b_arm*)/mean(b_clim*), and the Politis-White length is computed on the hourly difference b_arm − b_clim.
- A comparison of two arms has a second test: the same bootstrap of the mean hourly log-loss difference, with the Politis-White length of that difference. Diebold-Mariano with 23 lags covers the overlap of the labels exactly, but not a dependence that lasts longer, such as a skill that changes with the regime.
- Each difference is also reported as a share of climatology's log-loss, beside its p-value.
- Each comparison also gives the share of hours at which the two arms' hourly log-losses are identical, because both read the same cells at every scored row, and the count of the other hours, the informative ones. Above one half, the report says that the tests rest on few informative hours. This is a description and changes no verdict.
- The test months that smoke runs scored before the official run, 2019-01 → 2020-06, are also reported apart from the other 54. The Brier skill score of `matrix-select` and every comparison are computed on each part alone, with the same statistics and each part's own climatology. It is a description: the verdicts rest on the whole period, and a part's comparison says whether the rule is met, never that it passes. A part in which two arms agree at every hour has no test, and the report says so.

**Decision rules.** A comparison passes when the Diebold-Mariano test gives p < 0.05 and the bootstrap's 95 % interval of the difference lies on the same side of 0.
- **H2** holds if the Brier skill score of `matrix-select` is above 0 and its 95 % interval lies above 0.
- **H3** holds if `matrix-1y` has a lower log-loss than `softmax-1y` and than `knn-1y`, each comparison passing. Each comparison is reported.
- **H10** holds if `matrix-adaptive` has a lower log-loss than `matrix-select`, the comparison passing.
- **H11** holds if `matrix-stack` has a lower log-loss than `matrix-select`, the comparison passing.
- **H12** holds if two conditions both hold:
  - the 95 % one-sided upper bound of the mean log-loss of `matrix-cusum` minus that of `matrix-select` is below 0.005 times climatology's log-loss. The bound is the mean difference plus the 95 % quantile of Student's t with T − 1 degrees of freedom, times the Diebold-Mariano standard error above (HLN-corrected), where T is the number of hours. The bootstrap's 95th percentile of the mean difference must be below the margin too;
  - `matrix-cusum` makes at most 36 fits, the first included: half the 72 of the monthly schedule.

**Future invariance on the panel.** Before any result, every arm passes H1 on a sub-panel.
- The sub-panel: the 10 members with the most member months in the development period.
- The cuts: 8 cut hours, drawn with a fixed seed in the test months, one of them at a month's first hour and one at its last.
- Every bar of every member after the cut is perturbed in both directions, as in H1. Every output at or before the cut is compared bit for bit, with every fit-time choice behind it. The fit of the cut's month is compared when a row of that month is decided by the cut; without one, nothing of that month is compared.
- A member with no bar after a cut, or none at or before it (not yet listed), is left out of that cut, and the count is reported.
- Planted online leaks must each be caught where predicted:
  - entries stamped with their decision time instead of `label_known_at`;
  - a window that ends one hour after the decision;
  - σ fitted on the whole test month, predicted at 7 of the 8 cuts: at a month's last hour, every feature of the month is already known;
  - a fit-time selection on rows whose labels are not yet known (no purge);
  - a kernel readout whose candidates reach one label horizon past the decision.
- A limit: only the sub-panel's bars are perturbed. An input built from other members' bars would not move. No arm has such an input.
- A second limit: a member not yet listed at a cut stays unperturbed, since all its bars lie after the cut. An arm that read such a member's future bars would not be caught at the cuts before its listing.

**The readout, described.** For a seeded sample of 1,000 test decisions of `matrix-1y`, the report gives the share of negative weights. It also gives the signed contribution of the last 30 days, and that of the older entries.

**Out of scope here.** Trading metrics of the Matrix arms wait for a portfolio simulator. Each arm still counts as a variant.

## The encoder, and what a verdict is worth (iteration 4)

Registered on 2026-10-29, before any run of iteration 4, and audited before any run (see the change log). It defines the encoder arms of H4, H5 and H13, the size and power study of the pass rule, `olsprime.explain`, H1's blind spots, and H14, which is registered now and runs in iteration 5. Every choice below is the same for every arm, and nothing is tuned per arm.

**Priority order**, fixed before any result. A hypothesis that was not run is reported as not run.
1. These pre-registrations, and an audit pass on them before any run.
2. Report n°2's series, then the size and power study.
3. `olsprime.explain`: `why` and `head`.
4. The encoder: H4's three arms and H5, with the cost table and H13. LFM3's two ablations, then H6, run only if time remains, in that order.
5. H1's blind spots: the future-shuffle twins only.
6. Deferred to iteration 5, registered now: the portfolio simulator (H14) and H1's extreme-shape cut.

### The encoder arms

**Panel and scoring.** The panel, test months, scored rows, hourly series, statistics and decision rule of "Matrix on hourly bars (iteration 3)". Every encoder arm forecasts every scored row of Report n°2, so its hourly series pairs with Report n°2's hour by hour.

**Inputs: a window of bars.** Row (s, t) reads the 64 hourly bars of pair s that end with bar t. They are all final at its decision time, so attention inside the window may be bidirectional.
- Each bar j gives eight quantities:
  - `ret` = ln(c_j / c_{j−1}) and `gap` = ln(o_j / c_{j−1});
  - `range` = ln(h_j / l_j) and `body` = ln(c_j / o_j);
  - `upper` = ln(h_j / max(o_j, c_j)) and `lower` = ln(min(o_j, c_j) / l_j);
  - ln(1 + quote volume);
  - the taker share of the quote volume minus 1/2, which is 0 for a bar without volume.
- Each quantity is standardized with its mean and standard deviation over the last bar of every training row of the fit, then clipped to ±8. These statistics are fitted at the fit (see Fits).
- The window's 65 bars, from t − 64 for the first return, must be consecutive hours. A complete row always has them, since its 90-bar features require 90 gaps of one hour. A scored row whose window fails takes the arm's climatology, and the report counts it.

**Encoder**, shared by the three arms, which differ only in the attention operator:
- a linear map of the eight quantities to d_model = 32, plus a learned embedding of the 64 positions;
- 2 pre-LayerNorm blocks:
  - attention, with 4 heads of d_head = 8;
  - an MLP 32 → 64 → 32 with GELU;
  - a residual connection around each, and no dropout;
- a final LayerNorm. The state h is the output at bar t, the last position.

**The attention operators.** In every arm, Q, K and V are a head's 64 × 8 projections, made by the same weights.
- `enc-ols`, the OLS head of `docs/DESIGN.md` §4:
  - Queries and keys are scaled to unit root mean square at each position, with no parameter.
  - K̃ = [1 | K] and q̃ = [1 | q]: an unpenalized constant key coordinate, and a 1 in every query.
  - Λ = diag(0, 64λ, …, 64λ), with λ = softplus(θ) + 10⁻³ learned per head and θ initialised so that λ = 0.1.
  - W = Q̃ (K̃ᵀK̃ + Λ)⁻¹ K̃ᵀ and O = W V. It is solved by a Cholesky factorization in fp32, never by an explicit inverse.
  - Every row of W then sums to 1 (`docs/DESIGN.md` §1), so a row sum that is not 1 within rounding is a bug, and `head` checks it.
  - T / d_head = 8.
- `enc-softmax`: PyTorch's native scaled dot-product attention, softmax(Q Kᵀ / √8) V.
- `enc-linear`: φ(Q) (φ(K)ᵀ V) / (φ(Q) φ(K)ᵀ 1), with φ(x) = elu(x) + 1 (Katharopoulos et al., 2020).

**Parameters.** `enc-softmax` and `enc-linear` have the same count, N. `enc-ols` has N + 8: one λ per head, 2 layers × 4 heads. The constant key coordinate is a fixed input, not a parameter. The difference is under 0.1 %, inside the 1 % allowed, and the report gives the exact counts.

**Memory: Matrix over learned keys.** Every arm reads a Matrix whose keys it learns.
- Each row's key is z = W_z h ∈ R⁸ and its value is its one-hot label. The entry is stamped with the row's `label_known_at`.
- A readout at decision time d uses the entries with d − 30 days < `label_known_at` ≤ d.
- It is the centred ridge with a free intercept of `docs/DESIGN.md` §3.2, m = ȳ + β (z − z̄), with Λ = ρ·diag(M_zz) + 10⁻⁶·n_w·I and ρ = 10⁻². This is ridge on keys standardized inside the window. An empty window gives (1/3, 1/3, 1/3).
- The statistics accumulate in fp64 and the 8 × 8 solve is in fp64. Prefix sums of raw moments are differenced in fp64 before centring, never in fp32.

**Decision head.** [h, m] → 32 → GELU → 3 → softmax. The arm's probabilities then pass through the protocol's floor, pₖ = max(pₖ, 10⁻³) / Σⱼ max(pⱼ, 10⁻³).
- The loss is cross-entropy on the softmax output, before the floor. The floor applies to the scored probabilities only.
- The Brier term is H6's ablation, not part of the core arms.

**Training in episodes.** A step is one episode: the training rows decided in one calendar week, Monday 00:00 UTC to the next, over every member.
- **The memory's causality.** Inside an episode, the memory used for a query at decision time d holds exactly the entries with d − 30 days < `label_known_at` ≤ d.
  - The statistics at d are prefix sums over the entries ordered by `label_known_at`, so an outcome joins the memory only once it is known, inside the episode too.
  - The rows decided in the episode are keyed with gradient.
  - The older entries the window needs are keyed with the current weights, without gradient: a cache.
- **Its test.** On a synthetic episode, at every decision time d, the memory must hold the same entries as `Matrix.window_range(d, 30 days)` of the Rust core, and give its readout within rounding.

**Fits.** One fit per test year, at 00:00 UTC on 1 January, 2019 to 2024: 6 fits. A fit at F:
- **trains** on the complete rows whose labels are known by F − 30 days;
- **stops early** on a slice: the complete rows decided in [F − 30 days, F) whose labels are known by F − 24 h. The slice is never trained on, and every training label is known before its first decision, so it is purged;
- **fits** the inputs' standardization on the training rows, and takes its climatology from the labelled rows known by F − 24 h, as `climatology-panel` does;
- **runs** at most 6 epochs. An epoch takes every week of training rows once, in an order drawn from the seed. After each epoch, the slice's mean log-loss is computed in evaluation mode, with the memory as at test time. The fit keeps the epoch with the lowest slice loss, the first on ties;
- **optimizes** with AdamW:
  - learning rate 10⁻³ and betas (0.9, 0.999);
  - weight decay 0.01 on the weights of the linear maps only: the input map, the Q, K, V and output projections, the MLP, W_z and the decision head. Biases, LayerNorm parameters, the position embedding and θ have none;
  - linear warm-up over the first 100 steps, then cosine decay to 10⁻⁴ at the end of epoch 6;
  - the gradient norm clipped at 1;
- **forecasts** every scored row of its year. A row's year is that of its month, the month of its bar's open, as in iteration 3. Its memory takes every entry once its label is known, test rows included, keyed by the frozen encoder.

**Seeds.** Each arm has 3 seeds (1, 2, 3); a seed sets the initialisation and the order of the episodes.
- The arm's forecast is the mean of its seeds' probabilities before the floor, then floored. That mean is the model.
- Each seed's log-loss and their spread are reported as a description.

**Determinism.**
- The settings: `torch.use_deterministic_algorithms(True)`, `CUBLAS_WORKSPACE_CONFIG=:4096:8`, TF32 off, cuDNN benchmark off and fixed seeds.
- The machine: one named GPU, the RTX 3060 in WSL2, and one build, whose driver, CUDA and torch versions are recorded.
- Colab runs only if the sizing below rules the 3060 out for the whole schedule. Its runs are named apart, and never enter a 3060 column.

**Batches.** Every batched computation outside a training step runs in fixed-size batches of 4,096 rows taken in panel order, by decision time and then symbol. That covers the encoder's forward pass for queries, entry keys and the cache, the slice evaluation and the forecasts.
- The last batch is padded to 4,096 rows with copies of its last row.
- So a row's outputs do not depend on which other rows are in the run. This matters because BLAS and cuBLAS choose their kernels by problem size, and the same row of a product can differ in its last bits between two sizes (audit pass 4a).
- Training steps keep their weekly episodes, which are the same in every run of a fit.

**Sizing, before the schedule.** One fit of an encoder arm on the largest training set (the 2024 fit), measured on a synthetic panel of the real panel's shape before any run on real data. The numbers and the schedule they allow are in `docs/ITERATIONS.md`, iteration 4's brief.

**Smoke runs on the real panel**, if any, train on rows decided before 2019 and forecast no test month. Any run that scores a test month before the official runs is listed in the change log, and its months are shown apart, as in iteration 3.

**Frozen.** Every choice of this section is fixed before the first encoder run on real data. It is committed before the first `explain` call on any hour of 2019–2024.
- After that first call, this section changes only for what cannot be built as written.
- Each such change-log entry cites the line count of `runs/explain/CONTACTS.log` at that moment.

### H4, H5 and H13

- **H4** holds if `enc-ols` is non-inferior to `enc-softmax` over the test months 2019-01 → 2024-12.
  - **The margin** is 0.005 × the mean hourly log-loss of Report n°2's `climatology-panel` over the scored hours.
  - **Two bounds** of mean(ll_ols − ll_softmax) must both lie below the margin:
    - its one-sided 95 % upper bound: the mean plus t₀.₉₅(T − 1) times the HLN-corrected Diebold-Mariano standard error, as for H12;
    - the stationary bootstrap's 95th percentile of the same mean.
  - **Testable only if an arm learned something.** `enc-ols` or `enc-softmax` must have a Brier skill score against `climatology-panel` whose 95 % interval lies above 0 over the test months. Two arms that both sit at climatology would meet the bounds vacuously, so without that skill H4, and with it H13, are reported as not testable, not as holding (audit pass 4a).

  `enc-linear` is a reference arm. Its comparisons with `enc-ols` and `enc-softmax` are described.
- **H5** holds if `enc-ols` has a lower log-loss than `matrix-select`, the comparison passing: Diebold-Mariano p < 0.05, and the bootstrap interval below 0.
  - `matrix-select`'s series is read from Report n°2's `series.npz`, by its digest, on the same scored hours.
  - **A limit.** The encoder refits yearly and `matrix-select` monthly, so H5 compares two systems, not two attentions at equal cadence.
- **H13** holds if H4 holds **and** the median wall time per 10⁴ decisions of `enc-ols`, over 10 repeats, is at most 0.9 × `enc-softmax`'s.
  - A decision is the whole forward pass: encoder, memory readout and head, with the memory's statistics already built.
  - The conditions: T = 64, d_head = 8, 4 heads, 2 layers, inference batches of 4,096 rows, the RTX 3060 in WSL2, and the driver, CUDA and torch versions recorded.
  - Both arms run in plain fp32 eager mode with no fused attention kernel. The softmax goes through the math backend of scaled dot-product attention. The deterministic settings are on, as in the runs.
  - **The timed rows.** A sample of 12,288 scored rows (3 batches of 4,096), drawn with the seed 20261030. The time is scaled to 10⁴ decisions.
  - **The protocol of a repeat.** 3 untimed warm-up batches, then the 3 timed batches, with `torch.cuda.synchronize()` before and after each.
  - **The repeats** alternate the arms, ABAB, against drift of the clock and the temperature.
  - **Reported:** the median ratio, the 10 repeats' minimum, median and maximum for each arm, and, as a description, the attention operator's own time beside the whole pass.
  - Analytic FLOPs favour OLS by construction when T ≫ d_head, so they stay descriptive.
- **The cost table** is descriptive. It covers every arm of H4 and H5 and the eight Matrix arms, with five columns:
  - parameters;
  - analytic FLOPs per decision;
  - wall time per 10⁴ decisions;
  - peak memory: `torch.cuda.max_memory_allocated` on GPU, the process's peak on CPU;
  - GPU-hours of training, with the GPU named.

  Each column holds one machine and one build: GPU timings on the 3060 in WSL2, Matrix's CPU timings on the Ryzen 5 3600 with the portable build. A Colab T4 or A100 is never mixed into a 3060 column.

### H1 for the encoder arms

**On GPU.** Each encoder arm runs the panel H1 of iteration 3 with its first seed: the same sub-panel, the same 8 cuts, both directions, plus the purge cut below.
- **The runs.**
  - The honest run trains, on the sub-panel, the fit of each cut's fit year, 2021 for the purge cuts. It forecasts every scored row of that year.
  - Each perturbed run rebuilds the sub-panel and its windows from the perturbed bars, retrains the fit of the cut's year on them, and forecasts up to the cut.
- **What is compared, at or before the cut:**
  - the fit's inputs: training and slice rows, standardization, climatology and the order of the episodes;
  - every trained parameter, each epoch's slice loss and the epoch kept;
  - the memory's stamps and statistics at each compared decision;
  - every output.
- **Pre-check, before H1.**
  - Two honest runs with identical inputs.
  - A scope test: the honest run restricted to the rows decided at or before the first cut must give the full honest run's outputs on those rows.
  - If both agree to the bit on everything above, H1 is bit for bit, as for the Matrix arms.
- **Fallback, registered now in case they do not** (rewritten after audit pass 4a).
  - The registered H1 for the encoder arms then runs on CPU torch with the same settings, where it must be bit for bit.
  - The GPU run is reported beside it as a description:
    - everything computed outside the training loop must still match to the bit: the inputs, the standardization, the climatology, the training, slice and selection rows, the order of the episodes, and the memory's stamps and membership;
    - the floor is the largest pairwise difference over three honest runs, quantity by quantity;
    - each control's smallest catch is given as a multiple of the floor, and a catch under 100 × the floor is called weakly separated.
  - A failed pre-check on the GPU is the first finding to report, before any H4 number.
  - This rule is fixed now, never after a violation.
- **The budget.** If the sizing projects this H1 beyond 12 hours, the planted controls run only at cuts 1, 3 and 8, in time order, and at the purge cuts. The honest arms run at every cut.
  - Under the CPU fallback, the honest arms' retrains alone may exceed the budget. Then the honest arms retrain only at cuts 1, 3 and 8 and at the purge cuts.
  - At the other cuts, they forecast up to the cut with the honest fit's parameters loaded, without retraining. The comparison there covers the memory and the outputs only, and the report says so.
- **Limits.**
  - H1 tests seed 1's pipeline, while the model is the ensemble of three seeds.
  - The honest runs' forecasts are a first look at the encoder's skill on the sub-panel's cut years. That contact is listed in the change log when it happens, and Report n°3 says so.

**The purge cuts.** Two more cuts, whose perturbed bars come before the 2021 fit, at F = 2021-01-01T00:00 UTC. They are the only cuts that can see a fit read labels too early.
- At each, the perturbed run rebuilds the sub-panel from the perturbed bars and retrains the 2021 fit.
- No output is compared, since every one is decided after F.
- **At F − 24 h, 2020-12-31T00:00 UTC.**
  - Compared: the 2021 fit's inputs, every trained parameter, each epoch's slice loss and the epoch kept.
  - Every input of an honest fit is known by F − 24 h, so every honest arm is predicted invariant.
  - So are `cheat-stamp` and `cheat-value`: in that fit, their leaks read only labels known by F − 30 days in training, and by F − 24 h in the slice.
- **At F − 30 days, 2020-12-02T00:00 UTC** (audit pass 4b's bolder check).
  - Compared: the training rows, the standardization, the order of the episodes, and the trained parameters after every epoch.
  - Not compared: the slice's labels and losses, the epoch kept and the climatology. They legitimately read labels known after F − 30 days.
  - Every training input of an honest fit is known by F − 30 days, so every honest arm, `cheat-stamp` and `cheat-value` are predicted invariant there.
- Together the two cuts bracket the purge window on real data. The planted-label test of `test_train.py` brackets it on synthetic data.

**Planted training-time leaks.** These are controls, not variants. Each runs with its first seed.
- **`cheat-stamp`, the panel H1's sixth online leak.** `enc-ols` with its memory prefix-summed by decision time: an entry joins at its row's decision time, before its label is known, in training and at test time.
- **`cheat-value`.** `enc-ols` whose last position, in every attention head, adds a learned projection of the row's own one-hot label to its value.
- **`cheat-purge`** (after audit pass 4a). `enc-ols` whose 2021 fit trains on the rows whose labels are known by F, with no purge.
  - It runs at the two purge cuts only.
  - It is predicted caught at both, in both directions: some of its training rows have exit bars that open after each cut.
- **`cheat-slice`** (after audit pass 4b). `enc-ols` whose 2021 fit trains on the rows whose labels are known by F − 24 h, its own slice included.
  - It runs at the two purge cuts only.
  - It is predicted caught at F − 30 days, in both directions, and invariant at F − 24 h.
- **`cheat-stamp-day`** (added on 2026-10-30, before any run on real data; see the change log). `enc-ols` whose memory holds only the last 24 hours by decision time, (d − 24 h, d], with every entry stamped at its decision time, in training and at test time.
  - Every entry it reads has a label not yet known at d.
  - It runs where `cheat-stamp` runs, with the same predicted-pattern rule and the same skill check.
  - It shows whether H1 catches a stamp leak that gives skill.
- **Predicted patterns.** They are computed per cut, as iteration 3's are. `cheat-stamp` and `cheat-value` are predicted caught at a cut when some compared row has a label whose exit bar opens after the cut. At the eight cuts this is expected to give `XXXXXXXX` for both; the computed prediction is the one tested.
- **Their skill.** `cheat-stamp` and `cheat-value` must also show a Brier skill score far above every honest arm's: at least 0.1, with a 95 % interval above every honest arm's interval. So must `cheat-stamp-day`. It is measured on the scored rows of the sub-panel in the cuts' years, which H1's honest run forecasts for every arm.
- **Three verdicts, reported apart** (made precise on 2026-10-30, before any run on real data).
  - H1, as `docs/HYPOTHESES.md` defines it: every honest arm bit for bit at every cut, and every control caught on its predicted pattern.
  - The skill check, control by control.
  - `pos-window`'s check, below.

  Each is reported as passing or failing, and none stands in for another.
- **The first finding.** If H1 cannot catch `cheat-stamp` bit for bit, on the GPU or under the fallback, that is the first finding to report, before any H4 number.

**The positive control, `pos-window`** (audit pass 4a's bolder check). `enc-ols`, seed 1, trained and scored on a label that lies inside its own window: the class of ln(c_t / c_{t−24}), under the panel's label rule with the row's own threshold.
- It runs the honest fits of the cut years on the sub-panel, and is scored on the same rows as the cheaters' skill, against the climatology of its own label.
- Its entries keep the panel's stamp, `label_known_at`, the open of the exit bar, although its own label is known earlier. Stamped at its decision time, a row would sit in its own memory, as in `cheat-stamp`, and inflate the skill.
- It must reach a Brier skill score of at least 0.5. That shows that the training loop learns a signal that is there.
- If it fails, that is reported before any H4 or H5 number.
- It is a control, not a variant.

### LFM3's ablations and H6, if time remains

Each is `enc-ols` with one change, three seeds and the same schedule. Each counts as a variant.
- **`enc-ols-gate`.** A sigmoid gate per OLS head, after LFM3: O ← σ(x W_g) ⊙ O, where W_g maps the block's normalized input to the head's 8 outputs.
- **`enc-ols-conv`.** A conv-first hybrid: the first block's attention is replaced by a gated short convolution, a depthwise causal convolution of width 3 over the window gated by a sigmoid. The second block keeps its OLS attention.
- **`enc-ols-brier`, H6.** The loss is cross-entropy plus the Brier score, with weight 1. H6 holds if both conditions hold (made precise after audit pass 4a):
  - its ECE is at most 0.8 × `enc-ols`'s, and the paired stationary bootstrap's 95 % upper bound of the ratio of the two ECEs is below 1;
  - its log-loss exceeds `enc-ols`'s by no more than a tolerance: the larger of two numbers, the range (max − min) of `enc-ols`'s three per-seed log-losses and the HLN-corrected Diebold-Mariano standard error of the difference.

  The LFM3 arms are described against `enc-ols`, with no registered rule.

### Size and power of the pass rule

The pass rule does not change. This study describes what a verdict under it is worth.
- **Its input.** It reads `series.npz` of a named run of Report n°2, by its SHA-256, and refits nothing.
- **Size.** For each registered comparison, take the hourly difference d.
  - Centre it, d − d̄. Then sign-flip it in circular blocks of L hours, for L ∈ {24, 48, 168, 720}, with 2,000 replicates per L. A replicate rotates the hours by a random offset in [0, L), cuts them into consecutive blocks of L, and multiplies each block by an independent random sign.
  - A block flip keeps the lag-k autocovariance with weight (L − k)/L. So L = 24 keeps only about two thirds of the long-run variance of the 24-hour overlap, and cannot show an over-rejection caused by the overlap itself. L = 48 was added for that, after audit pass 4a.
  - The pass rule runs on each replicate as registered. The Politis-White block length is recomputed on that replicate. Only the bootstrap's RNG seed is fixed across replicates: it is the registered seed of the comparison. The study's intervals are therefore conditional on that seed.
  - The study reports, per comparison and per L, with 95 % Wilson intervals, the rejection rate of each of these:
    - Diebold-Mariano alone;
    - the bootstrap alone;
    - both on the same side, the pass rule;
    - the pass rule in its registered direction.
  - For H12's non-inferiority rule, the size is the rate at which it holds when the true difference sits on the margin: (d − d̄) + m.
  - Any L under which the pass rule's two-sided size exceeds 7.5 % is named.
- **Power, model-free.**
  - The replicates are flip(d − d̄) + δ, with δ in the registered direction. The grid of δ is {0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0} % of climatology's log-loss, with 1,000 replicates per point.
  - The study reports power(δ) and the smallest δ on the grid with power at least 80 %.
  - A constant shift is the easiest gain to see, so that detectable δ is a lower bound of the detectable mean gain. A gain concentrated in regimes needs more.
  - So a second grid, at L = 168 only, concentrates the shift. The series is cut into 720-hour blocks, rotated by a random offset. Exactly round(0.1 × the number of blocks) of them, drawn without replacement, get a shift scaled so that the mean shift over the series is δ, about 10 δ; the others get nothing. It reports the same power curve beside the constant one.
  - H3's `matrix-1y` − `knn-1y`, −0.094 %, is then read against those detectable sizes.
- **Seed.** The flips use one registered seed, 20261030.

### `olsprime.explain`

An instrument for the orchestrator, read by Claude.
- **Output.** Compact, bounded and reproducible: JSON lines and a short text summary.
  - JSON is written with sorted keys and no wall clock.
  - Every answer carries its provenance: commit, manifest digest and panel fingerprint.
- **The log of contacts.** Every call appends one line to the git-tracked `runs/explain/CONTACTS.log`: UTC time, subcommand, period touched, arm and commit.
- **The default period** is 2017-11 → 2018-12, the only development hours that are not test hours. Any other period must be named in the call, with an explicit flag, or the call is refused.
  - `series` and `sample` read `series.npz`, which holds test rows only, so they touch test months by construction. They are logged like any call.
- **Its reach.** It reads the development panel only, 2017-10 → 2024-12. The validation year and the vault are out of its reach.
- **Exploratory, never tested.** A pattern seen through `explain` on 2019–2024 hours is exploratory. It is never tested as a hypothesis on those months: it waits for the validation year's scheduled opening, or for the vault.
- **`why <pair> <as_of> --arm --by {year,month,day} --top k`** gives:
  - the forecast, the intercept and the cell's status;
  - the contributions of the memory's tree nodes at that granularity, sorted by |c|, with the rest summed so that the parts add up exactly. The grouping is by entry stamp (`label_known_at`), not by decision time, and the output says so;
  - the per-feature view βⱼ·z̃ⱼ. It sums to the forecast within rounding. Summed in the core's order, it can give the forecast to the bit: the output says which, as a fact checked at that call;
  - the top-k entries by |w|, with their labels and feature deltas;
  - diagnostics: Σ|w|, the negative mass, the effective sample size 1/Σw² and the leverage.
- **`why`'s two loud checks.** A failure stops the call.
  - Each weighted entry's `label_known_at` is recomputed from its panel row, and from the raw bar's `open_time` for the top-k, and must be at or before `as_of`. Matrix's own stamps are never trusted for this.
  - The forecast must equal the arm's probability in `series.npz` to the bit. A row that is not scored, such as every row of the default period, has no such check. The output then says so, and only the first check applies.
- **`series <arm> [<arm_b>] --period --by {year,month} --top k`** reads only a run's `series.npz`, by its digest. It shows how one of two things is spread over hours:
  - an arm's Brier skill against climatology;
  - or the log-loss difference of two arms.

  It gives the share carried by the top 1 %, 5 % and 10 % of hours, the parts by year or month, and the k hours that carry the most.
- **`sample <arm> --period --n --seed`** runs `why`'s diagnostics on a random sample of n scored rows of the period, drawn by the seed alone, without the per-entry lists. For each row it gives:
  - the negative mass, the effective sample size, the leverage and Σ|w|;
  - the per-feature parts;
  - the row's log-loss.
- **`head`**, once the encoder exists, gives per OLS head:
  - the row of W;
  - its diagonal mass, which shows a head that copies its input;
  - its effective rank;
  - its row sum, 1 by construction.

### H1's blind spots

- **The twins.** Each random leak of the adversary gets K = 8 seeded future-shuffle twins at each cut. In a twin, each of the pair's bars after the cut keeps its time stamps. It takes every other value of a bar drawn, with replacement, from the same pair's bars at or before the cut: open, high, low, close, volume, quote volume, trades, and the taker base and quote volumes. The draws use one registered seed, 20261030.
- **Moved by a twin.** A twin moves a leak when, at a compared row, one of its outputs differs by more than 10⁻⁹, or turns missing, or stops being missing. That is H1's own catch rule.
- **The misses.** A leak caught at no cut is classed as one of three kinds:
  - constant at the compared rows;
  - unchanged under all K twins at every cut: on these bars it does not depend on the future;
  - a true blind spot: some twin moves it, yet H1 did not catch it.
- **Descriptive.** The result measures this generator's misses; H1's rule does not change.
- **Deferred to iteration 5:** the extreme-shape cut. It will be a separate cut type, with its own predicted pattern for every existing control.

### H14, registered now, run in iteration 5

- **The claim.** At Coinbase's and Kraken's entry-tier taker fees plus 2 bps of slippage, the long/flat portfolio of `matrix-select` beats always-flat, and not only through the market's drift. Both conditions must hold, at each venue (the second added after audit pass 4a):
  - **Above flat.** Its net annualized Sharpe ratio has a 95 % stationary-bootstrap interval above 0. Always-flat earns 0 every hour, and cash earns nothing, so beating it means a Sharpe ratio above 0.
  - **Above random positions.** A portfolio long most of the time would inherit the market's drift: buy and hold had a Sharpe ratio interval above 0 in Report n°1. So a second interval must also lie above 0, against 100 random long/flat portfolios (made precise after audit pass 4b):
    - For each member, a random portfolio is a two-state chain on the hourly grid. Its entry and exit probabilities are set so that its expected share of hours long and its expected number of entries per hour equal those of `matrix-select`'s portfolio for that member over the test months.
    - Its positions are sized and costed by the same rule.
    - The 100 portfolios use the seeds 0 … 99, derived from 20261030.
    - The paired 95 % stationary-bootstrap interval resamples hours jointly across the portfolio's and the 100 random portfolios' net hourly returns. Each resample gives Sharpe(portfolio) − the mean over the 100 of Sharpe(random).
    - Report n°1's `random-turnover` matched turnover only and was summarized by its median seed. This control differs.
  - Buy and hold of the equal-weight member universe is reported beside it.
- **The rule:**
  - the expected return is the `fwd_return` readout of `matrix-select`'s cell;
  - a member is entered when its expected return exceeds the round trip, and exited when it falls below 0;
  - decisions are hourly and re-evaluate every holding, and each executes at the next open;
  - a position opens at min(1/n, 1/10) of the equity at that hour, n being the members with a signal, as far as the cash allows. It is held without rebalancing until it exits;
  - a holding whose pair leaves the universe is closed at the open that follows its last member month, as if the month's last decision were an exit;
  - a position whose bars end is closed at its last close;
  - every entry and every exit pays the taker fee plus slippage.
- **The series.** The initial equity is 10,000 USDT. The portfolio's net hourly returns are annualized with √8760. A portfolio that is never exposed has no Sharpe ratio, and H14 then fails.
- **Assumptions, stated.** Binance's 5 USDT minimum and the BTC and ETH lot steps are applied to every pair.
- **Prior:** fails. Each sizing or threshold choice counts as a variant.

### Variants

18 before this iteration, plus one per encoder arm: `enc-ols`, `enc-softmax` and `enc-linear`, 21 in all.
- A seed ensemble counts once.
- Each ablation that runs counts as one more.
- The planted leaks and the positive control are controls, not variants.

## Leak detectors measured against each other (iteration 5)

Registered on 2026-11-18, after audit passes 5a and 5a-bis, before any detector touched the confirmatory population and before any new detector ran on real bars (see the change log). It defines the detectors compared on one generated population of leaks, the controls, the metrics, and H15. Drafted in `.claude/briefs/iteration-5/prereg-draft.md`: "v1" below means that draft at commit `8473776`; the findings are `audit-5a-findings.md` and `audit-5a-bis-findings.md` in the same folder, and the draft's §9 and §10 give the disposition of each. Section numbers (§) refer to this section's parts.

### 0. Facts the design rests on (checked in the code, or read verbatim in the source, 2026-11-18)

1. **A missing bar.** `SeriesView.at` and `_window` give NaN for a row outside the series. Making a row outside **a run's input** missing is new in this iteration: truncation and re-tiling do it (§2). A comparison with NaN is false (`Cmp.evaluate`; `Same`, `Colour`, `Pattern` and `Cell` likewise), so a **binary** leak is never NaN: where a future read is missing it returns a finite value, 0 for a single comparison and possibly 1 under `Logic` (OR, XOR). A value node (`At`, `Agg`, `LogRatio`, `Rel`, `Raw`, `WSum`) propagates NaN, so a **continuous** leak's output turns missing. H1's catch rule (`adversary.py:1147`) counts a move above 1e-9 **or** a change of missingness.
2. **Compared rows.** Only rows `t - 10 .. t` can read a bar after `t` (`FUTURE_REACH = 10`); the rows scored by H1 among them are compared (`Bench.scored`). At every cut row `t` is scored, and every leak reads a bar after its row (`draw_leak` asserts a future reach of 1 at least), so every detector that removes or changes bar `t + 1` touches a read of every leak at every cut.
3. **Fonseca, arXiv 2607.04958 §8.3, read verbatim on 2026-11-18** (orchestrator, browser pane; auditor, plain fetch): the two-run detector "re-executes the pipeline on perturbed future data at sampled epochs and flags a change"; the tiling detector "compares outputs across shifted data windows". The text gives no perturbation law, no epoch rule, no run count and no tolerance (all 11 occurrences of "perturb" checked). No "default" two-run detector exists to copy: ours is defined here, and the paper says so.
4. **freqtrade**, `develop`, `freqtrade/optimize/analysis/lookahead.py`, read verbatim by the auditor on 2026-11-18 (SHA-256 `25b02b2d4f6e4317d8855b01976a3fef112e56280b7a33954634ed4dc51e2cca`), with `trim_dataframe`: the slice ends one candle after the date checked (`to_dt`, "since it won't buy on the last candle"); `analyze_indicators` compares `full_df.loc[cut_df.index]` with `cut_df`, that is **every kept row, the slice's last row included**, NaN equal to NaN; `compared_dt` serves only `report_signal`. Not traced: whether `load_bt_data` trims the end through `trim_dataframe`. **Causify DataFlow**, arXiv 2512.23977, read verbatim by the auditor: Theorem 4.24 (input window `[t − 2τ + 1, t]`, outputs on `[t − τ + 1, t]`) and Remark 4.25 (tiles of length τ ≥ L, compared with the full run "up to numerical precision").
5. **The generator's ties to H1.** The default placement draws half of the thresholds on body, wicks, range, fill and close location inside H1's bands (`BANDS`). The `quantile` placement (§1.3) replaces the draw by H1's bands with a draw by the pre-2019 bars; the overlap remains (§1.5). **These ties remain** in both placements, and are stated wherever a rate is read: the `designed` tag and the 90-bar reference window; the margin position (`PUSH`), with margin 1 drawn with probability 0.7; future offset 1 drawn with weight 0.4; `k = 0` half the time for fill and close location, the two quantities H1 pushes against bar `t` alone; the cell boundary `SMALL_BODY` (H1's 0.01) half the time.

### 1. Populations and the quantile table

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

### 2. Detectors

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

### 3. Controls (predicted verdicts, registered; never pooled into any rate)

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

### 4. Metrics (fixed now)

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

### 5. H15, and what was dropped

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

### 6. What the paper may and may not claim from these outputs

- **May:** the catch rates of these detectors on this generator and these bars, with intervals; their overlap; the dependence of truncation's rate on the convention for a missing bar, as the registered sentence; each detector's mirror asymmetry; the controls' verdicts; that our two-run arm is our definition, and that its law inflates bodies; H15's two labels, with its qualifier if triggered, and the cut-date spread beside them.
- **May not:** a rate over "all leaks"; that FI is better or worse than truncation in general; that FI's rate on this population is free of H1's bands (§1.6); that re-tiling is a mechanism independent of truncation on this population; that re-tiling or truncation, as run here, applies to fitted models (a two-tile input window would change every honest output of an expanding-window fit, `min_train_rows = 365`); "freqtrade's rate" or "Causify's rate"; any comparison with Fonseca's 18/33 and 33/33 (another corpus, another language).

### 7. Order of work and contact with the real bars

1. **Before 5b's GO, no detector runs on real bars with a `quantile` population. FI and SHUFFLE run on real bars only with seed 20261029, `h1-bands`, as already run.** No new detector runs on real bars at all before 5b's GO. Wave 3 builds and tests every detector on `bench.synthetic` bars, with seed 51118 and TWO-RUN seed 51119.
2. The development-population digest (§1.7) is added by a dated change-log line before 5b's GO.
3. The descriptive run (seed 20261029) and the confirmatory run (seed 20261118) use **one frozen commit**, the one 5b passed. If the descriptive run shows a bug, the fix is logged, re-audited, and the confirmatory run is reported as run after a code change.
4. **The stop rule.** Every assertion and gate is evaluated first, on the descriptive run and then on the confirmatory run, and writes only pass or fail and counts. No rate or per-leak verdict is written or printed until all pass. A failure stops the run; the fix is logged and re-audited; the next run is reported as run after a stopped attempt.
5. Contacts already made with the real bars for this design: the auditor read two recorded outputs for counts (`runs/2026-10-29-h1-adversary/adversary.json`, `runs/2026-10-30-twins/twins.json`); the orchestrator computed the quantile table from the pre-2019 bars (§1.5). Both are logged.

### 8. Variants and seeds

No strategy variant: the count of `docs/RESULTS.md` stays at 21. Seeds:
- population: confirmatory 20261118, development 51118, descriptive 20261029;
- TWO-RUN: 20261119, development 51119;
- SHUFFLE twins: 20261030 (`[seed, crc32(pair), k, j]`);
- H1's cuts: 20261027; H1's perturbation: 7;
- long schedule: cut seed 20261030 (another role than the twins' 20261030; the two streams have different lengths and keys), perturbation seed 11;
- equivalence gate: 3;
- cut-date bootstrap: 20261120.

## Metrics

- **Primary, forecast quality:**
  - log-loss;
  - Brier skill score against climatology (historical class frequencies);
  - expected calibration error and reliability diagrams;
  - Diebold-Mariano tests between models.
- **Secondary, trading:** net return, Sharpe and Sortino ratios, maximum drawdown, turnover, fees paid, exposure.
  - PnL has little statistical power here. Over the ten-month vault, the standard error of an annualized Sharpe ratio is about 1.1, so a Sharpe of 1 cannot be told apart from 0.
  - Every reported Sharpe ratio comes with the number of variants tried (see [RESULTS.md](RESULTS.md)) and a deflated Sharpe ratio.
- **Robustness, after Microsoft-Decision-1:** how often the decision flips under small perturbations of the inputs, such as feature noise or asset order.

## Costs

Results are reported under four fee schedules, plus zero fees as the gross reference. Rates as of October 2026; re-check before use.

| Venue | Maker | Taker | Source, read on 2026-10-27 |
|---|---|---|---|
| Binance spot (history only) | 0.10 % | 0.10 % | checked in iteration 1 |
| Bitvavo, entry tier (MiCA, Dutch AFM) | 0.15 % | 0.25 % | Bitvavo's API documentation and a search snippet of its fee page. The page itself was not read. |
| Coinbase Advanced, entry tier, EU | 0.25 % | 0.50 % | two news reports of Coinbase's announcement of 2026-09-16. Coinbase's own pages answer HTTP 403. |
| Kraken Pro, entry tier | 0.40 % | 0.80 % | Kraken's fee-schedule page, level 1 |

- Slippage is 2 bps per side. The exchange minimum notional and lot step are enforced.
- Every order is charged the taker rate: a decision at a close executes at the next open.
- Fee schedules change (Kraken on 2026-07-09, Coinbase on 2026-09-16). Applying today's rates to past years is a stated assumption, not a leak.
- The backtest uses Binance's USDT prices. Bitvavo, Coinbase and Kraken quote BTC and ETH in EUR or USD, so their price paths differ by the exchange rate.

## Baselines

Climatology, always flat, buy and hold, moving-average momentum, random positions with the same turnover, ridge on hand-made features, XGBoost.

## Change log

- 2026-10-25: initial version.
- 2026-10-25: the vault is sealed in code, after the iteration 1 audit. The splits do not change.
- 2026-10-26: git tracks the vault's key file and access log, after the re-audit.
- 2026-10-27, before Report n°1 runs:
  - Fees re-read at the source by a `scout`. Kraken is confirmed. Coinbase rests on secondary sources.
  - Bitvavo joins as a fourth schedule. It is the cheapest MiCA-authorized venue found that serves French residents.
  - Binance's exit from France is confirmed at the source: the AMF withdrew BINANCE France SAS's registration on 2026-07-02, at the end of the MiCA transition period.
  - A runtime tripwire in `python/tests/conftest.py` now backs the static guard during tests.
  - Diebold-Mariano tests use the original rectangular kernel with h − 1 lags and the Harvey-Leybourne-Newbold correction. They fall back to Bartlett only when the rectangular variance is not positive. Measured size at a nominal 5 %, with h = 7: 5.25 % rectangular against 8.75 % for Bartlett. With h = 1 the two are identical.
- 2026-10-28, after Audit A of iteration 2 and before the official runs:
  - The future-invariance test is strengthened. Before, `trades` did not move, the volumes had no common level shift, the taker share moved one way only, and each cut ran in one direction. The auditor's peeker on `trades` was flagged at 0 of 8 cuts. Now every column moves, and every cut runs in both directions.
  - A second pass of the audit found that the ratios inside a bar still did not move: range, body, VWAP, taker VWAP and trade size. Six planted ratio leaks were flagged at 0 of 8 cuts. Now every ratio moves, bar t + 1 is built against the last 91 bars, and those leaks are flagged at 8 of 8. The auditor's planted leaks become permanent controls, and a positive control is added (see Leakage tests). The registered hypothesis H1 does not change.
  - A third pass found that the candle's shape kept its proportions in both runs, so a leak on the next bar's close location or fill was flagged at only 3 and 2 of 8 cuts. Now the two runs give bar t + 1 opposite shapes, and those leaks are flagged at 8 of 8. Five shape leaks join the permanent controls.
  - The same pass found that a `?` was read from the perturbed bars: a push that stopped working would have read as `?`, not as a failure. Now a `?` is predicted from the original bars before perturbing, for a declared reason only.
  - A fourth pass found that colour and size were tied. The two runs gave a small green bar and a large red one, so a leak on a small red next bar was flagged at 0 of 8 cuts. Now the colours alternate from cut to cut, and two controls on colour with size join the bench.
  - Two sensitivities join Report n°1. The registered analyses do not change.
    - H9's paired bootstrap is re-run with a block of max(PW(d), PW((d − d̄)²)), where PW is the Politis-White length.
    - Diebold-Mariano is re-run with a Newey-West Bartlett variance and L = floor(4(T/100)^(2/9)) lags, without the Harvey-Leybourne-Newbold correction.
  - The vault guards are strengthened after two evasions the auditor found. `docs/DATA.md` gives the details and the remaining limits.
    - The runtime tripwire now goes up before any test module is imported.
    - It now also wraps the raw-archive readers (`zipfile`, polars' CSV and other text readers) and pyarrow's dataset constructors.
    - It trips on any wrapped read of a path under `data/`.
    - It watches the seal. A test may not rebind the seal's names, and a sealed read that returns a vault row fails the test.
    - The static guard now flags `sys.modules`, edits of `sys.path`, and any patch of the seal.
    - The tripwire runs only under pytest. The command-line runs rely on the seal in `olsprime.protocol` and on the static guard.
- 2026-10-28, after the first official H1 run (commit 9c414ca), which held:
  - CI on Linux found a control caught by rounding alone. The transductive scaler fed its scaled features to the baseline ridge, which standardizes again on its training rows and so undoes the scaling exactly. Its outputs moved by 10⁻¹⁶ at most. The bit-for-bit rule counted that as a catch at every cut on Windows, and at all but one cut on Linux.
  - Now a control is caught only where an output moves by more than 10⁻⁹ (see Leakage tests). Measured on the synthetic bars, every other control's weakest catch moves an output by at least 2.7 · 10⁻³ or flips a target.
  - The transductive scaler's ridge now centres the features but keeps their scale, so the test month's spread reaches the penalty. Its catches move an output by 8 · 10⁻³ to 2.5 · 10⁻² on the synthetic bars.
  - H1 is run again on the corrected code (commit 881a63c). The first run's row stays in `docs/RESULTS.md`, followed by an erratum row for the second run. Report n°1 does not use the changed code. Re-run at 881a63c with `--check`, it reproduces every number: only the commit and code digest lines differ, in `config.json` and `report-1.md`. The registered hypothesis H1 does not change.
  - A second audit of the guards found three more ways around them and eight smaller holes. Each is closed, or stated as a limit in `docs/DATA.md`.
    - Every test gets an empty data root of its own. With both keys forged, the two file loaders still refuse the repository's `data/`.
    - A raw archive under `data/raw/` is read only when every file on the call stack holds the allowance, the test file included.
    - The allow-list is read-only. After every test, a check confirms that every guard is still in place, and a breach ends the session.
    - The static guard flags the attributes that take a guard apart, such as `__globals__`, `__closure__` and `__bases__`, and bans `runpy`, `gc` and `ctypes`.
    - A third audit closed two more ordinary routes. A test allowed to read back its own Parquet files could name the repository's `data/` directly, and `zipimport` could read the raw archives. Now, under pytest, only the seal's loaders may read the repository's `data/`, and `zipimport` is both gated and banned.
    - In plain words: a guard inside the process can be taken down from inside the process. These guards stop accidents, not sabotage. The structural fix is to keep the vault rows where the process cannot read them without both keys.
  - **A vault exposure, recorded here.**
    - **What was read.** To prove the holes D1 and D2, the auditor's evasion tests read BTCUSDT 1d vault rows outside the seal: the 31 bars of the 2026-03 raw archive, and the vault months of the Parquet file.
    - **What the tests show.** They assert row counts. One of them prints the first bar of the 2026-03 archive when it succeeds.
    - **Why it does not reach a model.** The auditor writes no model code, and no feature, model or decision of the project uses these rows.
    - **What follows.** The vault stays the final test set. This exposure is stated in every report that uses it. Proofs of a hole now run against fake data only, and the new guards stop both paths.
- 2026-10-29, before any run of iteration 3:
  - The design of "Matrix on hourly bars (iteration 3)" is fixed: panel, arms, folds, scoring and decision rules for H2, H3 and H10–H12. It includes a fallback for H3 to the 30-day window, should the one-year kernels not run in time.
  - H1 gains the adversary, a descriptive measure. Its registered rule does not change.
  - Two clarifications of the panel, the same day and before any Matrix run. They come from building it, and change nothing in the design.
    - 233 of the 274 members have rows in the development period; the other 41 first join in 2025.
    - The validation year's bars are loaded through the seal, then cut before features and labels. The earlier wording said they were not read at all.
  - The physical seal of the vault months, in "Splits": a vault tree outside `data/` (stage 1) and its age encryption (stage 2). The downloader and `build_parquet` now refuse vault months. No split or period changes.
- 2026-10-29, after audit pass 1a and before any Matrix run. The audit found three flaws in the design of iteration 3, and nine smaller points.
  - **H12's CUSUM measured nothing.** An average run length of 30 days gives about 72 false alarms over the 2,191 test days, so "fewer than 72 refits" was a coin flip under the null. And the mean of the members' residuals, which move together, does not have the unit variance the threshold assumed. Now the daily value is scaled by its spread over the last fit's selection days, the run length is 365 days, and H12 needs at most 36 fits (`docs/HYPOTHESES.md`).
  - **The first fit's selections could not be computed.** They need prequential forecasts that no arm had made yet. Now every candidate forecasts from 2017-11, with the σ of each row's month. A selection with fewer than 1,000 rows takes fixed defaults, which are counted.
  - **The CUSUM's timing was ambiguous.** One reading refitted an hour before the alarm's labels were known. Now the input, the instant it is known and the instant an alarm acts are fixed.
  - A comparison of two arms now needs the stationary bootstrap's interval as well as Diebold-Mariano, and each difference is reported as a share of climatology's log-loss.
  - Defined more tightly: the selection rows, the paired bootstrap of the Brier skill score, the variant count (8, 18 in all), a row's month (that of its bar's open), and the panel H1's members with no bar after a cut.
  - Stated as limits: the upper wick at odd cuts in H1, and the panel H1's inputs from other members.
  - The adversary's report gains an attenuation curve, the families it never produces, the share of constant twins and the mean per-cut rate.
- 2026-10-29, after audit pass 1b and before any Matrix run: the CUSUM's day that straddles a refit is defined. Its value uses the fit in force at its decision time, and the restarted CUSUM leaves it out.
- 2026-10-29, after audit pass 1c and before any official Matrix run. The audit found no Blocker and no Major point, and six Minor points, all fixed before the runs. No rule, threshold, grid, seed or period changes.
  - **The CUSUM's s** is now read with the fit's own σ, as its live days are. It was read with the σ of each selection row's month: a choice the text left open, and not the faithful one. On two synthetic panels the two differ by 2.4 × 10⁻⁵ and 1.7 × 10⁻⁴ of s.
  - **The panel H1** compares the fit of a cut's month only when a row of that month is decided by the cut. Without one, the run scoped to the cut makes no fit for that month, and the honest system was flagged. The predictions that rest on that fit follow the same rule.
  - **A member not yet listed at a cut** is left out of it too, and the limit this opens is stated.
  - **The reports say more.**
    - The panel H1 marks a run that is not the registered one, as Report n°2 does.
    - Report n°2 lists the days each refit left out of the CUSUM.
    - It gives the Diebold-Mariano kernel and lags behind each comparison.
    - It gives its coverage in hours.
  - **Smoke runs on the real panel came before this entry.** They measured run times and checked the reports' shape:
    - the panel H1 on its sub-panel, with test months 2019-01 → 2019-06;
    - Report n°2 on 5 members, with test months 2019-01 → 2019-03;
    - Report n°2 on every member, with test months 2019-01 → 2020-06, 18 of the 72.

    The full development panel, every member from 2017-10 to 2024-12, was also built with no arm run on it:
    - once for `docs/DATA.md`: its rows, its members and the shares of the three label classes;
    - once to size and time the runs, using no label value. That pass measured each feature's |mean| / std, over the panel and over each month's σ set, from feature moments only. It also counted the rows and kernel pairs each run reads, at the eight H1 cuts too. The official H1 sub-panel was rebuilt to time it.

    Their numbers are not results, and none of the changes above was chosen from them. The official runs score those months again, with the rest.
- 2026-10-29, after audit pass 1d and before any official Matrix run. No rule, threshold, grid, seed or period changes.
  - **The previewed months, apart.** Report n°2 also gives the Brier skill score of `matrix-select` and every comparison on the 18 test months the smoke runs scored, and on the other 54 alone (Scoring). This is fixed before the run, and it describes: the verdicts rest on the whole period.
  - **Where the results are read.** Under its verdicts, the report states that those months were scored before the run, with the same arms and rules. The RESULTS rows of H2, H3 and H10–H12 say it too.
  - The entry above now lists the passes over the full development panel among the contacts with the real data.
- 2026-10-29, after audit pass 1e and before any official Matrix run. No rule, threshold, grid, seed or period changes.
  - **Identical hours.** Each comparison gives the share of hours at which both arms' hourly log-losses are identical and the count of informative hours, with the words "few informative hours" above one half (Scoring; the count after audit pass 1f). Two arms that read the same cells give exactly equal losses. A part where they differ at only a handful of hours would otherwise show an ordinary p-value, with degrees of freedom counting every hour.
  - **A part's words.** A comparison on the previewed months or on the others says whether the rule is met. "Passes" stays the word of the whole period's verdicts.
- 2026-10-29, during the official runs, after the panel H1 and the adversary and before Report n°2's verdicts. No rule, statistic, threshold, grid, seed or period changes.
  - **The first official Report n°2 stopped on an internal check.**
    - The run was at commit `3a22daa`. The arms ran over the whole test period. Then the first ECE, `climatology-panel`'s, differed from `stats.ece` by 1.3 × 10⁻⁹ relative, above that check's fixed tolerance of 10⁻⁹.
    - The cause is rounding. `stats.ece` adds a bin's rows in one sequential sum, and climatology repeats one calibrated forecast over many rows, so the rounding errors add up instead of cancelling.
    - A probe on synthetic data reproduced the gap. A lost row, the defect the check is there for, moves the ECE about 300 times more than the new tolerance.
    - The tolerance is now 4·n·ε, about eight times the worst-case rounding of the two sums over n rows: 1.2 × 10⁻⁹ in absolute terms for 1.4 million rows.
    - The run wrote no file. Its traceback showed one number, `climatology-panel`'s ECE over the test period, 0.0029. No other number of Report n°2 was seen before the re-run, which scores the same arms with the same rules.
- 2026-10-29, after audit phase 2, once Report n°2 had run. Wording only: no rule, statistic, threshold, grid, seed or period changes.
  - **What the ECE cross-check guards.**
    - It guards a row lost or counted twice between the hourly sums and `stats.ece`. Such a row moves the ECE by about |correct − confidence|/n. For a row of climatology, whose confidence is about 0.44, that is 220 to 285 times the tolerance on the panel.
    - A row whose confidence nearly equals its correctness, a confident and right forecast, moves it by almost nothing.
    - It cannot see a row put in another bin. Both paths bin the same way, and a row moved between two bins whose sums share a sign leaves the ECE unchanged.
    - The docstring of `ece_tolerance` says otherwise. It is corrected with the next change to `bench/report2.py`.
  - **The bound.** The two paths do not round alike.
    - `stats.ece` counts each bin's correct rows exactly, and adds its confidences in one sequential sum. Divided by n, that sum's rounding moves the ECE by at most about u·n·mean(confidence), where u = ε/2 is the unit roundoff. That is below n·ε/2.
    - The hourly path adds about 30 rows per cell, then the cells over about 50,000 hours. Its rounding is smaller still: at most about H·u, for H hours.
    - So 4·n·ε is more than eight times the worst case, as long as the mean confidence stays below 0.96. Climatology's is about 0.44.
    - For the run's 1,493,353 scored rows, the tolerance is 1.33 × 10⁻⁹. The entry above rounded the panel to 1.4 million rows and the tolerance to 1.2 × 10⁻⁹. The stopped run's gap was 3.7 × 10⁻¹² in absolute terms: 1.3 × 10⁻⁹ of an ECE of 0.0029.
- 2026-10-29, before any run of iteration 4. "The encoder, and what a verdict is worth (iteration 4)" is added. No rule, statistic, threshold, grid, seed or period of iteration 3 changes.
  - **What it registers:**
    - the encoder arms of H4, H5 and H13, with their fits, seeds, determinism settings and the cost table;
    - the panel H1 for the encoder arms on GPU, with a pre-check, a fallback rule fixed in advance, and two planted training-time leaks, `cheat-stamp` and `cheat-value`;
    - LFM3's two ablations and H6, run only if time remains;
    - the size and power study of the pass rule;
    - `olsprime.explain` and its log of contacts;
    - H1's future-shuffle twins;
    - H14, which runs in iteration 5.
  - **Variants:** 21, with the three new arms.
  - **Report n°2 is re-run once**, to save its hourly series and scored rows in `series.npz`, with their digest.
    - Audit phase 2's four logged items are folded in: the Coverage sentence, `ece_tolerance`'s docstring, H12's own rule in the parts, and a per-file summary in `diff_runs`.
    - Its numbers must not change. The re-run is compared with `runs/2026-10-29-report2/`, and only a fixed, named list of lines may differ.
  - **Contacts with the real data in this iteration** are listed in the entries below, as they happen. None has happened yet. The encoder is sized on a synthetic panel shaped like the real one, whose row counts come from `docs/DATA.md`.
- 2026-10-30, after audit pass 4a and before any run of iteration 4. The audit found five Major points, nine Minor points and seven Nits, and no Blocker. Every one is fixed in the section above. No rule of iteration 3 changes.
  - **H4 could hold vacuously.** Two arms that both sit at climatology meet its bounds. H4, and H13 with it, is now testable only if `enc-ols` or `enc-softmax` shows skill, an interval of its Brier skill score above 0.
  - **The GPU H1 would have flagged honest arms.** BLAS and cuBLAS choose their kernels by problem size. A probe on the design's shapes showed rows of the same product differing by up to 5.7 × 10⁻⁶ in fp32 between batch sizes. The perturbed run forecasts fewer rows than the honest one, so its batches differ.
    - Every batched computation outside a training step now runs in fixed batches of 4,096 rows, in panel order, the last one padded.
    - The pre-check gains a scope test.
  - **The fallback let leaks hide under one draw of noise.** If the GPU is not bit for bit, the registered H1 now runs on CPU torch, where it must be. The GPU run becomes a description, with a floor over three honest runs and catches given as multiples of it. A time budget for the controls is fixed in advance.
  - **H14 was confounded with the market's drift.** It now also needs a Sharpe ratio above that of random positions with the same exposure and turnover. Its sizing, exits at the universe's edge, initial equity, annualization and the never-exposed case are fixed.
  - **`explain` could open a channel into the encoder's design.** Wave 2 starts only after this pre-registration is committed. After the first `explain` call on 2019–2024, the encoder section changes only for what cannot be built as written, and each such entry cites the line count of `CONTACTS.log`. `series` and `sample` touch test months by construction. `why` outside the scored rows runs only its first check.
  - **The purge was invisible to the cuts**, which all fall at least 60 days after the fit they test.
    - A ninth cut, at F − 24 h for the 2021 fit, compares that fit itself.
    - A third control, `cheat-purge`, trains with no purge and is predicted caught there.
  - **The audit's bolder check is added: a positive control, `pos-window`.** It must learn a label that lies inside its own window to a Brier skill score of at least 0.5, or that is reported before any H4 or H5 number.
  - **Made precise:**
    - the controls' predicted patterns, computed per cut;
    - H13's timing protocol;
    - H6's rule, with an interval and a tolerance that three seeds cannot shrink to 0;
    - the twins' bar values and what "moved" means;
    - which parameters take weight decay;
    - the cross-entropy before the floor;
    - a row's year;
    - H4's margin;
    - the H1 runs' seed and their preview of skill, stated as limits.
  - **The power study**
    - adds L = 48, since L = 24 keeps only two thirds of the overlap's own dependence;
    - adds a second power grid whose shift is concentrated in a tenth of the blocks;
    - calls its detectable size a lower bound;
    - says that its intervals are conditional on the bootstrap's seed.
- 2026-10-30, after audit pass 4b, which re-checked the fixes of pass 4a, and before any run of iteration 4. GO to commit this pre-registration and start wave 2, with four Minor points and five Nits, all fixed above.
  - **H14's random positions** were not buildable as written. They are now two-state chains per member, matched in expected exposure and entries to `matrix-select`'s portfolio, 100 of them. The paired bootstrap of the Sharpe difference is defined.
  - **The purge cut saw only a leak past F − 24 h.** A second purge cut, at F − 30 days for the 2021 fit, compares the training and every epoch's parameters. A fourth control, `cheat-slice`, which trains on its own slice, is predicted caught there and not at F − 24 h. This was the audit's bolder check, and it is cheap once the first purge cut exists. The two cuts bracket the purge window.
  - **The budget had no answer** when the honest arms alone exceed it on CPU. They then retrain at four cuts, and only forecast with the honest parameters at the others.
  - **`pos-window` keeps the panel's stamp**, so that its row never sits in its own memory.
  - **Made precise:** the honest run's fit year at the purge cuts; the concentrated grid's exact count of shifted blocks; the twins draw from bars at or before the cut; `explain`'s explicit flag; and H14's change-log line in `docs/HYPOTHESES.md`, since a narrowed claim is still a changed one.
- 2026-10-30, wave 1, before any encoder run on real data and before the first `explain` call (`runs/explain/CONTACTS.log` does not exist yet). The encoder is built and sized on synthetic data only. Nothing registered above changes. Where the section leaves a choice, the build's reading is fixed here, so that no result can choose it.
  - **The attention block.** In every arm, Q, K and V come from one linear map with a bias. One output projection, with a bias, maps the four heads back to d_model.
  - **`enc-ols`.**
    - It computes O = Q̃ ((K̃ᵀK̃ + Λ)⁻¹ (K̃ᵀV)), the product W V taken in another order, with the same Cholesky factor. `head` computes W itself.
    - Queries and keys are scaled to unit root mean square with ε = 10⁻¹².
  - **`enc-softmax`** uses the math backend of scaled dot-product attention in training too, not only in H13's timing.
  - **The memory.**
    - Its key map W_z has no bias: the ridge is centred, so a bias would cancel.
    - Its entries are the complete rows with a valid window, the same rows that train and are forecast.
  - **The standardization** uses the population standard deviation.
  - **The fit.**
    - The slice loss that picks the epoch is the log-loss of the floored probabilities, as the scores read them. Training minimizes the cross-entropy before the floor.
    - All six epochs run. There is no patience rule.
    - The cosine reaches 10⁻⁴ at the last step of epoch 6.
  - **The controls.**
    - `cheat-value`'s label projection is a linear map, so it takes weight decay.
    - `pos-window`'s label sums the window's last 24 one-bar returns in order, in fp32, and classes the sum with the row's own threshold.
  - **Parameters:** 20,995 for `enc-softmax` and `enc-linear`, 21,003 for `enc-ols`. `cheat-value` adds 192.
  - **Checkpoints** are written by hand in the safetensors layout and never go through pickle.
  - **Sizing**, on a synthetic panel of 30 members, hourly from 2017-10 (`docs/ITERATIONS.md`, iteration 4).
    - Two whole 2024 fits of `enc-ols` on the RTX 3060 were bit-identical: every epoch's parameters, the slice losses, the epoch kept and the 253,193 forecasts. The scope test passed at every prefix.
    - So the registered H1 is planned on the GPU. Its own pre-check still runs first, on the real sub-panel.
    - The H1 with every control is projected at about 8.7 hours, under the 12-hour budget, so every cut runs.
  - **Contacts with the real data:** none yet.
- 2026-10-30, before the first `explain` call and before any encoder run on real data (`runs/explain/CONTACTS.log` does not exist yet). The panel H1 for the encoder arms is built and run on synthetic data. A fifth control is added and the verdicts are made precise. No rule is loosened.
  - **What the synthetic bench showed.** On the GPU, the pre-check matched to the bit, every honest arm was invariant at every cut, and the floor over three runs is 0. Every control was caught exactly where predicted, in both directions.
  - **A risk, named before the run.** In a synthetic probe, `cheat-stamp` was caught bit for bit, but its leak gave no measurable skill: a Brier skill score of −0.0009, against −0.0011 for honest `enc-ols`.
    - Its leaky entries are the last day's, about one in thirty of a 30-day window.
    - The synthetic members move independently. The real members move together, so the leak may weigh more on the real panel.
    - The registered check, at least 0.1 with an interval above every honest arm's, stands. Its result is reported as it falls.
  - **`cheat-stamp-day`, a fifth control**, described in "Planted training-time leaks". Its memory is made only of labels not yet known. It shows whether H1 catches a stamp leak that gives skill, whatever `cheat-stamp`'s skill turns out to be. With it, the panel H1 is projected at about 9 hours, under the 12-hour budget.
  - **Three verdicts, reported apart:** H1 as `docs/HYPOTHESES.md` defines it, the skill check control by control, and `pos-window`'s check. A failed skill check is a finding about the control, reported beside H1's verdict, never folded into it or dropped.
- 2026-10-30, after audit passes 4c to 4f and their second looks, before any encoder run on real data and before the first `explain` call (`runs/explain/CONTACTS.log` does not exist yet). No rule, statistic, threshold, grid, seed or period changes. Where the section leaves a choice, the build's reading is fixed here. Descriptions are added beside registered verdicts, and one line of the wave-1 entry is corrected.
  - **Audit pass 4c**, on Report n°2's series, the power study, the twins and the getters: no Blocker and no Major point, three Minor points and three Nits, all fixed before the study runs. GO for Report n°2's re-run and the twins. Its second look gave GO for the power study, with one Minor point and three Nits, all fixed.
    - Every command-line run of the study goes through a pool whose workers use one BLAS thread, so every worker count gives the same bytes. In one process, the main process's multithreaded BLAS moved the last bits of 7 of 5,452 values of `power.json`, never a rate.
    - On Windows a worker's pipe sometimes breaks (WinError 6), in about one test run in four. The pool is then rebuilt and only the calls without a result run again, at most three times. A pool in which no call finishes for 1,800 s counts as broken. Each restart is recorded in `run.json`. A call is a pure function of its arguments, and a pool broken on purpose by the audit gave the same bytes.
    - The study refuses a series whose recomputed comparisons differ from `report2.json`'s by more than 10⁻⁹ relative, instead of only recording it. Every value the comparison records is checked, the count of identical hours included, and so is climatology's mean log-loss.
    - The reader refuses a path outside the runs folder before it reads a byte.
    - The audit's bolder check is added as a description: the variance ratio each block length should give, predicted from the series' own autocovariances, beside the measured one. Each no-flips ratio is given with its standard error, about 14 %.
  - **Audit pass 4d**, on `olsprime.explain`, in three looks: two Major points, seven Minor points and six Nits, all fixed. GO for the five whys.
    - The residual that closed a forecast's parts was zero by construction. It is now bounded, and a residual above its bound stops the call (exit 3).
    - The shared environment held an extension built before `beta` and `mean_y`. It was synced, and every call probes the extension before it reads anything.
    - Each tree's partition is recounted group by group, not only checked by its sum.
    - A Matrix-free twin of the ridge forecast, in numpy, rebuilds each explained ridge forecast within a stated bound (the audit's bolder check).
    - One limit is stated, not fixed: check 1 holds the range of the entries behind σ² to the panel's stamps, not their values.
  - **Audit pass 4e**, on the encoder's core and its panel H1: no Blocker and no Major point, three Minor points and four Nits. GO for the panel H1 and for Report n°3's fits on this core. Its second look, at commit `abbc7d1`, gave GO for the panel H1 on the GPU, with one Minor point, on this entry's wording, corrected here, and five Nits. It trained `cheat-stamp`'s run 1 in four orders, and every part came out byte-identical.
    - A resume is refused if the build changed: torch and its CUDA build, cuDNN, Python, the platform, the GPU and the driver passed by `--driver`, and on CPU the thread count, as well as the config, the code and the manifest. The refusal names each field that changed. The platform holds WSL2's kernel version, so a kernel update between a stop and a resume also refuses the resume.
    - **A limit.** On CUDA the identity does not hold the CPU's thread count, although the memory's readout runs on the CPU there. The audit found the prefix sums and the readout bit-identical with 1, 2, 4 and 6 threads.
    - The registered scope test runs at the first cut. The same test also runs at every regular cut, as a description (below).
    - Torch 2.15's documentation lists `cumsum` on a CUDA floating tensor among the operations that act deterministically under `use_deterministic_algorithms(True)`; older releases listed it among those that raise. On the RTX 3060 it neither raised nor drifted across calls and prefix lengths, and it matched the CPU's sequential sum to the bit on a 5,000 × 100 fp64 probe. The pre-check remains the gate.
    - **A correction of the wave-1 entry.** `pos-window`'s label sums the 24 one-bar returns in fp64, as built, not in fp32. On 38,144 synthetic rows the two readings class every row alike, the closest margin being 308 fp32 ulps.
  - **Audit pass 4f**, on Report n°3: no Blocker, one Major point, seven Minor points and five Nits, all fixed before any fit. Its second look gave GO for the fits and the score, with three Minor points and three Nits, all fixed. It stopped a run at seven points where a file is written, and every resume gave the same bytes.
    - A saved part is checked against its folder: its arm, seed and year, and its checkpoint's and forecasts' own records. A copied folder would otherwise have been scored as another arm (the Major point).
    - A timing file that fails its digest stops the score, instead of reading as absent.
    - Every stage binds the code and manifest digests, and the score refuses two timing files drawn on different samples.
    - `report3.json` lists the fits' builds. Report n°3 is registered only if every fit ran on CUDA with one build, and H13's timing only if it ran on CUDA with the GPU named.
    - The tree is frozen at the fits' commit: the timings, the score and `--check` run at that commit. A fix found in between waits until `--check` has passed.
  - **The panel H1, as built.** Audit pass 4e accepted every reading.
    - At a compared decision, the memory's stamps and statistics are the window's range among the stamp-sorted entries, those entries' stamp, symbol and open time, the window's raw moments and the readout. They are read through a no-op hook in `predict`.
    - Inputs are compared as rows keyed by open time and symbol. The order of the episodes is the weeks' stamps and each epoch's permutation. The step, parameter and missing-window counts are compared too.
    - A control must be caught in each direction where it is predicted caught, and in neither where it is not. That is stricter than iteration 3, which took the union of the directions.
    - The pre-check compares the memory up to each fit year's last cut. The registered scope test runs at the first cut, with the fit reloaded from its file.
    - Every system's predicted pattern follows one rule, computed per cut through the system's own hooks: a system is predicted caught at a cut when a compared item reads a label whose `label_known_at` is after the cut hour.
    - `cheat-stamp` and `cheat-stamp-day` put a row's own label in its memory at its decision time. That is their leak, by design.
    - The purge cuts take the seeds of a 9th and a 10th cut of the same schedule (k = 8 and 9 in `perturbation_at`), and their mirror follows the parity of k.
    - `pos-window` is scored on the cut years. A row without a label of its own is dropped and counted.
    - The CPU fallback's floor is computed per system, from its own three unperturbed runs.
    - Exit codes: 2 if the pre-check fails, 1 if H1 fails, 3 if H1 holds and a skill check or `pos-window`'s check fails.
  - **Report n°3, as built.** Audit pass 4f accepted every reading.
    - H13's timing uses each arm's seed-1 fit of 2024. The 12,288 timed rows are drawn with the seed 20261030 from the scored rows that have a valid window. The Matrix timing uses the same sample, by its digest.
    - The memory readout is timed where `predict` computes it, on the CPU in fp64. It costs the same for every arm, about a fifth of the whole pass on synthetic data, so it pulls the ratio toward 1: it can only make a holding H13 fail.
    - Within each repeat the arms run in the order `enc-ols`, `enc-softmax`, `enc-linear`, so `enc-ols` and `enc-softmax` alternate.
    - H13's ratio is median(`enc-ols`) / median(`enc-softmax`), as registered.
    - Each Matrix arm is timed by its own readout at the last fit's choices, and `matrix-adaptive` at `matrix-select`'s ρ.
    - Every stage of Report n°3 runs in WSL2, on the Ryzen 5 3600 and the RTX 3060. Matrix's CPU column uses the portable build there, where the process's peak memory is `ru_maxrss`. That peak is the whole process's, panel and windows included, and the memory's own size is given beside it. Matrix's parameters are 0: its choices are selections.
    - The statistics' parameters come from Report n°2's `config.json`. The panel is checked by its fingerprint, and every scored row is paired one for one before any training.
  - **Descriptions, beside the registered verdicts.** None enters a verdict.
    - The scope test at every regular cut, for the honest arms and `cheat-stamp`, in the pre-check stage (audit pass 4e's bolder check). It loads each system's unperturbed run 1 of the cut's year; `cheat-stamp`'s is the control's own fit, the one H1 uses. At the registered setting, every system at every cut, it trains nothing that H1 does not train.
    - H13: the readout's own time, beside the attention operator's and the whole pass; and the median of the per-repeat ratios, beside the ratio of medians.
    - H4's two bounds on the three seed-matched pairs, and in the reversed direction, `enc-softmax` non-inferior to `enc-ols` (audit pass 4f's bolder check).
  - **`explain head`, its readings**, fixed before it is built.
    - It explains only scored rows of 2019–2024, which Report n°3 forecasts, so every call needs `--test-months` and is logged. A row before 2019 is refused: no fit of Report n°3 is in force there.
    - The model is the `enc-ols` checkpoint of the fit in force at the row's decision time, seed by seed, verified by its digest and against its folder.
    - Per block and head, W = Q̃ (K̃ᵀK̃ + Λ)⁻¹ K̃ᵀ over the row's 64-bar window. Its rank is at most 9.
    - The row of W is the decision bar's: 64 signed weights, oldest first.
    - The diagonal mass is trace(W) / 64. The decision token's own weight is given beside it.
    - The effective rank is the exponential of the Shannon entropy of W's normalized singular values (Roy and Vetterli, 2007).
    - Every row must sum to 1 within `row_sum_tolerance`. The row's forecast, recomputed from the checkpoint, must equal the saved one, to the bit where the fits' computation is reproduced. Either failure stops the call.
  - **Contacts with the real data in this iteration so far**, all from a clean clone of 221591c on Windows, before any `explain` call and any encoder run:
    1. Report n°2's re-run, `--compare-with runs/2026-10-29-report2`, 2026-10-30 02:42–03:05 UTC. It reads 2017-10 → 2024-12 and scores 2019-01 → 2024-12, as in iteration 3. The five allowed differences were met and every other byte matched. `series.npz`'s SHA-256 is `03916fda8ffa9f97709216b2365e7a224dd8c8d71448d75035a7824fdc9cc0b9`.
    2. Its `--check`, 03:05–03:28 UTC: the four files were byte-identical, `series.npz` included.
    3. The twins, twice, at 03:28 and 03:29 UTC, byte-identical. They read BTCUSDT's and ETHUSDT's daily bars through 2024-12, as iteration 3's H1 and adversary did.
- 2026-10-30, before the first `explain` call and before any encoder run on real data (`runs/explain/CONTACTS.log` does not exist yet). Report n°3 cannot be built as written on the Windows runs of Report n°2, so it is given a Report n°2 run made in WSL2. No rule, statistic, threshold, grid, seed or period changes.
  - **What was found.** On the same input bytes, `np.log` and `np.exp` give different last bits on Windows and in WSL2's Linux.
    - So the panel's log-based columns differ in their last bits between the two platforms: among the features the returns, volatilities, moving-average gaps and ranges, and also the threshold and the forward return. The panel's fingerprint differs with them.
    - On identical synthetic bars, exactly representable on both sides, the times, the labels, `f_qvol_z_30` and `f_taker_7` matched, and the other columns did not.
    - The `explain head` engineer found it, and the orchestrator reproduced it.
  - **Why it matters.**
    - Every stage of Report n°3 runs in WSL2, and Report n°3 checks its panel against Report n°2's fingerprint before any training. Every Report n°2 run so far was made on Windows, so Report n°3 would be refused.
    - Scoring an encoder trained on Linux features against Matrix forecasts made from Windows features would not compare two systems on one panel either.
  - **What is done.**
    - Report n°2 is re-run in WSL2, from the clean WSL2 clone, with the registered configuration.
    - Report n°3 reads that run, by its series' digest: its panel and fingerprint, `matrix-select`'s series for H5, and `climatology-panel`'s log-loss for H4's margin.
    - `explain head` runs in WSL2 too, on Report n°3's folder.
    - The Windows runs remain Report n°2's record of iteration 3. `why`, `series` and `sample` keep reading the Windows re-run.
  - **A description, beside it.** The two runs of Report n°2 are compared: the scored rows and their labels, each arm's scores, and the verdicts of H2, H3, H10, H11 and H12. A verdict that the platform's last bits can move is the first finding to report.
  - The panel H1 for the encoder arms is not affected: it builds its sub-panel and compares its own runs, all in WSL2.
- 2026-10-30, after audit pass 4g on `explain head`, before the first `explain` call (`runs/explain/CONTACTS.log` does not exist yet). No rule, statistic, threshold, grid, seed or period changes.
  - **Audit pass 4g**, on `explain head`: no Blocker, one Major point, two Minor points and two Nits. GO once the Major point is fixed, before any call on a real checkpoint. Each of the build's seven interpretations was accepted.
    - **The Major point.** `head` checked a part only against its own folder. A checkpoint changed by one bit, with its digests rewritten to match, was explained as if it were Report n°3's. `head` now refuses a part unless its checkpoint's and forecasts' digests, its count of forecasts and its epoch kept are the ones `report3.json` records for that arm, seed and year.
    - The forecast check is a fingerprint of the forecast, not a proof of the checkpoint's bytes. The digests bound to `report3.json` are the checkpoint's identity.
    - The registered row-sum check, on the fp32 W, is loose by three orders of magnitude. The same check on W formed in fp64 from the same Q, K and λ, with its own bound, is added beside it, and it stops the call too.
    - The contact line names all that a call reads: the fit year's forecasts and labels, and the memory through `as_of`.
    - The audit's bolder check, if it can be built without loosening a guard: with every seed, the recomputed forecasts, ensembled as the fits ensemble them, must equal the `enc-ols` probability of the row in Report n°3's `series.npz`, to the bit.
  - **Contacts with the real data since the last entry**, from clean clones at `5f17a76`, whose CI was green on Linux and Windows:
    4. The panel H1 for the encoder arms, on the GPU in WSL2, from 07:38 UTC. It reads the 10-member sub-panel's hourly bars through 2024-12, and forecasts and scores its rows in the cut years 2020, 2021, 2022 and 2024.
    5. The power study, on Windows, from 07:38 UTC. It reads Report n°2's series `03916fda…` by its digest.
    6. Report n°2's re-run in WSL2, from 07:39 UTC, compared with `runs/2026-10-30-report2`. It reads 2017-10 → 2024-12 and scores 2019-01 → 2024-12, as before.
- 2026-10-30, after the first `explain` call (07:42:06 UTC). From that call on, the iteration 4 section changes only for what cannot be built as written. `runs/explain/CONTACTS.log` holds 24 lines at this entry. No rule, statistic, threshold, grid, seed or period changes.
  - **Contacts with the real data since the last entry.** The five whys ran from the clean Windows clone at `5f17a76`, on Report n°2's Windows re-run (`03916fda…`), each call with `--test-months`. Every answer is exploratory.
    7. Question 2's two `series` calls, at 07:42:06 and 07:42:20 UTC (lines 1 and 2 of `CONTACTS.log`).
    8. Question 3's `sample`, from 07:42:30 UTC (line 3). It stopped at 08:02 on the Matrix-free twin's loud check and printed no result (below).
    9. Question 5's `why` at its ten rows, at 08:03 UTC (lines 4 to 13). A line of the log names the arm and the hour, not the pair, so BTCUSDT's and ETHUSDT's rows at one hour read alike.
    10. Question 1's `series`, at 08:06:59 UTC (line 14), then its `why` at the four rows picked by the fixed rule, for both arms, from 08:07 to 08:10 UTC (lines 15 to 22). A first `series --top 100` was refused before it read anything, since `--top` takes 1 to 50. The rows were picked from the top 50.
    11. The diagnosis of the twin's failure, below: `why` at the failing row, at 08:12:04 UTC (line 23), then five probes from 08:18 to 08:35 UTC. The probes rebuilt Matrix through 2024-12-26, formed an exact reference at that row, and ran the twin at 133 values of `as_of` from 2024-11-29 to 2024-12-31. Their copies of the data were deleted at 08:35.
    12. Question 3's `sample` again, whole, from 08:41:59 to 09:02 UTC (line 24), with OpenMP, OpenBLAS and MKL at one thread. Every check passed on all 1,000 rows, and the twin's largest gap was 4 × 10⁻⁶ of its bound.
  - **The twin's failure at one row.** At SUIUSDT's row decided at 2024-12-26T10:59:59.999Z, window all, ρ = 10⁻⁴, over 1,587,472 entries, the twin's `fwd_return` was 0.0012707678705418557 and the core's 0.0012707731610964704. The gap, 5.29 × 10⁻⁹, exceeded its bound, 2.67 × 10⁻⁹.
    - **The core is exact there.** A reference computed in exact rational arithmetic gives the core's four outputs within 5 × 10⁻¹⁷.
    - **The twin's error did not reproduce.** Re-run at one BLAS thread, the twin gives the four outputs within 4 × 10⁻¹⁶ of the reference. It stays within its bound at all 133 values of `as_of` from 2024-11-29 to 2024-12-31, and at that row in a new `why` call.
    - **Its cause is not identified.** The suspects are OpenBLAS's multithreaded products on a loaded machine and a transient hardware fault. No single bit flip in the twin's Gram matrix reproduces the failing value exactly.
    - **No scored forecast is in question.** The forecasts are the core's, computed in Rust, and Report n°2's `--check` reproduced `series.npz` byte for byte.
    - **What is done.** The third why runs again, whole, and every later `explain` call runs with BLAS at one thread. The twin and its bound do not change: the check did its job.
  - **Audit pass 4g, second look**, on `explain head`'s fixes: GO for the commit and for the first call on Report n°3's checkpoints. No Blocker, no Major and no Minor point; three Nits, logged.
    - **The audit's bolder check is not built in iteration 4**, since it cannot be built without loosening a guard. It would hold the recomputed forecasts, ensembled as the fits ensemble them, to Report n°3's `series.npz` to the bit. The only reader of `series.npz` without pickles is `power.load_series`, which requires `report2.json` beside the file. A second reader in `head` would trip the protocol tests' rules on zip archives and binary loads. The chain of identity therefore ends at the part's record in `report3.json`, and Report n°3's score stage, audited in pass 4f, maps the parts to its series. The check stays for iteration 5, through a `report_file` argument on `power.load_series`.
    - **How `head` runs.** In WSL2, with the fits' build of torch, CUDA and cuDNN, after Report n°3's score stage has written `report3.json`, and with OpenMP, OpenBLAS and MKL at one thread. On CUDA the fits record no CPU thread count. The memory's readout on the CPU is bit-identical at 1, 2, 4 and 6 threads (audit pass 4e). The first call asks one seed at one row.
- 2026-10-30, after audit pass 4h on LFM3's ablations and H6, before any ablation fit on real data. `runs/explain/CONTACTS.log` holds 24 lines at this entry. No registered rule, statistic, threshold, grid, seed or period changes. The build's readings are recorded, and one control with no verdict is added beside H6.
  - **Contacts with the real data since the last entry**, from clean clones at `5f17a76`:
    13. Report n°3's 54 fits, on the GPU in WSL2, from 09:00:54 UTC, from `~/ols-prime-r3`. They read the panel through 2024-12 and Report n°2's WSL2 series (`691e7ea7…`), and fit the yearly models 2019 to 2024. No score is computed before the score stage.
    14. The power study's second run, for byte identity, on Windows, from 09:05:23 to 09:10:17 UTC. It read Report n°2's series `03916fda…` by its digest, then stopped when its worker pool failed at start-up, before any output. It is not re-run in iteration 4: the study gives the same bytes for every worker count (audit pass 4c), and the week's budget goes to Report n°3.
  - **The ablations, as built.** Audit pass 4h accepted each of the build's readings.
    - **`enc-ols-gate`.** σ(x W_g), with x = LN1(x), the block's normalized input.
      - W_g is a 32 × 32 map without bias. Its slice h gates head h's 8 outputs, before the output projection.
      - It takes weight decay.
      - It is drawn after every module of `enc-ols`.
    - **`enc-ols-conv`.** The first block's attention becomes out(σ(x W_g) ⊙ conv3(x W_u + b_u)), with x the block's normalized input.
      - The value map and the output projection have a bias. The gate and the kernel have none, since b_u already offsets each channel.
      - The convolution is depthwise and causal, of width 3, zero-padded on the left.
      - The kernel is drawn U(±1/√3), as `nn.Conv1d` draws a depthwise kernel.
      - It is computed as shifted products, not with cuDNN, for determinism.
      - The arm needs n_layers ≥ 2. The second block keeps its OLS attention.
      - **The kernel takes no weight decay. This is the build's choice, not a consequence of the protocol:** a depthwise kernel is a linear map, and AdamW usually decays a `Conv1d`. It is immaterial (96 parameters) and recorded as a choice.
    - **`enc-ols-brier`.** The loss is the cross-entropy plus Σ_k (p_k − 1{y=k})², the form the scores use, in [0, 2].
      - The Brier term is taken on the softmax before the floor, averaged over the episode's rows, with weight 1.
      - The epoch kept is still chosen by the slice's log-loss.
    - **Shared by all three.**
      - Each arm is built as `enc-ols`, then changed. Under one seed it starts from `enc-ols`'s initial weights for every module they share, and draws the same episode order.
      - `EncoderConfig` and `FitConfig` gain no field, so their JSON is unchanged. A subclass, `BrierFitConfig`, alone carries `brier_weight`.
    - **Parameters.** `enc-ols` 21,003; `enc-ols-gate` 23,051 (+2,048); `enc-ols-conv` 20,007 (−996); `enc-ols-brier` 21,003. Each count holds both by the closed form and by counting the built models.
  - **H6, as computed.**
    - The ECE is `stats.ece` on the ensemble's floored forecasts over the scored rows.
    - **The ratio's bootstrap.**
      - Hours are resampled jointly for both arms.
      - Each replicate's ECE is rebuilt exactly from per-hour bin sums: count, sum of confidences and sum of hits. They are cross-checked against `stats.ece`.
      - The block is the larger of the two arms' Politis-White blocks of their hourly Brier scores.
      - The seed is `_seed(rcfg, "ece_ratio", "enc-ols-brier", "enc-ols")`, and `n_boot` is Report n°2's.
    - **"The 95 % upper bound" is the bootstrap's one-sided 95th percentile**, as for H4's bound.
      - The two-sided interval and both ECEs are reported beside it.
      - A bound that is not a number never passes.
      - The condition reads the ratio the report prints.
    - **The log-loss condition is inclusive (≤)**, on the difference `enc-ols-brier` − `enc-ols`, with Diebold-Mariano at 23 lags and HLN. If the test is undefined (the same difference at every hour), the tolerance is the seed range alone.
  - **The registered run.**
    - The arms are fitted and scored in the protocol's order, as a prefix of it.
    - Every fit runs on CUDA, in one build equal to Report n°3's, driver included.
    - The fits cannot share Report n°3's code digest, since that code predates the ablations. They are bound to it by the data's digests:
      - `series.npz`;
      - `report3.json`;
      - each of Report n°3's parts: its `fit_sha256`, `forecast_sha256`, `forecast_rows` and `kept_epoch`.
    - The score rebuilds Report n°3's series from the bound parts and requires its digest. `np.log`'s last bits differ between Windows and WSL2, so the score stage runs in WSL2, like Report n°3's.
    - **After audit pass 4h's Major point, the score takes stock of every arm in the run folder.**
      - An arm fitted in full must be scored.
      - An arm fitted in part is reported as such, with its count of parts, and is not scored.
      - Only an arm with no part is reported as not run.
    - **Variants.** 21 before, plus one for each ablation scored. An arm fitted in part is never scored, so it is not a variant.
  - **Evidence before any fit on real data.**
    - **On the CPU.** Old code (`ece1950`) against new: the checkpoints and forecasts of `enc-ols`, `enc-softmax`, `enc-linear`, `cheat-stamp` and `cheat-value` are byte-identical, 11 files of 11. The build found it, and the audit reproduced it on its own run.
    - **On the RTX 3060**, from 09:51:58 to 10:05:27 UTC:
      - the same 11 files of 11 are identical;
      - each ablation, fitted twice, is identical;
      - then a synthetic Report n°3, the ablations against it, and `--check`, which passed.
    - **The Windows suite:** 1,539 passed, 4 skipped.
  - **The prior on H6, an analysis and not a result.** Near uniform forecasts, the Brier term's gradient in the logits is 2/3 of the cross-entropy's, in nearly the same direction. AdamW is nearly invariant to the gradient's scale, so CE + Brier ≈ CE at first order, and H6 is expected to be close to a null.
    - **The audit's probe.** The ratio of the two gradients' norms and their cosine:
      - at logits of scale 0.05: 0.666 and 0.9996;
      - at scale 1: 0.57 and 0.90;
      - at scale 4: 0.30 and 0.54.
    - **Its caveat.** AdamW is invariant to a constant gradient scale, not to the clipping at norm 1, which rescales step by step. A gradient 5/3 larger is clipped on more steps.
    - **The GPU smoke agrees.** `enc-ols-brier`'s per-seed log-losses differ from `enc-ols`'s by 1 to 2 × 10⁻⁵, and the epochs kept are the same (4, 5 and 6).
    - **An observation on the rule, kept as registered.** On the synthetic smoke, the log-loss tolerance came from the seed range (5.4 × 10⁻³), 500 times the Diebold-Mariano standard error (1.1 × 10⁻⁵). On the real panel the seed range will very likely dominate too, which makes the log-loss condition lenient. The ECE condition carries H6.
  - **Audit pass 4h.** No Blocker, one Major point, six Minor points and six Nits. GO, with the Major point fixed before the real score stage and the Minor points before the commit. The fixes were made in the working tree the same day. By the engineer's account, every plant the suite had missed now fails a named test. Neither the orchestrator's verification nor the audit's second look has seen them yet.
    - **The Major point.** A fitted arm could be reported as not run by a run that called itself registered: all 54 fits, then a score of two arms, gave "H6 not run". The fix is the stock-taking above. The fits stage also refuses an arm list that is not a prefix of the protocol's order, unless every part of each earlier arm is sealed.
    - **Five Minor points were test gaps.** The code was right, but the suite could not tell:
      - the Brier term before the floor;
      - the Brier arm's early-stopping statistic;
      - the inclusive log-loss condition;
      - the block-length rule;
      - the two guards that bind the numbers to Report n°3's series.
    - **The sixth Minor point.** Report n°3's checkpoint reader could not rebuild a `BrierFitConfig`. Its fix reads a config that carries `brier_weight` as a `BrierFitConfig`, and every other config as before.
    - **The Nits.**
      - The WSL2-bound score is stated in its refusal.
      - The ECE condition reads the printed ratio.
      - A docstring names the binding check that does the work.
      - The kernel's decay and the lenient log-loss condition are recorded above.
  - **A control with no verdict, beside H6: its ECE condition on two seeds of one model.** It comes from the audit's bolder check.
    - **What it measures.** How far seed noise alone moves the ECE ratio. It needs no new fit.
    - **What it computes.** For each of the six ordered pairs (i, j) of Report n°3's `enc-ols` seeds, each seed's forecasts are floored on their own, as its per-seed log-loss floors them, over the scored rows. Then:
      - ECE_i and ECE_j;
      - the ratio ECE_i / ECE_j and its paired bootstrap, by H6's own machinery and block rule, with the seed `_seed(rcfg, "ece_ratio", "enc-ols seed i", "enc-ols seed j")`;
      - its two-sided 95 % interval and its 95th percentile;
      - whether H6's ECE condition holds for i against j.
    - **The log-loss condition is not applied.** Two seeds of one model differ by at most the seed range, by construction.
    - **How to read it, fixed before the run.**
      - H6 compares 3-seed ensembles, whose seed noise is smaller than one seed's.
      - If the ECE condition holds for any ordered pair, H6's verdict is reported with that fact beside it: one seed's luck can meet the ECE condition.
      - The control never changes H6's verdict, and it is not a variant.
    - **The audit's positive control**, forecasts sharpened with a temperature of 0.7, is a test on synthetic data and does not run on the real panel.
  - **The ablations stop here in iteration 4, for the week's budget.**
    - **What is not done.** They are not fitted, and H6 is reported as not run.
    - **What moves to iteration 5:**
      - the verification of the fixes and the audit's second look;
      - the ablations' 54 fits, their score and the seed-split control, as registered above;
      - `explain head`, which is built and audited but not called in iteration 4.
    - **What runs unattended** (`runs/2026-10-30-chain.log`):
      - the panel H1, resumed with the same folder if it reaches its 16-hour timeout;
      - then Report n°3's timing, Matrix timing, score and `--check`, at `5f17a76`, once both GPU jobs have ended.
- 2026-10-31, after the official runs of iteration 4, before the results audit. `runs/explain/CONTACTS.log` holds 24 lines at this entry. No registered rule, statistic, threshold, grid, seed or period changes.
  - **Contacts with the real data since the last entry**, from the clean clone `~/ols-prime-r3` at `5f17a76`:
    15. Report n°3's timing, 2026-10-31 from 00:31:25 to 00:36:59 UTC; its Matrix timing to 00:40:39; its score to 00:43:03; its `--check`, first refused for missing arguments at 00:43:06 with no data read, then run from 00:44:18 to 00:46:52.
    16. The panel H1's resume, from 23:39:23 UTC on 2026-10-30 to 00:30:02 on 2026-10-31, with the same folder, from `~/ols-prime-official`. It belongs to contact 4.
    17. H13's timing repeated on the real rows, twice, on 2026-10-31 from 17:02:02 to 17:08:06 and from 17:09:00 to 17:14:01 UTC. Each read the panel through 2024-12 and Report n°2's WSL2 series, on a copy of Report n°3's parts. No score was computed, and no fit ran.
  - **H13's timing measured the timing stage's own GPU cache.** Report n°3's ratio, 0.4031, met every condition the protocol names, and the protocol names no state of the GPU's memory. `report-3.md` stays as it is, as the run's file.
    - **The sign.** Synthetic rows gave 1.06 at wave 1 and in the smokes, on the same code. `enc-softmax`'s operator was 10 times slower on real rows, `enc-ols`'s 1.4 times, and `enc-linear`'s unchanged.
    - **The cause.** `EncoderTimer` keys the memory over the panel's entries before the protocol. On the real panel that leaves torch's cache at 12,926 MiB reserved, on a card of 12,288 MiB, with 260 MiB allocated. On the synthetic panel, the card's used memory, every process included, peaks at about 4,300 MiB.
    - **The evidence.** On the same 12,288 rows, the ratio is 0.3739 as the code stands and 1.0732 with `torch.cuda.empty_cache()` before each protocol call. Emptied, the three operators fall to their synthetic times. The memory clock stays at 7,301 MHz in both repeats, so the state of the clocks does not explain it. The mechanism by which a full cache slows the operators is not measured.
    - **The reading: no verdict, the measurement is invalid.** The rule's arithmetic gives 0.4031 ≤ 0.9, but the number measures the stage's cache, not the arms. H1's cuts already treat a quantity that cannot be measured this way: it is reported and left out of the verdict, and it never counts as a pass. The diagnosis was triggered by the gap with a reference on record before the run, 1.06, not by the sign of the result. So `docs/RESULTS.md` records no verdict for H13, and says that OLS attention is not shown to be cheaper to run. The GPU wall times of the cost table carry the same artefact. H4 and H5 read no timing; the fits, the forecasts, the peak memories and the Matrix timing are unaffected.
    - **For iteration 5, before any re-measure.** The timing stage empties the cache before each protocol call and records the reserved memory, the card's total and the clocks. The bound stays 0.9. The re-measure is a new registered measurement under the amended conditions; its result is recorded whatever it is, with the note that 1.07 had been seen before it ran. A new kernel is a new variant, with its own registration.
- 2026-11-18, before any detector of iteration 5 runs on a leak of the confirmatory population (seed 20261118) and before any new detector runs on real bars. New section "Leak detectors measured against each other (iteration 5)", from the draft audited in pass 5a (register with fixes: 2 Blockers, 10 Major, 11 Minor, 4 Nits) and pass 5a-bis (register with fixes: no Blocker, 7 Major, 11 Minor), every finding fixed or logged; 5a-bis's replacement texts adopted verbatim. H15 is registered in `docs/HYPOTHESES.md`.
  - **Contacts with the real bars for this design.**
    - Pass 5a's auditor read counts from two recorded outputs, `runs/2026-10-29-h1-adversary/adversary.json` and `runs/2026-10-30-twins/twins.json`.
    - The orchestrator computed the quantile table (§1.4, §1.5) from the BTCUSDT and ETHUSDT daily bars with `open_time` before 2019-01-01, through the seal, on 2026-11-18 at 20:32 UTC: `.claude/briefs/iteration-5/quantile_table.py`, output `runs/2026-11-18-quantile-table/` (`table.json`, SHA-256 `527e01ba7028fb5666e694fcadd5b22d2fdea31718d96e53d98a29e383183c43`, and `summary.json`). 502 rows per pair, none of them scored. Pooling, the levels and the pre-2019 rows were written in v1 at `8473776`, and the treatment of zeros and the band shares were asked by pass 5a at the same commit. That `method="linear"` was chosen before the read, and that the table was computed once, is not verifiable from any commit. Nothing in the placement was changed after the read.
    - Pass 5a-bis's auditor read `summary.json` and hashed `table.json`.
  - **Seeds.** 20261118, 51118, 20261119, 51119 and 20261120 have never been run.
  - **Deviations from the brief** (`.claude/briefs/iteration-5/prereg.md`, committed 2026-11-18): the primary analysis holds every detector to H1's 16 cuts, and the brief's sampled dates become the secondary schedule; the brief's truncation one bar later is freqtrade's comparison, TRUNC-1, a date-shift replicate (§2.3); "the union beats the best single detector" and "no detector flags more than 0.1 % of the honest twins" are dropped (§5).
  - **Standing promises of iteration 4's section, dated now.** H1's extreme-shape cut, deferred to iteration 5, is among the items `docs/ITERATIONS.md` drops first, and has not run. H14 stays planned for iteration 5 if time remains, and has not run.
  - **Open, by a later dated line before audit pass 5b's GO:** the development population's digest (§1.7).
- 2026-11-19, before audit pass 5b's GO and before any run on seed 20261118. **The development population's digest (§1.7).** Seed 51118, n = 10,000, `placement="quantile"`, the registered table: SHA-256 `e03f78b187c1f7a7b62681a6c16214f7bd79d7f13b58459521cacb731ad9bc48`, numpy 2.5.4, computed by `python -m olsprime.bench.detectors digest --seed 51118 --placement quantile --table ../runs/2026-11-18-quantile-table/table.json`. **Commit:** the wave-3 tree on top of `6044037`, not yet committed when this line was written; the commit is named by a later dated line, before any official run. **Beyond §1.7's list, stated for pass 5b:** the digest was computed on Windows 11 (AMD64, Python 3.12.10). The same code gives another digest in WSL2 (Ubuntu, numpy 2.5.4, Python 3.12.14): `exp` and `log` differ by one ulp between the Windows C runtime and glibc, so numpy's version alone does not pin it. Pass 5b rules on this; §1.7 says the digest is reproduced on the machine of the official run.
- 2026-11-19, after audit pass 5b (GO with fixes, no Blocker; 4 Major, 12 Minor, 5 Nits) and before the frozen commit, before any detector runs on real bars and before any run on seed 20261118. The findings are `.claude/briefs/iteration-5/audit-5b-findings.md`; the fixes, `fixes.md` and `fixes-progress.md` in the same folder. Pass 5b-bis re-reads the diff of the fixes, and the development digest is reproduced on Windows at the frozen commit. Where this line and an item above disagree, this line is normative.
  - **The commit of the previous line:** `6ab7e3e`, the wave-3 tree that pass 5b audited (code digest `8607e7c4edb6c3dd30d332871958d185df0fa4308a9c3994e8811e70837a7c19`, 88 files). The official runs use the frozen commit, which contains the fixes below and is named by the next dated line.
  - **§3.3's predictions, replaced** (pass 5b, Minors 5 and 6):
    - **FI on M2 is three-valued.** At a cut where bar `t + 1`'s high is at least two thirds of bar `t`'s close (`high[t+1] ≥ 2/3 · close[t]`, the boundary included), FI must flag M2: asserted. At every other cut the verdict is "not predicted": the ×3 run sets bar `t + 1`'s low to `max(1.5 × the highest high of bars t−90..t, 3 × high[t+1])` (`perturb.py`), so the window's high alone can lift `close[t+1]` above twice `close[t]`, and the registered "unless" half was wrong. Those cuts are counted, with FI's flags among them, under `reported.classes["M2 FI <schedule>"]` (`predicted_flagged`, `not_predicted`, `flagged_where_not_predicted`), never asserted. As at `6ab7e3e`, FI's rule is checked on M2, not on its mirror.
    - **M1.** Under conventions G and M, no detector may flag M1 at any cut (unchanged). Under P, where a node with a missing operand is missing, the gate included, TRUNC-0 and TRUNC-1 (H1's cuts and the long schedule) and ENDS and RETILE (every end) must flag M1 at every cut, except a cut whose truncation point is the series' last row (`t` for TRUNC-0, `t + 1` for TRUNC-1, the end `e` for ENDS and RETILE): there the truncation removes no bar, so it cannot flag and must not. Such cuts are found from the cut lists, never from the flags, and counted apart as `cannot_flag_last_row`, under `reported.classes["M1 <schedule> under P"][detector]`; the synthetic bars have none, and the count on the real bars is unknown until the run. A missed flag and a flag at such a cut are both disagreements.
    - **§3.4, corrected:** item 3's verdicts on M2 depend on the bars (FI's rule reads `high[t+1]` and `close[t]`), so they are not identities of IEEE arithmetic or of the code. They still follow the stop rule: a disagreement stops the run, and is a finding to explain.
  - **Metrics now implemented** (pass 5b, Minors 7 and 8):
    - **§4.4's sensitivity, "ignores outputs that turn missing".** For every variant reported at H1's 16 cuts (RETILE and ENDS at their ends), the any-cut share under a second catch rule: a scored compared row counts only where, for some output, both values are finite and differ by more than 1e-9; a change of missingness alone never counts. It is reported under the three denominators of §4.6, as `metrics.ignores_outputs_that_turn_missing` and in its own section of `detectors.md`, and is never called "through a changed value", which stays the read split's own row-level label. It decides nothing.
    - **§4.6's three denominators** (all leaks; not constant at H1's compared rows; `designed: no`) now apply to every share of §4.1 to §4.5: the any-cut share and the mean per-cut rate (as before), the families, the `position` strata, the first-m-cuts curve, the conventions and their sentence, and the sensitivity above. The read split is summed over each denominator's leaks. In `detectors.json`, under `metrics`: `detectors[variant].by_family[denominator][family]` and `.by_position[denominator][stratum]`; `first_m_cuts[detector][denominator]`; `read_split[denominator][row]`; `conventions[detector][denominator][convention]` and `conventions.sentence[denominator]`; `ignores_outputs_that_turn_missing[variant][denominator]`. H15's deciding cell is unchanged.
  - **The registered command lines** (pass 5b, Minor 12). Run from `python/`, on Windows 11 AMD64, in the environment of the next line, through `.claude/briefs/iteration-5/wave4.py`, which stops at the first failure. Before item 1, it refuses a date on which an earlier attempt left any file, checks the platform and the frozen code digest, logs HEAD, and runs the `digest` command, which must print the registered development digest before any bar is read (the next line, as amended after pass 5b-bis):
    1. **§1.3's replay:** `python -m olsprime.bench.adversary --n 10000 --workers 8`, H1's adversary on seed 20261029, `h1-bands`, as run in iteration 3 (allowed by §7.1). **The comparison** (Minor 13): its `adversary.json` must equal `runs/2026-10-29-h1-adversary/adversary.json` on every top-level key but `provenance`, which holds the commit, the code digest and the data manifest's digest (`wave4.py` logs both manifest digests); both are parsed, `provenance` is removed, and the two are re-serialised with sorted keys and an indent of 2, then compared byte for byte. A difference stops wave 4.
    2. **The descriptive run:** `python -m olsprime.bench.detectors run --seed 20261029 --placement h1-bands --two-run-seed 29119 --bootstrap-seed 29120 --n 10000 --table ../runs/2026-11-18-quantile-table/table.json --workers 8`. **Seeds 29119 (TWO-RUN) and 29120 (cut-date bootstrap) are new**, chosen now, before any run with them; they serve the descriptive run only, and no other seed of §8 is reused. §8 named no TWO-RUN or bootstrap seed for the descriptive run: this item adds them.
    3. **The confirmatory run:** `python -m olsprime.bench.detectors run --seed 20261118 --placement quantile --two-run-seed 20261119 --bootstrap-seed 20261120 --n 10000 --table ../runs/2026-11-18-quantile-table/table.json --workers 8`, made only if the descriptive run exits with every assertion and gate passed (§7.3).
    4. **The identity rerun:** the confirmatory command with `--workers 4` and another output folder. Every output file but `run.json` (which holds the wall clock and the worker count) must be equal byte for byte. The `provenance` blocks are equal because `wave4.py` stops unless the output of every step records the commit and the code digest of its step 0; so nothing is committed, and nothing under the code digest's globs is edited, while wave 4 runs.
    - **The CLI enforces these lines** (pass 5b, M2), by a guard on the parsed arguments called before anything else (`registered_line_refusal`). It compares the population seed, the placement, the TWO-RUN seed, the bootstrap seed, `--n` and whether the bars are synthetic. It refuses seed 20261118 unless those are item 3's and the bars are real, refuses 20261119 and 20261120 in any other role, refuses seed 20261029 on real bars unless those are item 2's, and refuses real bars with any other population seed. `--workers` and `--out` are free: the identity rerun changes the first. `--table` must be given on every real-bar run, whatever the placement, because the platform pin needs it (next line); its path is free, but the file must hash to the registered table (`load_table`), or the run is refused before any bar is read; under `h1-bands` the table serves the pin only, and the generator does not receive it. The `digest` command refuses all three confirmatory seeds. Synthetic bars take any other seed, 29119 and 29120 included.
  - **The platform** (pass 5b, M1). On real bars, the `run` command (`main`; the function `detectors.run()`, called from Python, has neither the pin nor the guard) loads the registered table and regenerates the development population (seed 51118, n = 10,000, `quantile`) before it reads any bar, and refuses unless its digest equals `e03f78b1…bc48`; `detectors.json` records the result under `platform_pin`. Synthetic runs skip the pin. `detectors.json` and `run.json` record `platform.system()`, `platform.machine()`, the Python version and numpy's.
  - **Phase 2 can recompute the numbers** (pass 5b, M4):
    - `h15.qualifier.cells` holds both qualifier cells, convention M and the not-constant denominator, each with its paired 2×2 table, its difference and its Newcombe interval, beside `triggered_by`. The deciding cell carries its table too.
    - **The per-leak file, `verdicts.jsonl`,** is written beside `detectors.json` only when every assertion and gate passes, and is absent otherwise (§7.4). Its first line is a JSON header: the format (`olsprime-detector-verdicts/1`), the fields, the encoding, the cuts of each schedule (H1's, the long schedule's, RETILE's ends), the bit layout, every registered variant as an OR over named run columns of one raw key, the configuration, and what the file does not hold. Each following line is one leak, in id order: its id, family, output, `designed`, `position`, the placement-invariant flag and the two constancy flags, then three bit vectors as the hex of `numpy.packbits` in little bit order:
      - `flags`, every raw cut-by-run verdict of every detector, convention and schedule under H1's catch rule;
      - `finite`, the same under the sensitivity rule above;
      - `mirror`, the mirror leak's verdicts at H1's cuts and RETILE's ends under G, or null when the root is not a single comparison.
    - The file is deterministic, and the identity rerun compares it byte for byte. Every metric that is a function of per-leak cut verdicts and tags can be recomputed from it alone, and the tests do so. The read split (row level), the count of distinct expressions, the assertions, the gates, the controls and TWO-RUN's repair statistics are in `detectors.json` only.
  - **Narrowings of the implementation, ruled faithful by pass 5b and logged now** (ruling 2):
    - Newcombe's interval (§4.7) takes its correlation estimate ψ as Fagerland, Lydersen and Laake implement method 10 (the R package `contingencytables`, `Newcombe_square_and_add_CI_paired_2x2`, pinned on their worked example), not from a re-reading of the 1998 paper; pass 5b found the difference immaterial (at most 0.001 point at n = 10,000, 0.003 on an extreme table). If a limit falls within 0.003 point of 0 or of −1, the paper says so.
    - The cut-date bootstrap's spread (§4.15) is the 97.5th percentile minus the 2.5th.
    - The cancelled controls (§3.2) do not run through RETILE.
    - The read split (§4.4) is counted at row level.
    - On a zero-volume bar, TWO-RUN (§2.5) keeps every volume, quote volume, taker volume and trade count at 0; it now raises `RepairFailed` if such a bar holds a non-zero value in any of them (Minor 14).
  - **Code brought to the registered text** (no rule changes): the long schedule's class of §4.11 is the union of FI, TRUNC-0 (G), TRUNC-1 (G) and TWO-RUN (σ = 0.1, 2 runs) on the long schedule only (Minor 9); the read split has a row for TWO-RUN's primary arm (Minor 10); the cut-date bootstrap asserts 64 distinct dates shared by both pairs before it runs (Minor 11); the controls' "can be flagged" count is taken over H1's 16 cuts (nit). An empty set writes null, never NaN, in every share, mean, paired difference and Newcombe cell, and an empty qualifier cell cannot trigger H15's qualifier; none of these is reachable at n = 10,000 (the nit on `share(k, 0)`, carried further; pass 5b-bis, N3).
  - **§3.2's prediction is not an independent implementation** (Minor 15). It shares the expression evaluator and the bench with the detectors; only its comparison is its own. Wherever §3.2's agreement is reported, it is called a code-level prediction.
  - **The case study's choices, fixed before its one real call** (Minor 16, ruling 2), as `python/olsprime/bench/casestudy.py` states them at `6ab7e3e`:
    - **The regressors are payoffs, not signal levels.** The brief (`case-study.md`) says "signals"; the code regresses the loss differences on each strategy's hourly payoff, its position times the row's realized forward return, averaged over the hour's scored rows, consistent with Nagel's control. Because a payoff contains the realized return, the regression is an **attribution after the fact**, not a test that the signals predicted the difference, and the case study says so.
    - **The signal definitions were fixed by the implementing agent** in wave 3, from bars up to the decision bar `t`, with `r_s = ln(c_s / c_{s−1})`: reversal `−r_t`; momentum `ln(c_{t−1} / c_{t−25})` (24 hours, skipping the last); volatility-timed momentum (after Nagel), the momentum position divided by `24 · v_t`, with `v_t` the uncentred mean of `r_s²` over the last 90 hours, and 0 where `v_t = 0`.
    - **HAC:** Newey-West, Bartlett kernel, 168 lags (one week of hours), fixed for every regression, not chosen from the data.
  - **Not examined before the official runs** (pass 5b, "not covered"): whether any real cut has a next-day high below two thirds of the close, a close above twice the previous one, or a zero-volume bar. The official runs' assertions will meet them as they are.
- 2026-11-19, after audit pass 5b-bis (GO with fixes, no Blocker; 1 Major, 3 Minor, 9 Nits; `.claude/briefs/iteration-5/audit-5b-bis-findings.md`), before any detector runs on real bars and before any run on seed 20261118. **The frozen commit** (pass 5b's ruling 1, verbatim):
  - The frozen commit is `b71ba654ff7060ff7f835f8c3325cbd073eddaa9`. On it, on Windows 11 (AMD64), CPython 3.12.10, numpy 2.5.4, the development digest is `e03f78b1…bc48`; pass 5b reproduced it on the wave-3 tree (code digest `8607e7c4…`). The exact digest, hence the exact population of a seed, depends on the platform's `exp`. The three official runs are made in that environment, and `run` refuses unless the development digest reproduces. `table.json` can be read from WSL2; WSL2 is not the machine of the official run. The WSL2 digest and the 12-digit digest are diagnostics and pin nothing.
  - **Pass 5b-bis reproduced it at the frozen commit:** the development digest `e03f78b1…bc48`; the full suite, 1,743 passed and 5 skipped; the mutant test, 16 of 16 killed. The run path (`detectors.py`, `detector_stats.py`) needed no change after pass 5b-bis.
  - **The code digest** (pass 5b-bis, Minor 2). The commit's SHA is the identity of the frozen code. `3b59007a8111cc858bf01e15d7ed6636775903cbabce484ea3ac3b483ab4d5e5` (88 files) is the code digest of the Windows working tree that runs wave 4, with its mixed line endings (CRLF in 64 of the 88 hashed files, LF in 24), and `wave4.py` checks it at its step 0. A clone with LF line endings, as on Linux or GitHub, gives `3778cfcadb7d9cca4355b95d60896856ce6e1fcc9b23bd69671acb87c9c072c3`; an all-CRLF Windows clone gives `77851c2e9d1ffeafa11f50350ad5453d7e816075e79f5efe72b97167d37e14aa`. Both were recomputed from the commit's blobs by the orchestrator. No clone gives `3b59007a…`. Normalising line endings inside `code_digest` is for a later iteration.
  - **The commit the official outputs record.** HEAD when wave 4 starts is the commit that carries this line. From `b71ba65` it changes no file under the code digest's globs: only `docs/` and `.claude/briefs/`. Every output's `provenance` records that commit and the frozen code digest. Nothing is committed, and nothing under `python/` or `crates/` is edited, until wave 4 ends.
  - **`wave4.py`, amended after pass 5b-bis** (outside the code digest). Its first step refuses a date on which an earlier attempt left a log, an `.out` file or an output folder (Minor 1): a new attempt takes another `--date`, and is reported as run after a stopped attempt (§7.4). It logs HEAD. Before the replay, it runs the `digest` command and stops unless the printed digest is the registered one (N5). After each step it stops unless the output exists and its `provenance` records step 0's commit and code digest (Major 1, N4). The OK line of §1.3's replay logs both data manifest digests (N2). It passes each registered command line in the dated line's order (N9). The child processes write UTF-8 (`PYTHONUTF8=1`). The auditor's dry run, `audit-5b-bis-scripts/y2_wave4_dry.py`, runs to its last line on the amended file: scenario L is "refused at the start", and scenario M is "stopped".
  - **Logged, not fixed before wave 4:**
    - **Minor 3.** Five mutants planted in the fix wave's own code survive the detector tests: the count of M1's disagreements under P, a missed flag under P, FI's assertion on M2, the primary TWO-RUN arm's read-split row, and `can_flag` over every cut. The frozen code is right on all five. The tests that kill them, and the five mutants, are added after wave 4 (tests only, outside the code digest), and the kill count of all 21 is reported beside the 16.
    - **N6.** `write` puts `verdicts.jsonl` and `detectors.json` on disk before it renders the Markdown.
    - **N7.** The mutant harness copies files and runs pytest through a process pool, which avoids two patterns of the seal's scanner instead of asking for an allow-list rule. A later iteration either names that allowance or widens the scanner.
    - **N8.** An independent reader of `verdicts.jsonl`, the auditor's Y3, agrees with `detectors.json` on 1,012 shares and cells at n = 200 and at n = 10,000. It may become a test.
    - **N9.** `metrics.long_schedule` keeps its shares under "all leaks" only. The per-leak file lets phase 2 compute the other two denominators.
- 2026-11-19, after wave 4 and before audit phase 2. **Wave 4's contacts with the real bars** (UTC, from `runs/2026-11-19-wave4.log`, SHA-256 `29ba4fb1fc914fda097179d6f1afd65348d4bc0db0d18dfe723271e44fcd5cd4`). The runs were made on Windows 11 AMD64, CPython 3.12.10, numpy 2.5.4, through `wave4.py --frozen-digest 3b59007a…`, at HEAD `f12b9b5`, the commit that names the frozen one. Every output records that commit and code digest `3b59007a…`. Nothing was committed or edited under `python/` or `crates/` during the runs.
  - **15:17:40–15:17:44, step 0b.** The `digest` command printed `e03f78b1…bc48`. No bar was read.
  - **15:17:44–15:21:02, §1.3's replay.** `adversary.json` (SHA-256 `a5b71eb4ec0a2affcaee211ef07dbce027377bda251d0e039e3eda1c6494fcc0`) equals iteration 3's on every key but `provenance`. The data manifest digest is the same, `0ee7ac0f…`.
  - **15:21:02–15:32:05, the descriptive run** (seed 20261029, `h1-bands`, TWO-RUN 29119, bootstrap 29120). Exit 0; every assertion and gate passed, and the platform pin was checked. `detectors.json` `0b4b06f435ddba3d7d562207b6e927cd119a7d4b0f6f59b439d0cea4d10bb911`, `verdicts.jsonl` `f34327dbda2318762b43d4ebb316f36816673a6ed56aae1834fbfa965d526a3d`.
  - **15:32:05–15:43:01, the confirmatory run.** It is the first and only draw of seed 20261118 (`quantile`, TWO-RUN 20261119, bootstrap 20261120). Exit 0; every assertion and gate passed, and the platform pin was checked. `detectors.json` `09f9470e92413795daa985580c6b587e422244078dc7ec5856f5e5eb2ad02cdb`, `detectors.md` `98a050ee65ca9262c4d11c7557d34122de60d091d6f1a3aa6952936f230e1f9f`, `verdicts.jsonl` `9637561052f1804be48baa18374034f68c686d550f18c0bb0ec7080da8e2a38d`.
  - **15:43:01–15:59:29, the identity rerun** (`--workers 4`). Exit 0. `detectors.json`, `detectors.md` and `verdicts.jsonl` are equal to the confirmatory run's byte for byte; only `run.json` differs.
  - **Checked by the orchestrator after the runs.** The hashes above were recomputed. On both runs, every number that `verdicts.jsonl` determines was recomputed from it and agrees with `detectors.json` (`python -m tests.test_detector_verdicts <folder>`). The rates and H15's label go to `docs/RESULTS.md` only after audit phase 2 recomputes them. The stderr of every step holds no warning, traceback or `RepairFailed`.
  - **What the real bars held, among the items "not examined before the official runs"** (counts only, read from both runs' `reported.classes`):
    - no cut whose truncation point is the series' last row (`cannot_flag_last_row` 0 on every schedule);
    - no "not predicted" cut for FI on M2 (16 of 16 and 128 of 128 predicted, and flagged).
- 2026-11-19, after the case study's one real call and before audit phase 2. **The case study's contact with the data** (exploratory, test months; UTC, from `runs/2026-11-19-casestudy.log`, SHA-256 `125ad5d30e0ea4ed2815e08b923fabd7a1aee66bdf8532dd922c7e64d621f5da`).
  - **When and where.** 19:42:24–19:44:37, on Windows, at HEAD `1088aac`. That commit and the uncommitted changes of the moment touch docs and agent files only; the code digest was `3b59007a…` before and after the call.
  - **The command.** `python -m olsprime.bench.casestudy --report2 ../runs/2026-10-30-report2-wsl --report3 ../runs/2026-10-30-report3 --out ../runs/2026-11-19-casestudy`. Exit 0 in 128 s; it printed "registered inputs: True".
  - **What it read** (`run.json`):
    - Report n°2's `series.npz` `691e7ea7…` and Report n°3's `e8381799…`, the registered digests;
    - the hourly bars of their 233 pairs, through `load_klines`, cut to `known_at < 2025-01-01`.

    The vault's copy, `runs/vault/copy/series.npz`, was not passed on the command line. Audit phase 2 checks that it was not read.
  - **The outputs** (SHA-256):
    - `casestudy.json` `8d87294b0bf8ab26b364e04b339b36b064e63ca4731a29a38e78039665e2bcac`;
    - `casestudy.md` `7b308f10d9be1d19286bfadff57031e3de1269fc7a533d5934cb50a242f69653`;
    - `config.json` `ecc38cf2d8651b45540fa1eaa4cb77866f82c41074a9643ace321d6708e84277`;
    - `run.json` `36e24c7b4ec391e4ac537e6e106be9ff999d2df1a3f19c67e0b727cf319dea0c`.
  - **Not reported yet.** Its numbers go to `docs/RESULTS.md` only after audit phase 2 has read them. It was the only call; any other is a new contact, logged as such.
- 2026-11-19, after audit phase 2a. **Audit 2a (`leakage-auditor`, `.claude/briefs/iteration-5/audit-2a-findings.md`): GO with fixes.** No Blocker and no Major; 5 Minor and 8 Nits, all wording.
  - **What was recomputed.** 2,804 numbers of the two detector runs were recomputed from `verdicts.jsonl` by a reader that imports nothing from `olsprime`.
    - 2,795 agree. The 9 others are confirmatory-run rows under convention P, where the run clips at 1.0 the normal interval of a mean per-cut rate and the auditor does not.
    - The orchestrator re-ran the auditor's `a1_recompute.py` on both folders and got the same tables.
    - The case study: 382 checks, 0 failed.
  - **Corrections to the line "after wave 4 and before audit phase 2"** (N1). Its sentence on stderr is wrong as written.
    - Each detector step's stderr holds 26,700 log lines "fold … skipped: no test row", expected: 267 folds × 100 units of the truncation gate. The orchestrator counted them in `runs/2026-11-19-wave4-*.out`.
    - No step's stderr holds a Python warning, a traceback or `RepairFailed`.
  - **Corrections to the case study's contact line** (N7).
    - `load_klines` read the hourly rows of 2025, and `load_bars` dropped them before any computation.
    - The log holds no command line; the command is the one that line gives.
    - The auditor established that the vault was not read by path and by the seal's state: `power.run_output` refuses `runs/vault`, the manifest digest is the sealed one, and there is no `OPEN` or `ACCESS.log`.
  - **Minor 3 of pass 5b-bis: the deferral holds.**
    - The five lines read right at the frozen code. Lines 1016, 1018, 1031 and 1172 were also shown by behaviour on synthetic bars; line 1208 by reading only (N6).
    - Predicted counts equal flagged counts in both runs.
    - No registered sentence rests on a `check_classes` count that cannot be verified, except "and flagged" in "predicted, and flagged", which is the assertion's evidence (N5).
  - **The wording the rows and the paper must carry:**
    - H15's cell compares one run of TRUNC-0 with FI's two runs (×3 and ÷3). At one run each, TRUNC-0 is above FI ×3 alone and below FI ÷3 alone (Minor 1).
    - Under "date-dependent", the size moves but not the labels: they are the same in 2,000 of 2,000 subsets (Minor 2).
    - "By more than 1 point" is the label of one cell, all leaks under convention G. On the not-constant leaks the interval straddles −1, and convention P reverses the sign (Minor 3).
    - TWO-RUN's M2 class counts take any of 16 runs, both σ (Minor 4).
    - In the case study, the skill lies in "move or no move", and "share left ≈ 1" is not "zero loadings" (Minor 5).
    - Underflowed McNemar p-values are written "p < 10^-300" (N2).
    - P's mean per-cut rates are given without a normal interval (N3).
- 2026-11-19, after audit phase 2b. **Audit 2b (`leakage-auditor`, `.claude/briefs/iteration-5/audit-2b-findings.md`) gives GO with fixes.** There is no Blocker: 2 Major, 11 Minor and 21 Nits, all text and macros. No number is wrong, and no new contact with the data was needed.
  - **What it checked.**
    - The paper's 748 macros (draft 3): all checked, all agree, 352 of them against independently recomputed values.
    - `numbers.tex` regenerates byte for byte, and the draft compiles.
    - The five `docs/RESULTS.md` rows of 2026-11-19 agree with audit 2a's tables and `casestudy.json`.
  - **The two Majors were framing in FI's favour.**
    - **M1.** The abstract said no measurement of such detectors existed. Yet Fonseca's Table 2, as `reading-papers.md` records it, counts the misses and false alarms of a static checker, a two-run detector and a tiling detector on a small corpus.
    - **M2.** The paper showed TWO-RUN at σ 0.1 only. The registered σ 1.0 arm catches 96.58 % of the leaks with 1 run, 97.40 % with 2 and 98.45 % with 8. At one run each, it is above FI's ×3 run alone and not separated from its ÷3 run alone.
      - The auditor's paired cells (B4, computed from `verdicts.jsonl`) are not registered and decide nothing.
      - FI's 13-point lead over TWO-RUN is a property of σ 0.1.
  - **Fixed.**
    - In `paper/`, by its writer, draft 4: every finding on the paper. The orchestrator re-ran the writer's checklist (48 of 48 phrases found), regenerated `numbers.tex` byte for byte, and compiled it with MiKTeX: 23 pages, no undefined reference or citation.
    - In `docs/RESULTS.md`, the uncommitted rows of 2026-11-19:
      - the variant count is 21, not 0 (N17);
      - the σ 1.0 arms and the B4 cells are added to the two detector rows;
      - H7 and H8, never run since 2026-10-25, are added to the "Not run" row (m2).
    - The vault exposure's date in `paper.md` and `docs/ITERATIONS.md`: it was found on 2026-10-28 by Audit A of iteration 2, not in iteration 1 (N10).
  - **The registration's publicity (m5).**
    - `git ls-remote origin` shows `refs/heads/iteration-5` at `6044037` on GitHub.
    - The local reflog records its push at 2026-11-18 21:24:29 UTC. That is after the quantile table (20:32) and the commit (21:13), and before any run. GitHub's events list does not show that push.
    - Commits from `6ab7e3e` on are local only.
  - **Logged, not fixed:**
    - **N16.** `docs/DESIGN.md` credits the pairwise variance update to Chan, Golub and LeVeque's 1979 report, and the paper cites their 1983 paper. A read of the 1983 paper's pages is still due.
    - **N18.** `docs/DESIGN.md`'s OptMem sentence was corrected in place on 2026-11-19, and its §3 still calls Matrix's summaries "exact". That word belongs to the design document; the paper does not use it.
    - **m9.** Ten method papers are cited from their metadata only. A `\todo` in `paper/main.tex` asks for their first pages to be read before submission.
- 2026-11-20, before arXiv v1 (branch `arxiv-v1`). **The reading debts and the pre-submission audit.** No number, macro, run or code changed, and there was no contact with the data.
  - **The readings.** `scout` ran twice: `.claude/briefs/arxiv-v1/reading-notes.md` (method papers, revised arXiv sources) and `reading-2-notes.md` (the cited passages read again, mostly as page images).
    - MesaNet's equation numbers moved in v2.
    - Log-Linear Attention's bucket merging is in §3.2 of v3.
    - OptMem's README says neither "language model" nor "lossy", so the paper and `docs/DESIGN.md` were corrected.
  - **The audit.** `leakage-auditor` gave GO with fixes, with no Blocker: 3 Major, 9 Minor and 5 Nits (`.claude/briefs/arxiv-v1/audit-findings.md`). Every finding is fixed except m8 and the last Nit:
    - m8, the rendered draft markers, waits for Abdou's title;
    - the Nit on `crates/ols-core/src/centred.rs:10`, `:142` and `lib.rs:18`, which still say "Chan, Golub and LeVeque (1979)" without "attributed", is logged here, outside the diff.
  - **m9 of audit 2b is half paid.**
    - Five method papers were read at least to their abstract: McNemar, Brown–Durbin–Evans and Patton in their articles; Diebold–Mariano and Newey–West in the NBER working papers that preceded them.
    - Five could not be read at any primary source: Wilson, Harvey–Leybourne–Newbold, Politis–Romano, Page, and Chan–Golub–LeVeque.
    - They stay cited under the amendment of the method-citation rule that Abdou approved on 2026-11-20 (`.claude/briefs/iteration-5/paper.md`).
  - **N16 stays open.** No page of Chan, Golub and LeVeque, 1979 or 1983, was read. The paper now writes the merge formula out, checked against `centred.rs` by the auditor, so no statement rests on the citation.
