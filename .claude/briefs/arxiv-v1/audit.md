# Brief — audit of the paper's pre-submission diff (leakage-auditor, 2026-11-20)

**What changed.** Draft 4 of `paper/` is on `main` at `670d6b0`. The branch `arxiv-v1` changes `paper/main.tex`, `paper/refs.bib` and one line of `docs/DESIGN.md` (staged, not committed: `git diff --cached main -- paper docs/DESIGN.md`). The changes come from two readings:
- `reading-notes.md`: the method papers and the three revised arXiv sources;
- `reading-2-notes.md`: the verbatim re-read of the other cited passages.

Abdou's decisions are folded in: arXiv category cs.LG with a q-fin.ST cross-list, and licence CC BY-NC-SA 4.0. No number, macro, run or code changed.

**Read, claim by claim.**
1. Every changed sentence and `%` comment against the notes. Does the paper now state only what the notes record as read, at the level of reading recorded (verbatim, summarised, metadata only)?
2. The five method papers still at "metadata only": Wilson, Harvey–Leybourne–Newbold, Politis–Romano, Page, Chan–Golub–LeVeque. Is citing them only to name a standard method, with the gap stated in the paper, acceptable under the rule in `.claude/briefs/iteration-5/paper.md` ("Method citations")? Or must a citation or a sentence go? Say which.
3. The pairwise-merge formula now written out in §Matrix (`M_{A∪B} = M_A + M_B + n_A n_B/(n_A+n_B) δδᵀ`). Check it against `crates/ols-core` (the centred merge) and `docs/DESIGN.md` §3.1, with the sign and the scaling.
4. The freqtrade sentence: "through pandas' `DataFrame.compare`, under which two missing values do not differ". Check it against what `docs/PROTOCOL.md` §0.4 recorded of `lookahead.py`, and against pandas' documented behaviour if you can.
5. Overclaiming introduced by the new wording, including the "Reproducibility", "Limitations" and "AI assistance" sections, and the paragraph "How the sources were read".
6. Every `\todo` left must be one of Abdou's open decisions: the title, the author name, the endorser, the repository archive, the release of the corpus.

**Also check** that the paper compiles. A copy built with MiKTeX in a temporary folder gives 23 pages, no error and no BibTeX warning: `pdflatex -interaction=nonstopmode --disable-installer main.tex`, then `bibtex`, then `pdflatex` twice.

**Output.** Findings graded Blocker, Major, Minor or Nit, each with its file, line and a replacement text where you can give one. End with a verdict: GO for v1 (pending Abdou's decisions), GO with fixes, or NO-GO. Edit no file; the orchestrator saves the report as `audit-findings.md`.
