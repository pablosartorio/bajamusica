#!/usr/bin/env bash
# Lanzador de Sonido. uv crea el entorno virtual e instala las dependencias
# (solo la primera vez) y arranca el servidor (que abre el navegador solo).
set -e
cd "$(dirname "$0")"

# ── uv ──────────────────────────────────────────────────────
if ! command -v uv >/dev/null 2>&1; then
    echo ""
    echo "  Falta uv (el gestor de entornos/paquetes de Python)."
    echo "   Instalalo con:   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "   y volvé a correr este script."
    echo ""
    exit 1
fi

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
uv run --no-dev python app.py
