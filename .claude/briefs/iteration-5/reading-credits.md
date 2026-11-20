# Reading credits for claim 3 (run C, iteration 5), 2026-11-18

- **Author:** `scout` run C; saved by the orchestrator (scout cannot write files). Read-only.
- **Method.** WebFetch on HTML returns a small model's summary ("summary" below). PDFs were saved by WebFetch and read as page images (primary text). No source was read to the last appendix: the strongest status is "main text read as PDF pages, appendices not". Under `paper.md`'s rule none of the four is "read in full" yet. Options: read the remaining pages, cite only for the pages read (naming them), or drop.
- **Versions read:** Log-Linear Attention arXiv 2506.04761v2 (25 Jun 2025; a v3 of March 2026 exists, not read). MesaNet arXiv 2506.05233v1 (5 Jun 2025; ICLR 2026 version not read). Goulet Coulombe arXiv 2504.09663v3 (5 Oct 2026). Nagel NBER w34104 (Aug 2025).
- **Saved PDFs** (session tool-results folder `C:\Users\abdou\.claude\projects\C--Users-abdou-ols-prime\42564a09-9a68-4105-bae2-0e91463486d3\tool-results\`): Log-Linear `webfetch-1795030807133-x4jewq.pdf`, MesaNet `webfetch-1795030807737-4ozltw.pdf`, Goulet Coulombe `webfetch-1795030777644-7ls70v.pdf`, Nagel `webfetch-1795030792799-leu9uv.pdf`. Readable further with Read and `pages`.

## 1. Log-Linear Attention (Guo, Yang, Goel, Xing, Dao, Kim; arXiv 2506.04761v2)

**Read level: partial.** PDF pp. 1-8 (abstract, §1, §2, §3.1-3.5, §4.1-4.2). Appendix tail only as summary (no mention of least squares, ridge, sufficient statistics or arbitrary windows found). Not read: appendices A, B.1, B.4, C, D; v3.
- **State (pp. 4-5, §3.1):** about log T matrices S_t^(l), each a linear-attention state Σ v_s k_sᵀ over one bucket of a Fenwick-tree partition of the prefix [0, t) into power-of-two segments. Output o_t = Σ_l λ_t^(l) q_tᵀ S_t^(l); λ data-dependent, non-negative, from a linear projection of x_t, not solved for. Decoding O(log T) time and memory (Table 1).
- **Arbitrary window: no.** Causal queries over the whole prefix; buckets fixed by t; merged buckets overwrite lower levels (no raw log kept).
- **Least squares or ridge: no** in the pages read.
- **Verdict:** credit for the Fenwick-tree hierarchy of segment summaries; differs from Matrix (no ridge statistics, no raw log, no window query).

## 2. MesaNet (von Oswald, Scherrer et al.; arXiv 2506.05233v1)

**Read level: partial.** PDF pp. 1-7 (abstract, §1, §2 with Eqs. 1-8, §3, §4, §5 to 5.1). Appendices A, B, C, D, F.4, F.5, I and §6-7 only as summary. Not read: the rest, including Appendix K.
- **Layer (Eq. 4):** cumulative ridge regression over the prefix, Φ̂_t = argmin ½ Σ_{t'≤t} ‖v_t' − Φ k_t'‖² + Tr(ΦᵀΛΦ)/2.
- **Running statistics (Eq. 6):** G_t = γ_t G_{t−1} + β_t v_t k_tᵀ, H_t = γ_t H_{t−1} + β_t k_t k_tᵀ, gated by forget γ and input β.
- **Readout (Eq. 8):** q*_t = (H_t + Λ)⁻¹ q_t by conjugate gradient; o_t = Σ_i ζ_ti v_i k_iᵀ q*_t; causal. Training uses a fixed 30 CG steps (p. 7).
- **Not exact:** CG is iterative. A stopping ε = 10⁻⁴ with about 9 steps came from a summary only: unverified.
- **Λ:** meta-learned, fixed over time (summary of F.4, F.5, D; not read). p. 4: forget gates plus a decaying Λ were numerically unstable in the original Mesa layer.
- p. 4 states that Atlas corresponds to a sliding-window variant of the Mesa layer: that is Atlas, not MesaNet.
- **Arbitrary window: no.** Gated full prefix with smooth exponential forgetting; no per-period decomposition in §3.
- **Verdict:** credit for the causal prefix ridge readout with running statistics and gates. Never "exact", never "window".

## 3. Goulet Coulombe, "Ordinary Least Squares as an Attention Mechanism" (arXiv 2504.09663v3)

**Read level: partial.** PDF pp. 1-10 (main text through §5 Limitations), references, Appendix A.1-A.6 and the start of B (pp. 11-18). Not read: the rest of B, and C-F (Regression Block, ablations, benchmarks).
- Eq. (7): ŷ_j = Σ_i ⟨F_j, F_i⟩ y_i, F = X U Λ^{-1/2} from the eigendecomposition of XᵀX; Q = X_test W_Q, K = X_train W_K, V = y, identity in place of softmax (p. 5). Cross-attention from a fixed train matrix to test rows: non-causal by design. Weights can be negative (p. 4).
- Ridge: Ω_λ = (XᵀX + λI)⁻¹ (p. 7, Eq. 23).
- Data: Monte Carlo (six DGPs) and eight UCI/OpenML tabular sets (Table 1, pp. 9-10). Time series only as illustration in A.3-A.5 (AR(1), VAR, pooled panels).
- **Appendix A.4 (pp. 15-16):** masking future entries is not enough, because the inverse Gram matrix is estimated on the full sample. This is the primary source for the leak `docs/DESIGN.md` §1 attributes to "the paper".
- Limitations (p. 10, and p. 8 §3.3): the exact identity covers one restricted attention module; in a full Transformer the reading is local.
- No sufficient-statistics store, windowed readout, per-period decomposition or causal memory. (2412.13076 is a different paper; see `reading-papers.md`.)
- **Verdict:** credit for the identity and the leakage warning; not a precedent for Matrix.

## 4. Nagel, "Seemingly Virtuous Complexity in Return Prediction" (NBER WP 34104, Aug 2025)

**Read level: partial.** PDF pp. 1-22 (abstract, §I, §II.A-II.G to the start of the simulations). Not read: the end of II.G (MA(2) simulation, wild-bootstrap tables), §III (cross-section, SDF), Appendices A and C.1, the conclusion.
- Setting: the Kelly-Malamud-Zhou market-timing design; CRSP value-weighted excess return, monthly; K = 15 predictors (14 Goyal-Welch plus the lagged return); P = 12,000 random Fourier features; rolling window T = 12 months; ridgeless (pseudoinverse); about 1930-2020 (pp. 1, 6, 12).
- Mechanism: for P > T the forecast is w_t′ r_t with w′ = z_t′ Z′(ZZ′)⁻¹ (p. 7, Eq. 3), a similarity-weighted average of the T training returns. Persistent predictors make recent months most similar (momentum); lower predictor volatility raises similarity (volatility timing).
- RFF dot products converge to a Gaussian kernel (Eqs. 5-10, p. 9); a "shifted kernel" form tracks within-window standardization empirically, with no closed form (p. 11). Weights correlate 0.99 with the kernel version for lag 1; predicted returns 0.93 (pp. 13-14).
- Simple rule (Eq. 14, p. 17): momentum with linearly declining weights, scaled by inverse predictor variance.
- Table I (p. 19), annualised alphas against the market: RFF 0.034 (t 2.417), kernel 0.040 (t 2.900), vol-timed momentum 0.034 (t 3.684). With the kernel factor the RFF alpha is −0.001 (t −0.122); with the vol-momentum factor 0.012 (t 0.945).
- p. 20 says the finding holds for T = 60 and T = 120 (Appendix C.1, not read).
- Scope: ridgeless P ≫ T, not OLS in general; the similarity form holds for any regression with P > T (§II.B); the momentum reduction needs a short window and persistent predictors.
- **Verdict:** use narrowly.

## What this changes for the paper's claim 3 and the case study

- **Log-Linear Attention.** May say: its memory is a Fenwick-tree partition of the causal prefix into O(log T) linear-attention states, not regression statistics. Forbidden: ridge, windows. Cite as pp. 1-8 read.
- **MesaNet.** May say: it solves a causal ridge regression over the gated prefix by CG, with running (YXᵀ, XᵀX)-type statistics and a fixed-over-time meta-learned Λ. Forbidden: "exact", "window". Cite for pp. 1-7.
- **Goulet Coulombe 2504.09663.** May say: OLS predictions have an attention form over a fixed train set (non-causal), and masking alone does not remove the leak (A.4). Forbidden: precedent for causal windowed ridge or Matrix. Cite for pp. 1-10 and A.1-A.6.
- **Nagel.** May say: for ridgeless P ≫ T regressions on monthly CRSP data with T = 12, the forecast is a similarity-weighted average of past returns and tracks a volatility-timed momentum rule. Forbidden: extending it to our crypto bars, to ridge with T ≫ P, or to daily or hourly data. Cite for §I to II.F.
- **Case study.** Nagel motivates a stated check of momentum and volatility timing (the `case-study.md` factor control). A design reading, not a finding of the papers.
- **Absence-in-literature wording,** for these four: "among the works we read (pages named), none stores a raw per-entry log with exact ridge on any window." Not yet supported for the regression cubes beyond pp. 1-10, 2412.13076 or Garnelo & Czarnecki (summarised reads).

**Scout's bolder idea:** run Nagel's diagnostic on Matrix itself: check whether its per-entry signed weights wᵢ = xᵢᵀa decay with lag and scale with inverse feature volatility, against a lag-decay baseline.
