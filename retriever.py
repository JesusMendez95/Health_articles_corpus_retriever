"""
Article Retriever — Orquestador principal
=========================================
Cascada de 4 fuentes por DOI:
  1. Unpaywall API  → PDF completo (Open Access)
  2. PubMed/PMC    → PDF completo Open Access via OA API
  3. Sci-Hub        → PDF completo (respaldo)
  4. Consensus Pro  → Study Snapshot en CSV (cuando no hay PDF)

Uso:
    python retriever.py                     # Procesa todos los CSVs
    python retriever.py --limit 5           # Solo 5 artículos por CSV (test)
    python retriever.py --csv mindfulness   # Solo el CSV que contenga "mindfulness"
    python retriever.py --skip-consensus    # Omite paso 3 (no necesita login)
"""

import argparse
import csv
import sys
import time
from pathlib import Path

import config
import utils
from sources import unpaywall, pubmed, scihub, consensus


# ── Columnas del CSV de resultados ────────────────────────────────────────────
RESULT_COLS = [
    "Topic", "Title", "Authors", "Year", "DOI",
    "Journal", "Study_Type", "Citations",
    "Abstract", "Study_Snapshot",
    "PDF_Path", "PDF_Source", "TXT_Path", "Status", "Status_Reason",
    "Consensus_Link",
]


def main():
    args = parse_args()
    config.validate()

    base_dir = Path(__file__).parent
    results_path = config.RESULTS_CSV

    # Leer artículos ya procesados para poder reanudar
    already_done = load_done_dois(results_path)
    print(f"📋 Artículos ya procesados: {len(already_done)}\n")

    # Abrir CSV de resultados en modo append
    results_file = open(results_path, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(results_file, fieldnames=RESULT_COLS)
    if results_path.stat().st_size == 0:
        writer.writeheader()

    # Buscar todos los CSVs de Consensus en el directorio data/
    data_dir = base_dir / "data"
    csv_files = sorted(data_dir.glob("*_consensus.csv"))
    csv_files = [f for f in csv_files if f.suffix == ".csv"]

    if args.csv:
        csv_files = [f for f in csv_files if args.csv.lower() in f.name.lower()]

    if not csv_files:
        print("❌ No se encontraron archivos CSV. Verifica el directorio.")
        sys.exit(1)

    total_all = 0
    ok_all = 0
    pdf_all = 0
    snapshot_all = 0
    fail_all = 0

    try:
        for csv_path in csv_files:
            topic = csv_path.stem.replace("_consensus", "").replace("_", " ").title()
            dest_dir = config.DOWNLOADS_DIR / csv_path.stem.replace("_consensus", "")
            dest_dir.mkdir(parents=True, exist_ok=True)

            articles = read_csv(csv_path)
            if args.limit:
                articles = articles[:args.limit]

            total = len(articles)
            ok = pdf_count = snap_count = fail = 0

            print(f"{'─'*60}")
            print(f"📂 {topic}  ({total} artículos)")
            print(f"{'─'*60}")

            for i, art in enumerate(articles, 1):
                doi   = art.get("DOI", "").strip()
                title = art.get("Title", "").strip()
                url   = art.get("Consensus Link", "").strip()

                utils.print_progress(i, total, topic, title[:40])

                # Skip si ya fue procesado
                if doi and doi in already_done:
                    ok += 1
                    continue

                if not doi:
                    fail += 1
                    write_result(writer, art, topic, status="skipped",
                                 reason="Sin DOI")
                    continue

                abstract = art.get("Abstract", "").strip()
                result = process_article(
                    doi, title, abstract, url, dest_dir,
                    skip_consensus=args.skip_consensus
                )
                write_result(writer, art, topic,
                             pdf_path=result.get("pdf_path"),
                             pdf_source=result.get("source"),
                             study_snapshot=result.get("study_snapshot"),
                             txt_path=result.get("txt_path"),
                             status=result["status"],
                             reason=result.get("reason", ""))
                results_file.flush()

                if result["status"] == "pdf_downloaded":
                    ok += 1
                    pdf_count += 1
                elif result["status"] == "snapshot_only":
                    ok += 1
                    snap_count += 1
                else:
                    fail += 1

                utils.random_delay()

            print()  # nueva línea tras barra de progreso
            print(f"  ✅ PDFs: {pdf_count}  📄 Snapshots: {snap_count}  ❌ Fallidos: {fail}\n")

            total_all   += total
            ok_all      += ok
            pdf_all     += pdf_count
            snapshot_all+= snap_count
            fail_all    += fail

    finally:
        results_file.close()
        consensus.close()  # cerrar navegador

    # Resumen final
    print(f"\n{'═'*60}")
    print(f"  RESUMEN FINAL")
    print(f"{'═'*60}")
    print(f"  Total artículos procesados : {total_all}")
    print(f"  PDFs descargados           : {pdf_all}")
    print(f"  Study Snapshots extraídos  : {snapshot_all}")
    print(f"  Sin resultado              : {fail_all}")
    print(f"  Resultados guardados en    : {config.RESULTS_CSV}")
    print(f"  PDFs en                    : {config.DOWNLOADS_DIR}/")
    print()


def process_article(doi: str, title: str, abstract: str, consensus_url: str,
                    dest_dir: Path, skip_consensus: bool = False) -> dict:
    """
    Ejecuta la cascada de 4 fuentes para un artículo.
    """
    # ── 1. Unpaywall ──────────────────────────────────────────────────────────
    if config.UNPAYWALL_EMAIL:
        result = unpaywall.fetch(doi, title, dest_dir)
        if result["success"]:
            return {**result, "status": "pdf_downloaded", "study_snapshot": None, "txt_path": None}

    # ── 2. PubMed/PMC ─────────────────────────────────────────────────────────
    result = pubmed.fetch(doi, title, dest_dir)
    if result["success"]:
        return {**result, "status": "pdf_downloaded", "study_snapshot": None, "txt_path": None}

    # ── 3. Sci-Hub ────────────────────────────────────────────────────────────
    result = scihub.fetch(doi, title, dest_dir)
    if result["success"]:
        return {**result, "status": "pdf_downloaded", "study_snapshot": None, "txt_path": None}

    # ── 4. Consensus (fallback: título + abstract + snapshot en .txt) ─────────
    if skip_consensus or not consensus_url:
        return {"status": "not_found", "pdf_path": None, "source": None,
                "study_snapshot": None, "txt_path": None,
                "reason": "No disponible en ninguna fuente"}

    snap_result = consensus.get_study_snapshot(consensus_url, title, abstract, dest_dir)
    if snap_result["success"]:
        return {
            "status": "snapshot_only",
            "pdf_path": None,
            "source": "consensus",
            "study_snapshot": snap_result["study_snapshot"],
            "txt_path": snap_result.get("txt_path"),
        }

    return {"status": "not_found", "pdf_path": None, "source": None,
            "study_snapshot": None, "txt_path": None,
            "reason": f"Todas las fuentes fallaron: {snap_result.get('reason', '')}"}


def read_csv(path: Path) -> list[dict]:
    """Lee un CSV de Consensus y devuelve lista de dicts."""
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_result(writer, art: dict, topic: str, pdf_path=None,
                 pdf_source=None, study_snapshot=None, txt_path=None,
                 status="not_found", reason=""):
    """Escribe una fila en el CSV de resultados."""
    writer.writerow({
        "Topic":          topic,
        "Title":          art.get("Title", ""),
        "Authors":        art.get("Authors", ""),
        "Year":           art.get("Year", ""),
        "DOI":            art.get("DOI", ""),
        "Journal":        art.get("Journal", ""),
        "Study_Type":     art.get("Study Type", ""),
        "Citations":      art.get("Citations", ""),
        "Abstract":       art.get("Abstract", ""),
        "Study_Snapshot": study_snapshot or "",
        "PDF_Path":       pdf_path or "",
        "PDF_Source":     pdf_source or "",
        "TXT_Path":       txt_path or "",
        "Status":         status,
        "Status_Reason":  reason,
        "Consensus_Link": art.get("Consensus Link", ""),
    })


def load_done_dois(results_path: Path) -> set:
    """Carga los DOIs ya procesados para poder reanudar."""
    done = set()
    if not results_path.exists():
        return done
    try:
        with open(results_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                doi = row.get("DOI", "").strip()
                if doi:
                    done.add(doi)
    except Exception:
        pass
    return done


def parse_args():
    parser = argparse.ArgumentParser(
        description="Descarga artículos científicos desde múltiples fuentes"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Número máximo de artículos a procesar por CSV (útil para pruebas)"
    )
    parser.add_argument(
        "--csv", type=str, default=None,
        help="Filtrar por nombre de CSV (ej: --csv mindfulness)"
    )
    parser.add_argument(
        "--skip-consensus", action="store_true",
        help="Omitir la extracción de Study Snapshots de Consensus (no requiere login)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
