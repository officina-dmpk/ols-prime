# Brief — the verbatim re-read of every cited passage (scout, 2026-11-20)

**Why.** `paper/main.tex` line 188 carries the `\todo` "The orchestrator re-reads each cited passage verbatim before submission." In iteration 5 most sources were read through a fetch tool that summarises pages. A summary can drop a qualifier or invent one, so each statement the paper makes about a source is checked against the source's own words before v1. The first run (`reading.md`, notes in `reading-notes.md`) already did this for MesaNet v2 and Log-Linear Attention v3, read as PDF page images, and for the method papers.

**Keys to re-read:** `fonseca2026`, `freqtrade`, `causify2025`, `gouletcoulombe2025ols`, `gouletcoulombe2024dual`, `garnelo2023`, `chen2006regcube`, `nagel2025`, `binancevisionterms`, `katharopoulos2020`, `optmem`, `newcombe1998paired`, `politiswhite2004`.

**For each key:**
1. Find every sentence of `paper/main.tex` that cites it (`grep -n '<key>' paper/main.tex`). The `%` comment beside each `\cite` names the part read (section, page, equation). `paper/refs.bib` gives the version.
2. Open that exact version and part **verbatim**: download the PDF and read the named pages as images, or read the raw text of the page (for freqtrade's documentation and the dataset terms). Do not rely on the fetch tool's summary. If only a summary is reachable, say so: that statement stays at "summarised".
3. For each citing sentence give a verdict: **holds**, **holds with a wording change** (give the replacement text), or **does not hold** (say what the source says instead). Quote at most one phrase under 15 words per sentence as evidence.
4. Note any version newer than the one cited, with its date. Do not re-read a newer version unless the cited statement depends on it.

**Highest priority**, if time is short: `fonseca2026` (the paper's main foil; §8.2 end, §8.3, §9, Table 2), `freqtrade`, `causify2025`, `gouletcoulombe2025ols`, `binancevisionterms`. Then the rest.

**Constraints.** Primary sources only. Edit no file; return the report, which the orchestrator saves as `reading-2-notes.md`. No personal data in any request. If a page is blocked, say so and move on.

**Done when.** One row per citing sentence: key, `main.tex` line, part read, verbatim or summarised, verdict, evidence phrase, proposed replacement if any. Then the list of edits for the orchestrator.
