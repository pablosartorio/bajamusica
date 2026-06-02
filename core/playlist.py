"""Expansión de playlists de YouTube usando yt-dlp."""
import yt_dlp

from .util import format_duration


def expand(url: str) -> tuple[str, list[dict]]:
    """
    Expande una URL de playlist de YouTube.
    Devuelve (título_playlist, lista_de_entradas).
    Cada entrada tiene: id, title, channel, duration, thumbnail, url.
    """
    opts = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    playlist_title = info.get("title") or "Playlist"
    entries = info.get("entries") or []

    results = []
    for entry in entries:
        if not entry:
            continue
        vid_id = entry.get("id", "")
        if not vid_id:
            continue
        thumbnail = entry.get("thumbnail") or f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
        results.append({
            "id": vid_id,
            "title": entry.get("title") or "(sin título)",
            "channel": entry.get("uploader") or entry.get("channel") or "",
            "duration": format_duration(entry.get("duration")),
            "thumbnail": thumbnail,
            "url": f"https://www.youtube.com/watch?v={vid_id}",
        })

    return playlist_title, results
