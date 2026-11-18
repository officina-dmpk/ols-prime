import sys
from collections import Counter
import numpy as np
src = open(sys.argv[1], encoding="utf-8").read().split("leaks = adv.generate")[0]
exec(src)
leaks = adv.generate(4000, 424242)
viol = Counter(); ops = Counter()
for l in leaks:
    a, b = eval_rule(l, B["TRUNC1"]), eval_rule(l, B["TRUNC0"])
    if (a & ~b).any():
        viol[l.family] += 1; ops[l.tag["operation"]] += 1
print("TRUNC1 flags a cut that TRUNC0 does not, by family:", dict(viol), "by operation:", dict(ops))
