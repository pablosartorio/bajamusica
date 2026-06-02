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
        _jobs[job_id] = {
            "id": job_id,
            "created": time.time(),
            "format": fmt,
            "dest_dir": dest_dir,
            "naming": naming,
            "overall": "running",
            "items": [
                {
                    "id": it["id"],
                    "title": it.get("title", ""),
                    "percent": 0,
                    "state": "queued",
                    "error": None,
                }
                for it in items
            ],
        }
    return job_id


def get_job(job_id: str) -> dict | None:
    """Devuelve una copia profunda del job (segura para serializar a JSON)."""
    with _lock:
        job = _jobs.get(job_id)
        return copy.deepcopy(job) if job else None


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
            job_snapshot = copy.deepcopy(_jobs[job_id])

    if job_snapshot is not None:
        _save_to_history(job_snapshot)


def load_history() -> list[dict]:
    """Carga el historial desde disco; devuelve [] si no existe o hay error."""
    path = config.HISTORY_FILE
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
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
