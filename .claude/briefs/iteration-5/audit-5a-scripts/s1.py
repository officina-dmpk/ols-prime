import numpy as np
# 1. SeedSequence: does a trailing zero collide? (neutral seeds only)
a = np.random.default_rng([123, 5]).random(3)
b = np.random.default_rng([123, 5, 0]).random(3)
c = np.random.default_rng([123, 5, 1]).random(3)
print("rng([123,5]) == rng([123,5,0]):", np.array_equal(a, b), "| vs [123,5,1]:", np.array_equal(a, c))
print("SeedSequence pool equal:", np.random.SeedSequence([123,5]).generate_state(4).tolist() == np.random.SeedSequence([123,5,0]).generate_state(4).tolist())
# 4-element and longer
print("[1,2,3,4] vs [1,2,3,4,0]:", np.array_equal(np.random.default_rng([1,2,3,4]).random(3), np.random.default_rng([1,2,3,4,0]).random(3)))
# 2. min with NaN
x = np.array([1.0, 2.0]); n = np.array([np.nan, 5.0])
print("np.minimum:", np.minimum(x, n), "np.fmin:", np.fmin(x, n), "builtin min(x,nan):", min(1.0, float('nan')), "min(nan,x):", min(float('nan'), 1.0))
print("np.min stack:", np.min(np.stack([x, n]), axis=0), "np.max:", np.max(np.stack([x, n]), axis=0), "sum:", np.sum(np.stack([x, n]), axis=0))
with np.errstate(invalid="ignore"):
    print("cmp NaN > :", (n > x), " < :", (n < x), " == :", (n == n))
v = np.array([np.nan, 3.0, -3.0])
print("v - v:", v - v, " 0*v:", 0 * v, " x + 0*v bits same as x for finite:", (np.float64(1.5) + 0 * -3.0) == 1.5)
z = np.float64(-0.0)
print("(-0.0)+(+0.0) signbit:", np.signbit(z + 0.0), "(+0.0)+(-0.0):", np.signbit(np.float64(0.0) + (-0.0)))
print("numpy", np.__version__)
