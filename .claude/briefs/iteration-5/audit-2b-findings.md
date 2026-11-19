# Audit phase 2b — the paper, claim by claim (iteration 5)

- **Agent:** `leakage-auditor` (fable), 2026-11-19. Read-only. Written by the auditor.
- **Object:** `paper/main.tex` (1,240 lines, draft 3, uncommitted), `paper/numbers.tex`, `paper/make_numbers.py`, `paper/refs.bib`; the five rows of 2026-11-19 in `docs/RESULTS.md`; the corrected OptMem sentence of `docs/DESIGN.md`. Line numbers are those of `main.tex` in the working tree.
- **Verdict: GO with fixes.** No Blocker; 2 Major, 11 Minor, 21 Nits.
  - **No number is wrong.** `numbers.tex` regenerates byte for byte, every macro the paper uses agrees with its source, and the five `RESULTS.md` rows agree with audit 2a's tables and the runs' JSON.
  - **No sentence of the body breaks the "Never claim" list.** The title does (Minor 11).
  - **The two Majors are framing.** Both make future invariance look better than the records allow, and both are fixed by text and a few macros, with no new contact.
- **Scripts:** `.claude/briefs/iteration-5/audit-2b-scripts/` (B1 to B4, under "Commands").

## Major

1. **The abstract's first claim is contradicted by our own reading note, and by the paper's line 205** (l. 66–68; l. 108–113).
   - **The claim.** "In the works we read, we found no measurement of how many leaks they catch."
   - **The note.** `reading-papers.md` §1, Table 2: Fonseca counts the two-run detector's misses (18 of 33 leaks) and false alarms (0 of 20 clean), the tiling detector's (33 of 33, 0 of 20), with a cluster bootstrap and permutation tests. The paper's own l. 205 says "we make no comparison with its rates".
   - **The introduction is narrower but still too wide.** Its list of what we did not find includes "whether it ever flags a function that does not read the future" (l. 109–110): Table 2 has that column.
   - **What the paper itself allows.** Only FI, TRUNC-0, TWO-RUN and SHUFFLE share H1's cuts; TRUNC-1 and RETILE run at other dates (l. 385). So the replacements below say "truncation and perturbation" and leave re-tiling out.
   - **What the notes do support.** Fonseca's corpus is small and clustered by mechanism (§9), 52 of its 53 pipelines are terms of the paper's own language, the two-run detector's perturbation law, epochs, run count and tolerance are not in the text read, and truncation is not among its detectors.
   - **Fix, l. 66–68.** Replace the first two sentences of the abstract by:

     ```latex
     Look-ahead detectors run a pipeline twice, with the data after a cut altered or removed, and flag
     any earlier output that moves. In the works we read, the one comparison of such detectors counts
     their misses on a small corpus built for that paper, and leaves the two-run detector's perturbation
     and run count unstated; we found none on a generated population of leaks over market bars, with
     truncation and perturbation held to the same cuts. We report a pre-registered one.
     ```
   - **Fix, l. 108–113.** Replace from "What we did not find" to the `\cite` and its comment by:

     ```latex
     What we did not find, in the works we read, is a \emph{measurement} of such detectors on a
     population large enough to speak of rates: how many leaks of a stated, generated population each
     one catches, with an interval, at cuts shared by the detectors it compares; how that count moves with the
     number of runs and with the way a missing value is read; and why it misses what it misses. The
     nearest is Fonseca's. It counts the misses and the false alarms of a static checker, a two-run
     detector and a tiling detector on a small corpus of pipelines, most of them terms of the paper's
     own language; the text we read gives the two-run detector no perturbation law, no rule for the
     epochs and no number of runs; and it states that such a corpus shows that leak types exist, not
     how often they occur~\cite{fonseca2026}. % sections 8.2-8.3 (detectors), 8 (corpus, Table 2), 9 (threats to validity), read
     ```
2. **The two-run rival is shown at our primary noise scale only, and the registered secondary arm, which closes most of the gap, is nowhere in the paper** (abstract l. 74; l. 134; `tab:shares` l. 603; l. 611–612; `tab:pairs` l. 728 and 738).
   - **What the paper prints.** "A two-run detector with random noise, 85.60 %", then FI minus TWO-RUN +12.97 points [+12.32, +13.64], p < 10^-300.
   - **What the run also wrote, as registered** (§2.5 "secondary σ = 1.0", §4.8; `metrics.detectors[...]`.any_cut.all of the confirmatory `detectors.json`; `RESULTS.md` row 34 carries the 97.40):

     | TWO-RUN | 1 run | 2 runs | 8 runs |
     |---|---|---|---|
     | σ = 0.1 | 80.84 % [80.06, 81.60] | 85.60 % [84.90, 86.27] | 91.50 % [90.94, 92.03] |
     | σ = 1.0 | 96.58 % [96.21, 96.92] | 97.40 % [97.07, 97.69] | 98.45 % [98.19, 98.67] |

   - **The paired cells, computed in this audit from `verdicts.jsonl` with audit 2a's reader (B4; mine only, not registered, deciding nothing).** <a id="b4"></a>
     - Confirmatory, FI minus TWO-RUN (σ = 1.0, 2 runs): +1.17 points [+0.91, +1.45], b = 153, c = 36.
     - Confirmatory, FI ×3 alone minus TWO-RUN (σ = 1.0, 1 run): −3.00 points [−3.42, −2.60], b = 74, c = 374.
     - Confirmatory, FI ÷3 alone minus TWO-RUN (σ = 1.0, 1 run): −0.30 points [−0.70, +0.10], b = 195, c = 225.
     - Confirmatory, FI minus TWO-RUN (σ = 1.0, 8 runs): +0.12 points [−0.08, +0.32], b = 57, c = 45.
     - Descriptive, in the same order: +1.57 [+1.22, +1.94]; −3.43 [−3.96, −2.91]; −0.91 [−1.37, −0.45]; +1.01 [+0.68, +1.35].
   - **Why it matters.** At one run per cut, random log-normal noise at σ = 1.0 catches more leaks than FI's ×3 run and as many as its ÷3 run (more, on the descriptive population). FI's designed perturbation is ahead only as the pair of its two runs, by about 1 point. A reader of the abstract and of `tab:pairs` takes away a 13-point win for FI over "a two-run detector with random noise". That gap is a property of the σ we chose, and the paper's brief asks that no sentence read as a win for FI.
   - **The caveat that must travel with σ = 1.0** is already in the paper (l. 762–766): at that scale the median body of a perturbed bar is 0.95.
   - **Fix, `make_numbers.py`.** In `DETS`, add `"TWO-RUN s0.1 r1": "TrOne"`, `"TWO-RUN s0.1 r8": "TrEight"`, `"TWO-RUN s1 r1": "TrHiOne"`, `"TWO-RUN s1 r2": "TrHi"`, `"TWO-RUN s1 r8": "TrHiEight"`. For the three audit cells, read the three "Confirmatory" lines above by anchor from this file, as the kind "A" does for audit 2a: macros `BHiDiff`, `BHiLo`, `BHiHi`, `BHiB`, `BHiC`; `BHiUpDiff`, `BHiUpLo`, `BHiUpHi`; `BHiDownDiff`, `BHiDownLo`, `BHiDownHi`.
   - **Fix, abstract l. 72–74.** Replace "caught `\NumCFiAll\pct{} [\NumCFiAllLo, \NumCFiAllHi]`" by "caught `\NumCFiAll\pct{}` (`\NumConf\pct{}` interval `[\NumCFiAllLo, \NumCFiAllHi]`)", and the last item of the list by:

     ```latex
     a two-run detector with random noise, as we defined it, \NumCTrAll\pct{} at its primary noise scale
     and \NumCTrHiAll\pct{} at its secondary one.
     ```
   - **Fix, l. 134.** Replace "and `\TR{} \NumCTrAll\pct`;" by "and `\TR{} \NumCTrAll\pct{}` at its primary scale (`\NumCTrHiAll\pct{}` at its secondary one);".
   - **Fix, `tab:shares`, l. 603.** Keep the row, name it "(σ = 0.1, primary)", and add five rows of the same form with the stems `TrOne`, `TrEight`, `TrHiOne`, `TrHi`, `TrHiEight`, the scales `\NumSigmaLo`, `\NumSigmaLo`, `\NumSigmaHi`, `\NumSigmaHi`, `\NumSigmaHi` and the run counts `\NumTwoRunOne`, `\NumTwoRunMany`, `\NumTwoRunOne`, `\NumRunsTwo`, `\NumTwoRunMany`.
   - **Fix, l. 615, after "(`\cref{tab:shares}`)."** Add:

     ```latex
     \TR's share is a property of the scale we gave it. With the same \NumRunsTwo{} runs,
     $\sigma=\NumSigmaHi$ reaches \NumCTrHiAll\pct{} [\NumCTrHiAllLo, \NumCTrHiAllHi]: \FI{} minus that
     arm is \NumBHiDiff{} points [\NumBHiLo, \NumBHiHi] (audit). With one run each, random noise at
     that scale, \NumCTrHiOneAll\pct{} [\NumCTrHiOneAllLo, \NumCTrHiOneAllHi], is above \FI's
     $\times\NumFIup$ run alone (\FI{} $\times\NumFIup$ minus it: \NumBHiUpDiff{} [\NumBHiUpLo,
     \NumBHiUpHi]; audit) and not separated from its $\div\NumFIdown$ run alone (\NumBHiDownDiff{}
     [\NumBHiDownLo, \NumBHiDownHi]; audit). The gap between \FI{} and \TR{} in \cref{tab:pairs} is a
     gap with our primary arm, not with random perturbation as such. At $\sigma=\NumSigmaHi$ the
     perturbed bars are far from market bars (see the law of the two-run arm below).
     ```
   - **Fix, `tab:pairs`, below the rule.** Add the row "`\FI{} $-$ \TR{}` (σ = `\NumSigmaHi`, `\NumRunsTwo{}` runs; audit)" with `\NumBHiB`, `\NumBHiC`, `\NumBHiDiff{} [\NumBHiLo, \NumBHiHi]` and no p-value.

## Minor

1. **"The cancelled controls followed their prediction" hides that the prediction is, mostly, "flagged"** (l. 751–753; abstract l. 74 stays true).
   - **The record.** `reported.controls.flagged_at_h1_cuts` of the confirmatory `detectors.json`: FP1 and FP2-min are flagged under truncation in each convention, under FI and under SHUFFLE, and never under TWO-RUN; FP2-fmin is flagged by none. `PROTOCOL.md` §3.2 states these consequences "so that nobody reads them as detector failures", and §6 lets the paper state the controls' verdicts.
   - **Why it matters.** FP1 and FP2 are Fonseca's clean classes. A reader who meets "no detector flagged an honest twin" and "the controls followed their prediction" concludes that nothing without a leak was flagged. Truncation flags `w + (v − v)` wherever `v` goes missing.
   - **Fix.** Replace "The cancelled controls followed … flagged by none." by:

     ```latex
     The cancelled controls followed their code-level prediction at H1's cuts under every detector they
     run through (not \RT). That prediction is not ``never flagged'': a control is flagged where its
     future node is missing or undefined in one run and not in the other. So truncation flags FP1 and
     FP2-min under each convention, \FI{} and \SH{} flag them where a changed bar leaves the node
     undefined, and \TR{} flags none; the missing-aware FP2-fmin was flagged by none. These flags come
     from comparing a missing value, not from a future value that reaches the output, and they are in
     no rate; but ``no honest twin was flagged'' does not mean that no function free of a leak was.
     ```
2. **Items not run are missing from "Not run", and two sentences on the mutants are in a future that has passed** (l. 496–498; l. 1032–1033; l. 1143–1145). `RESULTS.md` row 37 lists more than H6 and H14, and it defers the 21-mutant tests.
   - **Fix, l. 496–498.** Replace "Five further mutants … will then be reported." by:

     ```latex
     Five further mutants, planted by pass 5b-bis in the code of the fixes, survive the tests. The tests
     that would kill them were not written in this iteration, so no kill count over all \NumMutLater{}
     is reported; audit phase 2a read the five lines at the frozen code, found them right, and checked
     all but one by behaviour on synthetic bars as well.
     ```
   - **Fix, l. 1143–1145.** Replace the item by:

     ```latex
     \item \textbf{Tests not written.} Five mutants planted by pass 5b-bis survive the detector tests,
       and the tests that would kill them were not written in this iteration. The frozen code is right
       on all five by the audits' reading; one of the five lines was checked by reading only.
     ```
   - **Fix, l. 1032–1033.** Replace the item by:

     ```latex
     \item[Not run.] H6 (a Brier-loss ablation) was built and audited once but never fitted, and neither
       were the other ablations of its branch or its seed-split control. H14 (a long/flat portfolio
       after costs) was registered and not run: no portfolio simulator exists. H13's timing stage was
       not rebuilt, so H13 was not measured again under a valid one; the two repeats above are
       descriptions. An extreme-shape cut promised for future invariance, and the first calls of a
       tool that explains one encoder head, were not run either. Two hypotheses registered at the
       start of the project were never run: H7 (news tokens) and H8 (return-to-go conditioning).
     ```
   - **Checked for the last sentence:** H7 and H8 have no row in `docs/RESULTS.md` and no mention in `docs/PROTOCOL.md` or `docs/ITERATIONS.md`; a search of `python/olsprime` and `crates` for "news" and "return-to-go" finds no file.
   - **Not for the paper:** audit 2a's own text says "three of the five mutants are now answered by behaviour", while its N6 and the dated line of `PROTOCOL.md` say four lines by behaviour and one by reading. The replacement above quotes no count.
3. **"Variants tried so far: 18" counts ten strategies of a report the paper never describes** (l. 885–886; captions l. 920–921 and l. 996). H9 and Report n°1 are in the results log that §8.1 says it reports "exactly"; H7 and H8 are in `docs/HYPOTHESES.md` and in no row (fixed in Minor 2).
   - **Fix, `make_numbers.py`.** Add to `SPEC`: `(("VariantsBefore", "RepTwoArms"), R_H2, r"\((\d+) before this iteration, plus the (\d+) arms of Report n°2\)", "num")`.
   - **Fix, l. 886, after "records it."** Add:

     ```latex
     That log also holds one earlier report that this paper does not describe: \NumVariantsBefore{}
     baseline strategies on daily bars under venue fees, with one hypothesis, H9, that no active
     baseline beats buy and hold after fees; it held. Those \NumVariantsBefore{} variants are in the
     counts of variants tried that the tables below give.
     ```
4. **The validation year is not "sealed in code"** (l. 170–172; l. 1146–1147). The seal cuts at the vault's start (`PROTOCOL.md`, Splits; audit 2a, N7), and the paper's own l. 1040 says the seal returned the bars of 2025.
   - **Fix, l. 170–172.** Replace "No result from the validation year or from the vault, both sealed (" by "No result from the validation year or from the vault: the vault is sealed in code, and every pipeline drops the validation year's bars before any feature, label or model (".
   - **Fix, l. 1146–1147.** Replace "The validation year (2025) and the vault (2026 onwards) are sealed in code, and the vault months were moved" by:

     ```latex
     The vault (2026 onwards) is sealed in code: the one loader of stored bars drops them. The
     validation year (2025) is not behind that seal: each pipeline loads its bars and drops them before
     any feature, label or model. The vault months were moved
     ```
5. **The paper never names the commit of its registration, nor says what was public before the runs** (§10, l. 1181–1189; §9).
   - **What git shows.** `docs/HYPOTHESES.md` got H15, and `docs/PROTOCOL.md` its iteration-5 section, in `6044037` (2026-11-18 22:13 +01:00). The local reflog of `origin/iteration-5` records "update by push" at 22:24:29 the same evening, and `git branch -vv` shows the branch 5 commits ahead of it: `6ab7e3e`, `b71ba65`, `f12b9b5`, `1088aac` and `d72f595` are local only.
   - **The order of that evening, in UTC.** The quantile table was computed at 20:32 (`PROTOCOL.md` §1.5), the registration was committed at 21:13 and pushed at 21:24. So the push follows the one contact with real bars that l. 487–490 already disclose, and precedes every run.
   - **Why it matters.** "Pre-registered" in a title is read as a third-party timestamp. Here the registration has one (a push to a public repository, if GitHub confirms the date), but the dated changes of 2026-11-19 and the frozen commit do not: their place before the runs rests on local commit times and on the commit each output records. A later push cannot backdate them; the paper can only say so.
   - **Fix, l. 1188, after "made at `\code{f12b9b5}`."** Add (the orchestrator checks the push date on GitHub first):

     ```latex
     The benchmark's registration is commit \code{6044037} of 2026-11-18, pushed to the project's public
     repository that evening, after the quantile table had been computed from the pre-2019 bars
     (\cref{sec:prereg}) and before any run of the benchmark. The commits that carry the dated changes
     of 2026-11-19 and the frozen code (\code{6ab7e3e}, \code{b71ba65}, \code{f12b9b5}) were made before
     the runs but had not been pushed when this draft was audited: that they precede the runs rests on
     our own commit times and on the commit that each output records.
     ```
   - **Fix, §9.** Add the item:

     ```latex
     \item \textbf{The registration.} It is a dated text in our own repository, not an entry in a
       third-party registry; \cref{sec:repro} says which of its commits were public before the runs.
     ```
6. **A registered descriptive count is missing: the 10,000 draws are 8,434 distinct expressions** (`PROTOCOL.md` §4.12; `metrics.descriptive.distinct_expressions`, 8,533 in the descriptive run). The macros exist and are unused.
   - **Fix, l. 579, after "decides nothing."** Add:

     ```latex
     The \NumPopN{} draws of the confirmatory population hold \NumCDistinct{} distinct expressions
     (\NumDDistinct{} in the descriptive one), and \NumCConstH{} of the draws are constant at the
     compared rows of H1's cuts (\NumCConstBoth{} on both schedules). Every share is over draws, so an
     expression drawn twice counts twice.
     ```
7. **The regression cubes are said to aggregate "through sums of their measures, along time as along the other dimensions"** (l. 246–248). The note records two different rules (`reading-papers.md` §5: Theorem 4.4 along time, the Θ add and the coefficients combine weighted by them; Theorem 4.3 along the other dimensions, the coefficients add and Θ is unchanged), and a measure that is (η̂, Θ), not a pair of sums.
   - **Fix, l. 246–248.** Replace the sentence's predicate by:

     ```latex
     compress the regression of a data-cube cell into a measure whose size does not depend on the number
     of tuples, and aggregate cells losslessly from those measures alone, over a lattice of stored
     cells: along the time dimension the cells' $\Theta$ matrices add and their coefficients combine
     weighted by them, and along the other dimensions the coefficients add.
     ```
   - **Fix, l. 876.** "The additive merge of regression statistics" becomes "The lossless merge of compressed regression measures".
8. **Three bibliography entries print fields that `reading-methods.md` marks UNCONFIRMED** (`refs.bib`).
   - **`optmem`, l. 313–318.** The printed author is "Taelin (UNCONFIRMED)", and BibTeX warns of an empty year. Replace the two fields by `author = {{VictorTaelin (GitHub account)}}`, which is the account in the URL the scout read, and `year = {n.d.}`.
   - **`chen2006regcube`, l. 120 and 122.** The pages 1585–1598 and the DOI come from a search summary, and one record gives 1599. Remove `pages` and `doi` until a scout reads them at IEEE or Crossref.
   - **`neweywest1987`, l. 256.** The end page 708 comes from a search snippet. Confirm it at Crossref or JSTOR, or remove `pages`.
9. **"Every source below was read in part" is false for ten method papers** (l. 181; l. 256–257; l. 1171–1172). Their `%` comments say "metadata only", and `reading-methods.md` says such an entry "does not yet meet the rule's abstract-or-first-page check" of `paper.md`.
   - **Fix, l. 181.** "Every source below was read in part" becomes "Every source of this section, except the method papers of its last paragraph, was read in part".
   - **Fix, l. 256–257.** Replace the paragraph by:

     ```latex
     \paragraph{Methods.} The statistical and numerical methods we use are cited where they are first
     used, for their definitions only. For ten of them we checked the bibliographic record alone and
     have read no page yet~\cite{wilson1927,mcnemar1947,diebold1995,harvey1997,politis1994,patton2009,
     neweywest1987,page1954,brown1975,chan1983}. % metadata only, each of the ten (reading-methods.md, Part A)
     \todo{Read the abstract or first page of each before
     submission, as the citation rule asks.}
     ```
   - **Fix, l. 1171–1172.** Replace the item by:

     ```latex
     \item \textbf{The reading.} No source was read in full: most were read in part through a
       summarising fetch tool, and ten method papers are cited from their bibliographic record alone
       (\cref{sec:related}).
     ```
10. **Contribution 1 promises "a classification of misses, for six detectors and their union"** (l. 152–155). Section 5 classifies the union's 46 misses only; for each detector it gives a count of misses among the union's catches.
    - **Fix, l. 152–153.** Replace "Catch rates with Wilson intervals, honest-twin false positives and a classification of misses, for six detectors and their union on the same fresh population," by "Catch rates with Wilson intervals and honest-twin false positives for six detectors and their union on the same fresh population, what each detector misses among the union's catches, and a classification of the union's own misses,".
11. **The working title says "OLS attention"** (l. 52–53), against the first item of the "Never claim" list. The body avoids the phrase everywhere ("an encoder whose token weights come from an OLS fit").
    - **Fix.** Take the alternative title that the draft carries in its comment, l. 56–58.

## Nits

- **N1. "The first and only draw … These three seeds are spent", beside the rerun** (l. 534–537). The identity rerun drew them a second time, as registered. Replace "the first and only draw of seed `\NumConfSeed{}` … with another number of workers." by "the first draw of seed `\NumConfSeed{}` and of the `\TR{}` and bootstrap seeds `\NumTwoRunSeed{}` and `\NumBootSeed`; and the registered identity rerun of it with another number of workers, their only other draw."
- **N2. "About 9.3 % of leaks have no … control" is the share of a synthetic draw** (l. 410–411; `PROTOCOL.md` §3.2). The confirmatory run built 27,150 controls, three for each of 9,050 leaks. Replace the sentence by "Leaks with no future node of the required kind get no control (about `\NumNoControlShare\pct{}` of a synthetic draw; the confirmatory run built `\NumCControlsBuilt{}` controls, three per leak that has one)." Macro: `J(f"{_r}ControlsBuilt", _run, ("reported", "controls", "built"), "int")`.
- **N3. "McNemar's exact p-value" cites the 1947 note, known by its metadata only** (l. 433). Replace by "and the two-sided `$p$`-value of McNemar's test`~\cite{mcnemar1947}`, computed exactly from the binomial law of the discordant counts;", with the comment "metadata only; cited for the test of correlated proportions, as its title names it; the exact computation is ours". The caption of `tab:pairs` (l. 718–719) repeats the phrase: write "and the exact two-sided `$p$`-value of McNemar's test`~\cite{mcnemar1947}`" there.
- **N3b. Three `\cite` in captions have no `%` comment** (l. 583, l. 718, l. 719); every other one has its comment on its line or the next. End each of the three lines with a space and "% the method's definition only; read level as at l. 424" (l. 432 and l. 433 for the other two). Keep the space before the `%`, or the two lines join without one.
- **N4. The citation of Log-Linear Attention carries a remark that is ours** (l. 855–857). Replace "splits the same way, Log-Linear Attention's mixture of bucket readouts included`~\cite{guo2025loglinear}`." by "splits the same way; by our reading of its output formula, not by a statement of its authors, so does Log-Linear Attention's mixture of bucket readouts`~\cite{guo2025loglinear}`."
- **N5. "(audit)" is defined as "from `verdicts.jsonl`" (l. 577–579) and used three times for something else:** the drift check against earlier outputs (l. 771), the chance count of the yearly split (l. 1061), and, after Major 2, this audit's cells. Replace the definition by "A number marked ``(audit)'' was computed in an audit pass, from the per-leak file `\code{verdicts.jsonl}` by a reader independent of our package or, where said, from other stored outputs; it is not registered and decides nothing." At l. 771, write "(audit; a check of drift against those runs' outputs, not an independent implementation)".
- **N6. `\NumTwoRunOne` serves as FI's run count per direction** (l. 596–597): the right value from the wrong line. Add `J(f"{_r}RunsFiDir", _run, ("metrics", "detectors", "FI x3", "runs_per_cut"), "int")` and use `\NumCRunsFiDir`.
- **N7. Counts written as words.** "Five" mutants (l. 496, l. 1143) and "two tests" (l. 1148) are counts of the record with no macro; the protocol says "the auditor's evasion tests" for "the holes D1 and D2". At l. 1148, write "tests written to prove two holes in the code seal". Leave "Five" as a word: the protocol's line writes it so, and the macros beside it (16 killed, 21 in all) carry the count.
- **N8. "Half of that generator's thresholds"** (l. 298) is true of the banded quantities only, as l. 319 says. Write "Half of that generator's thresholds on body, wicks, range, fill and close location".
- **N9. "Before any detector ran on real bars"** (l. 412, l. 507–508). FI and the twins ran on real bars in iterations 3 and 4, as §3.2 reports. Write "before the benchmark's code ran on real bars".
- **N10. The vault's `\todo`** (l. 1153–1156). Both of the writer's points can be settled from the records.
  - **The date.** The paper is right and `paper.md` is wrong: the exposure is of 2026-10-28, in Audit A of iteration 2 (`PROTOCOL.md:719`, `ITERATIONS.md:200`). `paper.md` l. 20 and `ITERATIONS.md:601` say "iteration 1".
  - **The range.** "2026 onwards" is what the seal does. Replace the `\todo` by "The seal drops every bar from 2026-01-01 on; the protocol's vault period runs to October 2026, and the bars on disk when the months were moved ran to September 2026."
- **N11. "While `\FI`'s perturbed bars move it"** (l. 651): FI catches 682 of the 818. Write "can move it".
- **N12. The draft's own labels.** L. 1 says "first draft" and l. 60 "Draft 2"; `refs.bib` says draft 3. Write "% main.tex -- OLS Prime paper, draft 3 (2026-11-19)." at l. 1 and `\date{Draft 3, 2026-11-19}` at l. 60, or the number of the draft that carries these fixes.
- **N13. `tab:h15`, last row** (l. 691): "labels unchanged" is the audit's too. Write "percentiles; range `\NumCBootMin{}` to `\NumCBootMax{}` and labels unchanged (audit)".
- **N14. "(audit)" after two pairs** (l. 776–778) covers the second only; the ×3 pair is the run's. Write "(the second: audit)".
- **N15. The R package** (l. 520–522). Leaving `fagerland2013` uncited is right: by its title it is a paper on McNemar tests, not on the package or on method 10. Name the function, as the protocol does: "`\code{Newcombe\_square\_and\_add\_CI\_paired\_2x2}` of the R package `\code{contingencytables}`".
- **N16. `chan1983` against `docs/DESIGN.md`,** which names the 1979 report. Keep `chan1983` in the paper, since it is the entry the scout checked. In `docs/DESIGN.md:93`, write "Chan, Golub and LeVeque (1983; first a 1979 report)" once a scout has confirmed that the 1983 paper gives the pairwise update; until then the citation rests on the title alone, as Minor 9 says of all ten.
- **N17. `docs/RESULTS.md`, rows 33 to 35, "Variants tried so far: 0".** The header says "up to that point" and `PROTOCOL.md` §8 says the count "stays at 21"; rows 22 and 25 wrote 18 for bench rows, rows 13 and 14 wrote 0. The rows are uncommitted: write "21 (unchanged: no strategy variant; the detectors and leaks are tests)" before the commit.
- **N18. `docs/DESIGN.md`.** The OptMem correction agrees with the README notes. Its dated line of 2026-10-28 was edited in place, with "(corrected 2026-11-19)", where the other documents add a dated line; and §3 still calls Matrix's summaries "exact", a word the paper may not use.
- **N19. No figure.** `paper.md` names `paper/figures/`; the draft has nine tables and no figure, and nothing in "Must contain" asks for one.
- **N20. The `\todo` left for Abdou or the orchestrator,** none of them a finding: the title (l. 54), the author (l. 59, l. 1222), the category, licence and endorser (l. 89–92), the verbatim re-read of each cited passage (l. 184), the repository URL (l. 1177), the paper's licence (l. 1232–1233), the corpus release (l. 1235).

## The six steps of the brief

### 1. Every number

- **Regeneration.** `make_numbers.py`, unmodified, run with `python -B` in a scratch mirror that holds copies of its nine inputs only, writes 1,103 macros; the file equals `paper/numbers.tex` byte for byte (SHA-256 `22a48214…2469b`). The brief's command as written would overwrite `paper/numbers.tex`, which is why it ran on a mirror.
- **Macros used: 748 distinct; undefined: 0; defined and unused: 355** (B1).
- **Digits typed by hand.** 151 lines of the body hold one (B1's `digits.txt`). I read each: hypothesis and class names, dates and years of periods, `t+1`, the 0 and the 2×2 of a rule, section and clause numbers, product names. None is a measured quantity. The counts written as words are N7.
- **Macros against their sources: 748 checked, 748 agree** (B2). The check has three strengths:

  | Check | Macros | Agree |
  |---|---|---|
  | against the value audit 2a recomputed from `verdicts.jsonl` (the "mine" column), with the unit decided from the key's name | 265 | 265 |
  | read again from `detectors.json` or `casestudy.json` by B2's own walk and format (values the per-leak file cannot give) | 82 | 82 |
  | against the audit's "mine only" rows | 5 | 5 |
  | the cited line holds the matched fragment, and the fragment the raw value | 396 | 396 |

  - **The brief's sample.** The abstract, §5 and §8.4 use 414 distinct macros: 352 are in the first three rows of the table, 62 in the last.
  - **The last row shows that the source exists, not that the sentence means it.** For that, I read the rendered text (B1's `rendered.txt`, each macro replaced by its value) against the `RESULTS.md` rows, the registered text and audit 2a's tables: the abstract, l. 132–148, §3.1 to §3.4, §4, §5 whole, §6, §8 whole, the vault item and §10. Every value sits beside the right label, sign and unit. The differences `_newcombe` multiplies by 100 and H15's top-level points are both right (−3.35, −1.08, +1.43, −3.75).
  - **The bare keys.** `metrics.detectors["TWO-RUN"]` and `["SHUFFLE"]` are the registered arms (85.60 and 98.47, equal to `TWO-RUN s0.1 r2` and `SHUFFLE k8`), unlike the raw key of `reported.classes` that Minor 4 of audit 2a was about.
- **The five rows of `docs/RESULTS.md`.** `git diff HEAD` adds five lines and removes none. I read every number of rows 33 to 36 against audit 2a's tables and `casestudy.json`: all agree, signs included where a pair is reversed (+1.24 [+0.82, +1.67] and −1.46 [−1.92, −1.00] are the run's and the audit's pairs with the order swapped). B3 finds each of the 422 numbers of the five rows in the tables, the JSON or the dated lines; that screen is weak for two-decimal numbers and adds little to the reading. One Nit (N17).

### 2. Every claim

- **"Never claim", sentence by sentence.**
  - *OLS is attention:* the title only (Minor 11).
  - *Signed weights:* absent; "the weights can be negative" is said of two cited works.
  - *An exact ridge state:* absent. §7 says "a direct solve … in floating point", with the refusal bound "not proved".
  - *The idea of a two-run test:* disclaimed at l. 120–122 and l. 173.
  - *OLS beats softmax:* H4 is worded as non-inferiority with "we claim none"; H3's passing comparison carries "says nothing about softmax attention in general".
  - *Any profit:* none; H14 is "not run".
  - *The vault or the validation year:* no result. The wording of the seal is Minor 4.
- **The wording audit 2a requires.** All present: the cell named in the abstract, l. 135–137 and l. 625–626; ×3 and ÷3 beside it, the second marked as the audit's; the not-constant interval; P's reversal; "date-dependent" with the labels unchanged in 2,000 of 2,000 subsets; Minor 4's "any of 16 runs … not the registered arm's" (l. 758–760); Minor 5's three points, each under "exploratory, test months" (l. 1044–1061, l. 1086–1099, both captions, the table headers); N1 (l. 546–549), N2 (l. 713 and the tables), N3 (l. 622–623), N5 (l. 755–757), N7 (l. 1039–1041, l. 1159), N8 (the label is written by hand at each use).
- **Each "(audit)" number is marked.** The macros read from audit 2a's text or tables are used at l. 141, 147, 633, 640–641, 644–645, 647, 649–650, 660–664, 683, 685, 689–691, 776–778 and 1058–1061, each with "(audit)" or "computed in the audit". The scope of the word is N5.
- **Against the registered text.** H15's rule (l. 444–460) is `docs/HYPOTHESES.md`'s; the "may and may not" list (l. 558–568) is `PROTOCOL.md` §6; the changes after registration (l. 507–528) are the dated line of 2026-11-19; the audit tallies, the suite and the digests are the change log's.
- **Checked in the JSON because no table of audit 2a holds them:** "FP2-fmin was flagged by none" (`reported.controls.flagged_at_h1_cuts`, six zeros); "M3 was never flagged" (the assertion's `by_class.M3` is 0 against the registered "never"); the taker caps (0 and 0 of 11,520); the median body 0.95 at σ = 1.0.

### 3. Every citation

- **25 keys cited, 25 defined, none unused.** Each `\cite` has a `%` comment naming a part, except three repeats in captions (N3b), and each part is one its note records as read or, for ten method papers, as "metadata only" (Minor 9).
- **Statements beyond the note:** the regression cubes (Minor 7), the abstract and introduction on Fonseca (Major 1), the exact McNemar test (N3), the additivity remark (N4). The others stay inside their notes: Fonseca's detectors, classes and §9; freqtrade's slices and exact comparison, where "every kept indicator row" rests on the verbatim read of `PROTOCOL.md` §0.4; Causify's Remark 4.25; Goulet Coulombe's Eq. (7), ridge form and Appendix A.4; the dual decomposition; Garnelo and Czarnecki; MesaNet's Eqs. (4), (6), (8); Log-Linear Attention's §3.1; Nagel's §II; the dataset terms' clauses 3, 4.1, 4.5 and 8.
- **UNCONFIRMED fields in print:** Minor 8.

### 4. "Must contain"

- **The AI use:** §11, with "AI tools are not authors" and the author's responsibility. Present.
- **The data credit and the licence, as pending:** §12 and the open decisions of l. 88–92. Present.
- **Reproducibility:** the commits, the run folders, the rerun identity, the three code digests. Present, except the registration commit (Minor 5).
- **The vault's exposure:** stated in §9 and announced at l. 171. Present.
- **Every item not run:** incomplete (Minor 2).

### 5. The framing

- **Reads as a win for FI:** the two-run arm (Major 2), the controls (Minor 1). Elsewhere the draft holds its line: "not a win for `\FI`" (l. 148), the label "of one cell", the constant leaks named as the seat of the gap, the generator's ties to FI in §3.3 and §9.
- **Novelty not narrowed:** Major 1 and Minor 10. Matrix is worded as an absence in the parts read, with the three prior arts named and "we claim no more" (l. 861–879).

### 6. It compiles

- MiKTeX 25.12, in a scratch copy: `pdflatex` (exit 0), `bibtex` (exit 0), `pdflatex` twice (exit 0). 22 pages.
- **Undefined references: 0. Undefined citations: 0. LaTeX warnings: 0.** One BibTeX warning, "empty year in optmem" (Minor 8). One overfull box of 0.16 pt (l. 318–332).
- I looked at pages 10 and 11 (`tab:shares`, `tab:h15`): they fit the page.

## The points the writer flagged

- **The vault's exposure:** the paper is right to follow `PROTOCOL.md`; `paper.md` and `ITERATIONS.md:601` are wrong (N10).
- **The vault's range:** "2026 onwards" is right for the seal; N10 gives the sentence that replaces the `\todo`.
- **`fagerland2013` not cited:** right (N15).
- **Numbers from audit 2a's own outputs:** each is marked (step 2); the word's definition needs widening (N5).
- **The OptMem entry:** Minor 8.

## Clean: checked and found right, so nobody re-checks it blindly

- **Look-ahead in what the paper describes.** The catch rule, the compared rows, the stop rule, "entering at the next open", "an entry joins Matrix only when its outcome is known", the fold-internal fits: each is the registered text. The paper adds no result that an earlier audit did not see.
- **Leakage across populations.** Every number is labelled confirmatory or descriptive; §3.2, the last column of `tab:shares`, the replication sentence and the last paragraph of §5 are the descriptive ones, and each `D` macro reads the descriptive file.
- **Survivorship, as stated:** "delisted pairs stay in the history" is `PROTOCOL.md`'s and `DATA.md`'s.
- **Statistics, as stated.** Every share has its Wilson interval, every paired difference Newcombe's; the cut-date bootstrap is called a spread, never an interval; the yearly split is called unadjusted with its chance count; "variants tried" is in both report captions (its content is Minor 3); no Sharpe ratio and no cost appears.
- **§6, the power study:** every number is the row of 2026-10-30; "we had set as the alarm" and "lower bounds" are `PROTOCOL.md:400` and `:404`; the failed second run is said.
- **§7, Matrix:** the two partial blocks, the pairwise merge, the refusal bound "derived to first order … not proved" are `docs/DESIGN.md` §3 to §3.2.
- **§8.1 to §8.3:** H2, H3, H10 to H12, H4, H5 and H13 as their rows record them, the previewed months apart, the three verdicts of the encoder's H1 apart, H13 with no verdict. The limit on the first seed (l. 1161–1163) is `PROTOCOL.md:304`.
- **§10:** each commit and run folder is the one its row names; the `--check` file counts are the rows'.
- **The dated line "after audit phase 2a" of `PROTOCOL.md`** agrees with audit 2a's findings, tally by tally.

## Not checked

- **The cited passages themselves.** I read the notes, not the sources: no download. The draft's own `\todo` (l. 184) keeps the verbatim re-read open.
- **The push date of `6044037` on GitHub** (Minor 5): I read the local reflog only.
- **`uv run pytest`, `cargo test`, clippy, Kani:** not run. `git diff HEAD --stat` touches nothing under `python/` or `crates/`, and the brief forbids any run that reads real bars.
- **`docs/ITERATIONS.md`, `resume-5.md`, `paper-draft-1.md`:** not audited beyond the lines quoted here.
- **The 355 unused macros:** regenerated with the others, not read against their sources.
- **The PDF beyond pages 10 and 11,** and the bibliography's rendering beyond the three entries of Minor 8.
- **The bootstrap intervals and HAC errors of the case study:** as in audit 2a, read and not recomputed.

## Contacts

- **Real bars: none.** No read of `data/`, no `load_klines`, no registered command line.
- **Seeds 20261118 and 20261119: not drawn.** B4 executes audit 2a's A1 whole on both detector folders, and A1 reads seed 20261120 (29120 for the descriptive run) from each file's header to reproduce the cut-date bootstrap on the stored verdicts: the same stream on the same flags, no bar. B4 itself draws nothing.
- **The vault and the validation year: not opened.** Nothing under `runs/vault/` was listed, opened or hashed. `make_numbers.py` and B2 refuse any path that holds "vault".
- **`runs/`, read only, by explicit path:** `detectors.json` of the confirmatory and descriptive runs and `casestudy.json` (as `make_numbers.py` reads them); for B4, `verdicts.jsonl` and `detectors.json` of both detector runs, through audit 2a's reader, on stored verdicts.
- **Written:** this file; `audit-2b-scripts/` (four scripts); scratch files in the session's scratchpad (the mirror, the build, the tables of B1, B2 and B4). Nothing under `paper/`, `docs/`, `python/` or `crates/`. `git status` shows the same modified files before and after, plus `audit-2b-scripts/` and this file.
- **Git:** `status`, `diff HEAD`, `log`, `branch -a -vv`, `reflog show`. No command that rewrites the tree or the index.
- **Network: none.**

## Commands

All from `C:\Users\abdou\ols-prime\python`, with `uv run --no-sync python -B` and `PYTHONUTF8=1`.

- **The mirror:** `cp` of `paper/make_numbers.py`, `docs/RESULTS.md`, `docs/HYPOTHESES.md`, `docs/PROTOCOL.md`, `audit-2a-findings.md`, the two `table-*.tsv` and the three JSON files into the same relative paths under the scratchpad; `python -B <mirror>/paper/make_numbers.py`; `cmp` and `sha256sum` against `paper/numbers.tex`.
- **B1,** `b1_macros_and_digits.py <main.tex> <numbers.tex> <out-dir>`: macros used and defined, the hand-typed digits, the rendered text.
- **B2,** `b2_check_macros.py <repo root> <used-macros.tsv> <out.tsv>`: the 748 macros against their sources.
- **B3,** `b3_results_rows.py <repo root>`: the numbers of the five rows.
- **B4,** `b4_two_run_secondary.py <run folder> <scratch.tsv>`: TWO-RUN's six variants and the pairs of Major 2, from stored verdicts.
- **The build:** `pdflatex -interaction=nonstopmode --disable-installer main.tex`, `bibtex main`, `pdflatex` twice, in a scratch copy of the three files.

## Bolder check

One, already made, because it changes what the abstract may say: **B4, the secondary two-run arm paired with FI at equal run counts** (Major 2). It needed no bar; it replays one stored seed through audit 2a's reader, as that audit did (see Contacts). I propose nothing that needs a new contact.
