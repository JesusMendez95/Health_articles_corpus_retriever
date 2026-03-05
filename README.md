# Health Articles Corpus Retriever

A Python-based tool to automatically retrieve and download PDF versions of scientific articles from multiple sources using a 3-step cascade approach. It processes CSV files containing article DOIs, specifically designed to process exports from Consensus.

## Features

- Processes multiple Consensus CSV files containing article metadata.
- Implements a 3-source cascade fallback system to maximize the retrieval rate:
  1. **Unpaywall API**: Checks for open-access versions of the article.
  2. **Anna's Archive**: Scrapes for direct PDF download links if Unpaywall fails.
  3. **Consensus**: Uses Playwright to extract the *Study Snapshot* (requires a Pro account profile).
- Saves downloaded PDFs organized by topic.
- Generates a final `results.csv` report containing metadata, extraction results, and download status.
- State-aware and resumable operations (skips already processed articles).
- Implements rate limiting with random delays to avoid being blocked.

## Prerequisites

- Python 3.8+

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/JesusMendez95/Health_articles_corpus_retriever.git
   cd Health_articles_corpus_retriever
   ```

2. Install the required dependencies:
   ```bash
   pip install requests beautifulsoup4 playwright python-dotenv
   ```

3. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

4. Configuration:
   - Copy `.env.example` to a new file named `.env` and configure it with your Unpaywall email and Consensus credentials.

## Usage

Place your source CSV files in the `data/` directory, then run the main script:

```bash
python retriever.py
```

*(Optional flags like `--limit` may be available depending on your implementation to test with a smaller batch of articles).*

## Folder Structure

- `/data`: Directory for input CSV files.
- `/downloads`: Retrieved PDFs will be saved here, automatically organized by topic.
- `/sources`: Contains the modules for the different retrieval methods (`unpaywall.py`, `annas_archive.py`, `consensus.py`).
- `config.py`: Configuration and environment handling.
- `utils.py`: Helper and utility functions.
- `retriever.py`: The main entrypoint and orchestrator script.
