# Findings — the two definitions of a constant miss

- **Agent:** `ml-engineer`, 2026-11-18. Brief: `.claude/briefs/iteration-5/misses.md`.
- **Inputs:** the code, plus the saved JSON of two runs:
  - `runs/2026-10-29-h1-adversary/adversary.json`, SHA-256 `f572127b1eb1dbfcde30fa285976e6431192a25e82e0179b6074805c27325f54`;
  - `runs/2026-10-30-twins/twins.json`, SHA-256 `ff50dabaa31347855a038fb0fb8da2d718f3cb7122a29633b51368dab67864c2`.
- **What was not done:** no read of `data/`, nothing through the seal, and no recomputation, not even on synthetic bars, because the saved JSON already carries both flags for every leak. No code or docs file was changed.

## Verdict

**The suspected cause is confirmed, and nothing else is involved.** Both counts are correct. They count two different things, and the two `docs/RESULTS.md` rows describe both with the same phrase, "constant at the compared rows".

- **163, the adversary row.** A miss is constant at the compared rows of all 144 cuts: H1's 16 cuts and the 128 cuts of the long schedule.
- **193, the twins row.** A miss is constant at the compared rows of H1's 16 cuts only.

The two sets are nested. All 163 lie inside the 193, and the 30 extra misses are constant at H1's cuts but vary at some long-schedule cut. No leak goes the other way, on the 205 misses or on all 10,000 leaks.

**There is no code bug.** The twins run already reports both numbers:
- `twins.md` line 27: "163 misses are constant there, and 30 more are constant at H1's cuts only";
- `twins.json`: `misses.constant_both_schedules = 163` and `misses.constant_h1_only = 30`.

The fault is in the twins row of `docs/RESULTS.md`. It quotes the H1-only count with the adversary's wording and does not say which rows it means.

## The two definitions, from the code

Both flags come from the same function, `evaluate_fast`, in `python/olsprime/bench/adversary.py`:
- 1137: `constant = True`;
- 1141: `bits = np.ascontiguousarray(a[bench.scored]).view(np.uint64)`;
- 1142: `constant = constant and bool(bits.size == 0 or np.all(bits == bits[0]))`.

What the function computes:
- **Rows.** For each output array of the leak (`target` and/or `probs`), it takes the leak's outputs on the original bars at the compared rows of every cut in the bench. The compared rows of a cut t are t-10..t (`COMPARED = FUTURE_REACH + 1 = 11`, lines 208–210), kept only where H1 scores them (`bench.scored`). That is up to 11 rows per cut.
- **Pooling.** The rows of all cuts of both pairs are pooled into a single vector.
- **Flag.** A leak is constant when that vector holds a single bit pattern.
- **Vacuous case.** The flag is true when no row is scored.

The two flags differ only in which bench they are given.

1. **The adversary's flag, `constant_on_original_rows`.**
   - `build_bench` puts both schedules into one bench (`adversary.py:1107`, `for schedule, cut_list, hcfg in schedules(bars, folds, cfg)`).
   - `schedules` (lines 1091–1092) returns H1's cuts and the long schedule. The long schedule has `LONG_CUTS = 64` cuts per pair (line 233).
   - So the bench holds 8 + 64 cuts per pair, 16 + 128 = 144 in all. `adversary.json`'s `cuts` list holds `{'h1': 16, 'long': 128}`.
   - The miss count is at `adversary.py:1446`: `"constant_on_original_rows": int((missed & ev.constant).sum())`, which is **163**.
2. **The twins' classifying flag, `constant`.**
   - `twins.py:185` builds the H1 bench with the long schedule removed: `h1 = adv.build_bench(bars_by_pair, replace(cfg.adversary, long_cuts=0))`.
   - `twins.py:240` and `247` set `h = adv.evaluate_fast(leak, tb.h1)` and `out.constant[i] = h.constant`.
   - The flag therefore covers the 16 H1 cuts only, which gives **193**.
3. **The twins' copy of the adversary's flag, `constant_every`.**
   - `twins.py:209–213` and `218` build the `every` bench from both schedules (`for schedule, cut_list, _ in adv.schedules(...)`). It uses the same windows (`adv._window(q0, cut.index)`) and the same compared-row mask (`_compared`, lines 174–176).
   - `twins.py:248` sets `out.constant_every[i] = adv.evaluate_fast(leak, tb.every).constant`.
   - `cross_check` (`twins.py:424`) requires it to equal the adversary's `constant_on_original_rows` for every leak, and the run reports 0 mismatches.

**Why the sets are nested.** At H1's cuts, the `every` bench has the same cuts, the same windows and the same mask as the H1 bench, and it adds 128 more cuts. Adding rows to a single-value test can only turn true into false. So the set "constant over both schedules" is contained in the set "constant over H1's cuts", by construction. `python/tests/test_twins.py:176` already asserts this on synthetic bars: `assert (mine.constant | ~mine.constant_every).all()`.

The flag matters beyond the constant class:
- `classify` (`twins.py:277`) tests the H1-only flag first: `np.where(caught, "caught", np.where(ev.constant, "constant", np.where(moved, "blind-spot", "unchanged")))`. The flag therefore also decides how many misses become `unchanged` and `blind-spot`.
- The summary writes both counts (`twins.py:338–339`).
- The per-leak records carry both flags (`twins.py:315–316`, keys `constant` and `constant_both_schedules`).
- `caught_moved_by_a_twin.not_moved_constant` (`twins.py:348`) uses the H1-only flag.

## Leak by leak

Results from the script below, on the saved JSON:

| | over both schedules (144 cuts) | over H1's cuts only (16 cuts) |
|---|---|---|
| constant misses, of 205 | **163** | **193** |
| constant leaks, of all 10,000 | 765 | 1,172 |
| constant under this definition but not the other: misses | **0** | **30** |
| constant under this definition but not the other: all leaks | 0 | 407 |
| classes of the 205 misses (constant / unchanged / blind spot) | 163 / 22 / 20 | 193 / 5 / 7 (the run's classes) |
| shares, 95 % Wilson | 79.5 % [73.5, 84.5] / 10.7 % [7.2, 15.7] / 9.8 % [6.4, 14.6] | 94.1 % [90.0, 96.6] / 2.4 % [1.0, 5.6] / 3.4 % [1.7, 6.9] |
| constant misses still moved by some twin | 42 | 55 |
| caught leaks no twin moves (169) that are constant | 149 | 169 |

**Direction.** No leak is constant over both schedules without also being constant over H1's cuts. This holds for the 205 misses and for all 10,000 leaks.

**The 30**, constant at the compared rows of H1's 16 cuts but not at those of all 144 cuts:
- By family: aggregates 15, combinations 7, shapes 5 and ratios 3.
- In the twins run, all 30 are in the `constant` class.
- Under the both-schedules flag, they would split into 13 blind spots (moved by some twin at some H1 cut) and 17 unchanged.
- 26 of the 30 are caught at one long-schedule cut at least.
- Four are caught at no long cut: 83, 4848, 7044 and 7709. They vary at some long-schedule compared row, yet H1's perturbation never moves them there. "Not constant" must not be read as "caught".

| id | family | quantity | operation | offset | long cuts caught (of 128) | moved by a twin | expression |
|---|---|---|---|---|---|---|---|
| 83 | aggregates | range | sum | s+1..s+5 | 0 | no | `target = sum(range[s+1..s+5]) > range[s-3]` |
| 106 | combinations | two leaks | OR | s+10 | 5 | no | `target = (max(taker_quote_share[s+1..s+10]) > max(taker_quote_share[s-71..s-62])) OR (lower_wick[s+5] > 4.024e-05)` |
| 1002 | combinations | two leaks | AND | s+3 | 12 | no | `probs = (lower_wick[s+3] > 0.002525) AND (sum(range[s+1..s+3]) < range[s])` |
| 1570 | ratios | body | threshold | s+1 | 12 | yes | `probs = body[s+1] < 0.4348` |
| 1623 | aggregates | range | sum | s+1..s+3 | 8 | no | `probs = sum(range[s+1..s+3]) < 0.794 x range[s]` |
| 1676 | aggregates | lower_wick | max | s+1..s+10 | 14 | no | `target = max(lower_wick[s+1..s+10]) < 0.357 x lower_wick[s-66]` |
| 1710 | shapes | close_location | threshold | s+2 | 6 | yes | `target = close_location[s+2] > 0.9848` |
| 1751 | combinations | two leaks | AND | s+5 | 3 | yes | `target = (vwap[s+5] < 1.74 x close[s-10]) AND (sum(trades[s+1..s+3]) > 2.48 x sum(trades[s-6..s-4]))` |
| 2147 | shapes | fill | threshold | s+3 | 2 | no | `probs = fill[s+3] > 0.9762` |
| 3115 | aggregates | body | sum | s+1..s+5 | 1 | no | `target = sum(body[s+1..s+5]) < 0.342 x body[s-5]` |
| 3319 | ratios | body | threshold | s+1 | 10 | yes | `target = body[s+1] < 0.4784` |
| 3478 | aggregates | upper_wick | sum | s+1..s+10 | 2 | yes | `target = sum(upper_wick[s+1..s+10]) < upper_wick[s-3]` |
| 3587 | shapes | fill | threshold | s+1 | 1 | no | `target = fill[s+1] > 0.9731` |
| 4848 | combinations | two leaks | AND | s+3 | 0 | no | `probs = (max(quote_volume[s+1..s+3]) < 1.17 x quote_volume[s-58]) AND (vwap[s+1] > 2.68 x vwap[s-115])` |
| 4893 | shapes | fill | threshold | s+1 | 2 | no | `target = fill[s+1] < 0.9703` |
| 5130 | combinations | two leaks | AND | s+5 | 9 | yes | `target = (vwap[s+5] > close[s-22]) AND (star[s+2] (upper wick >= 2.72 x body, lower wick <= body))` |
| 5276 | aggregates | trade_size | mean | s+1..s+3 | 19 | yes | `target = mean(trade_size[s+1..s+3]) > 0.51 x trade_size[s-9]` |
| 5317 | aggregates | body | max | s+1..s+10 | 11 | no | `probs = max(body[s+1..s+10]) < 0.363 x body[s-10]` |
| 5402 | aggregates | upper_wick | max | s+1..s+10 | 5 | no | `target = max(upper_wick[s+1..s+10]) > 0.303 x upper_wick[s-36]` |
| 5669 | combinations | two leaks | AND | s+5 | 29 | yes | `probs = (close_location[s+5] < close_location[s-4]) AND (star[s+1] (upper wick >= 2.53 x body, lower wick <= body))` |
| 5684 | aggregates | range | sum | s+1..s+5 | 7 | yes | `probs = sum(range[s+1..s+5]) < 0.346 x sum(range[s-7..s-3])` |
| 6386 | shapes | colour and body | red-and-big | s+1 | 7 | yes | `target = red-and-big[s+1] (body > 0.3718)` |
| 6395 | aggregates | taker_buy_base_volume | max | s+1..s+5 | 17 | yes | `target = max(taker_buy_base_volume[s+1..s+5]) > 0.299 x taker_buy_base_volume[s-5]` |
| 6780 | aggregates | body | sum | s+1..s+10 | 6 | no | `target = sum(body[s+1..s+10]) < body[s-10]` |
| 7044 | aggregates | lower_wick | sum | s+1..s+3 | 0 | no | `target = sum(lower_wick[s+1..s+3]) > 0.26 x lower_wick[s-4]` |
| 7175 | aggregates | body | sum | s+1..s+10 | 2 | no | `probs = sum(body[s+1..s+10]) > body[s-12]` |
| 7304 | aggregates | range | max | s+1..s+5 | 4 | no | `target = max(range[s+1..s+5]) > 0.38 x range[s-8]` |
| 7709 | combinations | two leaks | XOR | s+1 | 0 | no | `target = (taker_base_share[s+1] < 0.5824) XOR (taker_quote_share[s+1] < 0.7594)` |
| 8826 | ratios | body | threshold | s+3 | 12 | yes | `target = body[s+3] < 0.4322` |
| 9851 | aggregates | range | sum | s+1..s+10 | 3 | yes | `target = sum(range[s+1..s+10]) < 0.359 x sum(range[s-25..s-16])` |

**Reconciling the two rows.**
- The adversary row's "other 42", which audit phase 2 classified, are the misses that are not constant over both schedules.
- They are exactly these 30, plus the twins run's 5 `unchanged` and 7 `blind-spot` misses: 42 = 30 + 5 + 7.
- By family, the 42 are aggregates 18, combinations 13, shapes 8 and ratios 3. That matches the audit's "11 thresholds" (shapes 8 + ratios 3), "18 aggregates" and "13 combinations".
- The 12 misses that are not constant even at H1's cuts:
  - unchanged: 3408, 7150, 8190, 9070 and 9819;
  - blind spots: 4393, 4822, 4896, 6720, 7483, 7982 and 9963.

**Other uses of the phrase in the two rows.**
- The twins row says "the 169 never moved are all constant at the compared rows". That count uses the H1-only flag (`twins.py:348`). Over both schedules, 149 of the 169 are constant.
- The adversary row says "1,166 [honest twins] are constant at the compared rows". That count is over both schedules: `adversary.py` `evaluate_all` runs the honest twin on the full 144-cut bench.

## Counting commands (re-runnable)

From the repository root. The script reads only the two JSON files and checks their digests first:

```bash
cd python
sha256sum ../runs/2026-10-29-h1-adversary/adversary.json ../runs/2026-10-30-twins/twins.json
# expect f572127b1eb1dbfcde30fa285976e6431192a25e82e0179b6074805c27325f54 and ff50dabaa31347855a038fb0fb8da2d718f3cb7122a29633b51368dab67864c2
uv run --no-sync python - .. <<'EOF'
"""The two constant flags on the adversary's 205 misses, leak by leak, from the two runs' saved JSON only."""
import json
import sys
from collections import Counter

root = sys.argv[1]
a = json.load(open(f"{root}/runs/2026-10-29-h1-adversary/adversary.json", encoding="utf-8"))
t = json.load(open(f"{root}/runs/2026-10-30-twins/twins.json", encoding="utf-8"))
A = {r["id"]: r for r in a["leaks"]}
T = {r["id"]: r for r in t["leaks"]}
assert set(A) == set(T) and len(A) == 10_000
print("cuts by schedule:", dict(Counter(c["schedule"] for c in a["cuts"])))
# The twins run's copy of the adversary's flag is the adversary's flag, on every leak.
assert all(A[i]["constant_on_original_rows"] == T[i]["constant_both_schedules"] for i in A)
M = sorted(i for i, r in A.items() if "X" not in r["h1_pattern"])  # caught at no H1 cut
assert M == sorted(i for i, r in T.items() if r["class"] != "caught")
both = {i for i in M if T[i]["constant_both_schedules"]}
h1 = {i for i in M if T[i]["constant"]}
print(f"misses {len(M)}: constant over both schedules {len(both)}, over H1's cuts only {len(h1)}")
print(f"H1-only minus both: {len(h1 - both)}; both minus H1-only: {len(both - h1)}")
ab = {i for i in A if T[i]["constant_both_schedules"]}
ah = {i for i in A if T[i]["constant"]}
print(f"all 10,000 leaks: both {len(ab)}, H1-only {len(ah)}, both minus H1-only {len(ab - ah)}, H1-only minus both {len(ah - ab)}")
diff = sorted(h1 - both)
print("the difference by family:", dict(Counter(A[i]["family"] for i in diff)))
print("  moved by some twin:", [i for i in diff if T[i]["twin_cuts_moved"] > 0])
print("  caught at no long cut:", [i for i in diff if A[i]["long_cuts_caught"] == 0])


def classes(flag):
    return dict(Counter("constant" if T[i][flag] else "blind-spot" if T[i]["twin_cuts_moved"] > 0 else "unchanged" for i in M))


print("classes, H1-only flag (the run's):", classes("constant"), " twins.json:", {k: v["count"] for k, v in t["classes"].items()})
print("classes, both-schedules flag:", classes("constant_both_schedules"))
print("the 42 non-constant over both schedules, by family:", dict(Counter(A[i]["family"] for i in M if i not in both)))
C = [i for i in A if "X" in A[i]["h1_pattern"] and T[i]["twin_cuts_moved"] == 0]
print(f"caught, never moved by a twin: {len(C)}; constant H1-only {sum(T[i]['constant'] for i in C)}, "
      f"both {sum(T[i]['constant_both_schedules'] for i in C)}")
print("constant misses moved by a twin: H1-only", sum(T[i]["constant"] and T[i]["twin_cuts_moved"] > 0 for i in M),
      "both", sum(T[i]["constant_both_schedules"] and T[i]["twin_cuts_moved"] > 0 for i in M))
print("| id | family | quantity | operation | offset | long cuts caught (of 128) | moved by a twin | expression |")
print("|---|---|---|---|---|---|---|---|")
for i in diff:
    r, g = A[i], A[i]["tags"]
    print(f"| {i} | {r['family']} | {g['quantity']} | {g['operation']} | {g['offset']} | {r['long_cuts_caught']} | "
          f"{'yes' if T[i]['twin_cuts_moved'] else 'no'} | `{r['expression']}` |")
EOF
```

The classification in the script reproduces `classify` (`twins.py:277`). A miss's "moved by some twin" is `twin_cuts_moved > 0` in the per-leak record, which is `ev.moved.any(axis=(1, 2))`. With the H1-only flag, the script reproduces the run's classes exactly (193 / 5 / 7).

The Wilson intervals come from the repository's own function:

```bash
cd python && uv run --no-sync python -c "
from olsprime.bench.adversary import wilson
for k in (163, 22, 20, 193, 5, 7):
    lo, hi = wilson(k, 205); print(k, f'{100*k/205:.1f} [{100*lo:.1f}, {100*hi:.1f}]')"
```

## Paragraph for the dated correction row in `docs/RESULTS.md`, and for the paper

One block of plain prose, with no line breaks and no `|` characters, so that it can be pasted into a single table cell:

Correction, 2026-11-18: two definitions of a "constant" miss. The adversary row of 2026-10-29 and the blind-spots row of 2026-10-30 both say "constant at the compared rows", but they mean different sets of rows, so their counts differ. In both, a leak is constant when its output on the original bars has one value, bit for bit, at every compared row (t-10..t, where H1 scores) of a set of cuts, pooled over every cut of both pairs. The adversary pools all 144 cuts of its two schedules, H1's 16 and the long schedule's 128. On that set, 163 of the 205 leaks caught at no H1 cut are constant (79.5 %, 95 % Wilson [73.5, 84.5]). The blind-spots run pools H1's 16 cuts only, and classifies with that flag. On that set, 193 of the same 205 are constant (94.1 % [90.0, 96.6]). The two sets are nested: every leak constant over 144 cuts is constant over 16, and none the other way round, among the misses or among all 10,000 leaks. The 30 in between (aggregates 15, combinations 7, shapes 5, ratios 3) vary at some long-schedule cut. 26 of them are caught at some long-schedule cut and 4 at none. These 30, with the 5 unchanged and the 7 blind-spot misses of the H1-only classification, are the 42 that the audit's phase 2 classified. Reclassified from the saved per-leak flags (no new run), with the both-schedules flag the 205 misses split into 163 constant, 22 unchanged (10.7 % [7.2, 15.7]) and 20 blind spots (9.8 % [6.4, 14.6]), against the run's 193, 5 and 7 with the H1-only flag. Likewise, the 169 caught leaks that no twin moves are all constant over H1's cuts, but 149 of them are constant over both schedules. The adversary row's 1,166 constant honest twins are counted over both schedules. Both counts come from the same function on the saved runs, and the twins report already printed both (163, then "30 more are constant at H1's cuts only"), so no number of either row is wrong and both rows stand. Any count of constant misses or of true blind spots, here or in the paper, names its set of cuts.

## Code change

**None is warranted.** The code computes both flags correctly, and the twins report prints both. `python/tests/test_twins.py:175–176` already tests two things on synthetic bars: that `constant_every` is the adversary's flag, and that the two flags are nested.

The brief's lines `twins.py` 33–37 and 229–230 are the module docstring and the dataclass field comments. They state the difference correctly. The operative lines are 185, 240 and 247–248.

For audit pass 5b, one wording change, for future runs only (recorded runs stay byte-identical as they are). In `render_md`, the class sentence (`twins.py:560–562`) and the table should say "the compared rows of H1's 16 cuts" rather than "the compared rows of H1's cuts".
- The test: in `test_the_cli_cross_checks_on_synthetic_bars`, read the written `twins.json` and `twins.md`, then `assert f"compared rows of H1's {len(result['per_cut'])} cuts" in md`. This ties the sentence to the actual number of H1 cuts, 8 on the synthetic bench and 16 in the real run.
- A rename of the per-leak JSON key `constant` is not proposed: it would break comparison with the recorded run for a label alone.

The "11 thresholds" match with the audit's phase 2 was checked by tag, not only by family. Among the 42, `tags.reference == "threshold"` holds for exactly 11 leaks: shapes 8 and ratios 3, including 6386 `red-and-big`. Check: `Counter(r['tags']['reference'] for r in a['leaks'] if 'X' not in r['h1_pattern'] and not r['constant_on_original_rows'] and r['family'] != 'combinations')`.

`adversary.md` line 15 confirms that the 1,166 are counted over both schedules: "10000 twins at 144 cuts each (both schedules)".

## Bolder next step

Replace both cut-dependent definitions with one that does not depend on any cut schedule: a leak is constant when it is constant at every row H1 scores in the development period. That is an "uninformative on these bars" flag.

Report the detection rate conditioned on it, with a Wilson interval. That gives the paper one headline miss count, free of where the cuts happened to fall.

This needs the development bars, so it is a fresh, registered run through `experiment-runner`. Before that, it can be checked on synthetic bars against the two existing flags: the new set must be contained in both.
