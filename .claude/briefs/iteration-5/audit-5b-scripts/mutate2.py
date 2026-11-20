import shutil, sys
from pathlib import Path
S = Path(sys.argv[1])
old = '''    for _, c, at in entries:
        w = adv._window(full_q[c["pair"]], at)
        cut_w = {k: v.copy() for k, v in w.items()}
        for v in cut_w.values():
            v[adv.PAST_REACH + 1 :] = np.nan  # every bar after the cut is missing
        orig_w.append(w)
        trunc_w.append(cut_w)
        masks.append(_compared(sched[c["pair"]].scored, at))
'''
new = '''    for part_, c, at in entries:
        shift = 1 if part_ == "TRUNC-1" else 0  # MUTANT: v1's arm, rows t-10..t, truncated after t+1
        w = adv._window(full_q[c["pair"]], at - shift)
        cut_w = {k: v.copy() for k, v in w.items()}
        for v in cut_w.values():
            v[adv.PAST_REACH + 1 + shift :] = np.nan
        orig_w.append(w)
        trunc_w.append(cut_w)
        masks.append(_compared(sched[c["pair"]].scored, at - shift))
'''
name = "m23_trunc1_is_v1s_arm"
dst = S / "mut" / name / "python"
if dst.exists(): shutil.rmtree(dst)
shutil.copytree(S / "base" / "python", dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
f = dst / "olsprime/bench/detectors.py"
t = f.read_text(encoding="utf-8"); assert t.count(old) == 1
f.write_text(t.replace(old, new), encoding="utf-8", newline="\n"); print("built", name)
