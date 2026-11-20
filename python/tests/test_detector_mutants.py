"""Audit pass 5b's planted-bug control for the detector bench: every mutant must be killed by the detector tests.

The 16 mutants are the auditor's (``.claude/briefs/iteration-5/audit-5b-scripts/mutate.py`` and ``mutate2.py``), with
the replaced strings adapted to the fixed code and each mutant's meaning kept. Each is applied to a temporary copy
of ``python/``, never to the repository, and the detector test modules run against the copy (as ``run_muts.sh``
does, each in a fresh spawned process running ``pytest.main``). A mutant is killed when that run fails a test (pytest's exit code 1); the
unmutated copy must pass first.

Opt-in: ``OLSPRIME_MUTANTS=1 uv run pytest tests/test_detector_mutants.py -s`` (``pyproject.toml`` is not touched; about
ten minutes on 12 cores). Without the variable only the cheap check that every mutant still applies runs.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from olsprime.bench import provenance
from olsprime.paths import REPO_ROOT

ENV = "OLSPRIME_MUTANTS"
PYTHON_DIR = REPO_ROOT / "python"
DET, ADV = "olsprime/bench/detectors.py", "olsprime/bench/adversary.py"
# The fast modules first: ``-x`` stops at the first failure.
MODULES = (
    "tests/test_detector_runpath.py",
    "tests/test_detector_independent.py",
    "tests/test_detector_stats.py",
    "tests/test_detector_classes.py",
    "tests/test_detector_verdicts.py",
    "tests/test_detectors.py",
)
PARALLEL = 4

M23_OLD = """    for _, c, at in entries:
        w = adv._window(full_q[c["pair"]], at)
        cut_w = {k: v.copy() for k, v in w.items()}
        for v in cut_w.values():
            v[adv.PAST_REACH + 1 :] = np.nan  # every bar after the cut is missing
        orig_w.append(w)
        trunc_w.append(cut_w)
        masks.append(_compared(sched[c["pair"]].scored, at))
"""
M23_NEW = """    for part_, c, at in entries:
        shift = 1 if part_ == "TRUNC-1" else 0  # MUTANT: v1's arm, rows t-10..t, truncated after t+1
        w = adv._window(full_q[c["pair"]], at - shift)
        cut_w = {k: v.copy() for k, v in w.items()}
        for v in cut_w.values():
            v[adv.PAST_REACH + 1 + shift :] = np.nan
        orig_w.append(w)
        trunc_w.append(cut_w)
        masks.append(_compared(sched[c["pair"]].scored, at - shift))
"""

MUTANTS: dict[str, tuple[str, str, str]] = {
    "m1_trunc0_one_bar_late": (
        DET,
        "v[adv.PAST_REACH + 1 :] = np.nan",
        "v[adv.PAST_REACH + 2 :] = np.nan",
    ),
    "m2_tworun_volume_unperturbed": (DET, 'v2 = v * f["volume"]', "v2 = v * 1.0"),
    "m3a_tworun_runs_3_to_8_reuse_run_2": (
        DET,
        'out, st = two_run_bars(bars, c["index"], sigma, zs[r])',
        'out, st = two_run_bars(bars, c["index"], sigma, zs[min(r, 2)])',
    ),
    "m3b_tworun_long_schedule_id_1": (
        DET,
        'zs = {r: two_run_z(cfg.two_run_seed, p, SCHEDULE_ID[c["schedule"]], c["k"], r)',
        'zs = {r: two_run_z(cfg.two_run_seed, p, 1, c["k"], r)',
    ),
    "m4_moved_threshold_1e-6": (
        DET,
        "return (change > inv.CAUGHT_ABOVE) | (np.isnan(a) != np.isnan(b))",
        "return (change > 1e-6) | (np.isnan(a) != np.isnan(b))",
    ),
    "m5_retile_one_tile_input": (
        DET,
        "            tiles[k][j, length - 2 * tau :] = q[k]\n",
        "            tiles[k][j, length - 2 * tau :] = q[k]\n            tiles[k][j, : length - tau] = np.nan\n",
    ),
    "m7_colour_under_M_is_G": (
        ADV,
        "            return _atom(x > 0.5, np.isnan(x), c)",
        '            return _atom(x > 0.5, np.isnan(x) & (c != "M"), c)',
    ),
    # Adapted: the rule is three-valued since pass 5b (Minor 5); the mutant still says "flagged at every cut".
    "m8_fi_m2_rule_every_cut": (
        DET,
        'return True if float(bars["high"][t + 1]) >= 2.0 / 3.0 * float(bars["close"][t]) else None',
        "return True",
    ),
    "m16_h15_deciding_cell_is_trunc1": (
        DET,
        'deciding = diff(denominators["all"], "TRUNC-0")',
        'deciding = diff(denominators["all"], "TRUNC-1/G")',
    ),
    "m17_union_without_shuffle": (
        DET,
        'union = anyc["FI"] | anyc["TRUNC-0"] | anyc["TWO-RUN"] | anyc["SHUFFLE"]',
        'union = anyc["FI"] | anyc["TRUNC-0"] | anyc["TWO-RUN"]',
    ),
    "m18_tworun_wick_wrong_factor": (
        DET,
        'uw2, lw2 = uw * f["high"], lw * f["low"]',
        'uw2, lw2 = uw * f["low"], lw * f["low"]',
    ),
    "m19_trunc1_is_trunc0": (
        DET,
        'entries.append(("TRUNC-1", c, t1))',
        'entries.append(("TRUNC-1", c, c["index"]))',
    ),
    "m20_fi_x3_is_column_1": (
        DET,
        'out[f"FI x3{suffix}"], out[f"FI /3{suffix}"] = fi[:, :, 0], fi[:, :, 1]',
        'out[f"FI x3{suffix}"], out[f"FI /3{suffix}"] = fi[:, :, 1], fi[:, :, 0]',
    ),
    "m21_twin_check_h1_rule_only": (
        DET,
        "moved = int(r.flags.any() or r.bits.any())",
        "moved = int(r.flags.any())",
    ),
    "m22_p_is_kleene_in_logic": (
        ADV,
        "        return np.where(np.isnan(x) | np.isnan(y), np.nan, op(x == 1.0, y == 1.0).astype(np.float64))",
        (
            '        return np.where((np.isnan(x) | np.isnan(y)) & ~((e.op == "AND") & ((x == 0.0) | (y == 0.0))), np.nan, '
            "op(x == 1.0, y == 1.0).astype(np.float64))"
        ),
    ),
    "m23_trunc1_is_v1s_arm": (DET, M23_OLD, M23_NEW),
}


def _source(rel: str) -> str:
    return (PYTHON_DIR / rel).read_text(
        encoding="utf-8"
    )  # text mode: CRLF read as LF, as the mutants are written


def test_there_are_sixteen_mutants_and_each_applies_exactly_once():
    """Cheap and always on: a code change that moves a mutant's string shows up here, not as a silent survivor."""
    assert len(MUTANTS) == 16
    for name, (rel, old, new) in MUTANTS.items():
        assert old != new and _source(rel).count(old) == 1, name


SKIP_DIRS = frozenset({".venv", "__pycache__", ".pytest_cache", ".ruff_cache"})
MARKER = "tests/test_copy_is_what_runs.py"
MARKER_SOURCE = '''"""Written into a copy by tests/test_detector_mutants.py: the copy's packages are the ones under test."""

from pathlib import Path

import olsprime
import tests


def test_the_copy_is_what_runs():
    root = Path(__file__).resolve().parents[1]
    assert Path(olsprime.__file__).resolve().is_relative_to(root), olsprime.__file__
    assert Path(tests.__file__).resolve().is_relative_to(root), tests.__file__
'''


def _copy(dst: Path) -> None:
    """``python/`` file by file into ``dst``, without the environment and the caches; and the marker test."""
    for path in PYTHON_DIR.rglob("*"):
        rel = path.relative_to(PYTHON_DIR)
        if path.is_file() and not SKIP_DIRS & set(rel.parts):
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            (dst / rel).write_bytes(path.read_bytes())
    (dst / MARKER).write_text(MARKER_SOURCE, encoding="utf-8", newline="\n")


def _args(copy: Path, basetemp: Path) -> list[str]:
    """``pytest.main``'s arguments for a copy. Its ``pythonpath`` option puts the copy first on the search path of the
    fresh process before any test or conftest is imported (pytest does it; this file edits no search path)."""
    return [f"--rootdir={copy}", "-c", str(copy / "pyproject.toml"), "-o", f"pythonpath={copy}", "-q", "-x", "-p", "no:cacheprovider",
            f"--basetemp={basetemp}", f"--junitxml={basetemp.parent / (basetemp.name + '.xml')}", "-k", "not worker_count",
            *(str(copy / m) for m in (MARKER, *MODULES))]  # fmt: skip


def _first_failure(xml: Path) -> str:
    from xml.etree import ElementTree

    if not xml.exists():
        return "no report"
    for case in ElementTree.parse(xml).getroot().iter("testcase"):
        if case.find("failure") is not None or case.find("error") is not None:
            return f"{case.get('classname')}::{case.get('name')}"
    return ""


def _mutate(root: Path, name: str) -> Path:
    rel, old, new = MUTANTS[name]
    copy = root / name / "python"
    _copy(copy)
    path = copy / rel
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, name
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    return copy


@pytest.mark.skipif(
    os.environ.get(ENV) != "1",
    reason=f"opt-in: set {ENV}=1 (about ten minutes; runs the detector tests 17 times)",
)
def test_every_planted_mutant_is_killed(tmp_path):
    """Each copy runs in a fresh spawned process whose target is ``pytest.main`` itself, so that nothing of the
    repository's packages is imported there before the copy is first on the path."""
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor

    before = provenance.code_digest()
    base = tmp_path / "base" / "python"
    _copy(base)
    copies = {name: _mutate(tmp_path / "mut", name) for name in MUTANTS}
    spawn = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(
        max_workers=1, mp_context=spawn, max_tasks_per_child=1
    ) as pool:
        code = int(
            pool.submit(pytest.main, _args(base, tmp_path / "tmp-base")).result()
        )
    assert code == 0, (
        f"the unmutated copy must pass first (the marker test included): {_first_failure(tmp_path / 'tmp-base.xml')}"
    )
    with ProcessPoolExecutor(
        max_workers=PARALLEL, mp_context=spawn, max_tasks_per_child=1
    ) as pool:
        futures = {
            name: pool.submit(pytest.main, _args(copy, tmp_path / f"tmp-{name}"))
            for name, copy in copies.items()
        }
        codes = {name: int(f.result()) for name, f in futures.items()}
    outcomes = {
        name: (code, _first_failure(tmp_path / f"tmp-{name}.xml"))
        for name, code in codes.items()
    }
    killed = [
        name
        for name, (code, line) in outcomes.items()
        if code == 1 and "test_the_copy_is_what_runs" not in line
    ]
    report = [
        f"{'killed  ' if name in killed else f'SURVIVED (exit {code})'} {name}: {line}"
        for name, (code, line) in outcomes.items()
    ]
    print(f"\nmutants killed: {len(killed)} of {len(MUTANTS)}\n" + "\n".join(report))
    assert provenance.code_digest() == before  # the repository was never touched
    assert len(killed) == len(MUTANTS), "\n".join(report)
