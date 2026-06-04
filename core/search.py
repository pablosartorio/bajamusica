"""
Búsqueda en YouTube usando yt-dlp.

Usa extracción "flat" (no resuelve el stream completo de cada video, solo los
metadatos del listado) para que la búsqueda sea rápida. La descarga real recién
resuelve el stream cuando el usuario elige qué bajar.
"""
import re

import yt_dlp

from .util import format_duration

_YT_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def _is_youtube_url(query: str) -> bool:
    return bool(_YT_URL_RE.search(query))


def search(query: str, max_results: int = 12) -> list[dict]:
    """
    Busca `query` en YouTube y devuelve una lista de resultados.

    Si `query` es una URL de YouTube, resuelve ese video directamente.
    Cada resultado es un dict con: id, title, channel, duration, thumbnail, url.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        if _is_youtube_url(query):
            info = ydl.extract_info(query, download=False)
            entries = [info] if info else []
        else:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            entries = info.get("entries", [])

    results = []
    for entry in entries:
        if not entry:
            continue
        vid = entry.get("id")
        if not vid:
            continue
        results.append({
            "id": vid,
            "title": entry.get("title") or "(sin título)",
            "channel": entry.get("channel") or entry.get("uploader") or "",
            "duration": format_duration(entry.get("duration")),
            "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "url": f"https://www.youtube.com/watch?v={vid}",
        })

    return results
