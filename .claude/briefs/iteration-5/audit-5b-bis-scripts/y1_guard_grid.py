"""Pass 5b-bis, Y1: the guard `registered_line_refusal` swept over a full grid, on the pure predicate only.

No leak is drawn, no bar is read, the CLI is never run. The three confirmatory seeds come from the module's
constants. The accept set on real bars must be exactly the two registered lines; a confirmatory seed must be accepted
nowhere but in its own slot of the confirmatory line.

Run from python/:  uv run --no-sync python ../.claude/briefs/iteration-5/audit-5b-bis-scripts/y1_guard_grid.py
"""
from itertools import product
from types import SimpleNamespace

from olsprime.bench import adversary as adv
from olsprime.bench import detectors as det

CONF = (det.CONFIRMATORY_POPULATION_SEED, det.CONFIRMATORY_TWO_RUN_SEED, det.CONFIRMATORY_BOOTSTRAP_SEED)
seeds = [*CONF, det.DESCRIPTIVE_POPULATION_SEED, det.DESCRIPTIVE_TWO_RUN_SEED, det.DESCRIPTIVE_BOOTSTRAP_SEED,
         det.DEVELOPMENT_POPULATION_SEED, det.DEVELOPMENT_TWO_RUN_SEED, 4242, 0, 1, 7, 11, 3, 20261027, 20261030]
boots = [*seeds, None]
ns = [10_000, 9_999, 10_001, 200, 1, 0, -10_000]
tables = [None, "t.json", ""]
accepted_real, accepted_conf_seed, total = [], [], 0
for seed, two, boot, placement, n, synthetic, table in product(seeds, seeds, boots, adv.PLACEMENTS, ns, (False, True), tables):
    total += 1
    args = SimpleNamespace(seed=seed, two_run_seed=two, bootstrap_seed=boot, placement=placement, n=n, synthetic=synthetic, table=table)
    reason = det.registered_line_refusal(args)
    if reason is None:
        if not synthetic:
            accepted_real.append((seed, placement, two, boot, n, table))
        if set(CONF) & {seed, two, boot}:
            accepted_conf_seed.append((seed, placement, two, boot, n, synthetic, table))
    else:
        assert isinstance(reason, str) and reason
want_conf = (CONF[0], adv.QUANTILE, CONF[1], CONF[2], 10_000)
want_desc = (det.DESCRIPTIVE_POPULATION_SEED, adv.H1_BANDS, det.DESCRIPTIVE_TWO_RUN_SEED, det.DESCRIPTIVE_BOOTSTRAP_SEED, 10_000)
print("combinations:", total)
print("accepted on real bars:", len(accepted_real))
for a in accepted_real:
    kind = "confirmatory" if a[:5] == want_conf else "descriptive" if a[:5] == want_desc else "OTHER"
    print("  ", kind, "table=%r" % (a[5],))
assert {a[:5] for a in accepted_real} == {want_conf, want_desc}, "the accept set on real bars is not the two registered lines"
assert all(a[5] is not None for a in accepted_real), "a real-bar line accepted without --table"
print("accepted with a confirmatory seed anywhere:", len(accepted_conf_seed))
assert all(a[:5] == want_conf and a[5] is False for a in accepted_conf_seed)
# An empty --table string: accepted by the guard (it is not None); load_table then refuses it. Reported, not asserted.
print("empty-string table accepted by the guard on real bars:", any(a[5] == "" for a in accepted_real))
# Types: argparse gives ints; a bool or a float equal to the seed would compare equal. Reported only.
odd = SimpleNamespace(seed=float(CONF[0]), two_run_seed=CONF[1], bootstrap_seed=CONF[2], placement=adv.QUANTILE, n=10_000.0, synthetic=0, table="t")
print("float-typed registered line accepted (argparse cannot produce it):", det.registered_line_refusal(odd) is None)
print("Y1 OK")
