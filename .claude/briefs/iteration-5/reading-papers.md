# Reading notes, run A: the papers (iteration 5)

- **Author:** `scout` run A, read 2026-11-18; saved by the orchestrator (scout cannot write files). Read-only.
- **Method caveat.** WebFetch passes each page through a small summarising model, so every answer from an arXiv HTML page below is a summary produced by that tool, not a line-by-line reading. Verbatim text was not checked. Where the tool did not see something, the note says "not found in what was read". Nothing is filled from recall, abstracts or snippets. The regression-cube PDF is the exception: its pages were read as images.
- **Consequence for the paper.** A "summarised read" is weaker than a full read. Before any of these sources is cited, the orchestrator re-reads the cited passages verbatim (section 7 below tracks it).

## 1. Fonseca, arXiv 2607.04958 v1 (submitted 2026-07-06, cs.CR, single author Xavier Fonseca)

**Read level: partial.**
- Fetch 1 (characters 0–100,000 of 185,217) returned only a table of contents and the abstract/introduction headline numbers. The tool said the bodies of sections 6–10 were missing from that part.
- Fetch 2 (characters 100,000 on) covered §6 and §7 in full, §8 (8.1–8.3, Tables 1–2), §9, the conclusion, "Data and Code Availability" and the references.
- Sections 1–4 and most of 5 were not read in body text. §2.3 (the DataFlow tiling background) was only summarised.

**Detectors (§8.2 end, §8.3).**
- **Dynamic oracle (end of §8.2).** At a sampled epoch it computes the decision on the stored data. It then recomputes after perturbing every datum whose availability exceeds that epoch. A differing decision counts as a witnessed leak. It shares no code with the static checker.
- **Two-run differential detector (§8.3).** It "re-executes the pipeline on perturbed future data at sampled epochs" and flags a change. It is presented as the design behind differential leakage testers such as DataFlow's.
- **Tiling detector (§8.3).** It compares outputs across shifted data windows.
- **Confirmed absent from the text read:** the sampled epochs, the perturbation distribution, the number of runs, the comparison rule and any tolerance.

**Leak classes, each defined by how a detector misses it (§8.3).**
- **M1, coverage miss.** The leak sits at an epoch between the two-run detector's sampled epochs.
- **M2, perturbation-insensitivity.** A future value is read through a threshold operation that the default perturbation does not flip on the tested input. Another input would flip it.
- **M3, insidious re-stamp.** A future-valued series is re-stamped to an admissible stamp. An output-comparing detector sees nothing, while the effect system rejects it.

**Clean classes.**
- **FP1, algebraic cancellation.** A future value subtracted from itself.
- **FP2, dominated future.** An operation that ignores its future argument.
- **FP2b, availability-structure domination.** The declared availability is min(t, t+1), which reduces to t. The checker accepts these.

No concrete code example is given for any class. The paper says only that the leaks target the detectors' blind spots.

**Corpus.**
- 53 pipelines: 33 leaks and 20 clean.
- 52 are synthetic terms over the paper's public DSL; one anchor comes from proprietary weekly-release data.
- Ground truth is "fixed by construction".
- Whether the cases were hand-written or generated: not stated.

**Table 2.**

| Detector | False negatives (of 33 leaks) | False positives (of 20 clean) |
|---|---|---|
| Checker | 0/33 (rule-of-three upper bound 9.1%) | 15/20, all from FP1/FP2; all 5 FP2b accepted |
| Two-run | 18/33 (54.5%) | 0/20 |
| Tiling | 33/33 | 0/20 |

- Statistics: cluster bootstrap and permutation tests (p < 1e-4, Benjamini–Hochberg-adjusted) and a Wilcoxon test (p < 1e-3).
- Post-hoc power for checker versus two-run is 76.7%.
- §9 limits: the corpus shows that leak types exist, not how often they occur. It is small and clustered by mechanism. The oracle's silence proves nothing.
- Oracle validation (§8.2): five archetypes on proprietary data, no oracle witness for any accepted clean pipeline.

**Artifact.**
- The text says the artifact will be deposited with a permanent DOI "upon acceptance". It names an open-source licence for code and an open-data licence for the synthetic data. It gives no URL, language or licence name.
- The abs page lists no GitHub or Zenodo link: only the PDF, HTML, TeX source, DOI 10.48550/arXiv.2607.04958 and arXiv's non-exclusive distribution licence.
- **Verdict: no artifact found** on the arXiv pages. The TeX source, GitHub and Zenodo were not searched separately.

## 2. Garnelo & Czarnecki, arXiv 2305.10203

**Read level: partial (summarised).** The tool saw the abstract, §1–7, the references and Appendices 1–9; the last 1,792 characters (a footer) were not read.
- **Causal:** the text read never mentions masking. Intention is defined over the full key and value set (Def. 3.1, §3), so as written it is non-causal.
- **Ridge:** yes. α ≥ 0 is a covariance-smoothing term (§2, Def. 2.7).
- **Learned λ:** optional (§3): "either a hyperparameter or a learnable parameter". Appendix 1 describes a learnable α that depends on K and V. Appendix 8 uses sigmoid(θ); Appendix 9 uses a trainable α initialised at 0.
- **Formulation:** f_ls(K,V,Q) = Q[KKᵀ+αI]⁻¹KᵀV (§2) as the tool transcribed it. Its dimensions look inconsistent, so check against the PDF. The practical module (Def. 3.1) uses Σ = XᵀX + αI, with MLP embeddings of Q, K and V.
- **Solve:** closed form, cost O(N²d) (Thm 3.2). The pseudoinverse is suggested for stability. A kernel (Nyström) variant and a constrained extension exist.
- **Tasks:** sine regression, MNIST pixels, MiniImageNet, policy distillation, Kabsch, CIFAR100 outliers. No time series or finance.
- **Versus Goulet Coulombe's OLS attention:** Garnelo's module is a trainable neural layer (embeddings plus solve); Goulet Coulombe's is a diagnostic reading of fitted models.
- **Versus our heads (DESIGN §4):** same algebraic family. Ours differ: unpenalised intercept coordinate (rows of W sum to 1); λ learned per head; window entirely in the past; Matrix causal through prefix sums and sufficient-statistic merges. An unpenalised intercept is "not found" in what was read, so it must not be claimed as new without a full read.

## 3. Goulet Coulombe, Göbel & Klieber, arXiv 2412.13076

**Read level: partial (summarised).** Read: abstract, §1, §2 (2.1–2.8), §3.1, §3.2–3.5, the conclusion, Appendix A.1–A.2 and the references. Fetch 1 stopped mid-§3.2 and fetch 2 resumed there.

**What is decomposed (§2.1).**
- The forecast for one out-of-sample observation j is split over the N training observations i.
- Weights: w_j = K_j(K+λI_N)⁻¹ with K = XX′ (the dual form). Contributions: c_ji = w_ji·y_i, with ŷ_j = Σ_i c_ji.
- Per training observation, not per feature, not crossed. The per-feature version is a separate "primal route" with c_jp = X_{j,p}·β̂_p.
- Extensions: kernel ridge (2.2), neural nets via last-hidden-layer outputs (2.3; replication above 99%, so approximate), random forest (2.4), boosting via AXIL (2.5), classification via dual kernel logistic regression (2.6). Concentration, short position, leverage and turnover statistics (2.8).
- **Data (§3.1):** FRED-QD/MD, quarterly 1961Q2–2024Q1, monthly to 2024M6, MARX transforms, standardised on the training sample. Targets: CPI inflation, GDP, unemployment, recessions. The inflation holdout is 2020Q1–2024Q1.
- **Weights can be negative** for ridge, kernel ridge, FAAR and NN (Table 2).
- **Look-ahead:** not discussed explicitly in what was read. The post-Covid exercise trains to 2019Q4 and is retrospective. Data vintages and refitting as the origin moves are not mentioned.

**Versus Matrix (DESIGN §1).**
- Matrix writes ŷ = Σᵢ wᵢyᵢ with wᵢ = xᵢᵀa and a = (XᵀX+Λ)⁻¹x_q: the primal-side form of the same ridge weights (inference: the push-through identity makes them equal).
- Differences that hold: Matrix stores (XᵀX, XᵀY) as mergeable sufficient statistics, so any set S of entries has an additive contribution C_S·a; they build an N×N kernel on a fixed training set, with no incremental store. We keep an unpenalised intercept so weights sum to 1 (not mentioned in what was read).
- Their decomposition is not new for ridge. Our novelty can only be the stored, mergeable and time-causal form.

## 4. Other detector arms

### 4a. freqtrade lookahead-analysis

**Read level: source read in full through the tool** (whole file, function names but no line numbers; `fill_full_varholder` in the base class not seen). **Docs page: read in full** except an abridged CLI block.
- **Truncation.** Per analysed trade there are two slices. The start is always the full run's `from_dt`; only the end is cut. Entry slice: `to_dt = open_date + one candle`, checked at `compared_dt = open_date`. Exit slice: `close_date + one candle`, checked at `close_date`. The extra candle exists because the strategy does not act on the last candle.
- **What is run.** One full baseline backtest on all pairs (fails with "too few trades" under `minimum_trade_amount`), then one backtest per analysed signal on a single pair. Default signal count 20 (docs).
- **Comparison.** `analyze_indicators` takes `full_df.loc[cut_df.index]`, calls `DataFrame.compare()`, and flags any exact difference; NaN equals NaN. Only the first differing row is examined. **No tolerance.** `report_signal` checks that the signal timestamp is reproduced in the truncated run; a miss increments the false entry or exit counters. Bias is reported if either counter is above 0 or any indicator differs.
- **Docs caveats.** Only triggered signals are verified (false negatives); pairlist-dependent strategies can be falsely flagged; limit orders can cause false positives; FreqAI targets are flagged falsely.
- **Type.** Truncation: it cuts the future away and compares the past. It does not perturb the future.

### 4b. Causify DataFlow, arXiv 2512.23977 v1

**Read level: partial (summarised).** Start through §4.5 (Remark 4.30); §5–8 not read. The tiling check itself was read.
- **Remark 4.25, §4.4, a four-step protocol.**
  1. Run the node or DAG on the full history to get Y_ref.
  2. Split the same history into tiles of different lengths τ₁, τ₂, … (each at least the context window L).
  3. Re-run per tiling, with two-tile input windows (Theorem 4.24), to get Y(τₖ).
  4. Check that Y(τₖ) equals Y_ref "up to numerical precision".
- Theorem 4.24: for a tile of length τ ≥ L, the output at u in the second tile depends only on [u−L+1, u], which fits inside the two-tile window.
- A mismatch means: L too small, the node reads the future, or the node is nondeterministic or has untracked dependencies.
- No numeric tolerance and no test implementation in what was read.

## 5. Regression cube, IEEE TKDE vol. 18 no. 12, Dec 2006, pp. 1585–1598

**Read level: pages 1–10 read as page images** from the author-hosted PDF (https://www2.cs.sfu.ca/~jpei/publications/regressioncube-tkde06.pdf). Pages 11 on (filtering extensions, experiments, related work) not read.
- **Measure (Def. 2, §4.2, eqs. 14–15).** Not literally (XᵀX, Xᵀy). The NCR of a cell is (η̂, Θ), with Θ = UᵀU; the response enters only through η̂ = Θ⁻¹Uᵀy, one scalar y. Since Θ·η̂ = Uᵀy (eq. 25), the NCR is information-equivalent to (UᵀU, Uᵀy) when Θ is invertible (inference). Size k(k+3)/2, independent of the tuple count (Thm 4.1). The linear case also stores n, t₀ and t₁.
- **Aggregation along the regression (time) dimension (Thm 4.4, eqs. 8–9, 29).** Θₐ = ΣΘᵢ and η̂ₐ = (ΣΘᵢ)⁻¹(ΣΘᵢη̂ᵢ). In standard dimensions (Thm 4.3): η̂ₐ = Ση̂ᵢ, Θ identical.
- **Windows.** Queryable cells are unions of stored descendant cells in a concept-hierarchy lattice; base cells materialised at the lowest level; partial materialisation in §1.2. No arbitrary range or sliding-window query and no subtraction of a cell in pages 1–10. Incremental update recomputes modified cells and propagates up (p. 10). An autoregressive-filter variant (§5) and a linear prediction filter.
- **Meaning for us.** The additive-statistics merge and lossless compression exist, over a fixed lattice of stored cells; prefix sums with subtraction do not.

## 6. What this changes for the paper's claims and for the detector design

1. **Fonseca.**
   - The paper must not say a "default" two-run detector exists in the literature: his text gives no perturbation law, epoch rule, run count or tolerance. Our two-run arm is defined by us and published.
   - Scout's proposed definition (inference): sample K epochs; at each, perturb every bar whose close time is after t (multiplicative lognormal noise, fixed seed); re-run; compare outputs at dates up to t exactly or with a stated relative tolerance. K, noise scale and tolerance are the arm's declared parameters. A second arm with larger K and heavier perturbation shows whether M1/M2 misses come from the parameters or the idea.
   - The classes can be rebuilt on OHLCV bars for M1–M3, FP1, FP2, as pure functions of the bars (examples are ours, not his): M1 uses close[t+1] only on dates that avoid the sampled epochs; M2 max(close[t+1], 2·close[t]); M3 a bar stamped with its open time; FP1 x[t+1] − x[t+1]; FP2 min(x[t], 0·x[t+1]). FP2b needs declared availability metadata: drop it or label it not rebuilt.
   - Do not compare our numbers with his: his come from his own DSL corpus, with power below 80% (§9).
2. **Garnelo & Czarnecki.** Claim only a time-causal, mergeable, past-only store with an unpenalised intercept; the intercept point needs a full read.
3. **Goulet Coulombe et al.** Per-observation ridge decomposition and its negative weights are prior art. Narrow our claim to incremental sufficient statistics and additive set contributions.
4. **freqtrade and Causify.** freqtrade truncates the future (end only, one candle after the trade date) and compares exactly; Causify re-tiles and compares to an unstated precision. Neither perturbs the future; Fonseca's two-run does. Three detector types; we fix every tolerance.
5. **Regression cube.** Cite as 2006 prior art for the compressible regression measure and lossless merge. Do not claim sufficient statistics for regression as new, nor that it supports sliding windows.

**Scout's bolder idea:** treat Fonseca's classes as a mutation-testing generator: a parametric family of leaks per class (epoch position, threshold height, stamp offset as knobs), and the curve of detection power against knob for every detector.

## 7. Orchestrator's follow-up (2026-11-18)

- Verbatim re-read needed before citing: Fonseca §8.2–8.3 and §9 (definitions, Table 2), Garnelo & Czarnecki §2–3 (formula, intercept), Causify Remark 4.25 and Theorem 4.24.
- Not read at all in this iteration yet (required by `paper.md` or dropped): Log-Linear Attention, MesaNet, Goulet Coulombe 2504.09663, Nagel NBER w34104.

Sources: [Fonseca abs](https://arxiv.org/abs/2607.04958), [Fonseca HTML](https://arxiv.org/html/2607.04958v1), [Garnelo & Czarnecki](https://arxiv.org/html/2305.10203), [Goulet Coulombe et al.](https://arxiv.org/html/2412.13076), [freqtrade docs](https://www.freqtrade.io/en/stable/lookahead-analysis/), [freqtrade source](https://raw.githubusercontent.com/freqtrade/freqtrade/develop/freqtrade/optimize/analysis/lookahead.py), [Causify DataFlow](https://arxiv.org/html/2512.23977v1), [Regression cubes TKDE 2006](https://www2.cs.sfu.ca/~jpei/publications/regressioncube-tkde06.pdf)
