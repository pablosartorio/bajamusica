"""
Registro del estado de cada tarea de descarga.

Una "tarea" (job) agrupa todos los items que el usuario eligió bajar de una vez.
Cada item tiene su propio estado y porcentaje.

Thread-safe vía un lock simple.
"""
import copy
import json
import threading
import time
import uuid

import config

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def create_job(
    items: list[dict],
    fmt: str = "mp3",
    dest_dir: str = "",
    naming: str = "youtube",
) -> str:
    """Crea una tarea con los items dados y devuelve su job_id."""
    job_id = uuid.uuid4().hex[:12]
    with _lock:
        _purge_old_jobs()
        _jobs[job_id] = {
            "id": job_id,
            "created": time.time(),
            "finished": None,
            "format": fmt,
            "dest_dir": dest_dir,
            "naming": naming,
            "overall": "running",
            "cancelled": False,
            "items": [
                {
                    "id": it["id"],
                    "title": it.get("title", ""),
                    "percent": 0,
                    "state": "queued",
                    "error": None,
                    "speed": None,       # bytes/s mientras baja
                    "eta": None,         # segundos restantes
                    "downloaded": 0,     # bytes bajados
                    "total": None,       # bytes totales (si yt-dlp los conoce)
                    "filename": None,    # nombre final del archivo guardado
                }
                for it in items
            ],
        }
    return job_id


def _purge_old_jobs() -> None:
    """Elimina jobs terminados hace rato; sin esto _jobs crece sin límite.

    Debe llamarse con _lock ya tomado.
    """
    cutoff = time.time() - config.JOB_RETENTION_SECONDS
    stale = [
        jid for jid, job in _jobs.items()
        if job["overall"] == "done" and (job.get("finished") or 0) < cutoff
    ]
    for jid in stale:
        del _jobs[jid]


def get_job(job_id: str) -> dict | None:
    """Devuelve una copia profunda del job (segura para serializar a JSON)."""
    with _lock:
        job = _jobs.get(job_id)
        return copy.deepcopy(job) if job else None


def cancel_job(job_id: str) -> bool:
    """Marca el job para cancelación. Devuelve False si el job no existe o ya terminó."""
    with _lock:
        job = _jobs.get(job_id)
        if not job or job["overall"] == "done":
            return False
        job["cancelled"] = True
        return True


def is_cancelled(job_id: str) -> bool:
    """Consulta liviana del flag de cancelación (la usa el progress hook de yt-dlp)."""
    with _lock:
        job = _jobs.get(job_id)
        return bool(job and job.get("cancelled"))


def update_item(job_id: str, video_id: str, **fields) -> None:
    """Actualiza campos de un item dentro de un job."""
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        for item in job["items"]:
            if item["id"] == video_id:
                item.update(fields)
                break


def set_overall(job_id: str, status: str) -> None:
    """Marca el estado global del job; si termina, persiste en el historial."""
    job_snapshot = None
    with _lock:
        if job_id not in _jobs:
            return
        _jobs[job_id]["overall"] = status
        if status == "done":
            _jobs[job_id]["finished"] = time.time()
            job_snapshot = copy.deepcopy(_jobs[job_id])

    if job_snapshot is not None:
        _save_to_history(job_snapshot)


def load_history() -> list[dict]:
    """Carga el historial desde disco; devuelve [] si no existe o hay error."""
    path = config.HISTORY_FILE
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            # Defensa ante un history.json corrupto/manipulado: solo devolvemos
            # una lista, si no el frontend (y _save_to_history) podrían romperse.
            if isinstance(data, list):
                return data
    except Exception:  # noqa: BLE001
        pass
    return []


def _save_to_history(job: dict) -> None:
    """Añade el job completado al historial en disco (falla en silencio)."""
    path = config.HISTORY_FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        history = load_history()
        entry = {
            "id": job["id"],
            "created": job["created"],
            "format": job.get("format", "mp3"),
            "dest_dir": job.get("dest_dir", ""),
            "naming": job.get("naming", "youtube"),
            "items": [
                {
                    "id": it["id"],
                    "title": it["title"],
                    "state": it["state"],
                    "error": it.get("error"),
                    "filename": it.get("filename"),
                }
                for it in job["items"]
            ],
        }
        history.insert(0, entry)
        path.write_text(
            json.dumps(history[:500], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:  # noqa: BLE001
        pass


def downloaded_index() -> dict[str, float]:
    """
    Mapa video_id → timestamp de la descarga exitosa más reciente, según el
    historial. Lo usa la búsqueda para marcar "ya lo bajaste" en los resultados.
    """
    index: dict[str, float] = {}
    for entry in load_history():
        created = entry.get("created")
        if not isinstance(created, (int, float)):
            continue
        for item in entry.get("items", []):
            if not isinstance(item, dict) or item.get("state") != "done":
                continue
            vid = item.get("id")
            # El historial está ordenado del más nuevo al más viejo: la primera
            # aparición de cada id es la descarga más reciente.
            if vid and vid not in index:
                index[vid] = created
    return index
