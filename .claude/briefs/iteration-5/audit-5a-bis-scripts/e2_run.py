exec(open(__import__("os").path.join(__import__("os").path.dirname(__file__), "e1.py"), encoding="utf-8").read())
from collections import Counter
from dataclasses import replace as rp

def or_mask(expr, v):
    rv = adv.RecordingView(v); expr.evaluate(rv)
    m = np.zeros((2 * C, adv.COMPARED), bool)
    for q, o in rv.reads:
        m |= np.isnan(v.at(q, o))
    return m

def eval_P(expr, v):
    """Strict propagation: a binary node is missing wherever any read under it is missing; value nodes as coded."""
    if isinstance(expr, adv.WSum):
        return expr.w1 * eval_P(expr.a, v) + expr.w2 * eval_P(expr.b, v)
    x = np.broadcast_to(np.asarray(expr.evaluate(v), np.float64), (2 * C, adv.COMPARED)).copy()
    if expr.binary:
        x[or_mask(expr, v)] = np.nan
    else:
        x = adv._clean(x)
    return x

# --- Experiment 2: P. (a) output missing exactly where the read mask is set? (b) the assertion as worded
mis = Counter(); notflag_worded = Counter(); nleak = Counter()
exc_fail = []
for l in leaks:
    x = eval_P(l.expr, view)
    m = or_mask(l.expr, view)
    root = type(l.expr).__name__
    nleak[root] += 1
    if ((np.isnan(x) != m) & np.concatenate([scored, scored])).any():
        mis[root] += 1
    a, b = x[:C], x[C:]
    flagged_cut = (rule(a, b) & scored).any(axis=1)          # output mapping is injective: verdict of x = verdict of outputs
    # worded exception: at every scored compared row where truncation removes a read, the ORIGINAL already has an undefined read
    rv = adv.RecordingView(view); l.expr.evaluate(rv)
    removed = np.zeros((C, adv.COMPARED), bool)
    for q, o in rv.reads:
        na, nb = np.isnan(view.at(q, o)[:C]), np.isnan(view.at(q, o)[C:])
        removed |= (~na & nb)
    live = removed & scored
    exception = ~(live & ~m[:C]).any(axis=1)                 # no live row with all original reads defined
    predicted = ~exception
    if not np.array_equal(predicted, flagged_cut):
        exc_fail.append(l); notflag_worded[root] += 1
print(f"[E2a] leaks whose P output is missing somewhere the read mask is not set (or the reverse), by root: {dict(mis)} of {dict(nleak)}")
print(f"[E2b] P's assertion as worded (undefined READ) disagrees with the flags for {len(exc_fail)} leaks, by root {dict(notflag_worded)}")
for l in exc_fail[:3]:
    print("     e.g.", l.render()[:140])

# --- Experiment 3: M on a single Cmp against G on its mirror, row by row, both outputs
def out_map(x, output):
    x = np.asarray(x, np.float64)
    return [x] if output == "target" else [0.8 * expit(-(2 * x - 1)), 0.8 * expit(2 * x - 1)]

def row_flags(xa, xb, output):
    m = np.zeros((C, adv.COMPARED), bool)
    for a, b in zip(out_map(xa, output), out_map(xb, output)):
        m |= rule(a, b)
    return m & scored

cmp_leaks = [l for l in leaks if isinstance(l.expr, adv.Cmp)]
row_diff = cut_diff = any_diff = 0; nontie = 0; by_out = Counter(); tie_rows = 0
for l in cmp_leaks:
    e = l.expr
    a = np.broadcast_to(np.asarray(e.lhs.evaluate(view), np.float64), (2 * C, adv.COMPARED))
    b = e.margin * np.broadcast_to(np.asarray(e.rhs.evaluate(view), np.float64), (2 * C, adv.COMPARED))
    miss = np.isnan(a) | np.isnan(b)
    with np.errstate(invalid="ignore"):
        gt, lt = a > b, a < b
    L_G = gt if e.op == ">" else lt
    Lm_G = lt if e.op == ">" else gt            # the mirror under G
    L_M = L_G | miss                            # the leak under M (both runs)
    fM = row_flags(L_M[:C], L_M[C:], l.output)
    fGm = row_flags(Lm_G[:C], Lm_G[C:], l.output)
    d = fM != fGm
    if d.any():
        row_diff += int(d.sum()); cut_diff += int((fM.any(axis=1) != fGm.any(axis=1)).sum()); any_diff += int(fM.any() != fGm.any()); by_out[l.output] += 1
        tie = (~miss[:C]) & (a[:C] == b[:C])
        tie_rows += int((d & tie).sum()); nontie += int((d & ~tie).sum())
print(f"[E3] single Cmp leaks: {len(cmp_leaks)} ({dict(Counter(l.output for l in cmp_leaks))}); M-on-leak vs G-on-mirror differ at {row_diff} rows "
      f"(at an exact tie in the original run: {tie_rows}; elsewhere: {nontie}); cut verdict differs {cut_diff}; any-cut verdict differs {any_diff}; leaks by output {dict(by_out)}")
