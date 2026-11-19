# Brief — audit phase 2a: wave 4's results and the case study, before any row enters `docs/RESULTS.md`

- **Agent:** `leakage-auditor` (fable, high). Read-only and adversarial. Write only into `.claude/briefs/iteration-5/audit-2a-findings.md` and `.claude/briefs/iteration-5/audit-2a-scripts/`.
- **Phase 2b comes later,** in its own brief, once `paper/main.tex` exists: the paper, claim by claim. This pass is the numbers only.
- **Abdou's rule of 2026-11-19 (`CLAUDE.md`).** Propose a bolder check only if it would significantly improve the paper; otherwise none. Your agent file may still carry the older line: this brief overrides it. The depth of the audit does not change.

## What exists

Wave 4 ran on Windows on 2026-11-19, 15:17–15:59 UTC, at HEAD `f12b9b5`. The frozen code is commit `b71ba65`, code digest `3b59007a…`, unchanged since. Your sources:
- **The log:** `runs/2026-11-19-wave4.log`.
- **The protocol line** "2026-11-19, after wave 4 and before audit phase 2" in `docs/PROTOCOL.md`'s change log. It holds the contacts and the SHA-256 of every output.
- **The runs:**
  - `runs/2026-11-19-h1-adversary-replay/`, §1.3's replay of iteration 3;
  - `runs/2026-11-19-detectors-descriptive/` (seed 20261029, `h1-bands`);
  - `runs/2026-11-19-detectors-confirmatory/` (seed 20261118, `quantile`, its only draw);
  - `runs/2026-11-19-detectors-confirmatory-rerun/` (`--workers 4`).
- **The registered rules:**
  - `docs/HYPOTHESES.md`, H15;
  - `docs/PROTOCOL.md`, "Leak detectors measured against each other (iteration 5)";
  - the dated lines of 2026-11-18 and 2026-11-19 in its change log. The 2026-11-19 line after pass 5b replaced some predictions and fixed the JSON paths of the metrics, the denominators and the sensitivity.
- **The per-leak file `verdicts.jsonl`:** a JSON header line, then one array per leak, with the bit vectors `flags`, `finite` and `mirror` in packbits hex, little bit order. `python -m tests.test_detector_verdicts <folder>` recomputes from it; write your own reader as well, as pass 5b-bis did with Y3.
- **The case study's one real call:** `runs/2026-11-19-casestudy/` and `runs/2026-11-19-casestudy.log`. The orchestrator adds its contact line to `docs/PROTOCOL.md` before you start. If the folder is missing or the run failed, say so and audit the rest.

## Do

1. **Recompute every number that will become a row or a sentence,** from the files and not from `detectors.md`, for both detector runs:
   - **The any-cut shares** of every registered detector variant under the three denominators: all leaks, not-constant, and `designed: no`. Give each Wilson interval.
   - **The honest twins flagged.**
   - **The pairwise McNemar tables.**
   - **The union and its misses,** with how many of them are constant.
   - **H15's deciding cell:** Newcombe method 10, the sign, the margin and the prior's label, by the rules of `docs/HYPOTHESES.md` H15.
   - **The qualifier's cells** (`metrics.h15.qualifier.cells`) and whether it fires.
   - **The cut-date bootstrap's percentiles,** and whether the registered "date-dependent" sentence fires.
   - **The conventions sentence and the sensitivity** "ignores outputs that turn missing".
   - **The placement-invariant subset and its complement** (descriptive run).
   - **The class counts in `reported.classes`.**

   Name the JSON path of each number, and put your value beside the run's.
2. **Read the `wave4.py` that actually spent the seed** (`git diff b71ba65..f12b9b5 -- .claude/briefs/iteration-5/wave4.py`) against the log. Pass 5b-bis read the previous version and a dry run of the amended one, not the file as run. Check:
   - each step's stop conditions;
   - the HEAD and provenance checks after each step;
   - the byte comparison of the rerun.

   Recompute every SHA-256 the protocol line cites.
3. **Minor 3 of pass 5b-bis is deferred, not fixed** (Abdou's rule): its 21 mutants are not written. Instead:
   - re-read the five lines its mutants touch (`detectors.py:1016`, `1018`, `1031`, `1172` and `1208`) at the frozen code;
   - check, in both runs' `reported.classes`, that the predicted counts equal the flagged counts wherever a prediction is registered;
   - say whether any registered sentence rests on a `check_classes` count that these two checks cannot verify. If one does, rate it.
4. **The case study:**
   - **The inputs:** check them by digest (`691e7ea7…` and `e8381799…`). `runs/vault/` must not be read; check that the run did not read it.
   - **The cut:** no bar at or after `DEVELOPMENT.end` reaches a signal.
   - **The labels:** every key and table says "exploratory, test months".
   - **The choices fixed in the 2026-11-19 line after pass 5b:** the payoff regressors as an attribution after the fact, the signal definitions, and HAC with a Bartlett kernel and 168 lags. Check them against what ran.
   - **The numbers:** recompute what the JSON lets you recompute.
5. **The replay:** confirm `adversary.json` equals iteration 3's outside `provenance`, and that the manifest digest is the same.

## Never

- Run `detectors run`, `adversary`, `casestudy`, or anything else that reads real bars. Seeds 20261118, 20261119 and 20261120 are spent, and a rerun would be a stopped attempt (§7.4). Recompute from the files.
- Open `runs/vault/` or the validation year.
- Run `git stash`, `checkout`, `reset`, `add` or `commit`. The code digest hashes this working tree.

## Report

- **The verdict:** GO, GO with fixes, or NO-GO. Rate each finding Blocker, Major, Minor or Nit.
- **One table of every recomputed number:** JSON path, the run's value, your value, and whether they agree. The orchestrator writes the `docs/RESULTS.md` rows from it.
- **The sentences the paper may state as they are,** and the ones it must word differently.
