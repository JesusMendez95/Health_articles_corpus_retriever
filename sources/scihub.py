"""
Sci-Hub source: descarga PDFs buscando por DOI.
Fuente de respaldo entre Anna's Archive y Consensus.
"""
import re
import time
import requests
from bs4 import BeautifulSoup
import config
from utils import sanitize_filename, save_pdf, log


# Mirrors en orden de preferencia (sci-hub.ru funciona, .st da 403)
MIRRORS = [
    "https://sci-hub.ru",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(doi: str, title: str, dest_dir) -> dict:
    """
    Busca un artículo por DOI en Sci-Hub e intenta descargar el PDF.

    Returns:
        dict con claves: success (bool), pdf_path (str|None), source (str), reason (str)
    """
    for mirror in MIRRORS:
        result = _try_mirror(mirror, doi, title, dest_dir)
        if result["success"]:
            return result
        # Si el mirror está caído/bloqueado, probar el siguiente
        if result.get("reason") in ("conexion_error", "http_error"):
            continue

    return {"success": False, "pdf_path": None, "source": "scihub",
            "reason": "No disponible en ningún mirror de Sci-Hub"}


def _try_mirror(mirror: str, doi: str, title: str, dest_dir) -> dict:
    """Intenta obtener el PDF desde un mirror concreto."""
    url = f"{mirror}/{doi}"
    session = requests.Session()
    session.headers.update(HEADERS)

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=config.HTTP_TIMEOUT, allow_redirects=True)

            if resp.status_code == 404:
                return {"success": False, "pdf_path": None, "source": "scihub",
                        "reason": "DOI no encontrado en Sci-Hub"}

            if resp.status_code != 200:
                log(f"  Sci-Hub {mirror}: HTTP {resp.status_code} para {doi}")
                time.sleep(2 ** attempt)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            pdf_url = _find_pdf_url(soup, mirror)

            if not pdf_url:
                return {"success": False, "pdf_path": None, "source": "scihub",
                        "reason": "No se encontró enlace de descarga en Sci-Hub"}

            filename = sanitize_filename(title or doi) + ".pdf"
            pdf_path = save_pdf(pdf_url, dest_dir / filename, headers=HEADERS)

            if pdf_path:
                log(f"  ✅ Sci-Hub: {filename}")
                return {"success": True, "pdf_path": str(pdf_path), "source": "scihub"}

            return {"success": False, "pdf_path": None, "source": "scihub",
                    "reason": "Fallo al descargar el PDF desde Sci-Hub"}

        except requests.exceptions.RequestException as e:
            log(f"  Sci-Hub {mirror} error (intento {attempt}): {e}")
            time.sleep(2 ** attempt)

    return {"success": False, "pdf_path": None, "source": "scihub",
            "reason": "conexion_error"}


def _find_pdf_url(soup: BeautifulSoup, mirror: str) -> str | None:
    """Extrae la URL del PDF de la página de Sci-Hub."""
    # 1) Enlace directo de descarga: <a href="/download/...pdf">
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/download/" in href:
            return href if href.startswith("http") else mirror + href

    # 2) Iframe o embed con el PDF
    for tag in soup.find_all(["iframe", "embed"], src=True):
        src = tag["src"]
        # src puede ser "//downloads.sci-hub.ru/..." o "/storage/..."
        if src.startswith("//"):
            return "https:" + src.split("#")[0]
        if src.startswith("/"):
            return mirror + src.split("#")[0]
        if src.startswith("http"):
            return src.split("#")[0]

    # 3) URL en atributo onclick o data-* de botones
    for btn in soup.find_all(True, onclick=True):
        match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", btn["onclick"])
        if match:
            href = match.group(1)
            if ".pdf" in href:
                return href if href.startswith("http") else mirror + href

    return None
