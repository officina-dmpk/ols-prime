"""Audit phase 2a, A6: do the counts of check_classes respond to a planted miss? (Minor 3 of pass 5b-bis, deferred.)

On synthetic bars only, with the development seeds. The source is not changed: the verdicts that check_classes
reads are altered in memory, one plant at a time, and the count of disagreements must move by the planted amount.
Plants: a missed flag of M1 under P (lines 1016 and 1018); a flag at a cut that cannot flag (1016); a flag of M1
under G (1012); a missed FI flag on M2 at a predicted cut (1031).

Run from python/:  python ../.claude/briefs/iteration-5/audit-2a-scripts/a6_classes_probe.py
"""
import numpy as np

from olsprime.bench import detectors as det

cfg = det.DetectorConfig(population_seed=51118, two_run_seed=51119)
b = det.build_benches(det.synthetic_pairs(), cfg)
base = det.check_classes(b)
print("baseline: pass", base["pass"], "| disagreements", base["disagreements"])
print("baseline reported:", {k: v for k, v in base["reported"].items() if k.startswith(("M1 h1", "M2 FI"))})

real_cut_verdicts, real_cannot = det.cut_verdicts, det.truncation_cannot_flag


def with_plant(call_number, plant, cannot=None):
    """check_classes with the verdicts of its call_number-th cut_verdicts call altered by plant (1: M1 h1, 4: M2)."""
    seen = {"n": 0}

    def fake(rows, benches, **kw):
        v = real_cut_verdicts(rows, benches, **kw)
        seen["n"] += 1
        if seen["n"] == call_number and plant is not None:
            v = {k: x.copy() for k, x in v.items()}
            plant(v)
        return v

    det.cut_verdicts = fake
    if cannot is not None:
        det.truncation_cannot_flag = cannot
    try:
        return det.check_classes(b)
    finally:
        det.cut_verdicts, det.truncation_cannot_flag = real_cut_verdicts, real_cannot


def clear(key, cut):
    def plant(v):
        assert v[key][cut].any(), ("nothing to clear", key, cut)
        v[key][cut] = False
    return plant


def raise_(key, cut):
    def plant(v):
        assert not v[key][cut].any(), ("already set", key, cut)
        v[key][cut, 0] = True
    return plant


def cannot_at(key_wanted, schedule_wanted, cut):
    def fake(benches, key, schedule):
        out = real_cannot(benches, key, schedule).copy()
        if key == key_wanted and schedule == schedule_wanted:
            out[cut] = True
        return out
    return fake


results = {
    "a missed flag of M1 under P (TRUNC-0/P, H1, cut 3)": (with_plant(1, clear(("TRUNC-0/P", "h1"), 3)), "M1 h1 under P", 1),
    "two missed flags of M1 under P (TRUNC-1/P, H1, cuts 0 and 5)": (with_plant(1, lambda v: (clear(("TRUNC-1/P", "h1"), 0)(v), clear(("TRUNC-1/P", "h1"), 5)(v))), "M1 h1 under P", 2),
    "a flag at a cut declared unable to flag (TRUNC-0/P, H1, cut 2)": (with_plant(1, None, cannot_at("TRUNC-0/P", "h1", 2)), "M1 h1 under P", 1),
    "a flag of M1 under G (FI, H1, cut 7)": (with_plant(1, raise_(("FI", "h1"), 7)), "M1 h1", 1),
    "a missed FI flag on M2 at a predicted cut (H1, cut 4)": (with_plant(4, clear(("FI", "h1"), 4)), "M2", 1),
    "three missed FI flags on M2 (long schedule)": (with_plant(4, lambda v: [clear(("FI", "long"), c)(v) for c in (0, 50, 127)]), "M2", 3),
}
failed = 0
for name, (out, key, expected) in results.items():
    got = out["disagreements"][key] - base["disagreements"][key]
    others = {k: x for k, x in out["disagreements"].items() if k != key and x != base["disagreements"][k]}
    good = got == expected and not others and out["pass"] is False
    failed += not good
    print(("ok  " if good else "FAIL"), name, "| count of", repr(key), "moved by", got, "expected", expected, "| pass:", out["pass"], "| others moved:", others)
print("M1 h1 under P with a declared cut:", with_plant(1, None, cannot_at("TRUNC-0/P", "h1", 2))["reported"]["M1 h1 under P"]["TRUNC-0/P"])
print("plants that did not move their count as expected:", failed, "of", len(results))
