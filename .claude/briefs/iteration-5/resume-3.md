# Resume 3 — iteration 5 after the registration, before wave 3

- **Written:** 2026-11-18, by the orchestrator of iteration 5's second session, which hands off at about 225k tokens of context.
- **State:** branch `iteration-5`. The registration is committed only once Abdou gives the go-ahead. Check `git log -1`: if the last commit is not "Iteration 5: the detector comparison registered", the registration is still uncommitted, so ask Abdou before anything touches seed 20261118. Nothing is pushed. Never `git add -A`: `.claude/worktrees/` and two iteration-4 drafts stay untracked on purpose.
- **Usage at hand-off:** 50 % of the 5-hour window, 16 % weekly (all models), 17 % weekly (Fable). Check `get_usage` before each wave.

## Done in session 2

- `prereg-draft.md` went v1 → v2 (pass 5a) → v3 (pass 5a-bis), and was then registered:
  - `docs/PROTOCOL.md`, section "Leak detectors measured against each other (iteration 5)", with a change-log line;
  - `docs/HYPOTHESES.md`, H15 (TRUNC-0 against FI, two labels and a qualifier), with a change-log line.
  - The controls are bench assertions, not hypotheses (§3.4).
- **Audit pass 5a-bis: register with fixes, no Blocker** (`audit-5a-bis-findings.md`, scripts in `audit-5a-bis-scripts/`). F1 to F7 and every Minor were fixed; the dispositions are in `prereg-draft.md` §10. No third re-read is needed, since the replacement texts were adopted verbatim.
- **The quantile table** was computed with `quantile_table.py`; output in `runs/2026-11-18-quantile-table/`, SHA-256 `527e01ba…`. It is a logged contact. `table.json` is outside git and is rebuilt by the script.
- `docs/RESULTS.md` has the dated correction row of the constant misses; `docs/DATA.md` has the Terms of Use line.

## Next steps

1. **Update `detectors.md` before wave 3.** It predates the registration. Changes to make:
   - **Ownership:** `adversary.py` must now change, for the `placement` and `table_path` arguments of `generate` and `draw_leak` (outside `AdversaryConfig`), the `quantile_table` builder, and evaluation under conventions M and P.
   - **Byte identity:** seed 20261029 must reproduce `adversary.json` byte for byte, and `twins.py:399`'s write-back must still pass.
   - **Assertions:** every registered assertion is a test (§3.4, §2.3, §2.4, §2.5, §4.4, §4.9).
   - **Stop rule:** follows §7.4.
   - **Synthetic only:** wave 3 runs on synthetic bars, with seeds 51118 and 51119 only.
   - **Digest:** the development digest of §1.7 (n = 10,000, `repr(expr)`, output and tags, numpy version) goes into a dated change-log line before 5b's GO.
2. **Wave 3, at most three agents:**
   - `ml-engineer` on `detectors.md`;
   - `ml-engineer` on `case-study.md`, on disjoint files;
   - then audit pass 5b.
3. **Pass 5b opens with two checks:**
   - diff the registered section of `docs/PROTOCOL.md` against `audit-5a-bis-findings.md`;
   - read hardest the parts the orchestrator wrote beyond the auditor's verbatim texts: §3.4 (assertions list), §4.14 (placement-invariant subset), §4.15 (cut-date bootstrap, seed 20261120), FI's rule on Fonseca's M2, M1's row mask, and §1.7's `table_path`.
4. Before citing any source in the paper, re-read its passage verbatim. This holds for Fonseca, Garnelo & Czarnecki, Causify, and anything from `reading-credits.md`.
5. Then waves 4 to 5, as `docs/ITERATIONS.md` plans them. Wave 6, the learning page, is dropped.
