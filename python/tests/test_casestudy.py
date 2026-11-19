"""The case study's two analyses (``olsprime.bench.casestudy``), on fake series and synthetic bars only.

- the registered digests are the ones the committed text records, and a fake series is refused by them;
- a wrong digest, a run that does not vouch for its file, a Report n°3 run on another Report n°2 series, two series that
  do not pair row for row, and stored losses that are not their probabilities' are each refused;
- the split: the move and direction targets equal their numpy closed forms; climatology is ``climatology-panel``
  collapsed; the three-class log-loss splits exactly into the move part and the direction part; hours without a move
  are dropped from the direction series; the intervals are Report n°2's own (``bss_interval``, ``mean_interval``);
  each year's numbers are those of its hours;
- HAC: an intercept-only fit gives ``stats._hac``'s Bartlett variance; zero lags give White's HC0; a regression with
  known coefficients recovers them; the intercept is what the payoffs leave;
- the factor builders equal their closed forms, are invariant to ``perturb_after`` at every cut (both levels, both
  shapes), and two planted cheats (bar t + 1, a full-sample statistic) are caught;
- the whole study writes every top-level key and every table with "exploratory, test months", says it is not the
  registered run, and gives the same bytes twice; the command refuses the fakes before it reads a bar.

Nothing reads the repository's ``data/``, a real ``series.npz`` or the vault: series are built here, bars by
``bench.synthetic``.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from olsprime.bench import casestudy as cs
from olsprime.bench import report2 as r2
from olsprime.bench.perturb import Perturbation, perturb_after
from olsprime.bench.synthetic import synthetic_bars
from olsprime.eval import stats
from olsprime.models.matrix import HOUR_MS
from olsprime.paths import REPO_ROOT, runs_dir

START = datetime(2018, 12, 27, tzinfo=UTC)
N_BARS = 420
FIRST_ROW, HORIZON = 100, 24
SYMBOLS = ("AAAUSDT", "BBBUSDT", "CCCUSDT")
RULE = r2.Report2Config(n_boot=60)
CFG = cs.CaseStudyConfig(min_year_hours=10)
R2_ARMS = (r2.CLIMATOLOGY, "matrix-select")
R3_ARMS = ("enc-ols", "enc-softmax", "enc-linear")


# --- Fakes -------------------------------------------------------------------------------------


def make_bars() -> dict[str, pl.DataFrame]:
    return {s: synthetic_bars(s, start=START, days=N_BARS, interval="1h", seed=i + 1, drift=0.0, vol=0.01) for i, s in enumerate(SYMBOLS)}


def softmax(z: np.ndarray) -> np.ndarray:
    e = np.exp(z - z.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def make_rows(bars: dict[str, pl.DataFrame]) -> dict[str, np.ndarray]:
    """The scored rows of a fake panel: one per pair and hour, a 24-bar forward label, panel order (time, then symbol)."""
    parts = []
    for code, s in enumerate(SYMBOLS):
        b = bars[s]
        open_ms = b["open_time"].dt.epoch("ms").to_numpy()
        known = b["known_at"].dt.epoch("ms").to_numpy()
        opens = b["open"].to_numpy()
        t = np.arange(FIRST_ROW, N_BARS - HORIZON - 1)
        fwd = np.log(opens[t + 1 + HORIZON] / opens[t + 1])
        label = np.where(fwd < -0.03, 0, np.where(fwd > 0.03, 2, 1))
        parts.append((open_ms[t], known[t], open_ms[t + 1 + HORIZON], fwd, label, np.full(t.size, code)))
    cols = [np.concatenate([p[i] for p in parts]) for i in range(6)]
    order = np.lexsort((cols[5], cols[0]))
    open_t, dec, lka, fwd, label, sym = (c[order] for c in cols)
    hours, hour = np.unique(open_t, return_inverse=True)
    return {
        "open_time": open_t,
        "decision_time": dec,
        "label_known_at": lka,
        "fwd_return": fwd,
        "label": label.astype(np.int64),
        "symbol": sym.astype(np.int64),
        "hours": hours,
        "hour": hour.astype(np.int64),
        "count": np.bincount(hour),
    }


def make_probs(label: np.ndarray, arms: tuple[str, ...], seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    clim = np.array([0.33, 0.34, 0.33])
    out = {}
    for i, arm in enumerate(arms):
        if arm == r2.CLIMATOLOGY:
            out[arm] = np.tile(clim + rng.normal(0, 0.005, 3) * np.array([1, -2, 1]), (label.size, 1))
            out[arm] /= out[arm].sum(axis=1, keepdims=True)
            continue
        z = np.log(clim) + 0.3 * rng.standard_normal((label.size, 3))
        z[np.arange(label.size), label] += 0.2 + 0.1 * i  # some skill
        out[arm] = softmax(z)
    return out


def series_arrays(rows: dict[str, np.ndarray], probs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    sc = r2.Scored(np.arange(rows["label"].size), rows["label"], rows["hour"], rows["hours"], rows["count"])
    arms = list(probs)
    ll, br = [], []
    for a in arms:
        losses = stats.per_row_losses(probs[a], rows["label"])
        ll.append(r2.hourly(losses.log_loss, sc))
        br.append(r2.hourly(losses.brier, sc))
    out = {
        "arms": np.array(arms),
        "hours": rows["hours"],
        "count": rows["count"],
        "log_loss": np.stack(ll),
        "brier": np.stack(br),
        "probs": np.stack([probs[a] for a in arms]),
        "label": rows["label"],
        "fwd_return": rows["fwd_return"],
        "symbol": rows["symbol"],
        "symbols": np.array(SYMBOLS),
        "open_time": rows["open_time"],
        "decision_time": rows["decision_time"],
        "label_known_at": rows["label_known_at"],
        "hour": rows["hour"],
    }
    return {k: np.ascontiguousarray(out[k], dtype=out[k].dtype if kind == "<U" else np.dtype(kind)) for k, kind, _ in r2.SERIES_KEYS}


def write_report2(folder: Path, arrays: dict[str, np.ndarray]) -> str:
    folder.mkdir(parents=True, exist_ok=True)
    r2.write_npz(folder / r2.SERIES_FILE, arrays)
    digest = r2.sha256_file(folder / r2.SERIES_FILE)
    r2._write_json(folder / "report2.json", {"registered": False, "series": {"file": r2.SERIES_FILE, "sha256": digest}})
    r2._write_json(folder / "config.json", {"config": asdict(RULE), "registered": False})
    return digest


def write_report3(folder: Path, arrays: dict[str, np.ndarray], report2_sha: str) -> str:
    folder.mkdir(parents=True, exist_ok=True)
    r2.write_npz(folder / r2.SERIES_FILE, arrays)
    digest = r2.sha256_file(folder / r2.SERIES_FILE)
    r2._write_json(folder / cs.REPORT3_FILE, {"series": {"file": r2.SERIES_FILE, "sha256": digest}, "report2": {"series_sha256": report2_sha}})
    r2._write_json(folder / "config.json", {"config": {}})
    return digest


@pytest.fixture(scope="module")
def bars() -> dict[str, pl.DataFrame]:
    return make_bars()


@pytest.fixture(scope="module")
def rows(bars):
    return make_rows(bars)


@pytest.fixture(scope="module")
def arrays(rows):
    return series_arrays(rows, make_probs(rows["label"], R2_ARMS, 1)), series_arrays(rows, make_probs(rows["label"], R3_ARMS, 2))


@pytest.fixture
def runs(arrays):
    """Both fake run folders under this test's runs root, and their digests."""
    a2, a3 = arrays
    d2 = write_report2(runs_dir() / "fake-report2", a2)
    d3 = write_report3(runs_dir() / "fake-report3", a3, d2)
    return runs_dir() / "fake-report2", d2, runs_dir() / "fake-report3", d3


def bits(x: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(x, dtype=np.float64).view(np.uint64)


# --- The registered digests and the refusals ----------------------------------------------------


def test_the_registered_digests_are_the_ones_the_committed_text_records():
    """Report n°2's WSL2 series in docs/RESULTS.md's row, Report n°3's in its committed report; both are set."""
    assert cs.REPORT2_SERIES_SHA256 is not None and cs.REPORT3_SERIES_SHA256 is not None
    results = (REPO_ROOT / "docs" / "RESULTS.md").read_text(encoding="utf-8")
    row = next(line for line in results.splitlines() if "Report n°2 (WSL2 re-run, descriptive)" in line)
    assert f"SHA-256 {cs.REPORT2_SERIES_SHA256}" in row
    report3 = (REPO_ROOT / "docs" / "reports" / "report-3.md").read_text(encoding="utf-8")
    assert f"This report's series (`series.npz`), SHA-256: `{cs.REPORT3_SERIES_SHA256}`" in report3
    assert f"Report n°2's series: `{cs.REPORT2_SERIES_SHA256}`" in report3


def in_memory_report3(p3: Path, d3: str, d2: str, a3: dict[str, np.ndarray]) -> cs.Series:
    """Report n°3's fake series as read_report3 would return it, built without opening the archive.

    The study's tests use it beside the reader's own test (below), which checks that both give the same run.
    """
    report_bytes = (p3 / cs.REPORT3_FILE).read_bytes()
    report = json.loads(report_bytes)
    assert report["series"]["sha256"] == d3 and report["report2"]["series_sha256"] == d2
    return cs.Series(p3, d3, dict(a3), report, {"config": {}}, hashlib.sha256(report_bytes).hexdigest())


def test_report2s_fake_series_is_read_by_its_digest(runs, arrays):
    p2, d2, _, _ = runs
    s2 = cs.read_report2(p2, d2.upper())
    for k in cs.SERIES_KEYS:
        assert np.array_equal(s2.arrays[k], arrays[0][k]), k


def test_report3s_fake_series_is_read_from_its_hashed_bytes_and_pairs(runs, arrays):
    """Through power.load_series with report_file="report3.json": the same reader as Report n°2's."""
    p2, d2, p3, d3 = runs
    s3 = cs.read_report3(p3, d3, report2_sha256=d2)
    for k in cs.SERIES_KEYS:
        assert np.array_equal(s3.arrays[k], arrays[1][k]), k
    s2 = cs.read_report2(p2, d2)
    cs.pair(s2, s3)
    assert not cs.registered_inputs(s2, s3, cs.CaseStudyConfig())
    expected = in_memory_report3(p3, d3, d2, arrays[1])
    assert (s3.report, s3.report_sha256, s3.sha256) == (expected.report, expected.report_sha256, expected.sha256)


def test_the_registered_digests_refuse_a_fake_series(runs):
    p2, d2, p3, _ = runs
    with pytest.raises(cs.CaseStudyRefused, match="SHA-256"):
        cs.read_report2(p2)  # the registered digest, not the fake's
    with pytest.raises(cs.CaseStudyRefused, match="SHA-256"):
        cs.read_report3(p3, report2_sha256=d2)


def test_a_wrong_or_missing_digest_is_refused(runs):
    p2, d2, p3, d3 = runs
    with pytest.raises(cs.CaseStudyRefused, match="SHA-256"):
        cs.read_report2(p2, "0" * 64)
    with pytest.raises(cs.CaseStudyRefused, match="SHA-256"):
        cs.read_report3(p3, "0" * 64, report2_sha256=d2)
    with pytest.raises(cs.CaseStudyRefused, match="not set"):
        cs.read_report2(p2, None)
    with pytest.raises(cs.CaseStudyRefused, match="not set"):
        cs.read_report3(p3, d3, report2_sha256=None)


def test_report3_must_vouch_for_its_file_and_name_report2s_series(runs):
    _, d2, p3, d3 = runs
    with pytest.raises(cs.CaseStudyRefused, match="names Report n°2's series"):
        cs.read_report3(p3, d3, report2_sha256="1" * 64)
    report = json.loads((p3 / cs.REPORT3_FILE).read_text(encoding="utf-8"))
    report["series"]["sha256"] = "2" * 64
    r2._write_json(p3 / cs.REPORT3_FILE, report)
    with pytest.raises(cs.CaseStudyRefused, match="records"):
        cs.read_report3(p3, d3, report2_sha256=d2)
    (p3 / cs.REPORT3_FILE).unlink()
    with pytest.raises(cs.CaseStudyRefused, match="no report3.json"):
        cs.read_report3(p3, d3, report2_sha256=d2)
    with pytest.raises(cs.CaseStudyRefused, match="no report2.json"):
        cs.read_report2(p3, d3)  # Report n°3's folder is not a Report n°2 run


def test_a_series_outside_the_runs_root_is_refused(tmp_path, arrays):
    d2 = write_report2(tmp_path / "elsewhere", arrays[0])
    with pytest.raises(cs.CaseStudyRefused, match="runs root"):
        cs.read_report2(tmp_path / "elsewhere", d2)
    d3 = write_report3(tmp_path / "elsewhere3", arrays[1], d2)
    with pytest.raises(cs.CaseStudyRefused, match="runs root"):
        cs.read_report3(tmp_path / "elsewhere3", d3, report2_sha256=d2)


def _series(arrays: dict[str, np.ndarray], **changes: np.ndarray) -> cs.Series:
    return cs.Series(Path("x"), "0" * 64, {**arrays, **changes}, {}, {"config": asdict(RULE)}, "0" * 64)


def test_two_series_that_do_not_pair_row_for_row_are_refused(arrays):
    a2, a3 = arrays
    cs.pair(_series(a2), _series(a3))
    label = a3["label"].copy()
    label[[0, 1]] = label[[1, 0]] if label[0] != label[1] else (label[[0, 1]] + 1) % 3
    with pytest.raises(cs.CaseStudyRefused, match="label"):
        cs.pair(_series(a2), _series(a3, label=label))
    with pytest.raises(cs.CaseStudyRefused, match="decision_time"):
        cs.pair(_series(a2), _series(a3, decision_time=a3["decision_time"] + 1))
    with pytest.raises(cs.CaseStudyRefused, match="no enc-ols"):
        cs.pair(_series(a2), _series(a3, arms=np.array(["x", "y", "z"])))


def test_stored_losses_that_are_not_their_probabilities_are_refused(arrays):
    a2, _ = arrays
    sc = cs.scored(a2)
    cs.check_reproduced(_series(a2), "matrix-select", sc)
    ll = a2["log_loss"].copy()
    ll[1, 5] += 1e-9
    with pytest.raises(cs.CaseStudyRefused, match="log_loss"):
        cs.check_reproduced(_series(a2, log_loss=ll), "matrix-select", sc)


# --- 1. The split -------------------------------------------------------------------------------


def test_the_targets_equal_their_closed_forms():
    p = np.array([[0.2, 0.5, 0.3], [0.1, 0.2, 0.7], [0.6, 0.3, 0.1], [0.25, 0.5, 0.25]])
    y = np.array([1, 2, 0, 2])
    sc = r2.Scored(np.arange(4), y, np.array([0, 0, 1, 1]), np.array([0, HOUR_MS]), np.array([2, 2]))
    moved = cs.subset(sc, y != cs.NEUTRAL)
    ts = cs.target_series(p, sc, moved)
    pm = p[:, 0] + p[:, 2]
    ym = (y != 1).astype(float)
    move_ll = -np.where(ym == 1, np.log(pm), np.log(p[:, 1]))
    move_br = (p[:, 1] - (1 - ym)) ** 2 + (pm - ym) ** 2
    np.testing.assert_allclose(ts.move_ll, [move_ll[:2].mean(), move_ll[2:].mean()], rtol=1e-15)
    np.testing.assert_allclose(ts.move_brier, [move_br[:2].mean(), move_br[2:].mean()], rtol=1e-15)
    up = p[:, 2] / pm
    yu = (y == 2).astype(float)
    dir_ll = -np.where(yu == 1, np.log(up), np.log(1 - up))
    dir_br = 2.0 * (up - yu) ** 2  # Report n°2's convention on two columns: both columns' squared errors
    np.testing.assert_allclose(ts.dir_ll, [dir_ll[1], dir_ll[2:].mean()], rtol=1e-14)
    np.testing.assert_allclose(ts.dir_brier, [dir_br[1], dir_br[2:].mean()], rtol=1e-14)
    np.testing.assert_allclose(ts.dir_ll_part, [dir_ll[1] / 2, dir_ll[2:].sum() / 2], rtol=1e-14)


def test_the_three_class_log_loss_splits_exactly_into_move_and_direction(arrays):
    a2, a3 = arrays
    sc = cs.scored(a2)
    moved = cs.subset(sc, sc.label != cs.NEUTRAL)
    for p in (a2["probs"][1], a3["probs"][0], a2["probs"][0]):
        ts = cs.target_series(p, sc, moved)
        np.testing.assert_allclose(ts.ll, ts.move_ll + ts.dir_ll_part, rtol=0, atol=1e-13)
        np.testing.assert_allclose(ts.ll, r2.hourly(stats.per_row_losses(p, sc.label).log_loss, sc), rtol=0, atol=0)


def test_hours_without_a_move_are_dropped_from_the_direction_series():
    y = np.array([1, 1, 0, 2, 1])
    sc = r2.Scored(np.arange(5), y, np.array([0, 0, 1, 1, 2]), np.array([0, 1, 2]) * HOUR_MS, np.array([2, 2, 1]))
    sub = cs.subset(sc, y != cs.NEUTRAL)
    assert sub.hours.tolist() == [HOUR_MS] and sub.count.tolist() == [2] and sub.hour.tolist() == [0, 0] and sub.rows.tolist() == [2, 3]
    with pytest.raises(ValueError, match="realized move"):
        cs.direction_labels(y)


def test_climatology_is_report2s_arm_collapsed_and_has_no_skill_against_itself(arrays):
    a2, _ = arrays
    sc = cs.scored(a2)
    clim = a2["probs"][0]
    probs = {r2.CLIMATOLOGY: clim, **dict.fromkeys(cs.SPLIT_ARMS, clim)}
    out = cs.skill_split(probs, sc, RULE, CFG)
    e = out["arms"]["enc-ols"]["all"]
    for target in ("move", "direction"):
        for metric in ("brier_skill", "log_loss_skill"):
            assert e[target][metric]["estimate"] == 0.0
    assert e["log_loss_gain"]["total"] == 0.0 and e["log_loss_gain"]["move"]["estimate"] == 0.0
    np.testing.assert_allclose(cs.move_probs(clim)[:, 1], clim[:, 0] + clim[:, 2], rtol=0)
    np.testing.assert_allclose(cs.direction_probs(clim)[:, 1], clim[:, 2] / (clim[:, 0] + clim[:, 2]), rtol=0)
    with pytest.raises(cs.CaseStudyRefused, match="no probability to a move"):
        cs.direction_probs(np.array([[0.0, 1.0, 0.0]]))


def test_the_intervals_are_report2s_own_and_each_year_reads_its_hours(arrays):
    a2, a3 = arrays
    sc = cs.scored(a2)
    probs = {r2.CLIMATOLOGY: a2["probs"][0], "matrix-select": a2["probs"][1], "enc-ols": a3["probs"][0], "enc-softmax": a3["probs"][1]}
    out = cs.skill_split(probs, sc, RULE, CFG)
    years = cs.years_of(sc.hours)
    assert sorted(out["periods"]) == ["2018", "2019", "all"] and set(np.unique(years)) == {2018, 2019}
    moved = cs.subset(sc, sc.label != cs.NEUTRAL)
    clim = cs.target_series(probs[r2.CLIMATOLOGY], sc, moved)
    ts = cs.target_series(probs["enc-ols"], sc, moved)
    for period in ("all", "2018", "2019"):
        keep = np.ones(years.size, bool) if period == "all" else years == int(period)
        dkeep = np.ones(moved.hours.size, bool) if period == "all" else cs.years_of(moved.hours) == int(period)
        e = out["arms"]["enc-ols"][period]
        assert e["move"]["brier_skill"] == r2.bss_interval(
            ts.move_brier[keep], clim.move_brier[keep], RULE, "casestudy", "move", "brier", "enc-ols", period
        )
        assert e["direction"]["log_loss_skill"] == r2.bss_interval(
            ts.dir_ll[dkeep], clim.dir_ll[dkeep], RULE, "casestudy", "direction", "log-loss", "enc-ols", period
        )
        assert e["log_loss_gain"]["direction"] == r2.mean_interval(
            clim.dir_ll_part[keep] - ts.dir_ll_part[keep], RULE, "casestudy", "gain", "direction", "enc-ols", period
        )
        assert e["move"]["brier_skill"]["estimate"] == pytest.approx(1 - ts.move_brier[keep].mean() / clim.move_brier[keep].mean(), rel=1e-12)
        assert e["log_loss_gain"]["parts_gap"] < 1e-12
        assert e["hours"] == int(keep.sum()) and e["direction_hours"] == int(dkeep.sum())
    assert out["periods"]["2018"]["hours"] + out["periods"]["2019"]["hours"] == out["periods"]["all"]["hours"]
    few = cs.skill_split(probs, sc, RULE, cs.CaseStudyConfig(min_year_hours=10_000))
    assert "too_few_hours" in few["arms"]["enc-ols"]["2018"] and "too_few_hours" not in few["arms"]["enc-ols"]["all"]


def test_the_years_are_utc_calendar_years():
    ms = np.array([datetime(2018, 12, 31, 23, tzinfo=UTC).timestamp(), datetime(2019, 1, 1, 0, tzinfo=UTC).timestamp()]) * 1000
    assert cs.years_of(ms.astype(np.int64)).tolist() == [2018, 2019]


# --- 2. HAC -------------------------------------------------------------------------------------


def ar1(rho: float, t: int, rng: np.random.Generator) -> np.ndarray:
    e = rng.standard_normal(t)
    x = np.empty(t)
    x[0] = e[0]
    for i in range(1, t):
        x[i] = rho * x[i - 1] + e[i]
    return x


@pytest.mark.parametrize("lags", [0, 1, 23, 168])
def test_an_intercept_only_fit_gives_the_bartlett_long_run_variance_of_stats(lags):
    rng = np.random.default_rng(3)
    d = 0.01 + ar1(0.6, 2000, rng)
    fit = cs.hac_ols(d, np.zeros((d.size, 0)), lags)
    assert fit["beta"][0] == pytest.approx(d.mean(), rel=1e-12)
    assert fit["se"][0] == pytest.approx(math.sqrt(stats._hac(d, lags, "bartlett") / d.size), rel=1e-10)


def test_zero_lags_give_whites_hc0():
    rng = np.random.default_rng(4)
    t = 500
    x = rng.standard_normal((t, 3))
    y = 0.2 + x @ np.array([1.0, -0.5, 0.0]) + rng.standard_normal(t) * (1 + np.abs(x[:, 0]))
    fit = cs.hac_ols(y, x, 0)
    design = np.column_stack([np.ones(t), x])
    bread = np.linalg.inv(design.T @ design)
    beta = bread @ design.T @ y
    e = y - design @ beta
    cov = bread @ (design.T * e**2) @ design @ bread
    np.testing.assert_allclose(fit["beta"], beta, rtol=1e-12)
    np.testing.assert_allclose(fit["se"], np.sqrt(np.diag(cov)), rtol=1e-10)


def test_the_regression_recovers_known_coefficients_and_the_intercept_is_what_is_left():
    rng = np.random.default_rng(5)
    t = 20_000
    f = 0.002 + 0.01 * np.column_stack([ar1(0.5, t, rng) for _ in range(3)])
    beta = np.array([-0.5, 0.0, 0.25])
    d = -0.001 + f @ beta + 0.001 * ar1(0.8, t, rng)
    c = cs.factor_control(d, f, cs.CaseStudyConfig())
    co = c["coefficients"]
    for name, b in zip(cs.FACTORS, beta, strict=True):
        assert abs(co[name]["estimate"] - b) < 4 * co[name]["hac_se"]
    assert abs(c["intercept"] + 0.001) < 4 * co["intercept"]["hac_se"]
    assert c["intercept"] + c["explained"] == pytest.approx(c["mean_difference"], rel=1e-9)
    assert c["share_left"] == pytest.approx(c["intercept"] / c["mean_difference"], rel=1e-12)
    assert c["hac"] == {"kernel": "bartlett", "lags": 168} and co["momentum"]["p"] > 1e-4 and co["reversal"]["p"] < 1e-6


def test_a_regressor_on_another_scale_changes_its_coefficient_and_no_t():
    """Unit-RMS scaling inside the solve: a payoff times c gives a coefficient divided by c, the same t and intercept."""
    rng = np.random.default_rng(8)
    t = 3000
    f = np.column_stack([3e-4 * ar1(0.3, t, rng), 1.4e-3 * ar1(0.3, t, rng), 0.5 * ar1(0.3, t, rng)])
    f[:, 2] += 300 * f[:, 1]  # nearly collinear, as momentum and its timed form can be
    d = 0.01 + f @ np.array([2.0, -1.0, 0.003]) + 0.01 * ar1(0.5, t, rng)
    base = cs.hac_ols(d, f, 24)
    for c in (1e6, 1e-6):
        g = f.copy()
        g[:, 0] *= c
        fit = cs.hac_ols(d, g, 24)
        assert fit["beta"][1] == pytest.approx(base["beta"][1] / c, rel=1e-8)
        np.testing.assert_allclose(fit["t"], base["t"], rtol=1e-8)
        np.testing.assert_allclose(fit["beta"][[0, 2, 3]], base["beta"][[0, 2, 3]], rtol=1e-8)


# --- 2. The factor builders, past-only ----------------------------------------------------------


def hand_bars(close: np.ndarray, open_hours: np.ndarray) -> pl.DataFrame:
    open_ms = (np.asarray(open_hours, dtype=np.int64) + 427_000) * HOUR_MS
    return pl.DataFrame({"symbol": ["X"] * close.size, "open_time": pl.Series(open_ms).cast(pl.Datetime("ms", "UTC")), "close": close})


def test_the_builders_equal_their_closed_forms_and_respect_the_grid():
    rng = np.random.default_rng(6)
    hours = np.r_[np.arange(12), np.arange(13, 25)]  # hour 12 is missing: one gap
    r = 0.01 * rng.standard_normal(hours.size)
    close = 100 * np.exp(np.cumsum(r))
    b = hand_bars(close, hours)
    cfg = cs.CaseStudyConfig(momentum_bars=3, volatility_bars=4)
    rev, mom, var, vtm = cs.reversal(b, cfg), cs.momentum(b, cfg), cs.realized_variance(b, cfg), cs.vol_timed_momentum(b, cfg)
    lr = np.log(close[1:] / close[:-1])
    on_grid = np.diff(hours) == 1
    for t in range(hours.size):
        ok1 = t >= 1 and on_grid[t - 1]
        assert (rev[t] == pytest.approx(-lr[t - 1], rel=1e-12)) if ok1 else np.isnan(rev[t])
        ok_m = t >= 4 and on_grid[t - 4 : t].all()
        assert (mom[t] == pytest.approx(math.log(close[t - 1] / close[t - 4]), rel=1e-12)) if ok_m else np.isnan(mom[t])
        ok_v = t >= 4 and on_grid[t - 4 : t].all()
        assert (var[t] == pytest.approx(float(np.mean(lr[t - 4 : t] ** 2)), rel=1e-12)) if ok_v else np.isnan(var[t])
        if ok_m and ok_v:
            assert vtm[t] == pytest.approx(mom[t] / (3 * var[t]), rel=1e-12)
        else:
            assert np.isnan(vtm[t])
    assert np.isnan(rev[12]) and np.isnan(mom[15]) and not np.isnan(mom[16])  # bar 12 opens two hours after bar 11
    with pytest.raises(ValueError, match="one pair"):
        cs.reversal(pl.concat([b, b.with_columns(pl.lit("Y").alias("symbol"))]), cfg)


def test_a_flat_pair_takes_no_volatility_timed_position():
    """v_t = 0: the last 90 returns are 0, so the momentum is 0 and the timed position is 0, not a refusal."""
    close = np.r_[100 * np.exp(0.01 * np.random.default_rng(7).standard_normal(20).cumsum()), np.full(100, 50.0)]
    b = hand_bars(close, np.arange(close.size))
    cfg = cs.CaseStudyConfig()
    v, m, vtm = cs.realized_variance(b, cfg), cs.momentum(b, cfg), cs.vol_timed_momentum(b, cfg)
    flat = np.flatnonzero(v == 0)
    assert flat.size > 0 and np.all(m[flat] == 0) and np.all(vtm[flat] == 0)
    assert np.all(np.isnan(vtm[:90]))  # no window yet: missing, not zero


def invariant(builder, bars: pl.DataFrame, cut: int, level: float) -> bool:
    """H1's future invariance for a builder: every value at or before the cut, NaNs included, the same bit for bit."""
    cfg = cs.CaseStudyConfig()
    out = perturb_after(bars, cut, seed=cut, config=Perturbation(level_shift=level, mirror=bool(cut % 2)))
    a, b = builder(bars, cfg), builder(out, cfg)
    assert np.any(bits(a[cut + 1 :]) != bits(b[cut + 1 :])), "the perturbation never reached the builder"
    return bool(np.array_equal(bits(a[: cut + 1]), bits(b[: cut + 1])))


@pytest.fixture(scope="module")
def one_pair() -> pl.DataFrame:
    return synthetic_bars("BTCUSDT", start=START, days=400, interval="1h", seed=9, drift=0.0, vol=0.01)


@pytest.mark.parametrize("name", list(cs.FACTOR_BUILDERS))
@pytest.mark.parametrize("cut", [120, 151, 230, 333])
@pytest.mark.parametrize("level", [3.0, 1.0 / 3.0])
def test_every_factor_builder_is_invariant_to_the_future(one_pair, name, cut, level):
    assert invariant(cs.FACTOR_BUILDERS[name], one_pair, cut, level)


def _next_bar_reversal(bars, cfg):
    return np.append(cs.reversal(bars, cfg)[1:], np.nan)  # the position of bar t + 1, read at t


def _full_sample_momentum(bars, cfg):
    m = cs.momentum(bars, cfg)
    return m / np.nanstd(m)  # a scale fitted on every bar, later ones included


@pytest.mark.parametrize("cheat", [_next_bar_reversal, _full_sample_momentum])
@pytest.mark.parametrize("cut", [120, 151, 230, 333])
def test_the_planted_future_readers_are_caught(one_pair, cheat, cut):
    for level in (3.0, 1.0 / 3.0):
        assert not invariant(cheat, one_pair, cut, level)


def test_a_cheat_in_the_registry_would_be_caught_by_the_same_check(one_pair):
    """The check reads the builders through FACTOR_BUILDERS: a cheat put there fails it."""
    swapped = {**cs.FACTOR_BUILDERS, "reversal": _next_bar_reversal}
    assert not all(invariant(b, one_pair, 151, 3.0) for b in swapped.values())


# --- The signals at the scored rows -------------------------------------------------------------


def test_each_row_reads_its_own_bar_and_nothing_else(bars, arrays):
    a2, _ = arrays
    sig = cs.row_signals(bars, a2, CFG)
    i = 37
    b = bars[SYMBOLS[a2["symbol"][i]]]
    t = int(np.flatnonzero(b["open_time"].dt.epoch("ms").to_numpy() == a2["open_time"][i])[0])
    for j, name in enumerate(cs.FACTORS):
        assert sig[i, j] == cs.FACTOR_BUILDERS[name](b, CFG)[t]
        assert sig[i, j] == cs.FACTOR_BUILDERS[name](b[: t + 1], CFG)[t]  # the bars after t are not needed
    sc = cs.scored(a2)
    pay = cs.hourly_payoffs(sig, a2["fwd_return"], sc)
    np.testing.assert_allclose(pay[:, 0], r2.hourly(sig[:, 0] * a2["fwd_return"], sc), rtol=0)


def test_a_row_whose_bar_is_not_its_decision_is_refused(bars, arrays):
    a2, _ = arrays
    late = {**bars, SYMBOLS[0]: bars[SYMBOLS[0]].with_columns(pl.col("known_at") + pl.duration(milliseconds=1))}
    with pytest.raises(cs.CaseStudyRefused, match="known_at"):
        cs.row_signals(late, a2, CFG)
    with pytest.raises(cs.CaseStudyRefused, match="no bars"):
        cs.row_signals({k: v for k, v in bars.items() if k != SYMBOLS[1]}, a2, CFG)
    short = {**bars, SYMBOLS[2]: bars[SYMBOLS[2]][FIRST_ROW - 50 :]}  # the first rows lose their 90-hour window
    with pytest.raises(cs.CaseStudyRefused, match="no signal"):
        cs.row_signals(short, a2, CFG)


# --- The whole study ----------------------------------------------------------------------------


def test_the_study_labels_every_key_and_table_and_gives_the_same_bytes_twice(runs, arrays, bars, tmp_path):
    p2, d2, p3, d3 = runs
    s2, s3 = cs.read_report2(p2, d2), in_memory_report3(p3, d3, d2, arrays[1])
    prov = {"git_commit": "c" * 40, "code": {"sha256": "d" * 64, "files": 1}, "manifest_digest": "0" * 64}
    m = cs.run_casestudy(s2, s3, bars, CFG, tmp_path / "a", provenance=prov)
    cs.run_casestudy(s2, s3, bars, CFG, tmp_path / "b", provenance=prov)
    for name in (cs.OUT_JSON, cs.OUT_MD, "config.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes(), name
    assert all(k.endswith(cs.TAG) for k in m)
    for name in (cs.OUT_JSON, "config.json", "run.json"):  # every JSON file the module writes
        assert all(k.endswith(cs.TAG) for k in json.loads((tmp_path / "a" / name).read_text(encoding="utf-8"))), name
    assert m[f"registered{cs.TAG}"] is False
    md = (tmp_path / "a" / cs.OUT_MD).read_text(encoding="utf-8")
    lines = md.splitlines()
    headers = [lines[i - 1] for i, line in enumerate(lines) if line.startswith("|---")]
    assert len(headers) == 4 and all(cs.LABEL in h for h in headers)
    assert all(cs.LABEL in line for line in lines if line.startswith("#"))
    assert "NOT THE REGISTERED INPUTS" in md
    run = json.loads((tmp_path / "a" / "run.json").read_text(encoding="utf-8"))
    assert run[f"contact{cs.TAG}"]["label"] == cs.LABEL
    control = m[f"factor_control{cs.TAG}"]
    assert set(control) == {"enc-ols - enc-softmax", "matrix-select - climatology-panel"}
    c = control["enc-ols - enc-softmax"]
    d = s3.log_loss("enc-ols") - s3.log_loss("enc-softmax")
    assert c["mean_difference"] == pytest.approx(float(d.mean()), rel=1e-12)
    assert c["intercept"] + c["explained"] == pytest.approx(c["mean_difference"], rel=1e-9, abs=1e-15)
    split = m[f"skill_split{cs.TAG}"]
    assert set(split["arms"]) == set(cs.SPLIT_ARMS) and set(split["arms"]["matrix-select"]) == {"all", "2018", "2019"}


def test_the_command_refuses_the_fakes_before_it_reads_a_bar(runs, monkeypatch):
    p2, _, p3, _ = runs

    def no_bars(*args, **kwargs):
        raise AssertionError("bars read before the digests were checked")

    monkeypatch.setattr(cs, "load_bars", no_bars)
    with pytest.raises(cs.CaseStudyRefused, match="SHA-256"):
        cs.main(["--report2", str(p2), "--report3", str(p3), "--out", str(runs_dir() / "never")])
    assert not (runs_dir() / "never").exists()


def test_the_registered_configuration_is_the_documented_one():
    cfg = cs.CaseStudyConfig()
    assert cfg.registered and (cfg.momentum_bars, cfg.volatility_bars, cfg.hac_lags, cfg.min_year_hours) == (24, 90, 168, 100)
    assert not CFG.registered
    assert "168 lags" in cs.__doc__ and "Bartlett" in cs.__doc__
