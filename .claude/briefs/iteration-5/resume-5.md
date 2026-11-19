# Resume 5 — iteration 5 after wave 4, before audit phase 2

- **Written:** 2026-11-19, by the orchestrator of iteration 5's fourth session, after wave 4. Read `resume-4.md` for what came before.
- **Branch:** `iteration-5`. Nothing is pushed. Never `git add -A`: `.claude/worktrees/` and the two iteration-4 drafts (`outcome-draft.md`, `results-draft.md`) stay untracked on purpose.

## What this session did

1. **Committed wave 3** at `6ab7e3e`. This is the tree pass 5b audited (code digest `8607e7c4…`).
2. **Ran the fix wave** (`fixes.md`, `fixes-progress.md`) and committed it at `b71ba65`, which is **the frozen commit**.
   - The orchestrator re-ran everything itself:
     - the full suite: 1,743 passed, 5 skipped;
     - the mutant test: 16 of 16 killed;
     - the development digest `e03f78b1…bc48`;
     - ruff on the touched files;
     - synthetic runs through `wave4.py` at n = 200 and at n = 10,000, with all assertions passing and the per-leak recomputation agreeing.
3. **Audit pass 5b-bis** (`audit-5b-bis-findings.md`): GO with fixes, no Blocker; 1 Major, 3 Minor, 9 Nits. The run path needed no change.
   - `wave4.py` was fixed (Major 1, Minor 1, N2, N4, N5, N9). The auditor's dry run `y2_wave4_dry.py` completes on it.
   - The text was fixed (N1–N3). Minor 2 is logged: the code digest pins the Windows working tree. An LF clone gives `3778cfca…`, an all-CRLF clone `77851c2e…`. The orchestrator recomputed both from the blobs.
   - The line naming `b71ba65` the frozen commit (pass 5b's ruling 1, verbatim) was committed at `f12b9b5`. That commit touches docs and briefs only.
4. **Wave 4 on Windows**, 15:17–15:59 UTC, at HEAD `f12b9b5`. Every step passed:
   - step 0b, the platform digest;
   - §1.3's replay, equal to iteration 3's outside `provenance`;
   - the descriptive run, with all assertions and gates passing;
   - the confirmatory run on seed 20261118, its first and only draw, with all assertions and gates passing;
   - the identity rerun, byte for byte.

   The contacts and output hashes are in `docs/PROTOCOL.md`'s dated line "after wave 4 and before audit phase 2" (uncommitted). The outputs are:
   - `runs/2026-11-19-wave4.log` and `runs/2026-11-19-wave4-*.out`;
   - `runs/2026-11-19-h1-adversary-replay/`;
   - `runs/2026-11-19-detectors-descriptive/`;
   - `runs/2026-11-19-detectors-confirmatory/`;
   - `runs/2026-11-19-detectors-confirmatory-rerun/`.

## The headline, as the run printed it (not yet recomputed by audit phase 2; not yet in `docs/RESULTS.md`)

- **H15 (confirmatory, seed 20261118):**
  - TRUNC-0 minus FI is −3.75 points [−4.20, −3.32] (Newcombe, method 10).
  - The labels are: sign **below FI**, margin **by more than 1 point**, prior **fails**.
  - The qualifier is not triggered. In both runs' `detectors.json`, `metrics.h15.qualifier.triggered_by` is empty and `convention_dependent` is false. Phase 2 recomputes both cells from `h15.qualifier.cells`.
- **The cut-date bootstrap** gives −6.38 to −2.95 points. The registered rule (§4.15) fires: the spread is wider than the 1-point margin, so "the paper says that H15's verdict is date-dependent".
  - Both percentiles are below −1 point. That is a fact about the subsets' point differences. The label itself comes from the Newcombe bounds, so do not write "the label holds across that range".
  - Phase 2 and the paper state the registered sentence and the two percentiles together, as facts, without softening either.
- **The real bars' class counts** (`reported.classes`, both runs):
  - `cannot_flag_last_row` is 0 on every schedule;
  - FI on M2 is predicted and flagged at 16 of 16 and 128 of 128 cuts, with no "not predicted" cut.
- **Any-cut shares, all leaks, H1's 16 cuts:**
  - FI: 98.57 %
  - TRUNC-0/G: 94.82 %
  - TRUNC-0/M: 95.22 %
  - TRUNC-0/P: 100 %
  - TRUNC-1/G: 94.04 %
  - TWO-RUN (σ 0.1, 2 runs): 85.60 %
  - SHUFFLE (8 twins): 98.47 %
  - RETILE/G: 95.09 %
  - the union: 99.54 %, missing 46 leaks, all of them constant at H1's compared rows.
- **The conventions sentence:** "Truncation's rate lies between 94.82 % and 100.00 % depending on how a missing bar is read (G to M: 94.82 % to 95.22 %)".
- **The sensitivity "ignores outputs that turn missing":** TRUNC-0/G falls to 84.14 %, and P falls to 0 %.
- **The descriptive run (seed 20261029, `h1-bands`):** TRUNC-0 minus FI is −5.53 points [−6.06, −5.02].
  - The bootstrap gives −7.90 to −4.73 points.
  - On the placement-invariant subset, the difference is −4.39 points; on its complement, −11.49 points.

## Next steps, in order

1. **Ask Abdou to commit this session's text:**
   - `docs/PROTOCOL.md`: the contacts line;
   - `docs/ITERATIONS.md`;
   - this file.

   Stage by name.
2. **Minor 3 of pass 5b-bis (tests only, outside the code digest).** Add tests so that `check_classes` counts each kind of disagreement:
   - a missed flag under P;
   - a flag at a cut that cannot flag;
   - a miss of FI on M2 at a predicted cut;
   - the primary TWO-RUN arm's read-split row strictly below the 8-run row;
   - `control_can_flag` on a long-schedule-only `v`.

   Then add mutants `n1` to `n5` (see `audit-5b-bis-scripts/y4_new_mutants.py`) to `test_detector_mutants.py`, for 21 in all. The code must not change; the code digest stays `3b59007a…`.

   **Deferred on 2026-11-19 under Abdou's rule** (`CLAUDE.md`), provisionally: audit 2a's step 3 decides whether the deferral holds. It is logged, and it is reported as not run. These tests guard future runs against a silent stop; they change no number of wave 4. Instead, phase 2 does two things:
   - it re-reads the five lines the mutants touch (`detectors.py:1016`, `1018`, `1031`, `1172` and `1208`);
   - it checks the class counts directly in both runs' `reported.classes`, as predicted against flagged.
3. **Done: the case study's one real call,** 2026-11-19, 19:42:24–19:44:37 UTC.
   - It ran at HEAD `1088aac`, with code digest `3b59007a…`, and wrote `runs/2026-11-19-casestudy/`.
   - Its contact line is the last line of `docs/PROTOCOL.md`. **Never run it again:** any other call is a new contact.
   - Abdou chose to keep the case study on 2026-11-19.

   The original step, for the record: the case study's one real call (`case-study.md`, `bench/casestudy.py`). It reads Report n°2's and Report n°3's `series.npz` by their SHA-256, and it is a logged contact. Its choices are fixed in the 2026-11-19 line after pass 5b: payoff regressors as an attribution after the fact, the signal definitions, and HAC with a Bartlett kernel and 168 lags.
4. **Audit phase 2.** It is split in two parts.
   - **2a, the numbers: done, GO with fixes** (5 Minor, 8 Nits, all wording; `audit-2a-findings.md`). Its fixes are logged in `docs/PROTOCOL.md`'s line "after audit phase 2a". The rows and the paper carry its wording (Minors 1–5), and the Minor 3 deferral holds.
   - **The paper's first draft exists** in `paper/`, written under `paper-draft-1.md`. It compiles with MiKTeX: 17 pages, `make_numbers.py` regenerates `numbers.tex` byte for byte.
     - Waiting for 2a's numbers: the abstract, §5, §8.4, and parts of §1, §4 and §10.
     - Flagged by its writer: sentences close to "OLS is attention" and "an exact ridge state" (§1, §2, §7, §8.3), and statistical methods named without a citation (no reading note).
   - **2b, the paper's claims.** It comes once `paper/main.tex` exists.

   The original step (`leakage-auditor`, `audit.md` "Phase 2"):
   - recompute every number of the new rows from the runs' JSON and `verdicts.jsonl`, and every verdict from the registered rules;
   - check the qualifier and the bootstrap sentence;
   - read the `wave4.py` that actually spent the seed (diff `b71ba65..f12b9b5`) against `runs/2026-11-19-wave4.log`: pass 5b-bis read the previous version and the dry run of the amended one, not the amended file as run;
   - then the paper, claim by claim.
5. **Write the record:**
   - the `docs/RESULTS.md` rows, after phase 2;
   - the outcome and the next step in `docs/ITERATIONS.md` (a bolder one only under `CLAUDE.md`'s rule of 2026-11-19);
   - the paper draft (`paper.md`, `paper/main.tex`: its "Never claim" list, the AI use reported, the endorser still needed).
6. **The teacher's learning page.** It is in French, published as an Artifact, and kept outside the repository, as decided at iteration 4's wrap-up. Its link goes in the outcome.
7. **Commit with Abdou's go-ahead.**

## Candidate bolder steps (none registered; all skipped on 2026-11-19)

Abdou's rule of 2026-11-19 (`CLAUDE.md`): to reach the arXiv paper sooner, a bolder step is taken only when it would significantly improve the work. None of the candidates below passes that bar for the first version of the paper, so none is run.

- **The auditor's (5b-bis):** measure the platform effect, rather than only refusing it.
  - Run the synthetic n = 10,000 line on Windows and in WSL2.
  - Diff the two `verdicts.jsonl` files leak by leak: how many verdicts and H15 cells change.
  - It needs no real-bar contact and no confirmatory seed.
- **The fix agent's:** make mutants part of the frozen evidence.
  - Have a different agent write mutants blind.
  - Report the kill rate in `docs/RESULTS.md` beside the detectors' rates.
- **From `docs/ITERATIONS.md`:** a population of realistic pipeline bugs plus a labelled corpus of community strategies, and European electricity (ENTSO-E) as a second domain.

## Where the next session runs

In this checkout (`C:\Users\abdou\ols-prime`), not in a new worktree. `runs/`, `data/` and the working tree whose code digest is `3b59007a…` exist only here.

## Constraints still in force

- Seeds 20261118, 20261119 and 20261120 are spent. They are never drawn again: any rerun is a stopped attempt reported as such (§7.4).
- No real-bar run beyond the case study's one call.
- The vault and the validation year stay sealed.
- Every result goes through `leakage-auditor` before it is reported. A subagent's report is a claim.
- Binance is history only. Never place orders and never handle keys.
- Commit only with Abdou's go-ahead; push nothing.
