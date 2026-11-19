"""The detector benchmark on synthetic bars (docs/PROTOCOL.md, "Leak detectors measured against each other (iteration 5)").

Synthetic bars only; development seeds only (population 51118, TWO-RUN 51119). Each registered assertion is a test
here and a check the CLI runs before it writes any rate.
"""

from __future__ import annotations

import json
import platform
import re
from collections import Counter
from dataclasses import dataclass, replace

import numpy as np
import pytest

from olsprime.bench import adversary as adv
from olsprime.bench import detectors as det
from olsprime.bench import invariance as inv
from olsprime.paths import REPO_ROOT

CFG = det.DetectorConfig(population_seed=det.DEVELOPMENT_POPULATION_SEED, two_run_seed=det.DEVELOPMENT_TWO_RUN_SEED, n=60)
REAL_ROWS = [502, 1048, 1233, 1597, 1994, 2100, 2143, 2664]  # §2: H1's cut rows on the real bars


@pytest.fixture(scope="module")
def bars():
    return det.synthetic_pairs(degrade=True)  # undefined wick ratios, VWAPs and shares: the undefined-read rules bite


@pytest.fixture(scope="module")
def benches(bars):
    return det.build_benches(bars, CFG)


@pytest.fixture(scope="module")
def population():
    return adv.generate(CFG.n, CFG.population_seed)


@pytest.fixture(scope="module")
def results(benches, population):
    return [det.process_leak(leak, benches) for leak in population]


def _total(results, name):
    return sum(r.violations[name] for r in results)


def _counts(results):
    c = Counter()
    for r in results:
        c.update(r.counts)
    return c


# --- Bars and schedules (§2, §2.3, §2.4) ----------------------------------------------------------------------


def test_the_synthetic_bars_span_the_real_dates_and_hold_every_registered_schedule(benches):
    for pair, s in benches.schedules.items():
        assert s.bars.height == 2694 and str(s.bars["open_time"][502])[:10] == "2019-01-01"
        assert int(np.flatnonzero(s.scored)[0]) == 502  # the first scored row
        assert sorted(c.index for c in s.h1) == REAL_ROWS  # choose_cuts gives §2's rows on these dates too
        assert len(s.long) == 64 and len({c.index for c in s.long}) == 64
    assert [c.index for c in benches.schedules["BTCUSDT"].long] == [c.index for c in benches.schedules["ETHUSDT"].long]
    assert len(benches.rows("h1")) == 16 and len(benches.rows("long")) == 128
    ends = [(m["tau"], m["m"], m["index"]) for m in benches.retile.ends]
    assert len(ends) == 28
    for tau, count in ((256, 8), (365, 6)):
        assert [e for t, _, e in ends if t == tau][:count] == [502 + m * tau - 1 for m in range(1, count + 1)] * 1
    assert not {e for _, _, e in ends} & set(REAL_ROWS)  # no end is an H1 cut
    assert 2 * 256 - 256 > 189  # a tile's past reads lie inside its input window


def test_trunc_1s_row_t_plus_1_exists_and_is_scored_at_every_cut(benches):
    """§2.3: TRUNC-1 is TRUNC-0 at t + 1, one code path; the cuts whose t + 1 is the last row are counted."""
    t0, t1 = benches.trunc_parts["TRUNC-0"], benches.trunc_parts["TRUNC-1"]
    assert t0.size == t1.size == 144
    for a, b in zip(t0, t1, strict=True):
        ca, cb = benches.trunc.cuts[a], benches.trunc.cuts[b]
        assert cb["at"] == ca["at"] + 1 and benches.schedules[cb["pair"]].scored[cb["at"]]
        assert benches.trunc.scored[b, -1]  # row t + 1 is the last compared row, and scored
    assert set(benches.last_row_cuts) == {"h1", "long"}


def test_trunc_1_refuses_a_cut_whose_next_row_is_not_scored(bars, monkeypatch):
    original = det.schedule_pair

    def broken(b, cfg):
        s = original(b, cfg)
        s.scored[s.h1[0].index + 1] = False
        return s

    monkeypatch.setattr(det, "schedule_pair", broken)
    with pytest.raises(AssertionError, match="row t \\+ 1"):
        det.build_benches(bars, CFG)


def test_retile_really_slices_the_bars_and_its_stacked_view_is_the_series_view(bars, benches):
    rt = benches.retile
    for j in (0, 13, 27):
        m = rt.ends[j]
        tau, e = m["tau"], m["index"]
        sliced = bars[m["pair"]].slice(e - 2 * tau + 1, 2 * tau)
        view = adv.SeriesView(adv.quantities(sliced))
        width = rt.tiles.n
        for q, o in (("close", 1), ("body", -180), ("vwap", 0), ("wick_ratio", 3)):
            stacked = rt.tiles.at(q, o)[j, width - 2 * tau :]
            assert np.array_equal(stacked, view.at(q, o), equal_nan=True), (j, q, o)


def test_retiles_flags_equal_windowed_trunc_0_at_the_28_ends(results):
    """§2.4, asserted: row for row, under G, M and P; no row before e - 10 flags."""
    assert _total(results, "retile-equals-windowed-trunc-0") == 0
    assert sum(r.flags["RETILE/G@ends"].sum() for r in results) > 0  # not vacuous


# --- TWO-RUN (§2.5) -------------------------------------------------------------------------------------------


def test_two_runs_draws_follow_the_registered_keys():
    z = det.two_run_z(51119, "BTCUSDT", 1, 3, 2)
    import zlib

    ref = np.random.default_rng([51119, zlib.crc32(b"BTCUSDT"), 1, 3, 2]).standard_normal((10, 9))
    assert np.array_equal(z, ref) and z.shape == (10, 9)
    with pytest.raises(ValueError):
        det.two_run_z(51119, "BTCUSDT", 1, 3, 0)


def test_two_runs_repair_keeps_every_registered_property(bars):
    b = bars["BTCUSDT"]
    q0 = adv.quantities(b)
    zero_volume = np.flatnonzero(b["volume"].to_numpy() == 0)
    t = int(zero_volume[zero_volume > 600][0]) - 3  # a zero-volume bar among t+1..t+10
    z = det.two_run_z(51119, "BTCUSDT", 1, 0, 1)
    low, low_stats = det.two_run_bars(b, t, 0.1, z)
    high, _ = det.two_run_bars(b, t, 1.0, z)  # the two sigmas share z: ten times the log-perturbation
    rows = np.arange(t + 1, t + 11)
    for name in ("open", "close"):
        x0, x1, x2 = (np.log(f[name].to_numpy()[rows] / b[name].to_numpy()[rows]) for f in (b, low, high))
        assert np.allclose(x2, 10 * x1) and np.allclose(x1, 0.1 * z[:, ["open", "high", "low", "close"].index(name)])
    q1 = adv.quantities(low)
    assert np.array_equal(np.isnan(q0["wick_ratio"][rows]), np.isnan(q1["wick_ratio"][rows]))
    assert np.array_equal(q0["upper_wick"][rows] == 0, q1["upper_wick"][rows] == 0)  # a zero wick stays zero
    zv = t + 3
    for c in ("volume", "quote_volume", "taker_buy_base_volume", "taker_buy_quote_volume", "trades"):
        assert low[c][zv] == b[c][zv] == 0
    keep = np.r_[0 : t + 1, t + 11 : b.height]
    for c in ("open", "high", "low", "close", "volume", "trades"):
        assert np.array_equal(low[c].to_numpy()[keep], b[c].to_numpy()[keep])
    assert low_stats["with_volume"] == 9 and low_stats["bars"] == 10


def test_two_runs_repair_fails_loudly_on_an_invalid_bar(bars):
    b = bars["BTCUSDT"]
    t = 700
    broken = b.with_columns(b["high"].scatter(t + 2, float(b["low"][t + 2]) * 0.5))  # high below the body: invalid
    with pytest.raises(det.RepairFailed):
        det.two_run_bars(broken, t, 0.1, det.two_run_z(51119, "BTCUSDT", 1, 0, 1))


def test_two_runs_repair_statistics_are_reported(benches):
    st = benches.two_run_stats
    assert set(st) == {"0.1", "1"}
    for s in st.values():
        for k in ("vwap_clip_binds", "taker_base_cap_binds", "taker_quote_cap_binds"):
            assert 0 <= s[k]["share"] <= 1
    assert st["0.1"]["median_body"]["after"] > st["0.1"]["median_body"]["before"]  # the law blows the body up (§2.5)


# --- Conventions (§2) ---------------------------------------------------------------------------------------


def test_convention_g_is_the_generators_evaluation_bit_for_bit(benches, population):
    view = benches.trunc.view
    for leak in population:
        a, b = leak.outputs(view), adv.outputs_under(leak, view, "G")
        for k in a:
            assert np.array_equal(np.asarray(a[k]).view(np.uint64), np.asarray(b[k]).view(np.uint64))


def test_conventions_on_atomic_predicates():
    @dataclass
    class V:
        q: dict

        def at(self, name, o):
            return self.q[name]

    nan = np.nan
    view = V({"close": np.array([1.0, nan, 3.0]), "green": np.array([1.0, nan, 0.0]), "red": np.array([0.0, nan, 1.0]),
              "body": np.array([0.1, 0.1, nan]), "upper_wick": np.array([0.0, 0.2, 0.1]), "lower_wick": np.array([0.5, 0.1, 0.1])})  # fmt: skip
    cmp_ = adv.Cmp(adv.At("close", 1), ">", 1.0, adv.Const(2.0))
    assert adv.evaluate_under(cmp_, view, "G").tolist() == [False, False, True]
    assert adv.evaluate_under(cmp_, view, "M").tolist() == [False, True, True]
    assert np.array_equal(adv.evaluate_under(cmp_, view, "P"), [0.0, nan, 1.0], equal_nan=True)
    both = adv.Logic("OR", cmp_, adv.Colour("green", 1))
    assert np.array_equal(adv.evaluate_under(both, view, "P"), [1.0, nan, 1.0], equal_nan=True)  # no Kleene logic
    pattern = adv.Pattern("hammer", 1, 1.0)
    assert adv.evaluate_under(pattern, view, "M").tolist() == [True, False, True]
    assert np.array_equal(adv.evaluate_under(pattern, view, "P"), [1.0, 0.0, nan], equal_nan=True)
    with pytest.raises(ValueError):
        adv.evaluate_under(cmp_, view, "K")


def test_under_p_trunc_0_flags_every_cut_but_the_exception(results):
    """§2, P's assertion; and binary roots: output missing exactly where the OR mask is set."""
    assert _total(results, "p-flags-every-cut-but-the-exception") == 0
    assert _total(results, "p-binary-output-missing-where-the-or-mask-is-set") == 0
    c = _counts(results)
    assert c["p-not-flagged-outside-the-exception:TRUNC-1"] == c["p-not-flagged-outside-the-exception:ENDS"] == 0


def test_m_on_a_single_cmp_is_g_on_its_mirror(benches, population):
    """§2, M: for a single Cmp, M's verdict equals G's verdict on the mirror leak except at exact ties."""
    differ = 0
    for leak in population:
        mir = det.mirror(leak)
        if mir is None:
            continue
        a = det.judge_window(leak, benches.trunc, "M")
        b = det.judge_window(mir, benches.trunc, "G")
        ties = det._ties(leak, "TRUNC/G", benches)
        differ += int(((a.flags != b.flags) & ~ties).sum())
    assert differ == 0


# --- Controls (§3.1, §3.2) ----------------------------------------------------------------------------------


def test_no_detector_flags_a_past_only_twin(results):
    """§3.1: every convention, schedule, sigma, run count, and both rules."""
    assert _total(results, "honest-twins-never-flagged") == 0
    c = _counts(results)
    assert {k for k in c if k.startswith("twin-flagged:")} == {f"twin-flagged:{k}" for k in
                                                              ("FI", "TWO-RUN", "SHUFFLE", *(f"{d}/{v}" for d in ("TRUNC", "RETILE") for v in "GMP"))}  # fmt: skip


@dataclass(frozen=True)
class _LeakyTwin:
    """A node whose 'twin' still reads bar s + 1: the twin check must see it."""

    binary = False

    def evaluate(self, view):
        return view.at("close", 1)

    def offsets(self):
        return frozenset({1})

    def twin(self):
        return self


def test_the_twin_check_sees_a_twin_that_reads_the_future(benches):
    leak = det.hand_leak(7, adv.Rel(_LeakyTwin(), adv.At("close", 0)), output="exp_return")
    assert det.process_leak(leak, benches).violations["honest-twins-never-flagged"] > 0


def test_the_cancelled_controls_equal_the_independent_prediction_run_for_run(results):
    """§3.2: FP1, FP2-min and FP2-fmin of every leak with a future At or Agg node, at H1's 16 cuts."""
    assert _total(results, "cancelled-controls-follow-the-prediction") == 0
    c = _counts(results)
    assert c["controls-built"] > 0
    assert sum(x for k, x in c.items() if k.startswith("control-disagreements-elsewhere:")) == 0
    assert c["control-flags-h1:FP1:TRUNC/G"] > 0  # truncation flags binary controls (a cancelled term makes a Cmp false)
    assert not any(x for k, x in c.items() if k.startswith("control-flags-h1:FP2-fmin"))


def test_the_control_is_built_at_the_future_node_of_largest_reach():
    leak = det.hand_leak(1, adv.Logic("AND", adv.Cmp(adv.At("close", 2), ">", 1.0, adv.At("close", 0)),
                                      adv.Cmp(adv.Agg("volume", "max", 1, 3), "<", 1.0, adv.At("volume", 3))))  # fmt: skip
    path, v = det.future_node(leak.expr)
    assert path == ("b", "lhs") and v == adv.Agg("volume", "max", 1, 3)  # reach 3: the first on the tie with At(volume, 3)
    control = det.cancelled_control(leak, "FP1")
    node = control.expr.b.lhs
    assert isinstance(node, det.Cancelled) and node.w == adv.Agg("volume", "max", -2, 0) and node.v == v
    assert det.cancelled_control(det.hand_leak(2, adv.Colour("green", 1)), "FP1") is None


def test_the_prediction_differs_from_a_wrong_one(benches):
    """The comparison is not vacuous: FP1's flags under truncation are not FP2-fmin's (none)."""
    base = det.FONSECA_FP_BASES[0]
    got = det.judge_window(det.cancelled_control(base, "FP1"), benches.trunc, "G").cut_flags
    assert got.any() and not det.predicted_flags("FP2-fmin", det.predicted_unit(base), benches.trunc, "G").any()


def test_fonsecas_classes_pass_on_the_degraded_bars(benches):
    """§3.3, as the CLI checks it (the literal verdicts are in tests/test_detector_classes.py)."""
    out = det.check_classes(benches)
    assert out["pass"], out["disagreements"]


# --- Read split, mirror (§4.4, §4.9) ------------------------------------------------------------------------


def test_every_truncation_catch_goes_through_a_missing_read(results):
    """§4.4 with the per-read rule: TRUNC-0, TRUNC-1 and RETILE, under every convention."""
    assert _total(results, "truncation-catches-through-a-missing-read") == 0
    split = Counter()
    for r in results:
        for k, (f, t) in r.split.items():
            split[k + ":f"] += f
            split[k + ":t"] += t
    for k in ("TRUNC-0/G@h1", "TRUNC-1/M@h1", "RETILE/P@ends"):
        assert split[k + ":f"] > 0 and split[k + ":t"] == split[k + ":f"]
    assert split["FI@h1:t"] < split["FI@h1:f"]  # FI catches through changed values too


def test_a_single_cmp_leak_and_its_mirror_are_flagged_together(results, population):
    """§4.9: wherever every read is defined in both runs and a != margin b in both runs."""
    assert _total(results, "mirror-flagged-together") == 0
    assert sum(r.mirror is not None for r in results) == sum(isinstance(leak.expr, adv.Cmp) for leak in population) > 0


def test_the_mirror_flips_the_operator_only():
    leak = det.hand_leak(3, adv.Cmp(adv.At("vwap", 2), ">", 1.7, adv.At("close", -4)), output="probs")
    m = det.mirror(leak)
    assert m.expr == adv.Cmp(adv.At("vwap", 2), "<", 1.7, adv.At("close", -4)) and m.output == "probs" and m.tags == leak.tags
    assert det.mirror(det.hand_leak(4, adv.Colour("red", 1))) is None


# --- FI and the gates (§4) ----------------------------------------------------------------------------------


def test_the_row_kernel_equals_the_adversarys_fast_path(results):
    assert _total(results, "fi-row-kernel-equals-fast-path") == 0


def test_the_gates_pass_and_see_a_broken_detector(bars, benches, population, monkeypatch):
    """§4 gates: FI against H1's own path; TRUNC-0 on really truncated bars, TWO-RUN and SHUFFLE through inv.outputs."""
    cfg = replace(CFG, adversary=replace(CFG.adversary, equivalence_leaks=1))
    leak = population[0]
    good = det.run_gates([leak], bars, benches, cfg, cuts_per_pair=1)
    assert good["pass"] and good["h1_path"]["units"] == 2 and good["fi"]["units"] == 4 + 4  # leak and twin, then 2 attenuations, on 2 pairs
    real = det.judge_window

    def flipped(unit, bench, convention="G"):
        r = real(unit, bench, convention)
        if bench is benches.trunc:  # every cut verdict negated
            negated = ~r.cut_flags
            r.flags = np.zeros_like(r.flags)
            r.flags[:, :, -1] = negated
        return r

    monkeypatch.setattr(det, "judge_window", flipped)
    bad = det.run_gates([leak], bars, benches, cfg, cuts_per_pair=1)
    assert not bad["pass"] and bad["h1_path"]["mismatches"]["TRUNC-0"] > 0


# --- Each detector can be fooled alone; the union catches it (planted) ------------------------------------------


PLANTED = {
    "FI": det.hand_leak(1, adv.Cmp(adv.At("close", 1), ">", 0.001, adv.At("close", 0))),  # always true under FI
    "TRUNC-0": det.class_m2(),  # never true, so truncation under G cannot change it
    "TWO-RUN": det.hand_leak(4, adv.Cmp(adv.At("volume", 1), ">", 3.0, adv.Agg("volume", "max", -180, 0))),
    "SHUFFLE": det.hand_leak(4, adv.Cmp(adv.At("volume", 1), ">", 3.0, adv.Agg("volume", "max", -180, 0))),  # no past bar holds it
}


@pytest.mark.parametrize("detector", det.PRIMARY)
def test_a_leak_built_to_escape_one_detector_is_missed_by_it_and_caught_by_another(benches, detector):
    result = det.process_leak(PLANTED[detector], benches)
    primary = [j for j, (s, r) in enumerate(benches.two_run_runs) if s == 0.1 and r <= 2]
    verdict = {"FI": result.flags["FI@h1"].any(), "TRUNC-0": result.flags["TRUNC-0/G@h1"].any(),
               "TWO-RUN": result.flags["TWO-RUN@h1"][:, primary].any(), "SHUFFLE": result.flags["SHUFFLE@h1"].any()}  # fmt: skip
    assert not verdict[detector]
    assert any(v for d, v in verdict.items() if d != detector)  # the union catches it


# --- The population pass: workers and determinism ------------------------------------------------------------


# On Linux the test tripwire refuses the unpickling done by a process pool's result thread (no allowed frame on its
# stack), so the pools run here on Windows only; in WSL2 the same check passed outside pytest (wave 3).
WORKERS = "2" if platform.system() == "Windows" else "1"
pools = pytest.mark.skipif(platform.system() != "Windows", reason="the tripwire refuses a process pool's unpickling on Linux")


@pools
def test_the_population_is_the_same_for_any_worker_count(bars, benches):
    cfg = replace(CFG, n=8)
    one = det.evaluate_population(bars, cfg, benches, None, workers=1)
    two = det.evaluate_population(bars, cfg, benches, None, workers=2)
    for a, b in zip(one, two, strict=True):
        assert a.id == b.id and a.violations == b.violations and a.counts == b.counts
        assert all(np.array_equal(a.flags[k], b.flags[k]) for k in a.flags)


# --- The stop rule, the outputs and the CLI (§7.4, §1.7) -----------------------------------------------------


def _stub_gates(*args, **kwargs):
    return {"leaks": 0, "fi": {"pass": True, "mismatches": 0, "twin_violations": 0, "units": 0},
            "h1_path": {"pass": True, "mismatches": {"TRUNC-0": 0, "TWO-RUN": 0, "SHUFFLE": 0}, "units": 0, "cuts_per_pair": None}, "pass": True}  # fmt: skip


ARGS = ["run", "--synthetic", "--seed", "51118", "--two-run-seed", "51119", "--placement", "h1-bands", "--n", "6",
        "--bootstrap-seed", "4242", "--workers", "1"]  # fmt: skip


def test_a_failing_assertion_stops_the_run_before_any_rate(tmp_path, monkeypatch, capsys):
    real = det.assertions_of

    def planted(*args, **kwargs):
        out = real(*args, **kwargs)
        out["§3.1 honest twins never flagged"] = {"pass": False, "violations": 3}
        return out

    monkeypatch.setattr(det, "assertions_of", planted)
    monkeypatch.setattr(det, "run_gates", _stub_gates)
    out = tmp_path / "stopped"
    assert det.main([*ARGS, "--out", str(out)]) == 1
    printed = capsys.readouterr()
    result = json.loads((out / "detectors.json").read_text(encoding="utf-8"))
    assert "stopped" in result and "metrics" not in result and "reported" not in result
    for text in ((out / "detectors.json").read_text(encoding="utf-8"), (out / "detectors.md").read_text(encoding="utf-8"), printed.out, printed.err):
        assert not re.search(r"\d %", text) and '"share"' not in text and "wilson95" not in text and "ci95" not in text
        assert "Sign:" not in text and "Any-cut share" not in text and "metrics" not in text
        assert "XX" not in text and '"leaks": [' not in text  # no per-leak verdict
    assert "STOPPED" in printed.out and "honest twins" in printed.out


def test_two_runs_give_byte_identical_json(tmp_path, monkeypatch):
    monkeypatch.setattr(det, "run_gates", _stub_gates)
    for name, workers in (("a", "1"), ("b", WORKERS)):
        assert det.main([*ARGS[:-1], workers, "--out", str(tmp_path / name)]) == 0
    a, b = ((tmp_path / x / "detectors.json").read_bytes() for x in "ab")
    assert a == b
    result = json.loads(a)
    assert result["placement"] == "h1-bands" and result["table_sha256"] is None and result["all_pass"]
    assert set(result["metrics"]) >= {"h15", "pairs", "union", "read_split", "mirror_asymmetry", "conventions", "cut_date_bootstrap",
                                      "placement_invariant_subset", "equal_run_counts", "first_m_cuts", "union_misses"}  # fmt: skip
    assert (tmp_path / "a" / "detectors.md").read_bytes() == (tmp_path / "b" / "detectors.md").read_bytes()


def test_the_cli_refuses_the_confirmatory_seeds_on_synthetic_bars_and_a_quantile_run_without_its_table(tmp_path):
    for flag in ("--seed", "--two-run-seed", "--bootstrap-seed"):
        args = list(ARGS)
        args[args.index(flag) + 1] = str(min(det.FORBIDDEN_IN_WAVE_3))
        with pytest.raises(SystemExit):
            det.main(args)
    args = list(ARGS)
    args[args.index("--placement") + 1] = "quantile"
    with pytest.raises(SystemExit):
        det.main([*args, "--out", str(tmp_path / "x")])
    with pytest.raises(SystemExit):
        det.main(["digest", "--seed", str(det.CONFIRMATORY_POPULATION_SEED), "--placement", "h1-bands"])


def test_the_digest_cli_prints_the_digest_and_numpys_version(capsys):
    assert det.main(["digest", "--seed", "51118", "--placement", "h1-bands", "--n", "50"]) == 0
    out = capsys.readouterr().out
    assert out.startswith(det.development_digest(adv.generate(50, 51118))) and np.__version__ in out


def test_the_seeds_have_no_default():
    with pytest.raises(TypeError):
        det.DetectorConfig()  # type: ignore[call-arg]
    assert det.DetectorConfig(population_seed=1, two_run_seed=2).bootstrap_seed is None


def test_no_test_file_holds_a_confirmatory_seed():
    """§7.1: the three confirmatory seeds appear only as named constants, never in a test."""
    forbidden = [str(s) for s in det.FORBIDDEN_IN_WAVE_3]
    for path in (REPO_ROOT / "python" / "tests").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for s in forbidden:
            assert s not in text, (path.name, s)


def test_the_development_digest_hashes_repr_not_render():
    leak = det.hand_leak(1, adv.Cmp(adv.At("body", 1), ">", 1.0, adv.Const(0.0123456789)))
    assert "0.0123456789" in det.digest_line(leak) and "0.0123456789" not in leak.render()
    assert inv.CAUGHT_ABOVE == 1e-9
