# Article Retriever — 3-Source Cascade

Script para descargar automáticamente PDFs de artículos científicos desde Sci-Hub, usando los DOIs de los archivos CSV de Consensus.

## Datos

| Archivo CSV | Artículos |
|---|---|
| Mindfulness_consensus.csv | ~379 |
| Psychology_consensus.csv | ~343 |
| Neuropsichology_consensus.csv | ~319 |
| Psichiatry_consensus.csv | ~257 |
| Neuroscience_consensus.csv | ~240 |
| somathic_psychology_consensus.csv | ~214 |
| Neuropsychiatry_consensus.csv | ~142 |
| functional_medicine_consensus.csv | ~66 |
| Psychoanalytic_consensus.csv | ~56 |
| epigenetic_consensus.csv | ~50 |
| **Total** | **~2,066** |

> [!WARNING]
> Sci-Hub no ha agregado artículos nuevos desde 2021. Artículos publicados después de esa fecha probablemente **no estarán disponibles**.

## Flujo en cascada por DOI

```
DOI
 └─ 1️⃣ Unpaywall API  →  PDF descargado  ✅
     └─ 2️⃣ Anna's Archive  →  PDF descargado  ✅
         └─ 3️⃣ Consensus (Playwright + login Pro)
               → Title + Abstract + Study Snapshot → results.csv
```

## Proposed Changes

### Configuración

#### [NEW] [config.py](file:///home/vincent/Documents/Programming/Arcicles_sci-hub_retriever/config.py)
Email para Unpaywall API y credenciales de Consensus (leídos desde variables de entorno o `.env`).

### Módulos fuente

#### [NEW] [sources/unpaywall.py](file:///home/vincent/Documents/Programming/Arcicles_sci-hub_retriever/sources/unpaywall.py)
Llama a `https://api.unpaywall.org/v2/{DOI}?email=...`, extrae la URL del PDF open access y lo descarga.

#### [NEW] [sources/annas_archive.py](file:///home/vincent/Documents/Programming/Arcicles_sci-hub_retriever/sources/annas_archive.py)
Scraping de `https://annas-archive.org/doi/{DOI}` con requests+BeautifulSoup para encontrar el enlace de descarga directa del PDF.

#### [NEW] [sources/consensus.py](file:///home/vincent/Documents/Programming/Arcicles_sci-hub_retriever/sources/consensus.py)
Playwright (navegador headless) que inicia sesión con cuenta Pro del usuario, visita cada `Consensus Link` del CSV, y extrae: **Study Snapshot**, confirmando que Title y Abstract ya están en el CSV.

### Script principal

#### [NEW] [retriever.py](file:///home/vincent/Documents/Programming/Arcicles_sci-hub_retriever/retriever.py)
Orquestador que:
1. Lee todos los `*_consensus.csv`
2. Para cada artículo corre la cascada de 3 fuentes
3. Guarda PDFs en `downloads/<topic>/`
4. Genera `results.csv` final con columnas: `Title, Authors, Year, DOI, Abstract, Study_Snapshot, PDF_Path, Source, Status`
5. Reanudable (salta artículos ya procesados)
6. Rate limiting con delays aleatorios entre requests

### Dependencias

- `requests` ✅ (ya instalado)
- `beautifulsoup4` ✅ (ya instalado)
- `playwright` ❌ (instalar: `pip install playwright && playwright install chromium`)
- `python-dotenv` ❌ (instalar: `pip install python-dotenv`)

## Verification Plan

### Prueba rápida con 3 artículos
```bash
python3 scihub_retriever.py --limit 3 --csv epigenetic_consensus.csv
```
Esto procesará solo 3 artículos del CSV más pequeño para verificar que:
- La lectura del CSV funciona
- El scraping de Sci-Hub encuentra el enlace al PDF
- El PDF se descarga y guarda correctamente
- El reporte se genera

### Verificación manual
- Abrir uno de los PDFs descargados para confirmar que no está corrupto
- Revisar que la estructura de carpetas sea correcta
