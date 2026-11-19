"""Pass 5b-bis, Y2: wave4.py main() driven through every branch with subprocess.run replaced by a fake.

Nothing is spawned: no CLI runs, no leak is drawn, no bar is read. RUNS and SAVED_ADVERSARY are repointed to a
scratch folder, so nothing is written to the repository runs/ folder. The command lines that wave4 would run are
captured and compared, token by token, with the registered lines parsed out of docs/PROTOCOL.md; the detectors
lines are then given to the pure predicate registered_line_refusal. The seeds are read from the files, never typed.

It is written to keep working after the fixes this pass asks for: a refusal when an output folder already exists
(Minor 1), a check of each output's recorded commit and code digest (Major 1), and a digest step before the replay
(N5). Scenarios that depend on those print which behaviour they saw; the others assert.

Run from python/:
    uv run --no-sync python ../.claude/briefs/iteration-5/audit-5b-bis-scripts/y2_wave4_dry.py SCRATCH_DIR [WAVE4_PATH]
"""
import importlib.util
import io
import json
import re
import shlex
import shutil
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

from olsprime.bench import detectors as det
from olsprime.bench.provenance import code_digest, git_commit
from olsprime.paths import REPO_ROOT

SCRATCH = Path(sys.argv[1]).resolve()
assert REPO_ROOT.resolve() not in SCRATCH.parents, "scratch must be outside the repository"
W4 = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else REPO_ROOT / ".claude" / "briefs" / "iteration-5" / "wave4.py"
DATE = "2099-01-01"
DIGEST = code_digest()["sha256"]
HEAD = git_commit()
TICK = chr(96)
PROV = {"git_commit": HEAD, "code": {"sha256": DIGEST}}
ALL = ["adversary-replay", "descriptive", "confirmatory", "confirmatory-rerun"]
seen = {}


def load(root: Path):
    spec = importlib.util.spec_from_file_location("wave4_under_audit", W4)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.PYTHON_DIR = REPO_ROOT / "python"  # a copy of wave4.py kept in scratch still runs from python/
    m.RUNS = root / "runs"
    m.RUNS.mkdir(parents=True)
    m.SAVED_ADVERSARY = root / "saved" / "adversary.json"
    m.SAVED_ADVERSARY.parent.mkdir(parents=True)
    saved = {"provenance": {"git_commit": "old", "code": {"sha256": "old"}}, "h1_cuts": {"overall": {"caught": 9795}}, "x": [1.5, float("nan")]}
    m.SAVED_ADVERSARY.write_text(json.dumps(saved), encoding="utf-8")
    return m


def classify(args):
    if "olsprime.bench.adversary" in args:
        return "adversary-replay"
    if "digest" in args:
        return "pin"
    if "run" in args and "--workers" in args:
        if args[args.index("--workers") + 1] == "4":
            return "confirmatory-rerun"
        return "descriptive" if "h1-bands" in args else "confirmatory"
    return "other"


def scenario(name: str, plan: dict, *, digest: str = DIGEST, pre=None):
    """plan[step] = dict(rc=..., write={file: text}, stdout=...). Returns (exit, steps without the pin, log, exception)."""
    root = SCRATCH / name.split(" ")[0]
    if root.exists():
        shutil.rmtree(root)
    m = load(root)
    if pre:
        pre(m)
    calls = []

    def fake(argv, **kw):
        assert kw.get("cwd") == m.PYTHON_DIR and kw.get("capture_output") and argv[0] == sys.executable
        args = argv[1:]
        step = classify(args)
        calls.append((step, args))
        p = plan.get(step, {})
        if "--out" in args:
            out = Path(args[args.index("--out") + 1])
            for fname, text in (p.get("write") or {}).items():
                out.mkdir(parents=True, exist_ok=True)
                (out / fname).write_text(text, encoding="utf-8")
        default = det.REGISTERED_DEVELOPMENT_DIGEST + "  seed, n, placement\n" if step == "pin" else "headline\n"
        return SimpleNamespace(returncode=p.get("rc", 0), stdout=p.get("stdout", default), stderr="")

    m.subprocess = SimpleNamespace(run=fake)
    old = sys.argv
    sys.argv = ["wave4.py", "--frozen-digest", digest, "--date", DATE]
    try:
        with redirect_stdout(io.StringIO()) as buf:
            rc = m.main()
        err = None
    except BaseException as e:  # noqa: BLE001
        rc, err = None, "".join(traceback.format_exception_only(type(e), e)).strip()
    finally:
        sys.argv = old
    logf = m.RUNS / (DATE + "-wave4.log")
    log = logf.read_text(encoding="utf-8") if logf.exists() else buf.getvalue()
    last = log.strip().splitlines()[-1][:120] if log.strip() else "(nothing logged)"
    done = [c for c in calls if c[0] != "pin"]
    print(f"{name:50s} exit={rc!s:5s} steps={len(done)} pin={sum(c[0] == 'pin' for c in calls)} last: {last}" + (f" || EXC: {err[:80]}" if err else ""))
    seen[name.split(" ")[0]] = (rc, [c[0] for c in done])
    return rc, done, log, err


def steps(calls):
    return [c[0] for c in calls]


def dj(**kw):
    return json.dumps({"provenance": PROV, **kw})


ADV_OK = dj(h1_cuts={"overall": {"caught": 9795}}, x=[1.5, float("nan")])
ADV_DIFF = dj(h1_cuts={"overall": {"caught": 9794}}, x=[1.5, float("nan")])
PASS = {"detectors.json": dj(all_pass=True, metrics={"x": 1}), "detectors.md": "md", "verdicts.jsonl": "v\n", "run.json": "{}"}
STOP = {"detectors.json": dj(all_pass=False, stopped="x"), "detectors.md": "md", "run.json": "{}"}
GOOD = {"adversary-replay": {"write": {"adversary.json": ADV_OK}}, "descriptive": {"write": PASS}, "confirmatory": {"write": PASS},
        "confirmatory-rerun": {"write": {**PASS, "run.json": json.dumps({"workers": 4})}}}

rc, calls, log, err = scenario("A all good", GOOD)
assert rc == 0 and steps(calls) == ALL
good_calls = calls

rc, calls, *_ = scenario("B wrong frozen digest", GOOD, digest="0" * 64)
assert rc == 2 and calls == []

rc, calls, *_ = scenario("C replay exit 1", {**GOOD, "adversary-replay": {"rc": 1, "write": {"adversary.json": ADV_OK}}})
assert rc == 1 and steps(calls) == ALL[:1]

rc, calls, *_ = scenario("D replay differs outside provenance", {**GOOD, "adversary-replay": {"write": {"adversary.json": ADV_DIFF}}})
assert rc == 1 and steps(calls) == ALL[:1]

rc, calls, log, err = scenario("D2 replay exit 0, no adversary.json", {**GOOD, "adversary-replay": {}})
print("     -> ends in a traceback, not a STOP line:", err is not None)
assert rc != 0 and steps(calls) == ALL[:1]

rc, calls, *_ = scenario("E descriptive exit 1 (stopped)", {**GOOD, "descriptive": {"rc": 1, "write": STOP}})
assert rc == 1 and steps(calls) == ALL[:2]

rc, calls, *_ = scenario("E2 descriptive exit 2 (refused, no file)", {**GOOD, "descriptive": {"rc": 2}})
assert rc == 1 and steps(calls) == ALL[:2]

rc, calls, *_ = scenario("F descriptive exit 0, all_pass false", {**GOOD, "descriptive": {"write": STOP}})
assert rc == 1 and steps(calls) == ALL[:2]

rc, calls, log, err = scenario("G descriptive exit 0, no detectors.json", {**GOOD, "descriptive": {}})
print("     -> ends in a traceback, not a STOP line:", err is not None)
assert rc != 0 and steps(calls) == ALL[:2]


def stale_descriptive(m):  # a passing detectors.json left by an earlier attempt of the same date
    d = m.RUNS / (DATE + "-detectors-descriptive")
    d.mkdir(parents=True)
    for k, v in PASS.items():
        (d / k).write_text(v, encoding="utf-8")


rc, calls, *_ = scenario("G2 stale passing folder, new run exit 1", {**GOOD, "descriptive": {"rc": 1}}, pre=stale_descriptive)
assert rc != 0 and "confirmatory" not in steps(calls)  # stops after the failed run, or refuses at the start (Minor 1 fixed)
rc, calls, log, err = scenario("G3 stale passing folder, new run exit 0, no write", {**GOOD, "descriptive": {}}, pre=stale_descriptive)
print("     -> the stale file read as the verdict of this run, confirmatory invoked:", "confirmatory" in steps(calls))

rc, calls, *_ = scenario("H confirmatory exit 1", {**GOOD, "confirmatory": {"rc": 1, "write": STOP}})
assert rc == 1 and steps(calls) == ALL[:3]
rc, calls, *_ = scenario("H2 confirmatory exit 0, all_pass false", {**GOOD, "confirmatory": {"write": STOP}})
assert rc == 1 and steps(calls) == ALL[:3]

other = dj(all_pass=True, metrics={"x": 2})
rc, calls, *_ = scenario("I rerun differs in detectors.json", {**GOOD, "confirmatory-rerun": {"write": {**PASS, "detectors.json": other}}})
assert rc == 1 and steps(calls) == ALL
rc, calls, *_ = scenario("I2 rerun differs in verdicts.jsonl", {**GOOD, "confirmatory-rerun": {"write": {**PASS, "verdicts.jsonl": "w\n"}}})
assert rc == 1
rc, calls, *_ = scenario("J rerun holds an extra file", {**GOOD, "confirmatory-rerun": {"write": {**PASS, "extra.txt": "x"}}})
assert rc == 1
no_verdicts = {k: v for k, v in PASS.items() if k != "verdicts.jsonl"}
rc, calls, *_ = scenario("J2 rerun lacks verdicts.jsonl", {**GOOD, "confirmatory-rerun": {"write": no_verdicts}})
assert rc == 1
rc, calls, *_ = scenario("K rerun exit 1", {**GOOD, "confirmatory-rerun": {"rc": 1}})
assert rc == 1


def stale_confirmatory(m):  # an earlier attempt of the same date left the confirmatory folders
    for name in ("confirmatory", "confirmatory-rerun"):
        d = m.RUNS / (DATE + "-detectors-" + name)
        d.mkdir(parents=True)
        (d / "detectors.json").write_text(dj(all_pass=True, metrics={"x": 0}), encoding="utf-8")


rc, calls, log, err = scenario("L same date again, over existing folders", GOOD, pre=stale_confirmatory)
print("     -> Minor 1:", "refused at the start" if rc != 0 and not calls else f"NOT refused: exit {rc}, {len(calls)} steps, the confirmatory line runs again over the earlier outputs")

# Major 1: the code moved after step 0 (a file under python/olsprime/ re-saved), so two runs record two code digests
moved = json.dumps({"provenance": {"git_commit": HEAD, "code": {"sha256": "f" * 64}}, "all_pass": True, "metrics": {"x": 1}})
later = {"write": {**PASS, "detectors.json": moved}}
rc, calls, *_ = scenario("M code digest moved before the confirmatory run", {**GOOD, "confirmatory": later, "confirmatory-rerun": later})
print("     -> Major 1:", "stopped" if rc != 0 else "NOT stopped: exit 0 though the descriptive and confirmatory runs record two code digests (§7.3)")
head2 = json.dumps({"provenance": {"git_commit": "0" * 40, "code": {"sha256": DIGEST}}, "all_pass": True, "metrics": {"x": 1}})
rc, calls, *_ = scenario("N HEAD moved before the rerun", {**GOOD, "confirmatory-rerun": {"write": {**PASS, "detectors.json": head2}}})
assert rc != 0  # a mismatch today; a named STOP once the commit is checked
rc, calls, *_ = scenario("O pin step fails (only if wave4 has one)", {**GOOD, "pin": {"rc": 2, "stdout": ""}})
print("     -> N5:", "stopped before the replay" if rc != 0 and not calls else "no digest step before the replay")

# --- The command lines against the dated line of docs/PROTOCOL.md ------------------------------------------
text = (REPO_ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
entry = text[text.index("- 2026-11-19, after audit pass 5b"):]
block = entry[entry.index("**The registered command lines**"):entry.index("**The CLI enforces these lines**")]
lines = re.findall(TICK + r"(python -m olsprime\.bench\.[^" + TICK + r"]+)" + TICK, block)
print("\nregistered command lines in PROTOCOL.md:", len(lines))
assert len(lines) == 3, lines  # item 4 is item 3 with --workers 4 and another folder


def tokens(argv):  # drop --out and its value; the path is free
    argv = list(argv)
    if "--out" in argv:
        i = argv.index("--out")
        del argv[i:i + 2]
    return argv


def as_set(argv):  # the positional head and the option/value pairs, order-free
    argv = tokens(argv)
    k = next(i for i, a in enumerate(argv) if a.startswith("--"))
    rest = argv[k:]
    return tuple(argv[:k]), dict(zip(rest[::2], rest[1::2], strict=True))


registered = [shlex.split(x)[1:] for x in lines]  # without "python"
got = dict(good_calls)
for step, reg in (("adversary-replay", registered[0]), ("descriptive", registered[1]), ("confirmatory", registered[2])):
    same_order = tokens(got[step]) == reg
    same_set = as_set(got[step]) == as_set(reg)
    print(f"  {step:20s} same tokens in the same order: {same_order}; same options and values: {same_set}")
    assert same_set, (tokens(got[step]), reg)
rerun = as_set(got["confirmatory-rerun"])
conf = as_set(registered[2])
assert rerun[0] == conf[0] and {**rerun[1], "--workers": "8"} == conf[1] and rerun[1]["--workers"] == "4"
print("  confirmatory-rerun   the confirmatory line with --workers 4: True")
outs = [a[a.index("--out") + 1] for _, a in good_calls]
assert len(set(outs)) == 4
print("  four distinct --out folders:", [Path(o).name for o in outs])


def namespace(argv):
    _, opts = as_set(argv)
    return SimpleNamespace(seed=int(opts["--seed"]), two_run_seed=int(opts["--two-run-seed"]), placement=opts["--placement"],
                           bootstrap_seed=int(opts["--bootstrap-seed"]) if "--bootstrap-seed" in opts else None,
                           n=int(opts.get("--n", 10_000)), synthetic="--synthetic" in argv, table=opts.get("--table"))


for step in ("descriptive", "confirmatory", "confirmatory-rerun"):
    ns = namespace(got[step])
    reason = det.registered_line_refusal(ns)
    print(f"  guard on the {step:20s} line of wave4: {'accepted' if reason is None else 'REFUSED: ' + reason}")
    assert reason is None
assert namespace(got["descriptive"]).seed == det.DESCRIPTIVE_POPULATION_SEED
assert namespace(got["confirmatory"]).seed == det.CONFIRMATORY_POPULATION_SEED
table = Path(got["descriptive"][got["descriptive"].index("--table") + 1])
print("  --table as wave4 passes it, resolved from python/:", (REPO_ROOT / "python" / table).resolve().exists())
print("Y2 done on", W4)
