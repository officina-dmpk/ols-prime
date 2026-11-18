# Brief — the case study's two analyses (exploratory)

- **Agent:** `ml-engineer` (opus, high), after `detectors.md` or beside it if the files are disjoint. Owns a new module, `python/olsprime/bench/casestudy.py`, and its tests.
- **Exploratory, by construction.** These analyses run on the test months 2019–2024, already seen. No hypothesis is tested on them. Each call is logged as a contact with the data in `docs/PROTOCOL.md`'s change log, and everything is labelled "exploratory, test months" wherever it appears.
- **Refits nothing.** Read Report n°2's `series.npz` (WSL2 `691e7ea7…`) and Report n°3's by their SHA-256 and refuse any other.

## Why

The research report of 2026-11-18 names two less flattering readings of the 0.013 Brier skill that a referee will raise:
1. A 3-class target rewards forecasting a move, not only its direction, so part of the skill may be volatility forecasting.
2. Nagel (NBER w34104) shows a ridgeless "complex" forecast reduces to volatility-timed momentum. Our OLS edge over softmax may load on known hourly effects.

## Do

1. **The split of the skill.** For `matrix-select`, `enc-ols` and `enc-softmax`, the Brier and log-loss skill of "move or no move" (neutral against the rest) and of "direction given a move" (up against down, on the hours with a realized move), each against its own climatology, with the stationary bootstrap of Report n°2. Ventilated by year.
2. **The factor control.** Regress the hourly log-loss difference (`enc-ols` − `enc-softmax`, and `matrix-select` − `climatology-panel`) on hourly short-term reversal, momentum and volatility-timing signals computed from past bars only, with HAC standard errors. Report the coefficients and how much of the mean difference the factors leave.
3. Every signal is computed from bars known at the decision hour; H1's leak test applies to the factor builders as to any feature (a test).

## Done when

Both tables exist with their intervals, the contacts are logged, the tests pass, and audit pass 5b has read the module.
