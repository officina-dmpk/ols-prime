# Progress — the detector benchmark (wave 3), ml-engineer

Resume from here. Brief: `detectors.md`. Normative design: `docs/PROTOCOL.md`, "Leak detectors measured against each other (iteration 5)".

## Milestone 1 — generator under `quantile` (done, 2026-11-18)

- `bench/adversary.py`: `Placement` (table + `_threshold` call counter) threaded through `_threshold`, the `_draw_*` functions and `_draw_combination`; `_draw_leak(seed, i, place)`; `draw_leak`/`generate` take `placement=` (default `h1-bands`) and `table_path=` (required with `quantile`). `build_table`, `table_bytes` moved unchanged; `parse_table` (refuses bytes that do not write back), `load_table` (refuses a digest other than `QUANTILE_TABLE_SHA256`; never rebuilds). The `h1-bands` branch of `_threshold` is untouched.
- `bench/detectors.py`: seed constants, `digest_line`, `development_digest`.
- Golden digests reproduce (both seeds, default and explicit `h1-bands`).
- **Development digest**, seed 51118, n = 10,000, `quantile`, registered table: `e03f78b187c1f7a7b62681a6c16214f7bd79d7f13b58459521cacb731ad9bc48` (numpy 2.5.4, Python 3.12.10, Windows 11). WSL2: pending.
- Placement-invariant subset on 51118: **8,316 of 10,000** leaks have no `_threshold` call (§1.6: 8,258 on a neutral seed).
- Tests (`tests/test_adversary.py`, appended): `test_the_default_placement_is_the_generator_of_iteration_3_bit_for_bit` (×2 seeds), `test_the_table_builder_gives_pinned_bytes_on_a_synthetic_input`, `test_a_quantile_threshold_consumes_exactly_one_draw` (×9 quantities), `test_leaks_drawn_without_a_threshold_are_the_same_under_both_placements`, `test_the_quantile_placement_needs_the_registered_table`, `test_the_registered_table_hashes_to_its_digest_and_drives_the_quantile_draw` (skips without the table). test_adversary.py: 43 passed.

## Notes

- `ruff` is not in the uv environment (`uv run ruff` fails: program not found); the repo has no ruff config and CI runs none; at `6044037` `ruff format --check .` would reformat 85 files under defaults. New files are kept clean under `uvx ruff check` (defaults).
- `.claude/briefs/iteration-5/quantile_table.py` still holds its own copy of `build_table` (not mine to edit); it can import `adv.build_table` now.

## Milestone 2 — detectors and conventions (core done, 2026-11-18)

- `adversary.py`: `CONVENTIONS`, `evaluate_under` (G is `expr.evaluate` itself; M and P compositional on atomic predicates), `outputs_under`; `Leak.outputs` split into `outputs` + `outputs_of` (same code, same bits).
- `detectors.py`: long synthetic pairs over the real dates (2,694 bars, `development_bars`; optional degraded variant), schedules, benches (FI = `adv.build_bench`; one truncation bench for TRUNC-0, TRUNC-1 and TRUNC-0 at RETILE's 28 ends; TWO-RUN with the registered draws and repair; SHUFFLE = `twins.build`; RETILE by really slicing, stacked series views), the row kernel `compare`, `judge_window`, `judge_retile`, `judge_all`, `cut_verdicts`.
- On the synthetic long bars the 16 H1 cut rows are §2's (502, 1048, 1233, 1597, 1994, 2100, 2143, 2664); 28 RETILE ends; no cut whose t + 1 is the last row.
- Probe (200 leaks of 51118, degraded bars): the row kernel equals `adv.evaluate_fast` on FI at cut level for all 200. ms per unit: FI 1.7, truncation 1.0 per convention, RETILE 3.9 per convention, TWO-RUN 8.0, SHUFFLE 2.3. Bench build 22 s.
- TWO-RUN repair on synthetic bars: sigma 0.1, median body 0.019 -> 0.097, fill 0.47 -> 0.82, VWAP clip binds 60 %; sigma 1.0, body 0.95, taker base cap 31 %. (§2.5 registered: 0.019 -> 0.096, 0.46 -> 0.81, 0.93.)
- `detector_stats.py` + `tests/test_detector_stats.py` (18 passed): Newcombe method 10 pinned on Fagerland et al.'s worked example (Cavo 2012: -0.0621 [-0.1186, -0.0046]); exact McNemar (P = 0.052479); H15 labels, each branch of the prior, the qualifier; first-m curve; bootstrap.

## Milestone 3 — controls and Fonseca's classes

- **Order:** `tests/test_detector_classes.py` (M1 per schedule, M2 and its mirror under TRUNC-0 G/M, FI's M2 rule, M3 never, FP1/FP2 on close against the independent prediction) was written with its verdicts **before any detector ran on these classes** (2026-11-18). Constructors and the prediction are in `detectors.py`; nothing had been evaluated on them at that point.

- First run of the class tests: 16 passed, no verdict edited after the run.

## Milestones 4 and 5 — assertions, gates, stop rule, statistics, outputs (done)

- `process_leak` evaluates each leak, its honest twin, its mirror and its three cancelled controls (with the independent prediction) through every detector, and counts every assertion. `evaluate_population` runs it on processes that build their own benches (never sent across). `run_gates`: FI by `adv.check_equivalence`; TRUNC-0 on really truncated bars, TWO-RUN (sigma 0.1, runs 1-2) and SHUFFLE (8 twins) through `inv.outputs` + `inv.compare`. `run` evaluates every assertion and gate, then writes metrics only if all pass. `summarize` covers §4.1 to §4.15 and H15. CLI: `python -m olsprime.bench.detectors digest|run`, no seed default, `--synthetic` refuses the confirmatory seeds.
- Smoke run, 40 leaks, degraded synthetic bars: every assertion 0, gates pass.

### Checkboxes of the brief ("Assertions as tests")

- §3.1 honest twins: `test_no_detector_flags_a_past_only_twin`, `test_the_twin_check_sees_a_twin_that_reads_the_future`; CLI: "§3.1 honest twins never flagged".
- §3.2 cancelled controls = prediction: `test_the_cancelled_controls_equal_the_independent_prediction_run_for_run`, `test_the_cancelled_controls_on_close_follow_the_prediction`, `test_the_prediction_differs_from_a_wrong_one`, `test_the_control_is_built_at_the_future_node_of_largest_reach`.
- §3.3 classes: `tests/test_detector_classes.py` (16 tests) and `test_fonsecas_classes_pass_on_the_degraded_bars`; CLI: `check_classes`.
- §2 P: `test_under_p_trunc_0_flags_every_cut_but_the_exception` (both clauses), `test_conventions_on_atomic_predicates`, `test_m_on_a_single_cmp_is_g_on_its_mirror`, `test_convention_g_is_the_generators_evaluation_bit_for_bit`.
- §4.4: `test_every_truncation_catch_goes_through_a_missing_read`.
- §4.9: `test_a_single_cmp_leak_and_its_mirror_are_flagged_together`, `test_the_mirror_flips_the_operator_only`.
- §2.4: `test_retiles_flags_equal_windowed_trunc_0_at_the_28_ends`, `test_retile_really_slices_the_bars_and_its_stacked_view_is_the_series_view`.
- §2.3: `test_trunc_1s_row_t_plus_1_exists_and_is_scored_at_every_cut`, `test_trunc_1_refuses_a_cut_whose_next_row_is_not_scored`, `test_the_synthetic_bars_span_the_real_dates_and_hold_every_registered_schedule`.
- §2.5: `test_two_runs_draws_follow_the_registered_keys`, `test_two_runs_repair_keeps_every_registered_property`, `test_two_runs_repair_fails_loudly_on_an_invalid_bar`, `test_two_runs_repair_statistics_are_reported`.
- §4 gates: `test_the_gates_pass_and_see_a_broken_detector`, `test_the_row_kernel_equals_the_adversarys_fast_path`.
- Planted fooling: `test_a_leak_built_to_escape_one_detector_is_missed_by_it_and_caught_by_another` (×4).
- Stop rule: `test_a_failing_assertion_stops_the_run_before_any_rate` (files, stdout and stderr). Byte identity: `test_two_runs_give_byte_identical_json` (workers 1 and 2). Seeds: `test_no_test_file_holds_a_confirmatory_seed`, `test_the_seeds_have_no_default`, `test_the_cli_refuses_the_confirmatory_seeds_on_synthetic_bars_and_a_quantile_run_without_its_table`.

## Milestone 6 — throughput (done)

200 leaks of 51118 (`quantile`) on the long synthetic bars, Windows, 12 logical cores:
- single process, ms per leak and detector (the leak alone): FI 4.2, truncation 6.8 (3 conventions, TRUNC-0 + TRUNC-1 + ends), RETILE 18.7 (3 conventions), TWO-RUN 10.8 (16 runs), SHUFFLE 2.6;
- `process_leak` (leak + twin + mirror + 3 controls + prediction, every detector): 107 ms per leak in one process; 200 leaks with 8 workers: 29.7 s including 8 parallel bench builds (34 s alone);
- gates: 1 leak, both pairs, 16 cuts: 106 s in one process.
- **Projection, n = 10,000, 8 workers, per population:** population pass about 3 to 4 min (1,075 s of single-process work / 8, plus the build); classes under 1 s; gates on 50 leaks about 5,300 s / 8, near 11 min. **About 15 min per population**; three runs (descriptive, confirmatory, byte-identity rerun) about 45 min. The adversary's precedent: 3 min 15 s for FI alone.

## Finding — the digests are machine-specific

- The `h1-bands` generator itself (untouched) gives different exact digests on WSL2 (numpy 2.5.4, Python 3.12.14, Linux): 20261029 `5606a1e1...`, 51118 `5d9e37ea...` against the Windows goldens. Cause, isolated by replaying leak 440's draw: the uniform draw is bit-identical on both machines and `exp` of it differs by one ulp (`math.exp` and `np.exp` alike: the Windows C runtime against glibc) (4 of the first 2,000 leaks of 20261029, e.g. margin 0.4907132632938939 vs 0.49071326329389386). `build_table` on synthetic bars differs too (np.log).
- Development digest, seed 51118, `quantile`: Windows `e03f78b187c1f7a7b62681a6c16214f7bd79d7f13b58459521cacb731ad9bc48`; WSL2 `0f806cd343b438ff4d7a0f4d4fea9da7f1a8194b2bb15ee28da65f057646d74e`.
- `portable_digest` (float literals to 12 significant digits) agrees on both: 20261029 `be11ba5d...`, 51118 `a5e9334a...`, 51118 `quantile` `200809fdc6cfdaf49b939bf99d869030dcb123ea36bf1c43836729d4f1d546fb`. Tests assert the exact pins on Windows only and the portable pins everywhere.

## Final verification (2026-11-18)

- Unstubbed CLI run, synthetic bars, 51118 `quantile` with the registered table, n = 200, bootstrap seed 4242 (not registered), 8 workers, output in the scratchpad (not `runs/`): every assertion 0, gates pass on **50 leaks** (FI: 220 units incl. 20 attenuated, 0 mismatches; TRUNC-0, TWO-RUN, SHUFFLE through H1's path: 100 units, 0 mismatches). `run.json` stages: benches 7.7 s, population 27.1 s, classes + gates 576 s. **Measured projection for n = 10,000, 8 workers: population about 2.5 to 3 min, gates about 9.6 min (fixed, 50 leaks): about 13 min per population.**
- FI gate now includes iteration 3's attenuated leaks (first 5, eps 1e-8 and 1e-10).
- Windows full suite (started before the last edits): 1645 passed, 1 failed (`test_explain_head::test_two_calls_give_the_same_bytes`, passes alone 20/20: a run under load, not my code). Final tree re-run of my files + `test_twins` + `test_protocol`: all pass once the `__pycache__` folders written by the concurrent WSL2 run were removed (their `co_filename` was `/mnt/c/...`, which the tripwire's allowlist does not know). WSL2 re-runs use `PYTHONPYCACHEPREFIX`.
- Lint: `uvx ruff@0.11.13 check` clean on every file I changed. `ruff format --check` not applied (no project config; 85 files fail at HEAD).

## Not done or narrowed

- Controls not run through RETILE (no H1 cuts there); the prediction shares the expression evaluator, not the benches or the comparison.
- The three denominators cover the any-cut share and the mean rate (not the pairs or the curve).
- TWO-RUN gate: sigma 0.1, runs 1-2 only; SHUFFLE gate: all 8 twins.
- `detectors.md` renders a subset of `detectors.json`.
- M1 under P not asserted (see report).

## Platform (added after the final runs)

- WSL2, outside pytest: a `fork` pool of `evaluate_population` hung (CPU idle, killed at 360 s); `spawn` gave the single-process results in 13 s. The module's pools now use `spawn`; the CLI sets `spawn` globally (covers `adv.check_equivalence`'s pool in FI's gate). The adversary's own CLI (`workers=4`, default context) may hang the same way on Linux: not tested, not mine to change.
- Under pytest on Linux the tripwire refuses the pool's result-thread `pickle.loads`: the two pool tests run their second worker count on Windows only.
- Final counts: Windows, my files + `test_twins` + `test_protocol`: all pass (test_detectors 36 passed; the rest 352 + 225 passed). WSL2 (CI clone's venv, working tree on PYTHONPATH, `PYTHONPYCACHEPREFIX`): test_detectors 35 passed, 1 skipped; the other five files 352 passed. Full Windows suite (before the last edits): 1645 passed, 1 failed (explain_head under load; passes alone).
