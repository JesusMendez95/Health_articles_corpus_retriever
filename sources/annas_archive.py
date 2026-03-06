"""
Anna's Archive source: descarga PDFs buscando por DOI.
Usa Playwright para navegar mirrors activos que requieren verificación de navegador.
"""
import re
import time
import config
from utils import sanitize_filename, save_pdf, log

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# Mirrors en orden de preferencia — actualizar si cambian de dominio
MIRRORS = [
    "https://annas-archive.gs",
    "https://annas-archive.ph",
]

_browser_context = None


def fetch(doi: str, title: str, dest_dir) -> dict:
    """
    Busca un artículo por DOI en Anna's Archive e intenta descargar el PDF.

    Returns:
        dict con claves: success (bool), pdf_path (str|None), source (str), reason (str)
    """
    if not PLAYWRIGHT_AVAILABLE:
        return {"success": False, "pdf_path": None, "source": "annas_archive",
                "reason": "playwright no instalado (pip install playwright)"}

    for mirror in MIRRORS:
        doi_url = f"{mirror}/doi/{doi}"
        result = _try_mirror(doi_url, doi, title, dest_dir)
        if result["success"]:
            return result
        if result.get("reason") == "bot_check":
            log(f"  Anna's Archive: bot-check en {mirror}, probando siguiente mirror...")
            continue
        # Si el DOI no existe en este mirror (404), no tiene sentido probar otros
        if "No encontrado" in result.get("reason", ""):
            return result

    return {"success": False, "pdf_path": None, "source": "annas_archive",
            "reason": "No disponible en ningún mirror de Anna's Archive"}


def _try_mirror(doi_url: str, doi: str, title: str, dest_dir) -> dict:
    """Intenta obtener el PDF desde un mirror concreto usando Playwright."""
    page = None
    try:
        context = _get_context()
        page = context.new_page()

        page.goto(doi_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        # Detectar redirección a bot-checker
        current_url = page.url
        if any(kw in current_url for kw in ("robot", "captcha", "parktons", "challenge")):
            page.close()
            return {"success": False, "pdf_path": None, "source": "annas_archive",
                    "reason": "bot_check"}

        # Detectar 404
        page_title = page.title().lower()
        if "404" in page_title or "not found" in page_title:
            page.close()
            return {"success": False, "pdf_path": None, "source": "annas_archive",
                    "reason": "No encontrado en Anna's Archive"}

        pdf_url = _find_download_link(page)
        page.close()

        if not pdf_url:
            return {"success": False, "pdf_path": None, "source": "annas_archive",
                    "reason": "No se encontró enlace de descarga PDF"}

        filename = sanitize_filename(title or doi) + ".pdf"
        pdf_path = save_pdf(pdf_url, dest_dir / filename)

        if pdf_path:
            log(f"  ✅ Anna's Archive: {filename}")
            return {"success": True, "pdf_path": str(pdf_path), "source": "annas_archive"}

        return {"success": False, "pdf_path": None, "source": "annas_archive",
                "reason": "Fallo al descargar el PDF"}

    except Exception as e:
        log(f"  Anna's Archive error: {e}")
        if page:
            try:
                page.close()
            except Exception:
                pass
        return {"success": False, "pdf_path": None, "source": "annas_archive",
                "reason": str(e)}


def _find_download_link(page) -> str | None:
    """
    Busca el enlace de descarga directa en la página actual.
    Si solo hay un link a la página del paper (md5), la visita y vuelve a buscar.
    """
    from urllib.parse import urlparse
    parsed = urlparse(page.url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    links = page.eval_on_selector_all("a[href]", "els => els.map(el => el.getAttribute('href'))")

    # 1) Enlace directo de descarga
    for href in links:
        if not href:
            continue
        if "/download/" in href or "/slow_download/" in href:
            return href if href.startswith("http") else base + href
        if href.lower().endswith(".pdf") and href.startswith("http"):
            return href

    # 2) Navegar a la página del paper individual (md5)
    paper_href = None
    for href in links:
        if href and re.search(r"/md5/[a-f0-9]+", href):
            paper_href = href if href.startswith("http") else base + href
            break

    if not paper_href:
        return None

    try:
        page.goto(paper_href, wait_until="domcontentloaded", timeout=20000)
        time.sleep(1)
        links2 = page.eval_on_selector_all("a[href]", "els => els.map(el => el.getAttribute('href'))")
        for href in links2:
            if not href:
                continue
            if "/download/" in href or "/slow_download/" in href:
                return href if href.startswith("http") else base + href
            if href.lower().endswith(".pdf") and href.startswith("http"):
                return href
    except Exception:
        pass

    return None


def _get_context():
    """Obtiene o crea el contexto Playwright reutilizable."""
    global _browser_context
    if _browser_context is not None:
        return _browser_context

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    _browser_context = context
    return context


def close():
    """Cierra el navegador al finalizar el proceso."""
    global _browser_context
    if _browser_context:
        try:
            _browser_context.browser.close()
        except Exception:
            pass
        _browser_context = None
