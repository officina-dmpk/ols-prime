# Brief — pre-registration of the detector comparison

- **Author:** the orchestrator, after the reading (`reading-papers.md`) is in.
- **Writes:** a new section of `docs/PROTOCOL.md`, "Leak detectors measured against each other (iteration 5)", and draft hypotheses for `docs/HYPOTHESES.md`. Both are registered only after audit pass 5a, with dated change-log lines.
- **Motto:** ambitious in the comparison, never in what we claim before it runs.

## The design to fix before any detector touches a leak

1. **The population.**
   - A fresh draw of `olsprime.bench.adversary.generate(n, seed)`, with a seed that nothing has run and n large enough for the intervals wanted (10,000 again, unless the power argument says otherwise).
   - The 10,000 leaks of seed 20261029 are descriptive only: H1's catch rate on them is known, and its misses were studied.
   - Each leak keeps its honest twin; each detector also runs on the twins, and a twin flagged is a false positive.
   - **The fresh seed is protected.** The generator draws leak i from its own stream, so any run of n' leaks is the first n' of the population. Development and throughput runs use the development seed 51118 only, never reported. The fresh seed is chosen at registration, and its first use is the official run after audit pass 5b.
   - **The generator's bias, stated or removed.** It places half its thresholds inside H1's perturbation bands (`BANDS`, `perturb.py`) and half outside, which is built around future invariance. Decide, before the run, whether the confirmatory population keeps that placement, and say what follows for each detector. Audit pass 5a judges it.
2. **The bars.** BTCUSDT and ETHUSDT daily, as the adversary. Optionally a second panel (hourly bars of a sub-panel) as a description of how far the rates carry. Every read goes through the seal.
3. **The detectors**, each defined exactly: what is changed, at which cuts or dates, what is compared, and the tolerance (bit for bit, or a stated ε).
   - **FI:** H1's ×3 / ÷3 perturbation at H1's 16 cuts, as in `bench/invariance.py`.
   - **Truncation**, after freqtrade: the bars after the cut are removed, in two variants: the series ends at the cut, or one bar later. The comparison covers the rows at or before the cut that exist in both runs.
   - **Re-tiling**, after Causify's DataFlow (arXiv 2512.23977): the series is cut into windows and run window by window; the rows each window shares with the full run are compared.
   - **Default two-run:** a perturbation of the future fixed without H1's bands (to fix after the reading: Fonseca's §8.3 says which), at dates drawn with a fixed seed.
   - **Future-shuffle twin as a detector:** `bench/twins.py`'s K = 8 twins per cut.
   - **The union** of all of them.
   - Fonseca's static checker cannot run on Python (the paper's own DSL only, per the search); it is not an arm.
4. **The metrics.** For each detector, the raw share of leaks caught at one cut at least, with its Wilson 95 % interval; the honest twins flagged, out of how many can be flagged at all (a twin constant at the compared rows cannot be); the per-family rates; pairwise McNemar tables, with exact p-values, over the same leaks. No adjusted "mutation score".
5. **Fonseca's classes on our bars,** if the reading allows: a small hand-written corpus of M1, M2, M3 leaks and FP1, FP2, FP2b clean cases, written before any detector runs on it, each with the verdict predicted for each detector.

## Draft hypotheses (numbered at registration)

- **Truncation against FI.** Prior, written now: truncation catches at least as many leaks as FI, because a missing bar makes every comparison with it false. A two-sided McNemar test decides whether they differ; the direction is reported either way.
- **The union.** The union of all the detectors catches strictly more than the best single detector: McNemar, one-sided, p < 0.05.
- **Honest twins.** No detector flags more than 0.1 % of the honest twins that can be flagged. A detector above that is reported as unusable at its tolerance, not tuned afterwards.

Audit pass 5a may reword, add or remove any of them. Nothing changes after a detector has touched the fresh population.

## Variants

None of these is a strategy variant: the variant count of `docs/RESULTS.md` stays at 21.

## Done when

The section and the draft hypotheses are written, audit pass 5a has read them, every finding is fixed or logged, and the registration is committed before `detectors.md` touches the fresh population.
