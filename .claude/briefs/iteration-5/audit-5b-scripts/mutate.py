"""Audit 5b: build mutated scratch copies (never the repository). Usage: mutate.py <scratch>"""
import shutil, sys
from pathlib import Path
S = Path(sys.argv[1])
MUTS = {
  "m1_trunc0_one_bar_late": ("olsprime/bench/detectors.py", "v[adv.PAST_REACH + 1 :] = np.nan", "v[adv.PAST_REACH + 2 :] = np.nan"),
  "m2_tworun_volume_unperturbed": ("olsprime/bench/detectors.py", 'v2 = v * f["volume"]', "v2 = v * 1.0"),
  "m3a_tworun_runs_3_to_8_reuse_run_2": ("olsprime/bench/detectors.py", "out, st = two_run_bars(bars, c[\"index\"], sigma, zs[r])", "out, st = two_run_bars(bars, c[\"index\"], sigma, zs[min(r, 2)])"),
  "m3b_tworun_long_schedule_id_1": ("olsprime/bench/detectors.py", 'zs = {r: two_run_z(cfg.two_run_seed, p, SCHEDULE_ID[c["schedule"]], c["k"], r)', 'zs = {r: two_run_z(cfg.two_run_seed, p, 1, c["k"], r)'),
  "m4_moved_threshold_1e-6": ("olsprime/bench/detectors.py", "return (change > inv.CAUGHT_ABOVE) | (np.isnan(a) != np.isnan(b))", "return (change > 1e-6) | (np.isnan(a) != np.isnan(b))"),
  "m5_retile_one_tile_input": ("olsprime/bench/detectors.py", "            tiles[k][j, length - 2 * tau :] = q[k]\n", "            tiles[k][j, length - 2 * tau :] = q[k]\n            tiles[k][j, : length - tau] = np.nan\n"),
  "m7_colour_under_M_is_G": ("olsprime/bench/adversary.py", "            return _atom(x > 0.5, np.isnan(x), c)", "            return _atom(x > 0.5, np.isnan(x) & (c != \"M\"), c)"),
  "m8_fi_m2_rule_every_cut": ("olsprime/bench/detectors.py", 'return not float(bars["high"][t + 1]) < 2.0 / 3.0 * float(bars["close"][t])', "return True"),
  "m16_h15_deciding_cell_is_trunc1": ("olsprime/bench/detectors.py", 'deciding = diff(denominators["all"], "TRUNC-0")', 'deciding = diff(denominators["all"], "TRUNC-1/G")'),
  "m17_union_without_shuffle": ("olsprime/bench/detectors.py", 'union = anyc["FI"] | anyc["TRUNC-0"] | anyc["TWO-RUN"] | anyc["SHUFFLE"]', 'union = anyc["FI"] | anyc["TRUNC-0"] | anyc["TWO-RUN"]'),
  "m18_tworun_wick_wrong_factor": ("olsprime/bench/detectors.py", 'uw2, lw2 = uw * f["high"], lw * f["low"]', 'uw2, lw2 = uw * f["low"], lw * f["low"]'),
  "m19_trunc1_is_trunc0": ("olsprime/bench/detectors.py", 'entries.append(("TRUNC-1", c, t1))', 'entries.append(("TRUNC-1", c, c["index"]))'),
  "m20_fi_x3_is_column_1": ("olsprime/bench/detectors.py", 'out[f"FI x3{suffix}"], out[f"FI /3{suffix}"] = fi[:, :, 0], fi[:, :, 1]', 'out[f"FI x3{suffix}"], out[f"FI /3{suffix}"] = fi[:, :, 1], fi[:, :, 0]'),
  "m21_twin_check_h1_rule_only": ("olsprime/bench/detectors.py", "moved = int(r.flags.any() or r.bits.any())", "moved = int(r.flags.any())"),
  "m22_p_is_kleene_in_logic": ("olsprime/bench/adversary.py", "        return np.where(np.isnan(x) | np.isnan(y), np.nan, op(x == 1.0, y == 1.0).astype(np.float64))", "        return np.where((np.isnan(x) | np.isnan(y)) & ~((e.op == \"AND\") & ((x == 0.0) | (y == 0.0))), np.nan, op(x == 1.0, y == 1.0).astype(np.float64))"),
}
for name, (rel, old, new) in MUTS.items():
    dst = S / "mut" / name / "python"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(S / "base" / "python", dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    f = dst / rel
    text = f.read_text(encoding="utf-8")
    assert text.count(old) == 1, (name, text.count(old))
    f.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    print("built", name)
