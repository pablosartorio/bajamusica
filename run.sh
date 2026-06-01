#!/usr/bin/env bash
# Lanzador de Sonido. Crea el entorno virtual la primera vez, instala
# dependencias y arranca el servidor (que abre el navegador solo).
set -e
cd "$(dirname "$0")"

# ── Entorno virtual ─────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "Creando entorno virtual (solo la primera vez)..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Verificando dependencias..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# ── Chequeo de ffmpeg ───────────────────────────────────────
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo ""
    echo "  ffmpeg no está instalado. La conversión a MP3/MP4 no va a funcionar."
    echo "   Instalalo con:   sudo apt install ffmpeg"
    echo ""
fi

# ── Arrancar ────────────────────────────────────────────────
echo ""
echo "Iniciando Sonido en http://127.0.0.1:5000"
echo "(Ctrl+C para detener)"
echo ""
python app.py
