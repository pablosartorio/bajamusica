"""
Chequeo de frescura de yt-dlp contra PyPI.

yt-dlp necesita actualizaciones frecuentes para seguir funcionando con YouTube;
en el .exe empaquetado queda congelado y con el tiempo las descargas empiezan a
fallar con errores crípticos. Este módulo compara la versión local con la última
publicada y avisa si la local quedó vieja.

Todo es best-effort: sin red (o con PyPI caído) se responde "no desactualizado"
y la app sigue normal.
"""
import json
import logging
import threading
import urllib.request
from datetime import date

from yt_dlp.version import __version__ as YTDLP_VERSION

logger = logging.getLogger(__name__)

PYPI_URL = "https://pypi.org/pypi/yt-dlp/json"
STALE_DAYS = 60   # margen: yt-dlp publica seguido, no molestar por cada release

_cache: dict | None = None
_cache_lock = threading.Lock()


def _parse_version_date(version: str) -> date | None:
    """Las versiones de yt-dlp son fechas: '2025.06.09' → date(2025, 6, 9)."""
    parts = version.split(".")[:3]
    try:
        y, m, d = (int(p) for p in parts)
        return date(y, m, d)
    except (ValueError, TypeError):
        return None


def is_outdated(current: str, latest: str, stale_days: int = STALE_DAYS) -> bool:
    """
    True si `current` quedó vieja respecto de `latest`.

    Con versiones-fecha (el caso normal) exige una diferencia mayor a
    `stale_days` para no molestar por cada release. Si alguna no parsea como
    fecha, cae a comparación de tuplas numéricas.
    """
    cur_date, lat_date = _parse_version_date(current), _parse_version_date(latest)
    if cur_date and lat_date:
        return (lat_date - cur_date).days > stale_days

    def as_tuple(v: str) -> tuple:
        return tuple(int(p) for p in v.split(".") if p.isdigit())

    try:
        return as_tuple(latest) > as_tuple(current)
    except ValueError:
        return False


def _fetch_latest(timeout: float) -> str | None:
    try:
        with urllib.request.urlopen(PYPI_URL, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("info", {}).get("version")
    except Exception as exc:  # noqa: BLE001 — sin red no es un error de la app
        logger.info("No se pudo consultar PyPI por yt-dlp: %s", exc)
        return None


def check(timeout: float = 5.0) -> dict:
    """
    Devuelve {"current", "latest", "outdated"}. El resultado se cachea para
    todo el proceso: una consulta a PyPI por sesión alcanza.
    """
    global _cache
    with _cache_lock:
        if _cache is not None:
            return _cache
        latest = _fetch_latest(timeout)
        _cache = {
            "current": YTDLP_VERSION,
            "latest": latest,
            "outdated": bool(latest and is_outdated(YTDLP_VERSION, latest)),
        }
        if _cache["outdated"]:
            logger.warning(
                "yt-dlp desactualizado: local %s, última %s", YTDLP_VERSION, latest,
            )
        return _cache
