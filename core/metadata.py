"""
Enriquecimiento de metadatos vía MusicBrainz.

Flujo: limpiar el título de YouTube → buscar en MusicBrainz →
       escribir ID3 tags + renombrar el archivo.
Todas las operaciones son best-effort: nunca propagan excepciones al caller.
"""
import re
from pathlib import Path

import musicbrainzngs
from mutagen.id3 import ID3, TALB, TIT2, TPE1
from mutagen.mp3 import MP3

musicbrainzngs.set_useragent("bajamusica", "0.1", "")

# Cualquier paréntesis/corchete que contenga alguna de estas palabras clave
_JUNK_BRACKETS = re.compile(
    r'\s*[\(\[【][^\)\]】]*\b(?:official|lyrics?|letra|hd|4k|uhd|'
    r'remaster(?:ed)?|visualizer|clip\s+oficial|video\s+oficial|'
    r'audio\s+oficial|full\s+album|feat\.?|ft\.?)[^\)\]】]*[\)\]】]\s*',
    re.IGNORECASE,
)
_INLINE_FEAT = re.compile(r'\s+(?:feat\.?|ft\.?)\s+.+$', re.IGNORECASE)


def clean_title(title: str) -> str:
    t = _JUNK_BRACKETS.sub(' ', title)
    t = _INLINE_FEAT.sub('', t)
    return ' '.join(t.split())


def lookup(title: str, channel: str = "") -> dict | None:
    """
    Busca en MusicBrainz el mejor match para el título dado.
    Devuelve dict con 'artist', 'album', 'title', o None si no hay match útil.
    """
    clean = clean_title(title)
    queries = []
    if channel:
        queries.append(f'artist:"{channel}" AND recording:"{clean}"')
    queries.append(f'recording:"{clean}"')

    for q in queries:
        try:
            res = musicbrainzngs.search_recordings(query=q, limit=3)
            recs = res.get("recording-list", [])
            if not recs:
                continue
            rec = recs[0]
            artist = rec.get("artist-credit-phrase") or channel or ""
            releases = rec.get("release-list", [])
            album = releases[0].get("title", "") if releases else ""
            return {
                "artist": artist,
                "album":  album,
                "title":  rec.get("title") or clean,
            }
        except Exception:
            continue
    return None


def _safe(s: str) -> str:
    """Elimina caracteres inválidos en nombres de archivo."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', s).strip(" .")[:100]


def build_filename(meta: dict, scheme: str, suffix: str) -> str:
    artist = _safe(meta.get("artist", ""))
    album  = _safe(meta.get("album", ""))
    title  = _safe(meta.get("title", ""))

    if scheme == "artist_album_title" and artist and album:
        name = f"{artist} - {album} - {title}"
    elif scheme in ("artist_title", "artist_album_title") and artist:
        name = f"{artist} - {title}"
    else:
        name = title or "descarga"
    return f"{name}{suffix}"


def apply(filepath: Path, meta: dict, scheme: str, fmt: str) -> Path:
    """
    Escribe ID3 tags (solo MP3) y renombra el archivo según el esquema.
    Devuelve el path final (puede ser el mismo si no hubo cambios).
    """
    try:
        if fmt == "mp3":
            _write_id3(filepath, meta)
        new_name = build_filename(meta, scheme, filepath.suffix)
        new_path = filepath.parent / new_name
        if new_path != filepath and not new_path.exists():
            filepath.rename(new_path)
            return new_path
    except Exception:
        pass
    return filepath


def _write_id3(filepath: Path, meta: dict) -> None:
    audio = MP3(str(filepath), ID3=ID3)
    try:
        audio.add_tags()
    except Exception:
        pass
    if meta.get("title"):
        audio.tags["TIT2"] = TIT2(encoding=3, text=meta["title"])
    if meta.get("artist"):
        audio.tags["TPE1"] = TPE1(encoding=3, text=meta["artist"])
    if meta.get("album"):
        audio.tags["TALB"] = TALB(encoding=3, text=meta["album"])
    audio.save()
