"""Audit 5b, X11: TRUNC-0 and TRUNC-1 by really truncating the bars (a SeriesView of bars.head), under G, M and P, on both
schedules, against the module's windowed flags. Development seeds, degraded synthetic bars. No data read."""
import sys
import numpy as np
from olsprime.bench import adversary as adv, detectors as det

TABLE, N = sys.argv[1], int(sys.argv[2])
cfg = det.DetectorConfig(population_seed=51118, two_run_seed=51119, placement="quantile", n=N, two_run_runs=1, sigmas=(0.1,))
bars = det.synthetic_pairs(degrade=True)
b = det.build_benches(bars, cfg)
leaks = adv.generate(N, 51118, placement="quantile", table_path=TABLE)
extras = {p: det.extra_quantities(x, i) for i, (p, x) in enumerate(bars.items())}
full = {p: adv.SeriesView({**adv.quantities(x), **extras[p]}) for p, x in bars.items()}
cut_views = {}
def view_at(p, at):  # the input really ends at bar `at`
    if (p, at) not in cut_views:
        head = bars[p].head(at + 1)
        cut_views[(p, at)] = adv.SeriesView({**adv.quantities(head), **{k: v[: at + 1] for k, v in extras[p].items()}})
    return cut_views[(p, at)]

def moved(a, c):
    both = ~np.isnan(a) & ~np.isnan(c)
    return (np.where(both, np.abs(a - c), 0.0) > 1e-9) | (np.isnan(a) != np.isnan(c))

bad = {"TRUNC-0": 0, "TRUNC-1": 0}; units = 0; reach1 = [0, 0]
for leak in leaks:
    for conv in ("G", "M", "P"):
        got = det.judge_window(leak, b.trunc, conv).cut_flags[:, 0]
        orig = {p: adv.outputs_under(leak, full[p], conv) for p in bars}
        for part, shift in (("TRUNC-0", 0), ("TRUNC-1", 1)):
            for j, i in enumerate(b.trunc_parts[part]):
                c = b.cuts[j]; p = c["pair"]; at = c["index"] + shift
                sc = b.schedules[p].scored
                rows = np.arange(at - 10, at + 1); rows = rows[sc[rows]]
                run = adv.outputs_under(leak, view_at(p, at), conv)
                flag = False
                for k in orig[p]:
                    x = np.broadcast_to(np.asarray(orig[p][k], float), (bars[p].height,))[rows]
                    y = np.broadcast_to(np.asarray(run[k], float), (at + 1,))[rows]
                    flag |= bool(moved(x, y).any())
                units += 1
                if flag != bool(got[i]): bad[part] += 1
                if conv == "G" and c["schedule"] == "h1" and part == "TRUNC-1" and leak.reach()[1] == 1:
                    reach1[0] += 1; reach1[1] += int(flag)
print("units", units, "disagreements", bad, "| reach-1 leaks x H1 cuts flagged by TRUNC-1 (G):", reach1)
