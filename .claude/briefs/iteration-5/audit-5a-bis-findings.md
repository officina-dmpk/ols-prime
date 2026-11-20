# Audit pass 5a-bis — re-read of `prereg-draft.md` v2 (iteration 5)

- **Agent:** `leakage-auditor`, 2026-11-18. Read-only; this file was written by the orchestrator from the agent's report, condensed, with every replacement text kept verbatim.
- **Object:** `prereg-draft.md` v2 (uncommitted on `8473776`). Line numbers are v2's.
- **Verdict: register with fixes.** No Blocker. Seven Major fixes block registration (F1 to F7); eleven Minor. No third re-read is needed if the replacement texts are adopted verbatim; pass 5b's first task is then to diff the registered text against this file.
- **Contacts of the pass:** read `runs/2026-11-18-quantile-table/summary.json`, hashed `table.json` (digest matches). Scratch on `bench.synthetic` bars only, seeds 424242, 777, 5, 6; the scripts are copied to `audit-5a-bis-scripts/` (e1 to e7, no data read, no registered seed). Nothing written in the repository.

## 5a's findings

- Hold as §9 says: B2, M1, M3, M4, M6, M7, M9, M10, m1, m2, m4 to m11, the four nits.
- Hold with a new defect in the fix: B1 (F1), D1 (F2), M2 (F4), M5 (F3, m4, m5), M8 (F5, m1), m3.
- §1.5 matches `summary.json` in every number.

## Major (blocking)

- **F1. §4.4's 100 % assertion fails on valid input** (5a's own wording). One OR mask per leak: in a `Logic` or `WSum` leak one part can read a value already undefined on the original bars while truncation changes the other; the mask is then set in both runs. Synthetic, 4 % undefined `wick_ratio`: 33 flagged rows in 13 of 4,000 leaks. **Fix, verbatim:** "For each `(quantity, offset)` read that `RecordingView` lists, `isnan` of that read is taken in each run. A catch at a row is **through a missing read** when at least one read is missing in one run and not in the other there, whatever the output did; otherwise it is **through a changed value**." 0 exceptions on 97,885 flagged rows. Keep the OR mask for convention P only.
- **F2. H15's labels** (5a's own wording). An interval inside (−1, 0) was labelled "not below FI (the prior holds)" while TRUNC-0 is significantly below. **Fix, verbatim:** with [L, U] the Newcombe interval of TRUNC-0 minus FI, in points: **Sign:** L > 0 "above FI"; U < 0 "below FI"; otherwise "not separated from FI". **Margin, when the sign is not "above":** L > −1 "within 1 point"; U < −1 "by more than 1 point"; otherwise "1-point margin not resolved". **The prior** holds if the sign is "above"; is not refuted if "not separated" and L > −1; fails if "below"; is undecided otherwise. Deciding cell and qualifier unchanged.
- **F3. TWO-RUN's VWAP assertion fails on valid input.** `(v'·vwap')/v'` is not `vwap'` in floats, and the clip binds in 61 to 66 % of bars; 3 to 5 % of bars fail an exact check, 0 with a relative tolerance of 1e-12. Taker caps bind in 29 to 33 % of bars at σ = 1.0. **Fix:** assert on `vwap'` as constructed; checks on stored columns use 1e-12; `_check_valid` on rows t + 1 .. t + 10 only; report per σ the share of bars where the clip and each cap bind.
- **F4. TRUNC-1's change not carried through.** Shared compared rows no longer true; TRUNC-1 is a date-shift replicate like RETILE but was kept in the primary union and pairs; M1's mask covers t − 10 .. t only (the faithful TRUNC-1 flagged M1 at 7 of 16 synthetic cuts through row t + 1). Row t + 1 is scored at H1's cuts on the real bars by reasoning, not by run. **Fix:** TRUNC-1 = TRUNC-0 run at cut t + 1, one code path; assert row t + 1 exists and is scored at every cut of both schedules, count cuts where it cannot flag; TRUNC-1 a secondary row of the union and out of §4.7's pairs (six pairs, five descriptive); report TRUNC-1 against TRUNC-0 as the one-bar date shift; extend M1's mask or give its verdict per detector and schedule.
- **F5. The development digest pins too little.** `render()` rounds to 3-4 digits. **Fix:** n = 10,000; hash `repr(leak.expr)`, the output and the tags, one line per leak; record the numpy version; `generate(placement="quantile")` loads the registered bytes of `table.json`, refuses on a digest mismatch, never rebuilds the table.
- **F6. §7.1 lets FI's confirmatory rate be estimated early.** **Fix, verbatim:** "Before 5b's GO, no detector runs on real bars with a `quantile` population. FI and SHUFFLE run on real bars only with seed 20261029, `h1-bands`, as already run."
- **F7. No rule for an assertion failing on the one-shot seed.** **Fix, verbatim:** "Every assertion and gate is evaluated first, on the descriptive run and then on the confirmatory run, and writes only pass or fail and counts. No rate or per-leak verdict is written or printed until all pass. A failure stops the run; the fix is logged and re-audited; the next run is reported as run after a stopped attempt."

## Minor

- **m1.** §1.6 binds nothing; line 14 "removes that one tie" contradicts §1.5. Reword: "replaces the draw by H1's bands with a draw by the pre-2019 bars; the overlap remains (§1.5)". `position` strata cannot isolate the placement (4,815 `inside`, 520 of them thresholds, neutral seed). Register the **placement-invariant subset** (leaks drawn with no `_threshold` call; 8,258 of 10,000 on a neutral seed): FI's share and H15's difference on it and its complement, never deciding. Add to "may not": FI's rate here is free of H1's bands. Do not touch the levels or the table.
- **m2.** P's "missing exactly where the read mask is set" fails for `LogRatio`/`Rel` (a zero level). Reword the exception: "unless the original output is already missing at every scored compared row where truncation removes a read". Mask identity for binary roots only.
- **m3.** H16 should be bench assertions, not a hypothesis; `HYPOTHESES.md` gets H15 only. Fonseca's classes need a verdict per class and detector: "every cut", "never" or "not predicted". FI on M2: flagged unless bar t + 1's high is below two thirds of bar t's close.
- **m4.** TWO-RUN: drop "as `perturb.py:427-430` does" (it adds 1e-3); "undefined iff undefined" a coded assertion; `(10, 9)` always drawn, rows past the series discarded; "1 run" is run 1.
- **m5.** TWO-RUN's law blows up the body (σ = 0.1: median body 0.019 → 0.096, fill 0.46 → 0.81; σ = 1.0: body 0.93). Say so; report these statistics on the perturbed bars.
- **m6.** Record `placement` and the table's digest in the new run's JSON.
- **m7.** First-m-cuts order: by date, then by pair.
- **m8.** Cancelled controls: the conventions they run under; node order depth-first.
- **m9.** H15's qualifier: "opposite sign" means opposite to the deciding cell's point difference.
- **m10.** The quantile contact: pooling, levels, pre-2019 rows were in v1 at `8473776`; zeros and shares in 5a. Only `method="linear"` and "run once" have no committed witness: write "not verifiable" for those two in the change log.
- **m11.** `docs/PROTOCOL.md` still says the extreme-shape cut and H14 run in iteration 5: date their status at registration.

## Questions

- **a.** Digest by a change-log line before 5b's GO: acceptable, under F5 and F6; the line adds only the digest, the commit and the numpy version; §1.3 normative if they disagree; 5b reproduces the digest on the official run's machine.
- **b.** Faithful TRUNC-1: yes, as a date-shift replicate (F4). Synthetic: 966 of 1,053 reach-1 leaks caught (v1's arm 0); 0 of 800 honest twins; any-cut verdict differs from TRUNC-0's for 57 of 4,000 leaks, of the order of H15's 1-point margin.
- **c.** Before registering: F1 to F7, m1, m3. Others can be logged.

## Clean

Convention M equals G on the mirror for a single `Cmp`, row by row, under `target` and `probs` (8 rows differ of 2,628 leaks, all exact ties; the undefined-read case exercised). P's assertion matched 4,000 of 4,000. TWO-RUN's seeds collide with nothing. RETILE's 28 ends right. H15 = D1. The quantile script reads through the seal and keeps 502 unscored rows per pair.

## Not covered by any run

That the real bars' last scored row is their last row; that BTC and ETH have no zero-volume day; that stored bars after t + 10 pass `_check_valid`; freqtrade's `load_bt_data`.

## Bolder check

**The cut-date bootstrap, never deciding.** Run TRUNC-0 and FI on the long schedule's 64 dates; draw 2,000 subsets of 8 dates without replacement, the same on both pairs, registered seed 20261120; report the 2.5th to 97.5th percentiles of the any-cut difference beside the Newcombe interval. If the spread exceeds the 1-point margin, the paper says H15's verdict is date-dependent.
