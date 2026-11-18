# Brief — the reading, before any detector is defined

- **Agent:** `scout` (sonnet, medium), two runs in parallel: run A reads the papers, run B the terms.
- **Read-only.** Notes go to `.claude/briefs/iteration-5/reading-papers.md` (run A) and `reading-terms.md` (run B), in English.
- **Motto:** we should be more ambitious in what we read in full, never in what we claim a source says.

## Why

The state-of-the-art search of 2026-11-18 is a set of leads, not a set of citations. Most sources were read at abstract or snippet level. Its report, in French, is `C:\Users\abdou\ols-prime-pages\reports\Antériorité OLS Prime Matrix et Caladrius.md`, and its notes are in `C:\Users\abdou\ols-prime-pages\research_notes\Antériorité OLS Prime Matrix et Caladrius\`. The shape of the detector comparison (`detectors.md`) depends on what Fonseca actually built. No citation enters the paper from an abstract or a snippet.

## Run A — the papers

Read in full, from arxiv.org's HTML or PDF (`pdftotext` is installed in Git Bash), and quote at most one sentence of under 15 words per source:
1. **Fonseca, "Look-Ahead-Freedom as Temporal Non-Interference", arXiv 2607.04958**, sections 4 to 8 above all:
   - the exact definitions of the paper's "two-run differential detector", "tiling detector" and dynamic oracle (§8.2, §8.3): what is perturbed, how, at which dates, and what is compared;
   - the leak classes M1, M2, M3 and the clean classes FP1, FP2, FP2b, each with one concrete example we could rebuild on OHLCV bars;
   - how the paper's 33 leaks and 20 clean cases were built (by hand or generated), and its Table 2;
   - the paper's artifact: a URL, a language, a licence, or "none found".
2. **Garnelo & Czarnecki, arXiv 2305.10203:** is their least-squares module causal, ridge-regularized, with a learned λ? How does it differ from Goulet Coulombe's OLS attention and from our heads (`docs/DESIGN.md` §4)?
3. **Goulet Coulombe, Göbel & Klieber, arXiv 2412.13076:** what exactly they decompose (per observation, per feature, crossed or not) and on what data. Compare with Matrix's decomposition (`docs/DESIGN.md` §1).
4. **The two other detector arms:** freqtrade's `lookahead-analysis` documentation and source (what is truncated, what is compared, with which tolerance), and Causify's DataFlow, arXiv 2512.23977 (how its re-tiling check works).
5. **The regression cube, TKDE 2006** (Chen, Dong, Han, Pei, Wah, Wang; locate the paper): is its measure exactly (XᵀX, Xᵀy)? Are its windows arbitrary or only unions of stored cells?

**Done when:** each item has its answers with the section or page they come from, and a last paragraph says what each changes for the paper's claims.

## Run B — Binance's Terms of Use

`docs/DATA.md` reads the Binance Vision dataset terms but lists the Binance Terms of Use, which those terms supplement (clause 1.2), as not read yet.
- Read the current Binance Terms of Use and any clause on market data, research use, publication of derived results, and access from France (Binance has been closed to French residents since 2026-07-01).
- Answer: may an individual in France publish an academic paper, under CC BY-NC-SA 4.0, whose figures derive from data.binance.vision archives downloaded in 2026-10? May the leak corpus (functions of those bars, and their outputs) be released?
- Give the clauses, their numbers and the date read. Say where the terms are ambiguous. This is not legal advice, and the report says so.

**Done when:** the answer, the clauses and the open questions are in `reading-terms.md`, with a proposed dated line for `docs/DATA.md` that the orchestrator applies.
