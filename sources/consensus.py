"""
Consensus source: extrae Title, Abstract y Study Snapshot de artículos.

Se conecta al Chrome real del usuario vía CDP (Chrome DevTools Protocol),
abre una pestaña nueva, navega a la URL del artículo en Consensus y
extrae el contenido. El resultado se guarda en un .txt.

Requisito único: Chrome debe estar corriendo con remote debugging:
    ./start_chrome_debug.sh
"""
import time
from pathlib import Path
from utils import sanitize_filename, log

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

CDP_URL = "http://localhost:9222"


def get_study_snapshot(consensus_url: str, title: str, abstract: str, dest_dir: Path) -> dict:
    """
    Abre una pestaña en el Chrome del usuario, navega a la URL de Consensus
    y extrae el Study Snapshot. Guarda título + abstract + snapshot en un .txt.

    Returns:
        dict con: success (bool), txt_path (str|None), study_snapshot (str|None), reason (str)
    """
    if not PLAYWRIGHT_AVAILABLE:
        return _fail("playwright no instalado")

    if not consensus_url:
        return _fail("URL de Consensus vacía")

    page = None
    pw = None
    browser = None

    try:
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(CDP_URL)
    except Exception as e:
        if pw:
            try:
                pw.stop()
            except Exception:
                pass
        return _fail(f"Chrome no disponible en {CDP_URL}. Ejecuta ./start_chrome_debug.sh  ({e})")

    try:
        # Usar el primer contexto del Chrome real (ya tiene la sesión activa)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        page.goto(consensus_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # Esperar a que cargue el contenido del artículo
        try:
            page.wait_for_selector(
                "[data-testid='study-snapshot'], [class*='StudySnapshot'], "
                "[class*='study-snapshot'], [class*='study_snapshot']",
                timeout=12000,
            )
        except PwTimeout:
            pass

        snapshot = _extract_snapshot(page)
        page_title = _extract_title(page) or title
        page_abstract = _extract_abstract(page) or abstract

        page.close()

        if not snapshot:
            return _fail("Study Snapshot no encontrado en la página de Consensus")

        txt_path = _write_txt(page_title, page_abstract, snapshot, dest_dir, title)
        log(f"  ✅ Consensus snapshot: {txt_path.name}")
        return {
            "success": True,
            "txt_path": str(txt_path),
            "study_snapshot": snapshot,
            "reason": "",
        }

    except Exception as e:
        log(f"  Consensus error: {e}")
        if page:
            try:
                page.close()
            except Exception:
                pass
        return _fail(str(e))
    finally:
        try:
            browser.close()
        except Exception:
            pass
        try:
            pw.stop()
        except Exception:
            pass


# ── Extracción de contenido ────────────────────────────────────────────────────

def _extract_snapshot(page) -> str | None:
    selectors = [
        "[data-testid='study-snapshot']",
        "[class*='StudySnapshot']",
        "[class*='study-snapshot']",
        "[class*='study_snapshot']",
    ]
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if text and len(text) > 20:
                    return text
        except Exception:
            continue

    # Fallback: buscar por encabezado "Study Snapshot"
    try:
        result = page.evaluate("""
            () => {
                const headers = [...document.querySelectorAll('h1,h2,h3,h4,strong')];
                const header = headers.find(h =>
                    h.textContent.trim().toLowerCase().includes('study snapshot'));
                if (!header) return null;
                const parent = header.closest('section, div[class], article')
                             || header.parentElement;
                return parent ? parent.innerText.trim() : null;
            }
        """)
        if result and len(result) > 20:
            return result
    except Exception:
        pass
    return None


def _extract_title(page) -> str | None:
    try:
        el = page.query_selector("h1, [class*='title'], [data-testid='paper-title']")
        if el:
            t = el.inner_text().strip()
            if t and len(t) > 5:
                return t
    except Exception:
        pass
    return None


def _extract_abstract(page) -> str | None:
    try:
        result = page.evaluate("""
            () => {
                const headers = [...document.querySelectorAll('h2,h3,h4,strong')];
                const h = headers.find(el =>
                    el.textContent.trim().toLowerCase() === 'abstract');
                if (!h) return null;
                const parent = h.closest('section, div[class]') || h.parentElement;
                return parent ? parent.innerText.trim() : null;
            }
        """)
        if result and len(result) > 20:
            return result
    except Exception:
        pass
    return None


# ── Escritura del .txt ─────────────────────────────────────────────────────────

def _write_txt(title: str, abstract: str, snapshot: str, dest_dir: Path, fallback_name: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = sanitize_filename(title or fallback_name) + ".txt"
    path = dest_dir / filename
    content = f"TITLE\n{'='*60}\n{title}\n\n"
    if abstract:
        content += f"ABSTRACT\n{'='*60}\n{abstract}\n\n"
    content += f"STUDY SNAPSHOT\n{'='*60}\n{snapshot}\n"
    path.write_text(content, encoding="utf-8")
    return path


def _fail(reason: str) -> dict:
    return {"success": False, "txt_path": None, "study_snapshot": None, "reason": reason}


def close():
    """Sin-op: ya no mantenemos un browser persistente."""
    pass
