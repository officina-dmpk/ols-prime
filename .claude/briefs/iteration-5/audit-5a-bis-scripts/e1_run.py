exec(open(__import__("os").path.join(__import__("os").path.dirname(__file__), "e1.py"), encoding="utf-8").read())
from collections import Counter
# --- Experiment 1: section 4.4's OR mask against a per-read comparison, TRUNC-0 under G
bad_leaks, bad_rows, tot_rows, per_read_bad = [], 0, 0, 0
roots = Counter()
for l in leaks:
    f = flags_G(l)
    if not f.any():
        continue
    R = reads_of(l)
    nan = np.stack([np.isnan(view.at(q, o)) for q, o in R])  # (reads, 2C, 11)
    a, b = nan[:, :C], nan[:, C:]
    or_diff = a.any(axis=0) != b.any(axis=0)
    read_diff = (a != b).any(axis=0)
    tot_rows += int(f.sum())
    w = f & ~or_diff
    per_read_bad += int((f & ~read_diff).sum())
    if w.any():
        bad_rows += int(w.sum()); bad_leaks.append(l); roots[type(l.expr).__name__ + ":" + getattr(l.expr, "op", "")] += 1
print(f"[E1] TRUNC-0 (G): flagged rows {tot_rows}; flagged rows whose OR mask is equal in both runs: {bad_rows}, in {len(bad_leaks)} of {N} leaks; by root {dict(roots)}")
print(f"[E1] flagged rows with no read whose missingness differs (per-read rule): {per_read_bad}")
for l in bad_leaks[:3]:
    print("     e.g.", l.render()[:150])
