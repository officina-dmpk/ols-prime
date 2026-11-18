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

## Phase 2 — the results and the paper

Recompute every number of the new rows from the runs' JSON, and every verdict from the registered rules. Read `paper/main.tex` claim by claim against `docs/RESULTS.md`, `paper.md`'s "Never claim" list and the citations' read level. GO, GO with fixes, or NO-GO, with each finding rated Blocker, Major, Minor or Nit.

## Done when

Each pass's findings are written to `.claude/briefs/iteration-5/audit-<pass>-findings.md`, and every one is fixed or logged by the orchestrator.
