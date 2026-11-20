"""Audit phase 2a, A2: the descriptive run against two outputs recorded before it, leak by leak, and the two detector
runs against each other where only the bars can matter. Reads JSON files of finished runs; no bar, no olsprime import.

- FI at the 16 cuts of H1 against h1_pattern of runs/2026-10-29-h1-adversary/adversary.json (iteration 3);
- FI on the long schedule against long_cuts_caught of the same file;
- SHUFFLE (8 twins) against twin_pattern of runs/2026-10-30-twins/twins.json (iteration 4), a count of twins per cut;
- the two constancy flags and the tags against both files.

Run:  python a2_external.py RUNS_DIR
"""
import json
import sys
from pathlib import Path

import numpy as np

runs = Path(sys.argv[1])


def load(folder):
    with open(runs / folder / "verdicts.jsonl", encoding="utf-8") as fh:
        header = json.loads(fh.readline())
        recs = [dict(zip(header["fields"], json.loads(line))) for line in fh]
    layout = {e["key"]: e for e in header["layout"]["flags"]}

    def key(name):
        e = layout[name]
        out = np.zeros((len(recs), e["cuts"], e["runs"]), dtype=bool)
        for i, r in enumerate(recs):
            raw = np.frombuffer(bytes.fromhex(r["flags"]), dtype=np.uint8)
            idx = e["offset"] + np.arange(e["cuts"] * e["runs"])
            out[i] = (np.right_shift(raw[idx // 8], (idx % 8).astype(np.uint8)) & 1).reshape(e["cuts"], e["runs"]).astype(bool)
        return out

    return header, recs, key


hd, rd, kd = load("2026-11-19-detectors-descriptive")
adv = json.loads((runs / "2026-10-29-h1-adversary" / "adversary.json").read_text(encoding="utf-8"))
tw = json.loads((runs / "2026-10-30-twins" / "twins.json").read_text(encoding="utf-8"))
n = len(rd)
print("leaks", n, len(adv["leaks"]), len(tw["leaks"]))

# the cuts: same order, index and date as the adversary recorded them
h1_adv = [c for c in adv["cuts"] if c["schedule"] == "h1"]
long_adv = [c for c in adv["cuts"] if c["schedule"] != "h1"]
same_h1 = [(a["pair"], a["index"], a["open_time"]) for a in h1_adv] == [(c["pair"], c["index"], c["open_time"]) for c in hd["cuts"]["h1"]]
same_long = sorted((a["pair"], a["index"]) for a in long_adv) == sorted((c["pair"], c["index"]) for c in hd["cuts"]["long"])
print("H1 cuts equal, in order:", same_h1, "| long cuts equal as a set:", same_long, len(long_adv))

fi = kd("FI@h1").any(axis=2)
pat = np.array([[ch == "X" for ch in leak["h1_pattern"]] for leak in adv["leaks"]])
print("FI at the 16 cuts: (leak, cut) cells that differ from iteration 3:", int((fi != pat).sum()), "| leaks whose any-cut verdict differs:", int((fi.any(1) != pat.any(1)).sum()))
fl = kd("FI@long").any(axis=2).sum(axis=1)
print("FI on the long schedule: leaks whose count of cuts differs from long_cuts_caught:", int((fl != np.array([leak["long_cuts_caught"] for leak in adv["leaks"]])).sum()))
sh = kd("SHUFFLE@h1").sum(axis=2)
tp = np.array([[int(ch) for ch in leak["twin_pattern"]] for leak in tw["leaks"]])
print("SHUFFLE: (leak, cut) cells whose count of moving twins differs from iteration 4:", int((sh != tp).sum()), "| moved by a twin:", int((sh.sum(1) > 0).sum()))
c16 = np.array([bool(r["constant_h1_cuts"]) for r in rd])
cb = np.array([bool(r["constant_both_schedules"]) for r in rd])
print("constant at the 16 cuts: differs from twins.json constant:", int((c16 != np.array([leak["constant"] for leak in tw["leaks"]])).sum()),
      "| constant on both schedules: differs from twins.json:", int((cb != np.array([leak["constant_both_schedules"] for leak in tw["leaks"]])).sum()),
      "| from adversary.json constant_on_original_rows:", int((cb != np.array([leak["constant_on_original_rows"] for leak in adv["leaks"]])).sum()))
tags = sum((r["family"] != a["family"]) + (r["designed"] != a["tags"]["designed"]) + (r["position"] != a["tags"]["position"]) + (r["output"] != a["tags"]["output"])
           for r, a in zip(rd, adv["leaks"]))
print("tags (family, designed, position, output) that differ from adversary.json:", int(tags))

# the two detector runs: the same bars, so the same cuts, and the same counts for the classes that draw nothing
hc, rc, kc = load("2026-11-19-detectors-confirmatory")
print("cuts of the two runs equal:", hd["cuts"] == hc["cuts"], "| layouts equal:", hd["layout"] == hc["layout"])
jd = json.loads((runs / "2026-11-19-detectors-descriptive" / "detectors.json").read_text(encoding="utf-8"))
jc = json.loads((runs / "2026-11-19-detectors-confirmatory" / "detectors.json").read_text(encoding="utf-8"))
for name in jd["reported"]["classes"]:
    a, b = jd["reported"]["classes"][name], jc["reported"]["classes"][name]
    print(f"  classes[{name}]: descriptive {a} | confirmatory {b} | {'equal' if a == b else 'DIFFERENT'}")
for name in ("assertions", "gates"):
    print(name, "equal across the two runs:", jd[name] == jc[name])
print("config differences:", {k: (jd["config"][k], jc["config"][k]) for k in jd["config"] if jd["config"][k] != jc["config"][k]})
print("placement, table:", jd["placement"], jc["placement"], jd["table_sha256"] == jc["table_sha256"])
