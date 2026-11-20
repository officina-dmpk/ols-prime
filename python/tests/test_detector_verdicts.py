"""Audit pass 5b, M4 (and X6, X6b, Minors 7 and 8): phase 2 can recompute the numbers from the per-leak file.

:func:`recompute` rebuilds, from ``verdicts.jsonl`` alone (its header holds the config, the cut lists and the run
labels), every number of ``metrics`` that is a function of per-leak cut verdicts and tags, with its own aggregation
(the registered variants by run label, the denominators, the union, the curve, the bootstrap loop); it calls
:mod:`olsprime.bench.detector_stats` only for the interval formulas, pinned in ``test_detector_stats.py``. It runs on
natural results and on results whose flags are seeded random bits, so that every wiring of ``summarize`` (which
variant, which arm, which denominator) is seen to matter. Synthetic bars only; development seeds only.

Usable on a run folder: ``python -m tests.test_detector_verdicts <folder>`` (from ``python/``).
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from olsprime.bench import adversary as adv
from olsprime.bench import detector_stats as ds
from olsprime.bench import detectors as det

CFG = det.DetectorConfig(
    population_seed=det.DEVELOPMENT_POPULATION_SEED,
    two_run_seed=det.DEVELOPMENT_TWO_RUN_SEED,
    n=60,
    bootstrap_seed=4242,
)
DENOMINATORS = ("all", "not-constant", "designed-no")
NOT_IN_THE_FILE = {
    "read_split"
}  # row level: JSON only (the header says so); distinct_expressions likewise


# --- The recomputation, from the file alone ---------------------------------------------------------------------


def _variants(
    header: dict[str, Any], rows: list[dict[str, Any]], part: str = "flags"
) -> dict[str, tuple[np.ndarray, int]]:
    """Every registered variant as ((leaks, cuts) bool, runs per cut), from raw bits by run label (not by position)."""
    cfg = header["config"]
    labels = {e["key"]: e["run_labels"] for e in header["layout"]["flags"]}

    def take(key: str, wanted: list[str]) -> tuple[np.ndarray, int]:
        cols = [labels[key].index(w) for w in wanted]
        return np.stack([r[part][key][:, cols].any(axis=1) for r in rows]), len(cols)

    v: dict[str, tuple[np.ndarray, int]] = {}
    for sched, sfx in (("h1", ""), ("long", "@long")):
        v[f"FI{sfx}"] = take(f"FI@{sched}", ["x3", "/3"])
        v[f"FI x3{sfx}"], v[f"FI /3{sfx}"] = (
            take(f"FI@{sched}", ["x3"]),
            take(f"FI@{sched}", ["/3"]),
        )
        for p in ("TRUNC-0", "TRUNC-1"):
            for c in "GMP":
                v[f"{p}/{c}{sfx}"] = take(f"{p}/{c}@{sched}", ["truncated"])
        for s in cfg["sigmas"]:
            for k in (1, 2, cfg["two_run_runs"]):
                v[f"TWO-RUN s{s:g} r{k}{sfx}"] = take(
                    f"TWO-RUN@{sched}", [f"s{s:g}-r{r}" for r in range(1, k + 1)]
                )
    for k in (1, 2, cfg["shuffle_k"]):
        v[f"SHUFFLE k{k}"] = take("SHUFFLE@h1", [f"twin-{j}" for j in range(k)])
    for c in "GMP":
        v[f"RETILE/{c}@ends"], v[f"ENDS/{c}@ends"] = (
            take(f"RETILE/{c}@ends", ["tile"]),
            take(f"ENDS/{c}@ends", ["truncated"]),
        )
    v["TRUNC-0"], v["TWO-RUN"], v["SHUFFLE"] = (
        v["TRUNC-0/G"],
        v[f"TWO-RUN s{cfg['sigmas'][0]:g} r2"],
        v[f"SHUFFLE k{cfg['shuffle_k']}"],
    )
    return v


def _share(caught: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    return ds.share(int((caught & mask).sum()), int(mask.sum()))


def _cell(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    t = {
        "a": int((x & y).sum()),
        "b": int((x & ~y).sum()),
        "c": int((~x & y).sum()),
        "d": int((~x & ~y).sum()),
    }
    return {**ds.newcombe_paired(t["a"], t["b"], t["c"], t["d"]), "table": t}


def _pair(
    x: np.ndarray, y: np.ndarray, rx: np.ndarray, ry: np.ndarray
) -> dict[str, Any]:
    c = _cell(x, y)
    t = c.pop("table")
    return {"table": t, "b": t["b"], "c": t["c"], "newcombe": c, "mcnemar_exact_p": ds.mcnemar_exact(t["b"], t["c"]),
            "per_cut_rate_difference": ds.paired_difference(rx, ry)}  # fmt: skip


def recompute(text: str) -> dict[str, Any]:
    """The metrics of ``summarize`` that the per-leak file determines, from the file alone."""
    header, rows = det.read_verdict_file(text)
    cfg = header["config"]
    n = len(rows)
    raw = _variants(header, rows)
    v = {k: x for k, (x, _) in raw.items()}
    runs = {k: r for k, (_, r) in raw.items()}
    vf = {k: x for k, (x, _) in _variants(header, rows, "finite").items()}
    anyc = {k: x.any(axis=1) for k, x in v.items()}
    rate = {k: x.mean(axis=1) for k, x in v.items()}
    family = np.array([r["family"] for r in rows])
    position = np.array([r["position"] for r in rows])
    constant_h1 = np.array([bool(r["constant_h1_cuts"]) for r in rows])
    constant_both = np.array([bool(r["constant_both_schedules"]) for r in rows])
    invariant = np.array([bool(r["placement_invariant"]) for r in rows])
    den = {
        "all": np.ones(n, dtype=bool),
        "not-constant": ~constant_h1,
        "designed-no": np.array([r["designed"] == "no" for r in rows]),
    }
    strata = {
        "inside": position == "inside",
        "outside": position == "outside",
        "other": ~np.isin(position, ["inside", "outside"]),
    }
    families = [f for f in adv.FAMILIES if (family == f).any()]
    names = [k for k in v if "@" not in k or k.endswith("@ends")]

    out: dict[str, Any] = {}
    out["detectors"] = {k: {"runs_per_cut": runs[k], "cuts": int(v[k].shape[1]),
                            "any_cut": {d: _share(anyc[k], m) for d, m in den.items()},
                            "mean_per_cut_rate": {d: ds.mean_rate(rate[k][m]) for d, m in den.items()},
                            "by_family": {d: {f: _share(anyc[k], m & (family == f)) for f in families} for d, m in den.items()},
                            "by_position": {d: {s: _share(anyc[k], m & sm) for s, sm in strata.items()} for d, m in den.items()}}
                        for k in names}  # fmt: skip
    out["ignores_outputs_that_turn_missing"] = {
        k: {d: _share(vf[k].any(axis=1), m) for d, m in den.items()} for k in names
    }
    out["long_schedule"] = {k: {"runs_per_cut": runs[k], "cuts": int(v[k].shape[1]), "any_cut": _share(anyc[k], den["all"]),
                                "mean_per_cut_rate": ds.mean_rate(rate[k])} for k in v if k.endswith("@long")}  # fmt: skip

    h1 = header["cuts"]["h1"]
    order = sorted(
        range(len(h1)),
        key=lambda j: (h1[j]["open_time"], header["pairs"].index(h1[j]["pair"])),
    )
    out["h1_cut_order"] = [h1[j]["open_time"][:10] + " " + h1[j]["pair"] for j in order]
    out["first_m_cuts"] = {k: {d: [{"m": mm, **_share(v[k][:, order[:mm]].any(axis=1), m)} for mm in (1, 2, 4, 8, 16) if mm <= len(order)]
                               for d, m in den.items()} for k in ("FI", "TRUNC-0", "TWO-RUN", "SHUFFLE", "TRUNC-1/G")}  # fmt: skip

    def sentence(m: np.ndarray) -> dict[str, Any]:
        if not m.any():
            return {"X": None, "Y": None, "G_to_M": [None, None]}
        s = {c: anyc[f"TRUNC-0/{c}"][m].mean() for c in "GMP"}
        return {
            "X": float(min(s.values())),
            "Y": float(max(s.values())),
            "G_to_M": sorted([float(s["G"]), float(s["M"])]),
        }

    out["conventions"] = {**{d_: {dd: {c: _share(anyc[f"{d_}/{c}" + ("@ends" if d_ == "RETILE" else "")], m) for c in "GMP"} for dd, m in den.items()}
                             for d_ in ("TRUNC-0", "TRUNC-1", "RETILE")}, "sentence": {d: sentence(m) for d, m in den.items()}}  # fmt: skip

    primary = ("FI", "TRUNC-0", "TWO-RUN", "SHUFFLE")
    out["pairs"] = {
        f"{x} - {y}": _pair(anyc[x], anyc[y], rate[x], rate[y])
        for i, x in enumerate(primary)
        for y in primary[i + 1 :]
    }
    out["pairs"]["TRUNC-1/G - TRUNC-0 (one-bar date shift)"] = _pair(
        anyc["TRUNC-1/G"], anyc["TRUNC-0"], rate["TRUNC-1/G"], rate["TRUNC-0"]
    )
    s0 = f"{cfg['sigmas'][0]:g}"
    out["equal_run_counts"] = {
        "FI x3 - TRUNC-0": _pair(
            anyc["FI x3"], anyc["TRUNC-0"], rate["FI x3"], rate["TRUNC-0"]
        ),
        f"TWO-RUN s{s0} r1 - TRUNC-0": _pair(
            anyc[f"TWO-RUN s{s0} r1"],
            anyc["TRUNC-0"],
            rate[f"TWO-RUN s{s0} r1"],
            rate["TRUNC-0"],
        ),
        "SHUFFLE k1 - TRUNC-0": _pair(
            anyc["SHUFFLE k1"], anyc["TRUNC-0"], rate["SHUFFLE k1"], rate["TRUNC-0"]
        ),
        f"FI - TWO-RUN s{s0} r2": _pair(
            anyc["FI"], anyc[f"TWO-RUN s{s0} r2"], rate["FI"], rate[f"TWO-RUN s{s0} r2"]
        ),
        "FI - SHUFFLE k2": _pair(
            anyc["FI"], anyc["SHUFFLE k2"], rate["FI"], rate["SHUFFLE k2"]
        ),
    }

    with_mirror = [r for r in rows if r["mirror"] is not None]
    mirror_keys = {"FI": ("FI@h1", None), "TRUNC-0": ("TRUNC-0/G@h1", None), "TRUNC-1": ("TRUNC-1/G@h1", None), "RETILE": ("RETILE/G@ends", None),
                   "TWO-RUN": ("TWO-RUN@h1", [f"s{s0}-r1", f"s{s0}-r2"]), "SHUFFLE": ("SHUFFLE@h1", None)}  # fmt: skip
    labels = {e["key"]: e["run_labels"] for e in header["layout"]["flags"]}
    out["mirror_asymmetry"] = {}
    for name, (key, wanted) in mirror_keys.items():
        if not with_mirror:
            break
        cols = slice(None) if wanted is None else [labels[key].index(w) for w in wanted]
        own = np.stack([r["flags"][key][:, cols].any(axis=1) for r in with_mirror])
        mir = np.stack([r["mirror"][key][:, cols].any(axis=1) for r in with_mirror])
        k = len(with_mirror)
        out["mirror_asymmetry"][name] = {"leaks": k, "any_cut": ds.share(int((own.any(axis=1) != mir.any(axis=1)).sum()), k),
                                         "per_cut": [ds.share(int((own[:, j] != mir[:, j]).sum()), k) for j in range(own.shape[1])]}  # fmt: skip

    union = anyc["FI"] | anyc["TRUNC-0"] | anyc["TWO-RUN"] | anyc["SHUFFLE"]
    s1 = f"{cfg['sigmas'][-1]:g}"
    long_four = (
        anyc["FI@long"]
        | anyc["TRUNC-0/G@long"]
        | anyc["TRUNC-1/G@long"]
        | anyc[f"TWO-RUN s{s0} r2@long"]
    )
    rows_ = {"primary": union, "with TRUNC-1": union | anyc["TRUNC-1/G"], "with RETILE": union | anyc["RETILE/G@ends"],
             f"with sigma {s1}": union | anyc[f"TWO-RUN s{s1} r2"], "over both schedules": union | long_four | anyc["TRUNC-1/G"],
             "under convention M": anyc["FI"] | anyc["TRUNC-0/M"] | anyc["TWO-RUN"] | anyc["SHUFFLE"]}  # fmt: skip
    out["union"] = {k: ds.share(int(m.sum()), n) for k, m in rows_.items()}
    out["missed_by_detector_among_union"] = {
        d: ds.share(int((union & ~anyc[d]).sum()), int(union.sum())) for d in primary
    }
    misses = ~union
    secondary = {"TRUNC-1": anyc["TRUNC-1/G"], "RETILE": anyc["RETILE/G@ends"], f"sigma {s1}": anyc[f"TWO-RUN s{s1} r2"],
                 "long schedule": long_four, "convention M": anyc["TRUNC-0/M"]}  # fmt: skip
    out["union_misses"] = {"count": int(misses.sum()), "constant_h1_cuts": int((misses & constant_h1).sum()),
                           "constant_both_schedules": int((misses & constant_both).sum()),
                           "caught_by_a_secondary_arm": {k: int((misses & m).sum()) for k, m in secondary.items()},
                           "by_family": {f: int((misses & (family == f)).sum()) for f in adv.FAMILIES}}  # fmt: skip
    out["descriptive"] = {
        "constant_h1_cuts": ds.share(int(constant_h1.sum()), n),
        "constant_both_schedules": ds.share(int(constant_both.sum()), n),
    }
    out["placement_invariant_subset"] = {}
    for name, m in (("invariant", invariant), ("complement", ~invariant)):
        c = _cell(anyc["TRUNC-0"][m], anyc["FI"][m])
        c.pop("table")
        out["placement_invariant_subset"][name] = {
            "leaks": int(m.sum()),
            "FI_any_cut": _share(anyc["FI"], m),
            "TRUNC-0_minus_FI": c,
        }

    deciding = _cell(anyc["TRUNC-0"], anyc["FI"])
    qualifiers = {
        "convention M": _cell(anyc["TRUNC-0/M"], anyc["FI"]),
        "not-constant denominator": _cell(
            anyc["TRUNC-0"][~constant_h1], anyc["FI"][~constant_h1]
        ),
    }
    h15 = ds.h15(deciding, qualifiers)
    h15["deciding_cell"] = {
        **deciding,
        "mcnemar_exact_p": out["pairs"]["FI - TRUNC-0"]["mcnemar_exact_p"],
    }
    h15["beside"] = {
        "mean_per_cut_rate_difference": ds.paired_difference(
            rate["TRUNC-0"], rate["FI"]
        ),
        "convention P": _cell(anyc["TRUNC-0/P"], anyc["FI"]),
    }
    out["h15"] = h15

    out["cut_date_bootstrap"] = None
    if cfg["bootstrap_seed"] is not None:
        dates = np.array([c["open_time"][:10] for c in header["cuts"]["long"]])
        unique = np.unique(dates)
        rng = np.random.default_rng(cfg["bootstrap_seed"])
        diffs = np.empty(cfg["bootstrap_subsets"])
        for s in range(cfg["bootstrap_subsets"]):
            cols = np.isin(
                dates, rng.choice(unique, size=cfg["bootstrap_dates"], replace=False)
            )
            diffs[s] = 100.0 * (
                v["TRUNC-0/G@long"][:, cols].any(axis=1).mean()
                - v["FI@long"][:, cols].any(axis=1).mean()
            )
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        out["cut_date_bootstrap"] = {"subsets": cfg["bootstrap_subsets"], "dates_per_subset": cfg["bootstrap_dates"], "dates": int(unique.size),
                                     "percentiles_points": [float(lo), float(hi)], "spread_points": float(hi - lo),
                                     "wider_than_margin": bool(hi - lo > ds.MARGIN_POINTS)}  # fmt: skip
    out["replications"] = {
        "FI any cut": out["detectors"]["FI"]["any_cut"]["all"],
        "SHUFFLE any cut": out["detectors"]["SHUFFLE"]["any_cut"]["all"],
    }
    out["leaks"] = [{"id": r["id"], "family": r["family"], "invariant": bool(r["placement_invariant"]), "constant_h1_cuts": bool(r["constant_h1_cuts"]),
                     **{d: "".join("X" if x else "." for x in v[d][i]) for d in primary}} for i, r in enumerate(rows)]  # fmt: skip
    return out


def _json(x: Any) -> Any:
    return json.loads(json.dumps(x, sort_keys=True, default=str))


def assert_recomputed(metrics: dict[str, Any], text: str) -> None:
    """Every number the file determines equals ``metrics``; the rest is named in ``NOT_IN_THE_FILE``."""
    got, want = _json(recompute(text)), _json(metrics)
    assert set(want) == set(got) | NOT_IN_THE_FILE | {"descriptive"}, set(want) ^ set(
        got
    )
    for key, value in got.items():
        if key == "descriptive":
            assert {k: want[key][k] for k in value} == value
            assert set(want[key]) - set(value) == {"distinct_expressions"}
            continue
        assert want[key] == value, key


# --- Fixtures ------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def benches():
    return det.build_benches(det.synthetic_pairs(degrade=True), CFG)


@pytest.fixture(scope="module")
def population():
    return adv.generate(CFG.n, CFG.population_seed)


@pytest.fixture(scope="module")
def results(benches, population):
    return [det.process_leak(leak, benches) for leak in population]


@pytest.fixture(scope="module")
def invariant(population):
    return det.placement_invariant(CFG, population)


# --- The file, and the recomputation on natural results -----------------------------------------------------------


def test_the_file_holds_every_raw_verdict_bit_for_bit(
    population, results, benches, invariant
):
    text = det.verdict_file(population, results, benches, CFG, invariant)
    header, rows = det.read_verdict_file(text)
    assert (
        header["format"] == det.VERDICT_FORMAT
        and header["fields"] == list(det.VERDICT_FIELDS)
        and header["leaks"] == len(rows) == CFG.n
    )
    assert header["config"] == _json(det.config_json(CFG)) and "read split" in " ".join(
        header["not_in_this_file"]
    )
    for leak, r, row in zip(population, results, rows, strict=True):
        assert (
            row["id"],
            row["family"],
            row["output"],
            row["designed"],
            row["position"],
        ) == (
            leak.id,
            leak.family,
            leak.output,
            leak.tag["designed"],
            leak.tag["position"],
        )
        assert (row["constant_h1_cuts"], row["constant_both_schedules"]) == (
            int(r.constant_h1),
            int(r.constant_both),
        )
        for part in ("flags", "finite"):
            assert set(row[part]) == set(getattr(r, part)) and all(
                np.array_equal(row[part][k], getattr(r, part)[k]) for k in row[part]
            )
        assert (row["mirror"] is None) == (r.mirror is None)
        if r.mirror is not None:
            assert all(np.array_equal(row["mirror"][k], r.mirror[k]) for k in r.mirror)
    assert sum(row["mirror"] is not None for row in rows) > 0
    assert (
        len(text.encode()) / CFG.n < 3_000
    )  # about 2 KB per leak: about 20 MB at n = 10,000


def test_the_headers_variants_are_the_registered_ones(
    population, results, benches, invariant
):
    header, rows = det.read_verdict_file(
        det.verdict_file(population, results, benches, CFG, invariant)
    )
    v = det.primary_verdicts(results, benches, CFG)
    mine = _variants(header, rows)
    assert set(v) == set(mine) == set(header["variants"])
    for name, spec in header["variants"].items():
        layout = {e["key"]: e for e in header["layout"]["flags"]}[spec["key"]]
        cols = [layout["run_labels"].index(lab) for lab in spec["runs"]]
        from_header = np.stack(
            [row["flags"][spec["key"]][:, cols].any(axis=1) for row in rows]
        )
        assert np.array_equal(from_header, v[name]) and np.array_equal(
            mine[name][0], v[name]
        ), name


def test_every_metric_of_the_file_is_recomputed_on_natural_results(
    population, results, benches, invariant
):
    metrics = det.summarize(population, results, benches, CFG, invariant=invariant)
    assert_recomputed(
        metrics, det.verdict_file(population, results, benches, CFG, invariant)
    )
    assert (
        metrics["h15"]["qualifier"]["cells"]["convention M"]["table"]["a"] >= 0
    )  # both cells, with their tables (M4)


def _random_results(results: list[det.LeakResult], seed: int) -> list[det.LeakResult]:
    """The same shapes with seeded random bits: every variant, arm and denominator then differs from its neighbours."""
    rng = np.random.default_rng(seed)
    p = {
        "FI": 0.03,
        "TRUNC-0": 0.02,
        "TRUNC-1": 0.04,
        "ENDS": 0.05,
        "RETILE": 0.05,
        "TWO-RUN": 0.004,
        "SHUFFLE": 0.003,
    }

    def draw(
        d: dict[str, np.ndarray],
    ) -> dict[str, np.ndarray]:  # the long schedule's 128 cuts at a 32nd of the rate
        return {
            k: rng.random(a.shape)
            < p[k.split("@")[0].split("/")[0]] / (32 if k.endswith("@long") else 1)
            for k, a in d.items()
        }

    mirror_shape = next(r.mirror for r in results if r.mirror is not None)
    out = []
    for r in results:
        out.append(replace(r, flags=draw(r.flags), finite=draw(r.finite), constant_h1=bool(rng.random() < 0.2), constant_both=bool(rng.random() < 0.1),
                           mirror=draw(mirror_shape) if rng.random() < 0.5 else None))  # fmt: skip
    return out


@pytest.mark.parametrize("seed", [1, 2])
def test_every_metric_of_the_file_is_recomputed_on_random_verdicts(
    population, results, benches, invariant, seed
):
    """Random verdicts make TRUNC-1 differ from TRUNC-0, SHUFFLE-only catches exist, x3 differs from /3, the long
    schedule's arms differ from H1's: a wrong wiring of ``summarize`` cannot agree with the recomputation."""
    fake = _random_results(results, seed)
    metrics = det.summarize(population, fake, benches, CFG, invariant=invariant)
    assert_recomputed(
        metrics, det.verdict_file(population, fake, benches, CFG, invariant)
    )
    union = metrics["union"]
    assert (
        union["primary"]["count"]
        > metrics["missed_by_detector_among_union"]["SHUFFLE"]["count"]
        > 0
    )
    assert metrics["pairs"]["TRUNC-1/G - TRUNC-0 (one-bar date shift)"]["b"] > 0


# --- X6: the inputs of the file, by other code ----------------------------------------------------------------------


def test_the_constant_flags_and_fis_directions_by_other_code(
    population, results, benches
):
    """``constant`` from the original outputs' bits at the scored compared rows of H1's cuts; FI's columns from the
    adversary's own fast path, by direction name."""
    h1 = benches.rows("h1")
    x3, d3 = benches.fi.directions.index("x3"), benches.fi.directions.index("/3")
    for leak, r in zip(population, results, strict=True):
        constant = True
        for value in leak.outputs(benches.fi.view).values():
            x = np.broadcast_to(
                np.asarray(value, float), (benches.fi.n_cuts * 3, adv.COMPARED)
            )[: benches.fi.n_cuts][h1]
            bits = x[benches.fi.scored[h1]].view(np.uint64)
            constant &= bool(np.all(bits == bits[0]))
        assert constant == r.constant_h1
        fast = adv.evaluate_fast(leak, benches.fi).caught
        assert np.array_equal(r.flags["FI@h1"][:, 0], fast[h1, x3]) and np.array_equal(
            r.flags["FI@h1"][:, 1], fast[h1, d3]
        )


def test_the_mirror_by_other_code(population, results, benches):
    """X6b: the mirror built here, FI through the adversary's fast path, TRUNC-0 through the kernel."""
    h1 = benches.rows("h1")
    t0 = benches.trunc_parts["TRUNC-0"][h1]
    seen = 0
    for leak, r in zip(population, results, strict=True):
        if not isinstance(leak.expr, adv.Cmp):
            assert r.mirror is None
            continue
        e = leak.expr
        mir = replace(
            leak, expr=adv.Cmp(e.lhs, "<" if e.op == ">" else ">", e.margin, e.rhs)
        )
        assert np.array_equal(
            r.mirror["FI@h1"], adv.evaluate_fast(mir, benches.fi).caught[h1]
        )
        assert np.array_equal(
            r.mirror["TRUNC-0/G@h1"][:, 0],
            det.judge_window(mir, benches.trunc, "G").cut_flags[t0, 0],
        )
        seen += 1
    assert seen > 0


# --- Minor 7: §4.4's sensitivity, by other code; Minor 8: the read split under each denominator ------------------


def test_ignores_outputs_that_turn_missing_recomputed_from_the_outputs(
    population, results, benches
):
    """A row counts only where both outputs are finite and move by more than 1e-9 (per output; any output)."""
    checked = {True: 0, False: 0}
    for leak, r in zip(population, results, strict=True):
        for key, bench, conv, part in (("FI@h1", benches.fi, "G", None), ("TWO-RUN@h1", benches.two_run, "G", None),
                                       ("TRUNC-0/G@h1", benches.trunc, "G", "TRUNC-0"), ("TRUNC-1/P@h1", benches.trunc, "P", "TRUNC-1")):  # fmt: skip
            c, runs = bench.n_cuts, len(bench.directions)
            outs = [
                np.broadcast_to(np.asarray(x, float), (c * (1 + runs), adv.COMPARED))
                for x in adv.outputs_under(leak, bench.view, conv).values()
            ]
            rows = (
                benches.rows("h1")
                if part is None
                else benches.trunc_parts[part][benches.rows("h1")]
            )
            for j, i in enumerate(rows):
                for run in range(runs):
                    hit = False
                    for o in outs:
                        a, b = o[i], o[(1 + run) * c + i]
                        for w in range(adv.COMPARED):
                            if (
                                bench.scored[i, w]
                                and np.isfinite(a[w])
                                and np.isfinite(b[w])
                                and abs(a[w] - b[w]) > 1e-9
                            ):
                                hit = True
                    assert hit == bool(r.finite[key][j, run]), (
                        leak.render(),
                        key,
                        j,
                        run,
                    )
                    checked[hit] += 1
    assert checked[True] > 0 and checked[False] > 0
    caught_only_through_missing = sum(
        bool(r.flags["TRUNC-0/G@h1"].any() and not r.finite["TRUNC-0/G@h1"].any())
        for r in results
    )
    assert (
        caught_only_through_missing > 0
    )  # continuous leaks whose output turns missing: the sensitivity drops them


def test_the_read_split_is_summed_over_each_denominators_leaks(
    population, results, benches, invariant
):
    metrics = det.summarize(population, results, benches, CFG, invariant=invariant)
    constant = np.array([r.constant_h1 for r in results])
    designed = np.array([leak.tag["designed"] == "no" for leak in population])
    for d, mask in (
        ("all", np.ones(len(results), bool)),
        ("not-constant", ~constant),
        ("designed-no", designed),
    ):
        for key, entry in metrics["read_split"][d].items():
            flagged = sum(
                r.split[key][0] for r, keep in zip(results, mask, strict=True) if keep
            )
            through = sum(
                r.split[key][1] for r, keep in zip(results, mask, strict=True) if keep
            )
            assert (
                entry["flagged_rows"] == flagged
                and entry["through_a_missing_read"]["count"] == through
            ), (d, key)
    primary = metrics["read_split"]["all"][
        "TWO-RUN s0.1 r2@h1"
    ]  # Minor 10: TWO-RUN's primary arm has its row
    assert (
        0
        < primary["flagged_rows"]
        <= metrics["read_split"]["all"]["TWO-RUN s0.1@h1"]["flagged_rows"]
    )


def test_the_long_schedule_class_of_the_unions_misses_is_the_long_arms_only(
    population, results, benches, invariant
):
    """§4.11 (Minor 9): ``FI@long | TRUNC-0/G@long | TRUNC-1/G@long | TWO-RUN s0.1 r2@long``, not the union over
    both schedules (which also holds TRUNC-1 at H1's cuts)."""
    fake = _random_results(results, 3)
    metrics = det.summarize(population, fake, benches, CFG, invariant=invariant)
    v = det.primary_verdicts(fake, benches, CFG)
    a = {k: x.any(axis=1) for k, x in v.items()}
    misses = ~(a["FI"] | a["TRUNC-0"] | a["TWO-RUN"] | a["SHUFFLE"])
    long_four = (
        a["FI@long"]
        | a["TRUNC-0/G@long"]
        | a["TRUNC-1/G@long"]
        | a["TWO-RUN s0.1 r2@long"]
    )
    assert metrics["union_misses"]["caught_by_a_secondary_arm"]["long schedule"] == int(
        (misses & long_four).sum()
    )
    assert int((misses & long_four).sum()) != int(
        (misses & (long_four | a["TRUNC-1/G"])).sum()
    )  # the two readings differ here


def main(folder: str) -> int:
    """Check a run folder: ``detectors.json`` against ``verdicts.jsonl``."""
    path = Path(folder)
    metrics = json.loads((path / "detectors.json").read_text(encoding="utf-8"))[
        "metrics"
    ]
    assert_recomputed(metrics, (path / det.VERDICT_FILE).read_text(encoding="utf-8"))
    print(
        f"recomputed from {det.VERDICT_FILE}: every number the file determines agrees with detectors.json"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))


def test_the_report_renders_an_empty_subset(population, results, benches):
    """Empty cells write null (pass 5b's nit); the Markdown says so instead of failing."""
    metrics = det.summarize(
        population,
        results,
        benches,
        CFG,
        invariant=np.ones(len(population), dtype=bool),
    )
    assert (
        metrics["placement_invariant_subset"]["complement"]["TRUNC-0_minus_FI"][
            "difference"
        ]
        is None
    )
    result = {
        "config": det.config_json(CFG),
        "placement": CFG.placement,
        "table_sha256": None,
        "assertions": {},
        "metrics": metrics,
    }
    assert "complement: 0 leaks" in det.render_md(
        result
    ) and "n/a (no leak)" in det.render_md(result)
