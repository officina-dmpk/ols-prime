"""Scratch, SYNTHETIC BARS ONLY: the auditor's own replacement rules, tested. (a) cancelled controls on every expression type,
against a mask-based prediction and against the verbal rule; (b) truncation under the propagation convention."""
import sys
from dataclasses import dataclass, replace as dc_replace, fields, is_dataclass
from typing import Any
from collections import Counter
import numpy as np, polars as pl
src = open(sys.argv[1], encoding="utf-8").read().split("leaks = adv.generate")[0]
if len(sys.argv) > 2:
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
class Cancel:   # x + (v - v): the draft's FP1
    x: Any
    v: Any
    binary = False
    def evaluate(self, view):
        v = self.v.evaluate(view)
        return self.x.evaluate(view) + (v - v)

@dataclass(frozen=True)
class Masked:   # the prediction: x, made missing where v is undefined. No arithmetic on v.
    x: Any
    v: Any
    binary = False
    def evaluate(self, view):
        return np.where(np.isnan(self.v.evaluate(view)), np.nan, self.x.evaluate(view))

CHILD = ("lhs", "rhs", "a", "b")
def future_nodes(e, path=()):
    out = []
    if isinstance(e, (adv.At, adv.Agg)) and max(e.offsets()) >= 1:
        out.append((path, e))
    for name in CHILD:
        if is_dataclass(e) and name in {f.name for f in fields(e)} and is_dataclass(getattr(e, name)):
            out += future_nodes(getattr(e, name), path + (name,))
    return out
def put(e, path, fn):
    if not path:
        return fn(e)
    return dc_replace(e, **{path[0]: put(getattr(e, path[0]), path[1:], fn)})
def get(e, path):
    for p in path:
        e = getattr(e, p)
    return e
def control(leak, wrap):
    fn = future_nodes(leak.expr)
    if not fn:
        return None
    reach = max(max(v.offsets()) for _, v in fn)
    path, v = next((p, v) for p, v in fn if max(v.offsets()) == reach)   # largest reach, first in lhs/rhs/a/b order
    t = leak.expr.twin()
    return adv.Leak(leak.id, leak.family, put(t, path, lambda node: wrap(node, v)), leak.output, leak.tags, twin=True), path, v

leaks = adv.generate(3000, 424242)
built = [(l, *control(l, Cancel)) for l in leaks if control(l, Cancel) is not None]
print("controls built:", len(built), "of", len(leaks), "| by root type:", dict(Counter(type(l.expr).__name__ for l, *_ in built)))
for name, bench in B.items():
    c, d = bench.n_cuts, len(bench.directions)
    ok_mask = ok_verbal = n_verbal = flagged = 0
    for l, ctl, path, v in built:
        act = eval_rule(ctl, bench)
        flagged += act.any()
        pred = eval_rule(control(l, Masked)[0], bench)
        ok_mask += np.array_equal(act, pred)
        if isinstance(l.expr, (adv.Logic, adv.WSum)):
            continue   # the verbal rule is stated for a single comparison or a single continuous function
        n_verbal += 1
        tw_ = l.honest_twin()
        T = np.broadcast_to(np.asarray(tw_.expr.evaluate(bench.view), dtype=np.float64), (c * (1 + d), adv.COMPARED))[:c]
        cond = (T > 0.5) if tw_.expr.binary else ~np.isnan(T)
        mv = np.isnan(np.broadcast_to(v.evaluate(bench.view), (c * (1 + d), adv.COMPARED)))
        rule = np.zeros(c, bool)
        for j in range(d):
            rule |= ((mv[:c] != mv[c * (1 + j): c * (2 + j)]) & cond & bench.scored).any(axis=1)
        ok_verbal += np.array_equal(act, rule)
    print(f"  {name:9s} flagged {int(flagged):5d} | mask prediction matches {ok_mask}/{len(built)} | verbal rule matches {ok_verbal}/{n_verbal}")

# (b) propagation convention for TRUNC-0: the output is missing where any read is missing
tb0 = B["TRUNC0"]
full = part = 0; never = Counter()
for l in leaks:
    rec = adv.RecordingView(tb0.view); l.expr.evaluate(rec)
    m = np.zeros((2 * C, adv.COMPARED), bool)
    for q, o in rec.reads:
        m |= np.isnan(tb0.view.at(q, o))
    cut = ((m[C:] & ~m[:C]) & tb0.scored).any(axis=1)
    full += cut.all(); part += cut.any()
    if not cut.all():
        never[l.tag["quantity"]] += 1
print("propagation: flagged at every cut", full, "| at one cut at least", part, "of", len(leaks), "| not at every cut, by quantity:", dict(never.most_common(4)))
