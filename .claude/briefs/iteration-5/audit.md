# Brief — audits of iteration 5

- **Agent:** `leakage-auditor` (fable, high). Read-only, adversarial.
- **Motto:** we should be more ambitious in how hard we attack the design and the claims, never in what we claim we found.

## Pass 5a — the pre-registration, before any detector touches a leak

Read `docs/PROTOCOL.md`'s new section "Leak detectors measured against each other (iteration 5)", the draft hypotheses, `prereg.md` and `reading-papers.md`. Find:
- a detector defined loosely enough that two honest implementations would give different flags;
- a comparison rigged for future invariance: the generator places half its thresholds by H1's bands; truncation or re-tiling defined so they cannot catch what they should; tolerances that differ between detectors;
- a detector's result that rests on a convention of the generator: an out-of-series row reads NaN and every comparison with NaN is false, so truncation's rate depends on it, as future invariance's depends on the band placement;
- a denominator that hides the twins that cannot be flagged, or a metric chosen after seeing rates;
- any contact with the fresh seed before registration;
- a claim the paper could not support from the planned outputs.

## Pass 5b — the code, before the official runs

`bench/detectors.py`, `bench/casestudy.py`, their tests, and any change to `adversary.py` or `twins.py` from `misses.md`. Check that each detector is the registered one, that the tests would fail on the planted fooling leaks, that the case study's factor signals use past bars only, and that every read goes through the seal.

**Updated 2026-11-18, after the registration (`6044037`).** Pass 5b opens with these checks, in order:
1. **Diff the registered text against pass 5a-bis.** Compare `docs/PROTOCOL.md`'s section "Leak detectors measured against each other (iteration 5)" and H15 in `docs/HYPOTHESES.md` with `audit-5a-bis-findings.md`: every replacement text of F1 to F7 adopted verbatim, every Minor carried through.
2. **Read hardest what the orchestrator wrote beyond those verbatim texts:** §3.4 (the list of assertions), §4.14 (the placement-invariant subset), §4.15 (the cut-date bootstrap, seed 20261120), FI's rule on Fonseca's M2, M1's row mask, and §1.7's `table_path`.
3. **Reproduce the development digest** (§1.7) from the change-log line, on the machine of the official run, and check that the line adds only the digest, the commit and the numpy version.
4. **Then the code against the registered text,** detector by detector and assertion by assertion (§3.4's list and the equivalence gates), with `.claude/briefs/iteration-5/detectors.md`'s checklist as a map, not as the norm.
5. **Seeds and contacts:** no test or default executes 20261118, 20261119 or 20261120; no new detector ran on real bars; `casestudy.py` was never called on a real `series.npz`; every caller of `generate`/`draw_leak` threads `placement` and `table_path` or provably keeps the default.
6. **The stop rule (§7.4)** is enforced by the CLI: no rate or per-leak verdict reaches an output file before every assertion and gate passes.

Verdict: GO, GO with fixes, or NO-GO, with each finding rated Blocker, Major, Minor or Nit, written to `audit-5b-findings.md`.

## Phase 2 — the results and the paper

Recompute every number of the new rows from the runs' JSON, and every verdict from the registered rules. Read `paper/main.tex` claim by claim against `docs/RESULTS.md`, `paper.md`'s "Never claim" list and the citations' read level. GO, GO with fixes, or NO-GO, with each finding rated Blocker, Major, Minor or Nit.

## Done when

Each pass's findings are written to `.claude/briefs/iteration-5/audit-<pass>-findings.md`, and every one is fixed or logged by the orchestrator.
