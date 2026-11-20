"""The case study's two analyses, exploratory, test months (``.claude/briefs/iteration-5/case-study.md``).

Usage::

    uv run --no-sync python -m olsprime.bench.casestudy --report2 <Report n°2 run> --report3 <Report n°3 run> [--out DIR]

**Exploratory, test months.** Both analyses read the test months 2019-01 -> 2024-12, which Reports n°2 and
n°3 already scored. No hypothesis is tested on them, and every number this module writes says so: each
top-level key of ``casestudy.json`` and each table of ``casestudy.md`` carries "exploratory, test months".
Each real call is a contact with the data, logged in ``docs/PROTOCOL.md``'s change log by the orchestrator;
``run.json`` records what the call read.

**Refits nothing; the inputs by their digests.** Report n°2's ``series.npz`` (the WSL2 re-run, the base of
Report n°3) and Report n°3's, each refused unless its SHA-256 is the registered one
(:data:`REPORT2_SERIES_SHA256`, :data:`REPORT3_SERIES_SHA256`) and its run's JSON records the same digest.
The command line takes no digest: any other file is refused before a bar is read. Report n°3's series must
name Report n°2's as its base and hold the same scored rows (symbol, times, label, forward return, hour),
one for one. Every arm's hourly log-loss and Brier score are recomputed from its stored probabilities and
must equal the stored series within :data:`REPRODUCE_TOL`. The bars, read through ``load_klines`` and cut
to ``known_at < DEVELOPMENT.end``, give the factor signals only.

**1. The split of the skill.** For ``matrix-select``, ``enc-ols`` and ``enc-softmax``, two binary targets
from each row's three probabilities (0 down, 1 neutral, 2 up):

- *move or no move*: ``(p_neutral, p_down + p_up)``, the label ``1{y != neutral}``, on every scored row;
- *direction given a move*: ``(p_down, p_up) / (p_down + p_up)``, the label ``1{y = up}``, on the scored
  rows with a realized move only. Each hour's mean is over its moving rows; hours without one are dropped.

Each target's climatology is Report n°2's ``climatology-panel`` arm, its stored probabilities collapsed the
same way (marginalized for the move, renormalized for the direction): no base rate is fitted on the test
months. Losses are ``stats.per_row_losses`` on the two columns, so the Brier score keeps Report n°2's
convention (``sum_k (p_k - 1{y = k})^2``); a skill is ``1 - mean(arm) / mean(climatology)`` over hours, for
the Brier score and for the log-loss alike, with Report n°2's paired stationary bootstrap
(:func:`olsprime.bench.report2.bss_interval`: Politis-White block of the difference, the resamples and the
level of Report n°2's run). The log-loss splits exactly, row by row:
``-ln p_y = -ln p(move status) - 1{move} ln p(direction | move)``. So each arm's mean hourly log-loss gain
over climatology is the sum of a move part and a direction part (the direction loss summed over an hour's
moving rows, divided by all its rows), each with Report n°2's bootstrap of a mean
(:func:`olsprime.bench.report2.mean_interval`). The three-class Brier score has no such split; its skill is
given as an estimate beside the two. Every quantity is given over the whole period and by calendar year
(UTC) of the hour; a year with fewer than ``min_year_hours`` hours gets no interval. Seeds: Report n°2's
``_seed`` with the tags ``("casestudy", target, metric, arm, period)``, none of which is a registered tag.

**2. The factor control.** The hourly log-loss differences ``enc-ols - enc-softmax`` (Report n°3's
series) and ``matrix-select - climatology-panel`` (Report n°2's) are regressed by OLS on the hourly
payoffs of three known strategies. Each strategy takes, on each pair at each decision, a position computed
from that pair's bars up to the decision bar t (the bar whose ``known_at`` is the row's decision time),
``c`` the close and ``r_s = ln(c_s / c_{s-1})``:

- **reversal**: ``-r_t``, against the last hour's move;
- **momentum**: ``ln(c_{t-1} / c_{t-1-k})``, k = ``momentum_bars`` = 24 hours, skipping the last hour;
- **volatility-timed momentum** (Nagel, NBER w34104): the momentum position divided by ``k * v_t``, with
  ``v_t`` the mean of ``r_s^2`` over the last ``volatility_bars`` = 90 hours (the panel's longest feature
  window, so every scored row has it), uncentred. Where ``v_t = 0`` the last 90 returns are all 0, so the
  momentum is 0 too, and the position is 0 (a flat pair takes no position), never a refusal.

A window counts only when every gap inside it is one hour (``olsprime.features.basic``'s grid rule); a
scored row without a signal is refused, never dropped. A row's payoff is its position times its realized
``fwd_return`` (Report n°2's, from the open of t + 1 to the open of t + 25); a strategy's hourly payoff is
the mean over the hour's scored rows, as the losses are. The regressors are neither centred nor scaled: a
payoff of zero is a strategy that earns nothing, so the intercept is the mean difference left when the three
strategies earn nothing, and ``share_left = intercept / mean difference``. ``explained = sum_j beta_j
mean(f_j)`` is the rest. Each coefficient also gives ``per_std = beta_j * std(f_j)``, the difference's move for
one standard deviation of that payoff. Momentum and its volatility-timed form can be nearly collinear, so a
joint coefficient can be shared between them: each payoff is also fitted alone (intercept, coefficient, HAC
standard errors, share left), with the same lags. These single fits describe; the joint fit is the analysis.

**HAC standard errors, the lag rule (fixed before any real run).** Newey-West, Bartlett kernel,
``hac_lags`` = 168 lags (one week of hours), fixed, the same for every regression and not chosen from the
data. Why: the labels overlap 24 bars, so a loss difference or a payoff is at least MA(23); Bartlett at
L lags weights lag k by ``1 - k / (L + 1)``, which at L = 168 keeps 86 % of lag 23 (the rule of thumb
``floor(4 (T / 100)^(2/9))`` gives 15 lags at T = 50,626, below the overlap). The sandwich is
``Q^-1 S Q^-1 / T`` with ``Q = X'X / T`` and ``S`` the Bartlett long-run covariance of ``x_t e_t`` (divisor
T), solved, not inverted. The columns are scaled to unit root mean square inside the solve and the
estimates scaled back, so the payoffs' different scales do not condition the system; a regressor multiplied
by c gives a coefficient divided by c and the same t. p-values: Student t with T - k degrees of freedom (k
regressors, intercept included), two-sided.

Outputs, to ``runs/<UTC date>-casestudy/`` (suffixed if taken) or ``--out``: ``casestudy.json`` (sorted keys,
no wall clock), ``casestudy.md``, ``config.json`` (configuration, digests, provenance) and ``run.json`` (the
wall clock and the record of the contact). Every top-level key of the three JSON files and every heading and
table of the Markdown carry "exploratory, test months".
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from scipy import stats as st

from olsprime.bench import power
from olsprime.bench import provenance as prov_mod
from olsprime.bench import report2 as r2
from olsprime.eval import stats
from olsprime.features.basic import _all_gaps_ok, _log_ratio, _shift, _window_matrix, grid_flags
from olsprime.models.matrix import HOUR_MS, iso
from olsprime.paths import runs_dir
from olsprime.protocol import DEVELOPMENT

LABEL = "exploratory, test months"
TAG = f" ({LABEL})"

# The registered inputs, copied from the committed text, never from the files:
# - Report n°2's WSL2 re-run (the base of Report n°3): docs/RESULTS.md, line 23, the row "Report n°2 (WSL2 re-run,
#   descriptive)"; docs/reports/report-3.md, line 171, repeats it.
# - Report n°3: docs/reports/report-3.md, line 172, "This report's series (`series.npz`), SHA-256".
REPORT2_SERIES_SHA256: str | None = "691e7ea703fa29f2b857cf353beb5866daf37c3fd8353112bb30173a40aeb843"
REPORT3_SERIES_SHA256: str | None = "e8381799c19638ff71bb685876054c476921d705245049be395774d24cae4249"

SERIES_FILE = r2.SERIES_FILE
REPORT3_FILE = "report3.json"
OUT_JSON, OUT_MD = "casestudy.json", "casestudy.md"
CLIMATOLOGY = r2.CLIMATOLOGY
MATRIX_SELECT = "matrix-select"
ENC_OLS, ENC_SOFTMAX = "enc-ols", "enc-softmax"
SPLIT_ARMS: tuple[str, ...] = (MATRIX_SELECT, ENC_OLS, ENC_SOFTMAX)
DIFFERENCES: tuple[tuple[str, str], ...] = ((ENC_OLS, ENC_SOFTMAX), (MATRIX_SELECT, CLIMATOLOGY))
FACTORS: tuple[str, ...] = ("reversal", "momentum", "vol_timed_momentum")
DOWN, NEUTRAL, UP = 0, 1, 2
SERIES_KEYS: tuple[str, ...] = tuple(k for k, _, _ in r2.SERIES_KEYS)
# What Report n°3's series shares with Report n°2's: the scored rows and their hours, one for one.
PAIRED_KEYS: tuple[str, ...] = ("hours", "count", "label", "fwd_return", "symbol", "symbols", "open_time", "decision_time", "label_known_at", "hour")
REPRODUCE_TOL = 1e-12  # the stored hourly losses against those recomputed from the stored probabilities (same code, same order)
BAR_COLUMNS = ["symbol", "open_time", "close", "known_at"]


@dataclass(frozen=True)
class CaseStudyConfig:
    momentum_bars: int = 24
    volatility_bars: int = 90
    hac_lags: int = 168
    min_year_hours: int = r2.MIN_SPLIT_HOURS

    @property
    def registered(self) -> bool:
        return self == CaseStudyConfig()


class CaseStudyRefused(ValueError):
    """An input is not the registered one, or does not pair with the other: nothing is computed."""


# --- The inputs, by their digests ---------------------------------------------------------------


@dataclass(eq=False)
class Series:
    """A run's ``series.npz`` (every key of ``report2.SERIES_KEYS``), its run's JSON report and ``config.json``."""

    path: Path
    sha256: str
    arrays: dict[str, np.ndarray]
    report: dict[str, Any]
    config: dict[str, Any]
    report_sha256: str

    @property
    def arms(self) -> list[str]:
        return [str(a) for a in self.arrays["arms"]]

    def _index(self, arm: str) -> int:
        if arm not in self.arms:
            raise CaseStudyRefused(f"{self.path}: no {arm} arm (arms: {', '.join(self.arms)})")
        return self.arms.index(arm)

    def probs(self, arm: str) -> np.ndarray:
        return self.arrays["probs"][self._index(arm)]

    def log_loss(self, arm: str) -> np.ndarray:
        return self.arrays["log_loss"][self._index(arm)]

    def brier(self, arm: str) -> np.ndarray:
        return self.arrays["brier"][self._index(arm)]


def _want(sha256: str | None, which: str) -> str:
    if sha256 is None:
        raise CaseStudyRefused(f"{which}'s registered digest is not set: the orchestrator fills it from the committed text")
    return sha256.strip().lower()


def read_report2(run_dir: Path, sha256: str | None = REPORT2_SERIES_SHA256) -> Series:
    """Report n°2's ``series.npz``, through the package's reader (:func:`olsprime.bench.power.load_series`)."""
    want = _want(sha256, "Report n°2")
    try:
        arrays, report, config, report_sha = power.load_series(Path(run_dir) / SERIES_FILE, want, keys=SERIES_KEYS)
    except power.SeriesRefused as exc:
        raise CaseStudyRefused(str(exc)) from None
    return Series(Path(run_dir), want, arrays, report, config, report_sha)


def read_report3(run_dir: Path, sha256: str | None = REPORT3_SERIES_SHA256, *, report2_sha256: str | None = REPORT2_SERIES_SHA256) -> Series:
    """Report n°3's ``series.npz``, through the package's reader with ``report3.json`` vouching for it, on Report n°2's series.

    ``power.load_series(..., report_file="report3.json")``: the path under the runs root, the SHA-256 the one given
    and the one ``report3.json`` records, the arrays read from the hashed bytes without pickles. Then
    ``report3.json`` must name ``report2_sha256`` as its Report n°2 series.
    """
    want, base = _want(sha256, "Report n°3"), _want(report2_sha256, "Report n°2")
    try:
        arrays, report, config, report_sha = power.load_series(Path(run_dir) / SERIES_FILE, want, keys=SERIES_KEYS, report_file=REPORT3_FILE)
    except power.SeriesRefused as exc:
        raise CaseStudyRefused(str(exc)) from None
    named = (report.get("report2") or {}).get("series_sha256")
    if named != base:
        raise CaseStudyRefused(f"{Path(run_dir) / SERIES_FILE}: its run's {REPORT3_FILE} names Report n°2's series {named!r}, not {base}")
    return Series(Path(run_dir), want, arrays, report, config, report_sha)


def rule_config(report2_config: Mapping[str, Any]) -> r2.Report2Config:
    """Report n°2's statistics with the parameters its run used (``config.json``), as Report n°3 rebuilds them."""
    c = report2_config.get("config")
    if not isinstance(c, Mapping):
        raise CaseStudyRefused("Report n°2's config.json has no config")
    return r2.Report2Config(
        n_boot=int(c["n_boot"]), level=float(c["level"]), dm_h=int(c["dm_h"]), bootstrap_seed=int(c["bootstrap_seed"]), ece_bins=int(c["ece_bins"])
    )


def scored(arrays: Mapping[str, np.ndarray]) -> r2.Scored:
    """Report n°2's scored rows and hours, as Report n°3's score stage rebuilds them."""
    sc = r2.Scored(np.arange(arrays["label"].size), arrays["label"].astype(np.int64), arrays["hour"], arrays["hours"], arrays["count"])
    if sc.hours.size == 0 or not np.array_equal(np.bincount(sc.hour, minlength=sc.hours.size), sc.count) or np.any(sc.count == 0):
        raise CaseStudyRefused("the hour index does not give the counts")
    if np.any(np.diff(sc.hours) <= 0):
        raise CaseStudyRefused("the hours are not strictly increasing")
    return sc


def pair(s2: Series, s3: Series) -> None:
    """Refuse unless Report n°3's series holds Report n°2's scored rows, one for one, and both hold the arms read."""
    for k in PAIRED_KEYS:
        a, b = s2.arrays[k], s3.arrays[k]
        if a.shape != b.shape or not np.array_equal(a, b):
            raise CaseStudyRefused(f"Report n°3's {k} is not Report n°2's: the two series do not pair row for row")
    for s, arms in ((s2, (CLIMATOLOGY, MATRIX_SELECT)), (s3, (ENC_OLS, ENC_SOFTMAX))):
        for arm in arms:
            s._index(arm)


def check_reproduced(s: Series, arm: str, sc: r2.Scored) -> None:
    """The arm's stored hourly log-loss and Brier score, recomputed from its stored probabilities, within REPRODUCE_TOL."""
    losses = stats.per_row_losses(s.probs(arm), sc.label)
    for name, rows, stored in (("log_loss", losses.log_loss, s.log_loss(arm)), ("brier", losses.brier, s.brier(arm))):
        gap = float(np.max(np.abs(r2.hourly(rows, sc) - stored)))
        if not gap <= REPRODUCE_TOL:
            raise CaseStudyRefused(f"{arm}'s stored hourly {name} is not its probabilities' (largest gap {gap:.3g})")


# --- 1. The split of the skill ------------------------------------------------------------------


def move_probs(p: np.ndarray) -> np.ndarray:
    """(no move, move) = (p_neutral, p_down + p_up)."""
    return np.stack([p[:, NEUTRAL], p[:, DOWN] + p[:, UP]], axis=1)


def move_labels(y: np.ndarray) -> np.ndarray:
    return (y != NEUTRAL).astype(np.int64)


def direction_probs(p: np.ndarray) -> np.ndarray:
    """(down, up) given a move: (p_down, p_up) / (p_down + p_up); refused where p_down + p_up is 0."""
    s = p[:, DOWN] + p[:, UP]
    if np.any(~(s > 0)):
        raise CaseStudyRefused("a forecast gives no probability to a move: its direction is undefined")
    return np.stack([p[:, DOWN] / s, p[:, UP] / s], axis=1)


def direction_labels(y: np.ndarray) -> np.ndarray:
    """1{up} on rows with a realized move."""
    if np.any(y == NEUTRAL):
        raise ValueError("the direction is defined on rows with a realized move only")
    return (y == UP).astype(np.int64)


def subset(sc: r2.Scored, keep: np.ndarray) -> r2.Scored:
    """The scored rows ``keep`` selects, their hours reindexed; an hour with none of them is dropped."""
    rows = np.flatnonzero(keep)
    present, inv = np.unique(sc.hour[rows], return_inverse=True)
    return r2.Scored(rows, sc.label[rows], inv.astype(np.int64), sc.hours[present], np.bincount(inv, minlength=present.size).astype(np.int64))


@dataclass(frozen=True, eq=False)
class TargetSeries:
    """One arm's hourly series of the two targets, and of the three-class losses they come from."""

    move_ll: np.ndarray  # (T,)
    move_brier: np.ndarray  # (T,)
    dir_ll: np.ndarray  # (T_dir,), over the hours with a move: mean over the hour's moving rows
    dir_brier: np.ndarray  # (T_dir,)
    dir_ll_part: np.ndarray  # (T,): the direction log-loss summed over the hour's moving rows, divided by all its rows
    ll: np.ndarray  # (T,) three-class
    brier: np.ndarray  # (T,) three-class


def target_series(p: np.ndarray, sc: r2.Scored, moved: r2.Scored) -> TargetSeries:
    y = sc.label
    three = stats.per_row_losses(p, y)
    mv = stats.per_row_losses(move_probs(p), move_labels(y))
    dr = stats.per_row_losses(direction_probs(p[moved.rows]), direction_labels(y[moved.rows]))
    part = np.zeros(y.size)
    part[moved.rows] = dr.log_loss
    return TargetSeries(
        r2.hourly(mv.log_loss, sc),
        r2.hourly(mv.brier, sc),
        r2.hourly(dr.log_loss, moved),
        r2.hourly(dr.brier, moved),
        r2.hourly(part, sc),
        r2.hourly(three.log_loss, sc),
        r2.hourly(three.brier, sc),
    )


def years_of(ms: np.ndarray) -> np.ndarray:
    """The UTC calendar year of each epoch-millisecond instant."""
    return np.asarray(ms, dtype=np.int64).astype("datetime64[ms]").astype("datetime64[Y]").astype(np.int64) + 1970


def _period_entry(
    arm: str,
    ts: TargetSeries,
    clim: TargetSeries,
    keep: np.ndarray,
    dkeep: np.ndarray,
    rows: int,
    moving_rows: int,
    period: str,
    rcfg: r2.Report2Config,
) -> dict[str, Any]:
    def skill(a: np.ndarray, c: np.ndarray, *tag: str) -> dict[str, Any]:
        return r2.bss_interval(a, c, rcfg, "casestudy", *tag, arm, period)

    gain_move = clim.move_ll[keep] - ts.move_ll[keep]
    gain_dir = clim.dir_ll_part[keep] - ts.dir_ll_part[keep]
    total = float(np.mean(clim.ll[keep] - ts.ll[keep]))
    return {
        "hours": int(keep.sum()),
        "rows": rows,
        "moving_rows": moving_rows,
        "direction_hours": int(dkeep.sum()),
        "move": {
            "brier_skill": skill(ts.move_brier[keep], clim.move_brier[keep], "move", "brier"),
            "log_loss_skill": skill(ts.move_ll[keep], clim.move_ll[keep], "move", "log-loss"),
            "brier": float(ts.move_brier[keep].mean()),
            "brier_climatology": float(clim.move_brier[keep].mean()),
            "log_loss": float(ts.move_ll[keep].mean()),
            "log_loss_climatology": float(clim.move_ll[keep].mean()),
        },
        "direction": {
            "brier_skill": skill(ts.dir_brier[dkeep], clim.dir_brier[dkeep], "direction", "brier"),
            "log_loss_skill": skill(ts.dir_ll[dkeep], clim.dir_ll[dkeep], "direction", "log-loss"),
            "brier": float(ts.dir_brier[dkeep].mean()),
            "brier_climatology": float(clim.dir_brier[dkeep].mean()),
            "log_loss": float(ts.dir_ll[dkeep].mean()),
            "log_loss_climatology": float(clim.dir_ll[dkeep].mean()),
        },
        "log_loss_gain": {
            "move": r2.mean_interval(gain_move, rcfg, "casestudy", "gain", "move", arm, period),
            "direction": r2.mean_interval(gain_dir, rcfg, "casestudy", "gain", "direction", arm, period),
            "total": total,
            "parts_gap": abs(total - float(gain_move.mean()) - float(gain_dir.mean())),
        },
        "three_class": {
            "brier_skill": float(1.0 - ts.brier[keep].mean() / clim.brier[keep].mean()),
            "log_loss_skill": float(1.0 - ts.ll[keep].mean() / clim.ll[keep].mean()),
        },
    }


def skill_split(probs: Mapping[str, np.ndarray], sc: r2.Scored, rcfg: r2.Report2Config, cfg: CaseStudyConfig) -> dict[str, Any]:
    """Each arm's skill on "move or no move" and on "direction given a move", against climatology-panel collapsed, by period."""
    moving = sc.label != NEUTRAL
    moved = subset(sc, moving)
    clim = target_series(probs[CLIMATOLOGY], sc, moved)
    years, dyears = years_of(sc.hours), years_of(moved.hours)
    row_years = years[sc.hour]
    periods: list[tuple[str, np.ndarray, np.ndarray, np.ndarray]] = [
        ("all", np.ones(years.size, bool), np.ones(dyears.size, bool), np.ones(sc.label.size, bool))
    ]
    periods += [(str(y), years == y, dyears == y, row_years == y) for y in np.unique(years)]
    out: dict[str, Any] = {"arms": {}, "periods": {}}
    for name, keep, dkeep, rkeep in periods:
        out["periods"][name] = {
            "hours": int(keep.sum()),
            "direction_hours": int(dkeep.sum()),
            "rows": int(rkeep.sum()),
            "moving_rows": int((rkeep & moving).sum()),
            "share_moving": float((rkeep & moving).mean() / rkeep.mean()),
            "first_hour": iso(int(sc.hours[keep][0])),
            "last_hour": iso(int(sc.hours[keep][-1])),
        }
    for arm in SPLIT_ARMS:
        ts = target_series(probs[arm], sc, moved)
        out["arms"][arm] = {}
        for name, keep, dkeep, rkeep in periods:
            if name != "all" and min(int(keep.sum()), int(dkeep.sum())) < cfg.min_year_hours:
                out["arms"][arm][name] = {
                    "hours": int(keep.sum()),
                    "direction_hours": int(dkeep.sum()),
                    "too_few_hours": f"fewer than {cfg.min_year_hours} hours: no interval",
                }
                continue
            out["arms"][arm][name] = _period_entry(arm, ts, clim, keep, dkeep, int(rkeep.sum()), int((rkeep & moving).sum()), name, rcfg)
    return out


# --- 2. The factor control: the signals, from past bars only ------------------------------------


def _one_pair(bars: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """The close and the grid flags of one pair's hourly bars, refused unless one symbol in strictly increasing time."""
    if bars.height and bars["symbol"].n_unique() != 1:
        raise ValueError("a factor builder reads one pair's bars at a time")
    open_ms = bars["open_time"].dt.epoch("ms").to_numpy().astype(np.int64)
    if open_ms.size > 1 and not np.all(np.diff(open_ms) > 0):
        raise ValueError("bars must be strictly increasing in open_time")
    return bars["close"].to_numpy().astype(np.float64), grid_flags(open_ms, HOUR_MS)


def _one_bar_returns(close: np.ndarray, flags: np.ndarray) -> np.ndarray:
    r = _log_ratio(close, _shift(close, 1))
    r[~flags] = np.nan
    return r


def reversal(bars: pl.DataFrame, cfg: CaseStudyConfig) -> np.ndarray:
    """Position at each bar t: ``-ln(c_t / c_{t-1})``; NaN off the grid."""
    close, flags = _one_pair(bars)
    return -_one_bar_returns(close, flags)


def momentum(bars: pl.DataFrame, cfg: CaseStudyConfig) -> np.ndarray:
    """Position at each bar t: ``ln(c_{t-1} / c_{t-1-k})``, k = momentum_bars, the last hour skipped; NaN unless the k + 1 gaps are on the grid."""
    close, flags = _one_pair(bars)
    k = cfg.momentum_bars
    m = _log_ratio(_shift(close, 1), _shift(close, 1 + k))
    m[~_all_gaps_ok(flags, 1 + k)] = np.nan
    return m


def realized_variance(bars: pl.DataFrame, cfg: CaseStudyConfig) -> np.ndarray:
    """Mean of ``r_s^2`` over the last volatility_bars one-bar returns up to t, uncentred; NaN unless those gaps are on the grid."""
    close, flags = _one_pair(bars)
    w = cfg.volatility_bars
    r = _one_bar_returns(close, flags)
    with np.errstate(all="ignore"):
        v = np.mean(_window_matrix(r * r, w), axis=1)
    v[~_all_gaps_ok(flags, w)] = np.nan
    return v


def vol_timed_momentum(bars: pl.DataFrame, cfg: CaseStudyConfig) -> np.ndarray:
    """Position at each bar t: the momentum position over ``k * v_t``; 0 where v_t is 0 (then the momentum is 0 too); NaN where either is missing."""
    m, v = momentum(bars, cfg), realized_variance(bars, cfg)
    with np.errstate(all="ignore"):
        timed = np.where(v > 0, m / (cfg.momentum_bars * np.where(v > 0, v, 1.0)), np.nan)
    return np.where((v == 0) & np.isfinite(m), 0.0, timed)


Builder = Callable[[pl.DataFrame, CaseStudyConfig], np.ndarray]
FACTOR_BUILDERS: dict[str, Builder] = {"reversal": reversal, "momentum": momentum, "vol_timed_momentum": vol_timed_momentum}


def row_signals(
    bars: Mapping[str, pl.DataFrame], arrays: Mapping[str, np.ndarray], cfg: CaseStudyConfig, builders: Mapping[str, Builder] = FACTOR_BUILDERS
) -> np.ndarray:
    """(N, factors): each scored row's positions, read at its own bar, whose ``known_at`` must be the row's decision time."""
    names = [str(s) for s in arrays["symbols"]]
    out = np.full((arrays["label"].size, len(builders)), np.nan)
    for code in np.unique(arrays["symbol"]):
        name = names[int(code)]
        if name not in bars:
            raise CaseStudyRefused(f"no bars for {name}")
        b = bars[name]
        rows = np.flatnonzero(arrays["symbol"] == code)
        open_ms = b["open_time"].dt.epoch("ms").to_numpy().astype(np.int64)
        known = b["known_at"].dt.epoch("ms").to_numpy().astype(np.int64)
        idx = np.searchsorted(open_ms, arrays["open_time"][rows])
        found = idx < open_ms.size
        idx = np.where(found, idx, 0)
        found &= open_ms[idx] == arrays["open_time"][rows]
        if not found.all():
            raise CaseStudyRefused(f"{name}: {int((~found).sum())} scored rows have no bar")
        if not np.array_equal(known[idx], arrays["decision_time"][rows]):
            raise CaseStudyRefused(f"{name}: a bar's known_at is not its row's decision time")
        for j, builder in enumerate(builders.values()):
            out[rows, j] = builder(b, cfg)[idx]
    bad = ~np.isfinite(out)
    if bad.any():
        raise CaseStudyRefused(
            f"{int(bad.any(axis=1).sum())} scored rows have no signal ({', '.join(f for f, c in zip(builders, bad.any(axis=0), strict=True) if c)})"
        )
    return out


def hourly_payoffs(signals: np.ndarray, fwd_return: np.ndarray, sc: r2.Scored) -> np.ndarray:
    """(T, factors): each strategy's payoff, position times realized forward return, averaged over each hour's scored rows."""
    return np.stack([r2.hourly(signals[:, j] * fwd_return, sc) for j in range(signals.shape[1])], axis=1)


# --- 2. The factor control: the regression ------------------------------------------------------


def hac_ols(y: np.ndarray, x: np.ndarray, lags: int) -> dict[str, Any]:
    """OLS of y on [1, x] with Newey-West (Bartlett, ``lags``) standard errors: ``Q^-1 S Q^-1 / T``, divisor T.

    The columns are scaled to unit root mean square for the solve, and the estimates and covariance scaled back.
    """
    y = np.asarray(y, dtype=np.float64)
    design = np.column_stack([np.ones(y.size), np.asarray(x, dtype=np.float64).reshape(y.size, -1)])
    t, k = design.shape
    if t <= k or lags < 0 or lags >= t:
        raise ValueError(f"need more hours than regressors and lags: T = {t}, k = {k}, lags = {lags}")
    scale = np.sqrt(np.mean(design * design, axis=0))
    if np.any(~(scale > 0)) or not np.all(np.isfinite(design)) or not np.all(np.isfinite(y)):
        raise ValueError("a regressor is zero at every hour, or a value is not finite")
    z = design / scale
    q = z.T @ z / t
    gamma = np.linalg.solve(q, z.T @ y / t)
    e = y - z @ gamma
    ze = z * e[:, None]
    s = ze.T @ ze / t
    for lag in range(1, lags + 1):
        g = ze[lag:].T @ ze[:-lag] / t
        s += (1.0 - lag / (lags + 1.0)) * (g + g.T)
    cov = np.linalg.solve(q, np.linalg.solve(q, s).T).T / t / np.outer(scale, scale)
    beta = gamma / scale
    se = np.sqrt(np.diag(cov))
    tstat = beta / se
    centred = y - y.mean()
    return {
        "beta": beta,
        "se": se,
        "t": tstat,
        "p": 2.0 * st.t.sf(np.abs(tstat), df=t - k),
        "cov": cov,
        "r2": float(1.0 - (e @ e) / (centred @ centred)) if centred @ centred > 0 else float("nan"),
        "hours": t,
        "lags": lags,
    }


def factor_control(d: np.ndarray, payoffs: np.ndarray, cfg: CaseStudyConfig) -> dict[str, Any]:
    """The regression of an hourly loss difference on the strategies' hourly payoffs, and what the intercept leaves."""
    fit = hac_ols(d, payoffs, cfg.hac_lags)
    mean_only = hac_ols(d, np.zeros((d.size, 0)), cfg.hac_lags)
    names = ("intercept", *FACTORS)
    mean_d = float(d.mean())
    means, sds = payoffs.mean(axis=0), payoffs.std(axis=0)
    explained = float(fit["beta"][1:] @ means)
    coefficients = {
        n: {"estimate": float(fit["beta"][i]), "hac_se": float(fit["se"][i]), "t": float(fit["t"][i]), "p": float(fit["p"][i])}
        for i, n in enumerate(names)
    }
    for j, f in enumerate(FACTORS):
        coefficients[f]["per_std"] = float(fit["beta"][j + 1] * sds[j])  # the difference's move for one standard deviation of the payoff
    alone = {}  # each payoff on its own: the payoffs can be collinear (momentum and its volatility-timed form), so the joint split is shared
    for j, f in enumerate(FACTORS):
        one = hac_ols(d, payoffs[:, j], cfg.hac_lags)
        alone[f] = {
            "intercept": float(one["beta"][0]),
            "intercept_hac_se": float(one["se"][0]),
            "estimate": float(one["beta"][1]),
            "hac_se": float(one["se"][1]),
            "t": float(one["t"][1]),
            "p": float(one["p"][1]),
            "share_left": float(one["beta"][0] / mean_d) if mean_d != 0 else None,
            "r2": one["r2"],
        }
    return {
        "coefficients": coefficients,
        "alone": alone,
        "mean_difference": mean_d,
        "mean_difference_hac_se": float(mean_only["se"][0]),
        "intercept": float(fit["beta"][0]),
        "explained": explained,
        "share_left": float(fit["beta"][0] / mean_d) if mean_d != 0 else None,
        "r2": fit["r2"],
        "hours": fit["hours"],
        "hac": {"kernel": "bartlett", "lags": cfg.hac_lags},
        "payoffs": {f: {"mean": float(means[j]), "std": float(sds[j])} for j, f in enumerate(FACTORS)},
        "payoff_correlation": [[float(c) for c in row] for row in np.corrcoef(payoffs, rowvar=False).reshape(len(FACTORS), len(FACTORS))],
    }


# --- The whole study ----------------------------------------------------------------------------


def registered_inputs(s2: Series, s3: Series, cfg: CaseStudyConfig) -> bool:
    return bool(s2.sha256 == REPORT2_SERIES_SHA256 and s3.sha256 == REPORT3_SERIES_SHA256 and cfg.registered and s2.report.get("registered"))


def compute(s2: Series, s3: Series, bars: Mapping[str, pl.DataFrame], cfg: CaseStudyConfig) -> dict[str, Any]:
    """Both analyses from the two series and the bars; every top-level key carries the label."""
    pair(s2, s3)
    rcfg = rule_config(s2.config)
    a = s2.arrays
    sc = scored(a)
    sources = {CLIMATOLOGY: s2, MATRIX_SELECT: s2, ENC_OLS: s3, ENC_SOFTMAX: s3}
    for arm, s in sources.items():
        check_reproduced(s, arm, sc)
    probs = {arm: s.probs(arm) for arm, s in sources.items()}
    ll = {arm: s.log_loss(arm) for arm, s in sources.items()}
    split = skill_split(probs, sc, rcfg, cfg)
    signals = row_signals(bars, a, cfg)
    payoffs = hourly_payoffs(signals, a["fwd_return"], sc)
    control = {f"{x} - {y}": factor_control(ll[x] - ll[y], payoffs, cfg) for x, y in DIFFERENCES}
    return {
        f"label{TAG}": f"{LABEL}: the test months 2019-2024 were already scored by Reports n°2 and n°3; no hypothesis is tested here",
        f"registered{TAG}": registered_inputs(s2, s3, cfg),
        f"inputs{TAG}": {
            "report2_series_sha256": s2.sha256,
            "report2_json_sha256": s2.report_sha256,
            "report2_registered_run": bool(s2.report.get("registered", False)),
            "report3_series_sha256": s3.sha256,
            "report3_json_sha256": s3.report_sha256,
            "rows": int(sc.label.size),
            "hours": int(sc.hours.size),
            "first_hour": iso(int(sc.hours[0])),
            "last_hour": iso(int(sc.hours[-1])),
            "symbols": [str(x) for x in a["symbols"]],
            "rule": {"n_boot": rcfg.n_boot, "level": rcfg.level, "bootstrap_seed": rcfg.bootstrap_seed},
        },
        f"skill_split{TAG}": split,
        f"factor_control{TAG}": control,
        f"config{TAG}": asdict(cfg),
    }


# --- The report ---------------------------------------------------------------------------------


def _ci(ci: Mapping[str, Any] | None, digits: int = 4) -> str:
    return r2._ci(ci, digits)


def _k(m: Mapping[str, Any], name: str) -> Any:
    return m[f"{name}{TAG}"]


def render(m: Mapping[str, Any]) -> str:
    inp, split, control, cfg = _k(m, "inputs"), _k(m, "skill_split"), _k(m, "factor_control"), _k(m, "config")
    lines = [f"# The case study's two analyses ({LABEL})", ""]
    if not _k(m, "registered"):
        lines += [
            (
                "**NOT THE REGISTERED INPUTS.** A series, its configuration or this study's configuration differs from the registered "
                "one (a test or a synthetic run): its numbers are not results."
            ),
            "",
        ]
    lines += [
        (
            f"**{LABEL.capitalize()}.** Reports n°2 and n°3 already scored these test months, 2019-2024; no hypothesis is tested "
            "here. Each number below describes; none is a verdict."
        ),
        "",
        (
            f"Inputs: Report n°2's series `{inp['report2_series_sha256']}`, Report n°3's series `{inp['report3_series_sha256']}`; "
            f"{inp['rows']} scored rows over {inp['hours']} hours ({inp['first_hour'][:13]} -> {inp['last_hour'][:13]}). Intervals: "
            f"Report n°2's stationary bootstrap, {inp['rule']['n_boot']} resamples, {inp['rule']['level']:.0%} percentile."
        ),
        "",
        f"## 1. The split of the skill ({LABEL})",
        "",
        (
            'Skill = 1 - mean(arm) / mean(climatology-panel collapsed to the target), over hours. "Move": neutral against the rest, every '
            'scored row. "Direction": up against down, on the rows with a realized move. The log-loss gain over climatology is the sum '
            "of its move part and its direction part, exactly; the three-class Brier skill has no such split and is given as an estimate."
        ),
        "",
        (
            f"| arm ({LABEL}) | period | hours | move: Brier skill | move: log-loss skill | direction hours | direction: Brier skill | "
            "direction: log-loss skill | log-loss gain, move part | log-loss gain, direction part | three-class Brier skill |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for arm, by in split["arms"].items():
        for period, e in by.items():
            if "too_few_hours" in e:
                lines.append(f"| {arm} | {period} | {e['hours']} | - | - | {e['direction_hours']} | - | - | - | - | - |")
                continue
            g = e["log_loss_gain"]
            lines.append(
                f"| {arm} | {period} | {e['hours']} | {_ci(e['move']['brier_skill'])} | {_ci(e['move']['log_loss_skill'])} | "
                f"{e['direction_hours']} | {_ci(e['direction']['brier_skill'])} | {_ci(e['direction']['log_loss_skill'])} | "
                f"{_ci(g['move'], 5)} | {_ci(g['direction'], 5)} | {e['three_class']['brier_skill']:.4f} |"
            )
    lines += ["", f"| period ({LABEL}) | hours | rows | rows with a move | share with a move |", "|---|---|---|---|---|"]
    lines += [f"| {p} | {e['hours']} | {e['rows']} | {e['moving_rows']} | {e['share_moving']:.4f} |" for p, e in split["periods"].items()]
    lines += [
        "",
        f"## 2. The factor control ({LABEL})",
        "",
        (
            f"Each hourly log-loss difference regressed on the hourly payoffs of reversal, momentum ({cfg['momentum_bars']} hours, the last "
            f"skipped) and volatility-timed momentum (over {cfg['momentum_bars']} x the mean squared hourly return of the last "
            f"{cfg['volatility_bars']} hours): position from the pair's bars up to the decision bar, times the realized forward return, "
            f"averaged over the hour's scored rows. Payoffs are not centred, so the intercept is the difference left when the three "
            f"strategies earn nothing. Newey-West standard errors, Bartlett kernel, {cfg['hac_lags']} lags, fixed before any run."
        ),
        "",
    ]
    for name, c in control.items():
        lines += [
            f"### {name} ({LABEL})",
            "",
            f"Mean difference {c['mean_difference']:+.6f} (HAC standard error {c['mean_difference_hac_se']:.6f}); intercept "
            f"{c['intercept']:+.6f}; explained by the payoffs {c['explained']:+.6f}; share left "
            + ("-" if c["share_left"] is None else f"{c['share_left']:.3f}")
            + f"; R² {c['r2']:.4f}; {c['hours']} hours.",
            "",
            (
                f"| coefficient ({LABEL}) | estimate | HAC standard error | t | p | per payoff std | payoff mean | payoff std | alone: estimate | "
                "alone: t | alone: share left |"
            ),
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for coef in ("intercept", *FACTORS):
            v, pay, one = c["coefficients"][coef], c["payoffs"].get(coef), c["alone"].get(coef)
            lines.append(
                f"| {coef} | {v['estimate']:+.6g} | {v['hac_se']:.6g} | {v['t']:+.3f} | {v['p']:.4f} | "
                + (
                    "- | - | - | - | - | - |"
                    if pay is None
                    else f"{v['per_std']:+.6g} | {pay['mean']:+.6g} | {pay['std']:.6g} | {one['estimate']:+.6g} | {one['t']:+.3f} | "
                    + ("-" if one["share_left"] is None else f"{one['share_left']:.3f}")
                    + " |"
                )
            )
        lines.append("")
    lines += [
        f"Payoff correlations, {', '.join(FACTORS)} ({LABEL}): "
        + "; ".join(", ".join(f"{x:+.3f}" for x in row) for row in next(iter(control.values()))["payoff_correlation"])
        + "."
    ]
    return "\n".join(lines) + "\n"


def run_casestudy(
    s2: Series,
    s3: Series,
    bars: Mapping[str, pl.DataFrame],
    cfg: CaseStudyConfig,
    out: Path,
    *,
    provenance: dict[str, Any],
    contact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute both analyses and write the run folder."""
    started = time.perf_counter()
    metrics = compute(s2, s3, bars, cfg)
    out.mkdir(parents=True, exist_ok=True)
    r2._write_json(out / OUT_JSON, metrics)
    metrics = json.loads((out / OUT_JSON).read_text(encoding="utf-8"))
    (out / OUT_MD).write_text(render(metrics), encoding="utf-8", newline="\n")
    r2._write_json(
        out / "config.json",
        {
            f"config{TAG}": asdict(cfg),
            f"registered{TAG}": _k(metrics, "registered"),
            f"provenance{TAG}": provenance,
            f"inputs{TAG}": {
                "report2": str(s2.path),
                "report3": str(s3.path),
                "report2_series_sha256": s2.sha256,
                "report3_series_sha256": s3.sha256,
            },
        },
    )
    run = {
        f"finished_at{TAG}": datetime.now(UTC).isoformat(timespec="seconds"),
        f"seconds{TAG}": round(time.perf_counter() - started, 1),
        f"contact{TAG}": {"label": LABEL, **(contact or {})},
    }
    r2._write_json(out / "run.json", run)
    return metrics


def load_bars(symbols: Sequence[str], *, data_dir: Path | None = None) -> dict[str, pl.DataFrame]:
    """Each pair's hourly bars through ``load_klines`` (the seal), cut to ``known_at < DEVELOPMENT.end``: close and times only."""
    from olsprime.protocol import load_klines

    out = {}
    for s in symbols:
        frame = load_klines(s, "1h", data_dir=data_dir, columns=BAR_COLUMNS, caller="bench.casestudy")
        out[s] = frame.filter(pl.col("known_at") < DEVELOPMENT.end)
    return out


def _default_out() -> Path:
    base = runs_dir() / f"{datetime.now(UTC):%Y-%m-%d}-casestudy"
    out, k = base, 2
    while out.exists():
        out, k = base.with_name(f"{base.name}-{k}"), k + 1
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m olsprime.bench.casestudy", description=f"The case study's two analyses ({LABEL}).")
    parser.add_argument(
        "--report2", type=Path, required=True, help="Report n°2's run folder (the WSL2 re-run); its series.npz must be the registered one"
    )
    parser.add_argument("--report3", type=Path, required=True, help="Report n°3's run folder; its series.npz must be the registered one")
    parser.add_argument("--out", type=Path, default=None, help="run folder (default: <runs>/<UTC date>-casestudy, suffixed if taken)")
    args = parser.parse_args(argv)
    cfg = CaseStudyConfig()
    started = datetime.now(UTC)
    s2 = read_report2(args.report2)  # the registered digests only: refused here, before a bar is read
    s3 = read_report3(args.report3)
    symbols = [str(x) for x in s2.arrays["symbols"]]
    bars = load_bars(symbols)
    out = args.out or _default_out()
    contact = {
        "started_at": started.isoformat(timespec="seconds"),
        "read": "Report n°2's and n°3's series.npz (test months 2019-01 -> "
        "2024-12) and the hourly bars of their pairs through load_klines, cut to known_at < 2025-01-01",
        "report2_series_sha256": s2.sha256,
        "report3_series_sha256": s3.sha256,
        "pairs": len(symbols),
        "commit": prov_mod.git_commit(),
    }
    t = time.perf_counter()
    metrics = run_casestudy(s2, s3, bars, cfg, out, provenance=prov_mod.record(prov_mod.current_manifest()), contact=contact)
    print(f"casestudy ({LABEL}) written to {out} in {time.perf_counter() - t:.0f} s; registered inputs: {_k(metrics, 'registered')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
