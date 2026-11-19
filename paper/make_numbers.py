"""Write ``paper/numbers.tex``: every number the paper prints, read from the repository's records.

Run from ``python/`` (no new dependency, the standard library only):

    cd python && uv run --no-sync python ../paper/make_numbers.py

Each number is taken from the file that records it, never typed by hand:

- a row of ``docs/RESULTS.md``, found by its date, its full hypothesis cell and, where two rows
  share both, a phrase of its experiment cell;
- a line of ``docs/HYPOTHESES.md`` or ``docs/PROTOCOL.md``, found by an anchor that must occur on
  exactly one line (the registered parameters: seeds, counts, margins, audit tallies).

A regular expression is applied to that row or line, and must match exactly once; its groups give
the numbers, as the record prints them (no re-rounding). Any miss or ambiguity stops the script with
a non-zero exit, and ``numbers.tex`` is not written. Each ``\\newcommand`` carries a comment naming
its file, its line, its row or anchor, the pattern and the raw text it matched.

Wave 4's rates, H15's verdict and the case study's two analyses are NOT read here: they wait for
audit phase 2a (``.claude/briefs/iteration-5/audit-2a.md``). This script opens nothing under
``runs/``. It reads no bar and imports nothing from ``olsprime``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parent
ROOT = PAPER.parent
RESULTS = ROOT / "docs" / "RESULTS.md"
HYPOTHESES = ROOT / "docs" / "HYPOTHESES.md"
PROTOCOL = ROOT / "docs" / "PROTOCOL.md"
OUT = PAPER / "numbers.tex"

SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")


class Missing(Exception):
    """A row, an anchor or a pattern did not resolve to exactly one place."""


def lines_of(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def ascii_only(text: str) -> str:
    """Render a raw source fragment in ASCII for a TeX comment."""
    return "".join(c if ord(c) < 128 else f"<U+{ord(c):04X}>" for c in text).replace("\n", " ")


# --- locating the text ------------------------------------------------------------------------


def results_row(date: str, hypothesis: str, phrase: str | None = None) -> tuple[int, str, str]:
    """The one row of RESULTS.md with this date, this exact hypothesis cell (and phrase)."""
    found = []
    for lineno, line in enumerate(lines_of(RESULTS), 1):
        if not line.startswith("| 20"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        if len(cells) < 6 or cells[0] != date or cells[1] != hypothesis:
            continue
        if phrase is not None and phrase not in cells[2]:
            continue
        found.append((lineno, line))
    if len(found) != 1:
        raise Missing(f"RESULTS.md row ({date}, {hypothesis!r}, {phrase!r}): {len(found)} rows")
    lineno, line = found[0]
    where = f"docs/RESULTS.md:{lineno}, row ({date} | {hypothesis}"
    where += f" | ...{phrase}...)" if phrase else ")"
    return lineno, line, where


def anchored_line(path: Path, anchor: str) -> tuple[int, str, str]:
    """The one line of ``path`` that contains ``anchor``."""
    found = [(n, line) for n, line in enumerate(lines_of(path), 1) if anchor in line]
    if len(found) != 1:
        raise Missing(f"{path.name}: anchor {anchor!r} on {len(found)} lines")
    lineno, line = found[0]
    rel = path.relative_to(ROOT).as_posix()
    return lineno, line, f"{rel}:{lineno}, line holding '{anchor}'"


# --- formatting -------------------------------------------------------------------------------

PLAIN = re.compile(r"^(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?$")


def fmt_num(raw: str) -> str:
    """A number as the record prints it: thousands commas kept, a minus as \\textminus."""
    s = raw.strip().replace("−", "-")
    sign = ""
    if s.startswith("-"):
        sign, s = "\\textminus{}", s[1:]
    elif s.startswith("+"):
        sign, s = "+", s[1:]
    if not PLAIN.match(s):
        raise Missing(f"not a plain number: {raw!r}")
    return sign + s


def fmt_sci(raw: str) -> str:
    """``3.0e-07`` or ``1e-9`` -> math; ``1.6 × 10⁻¹⁵`` -> math."""
    s = raw.strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)e([-+]?\d+)", s)
    if m is None:
        m = re.fullmatch(r"(\d+(?:\.\d+)?) × 10([⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)", s)
        if m is None:
            raise Missing(f"not a scientific number: {raw!r}")
        mantissa, exponent = m.group(1), int(m.group(2).translate(SUPERSCRIPT))
    else:
        mantissa, exponent = m.group(1), int(m.group(2))
    if mantissa == "1":
        return f"\\ensuremath{{10^{{{exponent}}}}}"
    return f"\\ensuremath{{{mantissa}\\times 10^{{{exponent}}}}}"


def fmt_hex(raw: str) -> str:
    """A digest or a commit: the first 12 characters, monospace (the comment keeps it whole)."""
    s = raw.strip()
    if not re.fullmatch(r"[0-9a-f]{7,64}", s):
        raise Missing(f"not a hex digest: {raw!r}")
    short = s if len(s) <= 12 else s[:12] + "\\ldots{}"
    return f"\\texttt{{{short}}}"


def fmt_ver(raw: str) -> str:
    s = raw.strip()
    if not re.fullmatch(r"\d+(?:\.\d+)+", s):
        raise Missing(f"not a version: {raw!r}")
    return s


FORMATS = {"num": fmt_num, "sci": fmt_sci, "hex": fmt_hex, "ver": fmt_ver}


# --- the specification ------------------------------------------------------------------------
# Each entry: (macro names, source, pattern, format). The source is ("R", date, hypothesis[, phrase])
# for RESULTS.md, ("H", anchor) for HYPOTHESES.md, ("P", anchor) for PROTOCOL.md. A format applies
# to every group, unless a tuple of formats is given.

R_H1_FIRST = ("R", "2026-10-28", "H1")
R_H1_SECOND = ("R", "2026-10-28", "H1 (second run; erratum to the first H1 row)")
R_H1_PANEL = ("R", "2026-10-29", "H1 (panel)")
R_ADV = ("R", "2026-10-29", "H1 (adversary, descriptive)")
R_TWINS = ("R", "2026-10-30", "H1 (blind spots, descriptive)")
R_CORR = (
    "R",
    "2026-11-18",
    "H1 (correction of the rows of 2026-10-29 and 2026-10-30, descriptive)",
)
R_ENC_H1 = ("R", "2026-10-31", "H1 (encoder arms)")
R_H2 = ("R", "2026-10-29", "H2")
R_H3 = ("R", "2026-10-29", "H3")
R_H10 = ("R", "2026-10-29", "H10")
R_H11 = ("R", "2026-10-29", "H11")
R_H12 = ("R", "2026-10-29", "H12")
R_REP2 = ("R", "2026-10-29", "Report n°2 (descriptive)")
R_REP2_RERUN = ("R", "2026-10-30", "Report n°2 (re-run, descriptive)")
R_REP2_WSL = ("R", "2026-10-30", "Report n°2 (WSL2 re-run, descriptive)")
R_POWER = ("R", "2026-10-30", "Size and power of the pass rule (descriptive)")
R_H4 = ("R", "2026-10-31", "H4")
R_H5 = ("R", "2026-10-31", "H5")
R_H13 = ("R", "2026-10-31", "H13")
R_H13_REP = ("R", "2026-10-31", "H13's timing, repeated (descriptive)")
R_REP3 = ("R", "2026-10-31", "Report n°3 (descriptive)")

H_H15 = ("H", "| H15 |")
H_H2 = ("H", "| H2 |")

P_CONFIRM = ("P", "1. **Confirmatory population.**")
P_DESCR = ("P", "2. **Descriptive population.**")
P_DRAW = ("P", "**The draw, at code level.**")
P_ROWS = ("P", "**Rows:** 502 per pair")
P_TABLE_SHA = ("P", "**SHA-256 of `table.json`:**")
P_BANDS = ("P", "**Share of levels in [0.02, 0.98]")
P_INVARIANT = ("P", "6. **What this means for the reading of FI's rate.**")
P_SHARED = ("P", "**Shared ground.**")
P_REACH = ("P", "2. **Compared rows.**")
P_MISSING = ("P", "1. **A missing bar.**")
P_FI = ("P", "1. **FI (future invariance).**")
P_TRUNC1_DEV = ("P", "*Deviation from v1, dated 2026-11-18:*")
P_TILES = ("P", "Tile lengths τ ∈")
P_DEEPEST = ("P", "The deepest past read is")
P_TWO_RUN = ("P", "5. **TWO-RUN (ours, after Fonseca's §8.3 class).**")
P_DRAWS = ("P", "**Draws:** `rng = np.random.default_rng(")
P_TIES = ("P", "5. **The generator's ties to H1.**")
P_NEVER = ("P", "**Consequence, added to the generator's \"never produced\" list")
P_RULES = ("P", "**Decision rules.** A comparison passes when")
P_DESC_RUN = ("P", "2. **The descriptive run:** `python -m olsprime.bench.detectors run")
P_PSI = ("P", "takes its correlation estimate ψ as Fagerland, Lydersen and Laake")
P_FI_M2 = ("P", "**FI on M2 is three-valued.**")
P_SIGMA = ("P", "**The two σ share `z`**")
P_BODY = ("P", "**Reported per σ, on the perturbed bars:**")
P_TWO_RUNS = ("P", "**Runs:** 2 runs per cut in the primary analysis")
P_SHUFFLE = ("P", "6. **SHUFFLE (the future-shuffle twins")
P_COUNTS = ("P", "7. **Run counts per cut, primary:**")
P_LONG = ("P", "**Secondary schedule (Fonseca's sampled epochs).**")
P_NO_CONTROL = ("P", "Leaks with no `At` or `Agg` future node")
P_BOOT = ("P", "15. **The cut-date bootstrap**")
P_H15_POWER = ("P", "**Power.** With 3 % of leaks discordant")
P_DATE_SHIFT = ("P", "**Reported beside it, never deciding:**")
P_GATES = ("P", "**Equivalence gates** (pass 5a, m4)")
P_A5A = ("P", "- 2026-11-18, before any detector of iteration 5 runs on a leak")
P_A5B = ("P", "- 2026-11-19, after audit pass 5b (GO with fixes")
P_A5BB = ("P", "- 2026-11-19, after audit pass 5b-bis (GO with fixes")
P_DEV_DIGEST = ("P", "**The development population's digest (§1.7).**")
P_SUITE = ("P", "**Pass 5b-bis reproduced it at the frozen commit:**")
P_CODE_DIGEST = ("P", "**The code digest** (pass 5b-bis, Minor 2).")
P_MINOR3 = ("P", "**Minor 3.** Five mutants planted")
P_FROZEN = ("P", "The frozen commit is `b71ba654ff7060ff7f835f8c3325cbd073eddaa9`")
P_EXPOSURE = ("P", "**What was read.** To prove the holes D1 and D2")
P_MATRIX_WIN = ("P", "The windows are 30 days, 365 days and all history.")
P_FEATURES = ("P", "- Features: the 15 `FEATURE_COLUMNS`")
P_LABELS = ("P", "- Labels: three classes over h = 24 bars")
P_PANEL = ("P", "233 of the 274 members have a member month in the development period")
P_ENC_WIN = ("P", "**Inputs: a window of bars.**")
P_ENC_DM = ("P", "- a linear map of the eight quantities to d_model")
P_ENC_BLOCKS = ("P", "pre-LayerNorm blocks:")
P_ENC_HEADS = ("P", "  - attention, with 4 heads of d_head")
P_ENC_MEM = ("P", "- A readout at decision time d uses the entries with d − 30 days")

N = r"([-+−]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"  # one number as printed
T = r"(\d{1,3}(?:,\d{3})+|\d+)"  # one integer, thousands commas allowed

SPEC: list[tuple[tuple[str, ...], tuple, str, object]] = [
    # --- H1, the record of future invariance before this benchmark ---------------------------
    (("HoneHonest", "HoneControls"), R_H1_FIRST, r"(\d+) honest models, (\d+) controls", "num"),
    (("HonePairCuts",), R_H1_FIRST, r"1d: (\d+) cuts per pair", "num"),
    (("HoneFactor",), R_H1_FIRST, r"multiplied by (\d+) in one run", "num"),
    (("HoneCheatCut", "HoneCheatCuts"), R_H1_SECOND, r"cheater is caught at (\d+) of (\d+) cuts", "num"),
    (("HoneSmallBTC", "HoneSmallETH"), R_H1_SECOND,
     r"smallest catch is ([\d.]+e-\d+) on BTCUSDT and ([\d.]+e-\d+) on ETHUSDT", "sci"),
    (("HonePanelMembers",), R_H1_PANEL, r"arms on the (\d+)-member sub-panel", "num"),
    (("HonePanelCuts",), R_H1_PANEL, r"hourly bars: (\d+) cuts", "num"),
    (("AdvN", "AdvSeed"), R_ADV, T + r" random leaks \(seed (\d+)\)", "num"),
    (("AdvCuts", "AdvLongCuts"), R_ADV, r"at H1's (\d+) cuts and a long schedule of (\d+) cuts", "num"),
    (("AdvCaught", "AdvTotal", "AdvRate", "AdvRateLo", "AdvRateHi"), R_ADV,
     r"Caught at one of H1's cuts at least: " + T + r" of " + T + r", " + N + r" %, 95 % Wilson \["
     + N + r" %, " + N + r" %\]", "num"),
    (("AdvPerCut", "AdvPerCutLo", "AdvPerCutHi"), R_ADV,
     r"Mean per-cut rate at H1's cuts: " + N + r" %, 95 % \[" + N + r" %, " + N + r" %\]", "num"),
    (("AdvTwinsCaught", "AdvTwinsTotal"), R_ADV, r"Honest twins caught: (\d+) of " + T + r"", "num"),
    (("AdvTwinsConst", "AdvTwinsConstPct"), R_ADV,
     T + r" of them \(" + N + r" %\) are constant at the compared rows and cannot", "num"),
    (("AdvDesigned", "AdvDesignedTotal"), R_ADV, r"Designed leaks: " + T + r" of " + T + r" caught", "num"),
    (("AdvEpsMin", "AdvEpsMinRate"), R_ADV, r"eps (1e-10) " + N + r" %", ("sci", "num")),
    (("AdvMissed", "AdvMissedConst"), R_ADV,
     r"(\d+) leaks are caught at no cut of H1; (\d+) of them are constant", "num"),
    (("TwinsK",), R_TWINS, r"K = (\d+) twins per cut", "num"),
    (("TwinsConst", "TwinsConstPct", "TwinsConstLo", "TwinsConstHi"), R_TWINS,
     r"constant at the compared rows (\d+) \(" + N + r" %, Wilson \[" + N + r", " + N + r"\]\)", "num"),
    (("TwinsUnch", "TwinsUnchPct"), R_TWINS, r"unchanged under every twin (\d+) \(" + N + r" %", "num"),
    (("TwinsBlind", "TwinsBlindPct"), R_TWINS, r"true blind spots (\d+) \(" + N + r" %", "num"),
    (("TwinsMoved", "TwinsMovedOf", "TwinsMovedPct"), R_TWINS,
     r"Caught leaks moved by some twin: " + T + r" of " + T + r", " + N + r" %", "num"),
    (("CorrMisses", "CorrBothConst", "CorrBothUnch", "CorrBothBlind", "CorrHoneConst",
      "CorrHoneUnch", "CorrHoneBlind", "CorrBetween"), R_CORR,
     r"(\d+) misses at H1's cuts: both schedules' flag (\d+) constant / (\d+) unchanged / (\d+) "
     r"blind spots; H1's cuts only (\d+) / (\d+) / (\d+); nested, (\d+) between them", "num"),
    (("CorrAllCuts",), R_CORR, r"pools all (\d+) cuts of its two schedules", "num"),
    (("EncPosBSS", "EncPosLo", "EncPosHi"), R_ENC_H1,
     r"Brier skill score " + N + r" \[" + N + r", " + N + r"\] against the climatology of its own label",
     "num"),
    (("EncStampBSS", "EncStampLo", "EncStampHi"), R_ENC_H1,
     r"`cheat-stamp` " + N + r" \[" + N + r", " + N + r"\] \(interval NOT above", "num"),
    (("EncStampFloor",), R_ENC_H1, r"and below " + N + r": NOT met", "num"),
    # --- Report n°2: H2, H3, H10-H12 -----------------------------------------------------------
    (("PanelMembers",), R_H2, r"pooled memory over (\d+) members", "num"),
    (("ScoredHours", "ScoredRows", "ScoredShare"), R_H2,
     r"\(" + T + r" scored decision hours, " + T + r" scored rows, " + N + r" % of the hours\)", "num"),
    (("RepTwoVariants",), R_H2, r"\| (\d+) \(10 before this iteration, plus the 8 arms", "num"),
    (("HtwoBSS", "HtwoBSSlo", "HtwoBSShi"), R_H2,
     r"BSS of matrix-select " + N + r" \[" + N + r", " + N + r"\]", "num"),
    (("PreviewMonths", "TestMonths"), R_H2, r"(\d+) of the (\d+) test months", "num"),
    (("HtwoPrevBSS", "HtwoPrevLo", "HtwoPrevHi", "HtwoPrevHours"), R_H2,
     r"previewed months, apart \(description\): " + N + r" \[" + N + r", " + N + r"\] over " + T + r" hours",
     "num"),
    (("RestMonths", "HtwoRestBSS", "HtwoRestLo", "HtwoRestHi", "HtwoRestHours"), R_H2,
     r"the other (\d+) months: " + N + r" \[" + N + r", " + N + r"\] over " + T + r" hours", "num"),
    (("HthreeSmDiff", "HthreeSmPct", "HthreeSmP", "HthreeSmLo", "HthreeSmHi"), R_H3,
     r"minus softmax-1y: " + N + r" \(" + N + r" % of climatology's log-loss\), DM p " + N
     + r", bootstrap \[" + N + r", " + N + r"\]", "num"),
    (("HthreeKnDiff", "HthreeKnPct", "HthreeKnP", "HthreeKnLo", "HthreeKnHi"), R_H3,
     r"minus knn-1y: " + N + r" \(" + N + r" %\), DM p " + N + r", bootstrap \[" + N + r", " + N + r"\]",
     "num"),
    (("HtenDiff", "HtenPct"), R_H10, r"Difference " + N + r" \(" + N + r" % of climatology's log-loss;", "num"),
    (("HtenP", "HtenLo", "HtenHi", "HtenIdent"), R_H10,
     r"DM p " + N + r", bootstrap \[" + N + r", " + N + r"\], does not pass\. Identical hours " + N + r" %",
     "num"),
    (("HelevenDiff", "HelevenPct", "HelevenP", "HelevenLo", "HelevenHi"), R_H11,
     r"Difference " + N + r" \(" + N + r" % of climatology's log-loss\), DM p " + N + r", bootstrap \["
     + N + r", " + N + r"\]", "num"),
    (("HtwelveDiff", "HtwelvePct", "HtwelveP", "HtwelveLo", "HtwelveHi"), R_H12,
     r"Difference " + N + r" \(" + N + r" % of climatology's log-loss\), DM p " + N + r", bootstrap \["
     + N + r", " + N + r"\]", "num"),
    (("MarginFactor", "Margin"), R_H12, r"margin " + N + r" x climatology's log-loss = " + N, "num"),
    (("HtwelveUB", "HtwelveQ"), R_H12,
     r"one-sided 95 % upper bound " + N + r"; bootstrap 95th percentile " + N + r"; both below", "num"),
    (("HtwelveFits", "HtwelveLimit", "HtwelveAlarms", "HtwelveDays"), R_H12,
     r"Fits: (\d+), against the limit of (\d+) \((\d+) alarms over " + T + r" daily values\)", "num"),
    (("CusumK", "CusumH", "CusumARL"), R_H12,
     r"Page CUSUM alarm, k = " + N + r", threshold " + N + r", ARL (\d+) days", "num"),
    (("LLclim", "LLclimLo", "LLclimHi"), R_REP2,
     r"(?<=\s)climatology-panel " + N + r" \[" + N + r", " + N + r"\]", "num"),
    (("LLsel", "LLselLo", "LLselHi"), R_REP2, r"(?<=\s)matrix-select " + N + r" \[" + N + r", " + N + r"\]", "num"),
    (("LLoney", "LLoneyLo", "LLoneyHi"), R_REP2, r"(?<=\s)matrix-1y " + N + r" \[" + N + r", " + N + r"\]", "num"),
    (("LLsoft", "LLsoftLo", "LLsoftHi"), R_REP2, r"(?<=\s)softmax-1y " + N + r" \[" + N + r", " + N + r"\]", "num"),
    (("LLknn", "LLknnLo", "LLknnHi"), R_REP2, r"(?<=\s)knn-1y " + N + r" \[" + N + r", " + N + r"\]", "num"),
    (("LLadapt", "LLadaptLo", "LLadaptHi"), R_REP2,
     r"(?<=\s)matrix-adaptive " + N + r" \[" + N + r", " + N + r"\]", "num"),
    (("LLstack", "LLstackLo", "LLstackHi"), R_REP2,
     r"(?<=\s)matrix-stack " + N + r" \[" + N + r", " + N + r"\]", "num"),
    (("LLcusum", "LLcusumLo", "LLcusumHi"), R_REP2,
     r"(?<=\s)matrix-cusum " + N + r" \[" + N + r", " + N + r"\]", "num"),
    (("BSSsel", "BSSoney", "BSSsoft", "BSSknn", "BSSadapt", "BSSstack", "BSScusum"), R_REP2,
     r"BSS against climatology: " + N + ", " + N + ", " + N + ", " + N + ", " + N + ", " + N + " and " + N
     + " for the seven other arms", "num"),
    (("RepTwoCheckFiles",), R_REP2, r"`--check` reproduces its (\d+) files byte for byte", "num"),
    (("RepTwoRerunFiles",), R_REP2_RERUN, r"`--check` reproduces its (\d+) files byte for byte", "num"),
    (("PyWSL", "PyWin"), R_REP2_WSL, r"Python ([\d.]+) \(Windows: ([\d.]+)\)", "ver"),
    (("PlatProbArms", "PlatArms", "PlatProbMax"), R_REP2_WSL,
     r"Probabilities differ in (\d+) of (\d+) arms, by at most (\d\.\d × 10[⁻¹²³⁴⁵⁶⁷⁸⁹⁰]+)",
     ("num", "num", "sci")),
    (("PlatNums", "PlatNumsOf", "PlatRelMax"), R_REP2_WSL,
     r"(\d+) of " + T + r" numbers of `report2.json` differ, by at most (\d\.\d × 10[⁻¹²³⁴⁵⁶⁷⁸⁹⁰]+) relative",
     ("num", "num", "sci")),
    # --- the size and power of the pass rule ---------------------------------------------------
    (("PowLa", "PowLb", "PowLc", "PowLd"), R_POWER, r"L ∈ \{(\d+), (\d+), (\d+), (\d+)\} hours", "num"),
    (("PowSizeReps",), R_POWER, T + r" replicates per L for size", "num"),
    (("PowGrid", "PowGridReps"), R_POWER, r"grid of (\d+) points with " + T + r" replicates each", "num"),
    (("PowConcPct", "PowConcBlock", "PowConcL"), R_POWER,
     r"concentrated in (\d+) % of (\d+)-hour blocks \(L = (\d+)\)", "num"),
    (("PowSeed", "PowReps"), R_POWER, r"flip seed (\d+); " + T + r" replicates\.", "num"),
    (("PowSizeLo", "PowSizeHi", "PowSizeCap"), R_POWER,
     r"two-sided size is " + N + r" % to " + N + r" % for every comparison and L: none above " + N + r" %",
     "num"),
    (("PowDirLo", "PowDirHi"), R_POWER, r"registered direction, " + N + r" % to " + N + r" %", "num"),
    (("PowBootMax", "PowBootLa", "PowBootLb"), R_POWER,
     r"bootstrap alone reaches " + N + r" % \(H10, L = (\d+) and (\d+)\)", "num"),
    (("PowTwelveLo", "PowTwelveHi"), R_POWER, r"H12 holds at its margin " + N + r" % to " + N + r" %", "num"),
    (("PowTarget",), R_POWER, r"smallest δ with (\d+) % power", "num"),
    (("PowSmLo", "PowSmHi", "PowSmConc"), R_POWER,
     r"H3 vs softmax " + N + r" % to " + N + r" % \(" + N + r" %\)", "num"),
    (("PowKnLo", "PowKnHi", "PowKnConc"), R_POWER, r"H3 vs kNN " + N + r" % to " + N + r" % \(" + N + r" %\)", "num"),
    (("PowTenLo", "PowTenHi", "PowTenConc"), R_POWER, r"H10 " + N + r" % to " + N + r" % \(" + N + r" %\)", "num"),
    (("PowElLo", "PowElHi", "PowElConc"), R_POWER, r"H11 " + N + r" % to " + N + r" % \(" + N + r" %\)", "num"),
    (("PowKnObs", "PowKnObsLo", "PowKnObsHi"), R_POWER,
     r"`knn-1y`, " + N + r" %, has (\d+) % to (\d+) % power", "num"),
    (("PowElObs", "PowElObsLo", "PowElObsHi"), R_POWER, r"H11's " + N + r" %, (\d+) % to (\d+) %", "num"),
    (("PowSecs", "PowWorkers"), R_POWER, r"first run's facts: " + T + r" s, (\d+) workers", "num"),
    # --- Report n°3: H4, H5, H13 ------------------------------------------------------------------
    (("RepThreeVariants",), R_H4, r"\| (\d+) \(18 before, plus the 3 encoder arms\)", "num"),
    (("Seeds", "YearlyFits"), R_H4, r"(\d+) seeds per arm, (\d+) yearly fits per seed", "num"),
    (("HfourBSSols", "HfourBSSolsLo", "HfourBSSolsHi", "HfourBSSsm", "HfourBSSsmLo", "HfourBSSsmHi"), R_H4,
     r"BSS `enc-ols` " + N + r" \[" + N + r", " + N + r"\], `enc-softmax` " + N + r" \[" + N + r", " + N + r"\]",
     "num"),
    (("HfourDiff", "HfourPct", "HfourMargin", "HfourUB", "HfourQ"), R_H4,
     r"Difference " + N + r" \(" + N + r" % of climatology's log-loss [\d.]+\); margin " + N
     + r"; one-sided 95 % upper bound " + N + r"; bootstrap 95th percentile " + N + ";", "num"),
    (("HfourLo", "HfourHi", "HfourP"), R_H4,
     r"Bootstrap 95 % interval \[" + N + r", " + N + r"\], DM p ([\d.]+e-\d+)", ("num", "num", "sci")),
    (("HfourSeedA", "HfourSeedB", "HfourSeedC"), R_H4, r"upper bounds " + N + r", " + N + r", " + N + r"\)", "num"),
    (("HfourRev",), R_H4, r"has upper bound " + N + r", also below the margin", "num"),
    (("HfiveDiff", "HfivePct", "HfiveP", "HfiveLo", "HfiveHi"), R_H5,
     r"Difference " + N + r" \(" + N + r" % of climatology's log-loss; positive: `enc-ols` worse\), DM p " + N
     + r", bootstrap 95 % interval \[" + N + r", " + N + r"\]", "num"),
    (("HfiveLLols", "HfiveLLsel"), R_H5, r"Log-loss " + N + r" for `enc-ols` against " + N + r" for `matrix-select`",
     "num"),
    (("HthirteenRatio", "HthirteenBound"), R_H13, r"Registered ratio " + N + r" \(paired-median ratio [\d.]+\); bound " + N,
     "num"),
    (("HthirteenRepeats",), R_H13, r": (\d+) repeats cycling the arms", "num"),
    (("CacheReserved", "CardTotal"), R_H13, T + r" MiB reserved on a card of " + T + r" MiB", "num"),
    (("RatioAsIs", "RatioEmptied"), R_H13,
     r"the ratio is " + N + r" as the code stands and " + N + r" with that cache emptied", "num"),
    (("RatioSynthLo", "RatioSynthHi"), R_H13, r"Synthetic rows give " + N + r" to " + N + r" on that", "num"),
    (("LLols", "LLolsLo", "LLolsHi", "BSSols", "BSSolsLo", "BSSolsHi"), R_REP3,
     r"`enc-ols` log-loss " + N + r" \[" + N + r", " + N + r"\], BSS " + N + r" \[" + N + r", " + N + r"\]", "num"),
    (("LLencsm", "LLencsmLo", "LLencsmHi", "BSSencsm", "BSSencsmLo", "BSSencsmHi"), R_REP3,
     r"`enc-softmax` log-loss " + N + r" \[" + N + r", " + N + r"\], BSS " + N + r" \[" + N + r", " + N + r"\]",
     "num"),
    (("LLlin", "LLlinLo", "LLlinHi", "BSSlin", "BSSlinLo", "BSSlinHi"), R_REP3,
     r"`enc-linear` log-loss " + N + r" \[" + N + r", " + N + r"\], BSS " + N + r" \[" + N + r", " + N + r"\]",
     "num"),
    (("ParamsOls",), R_REP3, r"`enc-ols`: " + T + r" parameters", "num"),
    (("ParamsSm",), R_REP3, r"`enc-softmax`: " + T + r" parameters", "num"),
    (("ParamsLin",), R_REP3, r"`enc-linear`: " + T + r" parameters", "num"),
    (("RepThreeFits",), R_REP3, r"6 yearly fits per seed \((\d+) fits\)", "num"),
    (("RepThreeCheckFiles",), R_REP3, r"every part verifies and (\d+) files are identical", "num"),
    # --- the registered design of iteration 5 ------------------------------------------------------
    (("PopN", "ConfSeed", "HoneCutsN"), H_H15,
     r"population of " + T + r" leaks of seed (\d+) \(placement `quantile`\), at H1's (\d+) cuts", "num"),
    (("NewcombeMethod",), H_H15, r"Newcombe 95 % interval \(method (\d+)\)", "num"),
    (("HfifteenMargin",), H_H15, r"against a margin of (\d+) point", "num"),
    (("Conf",), H_H2, r"with a block-bootstrap (\d+) % interval excluding 0", "num"),
    (("DevSeed",), P_CONFIRM, r"use seed \*\*(\d+)\*\* only", "num"),
    (("DescSeed", "DescFIany", "DescFIper"), P_DESCR,
     r"The [\d,]+ leaks of seed (\d+), placement `h1-bands`.*?\(" + N + r" % any-cut, " + N + r" % per cut\)", "num"),
    (("LevelLo", "LevelHi"), P_DRAW, r"`level = rng.uniform\(" + N + r", " + N + r"\)`", "num"),
    (("TableRows",), P_ROWS, r"\*\*Rows:\*\* (\d+) per pair", "num"),
    (("TableSha",), P_TABLE_SHA, r"`([0-9a-f]{64})`", "hex"),
    (("BandBody", "BandUpper", "BandLower", "BandRange", "BandFill", "BandCloseLoc", "BandHalf"), P_BANDS,
     r"body " + N + r" %, upper wick " + N + r" %, lower wick " + N + r" %, range " + N + r" %, fill " + N
     + r" %, close location " + N + r" %\. Under `h1-bands` each is " + N + r" %", "num"),
    (("InvSubset", "InvOf"), P_INVARIANT, r"\(" + T + r" of " + T + r" on a neutral seed\)", "num"),
    (("InsideTagged", "InsideThresholds"), P_INVARIANT,
     T + r" of [\d,]+ leaks are tagged `inside`, only (\d+) of them thresholds", "num"),
    (("CutDates", "CutRowA", "CutRowB", "CutRowC", "CutRowD", "CutRowE", "CutRowF", "CutRowG", "CutRowH",
      "CutSeed"), P_SHARED,
     r"(\d+) dates, the same row indices on both pairs \((\d+), (\d+), (\d+), (\d+), (\d+), (\d+), (\d+), (\d+)\), "
     r"chosen by `invariance.choose_cuts` with seed (\d+)", "num"),
    (("Reach",), P_REACH, r"\(`FUTURE_REACH = (\d+)`\)", "num"),
    (("CatchThreshold",), P_MISSING, r"counts a move above (1e-9)", "sci"),
    (("FIup", "FIdown", "FIseed"), P_FI, r"×(\d+) and ÷(\d+) at each cut.*?\(perturbation seed (\d+)\)", "num"),
    (("ReachOneShare",), P_TRUNC1_DEV, r"future reach 1 \(" + N + r" % of draws\)", "num"),
    (("TauA", "TauB"), P_TILES, r"τ ∈ \{(\d+), (\d+)\} bars", "num"),
    (("TileEnds",), P_TILES, r"\*\*(\d+) ends in all\.\*\*", "num"),
    (("DeepestRead",), P_DEEPEST, r"The deepest past read is (\d+) bars", "num"),
    (("TwoRunBars",), P_TWO_RUN, r"the bars `t \+ 1 \.\. t \+ (\d+)` \(the only later bars", "num"),
    (("TwoRunDevSeed", "TwoRunSeed"), P_DRAWS, r"Development seed \*\*(\d+)\*\* in place of (\d+)\.", "num"),
    (("SigmaLo", "SigmaHi"), P_SIGMA, r"Primary σ = " + N + r"; secondary σ = " + N + r"\.", "num"),
    (("BodyBefore", "BodyAfter", "FillBefore", "FillAfter", "BodyHiSigma"), P_BODY,
     r"median body " + N + r" to " + N + r", median fill " + N + r" to " + N + r"; σ = [\d.]+: median body " + N,
     "num"),
    (("TwoRunOne", "TwoRunMany"), P_TWO_RUNS, r"reported also with (\d+) run \(run 1\) and (\d+) runs", "num"),
    (("ShuffleOne", "ShuffleTwo"), P_SHUFFLE, r"Reported also with its first (\d+) and (\d+) twins", "num"),
    (("RefWindow",), P_TIES, r"the (\d+)-bar reference window", "num"),
    (("NeverLo", "NeverHi"), P_NEVER, r"beyond the (\d+)nd or the (\d+)th percentile", "num"),
    (("BootPLo", "BootPHi"), P_BOOT, r"the ([\d.]+)th and ([\d.]+)th percentiles of the any-cut difference", "num"),
    (("DescTwoRunSeed", "DescBootSeed"), P_DESC_RUN,
     r"\*\*Seeds (\d+) \(TWO-RUN\) and (\d+) \(cut-date bootstrap\) are new\*\*", "num"),
    (("PsiDiff", "PsiDiffExtreme"), P_PSI,
     r"at most " + N + r" point at n = [\d,]+, " + N + r" on an extreme table", "num"),
    (("PsiFlag",), P_PSI, r"If a limit falls within " + N + r" point of 0 or of", "num"),
    (("MtwoNum", "MtwoDen"), P_FI_M2, r"`high\[t\+1\] ≥ (\d+)/(\d+) · close\[t\]`", "num"),
    (("PassP",), P_RULES, r"gives p < ([\d.]+)", "num"),
    (("QuantPct",), R_H12, r"bootstrap (\d+)th percentile", "num"),
    (("WaveCPython", "WaveNumpy"), P_FROZEN, r"CPython ([\d.]+), numpy ([\d.]+), the development digest", "ver"),
    (("ShuffleK", "ShuffleSeed"), P_SHUFFLE, r"K = (\d+) twins per cut, seed (\d+)", "num"),
    (("RunsFI", "RunsTruncZero", "RunsTruncOne", "RunsTwo", "RunsShuffle"), P_COUNTS,
     r"FI (\d+), TRUNC-0 (\d+), TRUNC-1 (\d+), TWO-RUN (\d+), SHUFFLE (\d+)\.", "num"),
    (("LongFIseed", "LongPerPair", "LongCutSeed", "LongTotal"), P_LONG,
     r"FI \(perturbation seed (\d+)\).*?(\d+) cuts per pair, \d+ dates shared by both pairs, long cut seed (\d+)"
     r".*?over the 16 \+ (\d+) cuts", "num"),
    (("NoControlShare",), P_NO_CONTROL, r"about " + N + r" % in the synthetic draw", "num"),
    (("BootSubsets", "BootDates", "BootSeed"), P_BOOT,
     T + r" subsets of (\d+) dates drawn without replacement, the same dates on both pairs, seed (\d+)",
     "num"),
    (("PowDiscA", "PowHalfA", "PowDetA", "PowDiscB", "PowHalfB", "PowDetB"), P_H15_POWER,
     r"With " + N + r" % of leaks discordant, the paired difference's 95 % half-width is near " + N
     + r" point and a difference of " + N + r" point is detected with 80 % power; with " + N
     + r" % discordant, " + N + r" and " + N + r" point", "num"),
    (("ShiftChanged", "ShiftOf"), P_DATE_SHIFT, r"changed the any-cut verdict of (\d+) of " + T + r" leaks", "num"),
    (("GateLeaks", "GateSeed"), P_GATES, r"on (\d+) leaks \(equivalence seed (\d+)\)", "num"),
    (("AfiveaBlock", "AfiveaMajor", "AfiveaMinor", "AfiveaNit", "AfiveabisMajor", "AfiveabisMinor"), P_A5A,
     r"\(register with fixes: (\d+) Blockers, (\d+) Major, (\d+) Minor, (\d+) Nits\) and pass 5a-bis "
     r"\(register with fixes: no Blocker, (\d+) Major, (\d+) Minor\)", "num"),
    (("AfivebMajor", "AfivebMinor", "AfivebNit"), P_A5B,
     r"\(GO with fixes, no Blocker; (\d+) Major, (\d+) Minor, (\d+) Nits\)", "num"),
    (("AfivebbisMajor", "AfivebbisMinor", "AfivebbisNit"), P_A5BB,
     r"\(GO with fixes, no Blocker; (\d+) Major, (\d+) Minor, (\d+) Nits;", "num"),
    (("DevDigest", "NumpyVer"), P_DEV_DIGEST, r"SHA-256 `([0-9a-f]{64})`, numpy ([\d.]+),", ("hex", "ver")),
    (("SuitePassed", "SuiteSkipped", "MutKilled", "MutTotal"), P_SUITE,
     T + r" passed and (\d+) skipped; the mutant test, (\d+) of (\d+) killed", "num"),
    (("CodeDigest", "CodeFiles"), P_CODE_DIGEST, r"`([0-9a-f]{64})` \((\d+) files\)", ("hex", "num")),
    (("MutLater",), P_MINOR3, r"the kill count of all (\d+) is reported", "num"),
    (("FrozenCommit",), P_FROZEN, r"The frozen commit is `([0-9a-f]{40})`", "hex"),
    (("ExposedBars",), P_EXPOSURE, r"the (\d+) bars of the 2026-03 raw archive", "num"),
    (("WinShort", "WinYear"), P_MATRIX_WIN, r"The windows are (\d+) days, (\d+) days and all history", "num"),
    (("Features",), P_FEATURES, r"the (\d+) `FEATURE_COLUMNS`", "num"),
    (("LabelBars",), P_LABELS, r"three classes over h = (\d+) bars", "num"),
    (("PanelAll", "PanelLate"), P_PANEL, r"of the (\d+) members have a member month.*?the other (\d+) first join", "num"),
    (("EncT",), P_ENC_WIN, r"reads the (\d+) hourly bars of pair s", "num"),
    (("EncDmodel",), P_ENC_DM, r"d_model = (\d+)", "num"),
    (("EncBlocks",), P_ENC_BLOCKS, r"- (\d+) pre-LayerNorm blocks:", "num"),
    (("EncHeads", "EncDhead"), P_ENC_HEADS, r"with (\d+) heads of d_head = (\d+);", "num"),
    (("EncMemDays",), P_ENC_MEM, r"d − (\d+) days < `label_known_at` ≤ d", "num"),
]


def locate(source: tuple) -> tuple[int, str, str]:
    kind = source[0]
    if kind == "R":
        return results_row(*source[1:])
    if kind == "H":
        return anchored_line(HYPOTHESES, source[1])
    if kind == "P":
        return anchored_line(PROTOCOL, source[1])
    raise Missing(f"unknown source kind {kind!r}")


def build() -> list[str]:
    seen: set[str] = set()
    out = [
        "% numbers.tex -- GENERATED by paper/make_numbers.py; do not edit by hand.",
        "% Every macro below is read from the line named in its comment.",
        "% Wave 4's rates, H15's verdict and the case study's analyses are not here: they wait",
        "% for audit phase 2a and appear in main.tex as \\todo{after audit 2a}.",
        "",
    ]
    for names, source, pattern, formats in SPEC:
        lineno, text, where = locate(source)
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1:
            raise Missing(f"{where}: pattern {pattern!r} matched {len(matches)} times")
        groups = matches[0].groups()
        if len(groups) != len(names):
            raise Missing(f"{where}: {len(groups)} groups for {len(names)} macros")
        fmts = formats if isinstance(formats, tuple) else (formats,) * len(names)
        out.append(f"% {ascii_only(where)}")
        out.append(f"%   pattern: {ascii_only(pattern)}")
        out.append(f"%   matched: {ascii_only(matches[0].group(0))}")
        for name, raw, fmt in zip(names, groups, fmts):
            if not re.fullmatch(r"[A-Za-z]+", name):
                raise Missing(f"macro name {name!r}: letters only")
            if name in seen:
                raise Missing(f"macro {name!r} defined twice")
            seen.add(name)
            value = raw if fmt is None else FORMATS[fmt](raw)
            out.append(f"\\newcommand{{\\Num{name}}}{{{value}}}  % raw: {ascii_only(raw)}")
        out.append("")
    return out


def main() -> int:
    try:
        lines = build()
    except Missing as err:
        print(f"make_numbers: {err}", file=sys.stderr)
        return 1
    text = "\n".join(lines) + "\n"
    text.encode("ascii")  # raises if anything non-ASCII slipped through
    with OUT.open("w", encoding="ascii", newline="\n") as fh:
        fh.write(text)
    count = sum(1 for line in lines if line.startswith("\\newcommand"))
    print(f"make_numbers: wrote {count} macros to {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
