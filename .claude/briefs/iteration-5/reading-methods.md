# Reading — the method papers and the bibliography's gaps (scout, 2026-11-19)

- **Rule.** `paper.md`, "Method citations", 2026-11-19. Saved by the orchestrator from the scout's report.
- **How the metadata was checked.** It comes from Crossref (the DOI registry API), arXiv abstract pages or the publisher.
  - Crossref returns metadata only.
  - "Read" means the abstract or first page was read.
  - "Metadata only" means it was not, so that entry does not yet meet the rule's abstract-or-first-page check. It may be cited for the method's definition. A claim beyond the title waits for a read.
  - No field was filled from memory. UNCONFIRMED marks a field not seen at a primary page.

## Part A: method papers

| Key | Read level | Note |
|---|---|---|
| wilson1927 | Metadata only (Crossref) | Score interval |
| newcombe1998paired | **Read:** Summary and Table I (PDF pp. 1–2) | Method 10 is the paired score-based method: cite this one, not the independent-proportions paper of Stat Med 17(8):873–890 |
| mcnemar1947 | Metadata only; given name from Crossref | |
| fagerland2013 | Metadata only; issue 1, 2013-07-13 | The title states the conclusion |
| diebold1995 | Metadata only | |
| harvey1997 | Metadata only | The title does not say "small-sample correction": cite it for that only after a read |
| politis1994 | Metadata only | |
| politiswhite2004 | **Read:** abstract (IDEAS) | Flat-top lag-window block-length estimators |
| patton2009 | Metadata only | Corrects 2004's algorithm: cite both |
| neweywest1987 | Metadata only | End page 708 UNCONFIRMED (search snippet) |
| page1954 | Metadata only; given name UNCONFIRMED | |
| brown1975 | Metadata only | The title is "Techniques for Testing the Constancy of Regression Relationships over Time" |
| chan1983 | Metadata only | Crossref spells "Leveque" |
| katharopoulos2020 | **Read:** abstracts (PMLR, arXiv) | Self-attention as a linear dot product of kernel feature maps |
| optmem | **Read:** the README | See below |

```bibtex
@article{wilson1927,
  author={Wilson, Edwin B.}, title={Probable Inference, the Law of Succession, and Statistical Inference},
  journal={Journal of the American Statistical Association}, year={1927}, volume={22}, number={158},
  pages={209--212}, doi={10.1080/01621459.1927.10502953}}
@article{newcombe1998paired,
  author={Newcombe, Robert G.}, title={Improved confidence intervals for the difference between binomial proportions based on paired data},
  journal={Statistics in Medicine}, year={1998}, volume={17}, number={22}, pages={2635--2650},
  doi={10.1002/(SICI)1097-0258(19981130)17:22<2635::AID-SIM954>3.0.CO;2-C}}
@article{mcnemar1947,
  author={McNemar, Quinn}, title={Note on the Sampling Error of the Difference Between Correlated Proportions or Percentages},
  journal={Psychometrika}, year={1947}, volume={12}, number={2}, pages={153--157}, doi={10.1007/BF02295996}}
@article{fagerland2013,
  author={Fagerland, Morten W. and Lydersen, Stian and Laake, Petter},
  title={The {McNemar} test for binary matched-pairs data: mid-p and asymptotic are better than exact conditional},
  journal={BMC Medical Research Methodology}, year={2013}, volume={13}, pages={91}, doi={10.1186/1471-2288-13-91}}
@article{diebold1995,
  author={Diebold, Francis X. and Mariano, Roberto S.}, title={Comparing Predictive Accuracy},
  journal={Journal of Business \& Economic Statistics}, year={1995}, volume={13}, number={3}, pages={253--263},
  doi={10.1080/07350015.1995.10524599}}
@article{harvey1997,
  author={Harvey, David and Leybourne, Stephen and Newbold, Paul}, title={Testing the equality of prediction mean squared errors},
  journal={International Journal of Forecasting}, year={1997}, volume={13}, number={2}, pages={281--291},
  doi={10.1016/S0169-2070(96)00719-4}}
@article{politis1994,
  author={Politis, Dimitris N. and Romano, Joseph P.}, title={The Stationary Bootstrap},
  journal={Journal of the American Statistical Association}, year={1994}, volume={89}, number={428}, pages={1303--1313},
  doi={10.1080/01621459.1994.10476870}}
@article{politiswhite2004,
  author={Politis, Dimitris N. and White, Halbert}, title={Automatic Block-Length Selection for the Dependent Bootstrap},
  journal={Econometric Reviews}, year={2004}, volume={23}, number={1}, pages={53--70}, doi={10.1081/ETC-120028836}}
@article{patton2009,
  author={Patton, Andrew and Politis, Dimitris N. and White, Halbert}, title={Correction to ``Automatic Block-Length Selection for the Dependent Bootstrap'' by {D. Politis} and {H. White}},
  journal={Econometric Reviews}, year={2009}, volume={28}, number={4}, pages={372--375}, doi={10.1080/07474930802459016}}
@article{neweywest1987,
  author={Newey, Whitney K. and West, Kenneth D.}, title={A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix},
  journal={Econometrica}, year={1987}, volume={55}, number={3}, pages={703--708}, doi={10.2307/1913610}}
@article{page1954,
  author={Page, E. S.}, title={Continuous Inspection Schemes}, journal={Biometrika}, year={1954},
  volume={41}, number={1--2}, pages={100--115}, doi={10.1093/biomet/41.1-2.100}}
@article{brown1975,
  author={Brown, R. L. and Durbin, J. and Evans, J. M.}, title={Techniques for Testing the Constancy of Regression Relationships over Time},
  journal={Journal of the Royal Statistical Society: Series B (Methodological)}, year={1975}, volume={37}, number={2}, pages={149--163},
  doi={10.1111/j.2517-6161.1975.tb01532.x}}
@article{chan1983,
  author={Chan, Tony F. and Golub, Gene H. and LeVeque, Randall J.}, title={Algorithms for Computing the Sample Variance: Analysis and Recommendations},
  journal={The American Statistician}, year={1983}, volume={37}, number={3}, pages={242--247}, doi={10.1080/00031305.1983.10483115}}
@inproceedings{katharopoulos2020,
  author={Katharopoulos, Angelos and Vyas, Apoorv and Pappas, Nikolaos and Fleuret, Fran{\c{c}}ois},
  title={Transformers are {RNN}s: Fast Autoregressive Transformers with Linear Attention},
  booktitle={Proceedings of the 37th International Conference on Machine Learning}, series={Proceedings of Machine Learning Research},
  volume={119}, pages={5156--5165}, editor={Daum{\'e} III, Hal and Singh, Aarti}, year={2020}, eprint={2006.16236}, archivePrefix={arXiv}}
@misc{optmem,
  author={{Taelin (UNCONFIRMED)}}, title={{OptMem}: Permanent memory for AI agents}, howpublished={\url{https://github.com/VictorTaelin/OptMem}}, note={Accessed 2026-11-19; no release, no date, license not seen}}
```

## OptMem: a repository, not a paper

- **No paper was found.** The source is the GitHub repository `VictorTaelin/OptMem`: 42 commits, no release, no date seen. Its license was not checked. The author's name comes from the repository path and a secondary news article, so it is UNCONFIRMED.
- **The README confirms the structure:**
  - `LOG.txt` is append-only and never edited;
  - the memories form a binary tree of one-line summaries;
  - the summaries are a cache that can be rebuilt from the log;
  - a language model writes them.
- **Correction to `docs/DESIGN.md`.** OptMem also keeps its raw log, so "unlike OptMem, nothing is compacted away" is wrong. The difference is that OptMem's summaries are written by a model and lossy, while Matrix's are regression sufficient statistics. The orchestrator fixed DESIGN.md the same day.
- **Use:** cite it as software, for the design idea only.

## Part B: corrected entries for `paper/refs.bib`

These come from the arXiv abstract pages, fetched 2026-11-19. Two exceptions: Nagel's comes from the NBER page, and the regression cube's from its PDF page 1, which was read.

```bibtex
@misc{gouletcoulombe2024dual,
  author={Goulet Coulombe, Philippe and Goebel, Maximilian and Klieber, Karin},
  title={Dual Interpretation of Machine Learning Forecasts}, year={2024},
  eprint={2412.13076}, archivePrefix={arXiv}, primaryClass={econ.EM}, note={Submitted 2024-12-17}}
@misc{gouletcoulombe2025ols,
  author={Goulet Coulombe, Philippe}, title={Ordinary Least Squares as an Attention Mechanism}, year={2025},
  eprint={2504.09663}, archivePrefix={arXiv}, note={v1 2025-04-13; v3 2026-10-05}}
@misc{garnelo2023,
  author={Garnelo, Marta and Czarnecki, Wojciech Marian}, title={Exploring the Space of Key-Value-Query Models with Intention},
  year={2023}, eprint={2305.10203}, archivePrefix={arXiv}, note={Submitted 2023-05-17}}
@misc{vonoswald2025mesanet,
  author={von Oswald, Johannes and Scherrer, Nino and Kobayashi, Seijin and Versari, Luca and Yang, Songlin and Mittal, Sarthak and Schlegel, Maximilian and Maile, Kaitlin and Schimpf, Yanick and Sieberling, Oliver and Meulemans, Alexander and Saurous, Rif A. and Lajoie, Guillaume and Frenkel, Charlotte and Pascanu, Razvan and Ag{\"u}era y Arcas, Blaise and Sacramento, Jo{\~a}o},
  title={{MesaNet}: Sequence Modeling by Locally Optimal Test-Time Training}, year={2025},
  eprint={2506.05233}, archivePrefix={arXiv}, note={v1 2025-06-05; v2 2026-06-03; arXiv lists it as ICLR 2026}}
@misc{guo2025loglinear,
  author={Guo, Han and Yang, Songlin and Goel, Tarushii and Xing, Eric P. and Dao, Tri and Kim, Yoon},
  title={Log-Linear Attention}, year={2025}, eprint={2506.04761}, archivePrefix={arXiv}, note={v1 2025-06-05; the file read was v2; current v3 2026-03-01}}
@misc{causify2025,
  author={Saggese, Giacinto Paolo and Smith, Paul},
  title={Causify {DataFlow}: A Framework For High-performance Machine Learning Stream Computing}, year={2025},
  eprint={2512.23977}, archivePrefix={arXiv}, note={Submitted 2025-12-30}}
@techreport{nagel2025,
  author={Nagel, Stefan}, title={Seemingly Virtuous Complexity in Return Prediction},
  institution={National Bureau of Economic Research}, type={Working Paper}, number={34104}, year={2025}, note={August 2025}}
@article{chen2006regcube,
  author={Chen, Yixin and Dong, Guozhu and Han, Jiawei and Pei, Jian and Wah, Benjamin W. and Wang, Jianyong},
  title={Regression Cubes with Lossless Compression and Aggregation},
  journal={IEEE Transactions on Knowledge and Data Engineering}, volume={18}, number={12}, pages={1585--1598}, year={2006},
  doi={10.1109/TKDE.2006.196}}
```

- **Göbel.** arXiv spells the name "Goebel"; use that spelling.
- **MesaNet.** The full list of 17 authors replaces "and others".
- **Regression cube.** The title, authors, volume, issue and date come from PDF page 1. The DOI and the pages 1585–1598 come from a search summary only, so they are UNCONFIRMED; one IEEE-derived record gives 1599 as the last page.
- **Version drift.**
  - Since the versions the notes cite, 2504.09663 has reached v3 (2026-10-05) and 2506.05233 v2 (2026-06-03).
  - 2506.04761 was read at v2 and is now at v3.
  - Check that each cited passage is unchanged before submission.
