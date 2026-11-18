# Resume 2 — iteration 5 after wave 1 and the pre-registration draft

- **Written:** 2026-11-18, by the orchestrator of the first iteration-5 session. It hands off because its context passed about 190k tokens.
- **State:**
  - Branch `iteration-5`. The brief was committed at `a9db77f` in the preparation session; nothing has been committed since and nothing pushed.
  - Changed and uncommitted: `docs/ITERATIONS.md`, which has a "Progress (2026-11-18)" block at the end of iteration 5's section.
  - New in this folder, uncommitted: `reading-papers.md`, `reading-terms.md`, `misses-findings.md`, `prereg-draft.md`, this file, and `reading-credits.md` and `audit-5a-findings.md` once they land.
  - Never `git add -A`. Untracked and left alone on purpose: `.claude/worktrees/` and two iteration-4 drafts.
- **Abdou's decisions this session:**
  - **No learning page for iteration 5** (2026-11-18). The teacher wave is dropped and reported as not done.
  - Still open: the paper's licence, the author name, the arXiv category, the corpus release, arXiv v1 as the vault's public pre-registration, and the endorser. A written question to Binance's data contact or a lawyer is also Abdou's act (`reading-terms.md` §7).
- **Usage at hand-off:** about 10 % of the weekly limit, all models and Fable alike. Check `get_usage` before each wave.

## Done

- **Wave 1.**
  - Scout runs A and B, saved by the orchestrator, since scout cannot write files.
  - `ml-engineer` on the misses. The 163 and 193 counts are nested, and both are right: one compares both schedules (144 cuts), the other H1's 16 cuts. The `RESULTS.md` twins row borrows the adversary's wording.
- **Fonseca §8.3, re-read verbatim in the browser pane.** It gives no perturbation law, epoch rule, run count or tolerance. Our TWO-RUN arm is therefore our own definition.
- **The Binance Terms of Use** (in force since 2026-10-27) are a PDF embedded in binance.com/en/terms; its URL is in `reading-terms.md` §7. They were read in part.
- **`prereg-draft.md` was written** and sent to audit pass 5a (`leakage-auditor`, in the background, launched from the first session).
- **Scout run C** reads Log-Linear Attention, MesaNet, 2504.09663 and Nagel w34104 for the paper's credits. It was also launched from the first session.

## Audit pass 5a: done, "register with fixes"

The findings are in `audit-5a-findings.md` (184 lines). The auditor's scratch scripts on synthetic bars are in `audit-5a-scripts/` (s1 to s8, never real data, never seed 20261118). Counts: 2 Blockers, 10 Major, 11 Minor, 4 Nits.

**A re-read of the fixed text by `leakage-auditor` is a condition of registration.** Send it as a follow-up to the same audit, pass 5a-bis.

The fixes that reshape the design:
- **B1. The finite-only rule cannot separate catches through a missing bar.** A binary leak turns NaN, then false, then 0: a finite move.
  - Replace it by a read-based mask: "some read is missing", propagated through each expression.
  - Assert that every TRUNC and RETILE catch is through a missing read.
  - Drop D2 as worded.
- **B2. TRUNC's rate is the polarity of the NaN convention.** `x[s+1] > c` and `x[s+1] < c` get opposite verdicts.
  - Register three conventions: missing is false (primary), missing is true (mirrored), and propagation.
  - Add a second denominator: the leaks not constant at the 16 cuts' compared rows.
  - The auditor's consolidated D1 text, in the findings file, gives a Newcombe interval against a 1-point margin, plus a "convention-dependent" qualifier. Adopt it.
- **M2. TRUNC-1 as drafted is not freqtrade's check,** and it cannot catch a reach-1 leak (26 % of leaks). Make it faithful or rename it.
- **M3, M4. Metrics.** Register both the any-cut share and the mean per-cut rate, plus the first-m-cuts curve. Report every comparison at equal run counts.
- **M1, M5. TWO-RUN.**
  - Its own seed tuple, 20261119 for the official run and 51119 for development.
  - A code-level repair recipe: each wick rebuilt from its own log factor, as `perturb.py:427-430` does, with `_check_valid`.
- **M6. Cancelled controls.** Fix the construction rule and use the auditor's code-level prediction (twin with the node missing where `v` is undefined). Register FP2 under both `np.minimum` and `np.fmin`.
- **M7. No real-bar run of any new detector before 5b's GO.** One frozen commit serves both the descriptive and the confirmatory run.
- **M8. The quantile table.**
  - Compute it now, as a logged contact, with its digest, its method and its share inside each band.
  - Keep `placement` out of `AdversaryConfig`, so `adversary.json` stays byte-identical.
  - Register the development population's digest (seed 51118), never the confirmatory one's.
- **M10. RETILE.** Real slicing, its ends registered (28 of them), and an asserted equality with TRUNC-0 at the same ends. No claim that RETILE is independent of TRUNC-0.
- **The auditor's bolder check: the mirror-twin asymmetry,** a measured property for every detector. Worth adopting as a registered metric.

## Next steps

1. Read `CLAUDE.md`, iteration 5's section of `docs/ITERATIONS.md`, `prereg-draft.md` and `audit-5a-findings.md`.
2. **Fix every Blocker and Major in the text, and fix or log every Minor and Nit.** Then send the fixed draft to `leakage-auditor` for the re-read. Then move the fixed draft into `docs/PROTOCOL.md`, as a new section "Leak detectors measured against each other (iteration 5)", and its hypotheses into `docs/HYPOTHESES.md`, each with a dated change-log line. Log the quantile table's read of the pre-2019 bars as a data contact.
   - Commit that registration only with Abdou's go-ahead, and before wave 3 touches seed 20261118.
3. **`misses-findings.md`'s counting script was re-run by the orchestrator on 2026-11-18.**
   - The digests match.
   - Both schedules give 163 constant misses, H1's cuts only 193, and the 163 are nested in the 193 with 30 between them.
   - The classes are 193 / 5 / 7 against 163 / 22 / 20.
   - Remaining: append its correction paragraph to `docs/RESULTS.md` as a dated row; never edit the old rows.
4. **Apply the `docs/DATA.md` line** proposed in `reading-terms.md` §7, which replaces the line of §6.
5. **Before citing Fonseca, Garnelo & Czarnecki, Causify, or anything from `reading-credits.md` in the paper,** re-read the cited passages verbatim, as for Fonseca §8.3. The scouts' notes went through a summarising fetch. The browser pane's `javascript_tool` on the arXiv HTML works.
6. **Wave 3,** at most three agents: `ml-engineer` on `detectors.md`, following the registered design; `ml-engineer` on `case-study.md`, on disjoint files; then audit pass 5b.
   - TWO-RUN, TRUNC, RETILE and SHUFFLE all fit `adversary.Bench` as extra blocks of windows: truncation is a window with NaN after the cut.
   - `generate` gets an opt-in `placement` argument; seed 20261029 must reproduce byte for byte.
7. Waves 4 to 5, as `docs/ITERATIONS.md` plans them. Wave 6, the learning page, is dropped.
