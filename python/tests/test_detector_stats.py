"""The statistics of the detector benchmark (docs/PROTOCOL.md, iteration 5, §4 and §5): pure functions, known values."""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.stats import binom

from olsprime.bench import detector_stats as ds
from olsprime.bench.adversary import Z95

# Fagerland, Lydersen and Laake's worked example (Cavo et al., 2012), contingencytables tests/testthat/test-ch8.R:
# a = 59, b = 6, c = 16, d = 80: "estimate = -0.0621 (95% CI -0.1186 to -0.0046)"; exact McNemar "P = 0.052479".
CAVO = (59, 6, 16, 80)


def test_newcombe_method_10_on_the_published_example():
    r = ds.newcombe_paired(*CAVO)
    assert round(r["difference"], 4) == -0.0621
    assert [round(x, 4) for x in r["ci95"]] == [-0.1186, -0.0046]


def test_newcombe_on_the_packages_edge_cases():
    r = ds.newcombe_paired(1, 0, 0, 1)  # matrix(c(1, 0, 0, 1), 2): 0.0000 (95% CI -0.5734 to 0.5734)
    assert r["difference"] == 0.0 and [round(x, 4) for x in r["ci95"]] == [-0.5734, 0.5734]
    assert all(math.isnan(x) for x in ds.newcombe_paired(0, 0, 0, 0)["ci95"])


@pytest.mark.parametrize("big_a_case", ["above", "between", "negative"])
def test_newcombe_psi_follows_its_three_branches(big_a_case):
    tables = {"above": (500, 10, 12, 478), "between": (1, 1, 1, 1), "negative": (2, 40, 50, 3)}
    a, b, c, d = tables[big_a_case]
    n = a + b + c + d
    big_a = a * d - b * c
    root = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    expected = (big_a - n / 2) / root if big_a > n / 2 else 0.0 if big_a >= 0 else big_a / root
    assert ds.newcombe_paired(a, b, c, d)["psi"] == pytest.approx(expected)


def test_newcombe_is_antisymmetric_and_contains_the_estimate():
    rng = np.random.default_rng(4)
    for _ in range(200):
        a, b, c, d = (int(x) for x in rng.integers(0, 60, size=4))
        if a + b + c + d == 0:
            continue
        r, s = ds.newcombe_paired(a, b, c, d), ds.newcombe_paired(a, c, b, d)
        assert r["difference"] == pytest.approx(-s["difference"])
        assert r["ci95"][0] == pytest.approx(-s["ci95"][1]) and r["ci95"][1] == pytest.approx(-s["ci95"][0])
        assert r["ci95"][0] <= r["difference"] + 1e-12 <= r["ci95"][1] + 2e-12


def test_mcnemar_exact_on_the_published_example_and_by_definition():
    assert round(ds.mcnemar_exact(6, 16), 6) == 0.052479
    assert ds.mcnemar_exact(0, 0) == 1.0 and ds.mcnemar_exact(5, 5) == 1.0
    assert ds.mcnemar_exact(3, 20) == pytest.approx(2 * binom.cdf(3, 23, 0.5))
    assert ds.mcnemar_exact(20, 3) == ds.mcnemar_exact(3, 20)


def test_the_paired_table_counts_each_cell():
    x = np.array([1, 1, 0, 0, 1], bool)
    y = np.array([1, 0, 1, 0, 0], bool)
    assert ds.paired_table(x, y) == {"a": 1, "b": 2, "c": 1, "d": 1}


def test_the_paired_difference_is_the_mean_of_the_differences():
    x, y = np.array([1.0, 0.5, 0.25, 1.0]), np.array([0.5, 0.5, 0.0, 1.0])
    r = ds.paired_difference(x, y)
    d = x - y
    assert r["mean"] == pytest.approx(d.mean())
    half = Z95 * d.std(ddof=1) / 2
    assert r["ci95"] == pytest.approx([d.mean() - half, d.mean() + half])


def test_the_first_m_cuts_curve_follows_the_order_given():
    caught = np.array([[0, 0, 1], [1, 0, 0], [0, 0, 0]], bool)
    curve = ds.first_m_curve(caught, order=[2, 0, 1], ms=(1, 2, 3, 16))
    assert [(r["m"], r["count"]) for r in curve] == [(1, 1), (2, 2), (3, 2)]
    with pytest.raises(ValueError):
        ds.first_m_curve(caught, order=[0, 0, 1])


def _cell(lo: float, hi: float, point: float | None = None) -> dict:
    p = (lo + hi) / 2 if point is None else point
    return {"difference": p / 100, "ci95": [lo / 100, hi / 100]}


@pytest.mark.parametrize(
    ("lo", "hi", "sign", "margin", "prior"),
    [
        (0.2, 1.4, "above FI", None, "holds"),
        (-1.6, -1.2, "below FI", "by more than 1 point", "fails"),
        (-0.8, -0.1, "below FI", "within 1 point", "fails"),
        (-1.4, -0.3, "below FI", "1-point margin not resolved", "fails"),
        (-0.6, 0.4, "not separated from FI", "within 1 point", "not refuted"),
        (-1.3, 0.5, "not separated from FI", "1-point margin not resolved", "undecided"),
    ],
)
def test_h15_labels_and_each_branch_of_the_prior(lo, hi, sign, margin, prior):
    out = ds.h15(_cell(lo, hi), {})
    assert (out["sign"], out["margin"], out["prior"]) == (sign, margin, prior)
    assert out["words"] is None and not out["qualifier"]["convention_dependent"]


def test_h15s_qualifier_needs_the_opposite_sign_and_an_interval_without_zero():
    deciding = _cell(-0.6, 0.4, point=-0.1)
    assert ds.h15(deciding, {"M": _cell(0.2, 1.0)})["words"] == "convention-dependent"
    assert ds.h15(deciding, {"not-constant": _cell(0.3, 0.9)})["qualifier"]["triggered_by"] == ["not-constant"]
    assert ds.h15(deciding, {"M": _cell(-0.2, 1.0)})["words"] is None  # the interval holds 0
    assert ds.h15(deciding, {"M": _cell(-1.0, -0.2)})["words"] is None  # the same sign
    assert ds.h15(_cell(-0.5, 0.5, point=0.0), {"M": _cell(0.2, 1.0)})["words"] is None  # no sign to oppose


def test_the_cut_date_bootstrap_draws_the_same_dates_on_both_pairs_and_is_seeded():
    rng = np.random.default_rng(0)
    dates = np.tile(np.arange(64), 2)  # 64 dates shared by two pairs
    trunc = rng.random((500, 128)) < 0.05
    fi = rng.random((500, 128)) < 0.05
    a = ds.cut_date_bootstrap(trunc, fi, dates, seed=99, subsets=50)
    assert a == ds.cut_date_bootstrap(trunc, fi, dates, seed=99, subsets=50)
    assert a != ds.cut_date_bootstrap(trunc, fi, dates, seed=98, subsets=50)
    same = ds.cut_date_bootstrap(trunc, trunc, dates, seed=99, subsets=50)
    assert same["percentiles_points"] == [0.0, 0.0] and not same["wider_than_margin"]
    assert a["dates"] == 64 and a["dates_per_subset"] == 8
