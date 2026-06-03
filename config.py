"""
Configuración central de la aplicación.
Todo lo ajustable vive acá: carpeta destino, puerto, calidades, límites.
"""
import os
import sys
from pathlib import Path

# ── Servidor ──────────────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 5000
OPEN_BROWSER = True          # abrir el navegador automáticamente al arrancar

# ── Descargas ─────────────────────────────────────────────────────────────
DOWNLOAD_DIR = Path.home() / "Music" / "YT-Downloads"
MAX_SEARCH_RESULTS = 12

# Mapa de calidad de audio (MP3) → bitrate en kbps
AUDIO_QUALITY = {
    "high": "320",
    "medium": "192",
    "low": "128",
}

# Mapa de calidad de video (MP4) → altura máxima en píxeles
VIDEO_QUALITY = {
    "high": 1080,
    "medium": 720,
    "low": 480,
}

# Formatos soportados (para validación y para futuras extensiones)
SUPPORTED_FORMATS = ("mp3", "mp4")

# Esquemas de nomenclatura para los archivos descargados
NAMING_SCHEMES = ("youtube", "artist_title", "artist_album_title")

# Historial de descargas completadas
if sys.platform == "win32":
    _appdata = Path(os.environ.get("APPDATA", Path.home()))
    HISTORY_FILE = _appdata / "bajamusica" / "history.json"
else:
    HISTORY_FILE = Path.home() / ".local" / "share" / "bajamusica" / "history.json"

# Ubicación de ffmpeg: en el bundle apunta a la carpeta del .exe donde está ffmpeg.exe
if getattr(sys, 'frozen', False):
    FFMPEG_LOCATION = str(Path(sys.executable).parent)
else:
    FFMPEG_LOCATION = None  # usar ffmpeg del PATH del sistema
