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
MAX_SEARCH_RESULTS = 30

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

# Ubicación de ffmpeg dentro del bundle.
# OJO: PyInstaller >= 6.0 (onedir) deja los binarios en la subcarpeta `_internal`
# (expuesta como sys._MEIPASS), NO junto al .exe. Probamos las ubicaciones
# posibles y devolvemos la primera donde ffmpeg realmente exista, así el bundle
# funciona con cualquier versión/layout de PyInstaller.
def _find_ffmpeg_location():
    if not getattr(sys, 'frozen', False):
        return None  # desarrollo: usar el ffmpeg del PATH del sistema
    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    exe_dir = Path(sys.executable).parent
    candidates = [
        Path(getattr(sys, '_MEIPASS', exe_dir)),  # _internal (onedir 6.x) / temp (onefile) / exe dir (5.x)
        exe_dir,                                   # layout plano antiguo
        exe_dir / "_internal",                     # por las dudas
    ]
    for d in candidates:
        if (d / exe_name).is_file():
            return str(d)
    return str(candidates[0])  # no se encontró: mejor candidato (yt-dlp avisará)


FFMPEG_LOCATION = _find_ffmpeg_location()
