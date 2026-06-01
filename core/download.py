"""
Descarga y conversión con yt-dlp + ffmpeg.

Recibe config por parámetro (no importa config directamente) para mantener este
módulo desacoplado y testeable. La app web le inyecta las rutas y mapas de calidad.
"""
import os
from pathlib import Path

import yt_dlp

from . import jobs, metadata


def _make_progress_hook(job_id: str, video_id: str):
    """Crea el hook que yt-dlp llama durante la descarga para reportar avance."""
    def hook(d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            pct = int(downloaded * 100 / total) if total else 0
            # tope en 99: el 100 lo marcamos al terminar la conversión
            jobs.update_item(job_id, video_id, state="downloading", percent=min(pct, 99))
        elif status == "finished":
            # bajó el archivo; ahora ffmpeg lo convierte
            jobs.update_item(job_id, video_id, state="converting", percent=99)
    return hook


def _build_opts(fmt, quality, download_dir, audio_map, video_map, hook):
    """Arma el dict de opciones de yt-dlp según formato y calidad pedidos."""
    opts = {
        "outtmpl": os.path.join(download_dir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "progress_hooks": [hook],
        "ignoreerrors": False,
    }

    if fmt == "mp3":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": audio_map.get(quality, "192"),
        }]
    else:  # mp4
        max_h = video_map.get(quality, 720)
        opts["format"] = (
            f"bestvideo[height<={max_h}]+bestaudio/"
            f"best[height<={max_h}]/best"
        )
        opts["merge_output_format"] = "mp4"

    return opts


def run_job(job_id, items, fmt, quality, download_dir, audio_map, video_map, naming="youtube"):
    """
    Procesa todos los items de una tarea, secuencialmente.

    Pensado para correr en un thread aparte. Actualiza el estado de cada item
    en el registro `jobs` a medida que avanza.
    """
    download_dir = str(download_dir)
    os.makedirs(download_dir, exist_ok=True)

    for item in items:
        vid = item["id"]
        url = item.get("url") or f"https://www.youtube.com/watch?v={vid}"
        hook = _make_progress_hook(job_id, vid)
        opts = _build_opts(fmt, quality, download_dir, audio_map, video_map, hook)

        try:
            jobs.update_item(job_id, vid, state="downloading", percent=0)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

            if naming != "youtube":
                jobs.update_item(job_id, vid, state="tagging", percent=99)
                filepath = _get_filepath(info)
                if filepath and filepath.exists():
                    meta = metadata.lookup(
                        item.get("title", ""),
                        item.get("channel", ""),
                    )
                    if meta:
                        metadata.apply(filepath, meta, naming, fmt)

            jobs.update_item(job_id, vid, state="done", percent=100)
        except Exception as exc:  # noqa: BLE001 — queremos capturar cualquier fallo del item
            jobs.update_item(
                job_id, vid,
                state="error", percent=0, error=str(exc)[:200],
            )

    jobs.set_overall(job_id, "done")


def _get_filepath(info: dict | None) -> Path | None:
    """Extrae el path del archivo final a partir del info dict de yt-dlp."""
    if not info:
        return None
    rdls = info.get("requested_downloads") or []
    if rdls and rdls[0].get("filepath"):
        return Path(rdls[0]["filepath"])
    return None
