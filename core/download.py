"""
Descarga y conversión con yt-dlp + ffmpeg.

Recibe config por parámetro (no importa config directamente) para mantener este
módulo desacoplado y testeable. La app web le inyecta las rutas y mapas de calidad.
"""
import os
from pathlib import Path

import yt_dlp

import config
from . import jobs, metadata


def _make_progress_hook(job_id: str, video_id: str):
    """Crea el hook que yt-dlp llama durante la descarga para reportar avance."""
    def hook(d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            pct = int(downloaded * 100 / total) if total else 0
            # tope en 99: el 100 lo marcamos al terminar la conversión.
            # Pasamos speed/eta/bytes para que la UI muestre progreso rico.
            jobs.update_item(
                job_id, video_id,
                state="downloading",
                percent=min(pct, 99),
                speed=d.get("speed"),          # bytes/s (o None si no se conoce)
                eta=d.get("eta"),              # segundos restantes (o None)
                downloaded=downloaded,
                total=total,
            )
        elif status == "finished":
            # bajó el archivo; ahora ffmpeg lo convierte
            jobs.update_item(
                job_id, video_id,
                state="converting", percent=99,
                speed=None, eta=None,
            )
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

    if config.FFMPEG_LOCATION:
        opts["ffmpeg_location"] = config.FFMPEG_LOCATION

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
    en el registro `jobs` a medida que avanza. Cierra SIEMPRE el job al final
    (incluso ante un fallo inesperado), si no la UI quedaría polleando para
    siempre.
    """
    download_dir = str(download_dir)
    try:
        os.makedirs(download_dir, exist_ok=True)
    except OSError as exc:
        # Carpeta destino inválida o sin permisos: marcar todo como error y
        # cerrar el job. Si no, set_overall("done") nunca correría.
        for item in items:
            jobs.update_item(
                job_id, item.get("id", ""),
                state="error", percent=0, speed=None, eta=None,
                error=f"No se pudo crear la carpeta destino: {exc}"[:200],
            )
        jobs.set_overall(job_id, "done")
        return

    try:
        for item in items:
            vid = item.get("id")
            if not vid:
                continue
            url = item.get("url") or f"https://www.youtube.com/watch?v={vid}"
            hook = _make_progress_hook(job_id, vid)
            opts = _build_opts(fmt, quality, download_dir, audio_map, video_map, hook)

            try:
                jobs.update_item(job_id, vid, state="downloading", percent=0)
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)

                final_path = _get_filepath(info)
                if naming != "youtube" and final_path and final_path.exists():
                    jobs.update_item(job_id, vid, state="tagging", percent=99)
                    meta = metadata.lookup(
                        item.get("title", ""),
                        item.get("channel", ""),
                    )
                    if meta:
                        # apply() puede renombrar: nos quedamos con el path final.
                        final_path = metadata.apply(final_path, meta, naming, fmt)

                jobs.update_item(
                    job_id, vid,
                    state="done", percent=100,
                    speed=None, eta=None,
                    filename=final_path.name if final_path else None,
                )
            except Exception as exc:  # noqa: BLE001 — capturamos cualquier fallo del item
                jobs.update_item(
                    job_id, vid,
                    state="error", percent=0, speed=None, eta=None,
                    error=str(exc)[:200],
                )
    finally:
        # Pase lo que pase, cerramos el job para que la UI no quede colgada.
        jobs.set_overall(job_id, "done")


def _get_filepath(info: dict | None) -> Path | None:
    """Extrae el path del archivo final a partir del info dict de yt-dlp."""
    if not info:
        return None
    rdls = info.get("requested_downloads") or []
    if rdls and rdls[0].get("filepath"):
        return Path(rdls[0]["filepath"])
    return None
