exec(open(__import__("os").path.join(__import__("os").path.dirname(__file__), "e1.py"), encoding="utf-8").read())
from collections import Counter
# --- E3 coverage: rows where an operand is ALREADY undefined in the original and truncation removes a read
cmp_leaks = [l for l in leaks if isinstance(l.expr, adv.Cmp)]
rows_exercised = leaks_exercised = 0; flagged_there_M = flagged_there_Gm = 0
for l in cmp_leaks:
    e = l.expr
    rv = adv.RecordingView(view); e.evaluate(rv)
    removed = np.zeros((C, adv.COMPARED), bool); undef0 = np.zeros((C, adv.COMPARED), bool)
    for q, o in rv.reads:
        x = view.at(q, o); na, nb = np.isnan(x[:C]), np.isnan(x[C:])
        removed |= (~na & nb); undef0 |= na
    hit = removed & undef0 & scored
    if hit.any():
        rows_exercised += int(hit.sum()); leaks_exercised += 1
        a = np.broadcast_to(np.asarray(e.lhs.evaluate(view), np.float64), (2 * C, adv.COMPARED))
        b = e.margin * np.broadcast_to(np.asarray(e.rhs.evaluate(view), np.float64), (2 * C, adv.COMPARED))
        miss = np.isnan(a) | np.isnan(b)
        with np.errstate(invalid="ignore"):
            gt, lt = a > b, a < b
        L_M = (gt if e.op == ">" else lt) | miss; Lm = lt if e.op == ">" else gt
        flagged_there_M += int(((L_M[:C] != L_M[C:]) & hit).sum()); flagged_there_Gm += int(((Lm[:C] != Lm[C:]) & hit).sum())
print(f"[E3c] single Cmp: scored rows with an operand already undefined in the original AND a read removed by truncation: {rows_exercised} rows in {leaks_exercised} leaks; "
      f"flagged there under M: {flagged_there_M}, under G on the mirror: {flagged_there_Gm}")

# --- E5: the faithful TRUNC-1 = TRUNC-0 at the cut t+1, compared rows t-9..t+1
sc_by_pair = {}
from olsprime.bench import pipeline as pp
from olsprime.data.binance_vision import Month
W1o, W1t, S1 = [], [], []
for pair, k, t, n in C_list:
    if pair not in sc_by_pair:
        h1 = cfg.h1; frame = pp.build_frame(bars[pair], h1.interval, h1.h)
        folds = pp.make_folds(frame, h1.interval, h1.h, Month(*h1.start), Month(*h1.end))
        sc = np.zeros(n, bool); sc[adv.scored_rows(folds)] = True; sc_by_pair[pair] = (sc, adv.quantities(bars[pair]))
    sc, q0 = sc_by_pair[pair]
    w = adv._window(q0, t + 1); W1o.append(w)
    wt = {q: v.copy() for q, v in w.items()}
    for q in wt: wt[q][T + 1:] = np.nan
    W1t.append(wt)
    rows = t + 1 - adv.FUTURE_REACH + np.arange(adv.COMPARED)
    S1.append(sc[rows])
S1 = np.stack(S1)
print("[E5] row t+1 scored at each synthetic H1 cut:", S1[:, -1].tolist(), "| last scored row", int(np.flatnonzero(sc)[-1]), "height", n)
v1 = adv.WindowView({q: np.stack([w[q] for w in W1o] + [w[q] for w in W1t]) for q in adv.QUANTITY_NAMES})
def flags1(leak):
    m = np.zeros((C, adv.COMPARED), bool)
    for arr in leak.outputs(v1).values():
        arr = np.broadcast_to(np.asarray(arr, np.float64), (2 * C, adv.COMPARED)); m |= rule(arr[:C], arr[C:])
    return m & S1
reach = np.array([l.reach()[1] for l in leaks])
f0 = np.stack([flags_G(l).any(axis=1) for l in leaks]); f1 = np.stack([flags1(l).any(axis=1) for l in leaks])
print(f"[E5] faithful TRUNC-1 on reach-1 leaks: caught {int(f1[reach == 1].any(axis=1).sum())} of {int((reach == 1).sum())} (v1's arm: 0). "
      f"any-cut: TRUNC-0 {f0.any(axis=1).mean():.4f}, TRUNC-1 {f1.any(axis=1).mean():.4f}; any-cut verdicts differ for {int((f0.any(axis=1) != f1.any(axis=1)).sum())} leaks; "
      f"caught by TRUNC-1 only {int((f1.any(axis=1) & ~f0.any(axis=1)).sum())}, TRUNC-0 only {int((f0.any(axis=1) & ~f1.any(axis=1)).sum())}")
tw_bad = sum(flags1(l.honest_twin()).any() for l in leaks[:800])
print("[E5] honest twins flagged by the faithful TRUNC-1:", tw_bad, "of 800")
# M1 (gated on rows t-10..t of the cuts) under the faithful TRUNC-1: the gate is true at row t+1
x = v1.at("close", 1) > v1.at("close", 0)           # close[s+1] > close[s] at rows t-9..t+1
gate = np.zeros((2 * C, adv.COMPARED), bool); gate[:, -1] = True     # only row t+1 lies outside the masked rows
out = (x & gate).astype(float)
m1 = (rule(out[:C], out[C:]) & S1).any(axis=1)
print("[E5] hand-written M1 (masked on t-10..t only) flagged by the faithful TRUNC-1 at", int(m1.sum()), "of", C, "cuts")
