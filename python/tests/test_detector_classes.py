"""Fonseca's classes and the cancelled controls on our bars, with their registered verdicts (docs/PROTOCOL.md, §3.2-3.3).

Written, with every verdict below, before any detector ran on these classes (the progress log of iteration 5's
wave 3 records the order). Synthetic bars only; development seeds only.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from olsprime.bench import detectors as det

CFG = det.DetectorConfig(population_seed=det.DEVELOPMENT_POPULATION_SEED, two_run_seed=det.DEVELOPMENT_TWO_RUN_SEED)
TRUNC_DETECTORS = ("TRUNC-0", "TRUNC-1")


@pytest.fixture(scope="module")
def bars():
    return det.synthetic_pairs()


@pytest.fixture(scope="module")
def benches(bars):
    return det.build_benches(bars, CFG)


def _verdicts(unit, benches):
    return det.cut_verdicts(det.judge_all(unit, benches), benches)


def _any_run(v):
    return v.any(axis=1)


# --- M1: gated off at every compared row of the schedule at hand: "never" for every detector there ------------


@pytest.mark.parametrize("schedule", ["h1", "long", "ends"])
def test_m1_is_never_flagged_on_its_schedule(benches, schedule):
    v = _verdicts(det.class_m1(benches, schedule), benches)
    if schedule == "ends":
        keys = [f"{d}/{c}" for d in ("RETILE", "ENDS") for c in ("G", "M")]
    else:
        keys = ["FI", "TWO-RUN", *(f"{d}/{c}" for d in TRUNC_DETECTORS for c in ("G", "M"))]
        keys += ["SHUFFLE"] if schedule == "h1" else []
    for key in keys:
        assert not v[(key, schedule)].any(), key


@pytest.mark.parametrize("schedule", ["h1", "long", "ends"])
def test_m1_under_p_is_flagged_by_truncation_at_every_cut(benches, schedule):
    """Pass 5b, Minor 6 (registered after the class tests above): under P the gate's comparison with a missing operand
    is missing, so the truncation detectors flag M1 at every cut (every end for RETILE), except a cut whose
    truncation point is the series' last row, which cannot flag; these bars have none."""
    v = _verdicts(det.class_m1(benches, schedule), benches)
    keys = ["RETILE/P", "ENDS/P"] if schedule == "ends" else [f"{d}/P" for d in TRUNC_DETECTORS]
    for key in keys:
        assert not det.truncation_cannot_flag(benches, key, schedule).any()
        assert _any_run(v[(key, schedule)]).all(), key


def test_a_truncation_point_on_the_series_last_row_cannot_flag():
    """Structural: from the cut lists (t for TRUNC-0, t + 1 for TRUNC-1, e for ENDS and RETILE), never the flags."""
    b = SimpleNamespace(trunc=SimpleNamespace(cuts=[{"pair": "X", "at": 5}, {"pair": "X", "at": 9}, {"pair": "X", "at": 9}]),
                        trunc_parts={"TRUNC-0": np.array([0, 1]), "TRUNC-1": np.array([1, 2]), "ENDS": np.array([0, 2])},
                        rows=lambda schedule: np.array([0, 1]), schedules={"X": SimpleNamespace(bars=SimpleNamespace(height=10))})  # fmt: skip
    assert det.truncation_cannot_flag(b, "TRUNC-0/P", "h1").tolist() == [False, True]
    assert det.truncation_cannot_flag(b, "TRUNC-1/G", "long").tolist() == [True, True]
    assert det.truncation_cannot_flag(b, "RETILE/P", "ends").tolist() == [False, True]


# --- M2: close[s+1] > 2 close[s], and its mirror ------------------------------------------------------------


@pytest.mark.parametrize("schedule", ["h1", "long"])
def test_m2_under_trunc_0_never_under_g_and_every_cut_under_m(benches, schedule):
    v = _verdicts(det.class_m2(), benches)
    assert not v[("TRUNC-0/G", schedule)].any()
    assert v[("TRUNC-0/M", schedule)].all()


@pytest.mark.parametrize("schedule", ["h1", "long"])
def test_the_mirror_of_m2_swaps_the_two(benches, schedule):
    v = _verdicts(det.class_m2(mirrored=True), benches)
    assert v[("TRUNC-0/G", schedule)].all()
    assert not v[("TRUNC-0/M", schedule)].any()


@pytest.mark.parametrize("schedule", ["h1", "long"])
def test_m2_under_fi_follows_its_registered_rule(bars, benches, schedule):
    """Three-valued since pass 5b (Minor 5): flagged where the rule says so; elsewhere not predicted, not asserted.
    The engineered cases, both values of the rule included, are in tests/test_detector_runpath.py."""
    v = _verdicts(det.class_m2(), benches)
    cuts = [benches.cuts[i] for i in benches.rows(schedule)]
    rule = [det.fi_m2_rule(bars[c["pair"]], c["index"]) for c in cuts]
    assert set(rule) <= {True, None} and True in rule
    flagged = _any_run(v[("FI", schedule)])
    assert all(flagged[j] for j, r in enumerate(rule) if r is True)


# --- M3: a future close re-stamped to row s, frozen: "never" for every detector -----------------------------


def test_m3_is_never_flagged_by_any_detector_under_any_convention(benches):
    v = _verdicts(det.class_m3(), benches)
    for key, flags in v.items():
        assert not flags.any(), key


# --- FP1 and FP2 on close, and on every control: the independent prediction, run for run -------------------


@pytest.mark.parametrize("base", det.FONSECA_FP_BASES, ids=lambda leak: leak.render())
@pytest.mark.parametrize("kind", det.CANCELLED_KINDS)
def test_the_cancelled_controls_on_close_follow_the_prediction(benches, base, kind):
    control = det.cancelled_control(base, kind)
    predicted = det.predicted_unit(base)
    rows = det.judge_all(control, benches)
    for key, bench in (("FI", benches.fi), ("TWO-RUN", benches.two_run), ("SHUFFLE", benches.shuffle)):
        assert np.array_equal(rows[key].cut_flags, det.predicted_flags(kind, predicted, bench, "G")), key
    for conv in ("G", "M", "P"):
        assert np.array_equal(rows[f"TRUNC/{conv}"].cut_flags, det.predicted_flags(kind, predicted, benches.trunc, conv)), conv
    if kind == "FP2-fmin":
        assert not any(r.cut_flags.any() for r in rows.values())
