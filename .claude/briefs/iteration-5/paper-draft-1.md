# Brief — the paper's first draft, the parts that do not wait for audit 2a

- **Writer:** a fresh Opus agent, briefed by the orchestrator (2026-11-19). The orchestrator reads the draft, and audit phase 2b reads every claim. Your draft is a claim, not a result.
- **Read first:**
  - `CLAUDE.md`;
  - `.claude/briefs/iteration-5/paper.md`, the paper's brief: its claims, its "Never claim" list and its "Must contain" list bind you;
  - `docs/RESULTS.md`, `docs/HYPOTHESES.md`;
  - `docs/PROTOCOL.md`: the section "Leak detectors measured against each other (iteration 5)" and its change log from 2026-11-18;
  - `docs/DATA.md`;
  - the reading notes `reading-papers.md`, `reading-credits.md` and `reading-terms.md` in this folder.
- **Abdou's rule of 2026-11-19:** the paper comes first. Propose a bolder step only if it would significantly improve the paper.

## Why now, and what waits

Wave 4 (the detector runs) and the case study's real call are done. Audit 2a is recomputing their numbers right now. Until it returns, nothing from those runs is a result. So:
- **Write now:**
  - the introduction, without the abstract;
  - the related work;
  - the bench and the detectors, defined as `docs/PROTOCOL.md` registers them;
  - the pre-registration and its dated changes: the audits, the frozen commit `b71ba65`, the spent seeds, the platform pin, the stop rules;
  - claim 2 (the pass rule's size and power) and claim 3 (Matrix), from `docs/RESULTS.md`;
  - the recorded part of claim 4 (Reports n°2 and n°3, exactly as `docs/RESULTS.md` records H2–H5, H10–H13);
  - the limits, reproducibility, AI use and data credit sections.
- **Leave as visible placeholders** (`\todo{after audit 2a}`):
  - the abstract;
  - every wave-4 number and H15's verdict;
  - the case study's two exploratory analyses (`runs/2026-11-19-casestudy/`);
  - every sentence that states a verdict from those runs.

  You may lay out their tables' structure, with empty cells.

## Rules

- **Numbers.** Every number comes from a generated file: `paper/numbers.tex`, written by `paper/make_numbers.py` from the source it names (a `docs/RESULTS.md` row or a run's JSON path), one `\newcommand` per number, with a comment naming its source. Never type a number by hand.
- **Citations.** No source in the notes is read in full; each is "partial", with the parts read named. Cite a source only for a statement found in the parts the notes record as read, and put a `%` comment beside each citation naming the section or page. Nothing from an abstract or a summary alone. If a credit in `paper.md`'s claim 3 cannot be supported this way, drop that credit and list it in your report.
  - This replaces `paper.md`'s "read in full" rule for this draft (orchestrator, 2026-11-19, under Abdou's rule).
- **Never claim** (verbatim from `paper.md`):
  - OLS is attention;
  - signed weights;
  - an exact ridge state;
  - the idea of a two-run test;
  - OLS beats softmax;
  - any profit;
  - any result from the vault or the validation year. Both are sealed, and iteration 1's exposure of BTCUSDT 1d vault rows is stated.

  Future invariance is an instance of Fonseca's two-run class, not an invention. The contribution is the measurement, which must survive our detector losing.
- **Abdou's decisions, left as marked placeholders:** the title (use `paper.md`'s working title, marked as a draft), the author name, the arXiv category, the licence (CC BY-NC-SA 4.0 is what the Binance Vision terms impose, pending), and the endorser.
- **AI use:** the project was built with Claude Code agents, and Abdou takes full responsibility for every claim. AI tools are not authors.

## Limits

- **Write only in `paper/`:** `main.tex`, `refs.bib`, `make_numbers.py`, `numbers.tex`, and `figures/` if any. Read everything else; change nothing outside `paper/`.
- **Nothing under the code digest's globs:**
  - no file in `python/olsprime/`, `crates/`, `python/pyproject.toml`, `uv.lock` or `Cargo.lock`;
  - no new dependency (run the script with `cd python && uv run --no-sync python ../paper/make_numbers.py`);
  - tables instead of figures if plotting would need a package that is not installed.
- **Never open `runs/vault/` or the validation year.** Never run anything that reads real bars.
- **No downloads and no installs.**
  - Compile with MiKTeX, already installed on Windows: `pdflatex -interaction=nonstopmode --disable-installer main.tex`, plus `bibtex`.
  - If a package is missing, use another one or drop it. Never install one.
- **No git:** no `git add`, `commit`, `stash`, `checkout` or `reset`.

## Report

1. The files written, and whether `main.tex` compiles (the last lines of the log if it does not).
2. The sections, each marked written or waiting for 2a.
3. Each citation with its read level and the part it rests on, and every credit dropped.
4. The sentences you were unsure of, against the "Never claim" list.
