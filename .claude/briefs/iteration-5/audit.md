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

## Pass 5b-bis — the fix wave's diff, before the frozen commit is named

**Added 2026-11-19**, after pass 5b's GO with fixes on `6ab7e3e` (code digest `8607e7c4…`). The object is the diff from `6ab7e3e` to the fix commit only; the rest of the tree keeps pass 5b's GO.
1. **Each finding of `audit-5b-findings.md` against its fix:** M1 (platform pin before any bar is read; platform recorded), M2 (the guard: every registered command line, every forbidden role, real bars only with the two registered seeds), M4 (both qualifier cells; the per-leak file, written only when every check passes, deterministic, sufficient for phase 2), Minors 5–11 and 14, the nits. A fix that does more than its finding asks is a finding.
2. **The new tests are independent** of the code they test (scalar rewrites of X3, X6, X6b, X9, X11, X12), and the mutant test kills the 16 mutants on a temporary copy without touching the repository.
3. **The dated change-log line of 2026-11-19 after pass 5b** matches the code word for word: the replaced predictions (Minors 5 and 6), the metrics now implemented (Minors 7 and 8), the per-leak file, the command lines and seeds 29119 and 29120, the comparisons of Minor 13, and the case study's choices.
4. **Reproduce the development digest on Windows at the fix commit** (`e03f78b1…bc48`), check that the generator's draw path did not change (`adversary.py` and the goldens), that the allowlist gained no rule, and that no test or default executes 20261118, 20261119 or 20261120.
5. **`.claude/briefs/iteration-5/wave4.py`**, the unattended script of the official runs: it stops at the first failure, runs the confirmatory command only after a passing descriptive run, and compares what the protocol says it compares.

Verdict: GO, GO with fixes, or NO-GO, written to `audit-5b-bis-findings.md`. A GO lets the orchestrator name the frozen commit (ruling 1's line) and start wave 4.

## Phase 2 — the results and the paper

Recompute every number of the new rows from the runs' JSON, and every verdict from the registered rules. Read `paper/main.tex` claim by claim against `docs/RESULTS.md`, `paper.md`'s "Never claim" list and the citations' read level. GO, GO with fixes, or NO-GO, with each finding rated Blocker, Major, Minor or Nit.

## Done when

Each pass's findings are written to `.claude/briefs/iteration-5/audit-<pass>-findings.md`, and every one is fixed or logged by the orchestrator.
