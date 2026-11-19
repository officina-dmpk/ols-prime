"""The statistics of the detector benchmark (``docs/PROTOCOL.md``, iteration 5, §4 and §5), as pure functions.

Nothing here reads data or draws a seed it is not given. Proportions are in [0, 1]; H15's labels take points.

- :func:`wilson`, :func:`mean_rate`: the adversary's own (Wilson; normal interval over leaks).
- :func:`newcombe_paired`: Newcombe's square-and-add interval for the difference of two paired proportions,
  method 10 of Newcombe (1998), with the correlation estimate ``psi`` adjusted as Fagerland, Lydersen and Laake
  implement it (``contingencytables::Newcombe_square_and_add_CI_paired_2x2``, read 2026-11-18): ``A = ad - bc``;
  ``psi = (A - N/2) / sqrt(...)`` if ``A > N/2``, ``0`` if ``0 <= A <= N/2``, ``A / sqrt(...)`` if ``A < 0``, and 0
  when a margin is 0. Pinned on their worked example (Cavo et al., 2012).
- :func:`mcnemar_exact`: the exact conditional two-sided McNemar p-value, ``min(1, 2 P(X <= min(b, c)))``,
  ``X ~ Bin(b + c, 1/2)``; 1 when ``b + c = 0``.
- :func:`paired_difference`: the normal interval of the mean of per-leak differences.
- :func:`h15`: H15's sign, margin, prior and qualifier as a function of the numbers (§5).
- :func:`cut_date_bootstrap`: §4.15, with the seed as an argument.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np
from scipy.stats import binom

from olsprime.bench.adversary import Z95, _mean_rate, wilson

__all__ = [
    "MARGIN_POINTS",
    "cut_date_bootstrap",
    "first_m_curve",
    "h15",
    "mcnemar_exact",
    "mean_rate",
    "newcombe_paired",
    "paired_difference",
    "paired_table",
    "share",
    "wilson",
]

MARGIN_POINTS = 1.0  # H15's smallest difference of interest, in points


def share(k: int, n: int) -> dict[str, Any]:
    """``k`` of ``n`` with its Wilson interval; an empty denominator writes ``null`` (never NaN) for the share and interval."""
    if not n:
        return {"count": int(k), "n": 0, "share": None, "wilson95": [None, None]}
    lo, hi = wilson(int(k), int(n))
    return {"count": int(k), "n": int(n), "share": k / n, "wilson95": [lo, hi]}


def mean_rate(rates: np.ndarray) -> dict[str, Any]:
    """Mean of per-leak rates with a normal 95 % interval over leaks; ``null`` mean and interval over no leak."""
    rates = np.asarray(rates, dtype=np.float64)
    if rates.size == 0:
        return {"n_leaks": 0, "mean": None, "ci95": [None, None]}
    return _mean_rate(rates)


def paired_table(x: np.ndarray, y: np.ndarray) -> dict[str, int]:
    """The 2x2 table of two paired verdicts: ``a`` both, ``b`` x only, ``c`` y only, ``d`` neither."""
    x, y = np.asarray(x, dtype=bool), np.asarray(y, dtype=bool)
    if x.shape != y.shape:
        raise ValueError("paired verdicts must have the same shape")
    return {"a": int((x & y).sum()), "b": int((x & ~y).sum()), "c": int((~x & y).sum()), "d": int((~x & ~y).sum())}


def newcombe_paired(a: int, b: int, c: int, d: int, z: float = Z95) -> dict[str, Any]:
    """Share of the first verdict minus share of the second, with Newcombe's interval (method 10, 1998).

    ``a``: both positive; ``b``: first only; ``c``: second only; ``d``: neither.
    """
    n = a + b + c + d
    if n == 0:
        return {"difference": None, "ci95": [None, None], "n": 0}
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n, z)
    l2, u2 = wilson(a + c, n, z)
    margins = (a + b, c + d, a + c, b + d)
    if min(margins) == 0:
        psi = 0.0
    else:
        big_a = a * d - b * c
        root = math.sqrt(math.prod(float(m) for m in margins))
        psi = (big_a - n / 2) / root if big_a > n / 2 else 0.0 if big_a >= 0 else big_a / root
    est = p1 - p2
    lower = est - math.sqrt(max(0.0, (p1 - l1) ** 2 + (u2 - p2) ** 2 - 2 * psi * (p1 - l1) * (u2 - p2)))
    upper = est + math.sqrt(max(0.0, (p2 - l2) ** 2 + (u1 - p1) ** 2 - 2 * psi * (p2 - l2) * (u1 - p1)))
    return {"difference": est, "ci95": [lower, upper], "n": n, "psi": psi}


def mcnemar_exact(b: int, c: int) -> float:
    """Exact conditional two-sided McNemar p-value on the discordant counts."""
    if b + c == 0:
        return 1.0
    return float(min(1.0, 2.0 * binom.cdf(min(b, c), b + c, 0.5)))


def paired_difference(x: np.ndarray, y: np.ndarray, z: float = Z95) -> dict[str, Any]:
    """Mean of ``x - y`` over leaks (per-leak rates), with a normal 95 % interval."""
    diff = np.asarray(x, dtype=np.float64) - np.asarray(y, dtype=np.float64)
    n = diff.size
    if n == 0:
        return {"n_leaks": 0, "mean": None, "ci95": [None, None]}
    m = float(diff.mean())
    se = float(diff.std(ddof=1) / math.sqrt(n)) if n > 1 else math.nan
    return {"n_leaks": int(n), "mean": m, "ci95": [m - z * se, m + z * se]}


def first_m_curve(caught: np.ndarray, order: Sequence[int], ms: Sequence[int] = (1, 2, 4, 8, 16)) -> list[dict[str, Any]]:
    """Caught at one of the first ``m`` cuts at least, the cuts taken in ``order`` (§4.3: by date, then by pair)."""
    caught = np.asarray(caught, dtype=bool)
    order = list(order)
    if sorted(order) != list(range(caught.shape[1])):
        raise ValueError("order must be a permutation of the cuts")
    out = []
    for m in ms:
        if m > len(order):
            continue
        k = int(caught[:, order[:m]].any(axis=1).sum())
        out.append({"m": int(m), **share(k, caught.shape[0])})
    return out


def _sign(lo: float, hi: float) -> str:
    if lo > 0:
        return "above FI"
    if hi < 0:
        return "below FI"
    return "not separated from FI"


def _margin(lo: float, hi: float, margin: float) -> str:
    if lo > -margin:
        return "within 1 point"
    if hi < -margin:
        return "by more than 1 point"
    return "1-point margin not resolved"


def _prior(sign: str, lo: float, margin: float) -> str:
    if sign == "above FI":
        return "holds"
    if sign == "below FI":
        return "fails"
    if lo > -margin:
        return "not refuted"
    return "undecided"


def h15(deciding: dict[str, Any], qualifiers: dict[str, dict[str, Any]], margin: float = MARGIN_POINTS) -> dict[str, Any]:
    """H15's labels from the deciding cell's Newcombe difference (proportions), and the qualifier (§5).

    ``deciding``: :func:`newcombe_paired` of TRUNC-0 against FI, H1's 16 cuts, any cut, all leaks, convention G.
    ``qualifiers``: the same difference under convention M and on the not-constant denominator. The verdict is
    "convention-dependent" when one of them has the sign opposite to the deciding cell's point difference with an
    interval that excludes 0. With a deciding point difference of exactly 0 no sign is opposite: no qualifier.
    Both cells are written back under ``qualifier.cells``, as given (each with its 2x2 table when the caller adds it).
    """
    lo, hi = (100.0 * x for x in deciding["ci95"])
    point = 100.0 * deciding["difference"]
    sign = _sign(lo, hi)
    out: dict[str, Any] = {"difference_points": point, "ci95_points": [lo, hi], "sign": sign,
                           "margin": None if sign == "above FI" else _margin(lo, hi, margin),
                           "prior": _prior(sign, lo, margin)}  # fmt: skip
    triggered = []
    for name, q in qualifiers.items():
        if q.get("n") == 0:  # an empty cell (no leak in the denominator) cannot trigger the qualifier
            continue
        qlo, qhi = (100.0 * x for x in q["ci95"])
        qpoint = 100.0 * q["difference"]
        excludes_zero = qlo > 0 or qhi < 0
        if excludes_zero and point != 0 and math.copysign(1.0, qpoint) != math.copysign(1.0, point) and qpoint != 0:
            triggered.append(name)
    out["qualifier"] = {"triggered_by": triggered, "convention_dependent": bool(triggered), "cells": dict(qualifiers)}
    out["words"] = "convention-dependent" if triggered else None
    return out


def cut_date_bootstrap(trunc: np.ndarray, fi: np.ndarray, dates: np.ndarray, *, seed: int, subsets: int = 2000, size: int = 8) -> dict[str, Any]:
    """§4.15: subsets of ``size`` dates without replacement, the same dates on both pairs; never deciding.

    ``trunc`` and ``fi``: (leaks, cuts) any-run verdicts on the long schedule; ``dates``: (cuts,) a date key per cut
    (both pairs share the long schedule's dates). Returns the 2.5th and 97.5th percentiles, in points, of the
    any-cut share of TRUNC-0 minus FI's over the subsets.
    """
    trunc, fi = np.asarray(trunc, dtype=bool), np.asarray(fi, dtype=bool)
    keys = np.asarray(dates)
    unique = np.unique(keys)
    if unique.size < size:
        raise ValueError(f"{unique.size} dates for subsets of {size}")
    rng = np.random.default_rng(seed)
    diffs = np.empty(subsets)
    for s in range(subsets):
        pick = rng.choice(unique, size=size, replace=False)
        cols = np.isin(keys, pick)
        diffs[s] = 100.0 * (trunc[:, cols].any(axis=1).mean() - fi[:, cols].any(axis=1).mean())
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {"subsets": int(subsets), "dates_per_subset": int(size), "dates": int(unique.size), "percentiles_points": [float(lo), float(hi)],
            "spread_points": float(hi - lo), "wider_than_margin": bool(hi - lo > MARGIN_POINTS)}  # fmt: skip
