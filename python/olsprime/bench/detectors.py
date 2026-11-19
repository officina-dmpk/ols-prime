"""!!! LEAKY FUNCTIONS, ON PURPOSE, MEASURED BY SEVERAL DETECTORS. NOT MODELS. !!!

Leak detectors measured against each other: ``docs/PROTOCOL.md``, "Leak detectors measured against each other
(iteration 5)" ("§n" below is that section's part n), and H15 in ``docs/HYPOTHESES.md``. The leaks are the
adversary's (:mod:`olsprime.bench.adversary`), drawn with ``placement="quantile"`` (the confirmatory population)
or ``"h1-bands"`` (iteration 3's population, descriptive).

**The detectors** (§2), each on one or more cut lists of each pair, each comparing an original run with one or
more re-executions under H1's catch rule (an output moves by more than 1e-9, turns missing or stops being
missing) at the compared rows that H1 scores:

- **FI**: H1's perturbation, x3 and /3, through the adversary's own bench and fast path (never re-implemented);
- **TRUNC-0**: the input ends at bar t (every later bar missing), rows t-10..t;
- **TRUNC-1**: TRUNC-0 at the cut t + 1 (rows t-9..t+1), the same code path;
- **RETILE**: the bars really sliced to ``[e - 2 tau + 1, e]`` and evaluated through a series view, every scored
  row of the tile ``[e - tau + 1, e]`` compared with the full run; tau in {256, 365}, anchored at the first scored row;
- **TWO-RUN**: bars t+1..t+10 perturbed by a seeded log-normal law and repaired (§2.5);
- **SHUFFLE**: the future-shuffle twins of :mod:`olsprime.bench.twins` (seed 20261030), at H1's cuts only.

TRUNC-0, TRUNC-1 and RETILE run under three conventions for a missing read (G, M, P:
:func:`olsprime.bench.adversary.evaluate_under`), applied to both runs of a comparison.

**Controls and assertions** (§3, §4): honest twins, cancelled controls FP1 and FP2 with a prediction written apart
from the detectors, Fonseca's classes M1 to M3, P's assertion, the read split, the mirror, RETILE against windowed
TRUNC-0, TRUNC-1's row t + 1, TWO-RUN's repair, and the equivalence gates. **The stop rule** (§7.4): every
assertion and gate is evaluated first and only pass or fail and counts are written; no rate or per-leak verdict
is written or printed unless all pass.

Usage::

    uv run --no-sync python -m olsprime.bench.detectors digest --seed S --placement quantile --table PATH
    uv run --no-sync python -m olsprime.bench.detectors run --seed S --two-run-seed S2 --placement P [--table PATH]
        [--bootstrap-seed B] [--n N] [--workers W] [--out DIR] [--synthetic]

No seed has a default. ``--synthetic`` runs on synthetic bars and refuses the three confirmatory seeds.
"""

from __future__ import annotations

import hashlib
import math
import re
import zlib
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

import numpy as np
import polars as pl

from olsprime.bench import adversary as adv
from olsprime.bench import detector_stats as ds
from olsprime.bench import invariance as inv
from olsprime.bench import pipeline as pp
from olsprime.bench import twins as tw
from olsprime.bench.perturb import PERTURBED_COLUMNS, _candle, _check_valid
from olsprime.data.binance_vision import Month

# --- Seeds (§8). The three confirmatory seeds are named here and never given as a default anywhere. ---------
CONFIRMATORY_POPULATION_SEED = 20261118
CONFIRMATORY_TWO_RUN_SEED = 20261119
CONFIRMATORY_BOOTSTRAP_SEED = 20261120
FORBIDDEN_IN_WAVE_3: frozenset[int] = frozenset({CONFIRMATORY_POPULATION_SEED, CONFIRMATORY_TWO_RUN_SEED, CONFIRMATORY_BOOTSTRAP_SEED})
DEVELOPMENT_POPULATION_SEED = 51118
DEVELOPMENT_TWO_RUN_SEED = 51119
DESCRIPTIVE_POPULATION_SEED = 20261029

SIGMAS: tuple[float, ...] = (0.1, 1.0)  # TWO-RUN: primary, secondary
TWO_RUN_RUNS = 8
SCHEDULE_ID = {"h1": 1, "long": 2}
TAUS: tuple[int, ...] = (256, 365)
CONVENTIONS = adv.CONVENTIONS
TRUNCATION = ("TRUNC-0", "TRUNC-1", "ENDS")  # the parts of the truncation bench; ENDS: TRUNC-0 at RETILE's ends
EXTRA_QUANTITIES: tuple[str, ...] = ("row", "pair_id", "close_next_frozen")  # read by M1 (gate) and M3 (frozen close)


# --- The development digest (§1.7) -------------------------------------------------------------------------


def digest_line(leak: adv.Leak) -> str:
    """One leak's line of the digest: ``repr`` of its expression, its output and ``repr`` of its tags (not ``render``)."""
    return repr(leak.expr) + "\t" + leak.output + "\t" + repr(leak.tags) + "\n"


def development_digest(leaks: Sequence[adv.Leak]) -> str:
    """SHA-256 of one :func:`digest_line` per leak, in order, UTF-8 (§1.7). Machine-specific: see :func:`portable_digest`."""
    h = hashlib.sha256()
    for leak in leaks:
        h.update(digest_line(leak).encode("utf-8"))
    return h.hexdigest()


_FLOAT = re.compile(r"-?\d+\.\d+(?:e[-+]?\d+)?")


def portable_digest(leaks: Sequence[adv.Leak], digits: int = 12) -> str:
    """:func:`development_digest` with every float literal rounded to ``digits`` significant digits.

    The generator's ``exp`` of a log-uniform draw (margins, thresholds) differs by one ulp between Windows and Linux:
    the same uniform draw, bit for bit, gives ``exp`` results one ulp apart under the Windows C runtime and glibc
    (``math.exp`` and ``np.exp`` alike; numpy 2.5.4; 4 of the first 2,000 leaks of seed 20261029). The exact digest
    is a property of the machine; this one is not, at 12 digits, on the two machines checked (wave 3).
    """
    h = hashlib.sha256()
    for leak in leaks:
        h.update(_FLOAT.sub(lambda m: format(float(m.group()), f".{digits}g"), digest_line(leak)).encode("utf-8"))
    return h.hexdigest()


# --- Configuration ------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class DetectorConfig:
    """One run of the benchmark. The seeds have no default: a run names them."""

    population_seed: int
    two_run_seed: int
    placement: str = adv.H1_BANDS
    n: int = 10_000
    bootstrap_seed: int | None = None  # §4.15; without it the bootstrap is not run
    adversary: adv.AdversaryConfig = field(default_factory=adv.AdversaryConfig)  # H1, the long schedule, the gates
    sigmas: tuple[float, ...] = SIGMAS
    two_run_runs: int = TWO_RUN_RUNS
    shuffle_k: int = tw.K_TWINS
    shuffle_seed: int = tw.TWIN_SEED
    taus: tuple[int, ...] = TAUS
    bootstrap_subsets: int = 2000
    bootstrap_dates: int = 8


# --- Synthetic bars (tests and smoke runs only) ----------------------------------------------------------------

SYNTHETIC_PAIRS: dict[str, int] = {"BTCUSDT": 11, "ETHUSDT": 12}
SYNTHETIC_START = datetime(2017, 8, 17, tzinfo=UTC)  # the first real daily bar of both pairs
SYNTHETIC_DAYS = 2800  # cut to the development period by ``development_bars``: 2,694 bars, 2017-08-17 to 2024-12-31


def synthetic_pairs(*, degrade: bool = False) -> dict[str, pl.DataFrame]:
    """Two pairs of synthetic daily bars over the real dates of the development period. Reads no data.

    ``degrade`` gives about 2 % of bars a zero upper wick, 2 % a zero lower wick and 2 % zero volume (and zero
    trades): undefined wick ratios, VWAPs and shares, so that the rules about undefined reads are exercised.
    """
    from olsprime.bench.synthetic import synthetic_bars

    out = {}
    for pair, seed in SYNTHETIC_PAIRS.items():
        b = inv.development_bars(synthetic_bars(pair, start=SYNTHETIC_START, days=SYNTHETIC_DAYS, seed=seed))
        out[pair] = _degrade(b, seed) if degrade else b
    return out


def _degrade(df: pl.DataFrame, seed: int) -> pl.DataFrame:
    rng = np.random.default_rng([seed, 5])
    n = df.height
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    hi = np.where(rng.random(n) < 0.02, np.maximum(o, c), df["high"].to_numpy())
    lo = np.where(rng.random(n) < 0.02, np.minimum(o, c), df["low"].to_numpy())
    zero = rng.random(n) < 0.02
    cols = [pl.Series("high", hi), pl.Series("low", lo)]
    for name in ("volume", "quote_volume", "taker_buy_base_volume", "taker_buy_quote_volume"):
        cols.append(pl.Series(name, np.where(zero, 0.0, df[name].to_numpy())))
    cols.append(pl.Series("trades", np.where(zero, 0, df["trades"].to_numpy()), dtype=df.schema["trades"]))
    return df.with_columns(cols)


# --- Schedules ---------------------------------------------------------------------------------------------------


@dataclass
class PairSchedule:
    """One pair's bars, scored rows and cut lists (H1's in H1's order; the long schedule in time order)."""

    bars: pl.DataFrame
    scored: np.ndarray  # (rows,) bool
    folds: list[Any]
    h1: list[inv.Cut]
    long: list[inv.Cut]
    ends: list[tuple[int, int, int]]  # (tau, m, e)


def retile_ends(scored: np.ndarray, taus: Sequence[int] = TAUS) -> list[tuple[int, int, int]]:
    """RETILE's ends ``e = first + m tau - 1`` inside the scored rows, ``first`` the first scored row (§2.4)."""
    rows = np.flatnonzero(scored)
    first, last = int(rows[0]), int(rows[-1])
    out = []
    for tau in taus:
        m = 1
        while first + m * tau - 1 <= last:
            e = first + m * tau - 1
            if not scored[e]:
                raise AssertionError(f"RETILE's end {e} is not a scored row")
            out.append((tau, m, e))
            m += 1
    return out


def schedule_pair(bars: pl.DataFrame, cfg: DetectorConfig) -> PairSchedule:
    h1 = cfg.adversary.h1
    frame = pp.build_frame(bars, h1.interval, h1.h)
    folds = pp.make_folds(frame, h1.interval, h1.h, Month(*h1.start), Month(*h1.end))
    scored = np.zeros(bars.height, dtype=bool)
    scored[adv.scored_rows(folds)] = True
    (_, h1_cuts, _), (_, long_cuts, _) = adv.schedules(bars, folds, cfg.adversary)
    return PairSchedule(bars, scored, folds, h1_cuts, long_cuts, retile_ends(scored, cfg.taus))


def extra_quantities(bars: pl.DataFrame, pair_id: int) -> dict[str, np.ndarray]:
    """The row index, the pair's position and M3's frozen next close, read from the original bars of every run."""
    n = bars.height
    close = bars["close"].cast(pl.Float64).to_numpy()
    frozen = np.full(n, np.nan)
    frozen[:-1] = close[1:]
    return {"row": np.arange(n, dtype=np.float64), "pair_id": np.full(n, float(pair_id)), "close_next_frozen": frozen}


def _all_quantities(bars: pl.DataFrame, extra: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {**adv.quantities(bars), **extra}


def _stack(blocks: Sequence[Sequence[dict[str, np.ndarray]]]) -> adv.WindowView:
    names = list(blocks[0][0])
    return adv.WindowView({name: np.stack([w[name] for block in blocks for w in block]) for name in names})


def _compared(scored: np.ndarray, cut: int) -> np.ndarray:
    rows = cut - adv.FUTURE_REACH + np.arange(adv.COMPARED)
    ok = (rows >= 0) & (rows < scored.size)
    return np.where(ok, scored[np.clip(rows, 0, scored.size - 1)], False)


def _cut_meta(pair: str, schedule: str, k: int, cut: inv.Cut) -> dict[str, Any]:
    return {"pair": pair, "schedule": schedule, "k": k, "index": cut.index, "open_time": cut.open_time.isoformat(),
            "kind": cut.kind, "mirror": inv.is_mirrored(k)}  # fmt: skip


# --- TWO-RUN's law and repair (§2.5) -------------------------------------------------------------------------


def two_run_z(seed: int, pair: str, schedule_id: int, k: int, run: int) -> np.ndarray:
    """``z`` of shape (10, 9): rows are bars t+1..t+10, columns follow ``PERTURBED_COLUMNS``. ``run`` is 1, 2, ..."""
    if run < 1:
        raise ValueError("TWO-RUN's runs are numbered from 1")
    rng = np.random.default_rng([seed, zlib.crc32(pair.encode("ascii")), schedule_id, k, run])
    return rng.standard_normal((adv.FUTURE_REACH, len(PERTURBED_COLUMNS)))


class RepairFailed(AssertionError):
    """A check of TWO-RUN's repair failed: a bench bug, never evidence (§3.4)."""


def two_run_bars(bars: pl.DataFrame, t: int, sigma: float, z: np.ndarray) -> tuple[pl.DataFrame, dict[str, Any]]:
    """The bars with t+1..t+10 perturbed by ``exp(sigma z)`` and repaired exactly as §2.5 says, and the repair's counts."""
    n = bars.height
    rows = np.arange(t + 1, min(t + 1 + adv.FUTURE_REACH, n))
    z = z[: rows.size]  # rows past the series' end are discarded
    f = {c: np.exp(sigma * z[:, j]) for j, c in enumerate(PERTURBED_COLUMNS)}
    col = {c: bars[c].cast(pl.Float64).to_numpy().copy() for c in PERTURBED_COLUMNS}
    o, h, lo, c = (col[k][rows] for k in ("open", "high", "low", "close"))
    o2, c2 = o * f["open"], c * f["close"]
    _, uw, lw = _candle(o, h, lo, c)  # wicks in log units, as perturb._candle computes them
    uw2, lw2 = uw * f["high"], lw * f["low"]  # each multiplied by its own factor, no offset
    h2 = np.maximum(o2, c2) * np.exp(uw2)
    lo2 = np.minimum(o2, c2) * np.exp(-lw2)
    v, qv, tb, tq, tr = (col[k][rows] for k in ("volume", "quote_volume", "taker_buy_base_volume", "taker_buy_quote_volume", "trades"))
    has = v > 0
    with np.errstate(divide="ignore", invalid="ignore"):
        vwap = np.where(has, qv / np.where(has, v, 1.0), np.nan)
    v2 = v * f["volume"]
    raw = vwap * f["quote_volume"]
    vw2 = np.clip(raw, lo2, h2)
    if not np.all(~has | ((vw2 >= lo2) & (vw2 <= h2))):  # vwap' as constructed, before quote' = v' vwap'
        raise RepairFailed("TWO-RUN: vwap' outside [low', high'] as constructed")
    q2 = v2 * vw2
    tb_raw, tq_raw = tb * f["taker_buy_base_volume"], tq * f["taker_buy_quote_volume"]
    tb2, tq2 = np.minimum(tb_raw, v2), np.minimum(tq_raw, q2)
    tr2 = np.maximum(np.rint(tr * f["trades"]), 1.0)
    new = {"open": o2, "high": h2, "low": lo2, "close": c2,
           "volume": np.where(has, v2, v), "quote_volume": np.where(has, q2, qv),
           "taker_buy_base_volume": np.where(has, tb2, tb), "taker_buy_quote_volume": np.where(has, tq2, tq),
           "trades": np.where(has, tr2, tr)}  # fmt: skip  (a zero-volume bar keeps every volume, taker volume and count)
    for k in col:
        col[k][rows] = new[k]
    out = bars.with_columns([pl.Series(k, np.rint(x).astype(np.int64) if k == "trades" else x, dtype=bars.schema[k]) for k, x in col.items()])
    # Checks (§2.5, item 4).
    q0, q1 = adv.quantities(bars), adv.quantities(out)
    if not np.array_equal(np.isnan(q0["wick_ratio"][rows]), np.isnan(q1["wick_ratio"][rows])):
        raise RepairFailed("TWO-RUN: the wick ratio's definedness changed in a perturbed bar")
    try:
        _check_valid(out.head(t + 1 + adv.FUTURE_REACH), t)  # rows t+1..t+10 only
    except AssertionError as e:
        raise RepairFailed(f"TWO-RUN: {e}") from e
    stored_q = out["quote_volume"].cast(pl.Float64).to_numpy()[rows]
    stored_v = out["volume"].cast(pl.Float64).to_numpy()[rows]
    with np.errstate(divide="ignore", invalid="ignore"):
        stored_vwap = np.where(has, stored_q / np.where(has, stored_v, 1.0), np.nan)
    if np.any(has & ((stored_vwap < lo2 * (1 - 1e-12)) | (stored_vwap > h2 * (1 + 1e-12)))):
        raise RepairFailed("TWO-RUN: the stored VWAP is outside [low', high'] beyond 1e-12")
    for c_ in PERTURBED_COLUMNS:  # the bars outside t+1..t+10 are returned bit for bit
        a_, b_ = bars[c_].to_numpy(), out[c_].to_numpy()
        keep = np.ones(n, dtype=bool)
        keep[rows] = False
        if not np.array_equal(a_[keep], b_[keep]):
            raise RepairFailed(f"TWO-RUN moved {c_} outside bars t+1..t+10")
    stats = {
        "bars": int(rows.size),
        "with_volume": int(has.sum()),
        "vwap_clip_binds": int((has & (raw != vw2)).sum()),
        "taker_base_cap_binds": int((has & (tb_raw > v2)).sum()),
        "taker_quote_cap_binds": int((has & (tq_raw > q2)).sum()),
        "body_before": q0["body"][rows],
        "body_after": q1["body"][rows],
        "fill_before": q0["fill"][rows],
        "fill_after": q1["fill"][rows],
    }
    return out, stats


# --- Benches --------------------------------------------------------------------------------------------------


@dataclass
class Retile:
    """RETILE's two views: the full series of each pair and the sliced tiles, every one at width ``2 max(tau)``."""

    full: StackedSeriesView
    tiles: StackedSeriesView
    ends: list[dict[str, Any]]  # pair, tau, m, e
    pair_index: np.ndarray  # (ends,) row of ``full`` for each end
    rows: np.ndarray  # (ends, W) the rows compared, e - W + 1 .. e
    scored: np.ndarray  # (ends, W) scored rows of the tile [e - tau + 1, e]
    width: int


class StackedSeriesView:
    """:class:`olsprime.bench.adversary.SeriesView` row by row over stacked series: NaN outside each series."""

    def __init__(self, q: dict[str, np.ndarray]) -> None:
        self.q = q
        self.n = next(iter(q.values())).shape[1]

    def at(self, name: str, o: int) -> np.ndarray:
        a, n = self.q[name], self.n
        out = np.full(a.shape, np.nan)
        if abs(o) < n:
            if o >= 0:
                out[:, : n - o] = a[:, o:]
            else:
                out[:, -o:] = a[:, : n + o]
        return out


@dataclass
class Benches:
    pairs: list[str]
    schedules: dict[str, PairSchedule]
    cuts: list[dict[str, Any]]  # FI's cuts: per pair, H1's then the long schedule's (adv.build_bench's order)
    fi: adv.Bench
    trunc: adv.Bench  # TRUNC-0 at ``cuts``, TRUNC-1 at ``cuts`` + 1, TRUNC-0 at RETILE's ends; one run
    trunc_parts: dict[str, np.ndarray]  # part -> rows of ``trunc``
    two_run: adv.Bench  # ``cuts``; runs (sigma, run) in order
    two_run_runs: list[tuple[float, int]]
    shuffle: adv.Bench  # H1's cuts; K twins
    shuffle_rows: np.ndarray  # rows of ``cuts`` that SHUFFLE's cuts are
    retile: Retile
    two_run_stats: dict[str, Any]
    last_row_cuts: dict[str, int]  # per schedule, cuts where t + 1 is the series' last row (TRUNC-1 cannot flag)

    def rows(self, schedule: str) -> np.ndarray:
        return np.array([i for i, c in enumerate(self.cuts) if c["schedule"] == schedule], dtype=np.int64)


def _inject_extras(bench: adv.Bench, extras: dict[str, dict[str, np.ndarray]], blocks: int) -> None:
    """Every run of a bench reads the extra quantities of the original bars (the same window in every block)."""
    windows = [adv._window({**extras[c["pair"]], "close": extras[c["pair"]]["row"]}, c["index"]) for c in bench.cuts]
    for name in EXTRA_QUANTITIES:
        one = np.stack([w[name] for w in windows])
        bench.view.w[name] = np.concatenate([one] * blocks)


def build_benches(bars_by_pair: dict[str, pl.DataFrame], cfg: DetectorConfig) -> Benches:
    """Every detector's runs once, for every pair, in the pairs' order."""
    pairs = list(bars_by_pair)
    sched = {p: schedule_pair(b, cfg) for p, b in bars_by_pair.items()}
    extras = {p: extra_quantities(b, i) for i, (p, b) in enumerate(bars_by_pair.items())}
    full_q = {p: _all_quantities(b, extras[p]) for p, b in bars_by_pair.items()}

    # FI: the adversary's own bench (H1's cuts and the long schedule), the extras added to every block.
    fi = adv.build_bench(bars_by_pair, cfg.adversary)
    _inject_extras(fi, extras, 1 + len(fi.directions))
    cuts = fi.cuts
    for c in cuts:
        s = sched[c["pair"]]
        expected = (s.h1 if c["schedule"] == "h1" else s.long)[c["k"]].index
        if expected != c["index"]:
            raise AssertionError("the FI bench's cuts are not the schedules'")

    # Truncation: one code path, at t (TRUNC-0), at t + 1 (TRUNC-1) and at RETILE's ends (ENDS).
    entries: list[tuple[str, dict[str, Any], int]] = []
    last_row = {"h1": 0, "long": 0}
    for c in cuts:
        entries.append(("TRUNC-0", c, c["index"]))
    for c in cuts:
        s = sched[c["pair"]]
        t1 = c["index"] + 1
        if not (t1 < s.bars.height and s.scored[t1]):  # §2.3
            raise AssertionError(f"TRUNC-1: row t + 1 = {t1} does not exist or is not scored ({c['pair']} {c['schedule']})")
        last_row[c["schedule"]] += int(t1 == s.bars.height - 1)
        entries.append(("TRUNC-1", c, t1))
    end_meta = []
    for p in pairs:
        for tau, m, e in sched[p].ends:
            meta = {"pair": p, "schedule": "ends", "tau": tau, "m": m, "index": e, "open_time": sched[p].bars["open_time"][e].isoformat()}
            end_meta.append(meta)
            entries.append(("ENDS", meta, e))
    orig_w, trunc_w, masks = [], [], []
    for _, c, at in entries:
        w = adv._window(full_q[c["pair"]], at)
        cut_w = {k: v.copy() for k, v in w.items()}
        for v in cut_w.values():
            v[adv.PAST_REACH + 1 :] = np.nan  # every bar after the cut is missing
        orig_w.append(w)
        trunc_w.append(cut_w)
        masks.append(_compared(sched[c["pair"]].scored, at))
    trunc_cuts = [{**c, "part": part, "at": at} for part, c, at in entries]
    trunc = adv.Bench(_stack([orig_w, trunc_w]), trunc_cuts, np.stack(masks), ("truncated",), {})
    parts = {name: np.array([i for i, (part, _, _) in enumerate(entries) if part == name], dtype=np.int64) for name in TRUNCATION}

    # TWO-RUN: z drawn once per (pair, schedule, cut, run), shared by the two sigmas.
    runs = [(s_, r) for s_ in cfg.sigmas for r in range(1, cfg.two_run_runs + 1)]
    blocks: list[list[dict[str, np.ndarray]]] = [[] for _ in range(1 + len(runs))]
    stats: dict[float, dict[str, Any]] = {s_: {"bars": 0, "with_volume": 0, "vwap_clip_binds": 0, "taker_base_cap_binds": 0,
                                               "taker_quote_cap_binds": 0, "body_before": [], "body_after": [],
                                               "fill_before": [], "fill_after": []} for s_ in cfg.sigmas}  # fmt: skip
    for c in cuts:
        p = c["pair"]
        bars = bars_by_pair[p]
        blocks[0].append(adv._window(full_q[p], c["index"]))
        zs = {r: two_run_z(cfg.two_run_seed, p, SCHEDULE_ID[c["schedule"]], c["k"], r) for r in range(1, cfg.two_run_runs + 1)}
        for j, (sigma, r) in enumerate(runs):
            out, st = two_run_bars(bars, c["index"], sigma, zs[r])
            blocks[1 + j].append(adv._window(_all_quantities(out, extras[p]), c["index"]))
            for key, val in st.items():
                stats[sigma][key] = stats[sigma][key] + ([val] if isinstance(val, np.ndarray) else val)
    two_run = adv.Bench(_stack(blocks), cuts, fi.scored, tuple(f"s{s_:g}-r{r}" for s_, r in runs), {})
    two_run_stats = {}
    for sigma, st in stats.items():
        body_b, body_a, fill_b, fill_a = (np.concatenate(st[k]) for k in ("body_before", "body_after", "fill_before", "fill_after"))
        wv = st["with_volume"]
        two_run_stats[f"{sigma:g}"] = {
            "bars": st["bars"], "with_volume": wv,
            "vwap_clip_binds": _part(st["vwap_clip_binds"], wv), "taker_base_cap_binds": _part(st["taker_base_cap_binds"], wv),
            "taker_quote_cap_binds": _part(st["taker_quote_cap_binds"], wv),
            "median_body": {"before": float(np.nanmedian(body_b)), "after": float(np.nanmedian(body_a))},
            "median_fill": {"before": float(np.nanmedian(fill_b)), "after": float(np.nanmedian(fill_a))},
        }  # fmt: skip

    # SHUFFLE: twins.py's own twins at H1's cuts (same seed, cuts and bars as iteration 4).
    tcfg = tw.TwinsConfig(k=cfg.shuffle_k, seed=cfg.shuffle_seed, adversary=cfg.adversary)
    shuffle = tw.build(bars_by_pair, tcfg).twins
    _inject_extras(shuffle, extras, 1 + len(shuffle.directions))
    h1_rows = [i for i, c in enumerate(cuts) if c["schedule"] == "h1"]
    if [(c["pair"], c["k"], c["index"]) for c in shuffle.cuts] != [(cuts[i]["pair"], cuts[i]["k"], cuts[i]["index"]) for i in h1_rows]:
        raise AssertionError("SHUFFLE's cuts are not FI's H1 cuts")

    retile = build_retile(bars_by_pair, sched, extras, full_q, end_meta, cfg)
    return Benches(pairs, sched, cuts, fi, trunc, parts, two_run, runs, shuffle, np.array(h1_rows, dtype=np.int64), retile,
                   two_run_stats, last_row)  # fmt: skip


def _part(k: int, n: int) -> dict[str, Any]:
    return {"count": int(k), "of": int(n), "share": (k / n) if n else math.nan}


def build_retile(bars_by_pair: dict[str, pl.DataFrame], sched: dict[str, PairSchedule], extras: dict[str, dict[str, np.ndarray]],
                 full_q: dict[str, dict[str, np.ndarray]], end_meta: list[dict[str, Any]], cfg: DetectorConfig) -> Retile:  # fmt: skip
    """RETILE: each tile's input window really sliced from the bars, its quantities computed on the slice (§2.4)."""
    pairs = list(bars_by_pair)
    width = max(cfg.taus)
    length = 2 * width
    n_max = max(b.height for b in bars_by_pair.values())
    names = list(full_q[pairs[0]])
    full = {k: np.full((len(pairs), n_max), np.nan) for k in names}
    for i, p in enumerate(pairs):
        for k in names:
            full[k][i, : bars_by_pair[p].height] = full_q[p][k]
    tiles = {k: np.full((len(end_meta), length), np.nan) for k in names}
    rows = np.zeros((len(end_meta), width), dtype=np.int64)
    scored = np.zeros((len(end_meta), width), dtype=bool)
    for j, m in enumerate(end_meta):
        p, tau, e = m["pair"], m["tau"], m["index"]
        start = e - 2 * tau + 1
        if start < 0:
            raise AssertionError(f"RETILE's input window at {e} starts before the series")
        sliced = bars_by_pair[p].slice(start, 2 * tau)  # really slicing the bars
        q = _all_quantities(sliced, {k: v[start : e + 1] for k, v in extras[p].items()})
        for k in names:
            tiles[k][j, length - 2 * tau :] = q[k]
        rows[j] = e - width + 1 + np.arange(width)
        in_tile = rows[j] >= e - tau + 1
        scored[j] = in_tile & sched[p].scored[rows[j]]
    pair_index = np.array([pairs.index(m["pair"]) for m in end_meta], dtype=np.int64)
    return Retile(StackedSeriesView(full), StackedSeriesView(tiles), end_meta, pair_index, rows, scored, width)


# --- The kernel: H1's catch rule row by row, and the reads ---------------------------------------------------


@dataclass
class Rows:
    """One unit (a leak, a twin, a control) on one bench under one convention, row by row."""

    flags: np.ndarray  # (C, R, W) H1's catch rule at the scored compared rows
    bits: np.ndarray  # (C, R, W) a single differing bit at the scored compared rows
    missing_read: np.ndarray  # (C, R, W) some read missing in one run and not in the other
    removed_read: np.ndarray  # (C, R, W) some read defined in the original run and missing in the other
    all_defined: np.ndarray  # (C, R, W) every read defined in both runs
    orig_missing: np.ndarray  # (C, W) every output missing in the original run
    or_mask: np.ndarray  # (C, 1 + R, W) some read missing, per run (the original first)
    output_missing: np.ndarray  # (C, 1 + R, W) some output missing, per run
    orig_bits: list[np.ndarray]  # per output, (C, W) the original run's values

    @property
    def cut_flags(self) -> np.ndarray:  # (C, R)
        return self.flags.any(axis=2)

    @property
    def cut_bits(self) -> np.ndarray:
        return self.bits.any(axis=2)


def _moved(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """H1's catch rule (``invariance.compare``, ``adversary.evaluate_fast``): a move above 1e-9 or a change of missingness."""
    both = ~np.isnan(a) & ~np.isnan(b)
    change = np.where(both, np.abs(a - b), 0.0)
    return (change > inv.CAUGHT_ABOVE) | (np.isnan(a) != np.isnan(b))


def compare(orig_out: Sequence[np.ndarray], run_outs: Sequence[Sequence[np.ndarray]], orig_reads: Sequence[np.ndarray],
            run_reads: Sequence[Sequence[np.ndarray]], scored: np.ndarray) -> Rows:  # fmt: skip
    """Outputs and reads already aligned: original (C, W), each run (C, W); reads as ``isnan`` arrays."""
    c, w = scored.shape
    r = len(run_outs)
    flags = np.zeros((c, r, w), dtype=bool)
    bits = np.zeros((c, r, w), dtype=bool)
    for j, outs in enumerate(run_outs):
        for a, b in zip(orig_out, outs, strict=True):
            flags[:, j] |= _moved(a, b)
            bits[:, j] |= np.ascontiguousarray(a).view(np.uint64) != np.ascontiguousarray(b).view(np.uint64)
    flags &= scored[:, None, :]
    bits &= scored[:, None, :]
    missing_read = np.zeros((c, r, w), dtype=bool)
    removed = np.zeros((c, r, w), dtype=bool)
    defined = np.ones((c, r, w), dtype=bool)
    or_mask = np.zeros((c, 1 + r, w), dtype=bool)
    for k, na in enumerate(orig_reads):
        or_mask[:, 0] |= na
        for j in range(r):
            nb = run_reads[j][k]
            or_mask[:, 1 + j] |= nb
            missing_read[:, j] |= na != nb
            removed[:, j] |= ~na & nb
            defined[:, j] &= ~na & ~nb
    out_missing = np.zeros((c, 1 + r, w), dtype=bool)
    for k, a in enumerate(orig_out):
        out_missing[:, 0] |= np.isnan(a)
        for j in range(r):
            out_missing[:, 1 + j] |= np.isnan(run_outs[j][k])
    orig_missing = np.logical_and.reduce([np.isnan(a) for a in orig_out]) if orig_out else np.zeros((c, w), bool)
    return Rows(flags, bits, missing_read, removed, defined, orig_missing, or_mask, out_missing, [np.asarray(a) for a in orig_out])


def _as_blocks(arr: Any, c: int, blocks: int, w: int) -> list[np.ndarray]:
    a = np.ascontiguousarray(np.broadcast_to(np.asarray(arr, dtype=np.float64), (c * blocks, w)))
    return [a[c * j : c * (j + 1)] for j in range(blocks)]


def _bool_blocks(arr: np.ndarray, c: int, blocks: int) -> list[np.ndarray]:
    return [arr[c * j : c * (j + 1)] for j in range(blocks)]


def judge_window(unit: adv.Leak, bench: adv.Bench, convention: str = "G") -> Rows:
    """One unit on a windowed bench (FI, truncation, TWO-RUN, SHUFFLE) under a convention."""
    c, r, w = bench.n_cuts, len(bench.directions), adv.COMPARED
    rec = adv.RecordingView(bench.view)
    outs = [_as_blocks(v, c, 1 + r, w) for v in adv.outputs_under(unit, rec, convention).values()]
    reads = [_bool_blocks(np.isnan(bench.view.at(q, o)), c, 1 + r) for q, o in sorted(rec.reads)]
    return compare([o[0] for o in outs], [[o[1 + j] for o in outs] for j in range(r)], [x[0] for x in reads],
                   [[x[1 + j] for x in reads] for j in range(r)], bench.scored)  # fmt: skip


def judge_retile(unit: adv.Leak, rt: Retile, convention: str = "G") -> Rows:
    """One unit on RETILE: the full run at the tile's rows against the sliced run, under a convention."""
    rec = adv.RecordingView(rt.full)
    full = adv.outputs_under(unit, rec, convention)
    tiles = adv.outputs_under(unit, rt.tiles, convention)
    n, wd = len(rt.ends), rt.width

    def gather(x: Any) -> np.ndarray:
        x = np.broadcast_to(np.asarray(x, dtype=np.float64), (rt.full.q["row"].shape[0], rt.full.n))
        return np.ascontiguousarray(x[rt.pair_index[:, None], rt.rows])

    def tail(x: Any) -> np.ndarray:
        x = np.broadcast_to(np.asarray(x, dtype=np.float64), (n, rt.tiles.n))
        return np.ascontiguousarray(x[:, rt.tiles.n - wd :])

    names = list(full)
    reads = sorted(rec.reads)
    orig_reads = [gather(np.isnan(rt.full.at(q, o))) for q, o in reads]
    run_reads = [[tail(np.isnan(rt.tiles.at(q, o))).astype(bool) for q, o in reads]]
    return compare([gather(full[k]) for k in names], [[tail(tiles[k]) for k in names]], [x.astype(bool) for x in orig_reads], run_reads, rt.scored)


# --- Every detector on one unit -------------------------------------------------------------------------------

DETECTORS: tuple[str, ...] = ("FI", "TRUNC-0", "TRUNC-1", "RETILE", "TWO-RUN", "SHUFFLE")
PRIMARY: tuple[str, ...] = ("FI", "TRUNC-0", "TWO-RUN", "SHUFFLE")  # the union's members and §4.7's pairs


def judge_all(unit: adv.Leak, b: Benches, conventions: Sequence[str] = CONVENTIONS) -> dict[str, Rows]:
    """The unit on every bench: FI, TWO-RUN and SHUFFLE under G; the truncation bench and RETILE under each convention."""
    out = {"FI": judge_window(unit, b.fi), "TWO-RUN": judge_window(unit, b.two_run), "SHUFFLE": judge_window(unit, b.shuffle)}
    for conv in conventions:
        out[f"TRUNC/{conv}"] = judge_window(unit, b.trunc, conv)
        out[f"RETILE/{conv}"] = judge_retile(unit, b.retile, conv)
    return out


def cut_verdicts(rows: dict[str, Rows], b: Benches, *, bits: bool = False) -> dict[tuple[str, str], np.ndarray]:
    """(detector[/convention], schedule) -> (cuts, runs) bool, the cuts in the schedule's order."""
    h1, long_ = b.rows("h1"), b.rows("long")
    out: dict[tuple[str, str], np.ndarray] = {}
    for key, r in rows.items():
        f = r.cut_bits if bits else r.cut_flags
        if key in ("FI", "TWO-RUN"):
            out[(key, "h1")], out[(key, "long")] = f[h1], f[long_]
        elif key == "SHUFFLE":
            out[(key, "h1")] = f
        elif key.startswith("TRUNC/"):
            conv = key.split("/")[1]
            for part in ("TRUNC-0", "TRUNC-1"):
                p = f[b.trunc_parts[part]]
                out[(f"{part}/{conv}", "h1")], out[(f"{part}/{conv}", "long")] = p[h1], p[long_]
            out[(f"ENDS/{conv}", "ends")] = f[b.trunc_parts["ENDS"]]
        elif key.startswith("RETILE/"):
            out[(key, "ends")] = f
    return out


# --- Controls (§3) --------------------------------------------------------------------------------------------


def hand_leak(i: int, expr: Any, output: str = "target", family: str = "control", **tags: str) -> adv.Leak:
    base = {k: "control" for k in adv.TAG_KEYS} | {"family": family, "output": output} | tags
    return adv.Leak(i, family, expr, output, tuple((k, base[k]) for k in adv.TAG_KEYS))


CANCELLED_KINDS: tuple[str, ...] = ("FP1", "FP2-min", "FP2-fmin")


@dataclass(frozen=True)
class Cancelled:
    """A cancelled read of the future (§3.2): ``w + (v - v)``, ``minimum(w, w + 0 v)`` or ``fmin(w, w + 0 v)``."""

    kind: str
    w: Any
    v: Any
    binary = False

    def evaluate(self, view: Any) -> np.ndarray:
        w = np.asarray(self.w.evaluate(view), dtype=np.float64)
        v = np.asarray(self.v.evaluate(view), dtype=np.float64)
        with np.errstate(invalid="ignore"):
            if self.kind == "FP1":
                return w + (v - v)
            if self.kind == "FP2-min":
                return np.minimum(w, w + 0.0 * v)
            if self.kind == "FP2-fmin":
                return np.fmin(w, w + 0.0 * v)
        raise ValueError(f"unknown cancelled control {self.kind!r}")

    def offsets(self) -> frozenset[int]:
        return self.w.offsets() | self.v.offsets()

    def twin(self) -> Cancelled:
        raise ValueError("a control has no twin")

    def render(self) -> str:
        w, v = self.w.render(), self.v.render()
        return {"FP1": f"({w} + ({v} - {v}))", "FP2-min": f"min({w}, {w} + 0 x {v})"}.get(self.kind, f"fmin({w}, {w} + 0 x {v})")


_CHILDREN = ("lhs", "rhs", "a", "b")


def _walk(expr: Any, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any]]:
    """Depth first, children in ``lhs, rhs, a, b`` order; At and Agg are leaves."""
    out = [(path, expr)]
    if isinstance(expr, (adv.At, adv.Agg)):
        return out
    for name in _CHILDREN:
        child = getattr(expr, name, None)
        if child is not None and hasattr(child, "evaluate"):
            out += _walk(child, (*path, name))
    return out


def _get(expr: Any, path: tuple[str, ...]) -> Any:
    for name in path:
        expr = getattr(expr, name)
    return expr


def _put(expr: Any, path: tuple[str, ...], node: Any) -> Any:
    if not path:
        return node
    return replace(expr, **{path[0]: _put(getattr(expr, path[0]), path[1:], node)})


def future_node(expr: Any) -> tuple[tuple[str, ...], Any] | None:
    """§3.2's ``v``: the At or Agg at a positive offset of largest reach, the first in the walk on ties; None if none."""
    best, reach = None, 0
    for path, node in _walk(expr):
        r = node.o if isinstance(node, adv.At) else node.hi if isinstance(node, adv.Agg) and node.lo >= 1 else 0
        if r > reach:
            best, reach = (path, node), r
    return best


def cancelled_control(leak: adv.Leak, kind: str) -> adv.Leak | None:
    """``twin(L)`` with ``w``, the node at ``v``'s place, replaced by the cancelled form; None without a future node."""
    found = future_node(leak.expr)
    if found is None:
        return None
    path, v = found
    twin = leak.expr.twin()
    return replace(leak, expr=_put(twin, path, Cancelled(kind, _get(twin, path), v)))


def mirror(leak: adv.Leak) -> adv.Leak | None:
    """§4.9: a leak whose root is a single Cmp with its operator flipped; same reads, margin and output. Else None."""
    e = leak.expr
    if not isinstance(e, adv.Cmp):
        return None
    return replace(leak, expr=replace(e, op="<" if e.op == ">" else ">"))


# --- The prediction of the cancelled controls: shares nothing with the detectors (§3.2) ----------------------


@dataclass(frozen=True)
class MaskedAt:
    """The prediction's node: ``w`` made missing wherever ``v`` is undefined."""

    w: Any
    v: Any
    binary = False

    def evaluate(self, view: Any) -> np.ndarray:
        w = np.asarray(self.w.evaluate(view), dtype=np.float64)
        v = np.asarray(self.v.evaluate(view), dtype=np.float64)
        return np.where(np.isnan(v), np.nan, w)

    def offsets(self) -> frozenset[int]:
        return self.w.offsets() | self.v.offsets()


def predicted_unit(leak: adv.Leak) -> adv.Leak | None:
    """``twin(L)`` with the node at ``w``'s place made missing wherever ``v`` is undefined (FP1 and FP2-min)."""
    found = future_node(leak.expr)
    if found is None:
        return None
    path, v = found
    twin = leak.expr.twin()
    return replace(leak, expr=_put(twin, path, MaskedAt(_get(twin, path), v)))


def predicted_flags(kind: str, unit: adv.Leak | None, bench: adv.Bench, convention: str) -> np.ndarray:
    """(cuts, runs) the prediction's flags on a windowed bench, by its own comparison of its own outputs.

    FP2-fmin: nothing is flagged. FP1, FP2-min: the masked twin's outputs, the original block against each run, a
    move above 1e-9 or a change of missingness at a scored compared row.
    """
    n_cuts, n_runs, scored = bench.n_cuts, len(bench.directions), bench.scored
    out = np.zeros((n_cuts, n_runs), dtype=bool)
    if kind == "FP2-fmin" or unit is None:
        return out
    for value in adv.outputs_under(unit, bench.view, convention).values():
        x = np.broadcast_to(np.asarray(value, dtype=np.float64), (n_cuts * (1 + n_runs), adv.COMPARED))
        base = x[:n_cuts]
        for j in range(n_runs):
            other = x[n_cuts * (1 + j) : n_cuts * (2 + j)]
            nan_a, nan_b = np.isnan(base), np.isnan(other)
            with np.errstate(invalid="ignore"):
                big = np.abs(base - other) > 1e-9
            out[:, j] |= (((big & ~nan_a & ~nan_b) | (nan_a ^ nan_b)) & scored).any(axis=1)
    return out


def control_can_flag(leak: adv.Leak, bench: adv.Bench) -> bool:
    """§3.2: ``v`` missing or undefined at some scored compared row in some run of the bench."""
    found = future_node(leak.expr)
    if found is None:
        return False
    blocks = 1 + len(bench.directions)
    v = np.broadcast_to(np.asarray(found[1].evaluate(bench.view), dtype=np.float64), (bench.n_cuts * blocks, adv.COMPARED))
    return bool((np.isnan(v) & np.tile(bench.scored, (blocks, 1))).any())


# --- Fonseca's classes, hand-written on our bars (§3.3) --------------------------------------------------------


@dataclass(frozen=True, eq=False)
class RowGate:
    """M1's gate: the inner leak where ``active[pair][row]`` is true, false elsewhere; the mask is fixed at construction."""

    inner: Any
    active: tuple[np.ndarray, ...]  # per pair (its position in the bars), over the series' rows
    label: str
    binary = True

    def _gate(self, view: Any) -> np.ndarray:
        row, pid = view.at("row", 0), view.at("pair_id", 0)
        gate = np.zeros(np.shape(row), dtype=bool)
        known = ~np.isnan(row) & ~np.isnan(pid)
        for p, mask in enumerate(self.active):
            here = known & (pid == p)
            gate[here] = mask[row[here].astype(np.int64)]
        return gate

    def evaluate(self, view: Any) -> np.ndarray:
        return np.asarray(self.inner.evaluate(view)) & self._gate(view)

    def evaluate_under(self, view: Any, convention: str) -> np.ndarray:
        x, gate = adv.evaluate_under(self.inner, view, convention), self._gate(view)
        if convention == "P":  # strict: a node with a missing operand is missing
            return np.where(np.isnan(x), np.nan, ((x == 1.0) & gate).astype(np.float64))
        return np.asarray(x, dtype=bool) & gate

    def offsets(self) -> frozenset[int]:
        return self.inner.offsets() | frozenset({0})

    def twin(self) -> RowGate:
        return RowGate(self.inner.twin(), self.active, self.label)

    def render(self) -> str:
        return f"({self.inner.render()}) outside the rows compared on {self.label}"


NEXT_CLOSE_UP = adv.Cmp(adv.At("close", 1), ">", 1.0, adv.At("close", 0))


def m1_active(b: Benches, schedule: str) -> tuple[np.ndarray, ...]:
    """False on rows t-10..t+1 of every cut of the schedule (every end for ``ends``), true elsewhere, per pair."""
    out = []
    for p in b.pairs:
        s = b.schedules[p]
        mask = np.ones(s.bars.height, dtype=bool)
        idx = [e for _, _, e in s.ends] if schedule == "ends" else [c.index for c in (s.h1 if schedule == "h1" else s.long)]
        for t in idx:
            mask[max(0, t - adv.FUTURE_REACH) : t + 2] = False
        out.append(mask)
    return tuple(out)


def class_m1(b: Benches, schedule: str) -> adv.Leak:
    return hand_leak(-1, RowGate(NEXT_CLOSE_UP, m1_active(b, schedule), schedule), family="fonseca-M1")


def class_m2(*, mirrored: bool = False) -> adv.Leak:
    return hand_leak(-2, adv.Cmp(adv.At("close", 1), "<" if mirrored else ">", 2.0, adv.At("close", 0)), family="fonseca-M2")


def class_m3() -> adv.Leak:
    """A future close re-stamped to row s: ``close[s+1]`` frozen from the original bars, read at offset 0."""
    return hand_leak(-3, adv.Cmp(adv.At("close_next_frozen", 0), ">", 1.0, adv.At("close", 0)), family="fonseca-M3")


FONSECA_FP_BASES: tuple[adv.Leak, ...] = (
    hand_leak(-4, adv.Cmp(adv.At("close", 1), ">", 1.0, adv.At("close", -1)), family="fonseca-FP"),
    hand_leak(-5, adv.LogRatio(adv.At("close", 1), adv.At("close", -1)), output="exp_return", family="fonseca-FP"),
)


def fi_m2_rule(bars: pl.DataFrame, t: int) -> bool:
    """§3.3, M2 under FI: flagged at a cut unless bar t + 1's high is below two thirds of bar t's close."""
    return not float(bars["high"][t + 1]) < 2.0 / 3.0 * float(bars["close"][t])


def check_classes(b: Benches) -> dict[str, Any]:
    """§3.3's registered verdicts on the run's bars: counts of disagreements (each must be 0), and FI on M2 by its rule.

    M1 is checked under G and M (under P a gated comparison with a missing operand is missing: reported, not asserted).
    TWO-RUN and SHUFFLE on M2 are "not predicted": reported only.
    """
    bad: dict[str, int] = {}
    reported: dict[str, Any] = {}
    for schedule in ("h1", "long", "ends"):
        v = cut_verdicts(judge_all(class_m1(b, schedule), b), b)
        keys = [k for k in v if k[1] == schedule and (k[0].split("/")[-1] in ("G", "M") or "/" not in k[0])]
        bad[f"M1 {schedule}"] = int(sum(int(v[k].any(axis=1).sum()) for k in keys))
        reported[f"M1 {schedule} under P"] = {k[0]: int(v[k].any(axis=1).sum()) for k in v if k[1] == schedule and k[0].endswith("/P")}
    for mirrored in (False, True):
        name = "M2 mirror" if mirrored else "M2"
        v = cut_verdicts(judge_all(class_m2(mirrored=mirrored), b), b)
        count = 0
        for schedule in ("h1", "long"):
            g, m = v[("TRUNC-0/G", schedule)].any(axis=1), v[("TRUNC-0/M", schedule)].any(axis=1)
            count += int(g.sum() if not mirrored else (~g).sum()) + int((~m).sum() if not mirrored else m.sum())
            if not mirrored:
                cuts = [b.cuts[i] for i in b.rows(schedule)]
                rule = np.array([fi_m2_rule(b.schedules[c["pair"]].bars, c["index"]) for c in cuts])
                count += int((v[("FI", schedule)].any(axis=1) != rule).sum())
            reported[f"{name} {schedule}"] = {k[0]: int(v[k].any(axis=1).sum()) for k in v if k[1] == schedule and k[0] in ("TWO-RUN", "SHUFFLE")}
        bad[name] = count
    v = cut_verdicts(judge_all(class_m3(), b), b)
    bad["M3"] = int(sum(int(f.any(axis=1).sum()) for f in v.values()))
    count = 0
    for base in FONSECA_FP_BASES:
        pred = predicted_unit(base)
        for kind in CANCELLED_KINDS:
            rows = judge_all(cancelled_control(base, kind), b)
            for key, bench, conv in _windowed(b):
                count += int((rows[key].cut_flags != predicted_flags(kind, pred, bench, conv)).sum())
    bad["FP on close"] = count
    return {"pass": not any(bad.values()), "disagreements": bad, "reported": reported}


def _windowed(b: Benches) -> list[tuple[str, adv.Bench, str]]:
    return [("FI", b.fi, "G"), ("TWO-RUN", b.two_run, "G"), ("SHUFFLE", b.shuffle, "G"),
            *((f"TRUNC/{c}", b.trunc, c) for c in CONVENTIONS)]  # fmt: skip


# --- One leak through everything: its verdicts, its twin, its mirror, its controls, and the assertions -------

CHECKS: tuple[str, ...] = (
    "fi-row-kernel-equals-fast-path",  # the gate between this module's kernel and the adversary's fast path
    "honest-twins-never-flagged",  # §3.1, both rules
    "cancelled-controls-follow-the-prediction",  # §3.2, H1's 16 cuts
    "p-flags-every-cut-but-the-exception",  # §2, P
    "p-binary-output-missing-where-the-or-mask-is-set",  # §2, P
    "truncation-catches-through-a-missing-read",  # §4.4
    "mirror-flagged-together",  # §4.9
    "retile-equals-windowed-trunc-0",  # §2.4
)
MIRROR_KEYS: tuple[str, ...] = ("FI", "TWO-RUN", "SHUFFLE", "TRUNC/G", "RETILE/G")


@dataclass
class LeakResult:
    id: int
    flags: dict[str, np.ndarray]  # "<detector>[/<convention>]@<schedule>" -> (cuts, runs)
    mirror: dict[str, np.ndarray] | None  # the same at H1's cuts and RETILE's ends, G, for a single-Cmp leak
    constant_h1: bool  # the same output, bit for bit, at every compared row of H1's cuts (twins.py's flag)
    constant_both: bool  # ... of both schedules (the adversary's flag)
    twin_constant_h1: bool
    split: dict[str, list[int]]  # "<key>@<schedule>" -> [flagged rows, of them through a missing read]
    violations: dict[str, int]
    counts: dict[str, int]


def _constant(r: Rows, cut_rows: np.ndarray, scored: np.ndarray) -> bool:
    for a in r.orig_bits:
        bits = np.ascontiguousarray(a[cut_rows][scored[cut_rows]]).view(np.uint64)
        if bits.size and not np.all(bits == bits[0]):
            return False
    return True


def _ties(leak: adv.Leak, key: str, b: Benches) -> np.ndarray:
    """(C, R, W): ``a = margin b`` in the original run or in the other one, for a single-Cmp leak."""
    e = leak.expr
    if key.startswith("RETILE"):
        rt = b.retile

        def both(view: Any) -> np.ndarray:
            shape = (view.q["row"].shape[0], view.n)
            a = np.broadcast_to(np.asarray(e.lhs.evaluate(view), dtype=np.float64), shape)
            m = np.broadcast_to(e.margin * np.asarray(e.rhs.evaluate(view), dtype=np.float64), shape)
            return a == m

        full, tiles = both(rt.full), both(rt.tiles)
        orig = full[rt.pair_index[:, None], rt.rows]
        run = tiles[:, rt.tiles.n - rt.width :]
        return (orig | run)[:, None, :]
    bench = {"FI": b.fi, "TWO-RUN": b.two_run, "SHUFFLE": b.shuffle, "TRUNC/G": b.trunc}[key]
    c, r = bench.n_cuts, len(bench.directions)
    shape = (c * (1 + r), adv.COMPARED)
    a = np.broadcast_to(np.asarray(e.lhs.evaluate(bench.view), dtype=np.float64), shape)
    m = np.broadcast_to(e.margin * np.asarray(e.rhs.evaluate(bench.view), dtype=np.float64), shape)
    tie = a == m
    return np.stack([tie[:c] | tie[c * (1 + j) : c * (2 + j)] for j in range(r)], axis=1)


def _flag_dict(rows: dict[str, Rows], b: Benches, *, h1_only: bool = False) -> dict[str, np.ndarray]:
    v = cut_verdicts(rows, b)
    return {f"{k}@{s}": f for (k, s), f in v.items() if not h1_only or s in ("h1", "ends")}


def process_leak(leak: adv.Leak, b: Benches) -> LeakResult:
    """Every detector on the leak, its honest twin, its mirror and its cancelled controls; every assertion counted."""
    viol: dict[str, int] = dict.fromkeys(CHECKS, 0)
    counts: dict[str, int] = {}

    def add(name: str, k: int = 1) -> None:
        counts[name] = counts.get(name, 0) + int(k)

    rows = judge_all(leak, b)
    h1 = b.rows("h1")
    fast = adv.evaluate_fast(leak, b.fi)
    viol["fi-row-kernel-equals-fast-path"] += int(not np.array_equal(rows["FI"].cut_flags, fast.caught))
    constant_h1 = _constant(rows["FI"], h1, b.fi.scored)

    # P: flagged at every cut unless the original output is already missing at every live row; binary roots' mask.
    for part in TRUNCATION:
        idx = b.trunc_parts[part]
        r = rows["TRUNC/P"]
        live = r.removed_read[idx, 0] & b.trunc.scored[idx]
        exception = ~(live & ~r.orig_missing[idx]).any(axis=1)
        flagged = r.cut_flags[idx, 0]
        if part == "TRUNC-0":
            viol["p-flags-every-cut-but-the-exception"] += int((~exception & ~flagged).sum())
        add(f"p-not-flagged-outside-the-exception:{part}", int((~exception & ~flagged).sum()))
        add(f"p-exception-cuts:{part}", int(exception.sum()))
        add(f"p-flagged-inside-the-exception:{part}", int((exception & flagged).sum()))
    if leak.expr.binary:
        r = rows["TRUNC/P"]
        viol["p-binary-output-missing-where-the-or-mask-is-set"] += int((r.output_missing != r.or_mask).sum())

    # §4.4 for every truncation detector; the split itself for every detector.
    split: dict[str, list[int]] = {}
    for key, r in rows.items():
        through = r.flags & r.missing_read
        if key.startswith(("TRUNC/", "RETILE/")):
            viol["truncation-catches-through-a-missing-read"] += int((r.flags & ~r.missing_read).sum())
        if key.startswith("TRUNC/"):
            conv = key.split("/")[1]
            for part in ("TRUNC-0", "TRUNC-1"):
                idx = b.trunc_parts[part][h1]
                split[f"{part}/{conv}@h1"] = [int(r.flags[idx].sum()), int(through[idx].sum())]
        elif key.startswith("RETILE/"):
            split[f"{key}@ends"] = [int(r.flags.sum()), int(through.sum())]
        elif key == "SHUFFLE":
            split["SHUFFLE@h1"] = [int(r.flags.sum()), int(through.sum())]
        else:
            split[f"{key}@h1"] = [int(r.flags[h1].sum()), int(through[h1].sum())]
            if key == "TWO-RUN":
                for s_ in sorted({s for s, _ in b.two_run_runs}):
                    cols = [j for j, (s, _) in enumerate(b.two_run_runs) if s == s_]
                    split[f"TWO-RUN s{s_:g}@h1"] = [int(r.flags[h1][:, cols].sum()), int(through[h1][:, cols].sum())]

    # §2.4: RETILE's flags equal the windowed TRUNC-0 run at the same ends, row for row.
    ends = b.trunc_parts["ENDS"]
    for conv in CONVENTIONS:
        rt, en = rows[f"RETILE/{conv}"].flags[:, 0], rows[f"TRUNC/{conv}"].flags[ends, 0]
        viol["retile-equals-windowed-trunc-0"] += int((rt[:, -adv.COMPARED :] != en).any(axis=1).sum() + rt[:, : -adv.COMPARED].any(axis=1).sum())

    # §3.1: the honest twin, every detector, convention, schedule, sigma and run, under both rules.
    twin = leak.honest_twin()
    trows = judge_all(twin, b)
    for key, r in trows.items():
        moved = int(r.flags.any() or r.bits.any())
        viol["honest-twins-never-flagged"] += moved
        add(f"twin-flagged:{key}", moved)
    twin_constant = _constant(trows["FI"], h1, b.fi.scored)

    # §4.9: the mirror of a single-Cmp leak.
    mirror_flags = None
    mir = mirror(leak)
    if mir is not None:
        mrows = {"FI": judge_window(mir, b.fi), "TWO-RUN": judge_window(mir, b.two_run), "SHUFFLE": judge_window(mir, b.shuffle),
                 "TRUNC/G": judge_window(mir, b.trunc, "G"), "RETILE/G": judge_retile(mir, b.retile, "G")}  # fmt: skip
        for key in MIRROR_KEYS:
            region = rows[key].all_defined & ~_ties(leak, key, b)
            viol["mirror-flagged-together"] += int(((rows[key].flags != mrows[key].flags) & region).sum())
        mirror_flags = _flag_dict(mrows, b, h1_only=True)

    # §3.2: the cancelled controls, against the prediction, at H1's 16 cuts (and counted elsewhere).
    pred = predicted_unit(leak)
    if pred is not None:
        windowed = _windowed(b)
        expected = {key: predicted_flags("FP1", pred, bench, conv) for key, bench, conv in windowed}
        can_flag = {key: control_can_flag(leak, bench) for key, bench, _ in windowed if not key.endswith(("/M", "/P"))}
        trunc_h1 = np.concatenate([b.trunc_parts["TRUNC-0"][h1], b.trunc_parts["TRUNC-1"][h1]])
        h1_rows_of = {key: trunc_h1 if bench is b.trunc else np.arange(bench.n_cuts) if bench is b.shuffle else h1 for key, bench, _ in windowed}
        for kind in CANCELLED_KINDS:
            control = cancelled_control(leak, kind)
            add("controls-built")
            for key, flag in can_flag.items():
                add(f"controls-can-flag:{key.split('/')[0]}", int(flag))
            for key, bench, conv in windowed:
                got = judge_window(control, bench, conv).cut_flags
                exp = np.zeros_like(got) if kind == "FP2-fmin" else expected[key]
                at_h1 = h1_rows_of[key]
                wrong_h1 = int((got[at_h1] != exp[at_h1]).sum())
                viol["cancelled-controls-follow-the-prediction"] += wrong_h1
                add(f"control-disagreements-h1:{kind}:{key}", wrong_h1)
                add(f"control-disagreements-elsewhere:{kind}:{key}", int((got != exp).sum()) - wrong_h1)
                add(f"control-flags-h1:{kind}:{key}", int(got[at_h1].any(axis=1).sum()))
    return LeakResult(leak.id, _flag_dict(rows, b), mirror_flags, constant_h1, bool(fast.constant), twin_constant, split, viol, counts)


# --- The population, across workers -----------------------------------------------------------------------

_WORKER: dict[str, Any] = {}


def _spawn() -> Any:
    """Fresh worker processes on every platform. In WSL2 (wave 3, outside pytest) a ``fork`` pool of this module hung
    with its CPU idle while the same pool under ``spawn`` gave the single-process results; cause not isolated
    (consistent with forking a process that holds a thread pool)."""
    import multiprocessing

    return multiprocessing.get_context("spawn")


def _init_worker(bars_by_pair: dict[str, pl.DataFrame], cfg: DetectorConfig, table_path: str | None) -> None:
    _WORKER["benches"] = build_benches(bars_by_pair, cfg)
    _WORKER["cfg"] = cfg
    _WORKER["table"] = table_path


def _draw(cfg: DetectorConfig, table_path: str | None, ids: Sequence[int]) -> list[adv.Leak]:
    place = adv.placement_for(cfg.placement, table_path)
    return [adv._draw_leak(cfg.population_seed, i, place) for i in ids]


def _work(ids: Sequence[int]) -> list[LeakResult]:
    b, cfg = _WORKER["benches"], _WORKER["cfg"]
    return [process_leak(leak, b) for leak in _draw(cfg, _WORKER["table"], ids)]


def evaluate_population(bars_by_pair: dict[str, pl.DataFrame], cfg: DetectorConfig, b: Benches, table_path: str | None,
                        *, workers: int = 1) -> list[LeakResult]:  # fmt: skip
    """Every leak of the population through :func:`process_leak`, in order; the same results for any worker count.

    Processes, each building its own benches from the bars (deterministic): the benches are never sent to a worker.
    """
    ids = list(range(cfg.n))
    if workers <= 1 or cfg.n < 2:
        return [process_leak(leak, b) for leak in _draw(cfg, table_path, ids)]
    from concurrent.futures import ProcessPoolExecutor

    chunk = max(1, math.ceil(cfg.n / (6 * workers)))
    parts = [ids[s : s + chunk] for s in range(0, cfg.n, chunk)]
    with ProcessPoolExecutor(max_workers=workers, mp_context=_spawn(), initializer=_init_worker, initargs=(bars_by_pair, cfg, table_path)) as pool:
        return [r for part in pool.map(_work, parts) for r in part]


# --- The equivalence gates (§4, "Equivalence gates"): H1's own path on 50 leaks -----------------------------


def _h1_path_task(pair: str, bars: pl.DataFrame, cuts: list[inv.Cut], cfg: DetectorConfig, leaks: list[adv.Leak]) -> list[tuple[str, int, dict[str, Any]]]:
    """TRUNC-0 through ``LeakModel`` on really truncated bars; TWO-RUN (sigma 0.1, its first runs) and SHUFFLE through
    ``inv.outputs``; each compared with the original run by ``inv.compare`` at the cut, as H1 compares."""
    h1 = cfg.adversary.h1
    runs = [(cfg.sigmas[0], 1), (cfg.sigmas[0], 2)]  # the primary arm: sigma 0.1, two runs
    out = []
    for leak in leaks:
        spec = adv.leak_spec(leak)
        original = inv.outputs(spec, bars, h1)

        def caught(other: pl.DataFrame, cut: inv.Cut, spec: inv.ModelSpec = spec, original: pl.DataFrame = original) -> bool:
            return inv.compare(original, inv.outputs(spec, other, h1, before=cut.known_at), cut.known_at)["caught"] > 0

        rec: dict[str, Any] = {"TRUNC-0": [], "TWO-RUN": [], "SHUFFLE": []}
        for k, cut in enumerate(cuts):
            rec["TRUNC-0"].append(caught(bars.head(cut.index + 1), cut))
            rec["TWO-RUN"].append([caught(two_run_bars(bars, cut.index, s, two_run_z(cfg.two_run_seed, pair, SCHEDULE_ID["h1"], k, r))[0], cut)
                                   for s, r in runs])  # fmt: skip
            rec["SHUFFLE"].append([caught(tw.shuffle_after(bars, cut.index, tw.twin_rng(cfg.shuffle_seed, pair, k, j)), cut) for j in range(cfg.shuffle_k)])
        out.append((pair, leak.id, rec))
    return out


def run_gates(leaks: Sequence[adv.Leak], bars_by_pair: dict[str, pl.DataFrame], b: Benches, cfg: DetectorConfig, *,
              workers: int = 1, cuts_per_pair: int | None = None) -> dict[str, Any]:  # fmt: skip
    """FI's fast path against H1's own path (the adversary's check); TRUNC-0, TWO-RUN and SHUFFLE through H1's path.

    ``cuts_per_pair`` limits the H1-path gates to the first cuts of each pair (tests only).
    """
    fi = adv.check_equivalence(list(leaks), b.fi, bars_by_pair, cfg.adversary, workers=workers)
    a = cfg.adversary
    weak = [leak.attenuated(e) for leak in list(leaks)[: a.attenuated_equivalence_leaks] for e in a.attenuated_equivalence_eps]
    if weak:  # as in iteration 3: the first leaks attenuated, the 1e-9 rule near its edge in both paths
        at = adv.check_equivalence(weak, b.fi, bars_by_pair, a, workers=workers, twins=False)
        fi = {**fi, "agree": bool(fi["agree"] and at["agree"]), "mismatches": [*fi["mismatches"], *at["mismatches"]],
              "units_compared": fi["units_compared"] + at["units_compared"]}  # fmt: skip
    jobs = []
    for pair, bars in bars_by_pair.items():
        cuts = b.schedules[pair].h1[: cuts_per_pair or None]
        for leak in leaks:
            jobs.append((pair, bars, cuts, cfg, [leak]))
    if workers > 1:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=workers, mp_context=_spawn()) as pool:
            done = [r for f in [pool.submit(_h1_path_task, *job) for job in jobs] for r in f.result()]
    else:
        done = [r for job in jobs for r in _h1_path_task(*job)]
    primary = [j for j, (s, r) in enumerate(b.two_run_runs) if s == cfg.sigmas[0] and r <= 2]
    by_id = {leak.id: leak for leak in leaks}
    mismatches = {"TRUNC-0": 0, "TWO-RUN": 0, "SHUFFLE": 0}
    compared = 0
    for pair, leak_id, rec in done:
        leak = by_id[leak_id]
        rows = [i for i, c in enumerate(b.cuts) if c["pair"] == pair and c["schedule"] == "h1"][: len(rec["TRUNC-0"])]
        tr = judge_window(leak, b.trunc, "G").cut_flags[b.trunc_parts["TRUNC-0"][rows], 0]
        two = judge_window(leak, b.two_run).cut_flags[rows][:, primary]
        sh_rows = [i for i, c in enumerate(b.shuffle.cuts) if c["pair"] == pair][: len(rec["SHUFFLE"])]
        sh = judge_window(leak, b.shuffle).cut_flags[sh_rows]
        mismatches["TRUNC-0"] += int((np.array(rec["TRUNC-0"]) != tr).sum())
        mismatches["TWO-RUN"] += int((np.array(rec["TWO-RUN"]) != two).sum())
        mismatches["SHUFFLE"] += int((np.array(rec["SHUFFLE"]) != sh).sum())
        compared += 1
    return {
        "leaks": len(leaks),
        "fi": {"pass": bool(fi["agree"]), "mismatches": len(fi["mismatches"]), "twin_violations": len(fi["twin_violations"]), "units": fi["units_compared"]},
        "h1_path": {"pass": not any(mismatches.values()), "mismatches": mismatches, "units": compared, "cuts_per_pair": cuts_per_pair},
        "pass": bool(fi["agree"] and not any(mismatches.values())),
    }


# --- The metrics (§4) and H15 (§5) -------------------------------------------------------------------------------

def _stack_flags(results: Sequence[LeakResult], key: str) -> np.ndarray:
    return np.stack([r.flags[key] for r in results])


def primary_verdicts(results: Sequence[LeakResult], b: Benches, cfg: DetectorConfig) -> dict[str, np.ndarray]:
    """Every registered variant as (leaks, cuts) any-run verdicts; H1's cuts unless the name says ``@long`` or ``@ends``."""
    runs = b.two_run_runs

    def two(sigma: float, k: int) -> list[int]:
        return [j for j, (s, r) in enumerate(runs) if s == sigma and r <= k]

    out: dict[str, np.ndarray] = {}
    for sched in ("h1", "long"):
        suffix = "" if sched == "h1" else "@long"
        fi = _stack_flags(results, f"FI@{sched}")
        out[f"FI{suffix}"] = fi.any(axis=2)
        out[f"FI x3{suffix}"], out[f"FI /3{suffix}"] = fi[:, :, 0], fi[:, :, 1]
        for part in ("TRUNC-0", "TRUNC-1"):
            for conv in CONVENTIONS:
                out[f"{part}/{conv}{suffix}"] = _stack_flags(results, f"{part}/{conv}@{sched}")[:, :, 0]
        tr = _stack_flags(results, f"TWO-RUN@{sched}")
        for sigma in cfg.sigmas:
            for k in (1, 2, cfg.two_run_runs):
                out[f"TWO-RUN s{sigma:g} r{k}{suffix}"] = tr[:, :, two(sigma, k)].any(axis=2)
    sh = _stack_flags(results, "SHUFFLE@h1")
    for k in (1, 2, cfg.shuffle_k):
        out[f"SHUFFLE k{k}"] = sh[:, :, :k].any(axis=2)
    for conv in CONVENTIONS:
        out[f"RETILE/{conv}@ends"] = _stack_flags(results, f"RETILE/{conv}@ends")[:, :, 0]
        out[f"ENDS/{conv}@ends"] = _stack_flags(results, f"ENDS/{conv}@ends")[:, :, 0]
    out["TRUNC-0"], out["TWO-RUN"], out["SHUFFLE"] = out["TRUNC-0/G"], out[f"TWO-RUN s{cfg.sigmas[0]:g} r2"], out[f"SHUFFLE k{cfg.shuffle_k}"]
    return out


RUNS_PER_CUT = {"FI": 2, "FI x3": 1, "FI /3": 1, "TRUNC-0": 1, "TRUNC-1": 1, "RETILE": 1}


def _runs_per_cut(name: str) -> int:
    base = name.split("@")[0]
    if base in RUNS_PER_CUT:
        return RUNS_PER_CUT[base]
    base = base.split("/")[0]
    if base == "TWO-RUN":
        return 2  # the primary arm: sigma 0.1, two runs
    if base == "SHUFFLE":
        return tw.K_TWINS
    if base.startswith("TWO-RUN"):
        return int(base.split(" r")[1])
    if base.startswith("SHUFFLE k"):
        return int(base.split("k")[1])
    return RUNS_PER_CUT.get(base, RUNS_PER_CUT.get(base.split(" ")[0], 1))


def _h1_order(b: Benches) -> list[int]:
    """§4.3: H1's 16 cuts by date, then by pair (in the bars' pair order: BTCUSDT before ETHUSDT)."""
    cuts = [b.cuts[i] for i in b.rows("h1")]
    return sorted(range(len(cuts)), key=lambda j: (cuts[j]["open_time"], b.pairs.index(cuts[j]["pair"])))


def _strata(leaks: Sequence[adv.Leak]) -> dict[str, np.ndarray]:
    pos = np.array([leak.tag["position"] for leak in leaks])
    return {"inside": pos == "inside", "outside": pos == "outside", "other": (pos != "inside") & (pos != "outside")}


def _pair(x: np.ndarray, y: np.ndarray, rate_x: np.ndarray | None = None, rate_y: np.ndarray | None = None) -> dict[str, Any]:
    t = ds.paired_table(x, y)
    out = {"table": t, "b": t["b"], "c": t["c"], "newcombe": ds.newcombe_paired(t["a"], t["b"], t["c"], t["d"]),
           "mcnemar_exact_p": ds.mcnemar_exact(t["b"], t["c"])}  # fmt: skip
    if rate_x is not None and rate_y is not None:
        out["per_cut_rate_difference"] = ds.paired_difference(rate_x, rate_y)
    return out


def summarize(leaks: Sequence[adv.Leak], results: Sequence[LeakResult], b: Benches, cfg: DetectorConfig) -> dict[str, Any]:
    """Every registered metric of §4 and H15's labels (§5), from the verdicts."""
    v = primary_verdicts(results, b, cfg)
    n = len(leaks)
    anyc = {k: x.any(axis=1) for k, x in v.items()}
    rate = {k: x.mean(axis=1) for k, x in v.items()}
    family = np.array([leak.family for leak in leaks])
    designed = np.array([leak.tag["designed"] for leak in leaks])
    constant_h1 = np.array([r.constant_h1 for r in results])
    constant_both = np.array([r.constant_both for r in results])
    invariant = np.array([_no_threshold(cfg.population_seed, leak.id) for leak in leaks], dtype=bool)
    denominators = {"all": np.ones(n, dtype=bool), "not-constant": ~constant_h1, "designed-no": designed == "no"}
    strata = _strata(leaks)
    names = [k for k in v if "@" not in k or k.endswith("@ends")]

    def shares(mask: np.ndarray) -> dict[str, Any]:
        return {k: ds.share(int(anyc[k][mask].sum()), int(mask.sum())) for k in names}

    detectors = {}
    for k in names:
        detectors[k] = {
            "runs_per_cut": _runs_per_cut(k),
            "cuts": int(v[k].shape[1]),
            "any_cut": {d: ds.share(int(anyc[k][m].sum()), int(m.sum())) for d, m in denominators.items()},
            "mean_per_cut_rate": {d: ds.mean_rate(rate[k][m]) for d, m in denominators.items()},
            "by_family": {f: ds.share(int(anyc[k][family == f].sum()), int((family == f).sum())) for f in adv.FAMILIES if (family == f).any()},
            "by_position": {s: ds.share(int(anyc[k][m].sum()), int(m.sum())) for s, m in strata.items()},
        }
    long_names = [k for k in v if k.endswith("@long")]
    long_ = {k: {"runs_per_cut": _runs_per_cut(k), "cuts": int(v[k].shape[1]), "any_cut": ds.share(int(anyc[k].sum()), n),
                 "mean_per_cut_rate": ds.mean_rate(rate[k])} for k in long_names}  # fmt: skip

    order = _h1_order(b)
    curves = {k: ds.first_m_curve(v[k], order) for k in ("FI", "TRUNC-0", "TWO-RUN", "SHUFFLE", "TRUNC-1/G")}

    # §4.4: the read split, row level, at H1's cuts (RETILE at its ends).
    split: dict[str, list[int]] = {}
    for r in results:
        for k, (flagged, through) in r.split.items():
            s = split.setdefault(k, [0, 0])
            s[0] += flagged
            s[1] += through
    read_split = {k: {"flagged_rows": f, "through_a_missing_read": ds.share(t, f), "through_a_changed_value": ds.share(f - t, f)} for k, (f, t) in sorted(split.items())}

    # §4.5: conventions.
    conv_shares = {c: anyc[f"TRUNC-0/{c}"].mean() for c in CONVENTIONS}
    conventions = {
        "TRUNC-0": {c: ds.share(int(anyc[f"TRUNC-0/{c}"].sum()), n) for c in CONVENTIONS},
        "TRUNC-1": {c: ds.share(int(anyc[f"TRUNC-1/{c}"].sum()), n) for c in CONVENTIONS},
        "RETILE": {c: ds.share(int(anyc[f"RETILE/{c}@ends"].sum()), n) for c in CONVENTIONS},
        "sentence": {"X": float(min(conv_shares.values())), "Y": float(max(conv_shares.values())),
                     "G_to_M": sorted([float(conv_shares["G"]), float(conv_shares["M"])])},  # fmt: skip
    }

    # §4.7, §4.8: pairs.
    pairs = {}
    for i, x in enumerate(PRIMARY):
        for y in PRIMARY[i + 1 :]:
            pairs[f"{x} - {y}"] = _pair(anyc[x], anyc[y], rate[x], rate[y])
    pairs["TRUNC-1/G - TRUNC-0 (one-bar date shift)"] = _pair(anyc["TRUNC-1/G"], anyc["TRUNC-0"], rate["TRUNC-1/G"], rate["TRUNC-0"])
    s1, sk = f"TWO-RUN s{cfg.sigmas[0]:g} r1", f"TWO-RUN s{cfg.sigmas[0]:g} r2"
    equal = {"FI x3 - TRUNC-0": _pair(anyc["FI x3"], anyc["TRUNC-0"], rate["FI x3"], rate["TRUNC-0"]),
             f"{s1} - TRUNC-0": _pair(anyc[s1], anyc["TRUNC-0"], rate[s1], rate["TRUNC-0"]),
             "SHUFFLE k1 - TRUNC-0": _pair(anyc["SHUFFLE k1"], anyc["TRUNC-0"], rate["SHUFFLE k1"], rate["TRUNC-0"]),
             f"FI - {sk}": _pair(anyc["FI"], anyc[sk], rate["FI"], rate[sk]),
             "FI - SHUFFLE k2": _pair(anyc["FI"], anyc["SHUFFLE k2"], rate["FI"], rate["SHUFFLE k2"])}  # fmt: skip

    # §4.9: mirror asymmetry, H1's cuts (RETILE at its ends), G.
    with_mirror = [i for i, r in enumerate(results) if r.mirror is not None]
    mirror_keys = {"FI": ("FI@h1", None), "TRUNC-0": ("TRUNC-0/G@h1", None), "TRUNC-1": ("TRUNC-1/G@h1", None), "RETILE": ("RETILE/G@ends", None),
                   "TWO-RUN": ("TWO-RUN@h1", [j for j, (s, r) in enumerate(b.two_run_runs) if s == cfg.sigmas[0] and r <= 2]),
                   "SHUFFLE": ("SHUFFLE@h1", None)}  # fmt: skip
    mirrors = {}
    for name, (key, cols) in mirror_keys.items():
        if not with_mirror:
            break
        own = np.stack([results[i].flags[key] for i in with_mirror])
        mir = np.stack([results[i].mirror[key] for i in with_mirror])  # type: ignore[index]
        if cols is not None:
            own, mir = own[:, :, cols], mir[:, :, cols]
        oc, mc = own.any(axis=2), mir.any(axis=2)
        differ = oc != mc
        mirrors[name] = {"leaks": len(with_mirror), "any_cut": ds.share(int((oc.any(axis=1) != mc.any(axis=1)).sum()), len(with_mirror)),
                         "per_cut": [ds.share(int(differ[:, j].sum()), len(with_mirror)) for j in range(differ.shape[1])]}  # fmt: skip

    # §4.10, §4.11: the union and its misses.
    union = anyc["FI"] | anyc["TRUNC-0"] | anyc["TWO-RUN"] | anyc["SHUFFLE"]
    union_rows = {
        "primary": union,
        "with TRUNC-1": union | anyc["TRUNC-1/G"],
        "with RETILE": union | anyc["RETILE/G@ends"],
        f"with sigma {cfg.sigmas[-1]:g}": union | anyc[f"TWO-RUN s{cfg.sigmas[-1]:g} r2"],
        "over both schedules": union | anyc["FI@long"] | anyc["TRUNC-0/G@long"] | anyc["TRUNC-1/G@long"] | anyc[f"TWO-RUN s{cfg.sigmas[0]:g} r2@long"] | anyc["TRUNC-1/G"],
        "under convention M": anyc["FI"] | anyc["TRUNC-0/M"] | anyc["TWO-RUN"] | anyc["SHUFFLE"],
    }
    missed_by = {d: ds.share(int((union & ~anyc[d]).sum()), int(union.sum())) for d in PRIMARY}
    misses = ~union
    secondary = {"TRUNC-1": anyc["TRUNC-1/G"], "RETILE": anyc["RETILE/G@ends"], f"sigma {cfg.sigmas[-1]:g}": anyc[f"TWO-RUN s{cfg.sigmas[-1]:g} r2"],
                 "long schedule": union_rows["over both schedules"] & ~union, "convention M": anyc["TRUNC-0/M"]}  # fmt: skip
    union_misses = {
        "count": int(misses.sum()),
        "constant_h1_cuts": int((misses & constant_h1).sum()),
        "constant_both_schedules": int((misses & constant_both).sum()),
        "caught_by_a_secondary_arm": {k: int((misses & m).sum()) for k, m in secondary.items()},
        "by_family": {f: int((misses & (family == f)).sum()) for f in adv.FAMILIES},
    }

    # §4.12 to §4.14.
    descriptive = {"distinct_expressions": len({repr(leak.expr) for leak in leaks}), "constant_h1_cuts": ds.share(int(constant_h1.sum()), n),
                   "constant_both_schedules": ds.share(int(constant_both.sum()), n)}  # fmt: skip
    subset = {}
    for name, m in (("invariant", invariant), ("complement", ~invariant)):
        t = ds.paired_table(anyc["TRUNC-0"][m], anyc["FI"][m])
        subset[name] = {"leaks": int(m.sum()), "FI_any_cut": ds.share(int(anyc["FI"][m].sum()), int(m.sum())),
                        "TRUNC-0_minus_FI": ds.newcombe_paired(t["a"], t["b"], t["c"], t["d"])}  # fmt: skip

    # §5: H15.
    def diff(mask: np.ndarray, trunc_key: str) -> dict[str, Any]:
        t = ds.paired_table(anyc[trunc_key][mask], anyc["FI"][mask])
        return ds.newcombe_paired(t["a"], t["b"], t["c"], t["d"])

    deciding = diff(denominators["all"], "TRUNC-0")
    h15 = ds.h15(deciding, {"convention M": diff(denominators["all"], "TRUNC-0/M"), "not-constant denominator": diff(~constant_h1, "TRUNC-0")})
    h15["deciding_cell"] = {**deciding, "table": ds.paired_table(anyc["TRUNC-0"], anyc["FI"]), "mcnemar_exact_p": pairs["FI - TRUNC-0"]["mcnemar_exact_p"]}
    h15["beside"] = {"mean_per_cut_rate_difference": ds.paired_difference(rate["TRUNC-0"], rate["FI"]),
                     "convention P": diff(denominators["all"], "TRUNC-0/P")}  # fmt: skip

    boot = None
    if cfg.bootstrap_seed is not None:
        long_rows = b.rows("long")
        dates = np.array([b.cuts[i]["open_time"][:10] for i in long_rows])
        boot = ds.cut_date_bootstrap(v["TRUNC-0/G@long"], v["FI@long"], dates, seed=cfg.bootstrap_seed, subsets=cfg.bootstrap_subsets, size=cfg.bootstrap_dates)

    per_leak = [{"id": leak.id, "family": leak.family, "invariant": bool(invariant[i]), "constant_h1_cuts": bool(constant_h1[i]),
                 **{d: "".join("X" if x else "." for x in v[d][i]) for d in PRIMARY}} for i, leak in enumerate(leaks)]  # fmt: skip
    return {"detectors": detectors, "long_schedule": long_, "first_m_cuts": curves, "read_split": read_split, "conventions": conventions,
            "pairs": pairs, "equal_run_counts": equal, "mirror_asymmetry": mirrors, "union": {k: ds.share(int(m.sum()), n) for k, m in union_rows.items()},
            "missed_by_detector_among_union": missed_by, "union_misses": union_misses, "descriptive": descriptive, "placement_invariant_subset": subset,
            "h15": h15, "cut_date_bootstrap": boot, "replications": {"FI any cut": detectors["FI"]["any_cut"]["all"], "SHUFFLE any cut": detectors["SHUFFLE"]["any_cut"]["all"]},
            "h1_cut_order": [b.cuts[b.rows("h1")[j]]["open_time"][:10] + " " + b.cuts[b.rows("h1")[j]]["pair"] for j in order], "leaks": per_leak}  # fmt: skip


def _no_threshold(seed: int, i: int) -> bool:
    """§1.6: leak ``i`` is drawn with no ``_threshold`` call (the same under both placements)."""
    place = adv.Placement(adv.H1_BANDS)
    adv._draw_leak(seed, i, place)
    return place.calls == 0


# --- The run and its stop rule (§7.4) --------------------------------------------------------------------------


def config_json(cfg: DetectorConfig) -> dict[str, Any]:
    a = adv._config_json(cfg.adversary)
    return {
        "population_seed": cfg.population_seed, "two_run_seed": cfg.two_run_seed, "placement": cfg.placement, "n": cfg.n,
        "bootstrap_seed": cfg.bootstrap_seed, "bootstrap_subsets": cfg.bootstrap_subsets, "bootstrap_dates": cfg.bootstrap_dates,
        "sigmas": list(cfg.sigmas), "two_run_runs": cfg.two_run_runs, "shuffle_k": cfg.shuffle_k, "shuffle_seed": cfg.shuffle_seed,
        "taus": list(cfg.taus), "h1": a["h1"], "long_cuts": a["long_cuts"], "long_cut_seed": a["long_cut_seed"],
        "long_perturbation_seed": a["long_perturbation_seed"], "equivalence_leaks": a["equivalence_leaks"],
        "equivalence_seed": a["equivalence_seed"], "caught_above": a["caught_above"], "future_reach": a["future_reach"],
        "past_reach": a["past_reach"], "conventions": list(CONVENTIONS), "extra_quantities": list(EXTRA_QUANTITIES),
    }  # fmt: skip


def _check(violations: int, **counts: Any) -> dict[str, Any]:
    return {"pass": violations == 0, "violations": int(violations), **counts}


def assertions_of(results: Sequence[LeakResult], b: Benches, classes: dict[str, Any]) -> dict[str, Any]:
    """Every assertion of §3.4 as pass or fail and counts: no rate, no per-leak verdict."""
    tot = dict.fromkeys(CHECKS, 0)
    counts: dict[str, int] = {}
    for r in results:
        for k, x in r.violations.items():
            tot[k] += x
        for k, x in r.counts.items():
            counts[k] = counts.get(k, 0) + x
    twin_keys = sorted(k for k in counts if k.startswith("twin-flagged:"))
    control_keys = sorted(k for k in counts if k.startswith("control-disagreements-h1:"))
    stats = b.two_run_stats
    return {
        "§2.3 TRUNC-1's row t + 1 exists and is scored at every cut": _check(0, cuts_checked=2 * len(b.cuts),
                                                                             cuts_where_t_plus_1_is_the_last_row=b.last_row_cuts),
        "§2.4 RETILE equals windowed TRUNC-0 at the ends": _check(tot["retile-equals-windowed-trunc-0"], ends=len(b.retile.ends)),
        "§2.5 TWO-RUN's repair checks": _check(0, perturbed_bars_checked={s: st["bars"] for s, st in stats.items()}),
        "§2 P: TRUNC-0 flags every cut but the exception": _check(tot["p-flags-every-cut-but-the-exception"]),
        "§2 P: binary roots missing exactly where the OR mask is set": _check(tot["p-binary-output-missing-where-the-or-mask-is-set"]),
        "§3.1 honest twins never flagged": _check(tot["honest-twins-never-flagged"], by_detector={k.split(":", 1)[1]: counts[k] for k in twin_keys}),
        "§3.2 cancelled controls follow the prediction (H1's cuts)": _check(tot["cancelled-controls-follow-the-prediction"],
                                                                             controls_built=counts.get("controls-built", 0),
                                                                             by_control={k.split(":", 1)[1]: counts[k] for k in control_keys}),
        "§3.3 Fonseca's classes give their registered verdicts": _check(sum(classes["disagreements"].values()), by_class=classes["disagreements"]),
        "§4.4 truncation catches go through a missing read": _check(tot["truncation-catches-through-a-missing-read"]),
        "§4.9 a single-Cmp leak and its mirror are flagged together": _check(tot["mirror-flagged-together"]),
        "row kernel equals the adversary's fast path (FI)": _check(tot["fi-row-kernel-equals-fast-path"]),
    }  # fmt: skip


def reported_counts(results: Sequence[LeakResult], b: Benches, classes: dict[str, Any]) -> dict[str, Any]:
    """What is reported beside the metrics (written only when every assertion passes)."""
    counts: dict[str, int] = {}
    for r in results:
        for k, x in r.counts.items():
            counts[k] = counts.get(k, 0) + x
    n = len(results)
    return {
        "controls": {"built": counts.get("controls-built", 0),
                     "can_be_flagged": {k.split(":", 1)[1]: x for k, x in sorted(counts.items()) if k.startswith("controls-can-flag:")},
                     "flagged_at_h1_cuts": {k.split(":", 1)[1]: x for k, x in sorted(counts.items()) if k.startswith("control-flags-h1:")},
                     "disagreements_elsewhere": {k.split(":", 1)[1]: x for k, x in sorted(counts.items()) if k.startswith("control-disagreements-elsewhere:") and x}},
        "honest_twins": {"evaluated": n, "constant_at_h1_compared_rows": ds.share(sum(r.twin_constant_h1 for r in results), n)},
        "p_assertion": {k: x for k, x in sorted(counts.items()) if k.startswith("p-")},
        "two_run_repair": b.two_run_stats,
        "classes": classes["reported"],
    }  # fmt: skip


def run(bars_by_pair: dict[str, pl.DataFrame], cfg: DetectorConfig, *, table_path: str | None = None, workers: int = 1,
        prov: dict[str, Any] | None = None, gate_cuts_per_pair: int | None = None) -> dict[str, Any]:  # fmt: skip
    """The benchmark on the given bars. Assertions and gates first; the metrics only if every one passes."""
    import time

    timings: dict[str, float] = {}
    result: dict[str, Any] = {"config": config_json(cfg), "placement": cfg.placement,
                              "table_sha256": adv.QUANTILE_TABLE_SHA256 if cfg.placement == adv.QUANTILE else None}  # fmt: skip
    if prov is not None:
        result["provenance"] = prov
    t0 = time.perf_counter()
    try:
        b = build_benches(bars_by_pair, cfg)
    except AssertionError as e:
        result["assertions"] = {"benches": {"pass": False, "violations": 1, "error": str(e)}}
        result["stopped"] = "an assertion failed while the benches were built: no rate is written"
        result["_timings"] = {"benches": time.perf_counter() - t0}
        return result
    timings["benches"] = time.perf_counter() - t0
    t1 = time.perf_counter()
    leaks = _draw(cfg, table_path, range(cfg.n))
    results = evaluate_population(bars_by_pair, cfg, b, table_path, workers=workers)
    timings["population"] = time.perf_counter() - t1
    t2 = time.perf_counter()
    classes = check_classes(b)
    ids = adv.equivalence_ids(cfg.n, cfg.adversary)
    gates = run_gates([leaks[i] for i in ids], bars_by_pair, b, cfg, workers=workers, cuts_per_pair=gate_cuts_per_pair)
    timings["checks"] = time.perf_counter() - t2
    result["assertions"] = assertions_of(results, b, classes)
    result["gates"] = gates
    result["all_pass"] = bool(all(a["pass"] for a in result["assertions"].values()) and gates["pass"])
    if not result["all_pass"]:
        result["stopped"] = "an assertion or a gate failed: no rate and no per-leak verdict is written (stop rule, §7.4)"
        result["_timings"] = timings
        return result
    t3 = time.perf_counter()
    result["metrics"] = summarize(leaks, results, b, cfg)
    result["reported"] = reported_counts(results, b, classes)
    timings["metrics"] = time.perf_counter() - t3
    result["_timings"] = timings
    return result


# --- The report -------------------------------------------------------------------------------------------------


def _pct(x: float | None) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.2f} %"


def _ci(s: dict[str, Any]) -> str:
    lo, hi = s.get("wilson95", s.get("ci95"))
    return f"[{_pct(lo)}, {_pct(hi)}]"


def _pts(d: dict[str, Any]) -> str:
    lo, hi = d["ci95"]
    return f"{100 * d['difference']:+.2f} points [{100 * lo:+.2f}, {100 * hi:+.2f}]"


def render_md(result: dict[str, Any]) -> str:
    cfg = result["config"]
    lines = [
        "# Leak detectors measured against each other (iteration 5)",
        "",
        "Design: `docs/PROTOCOL.md`, \"Leak detectors measured against each other (iteration 5)\"; H15 in `docs/HYPOTHESES.md`. "
        "These rates describe one seeded generator of leaks on these bars and dates, not all leaks.",
        "",
        f"Population: {cfg['n']} leaks, seed {cfg['population_seed']}, placement `{result['placement']}`"
        + (f" (quantile table SHA-256 `{result['table_sha256']}`)" if result["table_sha256"] else "")
        + f". TWO-RUN seed {cfg['two_run_seed']}. Pairs {', '.join(cfg['h1']['pairs'])} {cfg['h1']['interval']}.",
        "",
        "## Assertions and gates (evaluated first)",
        "",
        "| assertion | pass | violations |",
        "|---|---|---|",
    ]
    for name, a in result["assertions"].items():
        lines.append(f"| {name} | {'yes' if a['pass'] else '**NO**'} | {a['violations']} |")
    if "gates" in result:
        g = result["gates"]
        lines.append(f"| gate: FI's fast path against H1's own path ({g['leaks']} leaks) | {'yes' if g['fi']['pass'] else '**NO**'} | {g['fi']['mismatches']} |")
        lines.append(f"| gate: TRUNC-0, TWO-RUN and SHUFFLE through H1's own path | {'yes' if g['h1_path']['pass'] else '**NO**'} | "
                     f"{sum(g['h1_path']['mismatches'].values())} |")  # fmt: skip
    if "stopped" in result:
        lines += ["", f"**Stopped:** {result['stopped']}.", ""]
        return "\n".join(lines) + "\n"
    m = result["metrics"]
    d = m["detectors"]
    lines += ["", "## Any-cut share at H1's 16 cuts (convention G unless named)", "",
              "| detector | runs per cut | all leaks | 95 % Wilson | not constant | designed: no | mean per-cut rate |", "|---|---|---|---|---|---|---|"]  # fmt: skip
    for k, x in d.items():
        a = x["any_cut"]
        lines.append(f"| {k} | {x['runs_per_cut']} | {_pct(a['all']['share'])} | {_ci(a['all'])} | {_pct(a['not-constant']['share'])} | "
                     f"{_pct(a['designed-no']['share'])} | {_pct(x['mean_per_cut_rate']['all']['mean'])} |")  # fmt: skip
    h = m["h15"]
    lines += ["", "## H15 (deciding cell: TRUNC-0 against FI, H1's 16 cuts, any cut, all leaks, convention G)", "",
              f"TRUNC-0 minus FI: {_pts(h['deciding_cell'])} (Newcombe, method 10). Sign: **{h['sign']}**. Margin: **{h['margin']}**. "
              f"Prior: **{h['prior']}**." + (f" Reported as **{h['words']}** ({', '.join(h['qualifier']['triggered_by'])})." if h["words"] else ""),
              f"Exact McNemar p: {h['deciding_cell']['mcnemar_exact_p']:.4g}. Beside it, never deciding: mean per-cut rate difference "
              f"{100 * h['beside']['mean_per_cut_rate_difference']['mean']:+.2f} points; convention P {_pts(h['beside']['convention P'])}."]  # fmt: skip
    if m["cut_date_bootstrap"]:
        bt = m["cut_date_bootstrap"]
        lines.append(f"Cut-date bootstrap ({bt['subsets']} subsets of {bt['dates_per_subset']} of {bt['dates']} dates): "
                     f"{bt['percentiles_points'][0]:+.2f} to {bt['percentiles_points'][1]:+.2f} points"
                     + (" (wider than the 1-point margin: H15's verdict is date-dependent)." if bt["wider_than_margin"] else "."))  # fmt: skip
    c = m["conventions"]["sentence"]
    lines += ["", f"Truncation's rate lies between {_pct(c['X'])} and {_pct(c['Y'])} depending on how a missing bar is read "
              f"(G to M: {_pct(c['G_to_M'][0])} to {_pct(c['G_to_M'][1])}).", "", "## Pairs (any cut, H1's 16 cuts)", "",
              "| pair | b | c | difference, Newcombe 95 % | exact McNemar p |", "|---|---|---|---|---|"]  # fmt: skip
    for name, p in {**m["pairs"], **m["equal_run_counts"]}.items():
        lines.append(f"| {name} | {p['b']} | {p['c']} | {_pts(p['newcombe'])} | {p['mcnemar_exact_p']:.4g} |")
    lines += ["", "## The union", "", *(f"- {k}: {_pct(s['share'])} {_ci(s)}" for k, s in m["union"].items()), "",
              "Caught by the union and missed by each detector (share of the union's catches):", "",
              *(f"- {k}: {s['count']} {_ci(s)}" for k, s in m["missed_by_detector_among_union"].items()), "",
              f"The union's misses: {m['union_misses']['count']} (constant at H1's compared rows: {m['union_misses']['constant_h1_cuts']}; "
              f"over both schedules: {m['union_misses']['constant_both_schedules']}).", "", "## Read split (row level)", ""]  # fmt: skip
    for k, s in m["read_split"].items():
        lines.append(f"- {k}: {s['flagged_rows']} flagged rows, {_pct(s['through_a_missing_read']['share'])} through a missing read.")
    lines += ["", "## Mirror asymmetry", "", *(f"- {k}: {_pct(s['any_cut']['share'])} {_ci(s['any_cut'])} of {s['leaks']} single-comparison leaks"
                                                for k, s in m["mirror_asymmetry"].items())]  # fmt: skip
    lines += ["", "## Placement-invariant subset (never deciding)", ""]
    for k, s in m["placement_invariant_subset"].items():
        lines.append(f"- {k}: {s['leaks']} leaks; FI {_pct(s['FI_any_cut']['share'])}; TRUNC-0 minus FI {_pts(s['TRUNC-0_minus_FI'])}.")
    if "provenance" in result:
        from olsprime.bench import provenance

        lines += ["", *provenance.render_md(result["provenance"])]
    return "\n".join(lines) + "\n"


def write(out: Any, result: dict[str, Any], run_info: dict[str, Any]) -> None:
    import json
    from pathlib import Path

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "detectors.json").write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (out / "detectors.md").write_text(render_md(result), encoding="utf-8")
    (out / "run.json").write_text(json.dumps(run_info, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def headline(result: dict[str, Any]) -> str:
    """The one line the CLI prints: pass or fail and counts while any check fails; H15's labels once all pass."""
    failed = [k for k, a in result.get("assertions", {}).items() if not a["pass"]]
    if "gates" in result and not result["gates"]["pass"]:
        failed.append("gates")
    if "stopped" in result:
        return f"detectors STOPPED: {len(failed)} check(s) failed: {'; '.join(failed)}"
    h = result["metrics"]["h15"]
    return f"detectors: every assertion and gate passed; H15 sign {h['sign']}, margin {h['margin']}, prior {h['prior']}"


# --- CLI ---------------------------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import logging
    import time

    from olsprime.bench import provenance
    from olsprime.paths import runs_dir

    parser = argparse.ArgumentParser(prog="python -m olsprime.bench.detectors", description="Leak detectors measured against each other.")
    sub = parser.add_subparsers(dest="command", required=True)
    dg = sub.add_parser("digest", help="the development digest of a population (§1.7)")
    dg.add_argument("--seed", type=int, required=True)
    dg.add_argument("--placement", choices=adv.PLACEMENTS, required=True)
    dg.add_argument("--table", default=None)
    dg.add_argument("--n", type=int, default=10_000)
    rn = sub.add_parser("run", help="the benchmark: assertions and gates first, rates only if all pass")
    rn.add_argument("--seed", type=int, required=True, help="the population's seed")
    rn.add_argument("--two-run-seed", type=int, required=True)
    rn.add_argument("--placement", choices=adv.PLACEMENTS, required=True)
    rn.add_argument("--table", default=None)
    rn.add_argument("--bootstrap-seed", type=int, default=None)
    rn.add_argument("--n", type=int, default=10_000)
    rn.add_argument("--workers", type=int, default=8)
    rn.add_argument("--out", default=None)
    rn.add_argument("--synthetic", action="store_true", help="synthetic bars, for tests and smoke runs: reads no data")
    args = parser.parse_args(argv)
    if args.command == "digest":
        if args.seed == CONFIRMATORY_POPULATION_SEED:
            parser.error("a digest of the confirmatory population is a deliberate, logged step after audit pass 5b (§1.7): not here")
        leaks = adv.generate(args.n, args.seed, placement=args.placement, table_path=args.table)
        import platform

        print(f"{development_digest(leaks)}  seed {args.seed}, n {args.n}, placement {args.placement}, numpy {np.__version__}, "
              f"{platform.system()} {platform.machine()}; portable (12 digits) {portable_digest(leaks)}")  # fmt: skip
        return 0
    if args.synthetic and FORBIDDEN_IN_WAVE_3 & {args.seed, args.two_run_seed, args.bootstrap_seed}:
        parser.error("the confirmatory seeds are never run on synthetic bars")
    logging.basicConfig(level=logging.ERROR, format="%(asctime)s %(levelname)s %(message)s")
    import multiprocessing

    multiprocessing.set_start_method("spawn", force=True)  # the adversary's own pool (FI's gate) too: see _spawn
    started = time.perf_counter()
    cfg = DetectorConfig(population_seed=args.seed, two_run_seed=args.two_run_seed, placement=args.placement, n=args.n, bootstrap_seed=args.bootstrap_seed)
    if args.synthetic:
        prov = {**provenance.record({}), "bars": "synthetic"}
        bars = synthetic_pairs()
    else:
        prov = provenance.record(provenance.current_manifest())  # before any data is read
        bars = {pair: adv._load_development(pair, cfg.adversary.h1) for pair in cfg.adversary.h1.pairs}
    if args.placement == adv.QUANTILE:
        if args.table is None:
            parser.error("--placement quantile needs --table, the registered quantile table")
        adv.load_table(args.table)  # refuses before any work if the table is not the registered one
    result = run(bars, cfg, table_path=args.table, workers=args.workers, prov=prov)
    timings = result.pop("_timings")
    out = args.out
    if out is None:
        base = runs_dir() / f"{datetime.now(UTC):%Y-%m-%d}-detectors"
        out, k = base, 2
        while out.exists():
            out, k = base.with_name(f"{base.name}-{k}"), k + 1
    write(out, result, {"finished_at": datetime.now(UTC).isoformat(), "seconds": round(time.perf_counter() - started, 1),
                        "stages": {k: round(v, 1) for k, v in timings.items()}, "workers": args.workers, "n": args.n})  # fmt: skip
    print(f"{headline(result)}; written to {out}")
    return 0 if result.get("all_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
