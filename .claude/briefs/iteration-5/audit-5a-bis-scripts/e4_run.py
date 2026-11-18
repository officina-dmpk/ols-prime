"""Scratch 5a-bis, SYNTHETIC BARS ONLY. The TWO-RUN repair of prereg-draft v2 section 2.5, implemented literally. Neutral seed 777."""
exec(open(__import__("os").path.join(__import__("os").path.dirname(__file__), "e1.py"), encoding="utf-8").read().split("leaks = adv.generate")[0])
from olsprime.bench.perturb import PERTURBED_COLUMNS, _check_valid, _candle
print("PERTURBED_COLUMNS:", PERTURBED_COLUMNS)

def two_run(df, t, sigma, z):
    n = df.height
    rows = np.arange(t + 1, min(t + 11, n))
    z = z[: rows.size]
    col = {c: df[c].cast(pl.Float64).to_numpy().copy() for c in PERTURBED_COLUMNS}
    f = {c: np.exp(sigma * z[:, i]) for i, c in enumerate(PERTURBED_COLUMNS)}
    o, h, lo, c = (col[k][rows] for k in ("open", "high", "low", "close"))
    o2, c2 = o * f["open"], c * f["close"]
    _, uw, lw = _candle(o, h, lo, c)
    uw2, lw2 = uw * f["high"], lw * f["low"]
    h2 = np.maximum(o2, c2) * np.exp(uw2)
    lo2 = np.minimum(o2, c2) * np.exp(-lw2)
    v, qv, tb, tq, tr = (col[k][rows] for k in ("volume", "quote_volume", "taker_buy_base_volume", "taker_buy_quote_volume", "trades"))
    has = v > 0
    with np.errstate(divide="ignore", invalid="ignore"):
        vwap = np.where(has, qv / v, np.nan)
    v2 = np.where(has, v * f["volume"], 0.0)
    raw = vwap * f["quote_volume"]
    vw2 = np.clip(raw, lo2, h2)
    clipped = has & (raw != vw2)
    q2 = np.where(has, v2 * vw2, 0.0)
    tb_raw, tq_raw = tb * f["taker_buy_base_volume"], tq * f["taker_buy_quote_volume"]
    tb2 = np.where(has, np.minimum(tb_raw, v2), 0.0)
    tq2 = np.where(has, np.minimum(tq_raw, q2), 0.0)
    tr2 = np.where(has, np.maximum(np.rint(tr * f["trades"]), 1.0), 0.0)
    new = {"open": o2, "high": h2, "low": lo2, "close": c2, "volume": v2, "quote_volume": q2,
           "taker_buy_base_volume": tb2, "taker_buy_quote_volume": tq2, "trades": tr2}
    for k in col:
        col[k][rows] = new[k]
    out = df.with_columns([pl.Series(k, np.rint(x).astype(np.int64) if k == "trades" else x, dtype=df.schema[k]) for k, x in col.items()])
    stats = dict(bars=int(has.sum()), clipped=int(clipped.sum()), tb_cap=int((has & (tb_raw > v2)).sum()), tq_cap=int((has & (tq_raw > q2)).sum()),
                 trades_same=int((has & (tr2 == tr)).sum()))
    # the VWAP assertion on the STORED columns, exact
    with np.errstate(divide="ignore", invalid="ignore"):
        rec = q2 / v2
    stats["vwap_out_exact"] = int((has & ((rec < lo2) | (rec > h2))).sum())
    stats["vwap_out_1e-12"] = int((has & ((rec < lo2 * (1 - 1e-12)) | (rec > h2 * (1 + 1e-12)))).sum())
    return out, rows, stats

for sigma in (0.1, 1.0):
    tot = {}; valid_fail = 0; wr_change = 0; wr_n = 0; pos_wick_lost = 0; body = []; fill = []
    for pair, k, t, n in C_list:
        for run in range(1, 9):
            z = np.random.default_rng([777, zlib.crc32(pair.encode("ascii")), 1, k, run]).standard_normal((10, 9))
            out, rows, st = two_run(bars[pair], t, sigma, z)
            for a, b in st.items():
                tot[a] = tot.get(a, 0) + b
            try:
                _check_valid(out, t)
            except AssertionError as e:
                valid_fail += 1; last = str(e)
            q0, q1 = adv.quantities(bars[pair]), adv.quantities(out)
            wr_change += int((np.isnan(q0["wick_ratio"][rows]) != np.isnan(q1["wick_ratio"][rows])).sum()); wr_n += rows.size
            pos_wick_lost += int(((q0["upper_wick"][rows] > 0) & ~(q1["upper_wick"][rows] > 0)).sum() + ((q0["lower_wick"][rows] > 0) & ~(q1["lower_wick"][rows] > 0)).sum())
            body.append(q1["body"][rows]); fill.append(q1["fill"][rows])
            assert all(out[c][: t + 1].equals(bars[pair][c][: t + 1]) for c in PERTURBED_COLUMNS)
    body, fill = np.concatenate(body), np.concatenate(fill)
    b = tot["bars"]
    print(f"[E4] sigma {sigma}: perturbed bars with volume {b}; VWAP clip binds {tot['clipped']/b:.1%}; recomputed quote'/v' outside [lo',h'] exactly: {tot['vwap_out_exact']} "
          f"({tot['vwap_out_exact']/b:.1%}), beyond 1e-12: {tot['vwap_out_1e-12']}; taker base cap binds {tot['tb_cap']/b:.1%}, taker quote cap {tot['tq_cap']/b:.1%}; "
          f"trades unchanged {tot['trades_same']}; _check_valid failures {valid_fail} of {len(C_list)*8}" + (f" ({last})" if valid_fail else ""))
    print(f"      wick_ratio definedness changed in {wr_change} of {wr_n} bars; positive wicks lost {pos_wick_lost}; perturbed body median {np.nanmedian(body):.3f} "
          f"(original {np.nanmedian(adv.quantities(bars['BTCUSDT'])['body']):.3f}); fill median {np.nanmedian(fill):.2f} (original {np.nanmedian(adv.quantities(bars['BTCUSDT'])['fill']):.2f})")
