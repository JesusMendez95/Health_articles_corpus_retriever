"""
Configuración central del Article Retriever.
Lee credenciales desde el archivo .env en el mismo directorio.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde el directorio del proyecto
load_dotenv(Path(__file__).parent / ".env")

# ── Unpaywall ────────────────────────────────────────────────────────────────
UNPAYWALL_EMAIL = os.getenv("UNPAYWALL_EMAIL", "")

# ── Consensus ────────────────────────────────────────────────────────────────
CONSENSUS_EMAIL    = os.getenv("CONSENSUS_EMAIL", "")
CONSENSUS_PASSWORD = os.getenv("CONSENSUS_PASSWORD", "")

# ── Directorios ───────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
RESULTS_CSV   = BASE_DIR / "results.csv"

# ── Rate limiting ─────────────────────────────────────────────────────────────
# Delay aleatorio entre requests (segundos)
DELAY_MIN = 3
DELAY_MAX = 8

# Número de reintentos por fuente
MAX_RETRIES = 3

# Timeout para requests HTTP (segundos)
HTTP_TIMEOUT = 30

# ── Validación ────────────────────────────────────────────────────────────────
def validate():
    """Verifica que las credenciales requeridas estén configuradas."""
    missing = []
    if not UNPAYWALL_EMAIL:
        missing.append("UNPAYWALL_EMAIL")
    if not CONSENSUS_EMAIL:
        missing.append("CONSENSUS_EMAIL")
    if not CONSENSUS_PASSWORD:
        missing.append("CONSENSUS_PASSWORD")
    if missing:
        print(f"⚠️  Variables de entorno faltantes en .env: {', '.join(missing)}")
        print("   Algunas fuentes no estarán disponibles.\n")
