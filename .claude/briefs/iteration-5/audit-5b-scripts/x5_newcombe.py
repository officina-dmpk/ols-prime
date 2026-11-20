"""Audit 5b, X5: Newcombe's paired interval written again from the formulae, the effect of psi's correction, exact McNemar."""
import math
from scipy.stats import binomtest, norm
from olsprime.bench import detector_stats as ds

Z = norm.ppf(0.975)
def wilson(k, n, z=Z):
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return mid - half, mid + half

def newcombe(a, b, c, d, corrected=True):
    n = a + b + c + d
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n); l2, u2 = wilson(a + c, n)
    den = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    A = a * d - b * c
    if den == 0: phi = 0.0
    elif not corrected: phi = A / den
    elif A > n / 2: phi = (A - n / 2) / den
    elif A >= 0: phi = 0.0
    else: phi = A / den
    dl, du = p1 - l1, u1 - p1
    el, eu = p2 - l2, u2 - p2
    theta = p1 - p2
    lo = theta - math.sqrt(dl * dl - 2 * phi * dl * eu + eu * eu)
    hi = theta + math.sqrt(du * du - 2 * phi * du * el + el * el)
    return theta, lo, hi

worst = 0.0
for (a, b, c, d) in [(9650, 150, 150, 50), (9700, 60, 140, 100), (9500, 300, 100, 100), (9795, 5, 180, 20), (9000, 500, 300, 200),
                     (9788, 7, 0, 205), (9600, 195, 200, 5), (9999, 0, 1, 0), (0, 0, 0, 10000), (5000, 0, 0, 5000), (59, 6, 16, 80)]:
    got = ds.newcombe_paired(a, b, c, d)
    th, lo, hi = newcombe(a, b, c, d)
    _, lo0, hi0 = newcombe(a, b, c, d, corrected=False)
    worst = max(worst, abs(got["ci95"][0] - lo), abs(got["ci95"][1] - hi), abs(got["difference"] - th))
    p = binomtest(min(b, c), b + c, 0.5).pvalue if b + c else 1.0
    print(f"{(a,b,c,d)}: diff {100*th:+.3f} pt [{100*lo:+.4f}, {100*hi:+.4f}] | uncorrected phi [{100*lo0:+.4f}, {100*hi0:+.4f}] "
          f"| shift of the limits {100*(lo-lo0):+.4f}, {100*(hi-hi0):+.4f} pt | McNemar module {ds.mcnemar_exact(b,c):.6g} scipy {p:.6g}")
print("largest gap module vs this rewrite:", worst)
# H15 labels at the boundaries
for lo, hi in [(0.0, 0.5), (-0.5, 0.0), (-1.0, -0.2), (-1.5, -1.0), (-2.0, -1.2), (1e-12, 1), (-3, 3)]:
    d = {"difference": (lo + hi) / 200, "ci95": [lo / 100, hi / 100]}
    h = ds.h15(d, {})
    print((lo, hi), h["sign"], "|", h["margin"], "|", h["prior"])
