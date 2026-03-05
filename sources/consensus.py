"""
Consensus source: usa Playwright para iniciar sesión con cuenta Pro y extraer
el Study Snapshot de cada artículo cuando no se pudo descargar el PDF.
"""
import time
import config
from utils import log

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


_browser_context = None  # Contexto reutilizable entre llamadas


def get_study_snapshot(consensus_url: str) -> dict:
    """
    Visita la página del artículo en Consensus (con sesión Pro activa)
    y extrae el Study Snapshot.

    Returns:
        dict con: success (bool), study_snapshot (str|None), reason (str)
    """
    if not PLAYWRIGHT_AVAILABLE:
        return {"success": False, "study_snapshot": None,
                "reason": "playwright no instalado"}

    if not config.CONSENSUS_EMAIL or not config.CONSENSUS_PASSWORD:
        return {"success": False, "study_snapshot": None,
                "reason": "Credenciales de Consensus no configuradas"}

    if not consensus_url:
        return {"success": False, "study_snapshot": None,
                "reason": "URL de Consensus vacía"}

    try:
        context = _get_context()
        page = context.new_page()
        page.goto(consensus_url, wait_until="domcontentloaded", timeout=30000)

        # Esperar a que cargue el contenido principal
        try:
            page.wait_for_selector("[data-testid='study-snapshot'], .study-snapshot, "
                                   "[class*='StudySnapshot'], [class*='study_snapshot']",
                                   timeout=10000)
        except PwTimeout:
            # Intentar selector más genérico si el anterior no funciona
            pass

        snapshot = _extract_snapshot(page)
        page.close()

        if snapshot:
            return {"success": True, "study_snapshot": snapshot}
        else:
            return {"success": False, "study_snapshot": None,
                    "reason": "Study Snapshot no encontrado en la página"}

    except Exception as e:
        log(f"  Consensus error: {e}")
        return {"success": False, "study_snapshot": None, "reason": str(e)}


def _extract_snapshot(page) -> str | None:
    """Intenta extraer el Study Snapshot probando varios selectores."""
    # Selectores conocidos de Consensus (pueden variar con updates del sitio)
    selectors = [
        "[data-testid='study-snapshot']",
        "[class*='StudySnapshot']",
        "[class*='study-snapshot']",
        "[class*='study_snapshot']",
        "section:has(h2:text('Study Snapshot'))",
        "div:has(> h3:text-is('Study Snapshot'))",
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

    # Fallback: buscar texto que contenga encabezado "Study Snapshot"
    try:
        result = page.evaluate("""
            () => {
                const headers = [...document.querySelectorAll('h1,h2,h3,h4,strong')];
                const header = headers.find(h => h.textContent.trim().toLowerCase().includes('study snapshot'));
                if (!header) return null;
                const parent = header.closest('section, div[class], article') || header.parentElement;
                return parent ? parent.innerText.trim() : null;
            }
        """)
        if result and len(result) > 20:
            return result
    except Exception:
        pass

    return None


def _get_context():
    """Obtiene o crea el contexto del navegador con sesión iniciada."""
    global _browser_context

    if _browser_context is not None:
        return _browser_context

    # Iniciar navegador y hacer login
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    )

    _login(context)
    _browser_context = context
    return context


def _login(context):
    """Inicia sesión en Consensus con las credenciales del .env."""
    page = context.new_page()
    log("  🔐 Iniciando sesión en Consensus...")

    try:
        page.goto("https://consensus.app/home/", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        # Intentar hacer click en botón de login
        login_selectors = [
            "a[href*='login']", "button:text('Log in')", "button:text('Sign in')",
            "[data-testid='login-button']"
        ]
        for sel in login_selectors:
            try:
                page.click(sel, timeout=3000)
                break
            except Exception:
                continue

        time.sleep(2)

        # Rellenar email y contraseña
        page.fill("input[type='email'], input[name='email']", config.CONSENSUS_EMAIL)
        page.fill("input[type='password'], input[name='password']", config.CONSENSUS_PASSWORD)

        # Submit
        page.press("input[type='password']", "Enter")
        time.sleep(3)

        log("  ✅ Sesión iniciada en Consensus")

    except Exception as e:
        log(f"  ⚠️  Error al iniciar sesión en Consensus: {e}")
    finally:
        page.close()


def close():
    """Cierra el navegador al finalizar."""
    global _browser_context
    if _browser_context:
        try:
            _browser_context.browser.close()
        except Exception:
            pass
        _browser_context = None
