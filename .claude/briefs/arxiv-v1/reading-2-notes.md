# Verbatim re-read of the cited passages (scout, 2026-11-20)

Saved by the orchestrator from the scout's report, brief `reading-2.md`. The scout read the PDFs the fetch tool saved locally as page images (Fonseca, Causify, Goulet Coulombe v3, Garnelo, Katharopoulos, Chen, Nagel). It read freqtrade's code and documentation, Binance's terms, OptMem and the dual-decomposition paper through the fetch tool, and they stay "summarised". It edited no file, and could not check hashes, having no shell. Line numbers are those of `paper/main.tex` before this pass.

| Key | Line | Part read | Mode | Verdict | Evidence or replacement |
|---|---|---|---|---|---|
| fonseca2026 | 104, 126 | §8.3 p. 24; PDF pp. 14–19, 22–27 | verbatim | holds | "re-executes the pipeline on perturbed future data at sampled epochs" |
| | 118 | §8.3, Table 2 p. 25, §9 pp. 26–27, appendices pp. 28–30 | verbatim | holds | "not estimates of how often leaks occur". 52 of 53 cases are synthetic terms over the paper's own DSL. No perturbation law, epoch rule, run count or tolerance; only "the detector's default perturbation" (M2). |
| | 192–209 | §8.2 end p. 22, §8.3 p. 24, §9 | verbatim | holds | The oracle perturbs "every datum whose availability exceeds t". M1–M3, FP1, FP2, FP2b as described. |
| | 205 | as above | verbatim | holds; comment wrong | The classes are defined in §8.3's text; Table 2 gives rates only. |
| freqtrade | 105–106, 211–217 | `lookahead.py` (develop, 2026-11-20) and the docs page | code quoted by the tool; docs summarised | holds, two wording changes | The end date is the trade's `open_date` or `close_date` plus one candle. Docs: "Signals that are not triggered will not have been verified." Missing-equals-missing comes from pandas' `DataFrame.compare`, not from code of freqtrade's own. |
| causify2025 | 107–108, 219–223 | Thm 4.24 and Remark 4.25, PDF pp. 19–20; Remark 4.30 p. 23 | verbatim | holds | Tiles of lengths ≥ L, two-tile windows, checked "up to numerical precision"; the three failure modes match. v1 is the only version. |
| gouletcoulombe2025ols | 226–231, 905 | v3 pp. 4–7, 10, 15–16 | verbatim | holds; comment fix | Eq. (7) is on p. 4, not p. 5; negative weights p. 4; the ridge version Eq. (23) p. 7; A.4: masking "is not enough" when Ω̂ uses the whole sample. |
| binancevisionterms | 1282–1288 | clauses 3, 4.1, 4.5; version 1.0, "Last updated August 26, 2026" | summarised, quotes consistent | holds; one change | 3.1 CC BY-NC-SA 4.0; 4.1 lists "academic research"; 4.5 applies to a "redistributed derivative work". |
| garnelo2023 | 236–239, 912 | PDF pp. 1–5 (Def. 3.1, Thm 3.2) | verbatim | holds | "α is either a hyperparameter or a learnable parameter". v1 only. Status upgraded to verbatim. |
| gouletcoulombe2024dual | 231–236, 914 | §2.1, Table 2 | summarised (HTML) | holds | Fixed training sample; weights "can be negative"; a per-feature route. Table 2 is "Forecast Statistics for GDP Growth", with a short-position column; it does not show contributions itself. HTML header: "This draft: August 24, 2026". |
| chen2006regcube | 249–253, 908–913 | pp. 1–10 (Def. 2, Thms 4.1–4.4) | verbatim | holds; one change | Thm 4.4 combines the coefficients weighted by Θ; Thm 4.3 needs equal tuple counts; no range query, sliding window or subtraction. "Lattice of stored cells" is not a phrase of pp. 1–10. |
| nagel2025 | 255–259, 1134 | pp. 1–6 (abstract, §I) | verbatim | holds | "effectively reduces to a certain volatility-timed momentum strategy". §II.B–F (pp. 7–17) not re-read. |
| katharopoulos2020 | 1023 | v3 PDF pp. 1–3, Eqs. (4)–(6) | verbatim | holds | "a linear dot-product of kernel feature maps" |
| optmem | 874–877 | README and repository page | summarised | does not hold in part | The README: a log "append-only, never edited", and a tree of summaries "rebuildable from the log". It never says a language model writes them or that they are lossy; the agent does the compressions `note` asks for. |
| newcombe1998paired | 441, 748 | not re-read: Wiley 403 | none | unchanged | Metadata 17(22), 2635–2650 confirmed by search only. Iteration 5's read (Summary and Table I) stands as recorded in `reading-methods.md`. |
| politiswhite2004 | 833 | IDEAS abstract | summarised | holds (name and metadata) | Authors, 23(1), 53–70 and DOI match. |

**Not a change, for a reviewer's question.** Fonseca calls DataFlow's design a "two-run" detector, while Causify's Remark 4.25 describes tiling. The paper follows Causify's own text.

No bolder idea.
