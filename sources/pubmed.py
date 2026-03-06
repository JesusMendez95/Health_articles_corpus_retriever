"""
PubMed/PMC source: descarga PDFs Open Access desde PubMed Central.

Flujo (solo requests, sin navegador):
  1. DOI → PMCID  via PMC ID Converter API
  2. PMCID → URL del paquete OA  via PMC OA API
  3. Descarga tar.gz y extrae el PDF

Solo funciona para artículos Open Access en PMC. Los artículos
de pago se saltan directamente a Sci-Hub.
"""
import io
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
import config
from utils import sanitize_filename, log


IDCONV_URL = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
OA_URL     = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}


def fetch(doi: str, title: str, dest_dir) -> dict:
    """
    Descarga el PDF de un artículo Open Access desde PubMed Central.

    Returns:
        dict con claves: success (bool), pdf_path (str|None), source (str), reason (str)
    """
    # 1. DOI → PMCID
    pmcid = _doi_to_pmcid(doi)
    if not pmcid:
        return {"success": False, "pdf_path": None, "source": "pubmed",
                "reason": "DOI no encontrado en PMC"}

    # 2. PMCID → URL del paquete OA
    pkg_url = _get_oa_package_url(pmcid)
    if not pkg_url:
        return {"success": False, "pdf_path": None, "source": "pubmed",
                "reason": "Artículo no disponible en Open Access en PMC"}

    # Convertir ftp:// → https:// (ambos funcionan, HTTPS más simple)
    if pkg_url.startswith("ftp://"):
        pkg_url = "https://" + pkg_url[6:]

    # 3. Descargar tar.gz y extraer PDF
    pdf_path = _download_and_extract_pdf(pkg_url, title or doi, Path(dest_dir))
    if pdf_path:
        log(f"  ✅ PubMed/PMC: {pdf_path.name}")
        return {"success": True, "pdf_path": str(pdf_path), "source": "pubmed"}

    return {"success": False, "pdf_path": None, "source": "pubmed",
            "reason": "No se pudo extraer el PDF del paquete PMC"}


def _doi_to_pmcid(doi: str) -> str | None:
    """Convierte un DOI a PMCID usando la API de conversión de PMC."""
    try:
        resp = requests.get(
            IDCONV_URL,
            params={"ids": doi, "format": "json"},
            headers=HEADERS,
            timeout=config.HTTP_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        for record in data.get("records", []):
            if record.get("status") != "error":
                pmcid = record.get("pmcid")
                if pmcid:
                    return pmcid
    except Exception as e:
        log(f"  PubMed ID Converter error: {e}")
    return None


def _get_oa_package_url(pmcid: str) -> str | None:
    """Obtiene la URL del paquete tar.gz para un PMCID Open Access."""
    try:
        resp = requests.get(
            OA_URL,
            params={"id": pmcid},
            headers=HEADERS,
            timeout=config.HTTP_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        root = ET.fromstring(resp.text)
        # Preferir tgz (contiene PDF), aceptar pdf directo si existe
        for fmt in ("tgz", "pdf"):
            for link in root.iter("link"):
                if link.get("format") == fmt:
                    href = link.get("href", "")
                    if href:
                        return href
    except Exception as e:
        log(f"  PubMed OA API error: {e}")
    return None


def _download_and_extract_pdf(pkg_url: str, title: str, dest_dir: Path) -> Path | None:
    """Descarga el tar.gz de PMC y extrae el PDF principal."""
    try:
        resp = requests.get(
            pkg_url,
            headers=HEADERS,
            timeout=config.HTTP_TIMEOUT * 3,  # paquetes pueden pesar varios MB
            stream=True,
        )
        if resp.status_code != 200:
            return None

        content = b"".join(resp.iter_content(65536))

        with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tar:
            pdf_members = [m for m in tar.getmembers() if m.name.lower().endswith(".pdf")]
            if not pdf_members:
                return None

            # El PDF más grande es el artículo principal (el resto son suplementos)
            pdf_member = max(pdf_members, key=lambda m: m.size)
            pdf_file = tar.extractfile(pdf_member)
            if not pdf_file:
                return None

            filename = sanitize_filename(title) + ".pdf"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / filename

            with open(dest_path, "wb") as f:
                f.write(pdf_file.read())

            if dest_path.stat().st_size > 1000:
                return dest_path
            dest_path.unlink(missing_ok=True)

    except Exception as e:
        log(f"  PubMed descarga error: {e}")
    return None
