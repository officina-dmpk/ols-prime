"""Audit 5b, X10: the generator at 6044037 (old tree) or in the working tree: one line per leak, hashed. Bar-free."""
import hashlib, sys, pickle
from olsprime.bench import adversary as adv
out = {}
for seed in (20261029, 51118):
    leaks = adv.generate(10_000, seed)
    lines = [repr(l.expr) + "\t" + l.output + "\t" + repr(l.tags) + "\n" for l in leaks]
    out[seed] = (hashlib.sha256("".join(lines).encode("utf-8")).hexdigest(), lines)
    print(sys.argv[1], seed, out[seed][0], "has placement:", hasattr(adv, "PLACEMENTS"))
pickle.dump({k: v[1] for k, v in out.items()}, open(sys.argv[2], "wb"))
