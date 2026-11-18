"""Scratch, SYNTHETIC BARS ONLY: the cancelled controls FP1 / FP2 of the draft, one reading of them, against its predicted verdicts."""
import sys
from dataclasses import dataclass
from typing import Any
import numpy as np, polars as pl
from collections import Counter
src = open(sys.argv[1], encoding="utf-8").read().split("leaks = adv.generate")[0]
ZERO_WICK = len(sys.argv) > 2
if ZERO_WICK:  # a variant of the synthetic bars: 3 % of bars with a zero upper wick (high == max(open, close)), as real bars can have
    src = src.replace("bars = tw.synthetic_pairs()", "bars = zero_wick(tw.synthetic_pairs())")
def zero_wick(b):
    out = {}
    for p, df in b.items():
        rng = np.random.default_rng(5 if p == "BTCUSDT" else 6)
        hit = rng.random(df.height) < 0.03
        top = np.maximum(df["open"].to_numpy(), df["close"].to_numpy())
        out[p] = df.with_columns(pl.Series("high", np.where(hit, top, df["high"].to_numpy())))
    return out
exec(src)

@dataclass(frozen=True)
class Cancel:
    x: Any
    v: Any
    binary = False
    def evaluate(self, view):
        v = self.v.evaluate(view)
        return self.x.evaluate(view) + (v - v)

@dataclass(frozen=True)
class Dominated:
    x: Any
    v: Any
    fn: str
    binary = False
    def evaluate(self, view):
        x = self.x.evaluate(view)
        return getattr(np, self.fn)(x, x + 0.0 * self.v.evaluate(view))

def control(leak, kind):
    e = leak.expr
    if isinstance(e, adv.Cmp) and isinstance(e.lhs, (adv.At, adv.Agg)) and max(e.lhs.offsets()) >= 1:
        t = e.twin()
        lhs = Cancel(t.lhs, e.lhs) if kind == "FP1" else Dominated(t.lhs, e.lhs, kind)
        return adv.Leak(leak.id, leak.family, adv.Cmp(lhs, t.op, t.margin, t.rhs), leak.output, leak.tags, twin=True)
    if isinstance(e, adv.LogRatio) and isinstance(e.a, (adv.At, adv.Agg)) and max(e.a.offsets()) >= 1:
        t = e.twin()
        a = Cancel(t.a, e.a) if kind == "FP1" else Dominated(t.a, e.a, kind)
        return adv.Leak(leak.id, leak.family, adv.LogRatio(a, t.b), leak.output, leak.tags, twin=True)
    if isinstance(e, adv.Raw) and max(e.a.offsets()) >= 1:
        t = e.twin()
        a = Cancel(t.a, e.a) if kind == "FP1" else Dominated(t.a, e.a, kind)
        return adv.Leak(leak.id, leak.family, adv.Raw(a), leak.output, leak.tags, twin=True)
    return None

leaks = adv.generate(3000, 424242)
for kind in ("FP1", "minimum", "fmin"):
    cs = [(l, control(l, kind)) for l in leaks]
    cs = [(l, c) for l, c in cs if c is not None]
    print()
    print(kind, "controls built:", len(cs), "binary:", sum(c.expr.binary for _, c in cs))
    for name, bench in B.items():
        flagged = np.array([eval_rule(c, bench).any() for _, c in cs])
        fin = np.array([eval_rule(c, bench, True).any() for _, c in cs])
        isbin = np.array([c.expr.binary for _, c in cs])
        vq = Counter((l.expr.lhs.q if isinstance(l.expr, adv.Cmp) else l.expr.a.q) for (l, _), f in zip(cs, flagged) if f)
        line = f"  {name:9s} flagged {int(flagged.sum()):5d} (binary {int((flagged & isbin).sum())}, continuous {int((flagged & ~isbin).sum())}); still flagged under the finite-only rule {int(fin.sum())}"
        if name in ("FI", "TWORUN.1", "TWORUN1", "SHUFFLE") and flagged.any():
            line += f"; by quantity of v: {dict(vq)}"
        print(line)
        if name == "TRUNC0" and kind == "FP1":
            # the exact rule for a binary control: flagged at a cut iff the twin itself is True at a live scored row
            ok = 0; nb = 0
            for l, c in cs:
                if not c.expr.binary:
                    continue
                nb += 1
                j = max(l.expr.lhs.offsets())
                x = np.asarray(l.honest_twin().expr.evaluate(h1.view), dtype=bool)[:C]
                live = np.zeros((C, adv.COMPARED), bool); live[:, adv.COMPARED - j:] = True
                ok += np.array_equal((x & live & h1.scored).any(axis=1), eval_rule(c, bench))
            print("            binary FP1 under TRUNC0: flagged iff the twin is True at a live scored row -> holds for", ok, "of", nb)
