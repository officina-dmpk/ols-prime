# Reading B: Binance terms and the arXiv paper / leak corpus (read 2026-11-18)

- **Author:** `scout` run B, 2026-11-18; saved by the orchestrator (scout cannot write files).
- **Not legal advice.** Paraphrase of terms by a research agent; a lawyer or Binance's written answer is the only firm basis.

## 1. What was read, and how well

| Document | URL | Read level |
|---|---|---|
| Binance Terms of Use | https://www.binance.com/en/terms | **Could not fetch.** The page returned only a site footer (nav links, ADGM regulatory notice, risk warning, "Binance© 2026"), not the terms. Variants https://www.binance.com/en/terms-of-use and .../terms-of-use/eu returned HTTP 404. https://www.binance.com/en/terms/ returned 404. A guessed support-FAQ URL returned "This article does not exist." The page is likely script-rendered, which the fetch tool cannot execute. Nothing was filled from snippets. |
| Binance Vision Dataset Terms v1.0 (updated 2026-08-26) | https://raw.githubusercontent.com/binance/binance-public-data/master/TERMS_AND_CONDITIONS.md | **Read in full, but through a summarising fetch tool, not verbatim.** Clause numbers below are as reported by it; they match `docs/DATA.md` (1.2, 1.4, 2.4, 3, 4.1-4.5, 7, 8). Re-check 1.5, 5, 9-12 against the raw file before relying on them. Commit hash not re-checked today (DATA.md: d3357a5c33ba, read 2026-10-25). |
| data.binance.vision front page | https://data.binance.vision/ | Read. It shows only a "Terms of Use" link and a GitHub link; no licence text of its own. |
| binance-public-data README | https://github.com/binance/binance-public-data | Partial. It points to TERMS_AND_CONDITIONS.md for dataset use and names MIT for the repository (scripts/docs, unclear whether it covers the data). |

## 2. Dataset terms: relevant clauses

- **1.2** supplements the Terms of Use and is subject to them. **1.5** (new vs DATA.md) says that on conflict the dataset terms control for the services they cover. **1.4**: amendments apply only to data released afterwards; data already downloaded stays under the terms in force at download.
- **1.3** provider: NEST EXCHANGE LIMITED (ADGM, Abu Dhabi).
- **2.3** any individual or entity may access the data free of charge, subject to the terms. No eligibility or restricted-jurisdiction clause was reported anywhere in the document.
- **2.4** charts, models, indicators and anything calculated with the data fall under the terms.
- **3.1-3.4** CC BY-NC-SA 4.0; stricter of terms and licence applies; commercial use needs a separate written licence.
- **4.1** permitted: academic research, non-monetised open educational projects, personal non-production backtesting, non-commercial open-source evaluation. **6.1**: data is meant for computational, educational and research purposes.
- **4.2-4.4** forbidden: live proprietary trading, automated commercial orders, paid signals, selling/hosting the data or derived data feeds, commercial products.
- **4.5** redistributed derivative works must credit Binance Vision and be licensed CC BY-NC-SA 4.0.
- **5** Binance may modify or discontinue datasets without notice. **7.2** no circumventing rate limits. **8.2/8.3** do not imply Binance endorsement.
- **9.2** do not de-anonymise identifiers. **10** "as is", no accuracy warranty. **11** indemnification of Binance for breach (adds to the Terms of Use).
- **12** disputes go through the Terms of Use machinery (negotiation, arbitration, governing law, class waiver). The governing law itself is **not named here, so it sits in the unread Terms of Use**.
- No dedicated clause on publishing research results, on restricted jurisdictions, or on termination.

## 3. Answers

**Q1. May an individual in France publish an arXiv paper under CC BY-NC-SA 4.0 with figures derived from archives downloaded in 2026-10?**
Under the dataset terms alone: **yes, on the face of it.** Academic research is expressly allowed (4.1), derived works are covered by 2.4, and 4.5 requires credit to Binance Vision plus the same CC BY-NC-SA 4.0 licence, which is exactly what the paper plans. Terms in force at download (2026-10) are v1.0 (1.4). Conditions: credit "Binance Vision", no endorsement claim (8.2), no commercial use (3.4). Caveat: arXiv's own licence menu includes CC BY-NC-SA 4.0, but arXiv also grants itself a distribution licence; not checked here (inference).
**Not settled:** the Terms of Use (unread) rank above the dataset terms (1.2) yet yield on conflict (1.5). Any France or jurisdiction clause there is unknown.

**Q2. May the leak corpus (Python functions of the bars, and their outputs) be released?**
- **Code (functions):** the code is ours (MIT); it contains no Binance data. Inference: fine.
- **Outputs that are functions of the bars:** these are derivatives under 2.4. Releasable under 4.5 (credit plus CC BY-NC-SA 4.0), as DATA.md already states. Ambiguity: 4.3 forbids "hosting ... derived data feeds". A corpus whose outputs let someone rebuild the bars (raw OHLCV, or near-invertible transforms) risks reading as hosting the data. Mitigations (inference): release functions plus checksummed fetch instructions, not raw bars; or only aggregate or non-invertible outputs; keep the licence label on the corpus.
- The MIT licence on the code and CC BY-NC-SA on the outputs must be stated separately.

**Q3. Does the French closure (2026-07-01) touch use of the public archive?**
Dataset terms: no jurisdictional restriction found, and 2.3 opens access to any individual. Whether the Terms of Use's restricted-jurisdiction clause reaches the public archive (a service, not an account) is **unknown, as the text was not fetched**. Ambiguity: a closure of trading services does not obviously extend to a static download site, but this is inference, not a finding.

## 4. Ambiguities and conflicts

1. Unread Terms of Use hold governing law, arbitration, jurisdiction, indemnity: unresolved.
2. 1.2 vs 1.5 create a circular precedence.
3. "Hosting derived data feeds" (4.3) vs "redistributed derivative works" (4.5): the line is not defined.
4. Repository MIT licence vs data CC BY-NC-SA: unclear coverage of data.
5. 3.1 "except where stated otherwise" is not itemised; 5 says some indicators may carry third-party restrictions (klines are Binance's own, inference).

## 5. Verdicts

- Q1 paper: **use**, with credit and CC BY-NC-SA 4.0, pending the Terms of Use check.
- Q2 corpus: **unsure**. Release code and recipes; avoid bars or invertible outputs until Binance answers or the Terms of Use are read.
- Q3 France: **unsure**.
- Bolder idea: email Binance's data-licensing contact with a two-line question (arXiv paper plus function corpus, French resident); a written yes also unblocks the phase-6 live-use question in DATA.md. Abdou's act, not an agent's.

## 6. Proposed line for `docs/DATA.md` (Terms of Use bullet)

- 2026-11-18: the Binance Terms of Use could not be fetched (binance.com/en/terms returned only a site footer, variants 404); the dataset terms re-read in full via a summarising fetch: add 1.5 (dataset terms control on conflict), 12 (disputes follow the Terms of Use, which name the governing law) and 4.3 (no hosting of derived data feeds); no jurisdiction clause found there. Publishing a paper under CC BY-NC-SA 4.0 with credit looks allowed under 4.1 and 4.5; releasing a corpus of bar-derived outputs stays open until the Terms of Use are read. Not legal advice.

## 7. Addendum: the Binance Terms of Use, read 2026-11-18

The orchestrator found the ToU in the built-in browser: binance.com/en/terms embeds a PDF (https://bin.bnbstatic.com/static/cms/cg08ou2ak0tn7mcplvfg/file/f7c3c8a8fbda48eaa272ff503b8c2e54c6c98ad4f0f2a1e5da3667af5962c7de.pdf, page 1 "Effective Date: 27 October 2026"). Scout run B then read it. Not legal advice; clause numbers as printed in the PDF.

### Read level
- WebFetch could not parse the PDF; the saved copy was read page by page as images. The PDF metadata title says "ADGM Binance Global Terms of Use (Draft - 27 Oct 2026)", while page 1 says "Effective Date: 27 October 2026": to check on binance.com.
- **Read:** pp. 1-6 (parties, Risk Warning, cl. 1.1-1.4, 2.1-2.2), pp. 44-56 (end of cl. 25 to 34.4), pp. 60-67 (cl. 36.2 to 41 start, definitions "Accepted..." to "Claim").
- **Not read:** pp. 7-43, 57-59, 68-74, including the definitions of "Binance Services", "Sites", "Created IP", "Restricted Person", "User Material", and the linked List of Prohibited Countries and Prohibited Use Policy.

### (1) Jurisdictions
- **Cl. 2.1(f)(ii):** to register and use the Binance Services you must not be located, resident or established in a jurisdiction on the List of Prohibited Countries (or one where use is illegal, 2.1(f)(i)); 2.1(e): not a Restricted Person.
- **Cl. 25.5:** services may be restricted in some countries and access blocked; no circumvention by VPN. **Cl. 31.1(e):** no use with high-risk jurisdictions or persons.
- **France:** the list is an external page, not read; whether France is on it is not found. DATA.md's press-based claim of closure remains unverified at a primary source.
- **Non-account use:** these clauses are framed around registering for and using the Binance Services (Account and Platform). Whether the public archive is a Binance Service depends on unread definitions. Inference only: not obviously covered; unresolved.

### (2) Intellectual property, market data
- **Cl. 26:** Binance IP stays vested in Binance. **Cl. 27:** non-exclusive licence, for the duration of the Agreement, solely to receive the Services for non-commercial personal or internal business use.
- **Cl. 28-29:** User IP licensed to Binance; Created IP vests in Binance (content produced through the Services).
- **Cl. 33.8:** Proprietary Information (databases, programmes, displays) is Binance's or its licensors'. **Cl. 33.11:** third-party indices or market data as is. **Cl. 33.4:** no warranty on site content. **Cl. 31.1(d):** do not violate IP.
- **Not found in the pages read:** any clause on publishing or redistributing market data, research use or derived works. Partial finding (pp. 7-43, 57-59 unread).

### (3) Governing law and disputes
- **Cl. 38:** ADGM law, exclusive. **Cl. 36.2-36.4:** notice, then 90-day negotiation before arbitration. **Cl. 37:** individual ICC arbitration, three arbitrators, seat ADGM (37.3), English, award unpublished, confidential. **Cl. 39:** class-action waiver. **Cl. 34.1:** broad indemnity. **Cl. 40.8:** English text prevails. Mandatory French consumer rules not mentioned in the pages read.

### (4) Precedence against the dataset terms
- **Cl. 1.3-1.4:** the Agreement includes Core Policies, Rulebooks, Product Terms and any agreement that expresses to form part of the ToU (1.3.4); an order of precedence is given. The Vision dataset terms are not named in the pages read and sit in none of the tiers. Vision 1.2 and 1.5 stay mutually inconsistent; unresolved.

### Revised verdicts
- **Q1, paper (CC BY-NC-SA 4.0, credit, no endorsement claim): use**, moderate confidence.
- **Q2, corpus: unsure**, unchanged. Release code and recipes; hold back bars and invertible outputs (Vision 4.3; ToU cl. 27 pushes the same way).
- **Q3, French closure: unsure.**

### Proposed DATA.md line (replaces the one of section 6)
- 2026-11-18: Binance Terms of Use (effective 2026-10-27, PDF; metadata says "Draft") read in part (pp. 1-6, 44-56, 60-67 of 74). Cl. 2.1(f)(ii) and 25.5 exclude residents of prohibited countries from the Services; the list was not read and no clause was found that applies this to the public archive. Cl. 27 licenses Binance IP for non-commercial use. Cl. 38 and 37 set ADGM law and ICC arbitration seated in the ADGM. No clause on publishing research or redistributing data was found in the pages read; pp. 7-43, 57-59, 68-74 are unread. The ToU's cl. 1.4 precedence list does not rank the Vision terms (Vision 1.2 and 1.5 conflict). A paper with credit under CC BY-NC-SA 4.0 looks allowed; a corpus of bar-derived outputs stays open. Not legal advice.

### Open, for Abdou
- One written question to Binance's data contact or a lawyer: is data.binance.vision a Binance Service under the ToU, and may a French resident publish CC BY-NC-SA derivatives? Abdou's act.
