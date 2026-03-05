"""
Utilidades compartidas: sanitización de nombres, descarga de PDFs,
logging con timestamp.
"""
import re
import time
import random
import logging
from pathlib import Path
from datetime import datetime

import requests
import config


# ── Logger ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("retriever.log", encoding="utf-8"),
    ]
)
_logger = logging.getLogger(__name__)


def log(msg: str):
    """Log a message with timestamp."""
    _logger.info(msg)


# ── Nombres de archivo ────────────────────────────────────────────────────────
def sanitize_filename(name: str, max_len: int = 120) -> str:
    """
    Convierte un título en un nombre de archivo seguro.
    - Elimina caracteres especiales
    - Limita la longitud
    - Reemplaza espacios con guiones bajos
    """
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    name = re.sub(r"\s+", "_", name.strip())
    name = re.sub(r"_+", "_", name)
    return name[:max_len]


# ── Descarga de PDFs ──────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}


def save_pdf(url: str, dest_path: Path, headers: dict = None) -> Path | None:
    """
    Descarga un PDF desde `url` y lo guarda en `dest_path`.

    Returns:
        Path del archivo guardado, o None si falló.
    """
    if dest_path.exists() and dest_path.stat().st_size > 1000:
        return dest_path  # ya existe y no está vacío

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    h = {**HEADERS, **(headers or {})}

    try:
        resp = requests.get(url, headers=h, timeout=config.HTTP_TIMEOUT,
                            stream=True, allow_redirects=True)

        if resp.status_code != 200:
            return None

        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type and not url.lower().endswith(".pdf"):
            # Verificar si los primeros bytes son un PDF
            first_bytes = b""
            for chunk in resp.iter_content(1024):
                first_bytes = chunk
                break
            if not first_bytes.startswith(b"%PDF"):
                return None
            # Si es PDF, guardar completo
            with open(dest_path, "wb") as f:
                f.write(first_bytes)
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
        else:
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)

        # Verificar que el archivo no esté vacío y sea un PDF válido
        if dest_path.stat().st_size < 1000:
            dest_path.unlink(missing_ok=True)
            return None

        return dest_path

    except Exception as e:
        log(f"  Error al descargar PDF: {e}")
        dest_path.unlink(missing_ok=True)
        return None


def random_delay():
    """Espera un tiempo aleatorio entre requests para evitar bloqueos."""
    delay = random.uniform(config.DELAY_MIN, config.DELAY_MAX)
    time.sleep(delay)


# ── Progreso simple ───────────────────────────────────────────────────────────
def print_progress(current: int, total: int, topic: str, status: str = ""):
    """Imprime una línea de progreso simple."""
    pct = (current / total * 100) if total else 0
    bar_len = 30
    filled = int(bar_len * current / total) if total else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"\r  [{bar}] {current}/{total} ({pct:.0f}%) {status[:40]:<40}", end="", flush=True)
