"""Audit pass 5b, M3: the auditor's independent scripts as tests (X3, X12, X11, X9, the catch rule, a one-bit twin).

Each test restates a registered rule in its own code (scalar rewrites, its own seed keys, its own truncation) and
compares it with the detectors module, so that a wrong detector fails here even when the module agrees with
itself. Synthetic bars only; development seeds only (population 51118 under the default placement, TWO-RUN 51119).
"""

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass

import numpy as np
import polars as pl
import pytest

from olsprime.bench import adversary as adv
from olsprime.bench import detectors as det
from olsprime.bench import twins as tw

CFG = det.DetectorConfig(
    population_seed=det.DEVELOPMENT_POPULATION_SEED,
    two_run_seed=det.DEVELOPMENT_TWO_RUN_SEED,
    n=40,
)
COLS = (
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "trades",
)
SCHEDULE_ID = {"h1": 1, "long": 2}  # §2.5, restated


@pytest.fixture(scope="module")
def bars():
    return det.synthetic_pairs(degrade=True)


@pytest.fixture(scope="module")
def benches(bars):
    return det.build_benches(bars, CFG)


@pytest.fixture(scope="module")
def population():
    return adv.generate(CFG.n, CFG.population_seed)


def _columns(bars: pl.DataFrame) -> dict[str, np.ndarray]:
    return {k: bars[k].cast(pl.Float64).to_numpy().copy() for k in COLS}


def _z(seed: int, pair: str, schedule_id: int, k: int, run: int) -> np.ndarray:
    """§2.5's draw, restated: ``default_rng([seed, crc32(pair), schedule_id, k, run]).standard_normal((10, 9))``."""
    return np.random.default_rng(
        [seed, zlib.crc32(pair.encode("ascii")), schedule_id, k, run]
    ).standard_normal((10, 9))


def _repair_bar(
    row: tuple[float, ...], z: np.ndarray, sigma: float
) -> tuple[float, ...]:
    """§2.5's repair of one bar, written with scalars (X3)."""
    o, h, lo, c, v, q, tb, tq, tr = row
    f_open, f_high, f_low, f_close, f_vol, f_quote, f_tb, f_tq, f_tr = (
        math.exp(sigma * float(x)) for x in z
    )
    o2, c2 = o * f_open, c * f_close
    uw, lw = math.log(h / max(o, c)), math.log(min(o, c) / lo)
    h2 = max(o2, c2) * math.exp(uw * f_high)
    lo2 = min(o2, c2) * math.exp(-(lw * f_low))
    if v > 0:
        v2 = v * f_vol
        vwap = min(max(q / v * f_quote, lo2), h2)
        q2 = v2 * vwap
        return (
            o2,
            h2,
            lo2,
            c2,
            v2,
            q2,
            min(tb * f_tb, v2),
            min(tq * f_tq, q2),
            max(float(np.rint(tr * f_tr)), 1.0),
        )
    return (o2, h2, lo2, c2, v, q, tb, tq, tr)


def _two_run_columns(
    col: dict[str, np.ndarray], t: int, sigma: float, z: np.ndarray
) -> dict[str, np.ndarray]:
    out = {k: a.copy() for k, a in col.items()}
    n = len(col["close"])
    for i, r in enumerate(range(t + 1, min(t + 1 + adv.FUTURE_REACH, n))):
        for k, x in zip(
            COLS,
            _repair_bar(tuple(float(col[k][r]) for k in COLS), z[i], sigma),
            strict=True,
        ):
            out[k][r] = x
    return out


def _close(a: np.ndarray, b: np.ndarray, rel: float = 1e-12) -> bool:
    nan = np.isnan(a) | np.isnan(b)
    if not np.array_equal(np.isnan(a), np.isnan(b)):
        return False
    return bool(np.all(np.abs(a[~nan] - b[~nan]) <= rel * np.abs(b[~nan])))


def _window_of(col: dict[str, np.ndarray], t: int) -> dict[str, np.ndarray]:
    """The quantities of rows t - PAST_REACH .. t + FUTURE_REACH, from a slice of the columns, NaN outside."""
    n = len(col["close"])
    lo, hi = max(0, t - adv.PAST_REACH), min(n, t + adv.FUTURE_REACH + 1)
    q = adv.quantities(pl.DataFrame({k: col[k][lo:hi] for k in COLS}))
    out = {}
    for name, a in q.items():
        w = np.full(adv.WIDTH, np.nan)
        w[lo - (t - adv.PAST_REACH) : hi - (t - adv.PAST_REACH)] = a
        out[name] = w
    return out


# --- X3: §2.5's repair, bar by bar, all nine columns, both sigmas -------------------------------------------


def test_two_runs_repair_equals_a_scalar_rewrite_of_section_2_5(bars):
    rng = np.random.default_rng(99)
    checked = 0
    for pair, b in bars.items():
        col = _columns(b)
        n = b.height
        zero = np.flatnonzero(col["volume"] == 0)
        cuts = [int(x) for x in rng.integers(300, n - 12, size=10)] + [
            int(zero[zero > 600][0]) - 4,
            n - 2,
            n - 5,
            n - 11,
        ]
        for k, t in enumerate(cuts):
            for run in (1, 2, 5, 8):
                z = _z(CFG.two_run_seed, pair, 2, k, run)
                assert np.array_equal(
                    det.two_run_z(CFG.two_run_seed, pair, 2, k, run), z
                )
                for sigma in det.SIGMAS:
                    got = _columns(det.two_run_bars(b, t, sigma, z)[0])
                    want = _two_run_columns(col, t, sigma, z)
                    for c in COLS:
                        assert _close(got[c], want[c], 4.5e-16), (
                            pair,
                            t,
                            run,
                            sigma,
                            c,
                        )
                        checked += np.isfinite(want[c][t + 1 : t + 11]).sum()
    assert checked > 5000


# --- X12: TWO-RUN and SHUFFLE from the registered seed keys, all 16 runs, both schedules --------------------


def test_two_runs_windows_are_the_registered_draws_on_both_schedules(bars, benches):
    """Every run (both sigmas, runs 1-8) of every cut of both schedules, from the registered keys, block by block."""
    bench, c_ = benches.two_run, benches.two_run.n_cuts
    cols = {p: _columns(b) for p, b in bars.items()}
    runs = [(s, r) for s in det.SIGMAS for r in range(1, det.TWO_RUN_RUNS + 1)]
    assert benches.two_run_runs == runs
    for i, c in enumerate(benches.cuts):
        p, t = c["pair"], c["index"]
        orig = _window_of(cols[p], t)
        for name in adv.QUANTITY_NAMES:
            assert _close(bench.view.w[name][i], orig[name]), (i, name)
        zs = {
            r: _z(CFG.two_run_seed, p, SCHEDULE_ID[c["schedule"]], c["k"], r)
            for r in range(1, det.TWO_RUN_RUNS + 1)
        }
        for j, (sigma, r) in enumerate(runs):
            want = _window_of(_two_run_columns(cols[p], t, sigma, zs[r]), t)
            for name in adv.QUANTITY_NAMES:
                assert _close(
                    bench.view.w[name][(1 + j) * c_ + i], want[name], 1e-11
                ), (c["schedule"], c["k"], p, sigma, r, name)


def test_shuffles_windows_are_the_registered_twins(bars, benches):
    """SHUFFLE's twin j at H1's k-th cut: rows after t take a past row drawn by ``[20261030, crc32(pair), k, j]``."""
    bench = benches.shuffle
    c_ = bench.n_cuts
    cols = {p: _columns(b) for p, b in bars.items()}
    for i, c in enumerate(bench.cuts):
        p, t = c["pair"], c["index"]
        n = len(cols[p]["close"])
        for j in range(tw.K_TWINS):
            rng = np.random.default_rng(
                [tw.TWIN_SEED, zlib.crc32(p.encode("ascii")), c["k"], j]
            )
            src = np.concatenate(
                [
                    np.arange(t + 1),
                    rng.integers(0, t + 1, size=n - t - 1, dtype=np.int64),
                ]
            )
            want = _window_of({k: a[src] for k, a in cols[p].items()}, t)
            for name in adv.QUANTITY_NAMES:
                assert _close(bench.view.w[name][(1 + j) * c_ + i], want[name], 0.0), (
                    p,
                    c["k"],
                    j,
                    name,
                )


def _moved(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    out = np.zeros(a.shape, dtype=bool)
    for i, (x, y) in enumerate(zip(a, b, strict=True)):
        out[i] = (math.isnan(x) != math.isnan(y)) or (
            not math.isnan(x) and not math.isnan(y) and abs(x - y) > 1e-9
        )
    return out


def _flag(
    orig: dict[str, np.ndarray],
    other: dict[str, np.ndarray],
    n: int,
    m: int,
    rows: np.ndarray,
) -> bool:
    """H1's catch rule at ``rows``: ``orig`` on a series of ``n`` rows, ``other`` on one of ``m`` rows."""
    return any(bool(_moved(np.broadcast_to(np.asarray(orig[k], float), (n,))[rows], np.broadcast_to(np.asarray(other[k], float), (m,))[rows]).any())
               for k in orig)  # fmt: skip


def _scored_rows(benches, pair: str, at: int) -> np.ndarray:
    rows = np.arange(at - adv.FUTURE_REACH, at + 1)
    return rows[benches.schedules[pair].scored[rows]]


def test_two_run_and_shuffle_flags_through_whole_perturbed_series(
    bars, benches, population
):
    """X12 at the flag level, through a series view of the whole perturbed bars: H1's cuts, runs 1, 2 and 8."""
    leaks = population[:8]
    cols = {p: _columns(b) for p, b in bars.items()}
    extras = {p: det.extra_quantities(b, i) for i, (p, b) in enumerate(bars.items())}
    full = {
        p: adv.SeriesView({**adv.quantities(b), **extras[p]}) for p, b in bars.items()
    }
    two = {leak.id: det.judge_window(leak, benches.two_run).cut_flags for leak in leaks}
    shf = {leak.id: det.judge_window(leak, benches.shuffle).cut_flags for leak in leaks}
    orig = {(leak.id, p): leak.outputs(full[p]) for leak in leaks for p in bars}
    seen: set[tuple[str, bool]] = set()
    for i in benches.rows("h1"):
        c = benches.cuts[i]
        p, t = c["pair"], c["index"]
        rows = _scored_rows(benches, p, t)
        for r in (1, 2, 8):
            view = adv.SeriesView(
                {
                    **adv.quantities(
                        pl.DataFrame(
                            _two_run_columns(
                                cols[p], t, 0.1, _z(CFG.two_run_seed, p, 1, c["k"], r)
                            )
                        )
                    ),
                    **extras[p],
                }
            )
            for leak in leaks:
                n = bars[p].height
                flag = _flag(orig[(leak.id, p)], leak.outputs(view), n, n, rows)
                assert flag == bool(two[leak.id][i, r - 1]), (leak.id, p, c["k"], r)
                seen.add(("TWO-RUN", flag))
    for i, c in enumerate(benches.shuffle.cuts):
        p, t = c["pair"], c["index"]
        rows = _scored_rows(benches, p, t)
        n = len(cols[p]["close"])
        for j in (0, 7):
            rng = np.random.default_rng(
                [tw.TWIN_SEED, zlib.crc32(p.encode("ascii")), c["k"], j]
            )
            src = np.concatenate(
                [
                    np.arange(t + 1),
                    rng.integers(0, t + 1, size=n - t - 1, dtype=np.int64),
                ]
            )
            view = adv.SeriesView(
                {
                    **adv.quantities(
                        pl.DataFrame({k: a[src] for k, a in cols[p].items()})
                    ),
                    **extras[p],
                }
            )
            for leak in leaks:
                flag = _flag(orig[(leak.id, p)], leak.outputs(view), n, n, rows)
                assert flag == bool(shf[leak.id][i, j]), (leak.id, p, c["k"], j)
                seen.add(("SHUFFLE", flag))
    assert seen == {
        (d, f) for d in ("TWO-RUN", "SHUFFLE") for f in (True, False)
    }  # not vacuous


# --- Hand-built leaks: one per node type, and reach-1 leaks true on the original bars ---------------------------


A, C0 = adv.At, adv.Const
HAND: tuple[adv.Leak, ...] = (
    det.hand_leak(101, adv.Cmp(A("close", 1), ">", 1.0, A("close", 0))),
    det.hand_leak(
        102,
        adv.Cmp(adv.Agg("volume", "max", 1, 3), "<", 1.2, adv.TrailMean("volume", 20)),
        output="probs",
    ),
    det.hand_leak(103, adv.Cmp(adv.Agg("body", "mean", 1, 5), ">", 1.0, C0(0.01))),
    det.hand_leak(
        104,
        adv.Cmp(adv.Agg("high", "min", 1, 2), ">", 1.0, adv.Agg("high", "max", -3, 0)),
    ),
    det.hand_leak(
        105, adv.Cmp(adv.Agg("trades", "sum", 1, 10), ">", 9.0, A("trades", 0))
    ),
    det.hand_leak(106, adv.Same(1, 0)),
    det.hand_leak(107, adv.Colour("green", 1)),
    det.hand_leak(108, adv.Colour("red", 2), output="probs"),
    det.hand_leak(109, adv.Pattern("hammer", 1, 2.0)),
    det.hand_leak(110, adv.Pattern("star", 2, 1.5)),
    det.hand_leak(111, adv.Cell("green", "small", 1, 0.01)),
    det.hand_leak(112, adv.Cell("red", "big", 3, 0.02)),
    det.hand_leak(
        113,
        adv.Logic(
            "AND",
            adv.Colour("green", 1),
            adv.Cmp(A("wick_ratio", 1), ">", 1.0, C0(0.0)),
        ),
    ),
    det.hand_leak(
        114,
        adv.Logic(
            "OR", adv.Colour("red", 1), adv.Cmp(A("close", 2), "<", 1.0, A("close", 0))
        ),
    ),
    det.hand_leak(115, adv.Logic("XOR", adv.Same(2, 1), adv.Pattern("hammer", 1, 1.0))),
    det.hand_leak(
        116,
        adv.WSum(
            0.7,
            adv.Colour("green", 1),
            -0.3,
            adv.LogRatio(A("close", 1), A("close", 0)),
        ),
        output="exp_return",
    ),
    det.hand_leak(117, adv.LogRatio(A("vwap", 1), A("vwap", 0)), output="exp_return"),
    det.hand_leak(
        118, adv.Rel(A("close", 1), adv.TrailMean("close", 5)), output="probs"
    ),
    det.hand_leak(119, adv.Raw(A("wick_ratio", 1)), output="exp_return"),
    det.hand_leak(
        120, adv.Cmp(A("close", 1), ">", 0.001, A("close", 0))
    ),  # reach 1, true on every original row
    det.hand_leak(
        121, adv.LogRatio(A("close", 1), A("close", 0)), output="exp_return"
    ),  # reach 1, continuous
)


# --- X11: truncation on really truncated bars, under G, M and P --------------------------------------------------


def _truncated_view(bars, extras, p: str, at: int) -> adv.SeriesView:
    head = bars[p].head(at + 1)  # the input really ends at bar ``at``
    return adv.SeriesView(
        {**adv.quantities(head), **{k: v[: at + 1] for k, v in extras[p].items()}}
    )


def test_truncation_on_really_truncated_bars_under_g_m_and_p(bars, benches, population):
    extras = {p: det.extra_quantities(x, i) for i, (p, x) in enumerate(bars.items())}
    full = {
        p: adv.SeriesView({**adv.quantities(x), **extras[p]}) for p, x in bars.items()
    }
    views: dict[tuple[str, int], adv.SeriesView] = {}
    units = [i for i in benches.rows("h1")] + [i for i in benches.rows("long")][::8]
    leaks = [*population[:12], *HAND]
    checked = 0
    seen: set[tuple[str, str, bool]] = set()
    for leak in leaks:
        for conv in det.CONVENTIONS:
            got = det.judge_window(leak, benches.trunc, conv).cut_flags[:, 0]
            orig = {p: adv.outputs_under(leak, full[p], conv) for p in bars}
            entries = [(part, i, benches.cuts[i]["pair"], benches.cuts[i]["index"] + shift)
                       for part, shift in (("TRUNC-0", 0), ("TRUNC-1", 1)) for i in units]  # fmt: skip
            entries += [
                ("ENDS", j, m["pair"], m["index"])
                for j, m in enumerate(benches.retile.ends)
            ]
            for part, i, p, at in entries:
                if (p, at) not in views:
                    views[(p, at)] = _truncated_view(bars, extras, p, at)
                run = adv.outputs_under(leak, views[(p, at)], conv)
                flag = _flag(
                    orig[p], run, bars[p].height, at + 1, _scored_rows(benches, p, at)
                )
                assert flag == bool(got[benches.trunc_parts[part][i]]), (
                    leak.render(),
                    conv,
                    part,
                    p,
                    at,
                )
                checked += 1
                seen.add((part, conv, flag))
    assert checked > 8_000
    assert seen == {
        (part, conv, f)
        for part in ("TRUNC-0", "TRUNC-1", "ENDS")
        for conv in det.CONVENTIONS
        for f in (True, False)
    }


def test_trunc_1_flags_a_reach_1_leak_at_every_cut(benches):
    """§2.3: TRUNC-1 compares row t + 1, where a read at s + 1 is missing: a reach-1 leak is flagged at every cut
    (v1's arm, rows t-10..t, could not). The binary one is true on every original row, so truncation makes it false."""
    for leak in (HAND[-2], HAND[-1]):
        v = det.cut_verdicts(det.judge_all(leak, benches), benches)
        assert leak.reach()[1] == 1
        for schedule in ("h1", "long"):
            assert v[("TRUNC-1/G", schedule)].all(), (leak.render(), schedule)
            assert v[("TRUNC-0/G", schedule)].all(), (leak.render(), schedule)


# --- X9: every node type under the three conventions, written again from §2 -------------------------------------


def _x9(view, shape):
    def val(e):
        if isinstance(e, adv.Const):
            return np.full(shape, e.c)
        if isinstance(e, adv.At):
            return np.broadcast_to(np.asarray(view.at(e.q, e.o), float), shape)
        if isinstance(e, adv.Agg):
            st = np.stack([view.at(e.q, o) for o in range(e.lo, e.hi + 1)])
            return {"max": np.max, "min": np.min, "mean": np.mean, "sum": np.sum}[e.op](
                st, axis=0
            )
        if isinstance(e, adv.TrailMean):
            return np.mean(np.stack([view.at(e.q, -o) for o in range(e.w)]), axis=0)
        raise TypeError(type(e))

    def atom(truth, missing, conv):
        out = np.where(truth, 1.0, 0.0)
        return np.where(missing, {"G": 0.0, "M": 1.0, "P": np.nan}[conv], out)

    def both(p1, p2):
        return np.where(
            np.isnan(p1) | np.isnan(p2), np.nan, ((p1 == 1) & (p2 == 1)).astype(float)
        )

    def tri(e, conv):
        with np.errstate(invalid="ignore"):
            if isinstance(e, adv.Cmp):
                a, c = val_or_cont(e.lhs, conv), val_or_cont(e.rhs, conv)
                return atom(
                    a > e.margin * c if e.op == ">" else a < e.margin * c,
                    np.isnan(a) | np.isnan(c),
                    conv,
                )
            if isinstance(e, adv.Same):
                x, y = view.at("green", e.o), view.at("green", e.r)
                return atom(x == y, np.isnan(x) | np.isnan(y), conv)
            if isinstance(e, adv.Colour):
                x = view.at(e.colour, e.o)
                return atom(x > 0.5, np.isnan(x), conv)
            if isinstance(e, adv.Pattern):
                body, up, lo = (
                    view.at(q, e.o) for q in ("body", "upper_wick", "lower_wick")
                )
                long_, short = (lo, up) if e.kind == "hammer" else (up, lo)
                return both(
                    atom(long_ >= e.a * body, np.isnan(long_) | np.isnan(body), conv),
                    atom(short <= body, np.isnan(short) | np.isnan(body), conv),
                )
            if isinstance(e, adv.Cell):
                body, col = view.at("body", e.o), view.at(e.colour, e.o)
                return both(
                    atom(col > 0.5, np.isnan(col), conv),
                    atom(
                        body < e.c if e.size == "small" else body > e.c,
                        np.isnan(body),
                        conv,
                    ),
                )
            if isinstance(e, adv.Logic):
                x, y = tri(e.a, conv), tri(e.b, conv)
                f = {
                    "AND": lambda p, q: p & q,
                    "OR": lambda p, q: p | q,
                    "XOR": lambda p, q: p ^ q,
                }[e.op]
                return np.where(
                    np.isnan(x) | np.isnan(y), np.nan, f(x == 1, y == 1).astype(float)
                )
        raise TypeError(type(e))

    def val_or_cont(e, conv):
        with np.errstate(all="ignore"):
            if isinstance(e, adv.WSum):
                x, y = (
                    tri(q, conv) if q.binary else val_or_cont(q, conv)
                    for q in (e.a, e.b)
                )
                return e.w1 * x + e.w2 * y
            if isinstance(e, adv.LogRatio):
                x, y = val_or_cont(e.a, conv), val_or_cont(e.b, conv)
                return np.where((x > 0) & (y > 0), np.log(x / y), np.nan)
            if isinstance(e, adv.Rel):
                return val_or_cont(e.a, conv) / val_or_cont(e.b, conv) - 1.0
            if isinstance(e, adv.Raw):
                return val_or_cont(e.a, conv)
        return val(e)

    return tri, val_or_cont


def test_every_node_type_under_the_three_conventions(benches, population):
    view = benches.trunc.view
    shape = (benches.trunc.n_cuts * 2, adv.COMPARED)
    tri, cont = _x9(view, shape)
    kinds: set[str] = set()
    for leak in [*population, *HAND]:
        kinds |= {type(node).__name__ for _, node in det._walk(leak.expr)}
        for conv in det.CONVENTIONS:
            got = np.broadcast_to(
                np.asarray(adv.evaluate_under(leak.expr, view, conv), float), shape
            )
            want = tri(leak.expr, conv) if leak.expr.binary else cont(leak.expr, conv)
            got, want = (np.where(np.isfinite(x), x, np.nan) for x in (got, want))
            assert np.array_equal(got, want, equal_nan=True), (leak.render(), conv)
            assert not (
                conv == "G" and leak.expr.binary and np.isnan(got).any()
            )  # a binary leak is never missing under G
    assert kinds >= {
        "Cmp",
        "Same",
        "Colour",
        "Pattern",
        "Cell",
        "Logic",
        "WSum",
        "LogRatio",
        "Rel",
        "Raw",
        "At",
        "Agg",
        "TrailMean",
        "Const",
    }


# --- The catch rule at its edge, and the twin check's bit rule ---------------------------------------------------


def test_the_catch_rule_at_0_9e_9_and_1_1e_9():
    a = np.array([0.0, 0.0, 0.0, np.nan, np.nan, 1.0, 5.0])
    b = np.array([0.9e-9, 1.1e-9, -1.1e-9, 0.0, np.nan, 1.0, np.inf])
    assert det._moved(a, b).tolist() == [False, True, True, True, False, False, True]
    assert det._moved_finite(a, b).tolist() == [
        False,
        True,
        True,
        False,
        False,
        False,
        False,
    ]  # §4.4's sensitivity
    rows = det.compare(
        [a[None, :]], [[b[None, :]]], [], [[]], np.ones((1, 7), dtype=bool)
    )
    assert rows.flags[0, 0].tolist() == [False, True, True, True, False, False, True]
    assert rows.finite_flags[0, 0].tolist() == [
        False,
        True,
        True,
        False,
        False,
        False,
        False,
    ]


@dataclass(frozen=True)
class _OneUlpTwin:
    """A 'twin' whose output moves by one ulp (below 1e-9) where bar s + 1 goes missing: only the bit rule sees it."""

    binary = False

    def evaluate(self, view):
        now, nxt = view.at("close", 0), view.at("close", 1)
        return np.where(np.isnan(nxt), now, np.nextafter(now, np.inf))

    def offsets(self):
        return frozenset({0, 1})


@dataclass(frozen=True)
class _LeakWithABadTwin:
    binary = False

    def evaluate(self, view):
        return view.at("close", 1)

    def offsets(self):
        return frozenset({1})

    def twin(self):
        return _OneUlpTwin()


def test_the_twin_check_sees_a_twin_that_differs_by_one_bit(benches):
    leak = det.hand_leak(9, _LeakWithABadTwin(), output="exp_return")
    twin = det.judge_window(leak.honest_twin(), benches.trunc, "G")
    assert (
        not twin.flags.any() and twin.bits.any()
    )  # H1's rule misses it; a single changed bit does not
    assert det.process_leak(leak, benches).violations["honest-twins-never-flagged"] > 0
