# Brief — the detector benchmark

- **Agent:** `ml-engineer` (opus, high). Owns the new module `python/olsprime/bench/detectors.py` and its tests. Does not edit `adversary.py`, `invariance.py` or `twins.py` except for a change audit pass 5b approves.
- **Starts only after** the pre-registration (`prereg.md`, new section of `docs/PROTOCOL.md`) is audited and committed.
- **Motto:** we should be more ambitious in how hard we try to make our own detector lose, never in what we claim when it wins.

## Goal

One command scores every registered detector on one leak population and its honest twins, and writes `detectors.json` and `detectors.md` with the registered metrics only.

## Build

1. Each detector as a pure function `(leak or model, bars, schedule) -> per-cut flags`, defined exactly as the protocol states. Reuse `bench/perturb.py` and `bench/invariance.py` for FI; never re-implement H1.
2. **Tests first, on synthetic bars** (`bench/synthetic.py`):
   - each detector catches a planted leak it must catch and passes an honest function, by name;
   - a leak built to fool each detector alone (one per detector) is missed by that detector and caught by another, so the union is tested;
   - the pre-registered predictions for Fonseca's classes, if that corpus exists, are tests too.
3. **Determinism.** Two runs give byte-identical `detectors.json` (the twins' and adversary's precedent: `runs/2026-10-30-twins-2/`).
4. **Throughput.** The adversary took 3 min 15 s with 8 workers for 10,000 leaks. Measure each detector's cost on 200 leaks of the development seed 51118, on synthetic bars, never on the fresh seed, and write the projection here before any real run.

## Runs (wave 4, `experiment-runner`)

- From a clean clone at the commit audit pass 5b passed. Every read through the seal; the fresh seed as registered.
- First the descriptive run on seed 20261029, then the confirmatory run on the fresh seed, each in its own folder under `runs/`, then a second run of the confirmatory one for byte identity.
- Rows for `docs/RESULTS.md`, drafted by `experiment-runner`, written by the orchestrator after audit phase 2.

## Done when

The tests pass on Windows and in WSL2, audit pass 5b gave GO, both runs and the identity check are done, and the rows are drafted.
