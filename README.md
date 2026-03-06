# Health Articles Corpus Retriever

A Python tool that automatically downloads PDF versions of scientific articles from multiple open-access and fallback sources. Designed to process exports from [Consensus](https://consensus.app), it implements a 4-source cascade to maximize retrieval rate.

## Dataset

The full article corpus (PDFs and metadata) is too large to host on GitHub and is available on HuggingFace:

**[Multidisciplinary Health Articles Dataset](https://huggingface.co/datasets/Chus010895/multidisciplinary-health-articles/tree/main)**

The dataset includes all downloaded PDFs organized by topic, along with the `results.csv` metadata index.

## Results

See [CORPUS_SUMMARY.md](CORPUS_SUMMARY.md) for full statistics on the downloaded corpus.

| Metric | Value |
|--------|-------|
| Articles processed | 1,694 |
| PDFs downloaded | 1,356 (80.2%) |
| Total archive size | ~1.2 GB |

## Retrieval Pipeline

For each article DOI, sources are tried in order until one succeeds:

```
DOI
 └─ 1. Unpaywall API       → Open Access PDF           ✅
     └─ 2. PubMed / PMC    → NIH Open Access PDF        ✅
         └─ 3. Sci-Hub     → PDF fallback               ✅
             └─ 4. Consensus Pro → Study Snapshot (.txt) ✅
```

| Source | Articles | Share |
|--------|-------:|------:|
| Unpaywall | 698 | 51.5% |
| PubMed / PMC | 358 | 26.4% |
| Sci-Hub | 300 | 22.1% |
| Consensus (snapshot) | 22 | 1.6% |

## Requirements

- Python 3.10+
- Google Chrome (for Consensus snapshot extraction)
- A [Consensus Pro](https://consensus.app) account (optional — only needed for study snapshots)
- A free [Unpaywall](https://unpaywall.org) email registration

## Installation

```bash
git clone https://github.com/JesusMendez95/Health_articles_corpus_retriever.git
cd Health_articles_corpus_retriever
python -m venv .venv && source .venv/bin/activate
pip install requests beautifulsoup4 python-dotenv playwright
playwright install chromium
```

## Configuration

```bash
cp .env.example .env
```

Edit `.env`:

```env
UNPAYWALL_EMAIL=your@email.com     # Required — free registration at unpaywall.org
CONSENSUS_EMAIL=your@email.com     # Optional — only for Study Snapshots
CONSENSUS_PASSWORD=yourpassword    # Optional — only for Study Snapshots
```

## Usage

Place `*_consensus.csv` files in the `data/` directory, then run:

```bash
# Process all CSVs
python retriever.py

# Test with a small batch
python retriever.py --limit 5

# Process a specific topic
python retriever.py --csv mindfulness

# Skip Consensus (no Chrome login needed)
python retriever.py --skip-consensus
```

The script is **resumable** — it skips already-processed DOIs on restart.

### Consensus Study Snapshots (optional)

To extract Study Snapshots, start Chrome with remote debugging before running the retriever:

```bash
./start_chrome_debug.sh   # Opens Chrome — log in to Consensus manually on first run
python retriever.py
```

## Project Structure

```
├── retriever.py            # Main orchestrator
├── config.py               # Configuration and environment variables
├── utils.py                # Shared helpers (filename sanitization, PDF saving, logging)
├── sources/
│   ├── unpaywall.py        # Source 1: Unpaywall Open Access API
│   ├── pubmed.py           # Source 2: PubMed / PMC OA API
│   ├── scihub.py           # Source 3: Sci-Hub scraper
│   └── consensus.py        # Source 4: Consensus Study Snapshot via CDP
├── data/                   # Input: *_consensus.csv files from Consensus
├── downloads/              # Output: PDFs organized by topic
├── results.csv             # Output: full metadata index with download status
├── .env.example            # Environment variables template
└── start_chrome_debug.sh   # Helper to launch Chrome with remote debugging
```

## Output

**`results.csv`** — one row per article with columns:

`Topic`, `Title`, `Authors`, `Year`, `DOI`, `Journal`, `Study_Type`, `Citations`, `Abstract`, `Study_Snapshot`, `PDF_Path`, `PDF_Source`, `TXT_Path`, `Status`, `Status_Reason`, `Consensus_Link`

**Status values:**
- `pdf_downloaded` — PDF saved to `downloads/<topic>/`
- `snapshot_only` — No PDF found; Study Snapshot saved as `.txt`
- `not_found` — Article not available in any source
- `skipped` — No DOI available
