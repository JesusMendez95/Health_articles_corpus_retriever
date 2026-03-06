"""
Helper para guardar la sesión de Consensus.

Abre un navegador VISIBLE para que hagas login manualmente.
Las cookies se guardan en .consensus_cookies.json y se reutilizan
automáticamente en cada ejecución del retriever.

Uso:
    python save_consensus_session.py
"""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

COOKIES_FILE = Path(__file__).parent / ".consensus_cookies.json"


def main():
    print("Abriendo navegador para login en Consensus...")
    print("1. Inicia sesión normalmente en el navegador.")
    print("2. Una vez que estés dentro, vuelve aquí y presiona ENTER.\n")

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=False)  # Navegador visible
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()
    page.goto("https://consensus.app/sign-in/", wait_until="domcontentloaded")

    input("Presiona ENTER cuando hayas iniciado sesión en el navegador...")

    # Guardar cookies
    cookies = context.cookies()
    COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
    print(f"\n✅ Sesión guardada en {COOKIES_FILE} ({len(cookies)} cookies)")
    print("   El retriever las cargará automáticamente en las próximas ejecuciones.")

    browser.close()
    pw.stop()


if __name__ == "__main__":
    main()
