# Health Articles Corpus — Download Summary

> Generated: 2026-03-06

## Overview

| Metric | Value |
|--------|-------|
| Total articles processed | 1,694 |
| **PDFs downloaded** | **1,356** |
| Study snapshots (Consensus) | 22 |
| Not found | 310 |
| Skipped (no DOI) | 6 |
| **Total files in archive** | **1,269** |
| Archive size | ~1.2 GB (`downloads/corpus_articles.tar.xz`) |

**Overall retrieval rate: 80.2%** (pdf + snapshot / total)

---

## By Topic

| Topic | Total | PDFs | Snapshots | Not Found | Skipped | Retrieval Rate |
|-------|------:|-----:|----------:|----------:|--------:|---------------:|
| Epigenetic | 42 | 39 | 0 | 3 | 0 | 92.9% |
| Functional Medicine | 42 | 27 | 0 | 15 | 0 | 64.3% |
| Mindfulness | 353 | 289 | 8 | 52 | 4 | 84.1% |
| Neuropsichology | 295 | 235 | 7 | 53 | 0 | 81.7% |
| Neuropsychiatry | 100 | 65 | 3 | 32 | 0 | 68.0% |
| Neuroscience | 169 | 124 | 4 | 41 | 0 | 75.7% |
| Psichiatry | 222 | 183 | 0 | 39 | 0 | 82.4% |
| Psychoanalytic | 50 | 40 | 0 | 10 | 0 | 80.0% |
| Psychology | 248 | 204 | 0 | 43 | 1 | 82.3% |
| Somathic Psychology | 173 | 150 | 0 | 22 | 1 | 86.7% |
| **Total** | **1,694** | **1,356** | **22** | **310** | **6** | **80.2%** |

---

## PDF Sources

| Source | PDFs | Share |
|--------|-----:|------:|
| Unpaywall (Open Access) | 698 | 51.5% |
| PubMed / PMC | 358 | 26.4% |
| Sci-Hub | 300 | 22.1% |
| Consensus (snapshot) | 22 | 1.6% |
| **Total** | **1,378** | 100% |

---

## Source Breakdown by Topic

| Topic | Unpaywall | PubMed | Sci-Hub | Consensus |
|-------|----------:|-------:|--------:|----------:|
| Epigenetic | 24 | 8 | 7 | 0 |
| Functional Medicine | 10 | 14 | 3 | 0 |
| Mindfulness | 126 | 63 | 100 | 8 |
| Neuropsichology | 129 | 72 | 34 | 7 |
| Neuropsychiatry | 28 | 11 | 26 | 3 |
| Neuroscience | 67 | 40 | 17 | 4 |
| Psichiatry | 107 | 49 | 27 | 0 |
| Psychoanalytic | 21 | 13 | 6 | 0 |
| Psychology | 120 | 36 | 48 | 0 |
| Somathic Psychology | 66 | 52 | 32 | 0 |
| **Total** | **698** | **358** | **300** | **22** |

---

## Files

```
downloads/
└── corpus_articles.tar.xz    (~1.2 GB, 1,269 PDFs)

results.csv                   (1,694 rows — full metadata index)
```

`results.csv` columns: `Topic`, `Title`, `Authors`, `Year`, `DOI`, `Journal`,
`Study_Type`, `Citations`, `Abstract`, `Study_Snapshot`, `PDF_Path`, `PDF_Source`,
`TXT_Path`, `Status`, `Status_Reason`, `Consensus_Link`

---

## Retrieval Pipeline

Articles were retrieved using a 4-source cascade per DOI:

1. **Unpaywall** — Open Access PDFs via API
2. **PubMed / PMC** — NIH Open Access PDFs
3. **Sci-Hub** — Fallback for paywalled articles
4. **Consensus Pro** — Study Snapshot text (when no PDF available)
