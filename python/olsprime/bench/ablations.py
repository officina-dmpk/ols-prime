"""LFM3's ablations and H6, against Report n°3's ``enc-ols`` (``docs/PROTOCOL.md``, "LFM3's ablations and H6, if time remains").

Usage::

    uv run --no-sync python -m olsprime.bench.ablations --report3 <Report n°3 run> --sha256 <its series.npz digest>
        --series <Report n°2 series.npz> --report2-sha256 <its digest> [--out DIR] [--stage fits|score|all]
        [--arms ARM ...] [--device cuda|cpu] [--driver VERSION]
    uv run --no-sync python -m olsprime.bench.ablations --report3 ... --sha256 ... --series ... --report2-sha256 ... --check DIR
    uv run --no-sync python -m olsprime.bench.ablations --synthetic --report3 <a report3 --synthetic folder> --sha256 <...> [--out DIR]

Each arm is ``enc-ols`` with one change (:data:`ABLATIONS`), fitted with three seeds on Report n°3's six yearly fits:

- ``enc-ols-gate``: a sigmoid gate per OLS head (:class:`olsprime.models.encoder.Attention`);
- ``enc-ols-conv``: the first block's attention replaced by a gated short convolution
  (:class:`olsprime.models.encoder.ShortConv`);
- ``enc-ols-brier``, H6: the loss is the cross-entropy plus the Brier score, weight 1
  (:class:`olsprime.train.fit.BrierFitConfig`).

Every other choice is ``enc-ols``'s: the configuration is refused unless its seeds, years and overrides are Report
n°3's, and each fit's saved configuration must differ from ``enc-ols``'s of the same seed and year in exactly its one
change (:func:`one_change`). Each ablation that is scored counts as one variant.

``enc-ols`` is never refitted. Its per-seed forecasts are read from Report n°3's run folder, each part verified by
:func:`olsprime.bench.report3.verified_part` and bound to ``report3.json``'s record of it (its checkpoint's and
forecast's digests, its row count and its epoch kept, as ``explain head`` binds a part), ``report3.json`` itself bound
by the digest of Report n°3's ``series.npz`` given on the command line. That ``series.npz`` is then rebuilt from the
bound parts of Report n°3's three arms, as its score builds it, and must hash to the same digest: so ``enc-ols``'s
ensemble and hourly series are Report n°3's to the bit, without opening the archive. Each seed's log-loss, the mean
log-loss, Brier score and ECE must equal ``report3.json``'s; otherwise the score is refused (:class:`BindingRefused`).

The stages:

- **fits** (GPU, WSL2): the panel rebuilt as Report n°3's fits read it (:func:`olsprime.bench.report3.load_panel`,
  checked against Report n°2's fingerprint and paired with its scored rows), then one part per (arm, seed, year)
  under ``<out>/parts/fits/<arm>/s<seed>/<year>/``, written and resumed exactly as Report n°3's
  (:class:`olsprime.bench.report3.Parts`). ``--arms`` restricts the stage, to a prefix of the protocol's order unless
  every part of each earlier arm is already sealed in the folder: "if time remains" fits the arms in that order
  (:func:`check_fit_order`).
- **score** (CPU, deterministic; WSL2, see below): Report n°2's statistics, unchanged, on Report n°2's scored rows
  paired hour by hour: each arm's log-loss, Brier, Brier skill and ECE with their intervals, each against ``enc-ols``
  (DM with HLN, the stationary bootstrap), each seed's log-loss; and H6 by its registered rule (:func:`h6_verdict`),
  with the paired bootstrap of the ratio of the two ECEs (:func:`ece_ratio_interval`). Beside H6, a control with no
  verdict: H6's ECE condition between single seeds of ``enc-ols`` (:func:`seed_split`). ``--arms`` names the arms
  scored. The score takes an inventory of every arm in the folder (:func:`inventory`): a part that does not verify
  refuses it, whatever its arm; an arm not scored whose parts are all sealed refuses it (score that arm); an arm not
  scored with some parts is reported as fitted in part and is not a variant; an arm with no part is not run.

The score stage is bound to the platform of Report n°3's score, WSL2: it rebuilds Report n°3's ``series.npz`` from
the parts and hashes it, and ``np.log``'s last bits differ between Windows and WSL2, so on another platform the
rebuild does not hash to the digest and the score is refused, as Report n°3's own ``--check`` would be.

Outputs, to ``runs/<UTC date>-ablations/`` or ``--out``: ``ablations.json`` (sorted keys, no wall clock),
``report-ablations.md``, ``series.npz`` (the ablations' hourly series and scored rows, as Report n°3 writes its
own), ``config.json`` and ``run.json`` (wall clock). ``--check DIR`` verifies every part by its digest, re-binds
``enc-ols``, re-runs the score into a temporary folder and compares the four files byte for byte.

``--synthetic`` reads a ``python -m olsprime.bench.report3 --synthetic`` folder and its own synthetic Report n°2
run (``<folder>/report2-synthetic``), and rebuilds that synthetic panel in memory. It never reads stored data.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import torch

from olsprime.bench import provenance as prov_mod
from olsprime.bench import report2 as r2
from olsprime.bench import report3 as r3
from olsprime.bench.power import run_output
from olsprime.eval import stats
from olsprime.models.encoder import EncoderConfig, EncoderModel, count_parameters, expected_parameters
from olsprime.models.matrix import prob_map
from olsprime.paths import runs_dir
from olsprime.train import checkpoint
from olsprime.train.determinism import deterministic
from olsprime.train.fit import FIT_YEARS, SEEDS, BrierFitConfig, EncoderData, EncoderSystem, FitConfig, year_start_ms

BASE = "enc-ols"
GATE, CONV, BRIER = "enc-ols-gate", "enc-ols-conv", "enc-ols-brier"
ABLATIONS: tuple[str, ...] = (GATE, CONV, BRIER)  # the protocol's order: LFM3's two ablations, then H6
H6_ARM = BRIER
VARIANTS_BEFORE = 21  # 18 before iteration 4, plus enc-ols, enc-softmax and enc-linear
REPORT_FILE = "report-ablations.md"
JSON_FILE = "ablations.json"
SERIES_FILE = r2.SERIES_FILE
COMPARED = ("config.json", JSON_FILE, REPORT_FILE, SERIES_FILE)
CHANGE = {
    GATE: "a sigmoid gate per OLS head: O_h <- sigmoid(x W_g)_h * O_h, W_g from the block's normalized input, no bias",
    CONV: "the first block's attention replaced by a gated short convolution: out(sigmoid(x W_g) * conv3(x W_u + b_u)), "
          "depthwise, causal, width 3, zero-padded on the left; the second block keeps its OLS attention",
    BRIER: "the loss: cross-entropy plus the Brier score sum_k (p_k - 1{y = k})^2, weight 1, both before the floor",
}  # fmt: skip
# The one key of a fit's saved configuration (FitConfig.to_json) each ablation changes from enc-ols's.
CHANGED_KEY = {GATE: ("encoder", "arm"), CONV: ("encoder", "arm"), BRIER: ("brier_weight",)}


class BindingRefused(ValueError):
    """Report n°3's run folder does not vouch for what is read from it, or the ablations' configuration is not ``enc-ols``'s."""


class InventoryRefused(ValueError):
    """The run folder's fits do not fit the stage: an arm fitted out of the protocol's order, or a fitted arm left unscored."""


# --- Configuration ------------------------------------------------------------------------------


@dataclass(frozen=True)
class AblationsConfig:
    """Everything the ablations fix. Saved with every run. ``arms`` are the arms scored (the registered run's: a prefix of :data:`ABLATIONS`)."""

    arms: tuple[str, ...] = ABLATIONS
    seeds: tuple[int, ...] = SEEDS
    years: tuple[int, ...] = FIT_YEARS
    device: str = "cuda"  # operational, as Report n°3's: outside config_json and the identity
    encoder: tuple[tuple[str, Any], ...] = ()  # EncoderConfig overrides: Report n°3's own, for tests and smoke runs only
    fit: tuple[tuple[str, Any], ...] = ()  # FitConfig overrides: Report n°3's own, for tests and smoke runs only
    brier_weight: float = 1.0  # H6: the Brier term's weight
    h6_ece_ratio: float = 0.8  # H6: ECE(enc-ols-brier) at most this times ECE(enc-ols)
    h6_ratio_bound: float = 1.0  # H6: the bootstrap's 95 % upper bound of the ratio below this
    h6_upper_quantile: float = 0.95  # the one-sided 95 % upper bound: the bootstrap's 95th percentile
    variants_before: int = VARIANTS_BEFORE
    synthetic: str | None = None

    def __post_init__(self) -> None:
        if not self.arms or len(set(self.arms)) != len(self.arms) or set(self.arms) - set(ABLATIONS):
            raise ValueError(f"the arms are a non-empty subset of {ABLATIONS}, without repeats")
        if list(self.arms) != [a for a in ABLATIONS if a in self.arms]:
            raise ValueError(f"the arms keep the protocol's order {ABLATIONS}")
        if self.device not in ("cuda", "cpu"):
            raise ValueError("the device is cuda or cpu")
        if not self.seeds or not self.years or list(self.years) != sorted(set(self.years)):
            raise ValueError("seeds and years must be non-empty, the years increasing")

    @property
    def in_order(self) -> bool:
        """The arms scored are the protocol's first ones: LFM3's two ablations, then H6, run only if time remains, in that order."""
        return tuple(self.arms) == ABLATIONS[: len(self.arms)]

    @property
    def registered(self) -> bool:
        """The registered configuration, with the arms scored a prefix of the protocol's order."""
        return self.in_order and dataclasses.replace(self, device="cuda", arms=ABLATIONS) == AblationsConfig()


def config_json(cfg: AblationsConfig) -> dict[str, Any]:
    """The configuration as saved: without the device, which is operational."""
    out = dataclasses.asdict(cfg)
    del out["device"]
    out["registered"] = cfg.registered
    return json.loads(json.dumps(r2._clean(out)))


def identity_config(cfg: AblationsConfig) -> dict[str, Any]:
    """What the fits' identity binds: the configuration without the device and the arms scored (each part binds its arm)."""
    out = config_json(cfg)
    for k in ("arms", "registered"):
        del out[k]
    return out


def fit_config(cfg: AblationsConfig, arm: str, seed: int, year: int) -> FitConfig:
    """The fit of an ablation: ``enc-ols``'s (:func:`olsprime.bench.report3.fit_config`) with the arm's one change."""
    if arm not in ABLATIONS:
        raise ValueError(f"not an ablation: {arm!r}")
    fit_ms, fit = year_start_ms(year), dict(cfg.fit)
    if arm == BRIER:
        return BrierFitConfig(fit_ms=fit_ms, seed=seed, encoder=EncoderConfig(arm=BASE, **dict(cfg.encoder)), brier_weight=cfg.brier_weight, **fit)
    return FitConfig(fit_ms=fit_ms, seed=seed, encoder=EncoderConfig(arm=arm, **dict(cfg.encoder)), **fit)


def base_fit_config(cfg: AblationsConfig, seed: int, year: int) -> FitConfig:
    return FitConfig(fit_ms=year_start_ms(year), seed=seed, encoder=EncoderConfig(arm=BASE, **dict(cfg.encoder)), **dict(cfg.fit))


def _flatten(obj: Any, prefix: tuple[str, ...] = ()) -> dict[tuple[str, ...], Any]:
    if isinstance(obj, dict):
        out: dict[tuple[str, ...], Any] = {}
        for k, v in obj.items():
            out |= _flatten(v, (*prefix, k))
        return out
    return {prefix: obj}


def one_change(arm: str, ablation: FitConfig, base: FitConfig) -> list[tuple[str, ...]]:
    """The keys in which an ablation's saved fit configuration differs from ``enc-ols``'s; refused unless it is the arm's one."""
    a, b = _flatten(json.loads(ablation.to_json())), _flatten(json.loads(base.to_json()))
    diff = sorted(k for k in set(a) | set(b) if a.get(k, ...) != b.get(k, ...))
    if diff != [CHANGED_KEY[arm]]:
        raise BindingRefused(f"{arm}: its fit differs from enc-ols's in {['.'.join(k) for k in diff]}, not in its one change {'.'.join(CHANGED_KEY[arm])}")
    return diff


def check_against_report3(cfg: AblationsConfig, cfg3: r3.Report3Config) -> None:
    """Everything else is enc-ols's: Report n°3's seeds, years and overrides, and the one change per fit.

    The load-bearing check is the one on ``enc-ols``'s fit: :func:`base_fit_config` must save the same configuration
    as Report n°3's own :func:`olsprime.bench.report3.fit_config`, so the base of every ablation is the ``enc-ols``
    that Report n°3 fitted. :func:`one_change` is then tautological here, since :func:`fit_config` builds each ablation
    from that base; it is kept as a guard against a later edit of :func:`fit_config`, and :func:`verified_part` holds
    each saved part to :func:`fit_config`.
    """
    for name in ("seeds", "years", "encoder", "fit"):
        if tuple(getattr(cfg, name)) != tuple(getattr(cfg3, name)):
            raise BindingRefused(f"the ablations' {name} {getattr(cfg, name)!r} are not Report n°3's {getattr(cfg3, name)!r}")
    for arm in ABLATIONS:
        for seed in cfg.seeds:
            for year in cfg.years:
                if base_fit_config(cfg, seed, year).to_json() != r3.fit_config(cfg3, BASE, seed, year).to_json():
                    raise BindingRefused(f"enc-ols's fit at seed {seed}, {year} is not Report n°3's")
                one_change(arm, fit_config(cfg, arm, seed, year), base_fit_config(cfg, seed, year))


def parameters(cfg: AblationsConfig) -> dict[str, int]:
    """Each arm's parameter count (the model built and counted, checked against the closed form), enc-ols's beside it."""
    out = {}
    for arm in (BASE, *ABLATIONS):
        enc = fit_config(cfg, arm, cfg.seeds[0], cfg.years[0]).encoder if arm != BASE else base_fit_config(cfg, cfg.seeds[0], cfg.years[0]).encoder
        with torch.random.fork_rng(devices=[]):  # building a model draws weights: leave the global generator as it was
            n = count_parameters(EncoderModel(enc))
        if n != expected_parameters(enc):
            raise AssertionError(f"{arm}: {n} parameters, the closed form says {expected_parameters(enc)}")
        out[arm] = n
    return out


# --- Report n°3's run, bound by its series' digest ----------------------------------------------


@dataclass(eq=False)
class Report3Run:
    """Report n°3's run folder: the digest of its ``series.npz``, its ``report3.json``, ``config.json`` and parts."""

    path: Path
    sha256: str
    report: dict[str, Any]
    report_sha256: str
    config: dict[str, Any]
    cfg: r3.Report3Config
    parts: r3.Parts


def rebuild_report3_config(recorded: Any, device: str) -> r3.Report3Config:
    """Report n°3's configuration from its ``config.json``; it must write back the same JSON."""

    def tup(v: Any) -> Any:
        return tuple(tup(x) for x in v) if isinstance(v, list) else v

    if not isinstance(recorded, Mapping):
        raise BindingRefused("Report n°3's config.json has no config")
    try:
        cfg = r3.Report3Config(**{k: tup(v) for k, v in recorded.items() if k != "registered"}, device=device)
    except (TypeError, ValueError) as exc:
        raise BindingRefused(f"Report n°3's config.json does not rebuild a Report3Config: {exc}") from None
    if r3.config_json(cfg) != json.loads(json.dumps(dict(recorded))):
        raise BindingRefused("Report n°3's config.json does not round-trip through Report3Config: the run was made by other code")
    return cfg


def read_report3(folder: Path, sha256: str, *, device: str = "cpu") -> Report3Run:
    """Report n°3's run, opened only if its ``series.npz`` has the SHA-256 given and its ``report3.json`` records that digest.

    The paths must be files under the runs root (:func:`olsprime.bench.power.run_output`), checked before a byte is
    read. ``series.npz`` is hashed, never opened: :func:`bind_base` rebuilds it from the bound parts instead, and its
    bytes must hash to the same digest.
    """
    path = run_output(Path(folder) / SERIES_FILE)
    want = sha256.strip().lower()
    got = r2.sha256_file(path)
    if got != want:
        raise BindingRefused(f"{path}: SHA-256 {got}, not the {want} given")
    report_path, config_path = path.parent / "report3.json", path.parent / "config.json"
    if not report_path.is_file() or not config_path.is_file():
        raise BindingRefused(f"{path.parent}: no report3.json and config.json beside the series: not a Report n°3 run folder")
    report_bytes = run_output(report_path).read_bytes()
    report = json.loads(report_bytes)
    rec = report.get("series")
    if not isinstance(rec, dict) or rec.get("file") != path.name or rec.get("sha256") != got:
        raise BindingRefused(f"{path}: its run's report3.json records {rec!r}, not this file's SHA-256 {got}")
    config = json.loads(run_output(config_path).read_bytes())
    cfg = rebuild_report3_config(config.get("config"), device)
    if not (path.parent / "parts" / "IDENTITY.json").is_file():
        raise BindingRefused(f"{path.parent}: no parts/IDENTITY.json, so no fit to read")
    rep2 = report.get("report2") or {}
    try:
        parts = r3.Parts(path.parent, None, require={"config": r3.config_json(cfg), "series_sha256": rep2.get("series_sha256")})
    except r3.ResumeRefused as exc:
        raise BindingRefused(f"Report n°3's parts are not its run's: {exc}") from None
    return Report3Run(path.parent, got, report, hashlib.sha256(report_bytes).hexdigest(), config, cfg, parts)


IDENTITY_KEYS = ("fit_sha256", "forecast_sha256", "forecast_rows", "kept_epoch")  # as explain head binds a part


def scored_entry(run3: Report3Run, key: str, rec: Mapping[str, Any], forecast: Mapping[str, Any]) -> dict[str, Any]:
    """The part's entry in ``report3.json["fits"]``: refused unless it records this part's digests, rows and epoch kept."""
    arm, seed, year = r3.parse_key(key)
    entries = [f for f in run3.report.get("fits") or [] if f.get("arm") == arm and f.get("seed") == seed and f.get("year") == year]
    if len(entries) != 1:
        raise BindingRefused(f"{key}: {len(entries)} entries for it in report3.json's fits: not a part Report n°3 scored")
    entry = entries[0]
    differ = [k for k in IDENTITY_KEYS if entry.get(k) != rec.get(k)]
    if differ:
        raise BindingRefused(f"{key}: the part's {', '.join(differ)} are not the ones report3.json records for it")
    if int(forecast["raw"].shape[0]) != int(entry["forecast_rows"]):
        raise BindingRefused(f"{key}: the forecast holds {forecast['raw'].shape[0]} rows, report3.json records {entry['forecast_rows']}")
    return entry


def check_rows(run2: r3.Report2Run, run3: Report3Run) -> None:
    """Report n°3 names Report n°2's series by its digest (its rows are then checked through :func:`bind_base`'s rebuild)."""
    rep2 = run3.report.get("report2") or {}
    if rep2.get("series_sha256") != run2.sha256:
        raise BindingRefused(f"Report n°3 paired with Report n°2's series {rep2.get('series_sha256')}, not the {run2.sha256} given")


@dataclass(eq=False)
class Base:
    """``enc-ols`` as Report n°3 scored it: its per-seed forecasts (verified, bound) and the ensemble, checked to the bit."""

    forecasts: r3.Forecasts
    probs: np.ndarray
    ll: np.ndarray
    br: np.ndarray
    record: dict[str, Any]  # report3.json's arms["enc-ols"]
    parts: list[dict[str, Any]]  # each part's key and digests, as bound


def bind_base(run3: Report3Run, run2: r3.Report2Run, sc: r2.Scored, floor: float) -> Base:
    """``enc-ols`` from Report n°3's folder, every part verified and bound to ``report3.json``, every number checked.

    - Each part of each arm of Report n°3 is verified against its folder (:func:`olsprime.bench.report3.verified_part`)
      and bound to ``report3.json``'s record of it (:func:`scored_entry`).
    - Report n°3's ``series.npz`` is rebuilt from those parts as Report n°3's score builds it (the ensembles, their
      hourly log-loss and Brier score, Report n°2's rows): its SHA-256 must be the digest given. So ``enc-ols``'s
      ensemble and hourly series are Report n°3's to the bit, and its rows are Report n°2's scored rows.
    - Each seed's log-loss, the mean log-loss, Brier score and ECE, and the fallbacks must equal ``report3.json``'s.
    """
    cfg3 = run3.cfg
    bound: list[dict[str, Any]] = []
    for arm in cfg3.arms:
        for seed in cfg3.seeds:
            for year in cfg3.years:
                key = r3.part_key(arm, seed, year)
                rec = r3.verified_part(run3.parts, key, cfg3)
                if rec is None:
                    raise BindingRefused(f"{key}: no finished part in Report n°3's folder")
                scored_entry(run3, key, rec, r3.read_forecast(run3.parts, key))
                if arm == BASE:
                    bound.append({"key": key, **{k: rec[k] for k in IDENTITY_KEYS}})
    fcs3 = r3.load_forecasts(run3.parts, cfg3, run2)
    probs3 = {a: r3.arm_probabilities(fcs3[a], floor) for a in cfg3.arms}
    ll3, br3 = {}, {}
    for a in cfg3.arms:
        losses = stats.per_row_losses(probs3[a], sc.label)
        ll3[a], br3[a] = r2.hourly(losses.log_loss, sc), r2.hourly(losses.brier, sc)
    scratch = Path(tempfile.mkdtemp(prefix="ablations-report3-series-"))
    try:
        r2.write_npz(scratch / SERIES_FILE, r3.series_out(run2, cfg3.arms, probs3, ll3, br3))
        rebuilt = r2.sha256_file(scratch / SERIES_FILE)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    if rebuilt != run3.sha256:
        raise BindingRefused(f"Report n°3's series rebuilt from its bound parts has SHA-256 {rebuilt}, not {run3.sha256}: "
                             "the parts are not the ones its series was made from, or this score runs on another platform "
                             "than Report n°3's (np.log's last bits differ between Windows and WSL2: score in WSL2, as "
                             "Report n°3 was scored)")  # fmt: skip
    fcs_base, probs, ll, br = fcs3[BASE], probs3[BASE], ll3[BASE], br3[BASE]
    record = (run3.report.get("arms") or {}).get(BASE)
    if not isinstance(record, dict):
        raise BindingRefused(f"report3.json has no {BASE} arm")
    seeds = r3.per_seed(fcs_base, sc, floor)
    if json.loads(json.dumps(r2._clean(seeds))) != record.get("seeds"):
        raise BindingRefused(f"{BASE}: each seed's log-loss recomputed from the parts is not report3.json's")
    if record["log_loss"]["estimate"] != float(ll.mean()) or record["brier"]["estimate"] != float(br.mean()):
        raise BindingRefused(f"{BASE}: the mean log-loss or Brier score is not report3.json's")
    if record["ece"]["estimate"] != ece_estimate(probs, sc, r3.rule_config(run2.config).ece_bins):
        raise BindingRefused(f"{BASE}: the ECE recomputed from the parts is not report3.json's")
    if int(record["fallbacks"]) != int(fcs_base.fallback.sum()):
        raise BindingRefused(f"{BASE}: the fallbacks are not report3.json's")
    return Base(fcs_base, probs, ll, br, record, bound)


# --- The panel ------------------------------------------------------------------------------------


def synthetic_panel(run2: r3.Report2Run) -> tuple[pl.DataFrame, dict[str, pl.DataFrame]]:
    """The panel of ``report3 --synthetic`` (:func:`olsprime.bench.report3.synthetic_report2`), rebuilt in memory; reads no data.

    Report n°2's fingerprint then checks that it is that panel (:func:`olsprime.bench.report3.build_inputs`).
    """
    from olsprime.bench.synthetic import synthetic_bars
    from olsprime.features.panel import assemble, pair_rows

    c = run2.config["config"]
    lo, hi = datetime(*c["first_month"], 1, tzinfo=UTC), datetime(*c["last_month"], 1, tzinfo=UTC)
    bars, parts = {}, []
    for i in range(r3.SMOKE_MEMBERS):
        symbol = f"S{i:02d}USDT"
        frame = synthetic_bars(symbol, start=r3.SMOKE_START, days=r3.SMOKE_HOURS, interval="1h", seed=i, drift=0.0, vol=0.01)
        bars[symbol] = frame
        months = [m for m in sorted(set(frame["open_time"].dt.truncate("1mo").to_list())) if lo <= m <= hi]
        parts.append(pair_rows(frame, months))
    return assemble(parts), bars


# --- Parts --------------------------------------------------------------------------------------------


def part_key(arm: str, seed: int, year: int) -> str:
    return f"fits/{arm}/s{seed}/{year}"


def parse_key(key: str) -> tuple[str, int, int]:
    head, arm, seed, year = key.split("/")
    if head != "fits" or arm not in ABLATIONS or not seed.startswith("s"):
        raise ValueError(f"not an ablation's part key: {key!r}")
    return arm, int(seed[1:]), int(year)


def verified_part(parts: r3.Parts, key: str, cfg: AblationsConfig) -> dict[str, Any] | None:
    """As :func:`olsprime.bench.report3.verified_part`, for an ablation: every file against its digest and its place.

    None if the part is not finished; refused unless ``part.json``, the checkpoint's config and the forecast's
    metadata all name the key's arm, seed, fit year and fit instant, the checkpoint's config being this fit's.
    """
    arm, seed, year = parse_key(key)
    fc = fit_config(cfg, arm, seed, year)
    want_config = json.loads(fc.to_json())
    rec = parts.get_json(f"{key}/part.json", unsealed_ok=True)
    if rec is None:
        return None
    where = f"parts/{key}/part.json"
    for name, want in (("arm", arm), ("seed", seed), ("year", year), ("fit_ms", fc.fit_ms), ("fit_config", want_config)):
        r3._expect(where, name, rec.get(name), want)
    files = {}
    for name, sha in (("fit.safetensors", rec.get("fit_sha256")), ("forecast.safetensors", rec.get("forecast_sha256"))):
        data = parts.get(f"{key}/{name}")
        if data is None or r3._sha(data) != sha:
            raise r3.PartRefused(f"parts/{key}/{name}: missing or not the file part.json records")
        files[name] = data
    where = f"parts/{key}/fit.safetensors"
    c = json.loads(r3._metadata(files["fit.safetensors"])["config"])
    r3._expect(where, "encoder.arm", c["encoder"]["arm"], fc.encoder.arm)
    r3._expect(where, "seed", c["seed"], seed)
    r3._expect(where, "fit_ms", c["fit_ms"], fc.fit_ms)
    r3._expect(where, "config", c, want_config)
    where = f"parts/{key}/forecast.safetensors"
    meta = r3._metadata(files["forecast.safetensors"])
    for name, want in (("arm", arm), ("seed", str(seed)), ("year", str(year)), ("fit_ms", str(fc.fit_ms)), ("fit_sha256", rec["fit_sha256"])):
        r3._expect(where, name, meta.get(name), want)
    return rec


def read_forecast(parts: r3.Parts, key: str) -> dict[str, Any]:
    data = parts.get(f"{key}/forecast.safetensors")
    if data is None:
        raise r3.PairingRefused(f"{key}: no verified forecast")
    arrays, meta = checkpoint.from_bytes(data)
    arm, seed, year = parse_key(key)
    for name, want in (("arm", arm), ("seed", str(seed)), ("year", str(year)), ("fit_ms", str(year_start_ms(year)))):
        r3._expect(f"parts/{key}/forecast.safetensors", name, meta.get(name), want)
    arrays["symbols"] = json.loads(meta["symbols"])
    return arrays


def load_fit(parts: r3.Parts, key: str, cfg: AblationsConfig) -> tuple[dict[str, np.ndarray], Any, FitConfig]:
    """An ablation part's kept parameters, standardizer and fit config (a :class:`BrierFitConfig` for ``enc-ols-brier``),
    the part verified first (:func:`verified_part`), read by Report n°3's reader (:func:`olsprime.bench.report3.read_fit`)."""
    if verified_part(parts, key, cfg) is None:
        raise r3.PairingRefused(f"{key}: no finished part; run the fits stage")
    data = parts.get(f"{key}/fit.safetensors")
    if data is None:
        raise r3.PairingRefused(f"{key}: no verified checkpoint")
    return r3.read_fit(data)


def n_parts(cfg: AblationsConfig) -> int:
    """The parts of one arm: one per seed and fit year (18 in the registered run)."""
    return len(cfg.seeds) * len(cfg.years)


def _inventory(parts: r3.Parts, cfg: AblationsConfig) -> tuple[dict[str, int], list[str]]:
    """Every arm of :data:`ABLATIONS` in the folder: the number of its sealed parts, and every part that does not verify.

    A part is sealed when its ``part.json`` is (an unsealed one is a part interrupted between its writes, which the fits
    stage redoes). Each sealed part is verified by :func:`verified_part`, whatever its arm. A folder under
    ``parts/fits/`` that holds a file and is not a part of this run's arms, seeds and years is a problem too.
    """
    problems: list[str] = []
    root = parts.dir / "fits"
    if root.is_dir():
        grid = {part_key(a, s, y) for a in ABLATIONS for s in cfg.seeds for y in cfg.years}
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(parts.dir).parts
            if path.is_file() and (len(rel) != 5 or "/".join(rel[:4]) not in grid):
                problems.append(f"parts/{'/'.join(rel)}: not a file of a part of this run's arms {list(ABLATIONS)}, seeds {list(cfg.seeds)} "
                                f"and years {list(cfg.years)}")  # fmt: skip
    counts = {}
    for arm in ABLATIONS:
        k = 0
        for seed in cfg.seeds:
            for year in cfg.years:
                try:
                    k += int(verified_part(parts, part_key(arm, seed, year), cfg) is not None)
                except r3.PartRefused as exc:
                    problems.append(str(exc))
        counts[arm] = k
    return counts, problems


def inventory(parts: r3.Parts, cfg: AblationsConfig) -> dict[str, int]:
    """The number of sealed parts of every arm of :data:`ABLATIONS`; refused (:class:`olsprime.bench.report3.PartRefused`)
    if any part in the folder does not verify, whatever its arm."""
    counts, problems = _inventory(parts, cfg)
    if problems:
        raise r3.PartRefused(f"{len(problems)} part(s) of the folder do not verify; the first: {problems[0]}")
    return counts


def unscored(counts: Mapping[str, int], cfg: AblationsConfig) -> tuple[list[str], dict[str, dict[str, int]]]:
    """The arms not scored: those with no part (not run), and those fitted in part (k of n parts, not scored, not a variant).

    Refused (:class:`InventoryRefused`) if an arm not scored has every part sealed: it is fitted, so it must be scored.
    """
    n = n_parts(cfg)
    full = [a for a in ABLATIONS if a not in cfg.arms and counts[a] == n]
    if full:
        arms = [a for a in ABLATIONS if a in cfg.arms or a in full]
        raise InventoryRefused(f"{', '.join(full)}: every one of its {n} parts is sealed in the folder, but the score leaves it out: "
                               f"score it (--arms {' '.join(arms)}); a fitted arm is a variant and is never left unreported")  # fmt: skip
    not_run = [a for a in ABLATIONS if a not in cfg.arms and counts[a] == 0]
    in_part = {a: {"parts": counts[a], "of": n} for a in ABLATIONS if a not in cfg.arms and 0 < counts[a] < n}
    return not_run, in_part


def check_fit_order(parts: r3.Parts, cfg: AblationsConfig, arms: Sequence[str]) -> None:
    """The fits stage takes its arms in the protocol's order: a prefix of :data:`ABLATIONS`, unless every part of each
    earlier arm left out is already sealed in the folder ("if time remains": LFM3's two ablations, then H6)."""
    idx = [ABLATIONS.index(a) for a in arms]
    if not idx or idx != sorted(set(idx)):
        raise InventoryRefused(f"the arms {list(arms)} are not in the protocol's order {list(ABLATIONS)}, or repeat one")
    counts = inventory(parts, cfg)
    n = n_parts(cfg)
    for a in ABLATIONS[: idx[-1]]:
        if a not in arms and counts[a] != n:
            raise InventoryRefused(f"--arms {' '.join(arms)} is not a prefix of the protocol's order {list(ABLATIONS)}, and {a}, which comes "
                                   f"first, has {counts[a]} of its {n} parts sealed: fit it first (the arms are fitted in the "
                                   "protocol's order, each only if time remains)")  # fmt: skip


def run_fits(data: EncoderData, rows: dict[int, np.ndarray], cfg: AblationsConfig, parts: r3.Parts, arms: Sequence[str], *,
             log: Callable[[str], None] = lambda s: None, driver: str | None = None) -> list[dict[str, Any]]:  # fmt: skip
    """Train and forecast every (arm, seed, year) not already saved, as Report n°3's fits stage does; returns their records."""
    device = torch.device(cfg.device)
    records = []
    symbols = list(data.arrays.symbols)
    for arm in arms:
        for seed in cfg.seeds:
            for year in cfg.years:
                key = part_key(arm, seed, year)
                rec = verified_part(parts, key, cfg)
                if rec is not None:
                    if rec.get("device") != cfg.device:
                        raise r3.ResumeRefused(f"{key} was fitted on {rec.get('device')!r}, this run is on {cfg.device!r}: "
                                               "every fit of a folder runs on one device")  # fmt: skip
                    log(f"{key}: saved, verified, skipped")
                    records.append(rec)
                    continue
                if parts.stop_after is not None and parts.saved >= parts.stop_after:
                    raise r3.Interrupted(f"stopped after {parts.saved} new parts")
                fc = fit_config(cfg, arm, seed, year)
                system = EncoderSystem(data, fc, device=device)
                r3._peak_reset(device)
                started = time.perf_counter()
                res = system.fit()
                peak_train = r3._peak_gpu(device)
                t = time.perf_counter()
                out = system.forecast(res, rows[year])
                if device.type == "cuda":
                    torch.cuda.synchronize(device)
                forecast_s = time.perf_counter() - t
                seconds = time.perf_counter() - started
                folder = parts.dir / key
                fit_sha = res.save(folder)
                parts.put(f"{key}/fit.safetensors", (folder / "fit.safetensors").read_bytes())
                arrays = r3.forecast_arrays(data, out, system.y)
                meta = {"arm": arm, "seed": str(seed), "year": str(year), "fit_ms": str(fc.fit_ms), "symbols": json.dumps(symbols),
                        "fit_sha256": fit_sha}  # fmt: skip
                forecast_sha = parts.put(f"{key}/forecast.safetensors", checkpoint.to_bytes(arrays, meta))
                parts.put_json(f"{key}/timing.json", {"seconds": seconds, "train_s": res.timing.get("train_s"), "slice_s": res.timing.get("slice_s"),
                                                      "forecast_s": forecast_s, "steps": res.steps, "peak_gpu_bytes_training": peak_train,
                                                      "device": str(device), "gpu": res.build.get("gpu"), "driver": driver,
                                                      "finished_at": datetime.now(UTC).isoformat(timespec="seconds")})  # fmt: skip
                rec = {
                    "arm": arm, "seed": seed, "year": year, "fit_ms": fc.fit_ms, "fit_config": json.loads(fc.to_json()),
                    "fit_sha256": fit_sha, "forecast_sha256": forecast_sha, "epoch_digests": res.epoch_digests(),
                    "slice_losses": list(res.slice_losses), "kept_epoch": res.kept_epoch, "steps": res.steps,
                    "n_parameters": res.n_parameters, "training_rows": int(res.train_rows.size), "slice_rows": int(res.slice_rows.size),
                    "climatology": res.climatology.tolist(), "climatology_rows": res.climatology_rows,
                    "complete_without_window": res.complete_without_window, "forecast_rows": int(rows[year].size),
                    "fallbacks": int(arrays["fallback"].sum()), "build": res.build, "device": cfg.device,
                }  # fmt: skip
                parts.put_json(f"{key}/part.json", rec)
                parts.saved += 1
                records.append(rec)
                log(f"{key}: {seconds:.1f} s, {res.steps} steps ({res.timing.get('train_s', 0.0) / max(res.steps, 1):.3f} s/step), "
                    f"kept epoch {res.kept_epoch}, slice losses {', '.join(f'{v:.4f}' for v in res.slice_losses)}")  # fmt: skip
    return records


def load_forecasts(parts: r3.Parts, cfg: AblationsConfig, run2: r3.Report2Run) -> dict[str, r3.Forecasts]:
    out = {}
    for arm in cfg.arms:
        raw, fallback = {}, None
        for seed in cfg.seeds:
            keys = [part_key(arm, seed, y) for y in cfg.years]
            missing = [k for k in keys if verified_part(parts, k, cfg) is None]
            if missing:
                raise r3.PairingRefused(f"{arm} seed {seed}: no verified part {missing[0]}; run the fits stage, or score fewer arms (--arms)")
            cat = r3.pair_forecasts([read_forecast(parts, k) for k in keys], run2, f"{arm} seed {seed}")
            raw[seed] = cat["raw"]
            if fallback is not None and not np.array_equal(fallback, cat["fallback"]):
                raise r3.PairingRefused(f"{arm}: the seeds disagree on the rows whose window failed")
            fallback = cat["fallback"]
        assert fallback is not None
        out[arm] = r3.Forecasts(raw, fallback)
    return out


# --- H6 -------------------------------------------------------------------------------------------------


def ece_estimate(p: np.ndarray, sc: r2.Scored, n_bins: int) -> float:
    """The top-label ECE over the scored rows from per-hour bin sums, as :func:`olsprime.bench.report2.ece_interval` takes it."""
    d = r2.ece_bins(p, sc.label, sc, n_bins)
    return float(np.abs(d.sum(axis=0)).sum() / sc.count.sum())


def ece_ratio_interval(p_a: np.ndarray, p_b: np.ndarray, sc: r2.Scored, br_a: np.ndarray, br_b: np.ndarray, rcfg: r2.Report2Config,
                       *tag: str, quantile: float = 0.95) -> dict[str, Any]:  # fmt: skip
    """ECE(a) / ECE(b) and its paired stationary bootstrap over hours (Report n°2's conventions).

    The top-label ECE of a resample of hours with multiplicities w is ``sum_bins |sum_h w_h D_hb| / sum_h w_h n_h``, D_hb
    the hour's bin sum of (hit - confidence) (:func:`olsprime.bench.report2.ece_bins`, the same per-hour sums as each
    arm's ECE interval), so each replicate is exact and cheap. Both arms take the same hours in every replicate; the
    denominators cancel in the ratio. Block length: the larger of the two arms' ECE blocks (each the Politis-White length
    of the arm's hourly Brier, as Report n°2's ECE interval takes it); seed: Report n°2's, tagged. Each ECE is checked
    against :func:`olsprime.eval.stats.ece` on the rows, as Report n°2 does. Returns the estimate, the two-sided interval
    at Report n°2's level, the one-sided upper bound (the bootstrap's ``quantile``), both ECEs, the block and the draws kept.
    """
    n = int(sc.count.sum())
    da, db = (r2.ece_bins(p, sc.label, sc, rcfg.ece_bins) for p in (p_a, p_b))
    ea, eb = (float(np.abs(d.sum(axis=0)).sum() / n) for d in (da, db))
    for e, p in ((ea, p_a), (eb, p_b)):
        if abs(e - stats.ece(p, sc.label, rcfg.ece_bins)) > r2.ece_tolerance(n):
            raise AssertionError("an ECE by hours differs from stats.ece by more than rounding")
    block = max(r2._block(br_a), r2._block(br_b))
    t = sc.hours.size
    draws = []
    for idx in r2._chunks(t, block, rcfg.n_boot, r2._seed(rcfg, *tag)):
        for row in idx:  # no BLAS: plain numpy sums, the same bits on every re-run
            w = np.bincount(row, minlength=t).astype(np.float64)
            num_a = np.abs((w[:, None] * da).sum(axis=0)).sum()
            num_b = np.abs((w[:, None] * db).sum(axis=0)).sum()
            draws.append(num_a / num_b if num_b > 0 else np.nan)
    draws_arr = np.asarray(draws, dtype=np.float64)
    estimate = ea / eb if eb > 0 else float("nan")
    out = r2._interval(draws_arr, estimate, rcfg.level, block)
    finite = draws_arr[np.isfinite(draws_arr)]
    out |= {"upper": float(np.quantile(finite, quantile)), "upper_quantile": quantile, "ece_a": ea, "ece_b": eb,
            "undefined_draws": int(draws_arr.size - finite.size)}  # fmt: skip
    return out


def ece_ratio_defined(ratio: Mapping[str, Any]) -> bool:
    """The ratio of two ECEs is defined: the denominator's ECE is positive."""
    return bool(ratio["ece_b"] > 0 and np.isfinite(ratio["estimate"]))


def ece_condition(ratio: Mapping[str, Any], cfg: AblationsConfig) -> bool:
    """H6's ECE condition on a ratio of :func:`ece_ratio_interval`: the reported ratio at most 0.8 and the bootstrap's
    95th percentile below 1. The condition reads the ratio the report prints, so the two cannot disagree by an ulp."""
    return bool(ece_ratio_defined(ratio) and ratio["estimate"] <= cfg.h6_ece_ratio and ratio["upper"] < cfg.h6_ratio_bound)


def seed_split(fc: r3.Forecasts, sc: r2.Scored, rcfg: r2.Report2Config, floor: float, cfg: AblationsConfig) -> dict[str, Any]:
    """H6's seed-split control: how far seed noise alone moves H6's ECE condition. A description, with no verdict.

    For each ordered pair (i, j), i != j, of ``enc-ols``'s seeds, each seed's forecasts floored on their own (as
    :func:`olsprime.bench.report3.per_seed` floors them) over the scored rows: ECE_i and ECE_j (:func:`olsprime.eval.stats.ece`),
    the ratio ECE_i / ECE_j and its paired stationary bootstrap through H6's machinery (:func:`ece_ratio_interval`: the
    hours resampled jointly, the larger of the two seeds' blocks of their hourly Brier scores, Report n°2's ``n_boot``,
    the seed tagged ``("ece_ratio", "enc-ols seed i", "enc-ols seed j")``), and whether H6's ECE condition
    (:func:`ece_condition`) holds for i against j. The log-loss condition is not applied: two seeds of one model differ by
    at most the seed range, by construction. H6 compares 3-seed ensembles, whose seed noise is smaller than one seed's.
    """
    seeds = sorted(fc.raw)
    p = {s: prob_map(fc.raw[s], floor) for s in seeds}
    br = {s: r2.hourly(stats.per_row_losses(p[s], sc.label).brier, sc) for s in seeds}
    ece = {s: float(stats.ece(p[s], sc.label, rcfg.ece_bins)) for s in seeds}
    pairs = []
    for i in seeds:
        for j in seeds:
            if i == j:
                continue
            tag = ("ece_ratio", f"{BASE} seed {i}", f"{BASE} seed {j}")
            r = ece_ratio_interval(p[i], p[j], sc, br[i], br[j], rcfg, *tag, quantile=cfg.h6_upper_quantile)
            pairs.append({"seed_i": i, "seed_j": j, "seed_tag": list(tag), "ece_i": ece[i], "ece_j": ece[j], "ratio": r["estimate"],
                          "interval_95": [r["low"], r["high"]], "upper_95": r["upper"], "block": r["block"], "n_boot": r["n_boot"],
                          "undefined_draws": r["undefined_draws"], "ece_condition_holds": ece_condition(r, cfg)})  # fmt: skip
    return {
        "kind": "control: a description with no verdict, not a variant",
        "seeds": seeds, "pairs": pairs, "holds_in": sum(q["ece_condition_holds"] for q in pairs), "of": len(pairs),
        "rule": f"H6's ECE condition alone, seed i against seed j of {BASE}: ECE_i / ECE_j <= {cfg.h6_ece_ratio} and the paired "
                f"stationary bootstrap's {cfg.h6_upper_quantile:.0%} percentile of the ratio below {cfg.h6_ratio_bound}; the log-loss "
                "condition is not applied",
        "note": "H6 compares 3-seed ensembles, whose seed noise is smaller than a single seed's; H6's verdict is computed without "
                "this control",
    }  # fmt: skip


def h6_verdict(ratio: Mapping[str, Any], comparison: Mapping[str, Any], base_seed_range: float, cfg: AblationsConfig) -> dict[str, Any]:
    """H6 by its registered rule; it holds if both conditions hold.

    - ECE: ``ECE(enc-ols-brier) <= 0.8 x ECE(enc-ols)``, and the paired stationary bootstrap's 95 % upper bound of their
      ratio below 1;
    - log-loss: mean(ll_brier - ll_ols) at most the larger of the range of enc-ols's three per-seed log-losses and the
      HLN-corrected Diebold-Mariano standard error of that difference.
    """
    ea, eb = ratio["ece_a"], ratio["ece_b"]
    defined = ece_ratio_defined(ratio)
    ece_met = ece_condition(ratio, cfg)
    se = comparison.get("dm_se")  # None when the difference is the same at every hour (no test)
    tolerance = max(base_seed_range, se) if se is not None else base_seed_range
    diff = float(comparison["mean_diff"])
    ll_met = bool(diff <= tolerance)
    status = "undefined: enc-ols's ECE is 0" if not defined else ("holds" if ece_met and ll_met else "does not hold")
    return {
        "status": status, "holds": status == "holds",
        "ece": {"brier": ea, "enc_ols": eb, "ratio": ratio["estimate"], "max_ratio": cfg.h6_ece_ratio, "upper_95": ratio["upper"],
                "upper_below": cfg.h6_ratio_bound, "interval_95": [ratio["low"], ratio["high"]], "block": ratio["block"], "met": ece_met},
        "log_loss": {"difference": diff, "seed_range": base_seed_range, "dm_se": se, "tolerance": tolerance,
                     "tolerance_from": "seed range" if se is None or base_seed_range >= se else "DM standard error", "met": ll_met},
        "rule": "ECE(enc-ols-brier) <= 0.8 x ECE(enc-ols) and the paired stationary bootstrap's 95 % upper bound of their ratio "
                "below 1; and mean(ll_brier - ll_ols) <= max(range of enc-ols's per-seed log-losses, HLN-corrected DM standard error "
                "of the difference)",
    }  # fmt: skip


# --- The score ------------------------------------------------------------------------------------------


def fits_builds(parts: r3.Parts, cfg: AblationsConfig) -> list[dict[str, Any]]:
    builds = []
    for a in cfg.arms:
        for sd in cfg.seeds:
            for y in cfg.years:
                rec = parts.get_json(f"{part_key(a, sd, y)}/part.json")
                tim = parts.get_json(f"{part_key(a, sd, y)}/timing.json")
                if rec:
                    b = rec["build"]
                    builds.append({"gpu": b.get("gpu"), "cuda": b.get("cuda_build"), "torch": b.get("torch"), "device": b.get("device"),
                                   "driver": (tim or {}).get("driver")})  # fmt: skip
    return [json.loads(t) for t in sorted({json.dumps(b, sort_keys=True) for b in builds})]


def score(run2: r3.Report2Run, run3: Report3Run, cfg: AblationsConfig, parts: r3.Parts) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Every number of the ablations from their saved forecasts, Report n°3's enc-ols bound to its run, and Report n°2's series."""
    check_against_report3(cfg, run3.cfg)
    check_rows(run2, run3)
    not_run, fitted_in_part = unscored(inventory(parts, cfg), cfg)
    rcfg = r3.rule_config(run2.config)
    s = run2.series
    sc = r2.Scored(np.arange(s["label"].size), s["label"], s["hour"], s["hours"], s["count"])
    if not np.array_equal(np.bincount(sc.hour, minlength=sc.hours.size), sc.count):
        raise r3.PairingRefused("Report n°2's hour index does not give its counts")
    floors = {fit_config(cfg, a, sd, y).prob_floor for a in cfg.arms for sd in cfg.seeds for y in cfg.years}
    floors |= {r3.fit_config(run3.cfg, BASE, sd, y).prob_floor for sd in cfg.seeds for y in cfg.years}
    if len(floors) != 1:
        raise r3.PairingRefused(f"the fits use several probability floors: {sorted(floors)}")
    floor = floors.pop()
    base = bind_base(run3, run2, sc, floor)
    fcs = load_forecasts(parts, cfg, run2)
    probs = {arm: r3.arm_probabilities(fcs[arm], floor) for arm in cfg.arms}
    ll = {r3.CLIMATOLOGY: run2.ll(r3.CLIMATOLOGY), BASE: base.ll}
    br = {r3.CLIMATOLOGY: run2.brier(r3.CLIMATOLOGY), BASE: base.br}
    for arm in cfg.arms:
        losses = stats.per_row_losses(probs[arm], sc.label)
        ll[arm], br[arm] = r2.hourly(losses.log_loss, sc), r2.hourly(losses.brier, sc)
    clim = float(ll[r3.CLIMATOLOGY].mean())
    if clim != run2.report["arms"][r3.CLIMATOLOGY]["log_loss"]["estimate"]:
        raise r3.PairingRefused("climatology-panel's mean hourly log-loss is not Report n°2's")
    n_params = parameters(cfg)
    arms: dict[str, Any] = {}
    for arm in cfg.arms:
        arms[arm] = {"change": CHANGE[arm], "log_loss": r2.mean_interval(ll[arm], rcfg, "ll", arm), "brier": r2.mean_interval(br[arm], rcfg, "brier", arm),
                     "bss": r2.bss_interval(br[arm], br[r3.CLIMATOLOGY], rcfg, "bss", arm),
                     "ece": r2.ece_interval(probs[arm], sc.label, sc, br[arm], rcfg, "ece", arm), "fallbacks": int(fcs[arm].fallback.sum()),
                     "seeds": r3.per_seed(fcs[arm], sc, floor), "parameters": n_params[arm]}  # fmt: skip
    base_rec = {k: base.record[k] for k in ("log_loss", "brier", "bss", "ece", "seeds", "fallbacks")}
    comparisons = {}
    for arm in cfg.arms:
        c = dict(r3._compare(ll, arm, BASE, clim, rcfg), name=f"{arm} vs {BASE}", kind="h6" if arm == H6_ARM else "described")
        c["within_base_seed_range"] = bool(abs(c["mean_diff"]) <= base.record["seeds"]["range"])  # a description
        comparisons[arm] = c
    out: dict[str, Any] = {
        "climatology_log_loss": clim, "arms": arms, "enc_ols": {**base_rec, "parameters": n_params[BASE], "source": "Report n°3, bound by digest"},
        "comparisons": comparisons, "not_run": not_run, "fitted_in_part": fitted_in_part,
    }  # fmt: skip
    if H6_ARM in cfg.arms:
        ratio = ece_ratio_interval(probs[H6_ARM], base.probs, sc, br[H6_ARM], br[BASE], rcfg, "ece_ratio", H6_ARM, BASE, quantile=cfg.h6_upper_quantile)
        if ratio["ece_b"] != base.record["ece"]["estimate"] or ratio["ece_a"] != arms[H6_ARM]["ece"]["estimate"]:
            raise AssertionError("the ratio's two ECEs are not the arms' own")
        out["h6"] = h6_verdict(ratio, comparisons[H6_ARM], float(base.record["seeds"]["range"]), cfg)
        out["h6"]["undefined_draws"] = ratio["undefined_draws"]
        out["h6_seed_split"] = seed_split(base.forecasts, sc, rcfg, floor, cfg)  # after H6's verdict, which never reads it
        if out["h6_seed_split"]["seeds"] != sorted(cfg.seeds):
            raise AssertionError("the seed-split control's seeds are not enc-ols's registered seeds")
    else:
        out["h6"] = {"status": "not run", "holds": False}
    fits = [verified_part(parts, part_key(a, sd, y), cfg) for a in cfg.arms for sd in cfg.seeds for y in cfg.years]
    timings = {part_key(a, sd, y): parts.get_json(f"{part_key(a, sd, y)}/timing.json") or {} for a in cfg.arms for sd in cfg.seeds for y in cfg.years}
    out["fits"] = [{k: f[k] for k in ("arm", "seed", "year", "fit_sha256", "forecast_sha256", "kept_epoch", "slice_losses", "epoch_digests",
                                      "steps", "n_parameters", "training_rows", "slice_rows", "climatology_rows", "forecast_rows", "fallbacks")}
                   for f in fits if f is not None]  # fmt: skip
    for arm in cfg.arms:
        mine = [t for k, t in timings.items() if t and k.split("/")[1] == arm]
        arms[arm]["training_hours"] = sum(t["seconds"] for t in mine) / 3600.0
        arms[arm]["seconds_per_step"] = sum(t["train_s"] for t in mine) / max(sum(t["steps"] for t in mine), 1)
        if any(f["n_parameters"] != n_params[arm] for f in out["fits"] if f["arm"] == arm):
            raise AssertionError(f"{arm}: a fit's parameter count is not the arm's")
    out["fits_devices"] = sorted({str(f.get("device")) for f in fits if f is not None})
    out["fits_builds"] = fits_builds(parts, cfg)
    report3_builds = run3.report.get("fits_builds")
    out["same_build_as_report3"] = out["fits_builds"] == report3_builds
    out["registered"] = bool(cfg.registered and run3.report.get("registered", False) and out["fits_devices"] == ["cuda"]
                             and len(out["fits_builds"]) == 1 and out["same_build_as_report3"])  # fmt: skip
    out["variants"] = {"before": cfg.variants_before, "this_report": len(cfg.arms), "total": cfg.variants_before + len(cfg.arms)}
    out["scored"] = {"rows": int(sc.label.size), "hours": int(sc.hours.size), "first_hour": r2.iso(int(sc.hours[0])), "last_hour": r2.iso(int(sc.hours[-1]))}
    out["report3"] = {"series_sha256": run3.sha256, "report3_json_sha256": run3.report_sha256, "registered": bool(run3.report.get("registered", False)),
                      "enc_ols_parts": base.parts, "fits_builds": report3_builds,
                      "git_commit": (run3.config.get("provenance") or {}).get("git_commit")}  # fmt: skip
    out["report2"] = {"series_sha256": run2.sha256, "report2_json_sha256": run2.report_sha256, "panel_fingerprint": run2.fingerprint,
                      "registered": bool(run2.report.get("registered", False))}  # fmt: skip
    return out, r3.series_out(run2, cfg.arms, probs, ll, br)


# --- The report -------------------------------------------------------------------------------------------


def _ci(ci: Mapping[str, Any] | None, digits: int = 4) -> str:
    return r2._ci(dict(ci) if ci is not None else None, digits)


def _not_run(m: Mapping[str, Any]) -> str:
    """The arms not scored, in the protocol's order: not run, or fitted in part (k of n parts, not scored, not a variant)."""
    out = []
    for arm in ABLATIONS:
        if arm in m["not_run"]:
            out.append(arm)
        elif arm in m["fitted_in_part"]:
            k = m["fitted_in_part"][arm]
            out.append(f"{arm} (fitted in part, {k['parts']} of {k['of']} parts, not scored)")
    return ", ".join(out) or "none"


def render(m: dict[str, Any], config: dict[str, Any]) -> str:
    lines = ["# LFM3's ablations and H6, against Report n°3's enc-ols", ""]
    if not m["registered"]:
        lines += ["**NOT THE REGISTERED RUN.** This run's configuration, its fits' build, or the Report n°3 run it pairs with differs from "
                  "the pre-registered one (a smoke run or a test): its numbers are not results.", ""]  # fmt: skip
    h6 = m["h6"]
    lines += [
        "Pre-registered in `docs/PROTOCOL.md`, \"LFM3's ablations and H6, if time remains\". Each arm is enc-ols with one change, "
        "three seeds averaged before the floor and Report n°3's six yearly fits. enc-ols is Report n°3's, never refitted: its parts are "
        "bound to that run's report3.json by their digests, and their ensemble equals its series.npz to the bit. Development period "
        "only; the validation year and the vault stay closed.",
        "",
        "## Verdict",
        "",
        "| hypothesis | verdict | rule |",
        "|---|---|---|",
        f"| H6 | {h6['status']} | {h6.get('rule', '-')} |",
        "",
        "The LFM3 arms (enc-ols-gate, enc-ols-conv) are described against enc-ols, with no registered rule.",
        "",
        f"Scored: {m['scored']['rows']} rows over {m['scored']['hours']} decision hours ({m['scored']['first_hour'][:13]} -> "
        f"{m['scored']['last_hour'][:13]}), Report n°2's scored rows one for one. Every mean is a mean over hours of the hourly means; "
        "intervals are stationary-bootstrap 95 % percentile intervals with Report n°2's seeds.",
        "",
        "## Arms",
        "",
        "| arm | change | parameters | log-loss | Brier | BSS vs climatology | ECE | fallbacks |",
        "|---|---|---|---|---|---|---|---|",
    ]
    b = m["enc_ols"]
    lines.append(f"| enc-ols (Report n°3) | - | {b['parameters']:,} | {_ci(b['log_loss'])} | {_ci(b['brier'])} | {_ci(b['bss'])} | {_ci(b['ece'])} | {b['fallbacks']} |")
    for arm in ABLATIONS:
        if arm in m["arms"]:
            a = m["arms"][arm]
            lines.append(f"| {arm} | {a['change']} | {a['parameters']:,} | {_ci(a['log_loss'])} | {_ci(a['brier'])} | {_ci(a['bss'])} | "
                         f"{_ci(a['ece'])} | {a['fallbacks']} |")  # fmt: skip
        elif arm in m["fitted_in_part"]:
            k = m["fitted_in_part"][arm]
            lines.append(f"| {arm} | fitted in part ({k['parts']} of {k['of']} parts), not scored | - | - | - | - | - | - |")
        else:
            lines.append(f"| {arm} | not run | - | - | - | - | - | - |")
    seeds = list(b["seeds"]["log_loss"])
    lines += ["", "Each seed's log-loss, a description (the model is the ensemble):", "", "| arm | " + " | ".join(f"seed {s}" for s in seeds) + " | range |",
              "|---|" + "---|" * (len(seeds) + 1),
              "| enc-ols | " + " | ".join(f"{b['seeds']['log_loss'][s]:.5f}" for s in seeds) + f" | {b['seeds']['range']:.5f} |"]  # fmt: skip
    for arm in ABLATIONS:
        if arm in m["arms"]:
            a = m["arms"][arm]["seeds"]
            lines.append(f"| {arm} | " + " | ".join(f"{a['log_loss'][s]:.5f}" for s in seeds) + f" | {a['range']:.5f} |")
    lines += ["", "## Against enc-ols", "", "Difference = arm - enc-ols in mean hourly log-loss (negative: the arm is better). Descriptions, "
              "but for H6's log-loss condition.", "",
              "| arm | difference | share of climatology | DM p | DM standard error (HLN) | bootstrap 95 % | within enc-ols's seed range | identical hours |",
              "|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for arm in ABLATIONS:
        c = m["comparisons"].get(arm)
        if c is None:
            continue
        if "undefined" in c:
            lines.append(f"| {arm} | {c['mean_diff']:+.5f} | - | - | - | - | {'yes' if c['within_base_seed_range'] else 'no'} | no test: {c['undefined']} |")
            continue
        bo = c["bootstrap"]
        lines.append(f"| {arm} | {c['mean_diff']:+.5f} | {c['share_of_climatology']:+.4%} | {c['dm_p']:.4f} | {c['dm_se']:.6f} | "
                     f"[{bo['low']:+.5f}, {bo['high']:+.5f}] | {'yes' if c['within_base_seed_range'] else 'no'} | {r2._informative(c)} |")  # fmt: skip
    lines += ["", "## H6", ""]
    if h6["status"] == "not run":
        k = m["fitted_in_part"].get(H6_ARM)
        lines.append(f"enc-ols-brier was fitted in part ({k['parts']} of {k['of']} parts) and not scored: H6 is not run." if k
                     else "enc-ols-brier was not run: H6 is not run.")  # fmt: skip
    else:
        e, ll = h6["ece"], h6["log_loss"]
        lines += [
            f"- **ECE.** enc-ols-brier {e['brier']:.6f}, enc-ols {e['enc_ols']:.6f}: ratio {e['ratio']:.4f} (at most {e['max_ratio']}); paired "
            f"stationary bootstrap over hours (block {e['block']}): 95 % interval [{e['interval_95'][0]:.4f}, {e['interval_95'][1]:.4f}], "
            f"one-sided 95 % upper bound {e['upper_95']:.4f} (below {e['upper_below']}). Condition {'met' if e['met'] else 'not met'}.",
            f"- **Log-loss.** mean(ll_brier - ll_ols) = {ll['difference']:+.6f}; tolerance {ll['tolerance']:.6f}, the larger of enc-ols's "
            f"per-seed range {ll['seed_range']:.6f} and the HLN-corrected DM standard error "
            f"{'-' if ll['dm_se'] is None else format(ll['dm_se'], '.6f')} ({ll['tolerance_from']}). Condition {'met' if ll['met'] else 'not met'}.",
            f"- **H6: {h6['status']}.**",
        ]  # fmt: skip
    split = m.get("h6_seed_split")
    if split is not None:
        lines += ["", "### H6's seed-split control", "",
                  "A control with no verdict, and not a variant: how far seed noise alone moves H6's ECE condition. For each ordered pair "
                  "of enc-ols's seeds (i, j), seed i's forecasts against seed j's, each floored on its own, through H6's own machinery "
                  "(the paired stationary bootstrap over hours, the larger of the two seeds' blocks, Report n°2's resamples). The "
                  "log-loss condition is not applied. H6 compares 3-seed ensembles, whose seed noise is smaller than a single seed's. "
                  "H6's verdict above is computed without this control and does not change with it.", "",
                  "| seed i | seed j | ECE i | ECE j | ratio i / j | 95 % interval | 95th percentile | block | ECE condition holds |",
                  "|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
        for q in split["pairs"]:
            lines.append(f"| {q['seed_i']} | {q['seed_j']} | {q['ece_i']:.6f} | {q['ece_j']:.6f} | {q['ratio']:.4f} | "
                         f"[{q['interval_95'][0]:.4f}, {q['interval_95'][1]:.4f}] | {q['upper_95']:.4f} | {q['block']} | "
                         f"{'yes' if q['ece_condition_holds'] else 'no'} |")  # fmt: skip
        lines += ["", f"The ECE condition holds for {split['holds_in']} of the {split['of']} ordered pairs of single seeds."]
    lines += ["", "## Fits", "", f"Fitted on: {', '.join(m['fits_devices']) or '-'}, in {len(m['fits_builds'])} build(s); the same build as "
              f"Report n°3's fits: {'yes' if m['same_build_as_report3'] else 'no'}. The slice losses are the registered early-stopping "
              "statistic, not results.", "", "| arm | training GPU-hours | s per step | fits |", "|---|---|---|---|"]  # fmt: skip
    for arm in ABLATIONS:
        if arm in m["arms"]:
            a = m["arms"][arm]
            lines.append(f"| {arm} | {a['training_hours']:.3f} | {a['seconds_per_step']:.3f} | {sum(1 for f in m['fits'] if f['arm'] == arm)} |")
    lines += ["", "| arm | seed | year | kept epoch | slice losses | checkpoint SHA-256 |", "|---|---|---|---|---|---|"]
    for f in m["fits"]:
        lines.append(f"| {f['arm']} | {f['seed']} | {f['year']} | {f['kept_epoch']} | {', '.join(f'{x:.4f}' for x in f['slice_losses'])} | `{f['fit_sha256'][:16]}` |")
    lines += [
        "",
        "## Variants",
        "",
        f"Variants tried so far: {m['variants']['before']} before these ablations, plus the {m['variants']['this_report']} that ran: "
        f"{m['variants']['total']}. A seed ensemble counts once; the controls are not variants. Not run: {_not_run(m)}.",
        "",
        *prov_mod.render_md(config["provenance"]),
        f"- Report n°3's series: `{m['report3']['series_sha256']}`; its report3.json: `{m['report3']['report3_json_sha256']}`.",
        f"- Report n°2's series: `{m['report2']['series_sha256']}`; panel fingerprint `{m['report2']['panel_fingerprint']}`.",
        f"- This report's series (`{m['series']['file']}`), SHA-256: `{m['series']['sha256']}`." if "series" in m else "",
    ]  # fmt: skip
    return "\n".join(lines) + "\n"


def config_record(cfg: AblationsConfig, run2: r3.Report2Run, run3: Report3Run, prov: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    import scipy

    return {
        "report": "ablations",
        "config": config_json(cfg),
        "registered": cfg.registered,
        "changes": {a: CHANGE[a] for a in cfg.arms},
        "report3": {"series_sha256": run3.sha256, "report3_json_sha256": run3.report_sha256},
        "report2": {"series_sha256": run2.sha256, "report2_json_sha256": run2.report_sha256, "panel_fingerprint": run2.fingerprint},
        "fits_identity": identity,
        "versions": {"numpy": np.__version__, "polars": pl.__version__, "scipy": scipy.__version__, "torch": torch.__version__, "python": sys.version.split()[0]},
        "provenance": prov,
    }


def write_score(run2: r3.Report2Run, run3: Report3Run, cfg: AblationsConfig, parts: r3.Parts, out: Path, prov: dict[str, Any]) -> dict[str, Any]:
    metrics, series = score(run2, run3, cfg, parts)
    out.mkdir(parents=True, exist_ok=True)
    r2.write_npz(out / SERIES_FILE, series)
    metrics["series"] = {"file": SERIES_FILE, "sha256": r2.sha256_file(out / SERIES_FILE)}
    r2._write_json(out / "config.json", config_record(cfg, run2, run3, prov, parts.identity()))
    r2._write_json(out / JSON_FILE, metrics)
    metrics, config = (json.loads((out / n).read_text(encoding="utf-8")) for n in (JSON_FILE, "config.json"))
    (out / REPORT_FILE).write_text(render(metrics, config), encoding="utf-8", newline="\n")
    return metrics


# --- Entry points ------------------------------------------------------------------------------------------


def identity_of(cfg: AblationsConfig, run2: r3.Report2Run, run3: Report3Run, prov: dict[str, Any]) -> dict[str, Any]:
    return {"config": identity_config(cfg), "code_sha256": prov.get("code", {}).get("sha256"), "manifest_digest": prov.get("manifest_digest"),
            "report3_series_sha256": run3.sha256, "series_sha256": run2.sha256, "panel_fingerprint": run2.fingerprint}  # fmt: skip


def run(inputs: r3.Inputs | None, run2: r3.Report2Run, run3: Report3Run, cfg: AblationsConfig, out: Path, stage: str, *, prov: dict[str, Any],
        arms: Sequence[str] | None = None, log: Callable[[str], None] = lambda s: None, stop_after: int | None = None,
        driver: str | None = None) -> dict[str, Any] | None:  # fmt: skip
    """Run ``stage`` (fits, score or all) into ``out``, resuming the fits from ``out/parts``. Returns the metrics when the score ran."""
    if stage not in ("fits", "score", "all"):
        raise ValueError(f"unknown stage {stage!r}")
    check_against_report3(cfg, run3.cfg)
    check_rows(run2, run3)
    arms = tuple(arms or cfg.arms)
    if set(arms) - set(ABLATIONS):
        raise ValueError(f"unknown arms {sorted(set(arms) - set(ABLATIONS))}")
    started, started_at, stages = time.perf_counter(), datetime.now(UTC), {}
    identity = identity_of(cfg, run2, run3, prov)
    metrics = None
    if stage in ("fits", "all"):
        assert inputs is not None and inputs.data is not None
        parts = r3.Parts(out, identity, log=log, stop_after=stop_after)
        check_fit_order(parts, cfg, arms)
        log(f"fits: {len(arms)} arms x {len(cfg.seeds)} seeds x {len(cfg.years)} years (saved parts are skipped); parameters "
            + ", ".join(f"{a} {n:,}" for a, n in parameters(cfg).items()))  # fmt: skip
        t = time.perf_counter()
        with deterministic():
            run_fits(inputs.data, inputs.years, cfg, parts, arms, log=log, driver=driver)
        stages["fits"] = time.perf_counter() - t
    if stage in ("score", "all"):
        parts = r3.Parts(out, None, require=identity, log=log)
        t = time.perf_counter()
        metrics = write_score(run2, run3, cfg, parts, out, prov)
        stages["score"] = time.perf_counter() - t
        r2._write_json(out / "run.json", {"started_at": started_at.isoformat(timespec="seconds"), "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
                                          "seconds": round(time.perf_counter() - started, 1), "stages_seconds": {k: round(v, 1) for k, v in stages.items()},
                                          "fits_builds": fits_builds(parts, cfg)})  # fmt: skip
    return metrics


def verify_parts(out: Path, cfg: AblationsConfig) -> list[str]:
    """Every part of every arm in the folder verifies, every part of each arm scored is there, and no arm fitted whole is left out."""
    parts = r3.Parts(out, None)
    counts, problems = _inventory(parts, cfg)
    for a in cfg.arms:
        for sd in cfg.seeds:
            for y in cfg.years:
                key = part_key(a, sd, y)
                try:
                    if verified_part(parts, key, cfg) is None:
                        problems.append(f"{key}: not finished (no sealed part.json)")
                except r3.PartRefused:
                    pass  # listed by the inventory
    try:
        unscored(counts, cfg)
    except InventoryRefused as e:
        problems.append(str(e))
    return problems


def rebuild_config(recorded: Any, device: str) -> AblationsConfig:
    """The run's configuration from its ``config.json``; it must write back the same JSON."""

    def tup(v: Any) -> Any:
        return tuple(tup(x) for x in v) if isinstance(v, list) else v

    if not isinstance(recorded, Mapping):
        raise BindingRefused("config.json has no config: not an ablations run")
    cfg = AblationsConfig(**{k: tup(v) for k, v in recorded.items() if k != "registered"}, device=device)
    if config_json(cfg) != json.loads(json.dumps(dict(recorded))):
        raise BindingRefused("config.json's config does not round-trip through AblationsConfig: the run was made by other code")
    return cfg


def check(expected: Path, run2: r3.Report2Run, run3: Report3Run, prov: dict[str, Any], device: str = "cpu") -> int:
    """Verify the parts, re-bind enc-ols, re-run the score from the parts and compare every output byte for byte."""
    if not (expected / JSON_FILE).is_file() or not (expected / "config.json").is_file():
        print(f"{expected}: not an ablations run folder (no {JSON_FILE} or config.json)")
        return 2
    cfg = rebuild_config(json.loads((expected / "config.json").read_text(encoding="utf-8"))["config"], device)
    problems = verify_parts(expected, cfg)
    ident = r3.Parts(expected, None).identity()
    code, manifest = prov.get("code", {}).get("sha256"), prov.get("manifest_digest")
    if ident.get("code_sha256") != code or ident.get("manifest_digest") != manifest:
        problems.append(f"the fits ran at code digest {ident.get('code_sha256')} and data manifest {ident.get('manifest_digest')}, "
                        f"this check at code digest {code} and data manifest {manifest}")  # fmt: skip
    scratch = Path(tempfile.mkdtemp(prefix="ablations-check-"))
    try:
        if not problems or all(p.startswith("the fits ran at code digest") for p in problems):
            parts = r3.Parts(expected, None, require={"config": identity_config(cfg), "series_sha256": run2.sha256,
                                                      "report3_series_sha256": run3.sha256})  # fmt: skip
            write_score(run2, run3, cfg, parts, scratch, prov)
            for name in COMPARED:
                x, y = r2._read(expected, name), r2._read(scratch, name)
                if x != y:
                    problems.append(r2._file_summary(name, x, y, first="the run", second="the re-score"))
                    if name != SERIES_FILE and x is not None and y is not None:
                        problems.append(r2._unified(x, y, f"run/{name}", f"re-score/{name}", 40))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    if problems:
        print(f"CHECK FAILED: {len(problems)} problem(s) in {expected}")
        for p in problems:
            r2._print(p)
        return 1
    print(f"check passed: every part verifies, enc-ols is bound to Report n°3, and {len(COMPARED)} files are identical to {expected} (run.json excluded)")
    return 0


def _default_out(suffix: str = "ablations") -> Path:
    return runs_dir() / f"{datetime.now(UTC):%Y-%m-%d}-{suffix}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m olsprime.bench.ablations", description="LFM3's ablations and H6, against Report n°3's enc-ols.")
    parser.add_argument("--report3", type=Path, required=True, help="Report n°3's run folder")
    parser.add_argument("--sha256", required=True, help="the SHA-256 of its series.npz, as its report3.json records it")
    parser.add_argument("--series", type=Path, default=None, help="Report n°2's series.npz (the one Report n°3 paired with)")
    parser.add_argument("--report2-sha256", default=None, help="its SHA-256")
    parser.add_argument("--out", type=Path, default=None, help="run folder (default: <runs>/<UTC date>-ablations; a restart resumes it)")
    parser.add_argument("--stage", choices=("fits", "score", "all"), default="all")
    parser.add_argument("--arms", nargs="+", choices=ABLATIONS, default=None,
                        help="fits: restrict the stage to these arms, a prefix of the protocol's order unless the earlier arms are "
                             "fitted whole; score: the arms scored (an arm fitted whole must be scored)")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--driver", default=None, help="the GPU driver's version, recorded (no subprocess may ask nvidia-smi)")
    parser.add_argument("--check", type=Path, default=None, metavar="DIR", help="verify the parts and re-score DIR, byte for byte")
    parser.add_argument("--synthetic", action="store_true", help="read a report3 --synthetic folder and rebuild its synthetic panel")
    args = parser.parse_args(argv)
    log = lambda s: print(f"{datetime.now(UTC):%H:%M:%S} {s}", flush=True)  # noqa: E731
    if args.synthetic:
        if args.series is not None or args.report2_sha256 is not None:
            parser.error("--synthetic reads the report3 folder's own synthetic Report n°2 run")
        series = args.report3 / "report2-synthetic" / SERIES_FILE
        sha2 = json.loads((series.parent / "report2.json").read_text(encoding="utf-8"))["series"]["sha256"]
    else:
        if args.series is None or args.report2_sha256 is None:
            parser.error("--series and --report2-sha256 are required (or --synthetic)")
        series, sha2 = args.series, args.report2_sha256
    if args.device == "cuda" and args.check is None and args.stage in ("fits", "all") and not torch.cuda.is_available():
        parser.error("CUDA is not available: run in WSL2 with the CUDA environment, or pass --device cpu")
    from olsprime.train.determinism import apply

    apply()
    run2 = r3.read_report2(series, sha2)
    run3 = read_report3(args.report3, args.sha256, device=args.device)
    prov = prov_mod.record({}) if args.synthetic else prov_mod.record(prov_mod.current_manifest())  # before any data is read
    if args.check is not None:
        return check(args.check, run2, run3, prov, device=args.device)
    cfg3 = run3.cfg
    synthetic = (f"against the report3 --synthetic run {run3.sha256[:16]}: {cfg3.synthetic}" if args.synthetic else None)
    arms = tuple(a for a in ABLATIONS if a in (args.arms or ABLATIONS))  # the protocol's order
    cfg = AblationsConfig(arms=arms, seeds=cfg3.seeds, years=cfg3.years, device=args.device, encoder=cfg3.encoder, fit=cfg3.fit,
                          synthetic=synthetic)  # fmt: skip
    if not args.synthetic and cfg3.synthetic is not None:
        parser.error("Report n°3's run is a synthetic one: pass --synthetic")
    out = args.out or _default_out("ablations-smoke" if args.synthetic else "ablations")
    inputs = None
    if args.stage != "score":
        t = time.perf_counter()
        panel, bars = synthetic_panel(run2) if args.synthetic else r3.load_panel(run2.config)
        inputs = r3.build_inputs(run2, panel, bars, cfg3)
        log(f"panel of {panel.height} rows, windows built, {inputs.scored.size} scored rows paired with Report n°2's in {time.perf_counter() - t:.1f} s")
    metrics = run(inputs, run2, run3, cfg, out, args.stage, prov=prov, log=log, driver=args.driver)
    if metrics is not None:
        log(f"ablations written to {out}: H6 {metrics['h6']['status']}")
    else:
        log(f"stage {args.stage} done in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
