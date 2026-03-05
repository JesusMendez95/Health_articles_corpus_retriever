"""
Anna's Archive source: descarga PDFs buscando por DOI en annas-archive.org
"""
import time
import re
import requests
from bs4 import BeautifulSoup
import config
from utils import sanitize_filename, save_pdf, log


BASE_URL   = "https://annas-archive.org"
SEARCH_URL = f"{BASE_URL}/doi/{{doi}}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(doi: str, title: str, dest_dir) -> dict:
    """
    Busca un artículo por DOI en Anna's Archive e intenta descargar el PDF.

    Returns:
        dict con claves: success (bool), pdf_path (str|None), source (str), reason (str)
    """
    doi_url = SEARCH_URL.format(doi=doi)

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            session = requests.Session()
            session.headers.update(HEADERS)

            resp = session.get(doi_url, timeout=config.HTTP_TIMEOUT, allow_redirects=True)

            if resp.status_code == 404:
                return {"success": False, "pdf_path": None, "source": "annas_archive",
                        "reason": "No encontrado en Anna's Archive"}

            if resp.status_code != 200:
                log(f"  Anna's Archive: HTTP {resp.status_code} para {doi}")
                time.sleep(2 ** attempt)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Buscar enlaces de descarga en la página de resultados
            pdf_url = _find_download_link(soup, session, resp.url)

            if not pdf_url:
                return {"success": False, "pdf_path": None, "source": "annas_archive",
                        "reason": "No se encontró enlace de descarga PDF en Anna's Archive"}

            filename = sanitize_filename(title or doi) + ".pdf"
            pdf_path = save_pdf(pdf_url, dest_dir / filename, headers=HEADERS)

            if pdf_path:
                log(f"  ✅ Anna's Archive: {filename}")
                return {"success": True, "pdf_path": str(pdf_path), "source": "annas_archive"}
            else:
                return {"success": False, "pdf_path": None, "source": "annas_archive",
                        "reason": "Fallo al descargar el PDF"}

        except requests.exceptions.RequestException as e:
            log(f"  Anna's Archive error (intento {attempt}): {e}")
            time.sleep(2 ** attempt)

    return {"success": False, "pdf_path": None, "source": "annas_archive",
            "reason": "Error de conexión tras reintentos"}


def _find_download_link(soup: BeautifulSoup, session: requests.Session, current_url: str) -> str | None:
    """
    Busca el enlace de descarga directa del PDF en la página de Anna's Archive.
    Puede ser un link directo o un enlace a una página de paper individual.
    """
    # 1) Buscar enlace directo a PDF en la página actual
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Links directos a descarga
        if "/download" in href or "/slow_download" in href:
            return _resolve_url(href)
        # Links que parecen ir directamente a un PDF
        if href.endswith(".pdf") and href.startswith("http"):
            return href

    # 2) Buscar enlace a página de paper individual (md5)
    paper_link = None
    for a in soup.find_all("a", href=True):
        if re.match(r"/md5/[a-f0-9]+", a["href"]):
            paper_link = BASE_URL + a["href"]
            break

    if not paper_link:
        return None

    # 3) Visitar la página del paper y buscar el botón de descarga
    try:
        resp2 = session.get(paper_link, timeout=config.HTTP_TIMEOUT)
        soup2 = BeautifulSoup(resp2.text, "html.parser")

        for a in soup2.find_all("a", href=True):
            href = a["href"]
            if "/download" in href or "/slow_download" in href:
                return _resolve_url(href)
            if href.endswith(".pdf") and href.startswith("http"):
                return href
    except Exception:
        pass

    return None


def _resolve_url(href: str) -> str:
    """Convierte paths relativos a URLs absolutas."""
    if href.startswith("http"):
        return href
    return BASE_URL + href
