"""LFM3's ablations and H6 (``olsprime.bench.ablations``) on Report n°2's fake store, CPU torch.

- the configuration: the protocol's order, the registered run, everything else enc-ols's (Report n°3's seeds, years and
  overrides), each fit enc-ols's but for its one change, the exact parameter counts;
- a Report n°3 run made by ``report3`` on the fake store, then the ablations' fits and score against it: enc-ols read and
  bound by digest, never refitted; ``--check`` byte for byte; a resumed run gives the same bytes;
- the binding refuses a wrong digest, a re-sealed enc-ols part and a ``report3.json`` whose per-seed log-loss was changed;
- H6's rule on chosen numbers, and the paired bootstrap of the ECE ratio against a direct recomputation on the rows.

Nothing reads the repository's ``data/`` or ``runs/``.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import pytest
import torch

from olsprime.bench import ablations as ab
from olsprime.bench import report2 as r2
from olsprime.bench import report3 as r3
from olsprime.eval import stats
from olsprime.models.matrix import prob_map
from olsprime.train import checkpoint
from olsprime.train.determinism import deterministic
from olsprime.train.fit import BrierFitConfig, EncoderSystem
from tests.test_report2 import CFG as R2CFG
from tests.test_report2 import FAKE_MANIFEST, fake_root  # noqa: F401 (fixture: Report n°2's synthetic store)

PROV = {"git_commit": "c" * 40, "code": {"sha256": "d" * 64, "files": 1}, "manifest_digest": "0" * 64}
TINY = (("d_model", 16), ("n_heads", 2), ("d_mlp", 32), ("n_layers", 2))  # two blocks: enc-ols-conv keeps an OLS block
SHORT = (("epochs", 2), ("warmup_steps", 3), ("eval_batch", 256))
CFG3 = r3.Report3Config(years=(2019,), seeds=(1, 2), device="cpu", encoder=TINY, fit=SHORT, synthetic="test: Report n°2's fake store")
CFG = ab.AblationsConfig(seeds=(1, 2), years=(2019,), device="cpu", encoder=TINY, fit=SHORT, synthetic="test: against the fake Report n°3")


@pytest.fixture(autouse=True, scope="module")
def one_thread():
    before = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(before)


@pytest.fixture(scope="module")
def runs_root(tmp_path_factory):
    """A runs root of this module: the readers open only files under it."""
    root = tmp_path_factory.mktemp("runs-ablations")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OLSPRIME_RUNS_DIR", str(root))
        yield root


@pytest.fixture(autouse=True)
def runs_env(sealed_vault, runs_root, monkeypatch):
    """Each test reads the module's runs root (after conftest's sealed_vault gives every test a runs root of its own)."""
    monkeypatch.setenv("OLSPRIME_RUNS_DIR", str(runs_root))


@pytest.fixture(scope="module")
def world(runs_root, fake_root):  # noqa: F811
    """Report n°2 on the fake store, Report n°3 on it (fits and score), and the inputs of the ablations' fits."""
    root, universe = fake_root
    out2 = runs_root / "report2"
    r2.run_report(R2CFG, out2, data_dir=root, universe=universe, manifest=FAKE_MANIFEST, provenance=PROV)
    run2 = r3.read_report2(out2 / r2.SERIES_FILE, r2.sha256_file(out2 / r2.SERIES_FILE))
    panel, bars = r3.load_panel(run2.config, data_dir=root, universe=universe)
    inputs = r3.build_inputs(run2, panel, bars, CFG3)
    out3 = runs_root / "report3"
    r3.run(inputs, CFG3, out3, "fits", prov=PROV)
    r3.run(inputs, CFG3, out3, "score", prov=PROV)
    sha3 = r2.sha256_file(out3 / r3.SERIES_FILE)
    return run2, inputs, out3, sha3


@pytest.fixture(scope="module")
def full(world, runs_root):
    run2, inputs, out3, sha3 = world
    run3 = ab.read_report3(out3, sha3)
    out = runs_root / "ablations"
    ab.run(inputs, run2, run3, CFG, out, "fits", prov=PROV)
    metrics = ab.run(None, run2, run3, CFG, out, "score", prov=PROV)
    return out, metrics


def _part_files(out: Path, arm: str | None = None) -> dict[str, bytes]:
    root = out / "parts" / "fits"
    return {p.relative_to(out).as_posix(): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file() and not p.name.startswith("timing.json") and (arm is None or p.relative_to(root).parts[0] == arm)}  # fmt: skip


def _ensembles(out: Path, run2: r3.Report2Run) -> tuple[dict, dict, dict]:
    """The ablations' ensembles and hourly log-loss and Brier, from their saved parts (series.npz is never opened here)."""
    fcs = ab.load_forecasts(r3.Parts(out, None), CFG, run2)
    s = run2.series
    sc = r2.Scored(np.arange(s["label"].size), s["label"], s["hour"], s["hours"], s["count"])
    probs = {a: r3.arm_probabilities(fcs[a], 1e-3) for a in ab.ABLATIONS}
    losses = {a: stats.per_row_losses(probs[a], sc.label) for a in ab.ABLATIONS}
    return probs, {a: r2.hourly(v.log_loss, sc) for a, v in losses.items()}, {a: r2.hourly(v.brier, sc) for a, v in losses.items()}


def _copy_tree(src: Path, dst: Path) -> None:
    for p in sorted(src.rglob("*")):
        if p.is_file():
            (dst / p.relative_to(src)).parent.mkdir(parents=True, exist_ok=True)
            (dst / p.relative_to(src)).write_bytes(p.read_bytes())


# --- The configuration ------------------------------------------------------------------------------------


def test_the_arms_keep_the_protocols_order_and_the_registered_run_is_a_prefix():
    assert ab.ABLATIONS == ("enc-ols-gate", "enc-ols-conv", "enc-ols-brier") and ab.H6_ARM == "enc-ols-brier"
    assert ab.AblationsConfig().registered and dataclasses.replace(ab.AblationsConfig(), device="cpu").registered
    assert ab.AblationsConfig(arms=("enc-ols-gate",)).registered and ab.AblationsConfig(arms=("enc-ols-gate", "enc-ols-conv")).registered
    assert not ab.AblationsConfig(arms=("enc-ols-brier",)).registered  # H6 before the LFM3 arms: out of order
    assert not ab.AblationsConfig(brier_weight=0.5).registered and not CFG.registered
    with pytest.raises(ValueError, match="order"):
        ab.AblationsConfig(arms=("enc-ols-conv", "enc-ols-gate"))
    with pytest.raises(ValueError, match="subset"):
        ab.AblationsConfig(arms=("enc-ols",))
    assert ab.AblationsConfig().variants_before == 21 and ab.AblationsConfig().h6_ece_ratio == 0.8


def test_the_exact_parameter_counts():
    assert ab.parameters(ab.AblationsConfig()) == {"enc-ols": 21003, "enc-ols-gate": 23051, "enc-ols-conv": 20007, "enc-ols-brier": 21003}


def test_each_fit_is_enc_ols_but_for_its_one_change():
    cfg = ab.AblationsConfig()
    for arm, key in ab.CHANGED_KEY.items():
        for seed in cfg.seeds:
            for year in cfg.years:
                fc = ab.fit_config(cfg, arm, seed, year)
                assert ab.one_change(arm, fc, ab.base_fit_config(cfg, seed, year)) == [key]
                assert ab.base_fit_config(cfg, seed, year).to_json() == r3.fit_config(r3.Report3Config(), "enc-ols", seed, year).to_json()
    assert json.loads(ab.fit_config(cfg, "enc-ols-brier", 1, 2019).to_json())["brier_weight"] == 1.0
    with pytest.raises(ab.BindingRefused, match="seed"):  # any other difference is refused
        ab.one_change("enc-ols-gate", ab.fit_config(cfg, "enc-ols-gate", 2, 2019), ab.base_fit_config(cfg, 1, 2019))
    other = dataclasses.replace(cfg, fit=(("epochs", 5),))
    with pytest.raises(ab.BindingRefused, match="epochs"):
        ab.one_change("enc-ols-conv", ab.fit_config(other, "enc-ols-conv", 1, 2019), ab.base_fit_config(cfg, 1, 2019))


def test_everything_else_must_be_report3s():
    ab.check_against_report3(CFG, CFG3)
    for change in ({"seeds": (1, 2, 3)}, {"years": (2019, 2020)}, {"encoder": (("d_model", 16), ("n_heads", 2))}, {"fit": (("epochs", 3),)}):
        with pytest.raises(ab.BindingRefused):
            ab.check_against_report3(dataclasses.replace(CFG, **change), CFG3)


# --- The run against a Report n°3 run -----------------------------------------------------------------


def test_the_ablations_are_fitted_scored_and_described_against_report3s_enc_ols(full, world):
    out, m = full
    run2, _, out3, sha3 = world
    report3 = json.loads((out3 / "report3.json").read_text(encoding="utf-8"))
    assert set(m["arms"]) == set(ab.ABLATIONS) and m["not_run"] == []
    assert m["enc_ols"]["seeds"] == report3["arms"]["enc-ols"]["seeds"] and m["enc_ols"]["ece"] == report3["arms"]["enc-ols"]["ece"]
    assert [p["key"] for p in m["report3"]["enc_ols_parts"]] == ["fits/enc-ols/s1/2019", "fits/enc-ols/s2/2019"]
    assert m["report3"]["series_sha256"] == sha3 and m["report2"]["series_sha256"] == run2.sha256
    assert m["variants"] == {"before": 21, "this_report": 3, "total": 24}
    assert m["h6"]["status"] in ("holds", "does not hold") and not m["registered"]
    for arm in ab.ABLATIONS:
        assert m["comparisons"][arm]["b"] == "enc-ols" and m["arms"][arm]["parameters"] == ab.parameters(CFG)[arm]
        assert {f["seed"] for f in m["fits"] if f["arm"] == arm} == {1, 2}
    assert m["comparisons"]["enc-ols-brier"]["kind"] == "h6" and m["comparisons"]["enc-ols-gate"]["kind"] == "described"
    # the series: the ablations' ensembles at Report n°2's scored rows, written as Report n°3 writes its own
    probs, ll, br = _ensembles(out, run2)
    series = r3.series_out(run2, ab.ABLATIONS, probs, ll, br)
    assert list(series["arms"]) == list(ab.ABLATIONS) and series["probs"].shape == (3, run2.series["label"].size, 3)
    r2.write_npz(out.parent / "rebuilt.npz", series)
    assert r2.sha256_file(out.parent / "rebuilt.npz") == r2.sha256_file(out / ab.SERIES_FILE) == m["series"]["sha256"]
    text = (out / ab.REPORT_FILE).read_text(encoding="utf-8")
    assert "NOT THE REGISTERED RUN" in text and "## H6" in text and "enc-ols (Report n°3)" in text


def test_h6s_numbers_are_its_rule_on_the_scored_series(full, world):
    out, m = full
    run2, _, out3, sha3 = world
    h6, c = m["h6"], m["comparisons"]["enc-ols-brier"]
    probs, ll, _ = _ensembles(out, run2)
    p_b, ll_b = probs["enc-ols-brier"], ll["enc-ols-brier"]
    p_o = r3.arm_probabilities(r3.load_forecasts(r3.Parts(out3, None), CFG3, run2)["enc-ols"], 1e-3)
    sc = r2.Scored(np.arange(run2.series["label"].size), run2.series["label"], run2.series["hour"], run2.series["hours"], run2.series["count"])
    ll_o = r2.hourly(stats.per_row_losses(p_o, sc.label).log_loss, sc)
    y = run2.series["label"]
    assert h6["ece"]["brier"] == pytest.approx(stats.ece(p_b, y, 10), rel=1e-9) and h6["ece"]["enc_ols"] == pytest.approx(stats.ece(p_o, y, 10), rel=1e-9)
    assert h6["log_loss"]["difference"] == pytest.approx(float((ll_b - ll_o).mean()), rel=1e-12)
    assert h6["log_loss"]["tolerance"] == max(h6["log_loss"]["seed_range"], h6["log_loss"]["dm_se"])
    assert h6["log_loss"]["seed_range"] == m["enc_ols"]["seeds"]["range"] and h6["log_loss"]["dm_se"] == c["dm_se"]
    met = h6["ece"]["ratio"] <= 0.8 and h6["ece"]["upper_95"] < 1.0
    assert h6["ece"]["met"] == met and h6["holds"] == (met and h6["log_loss"]["difference"] <= h6["log_loss"]["tolerance"])


def test_check_passes_and_fails_on_one_changed_digit(full, world, tmp_path, capsys):
    out, _ = full
    run2, _, out3, sha3 = world
    run3 = ab.read_report3(out3, sha3)
    assert ab.check(out, run2, run3, PROV) == 0
    copy = out.parent / "ablations-tampered"
    _copy_tree(out, copy)
    path = copy / ab.JSON_FILE
    text = path.read_text(encoding="utf-8")
    i = text.index('"difference": ') + len('"difference": ') + 4
    path.write_text(text[:i] + ("1" if text[i] != "1" else "2") + text[i + 1 :], encoding="utf-8")
    assert ab.check(copy, run2, run3, PROV) == 1
    assert ab.check(out, run2, run3, {**PROV, "code": {"sha256": "e" * 64, "files": 1}}) == 1  # another code: reported
    capsys.readouterr()


def test_a_resumed_run_gives_the_same_bytes_and_a_changed_config_refuses(full, world, runs_root):
    straight, _ = full
    run2, inputs, out3, sha3 = world
    run3 = ab.read_report3(out3, sha3)
    out = runs_root / "ablations-resumed"
    with pytest.raises(r3.Interrupted):
        ab.run(inputs, run2, run3, CFG, out, "fits", prov=PROV, arms=("enc-ols-gate",), stop_after=1)
    ab.run(inputs, run2, run3, CFG, out, "fits", prov=PROV, arms=("enc-ols-gate",))
    assert _part_files(out) == _part_files(straight, "enc-ols-gate")
    with pytest.raises(r3.ResumeRefused, match="code_sha256"):
        ab.run(inputs, run2, run3, CFG, out, "fits", prov={**PROV, "code": {"sha256": "e" * 64, "files": 1}})
    with pytest.raises(r3.ResumeRefused, match="config"):
        ab.run(inputs, run2, run3, dataclasses.replace(CFG, brier_weight=2.0), out, "fits", prov=PROV)
    # scoring the arms that ran: the first of the protocol's order; H6 not run
    m = ab.run(None, run2, run3, dataclasses.replace(CFG, arms=("enc-ols-gate",)), out, "score", prov=PROV)
    assert m["not_run"] == ["enc-ols-conv", "enc-ols-brier"] and m["h6"]["status"] == "not run" and m["variants"]["total"] == 22
    with pytest.raises(r3.PairingRefused, match="no verified part"):
        ab.run(None, run2, run3, CFG, out, "score", prov=PROV)


# --- The inventory: every arm in the folder (audit pass 4h, M1) ------------------------------------------------


GATE_CONV = dataclasses.replace(CFG, arms=("enc-ols-gate", "enc-ols-conv"))


def test_an_arm_fitted_whole_and_left_unscored_refuses_the_score(full, world, runs_root, capsys):
    out, _ = full
    run2, _, out3, sha3 = world
    run3 = ab.read_report3(out3, sha3)
    copy = runs_root / "ablations-unscored"
    _copy_tree(out, copy)
    with pytest.raises(ab.InventoryRefused, match=r"enc-ols-brier: every one of its 2 parts is sealed .* score it \(--arms enc-ols-gate enc-ols-conv enc-ols-brier\)"):
        ab.run(None, run2, run3, GATE_CONV, copy, "score", prov=PROV)
    assert (copy / ab.JSON_FILE).read_bytes() == (out / ab.JSON_FILE).read_bytes()  # nothing written
    # --check sees it too, on a run whose configuration scored two arms
    path = copy / "config.json"
    rec = json.loads(path.read_text(encoding="utf-8"))
    rec["config"]["arms"] = list(GATE_CONV.arms)
    r2._write_json(path, rec)
    assert ab.check(copy, run2, run3, PROV) == 1
    assert "every one of its 2 parts is sealed" in capsys.readouterr().out


def test_an_arm_fitted_in_part_is_reported_as_such_never_as_not_run_and_is_not_a_variant(full, world, runs_root, capsys):
    out, _ = full
    run2, _, out3, sha3 = world
    run3 = ab.read_report3(out3, sha3)
    copy = runs_root / "ablations-in-part"
    _copy_tree(out, copy)
    for p in sorted((copy / "parts" / "fits" / "enc-ols-brier" / "s2").rglob("*"), reverse=True):  # one of enc-ols-brier's two parts
        p.unlink() if p.is_file() else p.rmdir()
    m = ab.run(None, run2, run3, GATE_CONV, copy, "score", prov=PROV)
    assert m["fitted_in_part"] == {"enc-ols-brier": {"parts": 1, "of": 2}} and m["not_run"] == []
    assert set(m["arms"]) == {"enc-ols-gate", "enc-ols-conv"} and "enc-ols-brier" not in m["comparisons"]
    assert m["h6"] == {"status": "not run", "holds": False} and "h6_seed_split" not in m
    assert m["variants"] == {"before": 21, "this_report": 2, "total": 23} and all(f["arm"] != "enc-ols-brier" for f in m["fits"])
    assert dataclasses.replace(ab.AblationsConfig(), arms=GATE_CONV.arms).registered  # registered keeps its rule
    text = (copy / ab.REPORT_FILE).read_text(encoding="utf-8")
    assert "Not run: enc-ols-brier (fitted in part, 1 of 2 parts, not scored)." in text
    assert "| enc-ols-brier | fitted in part (1 of 2 parts), not scored | - |" in text
    assert "enc-ols-brier was fitted in part (1 of 2 parts) and not scored: H6 is not run." in text
    assert ab.check(copy, run2, run3, PROV) == 0
    # the arm with no part at all is not run
    for p in sorted((copy / "parts" / "fits" / "enc-ols-brier").rglob("*"), reverse=True):
        p.unlink() if p.is_file() else p.rmdir()
    m = ab.run(None, run2, run3, GATE_CONV, copy, "score", prov=PROV)
    assert m["fitted_in_part"] == {} and m["not_run"] == ["enc-ols-brier"] and m["variants"]["total"] == 23
    capsys.readouterr()


def test_a_part_that_does_not_verify_refuses_the_score_whatever_its_arm(full, world, runs_root):
    out, _ = full
    run2, _, out3, sha3 = world
    run3 = ab.read_report3(out3, sha3)
    copy = runs_root / "ablations-unverified"
    _copy_tree(out, copy)
    for p in sorted((copy / "parts" / "fits" / "enc-ols-brier" / "s2").rglob("*"), reverse=True):
        p.unlink() if p.is_file() else p.rmdir()
    part = copy / "parts" / ab.part_key("enc-ols-brier", 1, 2019) / "forecast.safetensors"  # an arm not scored
    data = part.read_bytes()
    part.write_bytes(data[:-3] + bytes([data[-3] ^ 1]) + data[-2:])
    with pytest.raises(r3.PartRefused, match="enc-ols-brier/s1/2019/forecast.safetensors: fails its digest"):
        ab.run(None, run2, run3, GATE_CONV, copy, "score", prov=PROV)
    part.write_bytes(data)
    stray = copy / "parts" / "fits" / "enc-ols-brier" / "s7" / "2019" / "part.json"  # a seed this run never fits
    stray.parent.mkdir(parents=True)
    stray.write_text("{}", encoding="utf-8")
    with pytest.raises(r3.PartRefused, match="s7/2019/part.json: not a file of a part"):
        ab.run(None, run2, run3, GATE_CONV, copy, "score", prov=PROV)


def test_the_fits_take_the_arms_in_the_protocols_order(full, world, runs_root):
    out, _ = full
    run2, inputs, out3, sha3 = world
    run3 = ab.read_report3(out3, sha3)
    folder = runs_root / "ablations-order"
    for arms, match in ((("enc-ols-conv",), "not a prefix .* enc-ols-gate, which comes first, has 0 of its 2 parts"),
                        (("enc-ols-gate", "enc-ols-brier"), "not a prefix .* enc-ols-conv, which comes first, has 0 of its 2 parts"),
                        (("enc-ols-conv", "enc-ols-gate"), "not in the protocol's order")):  # fmt: skip
        with pytest.raises(ab.InventoryRefused, match=match):
            ab.run(inputs, run2, run3, CFG, folder, "fits", prov=PROV, arms=arms)
    assert not (folder / "parts" / "fits").exists()  # refused before any fit
    # enc-ols-gate fitted in part: enc-ols-conv still waits; fitted whole: enc-ols-conv may run alone
    _copy_tree(out / "parts" / "fits" / "enc-ols-gate" / "s1", folder / "parts" / "fits" / "enc-ols-gate" / "s1")
    with pytest.raises(ab.InventoryRefused, match="has 1 of its 2 parts sealed"):
        ab.run(inputs, run2, run3, CFG, folder, "fits", prov=PROV, arms=("enc-ols-conv",))
    _copy_tree(out / "parts" / "fits" / "enc-ols-gate" / "s2", folder / "parts" / "fits" / "enc-ols-gate" / "s2")
    with pytest.raises(r3.Interrupted):  # past the order check, stopped before its first fit
        ab.run(inputs, run2, run3, CFG, folder, "fits", prov=PROV, arms=("enc-ols-conv",), stop_after=0)
    assert not (folder / "parts" / "fits" / "enc-ols-conv").exists()


# --- A Brier part, read back (audit pass 4h, m6) --------------------------------------------------------------


def test_a_brier_part_loads_as_its_brier_config_and_predicts_its_saved_forecasts_to_the_bit(full, world):
    import types

    out, _ = full
    _, inputs, _, _ = world
    parts = r3.Parts(out, None)
    key = ab.part_key("enc-ols-brier", 1, 2019)
    state, std, fc = ab.load_fit(parts, key, CFG)
    want = ab.fit_config(CFG, "enc-ols-brier", 1, 2019)
    assert type(fc) is BrierFitConfig and fc == want and fc.to_json() == want.to_json()
    arrays, _ = checkpoint.from_bytes(parts.get(f"{key}/fit.safetensors"))
    saved = ab.read_forecast(parts, key)
    with deterministic():
        system = EncoderSystem(inputs.data, fc, device="cpu")
        again = system.forecast(types.SimpleNamespace(config=fc, state=state, standardizer=std, climatology=arrays["climatology"]), inputs.years[2019])
    assert np.array_equal(again["raw"], saved["raw"]) and np.array_equal(again["fallback"], saved["fallback"])


# --- The binding to Report n°3 -------------------------------------------------------------------------------


def test_a_wrong_digest_or_a_folder_outside_the_runs_root_is_refused(world, tmp_path):
    _, _, out3, sha3 = world
    with pytest.raises(ab.BindingRefused, match="SHA-256"):
        ab.read_report3(out3, "0" * 64)
    from olsprime.bench.power import SeriesRefused

    outside = tmp_path / "elsewhere"
    _copy_tree(out3, outside)
    with pytest.raises(SeriesRefused, match="runs root"):
        ab.read_report3(outside, sha3)


def test_a_resealed_enc_ols_part_is_refused(full, world, runs_root):
    """The part verifies against its own folder, but it is not the part report3.json records."""
    out, _ = full
    run2, _, out3, sha3 = world
    forged = runs_root / "report3-forged"
    _copy_tree(out3, forged)
    parts = r3.Parts(forged, None)
    key = "fits/enc-ols/s2/2019"
    rec = parts.get_json(f"{key}/part.json")
    parts.put_json(f"{key}/part.json", {**rec, "kept_epoch": 3 - rec["kept_epoch"]})
    assert r3.verified_part(parts, key, CFG3) is not None  # its folder vouches for it
    run3 = ab.read_report3(forged, sha3)
    with pytest.raises(ab.BindingRefused, match="kept_epoch"):
        ab.run(None, run2, run3, CFG, out, "score", prov=PROV)


def test_a_report3_json_with_another_seed_log_loss_is_refused(full, world, runs_root):
    out, _ = full
    run2, _, out3, sha3 = world
    forged = runs_root / "report3-seeds"
    _copy_tree(out3, forged)
    path = forged / "report3.json"
    rep = json.loads(path.read_text(encoding="utf-8"))
    rep["arms"]["enc-ols"]["seeds"]["log_loss"]["1"] += 1e-12
    r2._write_json(path, rep)
    run3 = ab.read_report3(forged, sha3)  # report3.json still records the series' digest
    with pytest.raises(ab.BindingRefused, match="each seed's log-loss"):
        ab.run(None, run2, run3, CFG, out, "score", prov=PROV)


def test_a_forged_enc_ols_forecast_resealed_with_its_whole_chain_is_refused_by_the_series_rebuild(full, world, runs_root):
    """One row of one enc-ols forecast changed, then every record above it rewritten to agree: the part's digests, its
    entry in report3.json's fits and enc-ols's numbers there. Only the rebuild of Report n°3's series.npz from the bound
    parts, hashed against the digest given, can see it (audit pass 4h, m5)."""
    out, _ = full
    run2, _, out3, sha3 = world
    forged = runs_root / "report3-rebuilt"
    _copy_tree(out3, forged)
    parts = r3.Parts(forged, None)
    key = r3.part_key("enc-ols", 1, 2019)
    arrays, meta = checkpoint.from_bytes(parts.get(f"{key}/forecast.safetensors"))
    raw = np.array(arrays["raw"])
    i = int(np.flatnonzero(~arrays["fallback"].astype(bool))[0])
    raw[i] = raw[i][[1, 2, 0]]  # still a forecast: the same three probabilities, moved between the classes
    assert not np.array_equal(raw[i], arrays["raw"][i])
    sha = parts.put(f"{key}/forecast.safetensors", checkpoint.to_bytes({**arrays, "raw": raw}, meta))
    parts.put_json(f"{key}/part.json", {**parts.get_json(f"{key}/part.json"), "forecast_sha256": sha})
    assert r3.verified_part(parts, key, CFG3) is not None  # the folder vouches for it
    rep = json.loads((forged / "report3.json").read_text(encoding="utf-8"))
    entry = [f for f in rep["fits"] if (f["arm"], f["seed"], f["year"]) == ("enc-ols", 1, 2019)]
    assert len(entry) == 1
    entry[0]["forecast_sha256"] = sha
    s = run2.series
    sc = r2.Scored(np.arange(s["label"].size), s["label"], s["hour"], s["hours"], s["count"])
    fc = r3.load_forecasts(parts, CFG3, run2)["enc-ols"]
    p = r3.arm_probabilities(fc, 1e-3)
    losses = stats.per_row_losses(p, sc.label)
    arm = rep["arms"]["enc-ols"]
    arm["seeds"] = json.loads(json.dumps(r2._clean(r3.per_seed(fc, sc, 1e-3))))
    arm["log_loss"]["estimate"] = float(r2.hourly(losses.log_loss, sc).mean())
    arm["brier"]["estimate"] = float(r2.hourly(losses.brier, sc).mean())
    arm["ece"]["estimate"] = ab.ece_estimate(p, sc, r3.rule_config(run2.config).ece_bins)
    assert arm["seeds"] != json.loads((out3 / "report3.json").read_text(encoding="utf-8"))["arms"]["enc-ols"]["seeds"]
    r2._write_json(forged / "report3.json", rep)
    run3 = ab.read_report3(forged, sha3)  # report3.json still records the series' digest
    copy = runs_root / "ablations-rebuilt"
    _copy_tree(out, copy)
    with pytest.raises(ab.BindingRefused, match="rebuilt from its bound parts"):
        ab.run(None, run2, run3, CFG, copy, "score", prov=PROV)


def test_a_second_report2_run_is_not_the_one_report3_paired_with(full, world, runs_root):
    out, _ = full
    run2, _, out3, sha3 = world
    _, _, series, sha = r3.synthetic_report2(runs_root / "report2-second")
    second = r3.read_report2(series, sha)
    assert second.sha256 != run2.sha256
    run3 = ab.read_report3(out3, sha3)
    with pytest.raises(ab.BindingRefused, match="paired with Report n°2's series"):
        ab.run(None, second, run3, CFG, out, "score", prov=PROV)


def test_the_synthetic_mode_rebuilds_report3s_synthetic_panel(runs_root):
    """``--synthetic`` reads a ``report3 --synthetic`` folder: the panel it rebuilds is that run's, by Report n°2's fingerprint."""
    panel, _, series, sha = r3.synthetic_report2(runs_root / "r3-synthetic" / "report2-synthetic")
    run2 = r3.read_report2(series, sha)
    rebuilt, bars = ab.synthetic_panel(run2)
    assert r3.fingerprint(rebuilt) == r3.fingerprint(panel) == run2.fingerprint and len(bars) == r3.SMOKE_MEMBERS
    with pytest.raises(SystemExit):
        ab.main(["--synthetic", "--report3", str(runs_root / "r3-synthetic"), "--sha256", "0" * 64, "--series", str(series)])


# --- H6's rule and its bootstrap --------------------------------------------------------------------------------


def _ratio(ea: float, eb: float, upper: float) -> dict:
    return {"ece_a": ea, "ece_b": eb, "estimate": ea / eb, "upper": upper, "low": 0.0, "high": upper, "block": 3}


@pytest.mark.parametrize(("ea", "upper", "diff", "se", "rng", "holds", "why"), [
    (0.008, 0.95, 0.001, 0.002, 0.0005, True, "both met, tolerance from the DM standard error"),
    (0.008, 0.95, 0.001, 0.0002, 0.0015, True, "both met, tolerance from the seed range"),
    (0.0081, 0.95, 0.0, 0.002, 0.0, False, "ECE ratio 0.81 > 0.8"),
    (0.008, 1.0, 0.0, 0.002, 0.0, False, "upper bound not below 1"),
    (0.008, 0.95, 0.0021, 0.002, 0.001, False, "log-loss above the tolerance"),
    (0.008, 0.95, 0.002, 0.002, 0.001, True, "diff equal to the tolerance holds"),
    (0.008, 0.95, 0.0015, 0.0002, 0.0015, True, "diff equal to the seed range holds"),
])  # fmt: skip
def test_h6_holds_only_if_both_conditions_hold(ea, upper, diff, se, rng, holds, why):
    out = ab.h6_verdict(_ratio(ea, 0.01, upper), {"mean_diff": diff, "dm_se": se}, rng, ab.AblationsConfig())
    assert out["holds"] is holds, why
    assert out["log_loss"]["tolerance"] == max(rng, se)
    undefined = ab.h6_verdict({**_ratio(0.0, 1.0, 0.5), "ece_b": 0.0, "estimate": float("nan")}, {"mean_diff": 0.0, "dm_se": se}, rng, ab.AblationsConfig())
    assert not undefined["holds"] and undefined["status"].startswith("undefined")


def test_each_replicate_of_the_ece_ratio_is_the_ratio_of_the_ecess_of_the_resampled_rows():
    rng = np.random.default_rng(0)
    hours, per = 400, 5
    hour = np.repeat(np.arange(hours), per)
    y = rng.integers(0, 3, hour.size)
    p_a = prob_map(rng.dirichlet([2, 3, 2], hour.size), 1e-3)
    # p_b leans, hour by hour, toward a confident forecast of the wrong class by a weight that follows an AR(1) over the
    # hours: its hourly Brier has a longer dependence than p_a's, so the two arms' Politis-White blocks differ
    shock = rng.normal(size=hours)
    level = np.zeros(hours)
    for h in range(1, hours):
        level[h] = 0.97 * level[h - 1] + shock[h]
    lean = (1.0 / (1.0 + np.exp(-level)))[hour, None]
    wrong = 0.05 + 0.85 * np.eye(3)[(y + 1) % 3]
    p_b = prob_map((1 - lean) * (0.5 * p_a + 0.5 * rng.dirichlet([1, 1, 1], hour.size)) + lean * wrong, 1e-3)
    sc = r2.Scored(np.arange(hour.size), y, hour, np.arange(hours) * 3_600_000, np.full(hours, per))
    br_a, br_b = (r2.hourly(stats.per_row_losses(p, y).brier, sc) for p in (p_a, p_b))
    assert r2._block(br_b) > r2._block(br_a), (r2._block(br_a), r2._block(br_b))
    rule = r2.Report2Config(n_boot=50)
    out = ab.ece_ratio_interval(p_a, p_b, sc, br_a, br_b, rule, "t")
    assert out["estimate"] == pytest.approx(stats.ece(p_a, y, 10) / stats.ece(p_b, y, 10), rel=1e-12)
    assert out["block"] == max(r2._block(br_a), r2._block(br_b)) == r2._block(br_b)
    swapped = ab.ece_ratio_interval(p_b, p_a, sc, br_b, br_a, rule, "t")  # the larger block whichever arm comes first
    assert swapped["block"] == out["block"] and swapped["estimate"] == pytest.approx(1 / out["estimate"], rel=1e-12)
    # the same replicates, recomputed the slow way: every row of every drawn hour, then stats.ece
    idx = np.concatenate(list(r2._chunks(hours, out["block"], rule.n_boot, r2._seed(rule, "t"))))
    slow = []
    for row in idx:
        rows = np.concatenate([np.flatnonzero(hour == h) for h in row])
        slow.append(stats.ece(p_a[rows], y[rows], 10) / stats.ece(p_b[rows], y[rows], 10))
    lo, hi = np.quantile(slow, [0.025, 0.975])
    assert out["low"] == pytest.approx(lo, rel=1e-9) and out["high"] == pytest.approx(hi, rel=1e-9)
    assert out["upper"] == pytest.approx(np.quantile(slow, 0.95), rel=1e-9)


# --- H6's seed-split control: a description with no verdict -------------------------------------------------------


def _calibrated(seed: int = 0, hours: int = 400, per: int = 25) -> tuple[np.ndarray, r2.Scored]:
    """Forecasts whose labels are drawn from them (calibrated), over hours of ``per`` rows."""
    rng = np.random.default_rng(seed)
    hour = np.repeat(np.arange(hours), per)
    p = rng.dirichlet([2, 3, 2], hour.size)
    y = (rng.random(hour.size)[:, None] > np.cumsum(p, axis=1)).sum(axis=1)
    return p, r2.Scored(np.arange(hour.size), y, hour, np.arange(hours) * 3_600_000, np.full(hours, per))


def _sharpened(p: np.ndarray, temperature: float) -> np.ndarray:
    q = p ** (1.0 / temperature)
    return q / q.sum(axis=1, keepdims=True)


def test_two_identical_seeds_give_a_ratio_of_exactly_one_and_the_condition_holds_in_neither_direction():
    p, sc = _calibrated()
    fc = r3.Forecasts({1: p, 2: p.copy()}, np.zeros(p.shape[0], dtype=bool))
    out = ab.seed_split(fc, sc, r2.Report2Config(n_boot=50), 1e-3, ab.AblationsConfig())
    assert [(q["seed_i"], q["seed_j"]) for q in out["pairs"]] == [(1, 2), (2, 1)] and out["of"] == 2
    for q in out["pairs"]:
        assert q["ratio"] == 1.0 and q["interval_95"] == [1.0, 1.0] and q["upper_95"] == 1.0
        assert q["ece_i"] == q["ece_j"] and not q["ece_condition_holds"]
    assert out["holds_in"] == 0 and "no verdict" in out["kind"]


def test_a_sharpened_seed_moves_its_ratio_away_from_one_in_the_right_direction():
    """Seed 3's forecasts sharpened with a temperature of 0.7: over-confident, so its ECE is the larger."""
    p, sc = _calibrated()
    fc = r3.Forecasts({1: p, 3: _sharpened(p, 0.7)}, np.zeros(p.shape[0], dtype=bool))
    rule = r2.Report2Config(n_boot=50)
    out = ab.seed_split(fc, sc, rule, 1e-3, ab.AblationsConfig())
    pair = {(q["seed_i"], q["seed_j"]): q for q in out["pairs"]}
    calibrated, sharp = pair[(1, 3)], pair[(3, 1)]
    assert calibrated["ece_i"] == pytest.approx(stats.ece(prob_map(p, 1e-3), sc.label, 10), rel=1e-12)
    assert calibrated["ratio"] < 1 < sharp["ratio"] and calibrated["ratio"] == pytest.approx(1 / sharp["ratio"], rel=1e-12)
    assert calibrated["ece_condition_holds"] and not sharp["ece_condition_holds"] and out["holds_in"] == 1
    # each pair is H6's machinery with the seeds' own tags, floors and blocks
    p1, p3 = prob_map(p, 1e-3), prob_map(_sharpened(p, 0.7), 1e-3)
    br1, br3 = (r2.hourly(stats.per_row_losses(x, sc.label).brier, sc) for x in (p1, p3))
    direct = ab.ece_ratio_interval(p3, p1, sc, br3, br1, rule, "ece_ratio", "enc-ols seed 3", "enc-ols seed 1")
    assert sharp["seed_tag"] == ["ece_ratio", "enc-ols seed 3", "enc-ols seed 1"]
    assert (sharp["ratio"], sharp["interval_95"], sharp["upper_95"], sharp["block"]) == (direct["estimate"], [direct["low"], direct["high"]],
                                                                                          direct["upper"], direct["block"])  # fmt: skip


def test_the_seed_split_control_runs_on_report3s_registered_seeds_beside_h6(full, world):
    out, m = full
    run2, _, out3, _ = world
    split = m["h6_seed_split"]
    assert split["seeds"] == list(CFG.seeds) == [int(s) for s in m["enc_ols"]["seeds"]["log_loss"]]
    assert [(q["seed_i"], q["seed_j"]) for q in split["pairs"]] == [(1, 2), (2, 1)]
    assert [q["seed_tag"] for q in split["pairs"]] == [["ece_ratio", "enc-ols seed 1", "enc-ols seed 2"], ["ece_ratio", "enc-ols seed 2", "enc-ols seed 1"]]
    raw = r3.load_forecasts(r3.Parts(out3, None), CFG3, run2)["enc-ols"].raw  # Report n°3's per-seed forecasts, each floored on its own
    for q in split["pairs"]:
        assert q["ece_i"] == stats.ece(prob_map(raw[q["seed_i"]], 1e-3), run2.series["label"], 10)
        assert q["ece_condition_holds"] == (q["ratio"] <= 0.8 and q["upper_95"] < 1.0)
    assert m["variants"]["this_report"] == 3  # a control, not a variant
    text = (out / ab.REPORT_FILE).read_text(encoding="utf-8")
    assert "### H6's seed-split control" in text and "A control with no verdict" in text and "smaller than a single seed's" in text


def test_h6s_verdict_is_the_same_with_the_seed_split_control_and_without_it(full, world, runs_root, monkeypatch):
    out, m = full
    run2, _, out3, sha3 = world
    run3 = ab.read_report3(out3, sha3)
    copy = runs_root / "ablations-no-control"
    _copy_tree(out, copy)
    monkeypatch.setattr(ab, "seed_split", lambda fc, sc, rcfg, floor, cfg: {"seeds": sorted(fc.raw), "pairs": [], "holds_in": 0, "of": 0})
    without = ab.run(None, run2, run3, CFG, copy, "score", prov=PROV)
    assert without["h6"] == m["h6"] and without["comparisons"] == m["comparisons"] and without["arms"] == m["arms"]
    assert without["variants"] == m["variants"] and without["h6_seed_split"] != m["h6_seed_split"]


def test_check_reproduces_the_seed_split_control_byte_for_byte(full, world, capsys):
    out, m = full
    run2, _, out3, sha3 = world
    run3 = ab.read_report3(out3, sha3)
    assert ab.check(out, run2, run3, PROV) == 0
    path = out / ab.JSON_FILE
    text = path.read_text(encoding="utf-8")
    at = text.index('"upper_95": ', text.index('"h6_seed_split"')) + len('"upper_95": ') + 4
    assert text[at].isdigit()
    try:
        path.write_text(text[:at] + str((int(text[at]) + 1) % 10) + text[at + 1 :], encoding="utf-8", newline="\n")
        assert ab.check(out, run2, run3, PROV) == 1
        assert "ablations.json" in capsys.readouterr().out
    finally:
        path.write_text(text, encoding="utf-8", newline="\n")
    assert ab.check(out, run2, run3, PROV) == 0
    capsys.readouterr()
