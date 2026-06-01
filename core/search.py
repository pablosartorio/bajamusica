"""
Búsqueda en YouTube usando yt-dlp.

Usa extracción "flat" (no resuelve el stream completo de cada video, solo los
metadatos del listado) para que la búsqueda sea rápida. La descarga real recién
resuelve el stream cuando el usuario elige qué bajar.
"""
import yt_dlp

from .util import format_duration


def search(query: str, max_results: int = 12) -> list[dict]:
    """
    Busca `query` en YouTube y devuelve una lista de resultados.

    Cada resultado es un dict con: id, title, channel, duration, thumbnail, url.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,   # solo metadatos del listado, no resuelve streams
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)

    results = []
    for entry in info.get("entries", []):
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
            # La miniatura se arma desde el id: confiable y no depende del flat extract
            "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "url": f"https://www.youtube.com/watch?v={vid}",
        })

    return results
