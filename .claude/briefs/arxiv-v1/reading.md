# Brief — the reading before arXiv v1 (scout, 2026-11-20)

**Why.** Iteration 5's outcome (`docs/ITERATIONS.md`, "Next step: arXiv v1") leaves three reading debts before submission. The paper's citation rule (`.claude/briefs/iteration-5/paper.md`, "Method citations") allows a citation only for a statement found in a part that was read. Audit 2b logged the debts as m9 and N16 (`docs/PROTOCOL.md`, lines near 1204–1206).

**Inputs.** `paper/main.tex`, `paper/refs.bib`, `.claude/briefs/iteration-5/reading-methods.md` (Part A, the metadata already checked) and `reading-credits.md`.

## Part A — the ten method papers, and Chan, Golub and LeVeque

Keys: `wilson1927`, `mcnemar1947`, `diebold1995`, `harvey1997`, `politis1994`, `patton2009`, `neweywest1987`, `page1954`, `brown1975`, `chan1983`.

For each:
1. Read the abstract **and** the first page, from a primary source: the publisher's page, JSTOR's or Wiley's first-page preview, an author's copy, a university repository. Say which, with its URL.
2. Find every sentence of `paper/main.tex` that cites the key (`grep -n '<key>' paper/main.tex`). For each, say whether what we state is supported by the part read: **supported**, **not shown in the part read**, or **contradicted**. Quote at most one short phrase (under 15 words) as evidence.
3. Check the bibliographic record in `paper/refs.bib` against the first page: authors and their initials, title, journal, volume, issue, pages, year. Resolve the fields marked UNCONFIRMED in `reading-methods.md` (Newey–West's end page, Page's given name).
4. **`chan1983` specifically (N16).** Does the 1983 paper (*The American Statistician*) give the pairwise update that merges the mean and sum of squares of two batches? `docs/DESIGN.md:93` credits it to their 1979 report. Say what the pages read show, and the exact wording `docs/DESIGN.md` should use.
5. **`harvey1997` specifically.** The paper names it only as "their modified Diebold–Mariano test". Confirm the abstract describes a modification of the Diebold–Mariano test, and whether it is a small-sample correction.

If no primary page is reachable for a paper, say so: it stays at "metadata only", and the orchestrator decides whether to drop the sentence.

## Part B — the three sources revised since they were read

| Key | Version read | Cited for |
|---|---|---|
| `gouletcoulombe2025ols` (arXiv 2504.09663) | v3, 2026-10-05 | Eq. (7) p. 5; p. 4; Eq. (23) p. 7; Appendix A.4 pp. 15–16; p. 10 |
| `vonoswald2025mesanet` (2506.05233) | v1, 2025-06-05 | Eqs. (4), (6), (8), pp. 1–7 |
| `guo2025loglinear` (2506.04761) | v2, 2025-06-25 | §3.1 pp. 4–5, Table 1; pp. 1–8 |

For each:
1. From the arXiv abstract page's submission history, list the versions and their dates. Say whether a version newer than the one read exists.
2. If one does, read the **latest** version's passages that correspond to the ones cited (equation numbers may have moved). Say whether each statement of `paper/main.tex` that cites the key (lines 226, 242–245, 891–912; grep for the others) still holds against the latest version, and give the new equation or section numbers.
3. Give the updated `refs.bib` fields (version, date, venue if arXiv lists one, e.g. MesaNet as ICLR 2026).

## Constraints

- Primary sources only. No citation status rests on a search snippet or an abstract aggregator; say so where a page was summarised by the fetch tool rather than read verbatim.
- Do not edit any file. Return the report; the orchestrator saves it as `.claude/briefs/arxiv-v1/reading-notes.md` and makes the edits.
- No personal data in any request.

## Done when

A table per part, one row per key (and per citing line), each with: source URL, part read, verbatim or summarised, verdict, the evidence phrase, and the proposed `refs.bib` or wording change. Then a short list of the edits the orchestrator should make.
