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

## Wave 3 scope (added 2026-11-18, after the registration commit `6044037`)

- **Build and test only, on fake series.** In wave 3 the module is written and tested on synthetic `series.npz`-shaped arrays built in the tests (the keys and dtypes of `report2.py`'s `series.npz` section, around line 604) and on `bench.synthetic` bars. **No call on a real `series.npz`, no read of real bars, no vault.** Each real call is a logged contact; the one real run happens after audit pass 5b has read the module, launched and logged by the orchestrator.
- **Ownership:** writes `python/olsprime/bench/casestudy.py` and `python/tests/test_casestudy.py` only. Read-only: every other file, `report2.py` and `report3.py` included (import from them; if they must change, stop and report). Another `ml-engineer` works in parallel on `bench/detectors.py`, `bench/adversary.py` and their tests: never touch those. Never `git add`, never commit.
- **The refusal by digest** is tested: a fake `series.npz` with a wrong SHA-256 is refused; the registered digests are constants (Report n°2's WSL2 `691e7ea7…`: take the full digest from `docs/RESULTS.md` or the report's run folder record, never by opening the file; Report n°3's likewise). If a full digest cannot be found in the committed text, leave a named constant `None` and say so: the orchestrator fills it.
- **Past-only signals, tested as H1 tests features:** each factor builder (reversal, momentum, volatility timing) is checked with the future-invariance perturbation of `bench/perturb.py` on synthetic bars, and with a planted future-reading builder that the test must catch.
- **Statistics:** the stationary bootstrap of Report n°2 (reuse its function, do not re-implement), HAC standard errors (state the lag rule in the docstring, fixed before any real run), climatology per target as Report n°2 defines it.
- **Labels:** every table and JSON key the module writes carries "exploratory, test months".
- **Verification:** `cd python && uv run ruff check . && uv run ruff format --check . && uv run pytest tests/test_casestudy.py`, then the full `uv run pytest`.

## Done when

- **Wave 3:** the module and its tests pass; the report lists the files changed, the lag rule, and the CLI command the orchestrator will run on the real `series.npz` after 5b.
- **After 5b:** both tables exist with their intervals, and the contacts are logged.
