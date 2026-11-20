"""The quantile table of iteration 5's `quantile` placement (prereg-draft.md §1.4).

A logged contact with the training bars: BTCUSDT and ETHUSDT daily, read through the seal,
rows with open_time < 2019-01-01 UTC only. Run once by the orchestrator on 2026-11-18:

    cd python && uv run python ../.claude/briefs/iteration-5/quantile_table.py

Writes runs/2026-11-18-quantile-table/table.json and summary.json. Wave 3 moves `build_table`
into bench/adversary.py; a test checks the digest.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl

from olsprime.bench.adversary import BANDS, quantities
from olsprime.bench.invariance import development_bars
from olsprime.protocol import load_klines

PAIRS = ("BTCUSDT", "ETHUSDT")
TABLE_QUANTITIES = (
    "body", "upper_wick", "lower_wick", "range", "fill", "close_location",
    "taker_base_share", "taker_quote_share", "wick_ratio",
)  # fmt: skip
POSITIVE_ONLY = frozenset({"body", "upper_wick", "lower_wick", "range"})
END = datetime(2019, 1, 1, tzinfo=UTC)
LEVELS = (0.02, 0.98)


def build_table(bars_by_pair: dict[str, pl.DataFrame]) -> dict[str, np.ndarray]:
    """Sorted kept values of each quantity, both pairs pooled (finite; strictly positive for POSITIVE_ONLY)."""
    pooled: dict[str, list[np.ndarray]] = {q: [] for q in TABLE_QUANTITIES}
    for pair in PAIRS:
        q = quantities(bars_by_pair[pair])
        for name in TABLE_QUANTITIES:
            x = q[name][np.isfinite(q[name])]
            if name in POSITIVE_ONLY:
                x = x[x > 0]
            pooled[name].append(x)
    return {k: np.sort(np.concatenate(v)).astype(np.float64) for k, v in pooled.items()}


def table_bytes(table: dict[str, np.ndarray]) -> bytes:
    """JSON, sorted keys, each value written with repr, no spaces."""
    body = ",".join(f'"{k}":[' + ",".join(repr(float(v)) for v in table[k]) + "]" for k in sorted(table))
    return ("{" + body + "}").encode("ascii")


def band_share(values: np.ndarray, lo: float, hi: float) -> float:
    """Share of levels uniform on LEVELS whose linear quantile falls in [lo, hi), by a fine grid of levels."""
    levels = np.linspace(LEVELS[0], LEVELS[1], 960_001)
    c = np.quantile(values, levels, method="linear")
    return float(np.mean((c >= lo) & (c < hi)))


def main() -> None:
    bars = {}
    rows = {}
    for pair in PAIRS:
        b = development_bars(load_klines(pair, "1d", caller="iteration-5 quantile table"))
        b = b.filter(pl.col("open_time") < END)
        bars[pair] = b
        rows[pair] = {"rows": b.height, "first": str(b["open_time"][0]), "last": str(b["open_time"][-1])}
    table = build_table(bars)
    raw = table_bytes(table)
    out = Path(__file__).resolve().parents[3] / "runs" / "2026-11-18-quantile-table"
    out.mkdir(parents=True, exist_ok=True)
    (out / "table.json").write_bytes(raw)
    summary = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "method": "np.quantile(values, level, method='linear'); level ~ U[0.02, 0.98]",
        "rows": rows,
        "values_kept": {k: int(v.size) for k, v in table.items()},
        "range_at_levels": {k: [float(np.quantile(v, LEVELS[0])), float(np.quantile(v, LEVELS[1]))] for k, v in table.items()},
        "share_inside_band": {k: band_share(table[k], *BANDS[k]) for k in BANDS},
        "bands": {k: list(v) for k, v in BANDS.items()},
        "utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
