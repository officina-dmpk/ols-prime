# Reading notes for arXiv v1 (scout, fetched 2026-11-20)

Saved by the orchestrator from the scout's report, brief `reading.md`. "Fetch-summ." means a small model summarised the HTML page. "PDF-verbatim" means the saved PDF was read as page images. The scout edited no file.

## Part A: the ten method papers

| Key (citing lines of draft 4) | Source and part read | Mode | Verdict and evidence | refs.bib or wording change |
|---|---|---|---|---|
| wilson1927 (432, 596) | JSTOR: error page. T&F: 403. A free copy on a third-party host was blocked by the permission system and not fetched. | none | **Metadata only** | None; the DOI stays unverified at a primary page. |
| mcnemar1947 (441, 748) | Springer article page: the abstract only, no preview | Fetch-summ., abstract quoted | **Supported** for a test of correlated proportions: "Two formulas are presented for judging the significance of the difference". The exact binomial p-value is ours, not claimed from the paper. | Author "Quinn McNemar" and pp. 153–157 confirmed. The page lists no issue; keep 2 (Crossref). |
| diebold1995 (821) | NBER Technical Working Paper 169, Nov 1994: cover, abstract, p. 1 of the text. The JBES page is blocked. | PDF-verbatim | **Supported** for tests of no difference in the accuracy of two forecasts: "tests of the null hypothesis of no difference in the accuracy". | The published first page is not read. Volume, issue and pages stay at Crossref/RePEc. |
| harvey1997 (823) | ScienceDirect and Nottingham: 403. RePEc/IDEAS: "No abstract is available." | none | **Metadata only.** Whether the article describes a modified DM test, and whether it is a small-sample correction, is not answered at a primary page. | Authors, title, volume, issue and pages match RePEc. Only a search snippet says "finite sample modifications"; not primary. |
| politis1994 (825) | JSTOR: error page. UCY repository: empty page. | none | **Metadata only** | None |
| patton2009 (832) | Duke author-site copy of the publisher PDF, pp. 1–2 | PDF-verbatim | **Supported**: a correction of Politis and White (2004), "A correction on the optimal block size algorithms of Politis and White (2004)". It sets D_SB = 2g²(0) and replaces eq. (8). | Record correct: Econometric Reviews 28(4):372–375, DOI matches. Comment: "read: pp. 1–2 (Duke author copy)". |
| neweywest1987 (1134) | (a) NBER Technical Working Paper 55, Apr 1986: cover, abstract, p. 1. (b) Econometric Society page of the 1987 article. | (a) PDF-verbatim. (b) Fetch-summ., no abstract shown. | **Supported by (a)**: "describes a simple method of calculating a heteroskedasticity and autocorrelation consistent covariance matrix". The 1987 first page is not read. | **Add `pages = {703--708}`**, confirmed at the Econometric Society page (publisher metadata; Crossref gives only 703). That page lists West first and prefixes the title with "Notes and Comments:"; keep our author order. |
| page1954 (943) | OUP Biometrika page: metadata only; the first page is an image and the PDF is restricted. | Fetch-summ. | **Metadata only.** Vol. 41, issue 1–2, pp. 100–115, June 1954 confirmed. | The given name is unresolved at a primary page, which prints "E. S. Page". Keep the initials. |
| brown1975 (945) | OUP JRSS-B page (the DOI's target), abstract | Fetch-summ. | **Supported** for a test of the constancy of a regression over time: tests built on cumulative sums of recursive residuals and of their squares ("Recursive residuals ... are introduced"). | Vol. 37(2), pp. 149–163 and the initials confirmed. The title ends "Over Time". |
| chan1983 (870) | T&F: 403. DTIC (1979 report, 1981 Yale report): 403. Stanford: connection refused. A course copy on a host with a certificate mismatch looked unauthorised and was not used. | none | **Metadata only.** N16 is not answered at a primary page. | See below. |

**Chan, Golub and LeVeque.** For `docs/DESIGN.md:93` the scout proposes "the pairwise update attributed to Chan, Golub and LeVeque (Stanford report STAN-CS-79-773, 1979; *The American Statistician* 37(3), 1983), unverified at both", without choosing between the two. A non-primary pointer: the abstract of arXiv 2410.21922 calls its update "algebraically equivalent to the pairwise formula of Chan, Golub, and LeVeque (1983)"; it does not show what the 1983 paper contains. For the paper, the merge formula can be written out in one line, so that nothing rests on the citation.

**Draft 4's lines 262–265** ("have read no page yet", all ten keys) are now false for mcnemar1947, diebold1995 (working paper), patton2009, neweywest1987 (working paper) and brown1975, and still true for wilson1927, harvey1997, politis1994, page1954 and chan1983.

## Part B: the sources revised since they were read (arXiv abstract pages, fetch-summ.)

| Key | History | Newer than the version read? |
|---|---|---|
| gouletcoulombe2025ols | v1 2025-04-13, v2 2026-01-09, v3 2026-10-05; comments "Accepted at NeurIPS 2026" | No: v3, read, is the latest. Add the NeurIPS note. |
| vonoswald2025mesanet | v1 2025-06-05, **v2 2026-06-03**; "Published at ICLR 2026" | Yes |
| guo2025loglinear | v1 2025-06-05, v2 2025-06-25, **v3 2026-03-01**; header "ICLR 2026" | Yes |

**MesaNet v2** (PDF-verbatim, pp. 1–6; p. 7 not read).
- The equation numbers moved. In v2: Eq. (4) the cumulative ridge objective; Eqs. (5)–(6) the closed form; Eq. (7) the readout by linsolve (the conjugate-gradient text follows Eq. (8)); Eq. (8) the recurrences G_t, H_t with gates γ_t and β_t; Eq. (10) a decomposition.
- Draft 4's "(4), (6), (8)" (line 242) becomes "(4), (7), (8)"; "(4), (6)" (line 912) becomes "(4), (8)".
- The statements of lines 243–245 and 897–898 hold. Table 1 on p. 6 lists Mesa's recurrence and its linsolve readout.

**Log-Linear Attention v3** (PDF-verbatim, pp. 1–8).
- §3.1, Fenwick tree partitioning, pp. 4–5, unchanged. Eq. (3) on p. 5 gives the output as a sum over buckets with a nonnegative coefficient.
- Bucket merging is in §3.2, pp. 5–6 ("buckets up to lssb(t) merge"). Line 245 cites §3.1 only: add §3.2.
- v3's Table 1 (p. 2) compares attention mechanisms; it is not a bucket table.
- No least-squares solve in pp. 1–8; the DeltaNet inverse on p. 3 is a triangular solve.
- Lines 245–248, 891 and 899–900 hold. v2 was not diffed against v3.

## The scout's list of edits

1. Lines 242 and 912 (MesaNet's equation numbers); line 245 (add §3.2).
2. Lines 262–265, the "read no page yet" sentence and its `\todo`.
3. The `%` comments and `refs.bib` entries per the tables: MesaNet v2, Log-Linear v3, the NeurIPS note, Newey–West's pages, Patton's comment.
4. Lines 823 (Harvey) and 870 (Chan): drop the citation or soften the sentence.
5. `docs/DESIGN.md:93`.

No bolder idea.
