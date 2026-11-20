# Audit of the pre-submission diff (leakage-auditor, 2026-11-20)

Saved by the orchestrator from the auditor's report, brief `audit.md`. Line numbers are those of the staged `paper/main.tex` before the fixes.

**Verdict: GO with fixes.** 3 Major, 9 Minor, 5 Nits. No number, macro, run or code is touched. Most findings share one cause: the diff fixed one occurrence of a statement and left its twin elsewhere in the file.

## The three questions

1. **The merge formula** is correct in sign and scale.
   - `crates/ols-core/src/centred.rs:268–302` adds `f·δ_xδ_xᵀ`, `f·δ_yδ_xᵀ` and `f·δ_yδ_yᵀ`, with `f = n_a n_b / n`.
   - A numpy check (200 random splits) gives a worst relative error of 1.1e-14.
   - `cargo test -p ols-core centred`: 13 passed.
   - The paper's single `δδᵀ` covers `M_yz` only if δ is the mean difference of the stacked vector (m1).
2. **The freqtrade sentence holds.**
   - `lookahead.py` on `develop` has the SHA-256 recorded in `refs.bib`; line 73 calls `cut_full_df.compare(cut_df)`.
   - pandas' docstring: "Matching NaNs will not appear as a difference." Tested on pandas 3.1.1.
   - PROTOCOL §0.4 does not name `DataFrame.compare` (m4).
3. **The five metadata-only citations do not meet the rule as written** (M2).

## Major

- **M1.** `:188–190` and `:1217–1219` claim each cited passage was re-read "as page images, wherever a primary copy was reachable". That is false against the notes:
  - Nagel §II.B–F was not re-read;
  - Newcombe was not re-read;
  - the dual paper, freqtrade's docs, the terms and OptMem stayed summaries although primary copies were reachable;
  - Goulet Coulombe's pages behind the absence claim were re-read only in part.

  Replacement texts given.
- **M2.** `paper.md`'s "Method citations" rule requires the abstract or first page to be checked at the publisher. Five keys remain unread: `wilson1927`, `harvey1997`, `politis1994`, `page1954`, `chan1983`. `politiswhite2004` rests on an aggregator's abstract.
  - Recommended: Abdou approves a dated amendment. Keep four keys, soften Harvey, and state Politis–White's aggregator.
  - Fallback if the amendment is refused: drop the five `\cite`s and keep the method names.
  - Either way, record that m9 is half paid and N16 is still open.
- **M3.** `:824–825`: "in the modified form of Harvey, Leybourne and Newbold" asserts content the notes leave unanswered. Write the correction out as the code computes it (`eval/stats.py:771–772`, `bench/power.py:659–661`).

## Minor

- **m1.** `:872–874`: the merge-formula wording is wrong for `M_yz`. Say the stacked vector `(z, y)`, and call it the matrix form of the variance update.
- **m2.** `:266–268`:
  - "no primary page was reachable" is wrong for Page, whose OUP page was reached, for metadata only;
  - "the one formula we take from them is written out" is wrong too, since the Wilson interval, the bootstrap and the CUSUM are only named.
- **m3.** `:263–265`:
  - McNemar's and Brown's abstracts were read through the summarising tool;
  - Newcombe, Politis–White and Katharopoulos are in neither group of five.
- **m4.** Stale read-level comments:
  - `:443`, `:750`, `:949` (McNemar, Brown);
  - `:913` and `refs.bib:77` (Garnelo);
  - `:907` ("some of those");
  - `:106` (freqtrade);
  - `:1135` (Nagel);
  - `:442`, `:749` (Newcombe);
  - `:834` (Politis–White);
  - `:906` (Goulet Coulombe);
  - `:1283` (terms).
- **m5.** `:908`: "over a lattice of stored cells" is still in the rendered text.
- **m6.** `:1241–1244`: "had not been pushed when this draft was audited" is stale. The local reflog shows `origin/iteration-5` at `76edd6c` on 2026-11-19, 23:22 +01:00, after the runs.
- **m7.** `:1275–1277`: the AI section under-reports. Later drafts and the reading were also done by agents, partly from page images.
- **m8.** Draft markers that are rendered but are not `\todo`s:
  - `\date{Draft 4, 2026-11-19}`;
  - the "Open decisions" block;
  - the red working-title line;
  - the header comments of `main.tex` and `refs.bib`.
- **m9.** `docs/DESIGN.md:78` and `:268` still say OptMem's summaries are written by a language model and lossy. The README says neither.

## Nit

- `:213–214`: "the strategy does not act on the last candle" matches only the entry comment of the code. The text says "the signal's date" where `:105` says the trade's entry or exit date.
- `:233`, `:915`: Table 2 of the dual paper is in its appendix, and `:915` lacks "short-position statistics".
- `:253–254`: Theorem 4.3 needs equal tuple counts, and the sentence drops that condition.
- `refs.bib` comments:
  - `:299` (Katharopoulos) is stale;
  - `:213` and `:262` lack the reason the paper was not read;
  - the dual paper is version 1, the only version.
- `crates/ols-core/src/centred.rs:10`, `:142` and `lib.rs:18` say "Chan, Golub and LeVeque (1979)" without "attributed". This is outside the diff; log only.

## Checked clean

- The build: 23 pages, no error, no BibTeX warning, one overfull box of 0.16 pt.
- The five `\todo`s are all Abdou's.
- The Binance terms, freqtrade's docs and OptMem's README, each read verbatim by the auditor, with SHA-256 digests recorded.
- The three arXiv abstract pages. For Log-Linear Attention, "ICLR 2026" is the header of the v3 PDF, not a venue on its abstract page.
- The other diff lines match the notes.

## Digests of the files the auditor read verbatim (SHA-256, computed by the orchestrator on 2026-11-20 from the auditor's scratchpad downloads)

| File | SHA-256 |
|---|---|
| freqtrade `lookahead.py` (develop) | `25b02b2d4f6e4317d8855b01976a3fef112e56280b7a33954634ed4dc51e2cca`, the same as in `refs.bib` |
| freqtrade `lookahead-analysis.md` (develop) | `49c0cc7f34f5aa071827366d0fe28af765a2fe7a91f823548d33687bf5b633b9` |
| Binance Vision `TERMS_AND_CONDITIONS.md` (master) | `99c4921dbe023cd68c1a447775707d621453cc78aec6ac0bfe2e6c06a5114ee0` |
| OptMem `README.md` (main) | `9f73e4374fc9dc1f58b3fcb228eff2064b9df313a012f88b7b925d2e401f663d` |
| Log-Linear Attention v3 PDF | `d04b04a19bc61c5689bf56d6129d1c67089aeb58127f8114d3f831630f4ba24e` |
| Dual-decomposition v1 HTML | `2a6e0b458a4dfdefd8d5fc90f91e11de62ab93a1e67b13fc4225ec5a9a6a8d6b` |

## Not verified

- The scout's page-image reads.
- The five method papers.
- Freqtrade's pinned pandas version.
- That today's terms file equals commit `d3357a5c33ba`.
- The dual paper's per-feature route.
- The test suites, since no code changed.
