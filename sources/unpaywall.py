"""
Unpaywall source: descarga PDFs Open Access usando la API de Unpaywall.
API docs: https://unpaywall.org/products/api
"""
import time
import requests
import config
from utils import sanitize_filename, save_pdf, log


UNPAYWALL_API = "https://api.unpaywall.org/v2/{doi}?email={email}"


def fetch(doi: str, title: str, dest_dir) -> dict:
    """
    Busca el PDF Open Access de un artículo en Unpaywall.

    Returns:
        dict con claves: success (bool), pdf_path (str|None), source (str)
    """
    if not config.UNPAYWALL_EMAIL:
        return {"success": False, "pdf_path": None, "source": "unpaywall",
                "reason": "UNPAYWALL_EMAIL no configurado"}

    url = UNPAYWALL_API.format(doi=doi, email=config.UNPAYWALL_EMAIL)

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=config.HTTP_TIMEOUT)

            if resp.status_code == 404:
                return {"success": False, "pdf_path": None, "source": "unpaywall",
                        "reason": "DOI no encontrado en Unpaywall"}

            if resp.status_code != 200:
                log(f"  Unpaywall: HTTP {resp.status_code} para {doi}")
                time.sleep(2 ** attempt)
                continue

            data = resp.json()

            # Buscar URL del PDF: primero best_oa_location, luego oa_locations
            pdf_url = _extract_pdf_url(data)

            if not pdf_url:
                return {"success": False, "pdf_path": None, "source": "unpaywall",
                        "reason": "No hay versión Open Access disponible"}

            # Descargar el PDF
            filename = sanitize_filename(title or doi) + ".pdf"
            pdf_path = save_pdf(pdf_url, dest_dir / filename)

            if pdf_path:
                log(f"  ✅ Unpaywall: {filename}")
                return {"success": True, "pdf_path": str(pdf_path), "source": "unpaywall"}

        except requests.exceptions.RequestException as e:
            log(f"  Unpaywall error (intento {attempt}): {e}")
            time.sleep(2 ** attempt)

    return {"success": False, "pdf_path": None, "source": "unpaywall",
            "reason": "Error de conexión tras reintentos"}


def _extract_pdf_url(data: dict) -> str | None:
    """Extrae la mejor URL de PDF de la respuesta de la API de Unpaywall."""
    # Primero intentar best_oa_location
    best = data.get("best_oa_location")
    if best:
        url = best.get("url_for_pdf") or best.get("url")
        if url and url.endswith(".pdf"):
            return url
        if url and "pdf" in url.lower():
            return url

    # Luego recorrer todas las oa_locations
    for loc in data.get("oa_locations", []):
        url = loc.get("url_for_pdf")
        if url:
            return url

    return None
