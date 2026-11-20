"""Audit pass 5b, the run path: the platform pin (M1), the guard on the registered command lines (M2), FI's rule on
M2 (Minor 5), the 64 long-schedule dates (Minor 11) and zero-volume bars in TWO-RUN (Minor 14).

Synthetic bars only. The three confirmatory seeds appear only through the module's constants, and no test runs the
CLI past its guard with them: the accepted lines are tested on the pure predicate, and every CLI refusal runs with
the draws stubbed to fail.
"""

from __future__ import annotations

import json
import platform
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import numpy as np
import polars as pl
import pytest

from olsprime.bench import adversary as adv
from olsprime.bench import detectors as det
from olsprime.bench import provenance
from olsprime.paths import REPO_ROOT

TABLE = REPO_ROOT / "runs" / "2026-11-18-quantile-table" / "table.json"
needs_table = pytest.mark.skipif(
    not TABLE.exists(), reason="the registered quantile table is not on this machine"
)
CONF = (
    det.CONFIRMATORY_POPULATION_SEED,
    det.CONFIRMATORY_TWO_RUN_SEED,
    det.CONFIRMATORY_BOOTSTRAP_SEED,
)

CONFIRMATORY = {"seed": CONF[0], "two_run_seed": CONF[1], "placement": adv.QUANTILE, "bootstrap_seed": CONF[2],
                "n": det.REGISTERED_N, "synthetic": False, "table": "table.json"}  # fmt: skip
DESCRIPTIVE = {"seed": det.DESCRIPTIVE_POPULATION_SEED, "two_run_seed": det.DESCRIPTIVE_TWO_RUN_SEED, "placement": adv.H1_BANDS,
               "bootstrap_seed": det.DESCRIPTIVE_BOOTSTRAP_SEED, "n": det.REGISTERED_N, "synthetic": False, "table": "table.json"}  # fmt: skip
DEVELOPMENT = {"seed": det.DEVELOPMENT_POPULATION_SEED, "two_run_seed": det.DEVELOPMENT_TWO_RUN_SEED, "placement": adv.QUANTILE,
               "bootstrap_seed": 4242, "n": 200, "synthetic": True, "table": "table.json"}  # fmt: skip


def _line(base: dict, **change) -> SimpleNamespace:
    return SimpleNamespace(**{**base, **change})


def _refused(base: dict, **change) -> bool:
    return det.registered_line_refusal(_line(base, **change)) is not None


# --- M2: the guard, a pure predicate ----------------------------------------------------------------------------


def test_the_two_registered_lines_and_a_development_line_are_accepted():
    """The accept cases, on the predicate only (never through the CLI)."""
    assert det.registered_line_refusal(_line(CONFIRMATORY)) is None
    assert det.registered_line_refusal(_line(DESCRIPTIVE)) is None
    assert det.registered_line_refusal(_line(DEVELOPMENT)) is None
    assert (
        det.registered_line_refusal(
            _line(
                DEVELOPMENT,
                placement=adv.H1_BANDS,
                table=None,
                bootstrap_seed=None,
                n=6,
            )
        )
        is None
    )
    assert (
        det.registered_line_refusal(_line(DESCRIPTIVE, synthetic=True)) is None
    )  # synthetic bars: no registered line needed


@pytest.mark.parametrize("slot", ["seed", "two_run_seed", "bootstrap_seed"])
@pytest.mark.parametrize("seed", CONF, ids=["population", "two-run", "bootstrap"])
@pytest.mark.parametrize(
    "base",
    [DEVELOPMENT, DESCRIPTIVE, {**DESCRIPTIVE, "synthetic": True}],
    ids=["development", "descriptive", "synthetic-descriptive"],
)
def test_every_confirmatory_seed_is_refused_in_every_slot_outside_its_line(
    base, seed, slot
):
    """Each of the three seeds, in each of the three slots, on synthetic and real bars (the nit at test_detectors.py:444)."""
    assert _refused(base, **{slot: seed})


@pytest.mark.parametrize("slot", ["seed", "two_run_seed", "bootstrap_seed"])
def test_a_confirmatory_seed_in_another_confirmatory_slot_is_refused(slot):
    for seed in CONF:
        if seed != CONFIRMATORY[slot]:
            assert _refused(CONFIRMATORY, **{slot: seed})


CONFIRMATORY_DEVIATIONS = [
    ("placement", adv.H1_BANDS), ("two_run_seed", det.DEVELOPMENT_TWO_RUN_SEED), ("two_run_seed", det.DESCRIPTIVE_TWO_RUN_SEED),
    ("two_run_seed", 1), ("bootstrap_seed", None), ("bootstrap_seed", 4242), ("bootstrap_seed", det.DESCRIPTIVE_BOOTSTRAP_SEED),
    ("n", 9_999), ("n", 10_001), ("n", 200), ("synthetic", True), ("table", None),
]  # fmt: skip
DESCRIPTIVE_DEVIATIONS = [
    ("placement", adv.QUANTILE), ("two_run_seed", det.DEVELOPMENT_TWO_RUN_SEED), ("two_run_seed", det.DESCRIPTIVE_BOOTSTRAP_SEED),
    ("bootstrap_seed", None), ("bootstrap_seed", 4242), ("bootstrap_seed", det.DESCRIPTIVE_TWO_RUN_SEED), ("n", 9_999), ("n", 200),
    ("seed", det.DEVELOPMENT_POPULATION_SEED), ("seed", 1), ("table", None),
]  # fmt: skip


@pytest.mark.parametrize(("field", "value"), CONFIRMATORY_DEVIATIONS)
def test_every_single_deviation_from_the_confirmatory_line_is_refused(field, value):
    assert _refused(CONFIRMATORY, **{field: value})


@pytest.mark.parametrize(("field", "value"), DESCRIPTIVE_DEVIATIONS)
def test_every_single_deviation_from_the_descriptive_line_is_refused_on_real_bars(
    field, value
):
    assert _refused(DESCRIPTIVE, **{field: value})


def test_real_bars_refuse_every_other_population_seed():
    for seed in (det.DEVELOPMENT_POPULATION_SEED, 0, 1, 99):
        for placement in adv.PLACEMENTS:
            assert _refused(
                DEVELOPMENT, seed=seed, synthetic=False, placement=placement
            )


def _no_draw(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every path past the guard fails the test: no leak is drawn, no bench built, no pin regenerated."""

    def fail(*args, **kwargs):
        raise AssertionError("the guard let a refused command line through")

    for target, name in ((adv, "_draw_leak"), (adv, "generate"), (det, "_draw"), (det, "run"), (det, "check_platform_pin"),
                         (det, "synthetic_pairs"), (adv, "_load_development"), (provenance, "current_manifest")):  # fmt: skip
        monkeypatch.setattr(target, name, fail)


def _argv(line: dict) -> list[str]:
    out = ["run", "--seed", str(line["seed"]), "--two-run-seed", str(line["two_run_seed"]), "--placement", line["placement"],
           "--n", str(line["n"]), "--workers", "1"]  # fmt: skip
    if line["bootstrap_seed"] is not None:
        out += ["--bootstrap-seed", str(line["bootstrap_seed"])]
    if line["table"] is not None:
        out += ["--table", line["table"]]
    return out + (["--synthetic"] if line["synthetic"] else [])


def test_the_cli_calls_the_guard_before_anything_else(monkeypatch, tmp_path):
    """One wiring test: refused lines exit through argparse, with every draw stubbed to fail."""
    _no_draw(monkeypatch)
    refused = [
        {**DEVELOPMENT, slot: seed}
        for slot in ("seed", "two_run_seed", "bootstrap_seed")
        for seed in CONF
    ]
    refused += [{**CONFIRMATORY, "placement": adv.H1_BANDS}, {**CONFIRMATORY, "synthetic": True}, {**DESCRIPTIVE, "table": None},
                {**DEVELOPMENT, "synthetic": False}]  # fmt: skip
    for line in refused:
        with pytest.raises(SystemExit) as e:
            det.main([*_argv(line), "--out", str(tmp_path / "x")])
        assert e.value.code == 2
    assert not (tmp_path / "x").exists()
    for (
        seed
    ) in CONF:  # the digest command: never a population drawn from a confirmatory seed
        with pytest.raises(SystemExit):
            det.main(
                ["digest", "--seed", str(seed), "--placement", adv.H1_BANDS, "--n", "5"]
            )


# --- M1: the platform pin -------------------------------------------------------------------------------------


@needs_table
def test_the_pin_refuses_a_digest_that_is_not_the_registered_one():
    with pytest.raises(
        det.PlatformRefused, match="not the platform of the official runs"
    ):
        det.check_platform_pin(TABLE, expected="0" * 64, n=5)
    small = det.development_digest(
        adv.generate(
            5, det.DEVELOPMENT_POPULATION_SEED, placement=adv.QUANTILE, table_path=TABLE
        )
    )
    assert det.check_platform_pin(TABLE, expected=small, n=5) == small


@needs_table
@pytest.mark.skipif((platform.system(), platform.machine()) != ("Windows", "AMD64"),
                    reason="the registered digest is Windows AMD64's (pass 5b, ruling 1); elsewhere the pin refuses, by design")  # fmt: skip
def test_the_full_pin_passes_on_the_registered_platform():
    assert det.check_platform_pin(TABLE) == det.REGISTERED_DEVELOPMENT_DIGEST


def _real_bar_argv(tmp_path) -> list[str]:
    return ["run", "--seed", str(det.DEVELOPMENT_POPULATION_SEED), "--two-run-seed", str(det.DEVELOPMENT_TWO_RUN_SEED),
            "--placement", adv.H1_BANDS, "--n", "6", "--bootstrap-seed", "4242", "--workers", "1", "--table",
            str(tmp_path / "table.json"), "--out", str(tmp_path / "out")]  # fmt: skip


def test_a_real_bar_run_checks_the_table_and_the_pin_before_the_manifest_and_the_bars(
    monkeypatch, tmp_path
):
    """The order of ``main`` on real bars: table, pin, manifest, bars. The guard is stubbed open so that no registered
    seed is used; the manifest raises, so no bar is ever read."""
    calls: list[str] = []
    monkeypatch.setattr(det, "registered_line_refusal", lambda args: None)

    class Stop(Exception):
        pass

    def manifest():
        calls.append("manifest")
        raise Stop

    monkeypatch.setattr(adv, "load_table", lambda path: calls.append("table"))
    monkeypatch.setattr(
        det,
        "check_platform_pin",
        lambda path: calls.append("pin") or det.REGISTERED_DEVELOPMENT_DIGEST,
    )
    monkeypatch.setattr(provenance, "current_manifest", manifest)
    monkeypatch.setattr(adv, "_load_development", lambda *a, **k: calls.append("bars"))
    with pytest.raises(Stop):
        det.main(_real_bar_argv(tmp_path))
    assert calls == ["table", "pin", "manifest"]


@pytest.mark.parametrize("failing", ["table", "pin"])
def test_a_refused_table_or_pin_stops_before_anything_is_read_or_written(
    monkeypatch, tmp_path, failing
):
    calls: list[str] = []
    monkeypatch.setattr(det, "registered_line_refusal", lambda args: None)

    def table(path):
        calls.append("table")
        if failing == "table":
            raise adv.TableRefused("not the registered table")

    def pin(path):
        calls.append("pin")
        raise det.PlatformRefused("the development digest does not reproduce")

    def reached(*args, **kwargs):
        raise AssertionError("reached past the pin")

    monkeypatch.setattr(adv, "load_table", table)
    monkeypatch.setattr(det, "check_platform_pin", pin)
    for target, name in (
        (provenance, "current_manifest"),
        (adv, "_load_development"),
        (det, "run"),
    ):
        monkeypatch.setattr(target, name, reached)
    with pytest.raises(SystemExit) as e:
        det.main(_real_bar_argv(tmp_path))
    assert e.value.code == 2 and calls == (
        ["table"] if failing == "table" else ["table", "pin"]
    )
    assert not (tmp_path / "out").exists()


# --- Minor 5: FI's rule on M2, three-valued, on engineered bars (X4) ------------------------------------------


EXACT = "2/3"


def _engineered(
    b0: pl.DataFrame, t: int, ratio: float | str, crash: bool
) -> pl.DataFrame:
    cols = {c: b0[c].to_numpy().copy() for c in ("open", "high", "low", "close")}
    if (
        crash
    ):  # a tall bar 30 days before the cut: the 90-bar window's high is 1.6 x close[t]
        cols["high"][t - 30] = 1.6 * cols["close"][t]
    target = (
        2.0 / 3.0 * cols["close"][t] if ratio == EXACT else ratio * cols["close"][t]
    )
    scale = target / cols["high"][t + 1]
    for values in cols.values():
        values[t + 1] *= scale
    cols["high"][t + 1] = target
    return b0.with_columns([pl.Series(c, v) for c, v in cols.items()])


def test_fis_rule_on_m2_is_three_valued_on_engineered_bars():
    """Where high[t+1] >= 2/3 close[t] the rule says "flagged" and FI flags; elsewhere "not predicted", and FI may
    flag (a tall bar in the 90-bar window: the cases the old rule got wrong) or not."""
    cfg = adv.AdversaryConfig(long_cuts=0)
    b0 = det.synthetic_pairs()["BTCUSDT"]
    m2 = det.class_m2()
    seen = set()
    for t in (
        2143,
        502,
    ):  # two H1 cuts whose 90-bar window high stays below 4/3 of the close
        for crash in (False, True):
            for ratio in (0.70, EXACT, 0.666, 0.60, 0.40):
                b = _engineered(b0, t, ratio, crash)
                bench = adv.build_bench({"BTCUSDT": b}, cfg)
                i = next(j for j, c in enumerate(bench.cuts) if c["index"] == t)
                flagged = bool(adv.evaluate_fast(m2, bench).caught[i].any())
                rule = det.fi_m2_rule(b, t)
                above = ratio == EXACT or ratio >= 2 / 3
                assert rule is (True if above else None), (t, crash, ratio)
                if rule is True:
                    assert flagged, (
                        t,
                        crash,
                        ratio,
                    )  # asserted where the rule predicts
                else:
                    assert flagged == crash, (
                        t,
                        crash,
                        ratio,
                    )  # observed on these bars: "not predicted" covers both
                seen.add((rule, flagged))
    assert seen == {(True, True), (None, True), (None, False)}


# --- Minor 11: the long schedule's 64 dates ------------------------------------------------------------------


def _fake_schedules(dates_by_pair: dict[str, list[datetime]]) -> SimpleNamespace:
    return SimpleNamespace(pairs=list(dates_by_pair),
                           schedules={p: SimpleNamespace(long=[SimpleNamespace(open_time=d) for d in ds]) for p, ds in dates_by_pair.items()})  # fmt: skip


def test_the_bootstrap_needs_64_dates_shared_by_both_pairs():
    days = [datetime(2019, 1, 1, tzinfo=UTC) + timedelta(days=7 * i) for i in range(64)]
    assert det.long_dates_check(
        _fake_schedules({"BTCUSDT": days, "ETHUSDT": days}), 64
    )["pass"]
    assert not det.long_dates_check(
        _fake_schedules({"BTCUSDT": days, "ETHUSDT": days}), 63
    )["pass"]
    shifted = [*days[:-1], days[-1] + timedelta(days=1)]
    assert not det.long_dates_check(
        _fake_schedules({"BTCUSDT": days, "ETHUSDT": shifted}), 64
    )["pass"]
    assert not det.long_dates_check(
        _fake_schedules({"BTCUSDT": days, "ETHUSDT": [*days[:-1], days[0]]}), 64
    )["pass"]


# --- Minor 14: a zero-volume bar keeps its zeros, or TWO-RUN refuses it ----------------------------------------


@pytest.mark.parametrize(
    "column",
    ["quote_volume", "taker_buy_base_volume", "taker_buy_quote_volume", "trades"],
)
def test_two_run_refuses_a_zero_volume_bar_with_another_non_zero_column(column):
    b = det.synthetic_pairs()["BTCUSDT"]
    t, row = 700, 703
    zeroed = {
        c: b[c].scatter(row, 0)
        for c in (
            "volume",
            "quote_volume",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
            "trades",
        )
    }
    clean = b.with_columns(list(zeroed.values()))
    z = det.two_run_z(det.DEVELOPMENT_TWO_RUN_SEED, "BTCUSDT", 1, 0, 1)
    out, stats = det.two_run_bars(
        clean, t, 0.1, z
    )  # every column zero: kept, no refusal
    assert stats["with_volume"] == 9 and out["trades"][row] == 0
    broken = clean.with_columns(clean[column].scatter(row, 3))
    with pytest.raises(det.RepairFailed, match="zero-volume"):
        det.two_run_bars(broken, t, 0.1, z)


def test_the_platform_is_recorded():
    info = det.platform_info()
    assert (
        set(info) == {"system", "machine", "python", "numpy"}
        and info["numpy"] == np.__version__
    )


@pytest.mark.parametrize("placement", [adv.H1_BANDS, adv.QUANTILE])
def test_a_real_bar_run_gives_the_table_to_the_generator_under_quantile_only(
    monkeypatch, tmp_path, placement
):
    """The descriptive line names ``--table`` for the pin; ``h1-bands`` refuses a table, so ``run`` must get None."""
    seen: dict = {}
    bars = det.synthetic_pairs()
    monkeypatch.setattr(det, "registered_line_refusal", lambda args: None)
    monkeypatch.setattr(adv, "load_table", lambda path: None)
    monkeypatch.setattr(
        det, "check_platform_pin", lambda path: det.REGISTERED_DEVELOPMENT_DIGEST
    )
    monkeypatch.setattr(provenance, "current_manifest", dict)
    monkeypatch.setattr(adv, "_load_development", lambda pair, cfg: bars[pair])

    def run(bars_by_pair, cfg, **kwargs):
        seen.update(kwargs)
        return {"config": det.config_json(cfg), "placement": cfg.placement, "table_sha256": None, "assertions": {},
                "all_pass": False, "stopped": "stubbed", "_timings": {}}  # fmt: skip

    monkeypatch.setattr(det, "run", run)
    argv = _real_bar_argv(tmp_path)
    argv[argv.index("--placement") + 1] = placement
    assert det.main(argv) == 1
    table = str(tmp_path / "table.json")
    assert seen["table_path"] == (table if placement == adv.QUANTILE else None)
    written = json.loads(
        (tmp_path / "out" / "detectors.json").read_text(encoding="utf-8")
    )
    assert written["platform_pin"] == {"checked": True, "development_digest": det.REGISTERED_DEVELOPMENT_DIGEST,
                                       "registered": det.REGISTERED_DEVELOPMENT_DIGEST}  # fmt: skip
    assert not (tmp_path / "out" / det.VERDICT_FILE).exists()
