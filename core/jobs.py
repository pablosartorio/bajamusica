"""
Registro en memoria del estado de cada tarea de descarga.

Una "tarea" (job) agrupa todos los items que el usuario eligió bajar de una vez.
Cada item tiene su propio estado y porcentaje, así el frontend puede mostrar una
barra de progreso individual por video.

Thread-safe vía un lock simple. Para una app local de un solo usuario alcanza;
si en el futuro esto escala a múltiples usuarios o se persiste a disco/DB, este
módulo es el único punto a reemplazar.
"""
import copy
import threading
import time
import uuid

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def create_job(items: list[dict]) -> str:
    """Crea una tarea con los items dados y devuelve su job_id."""
    job_id = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "created": time.time(),
            "overall": "running",      # running | done
            "items": [
                {
                    "id": it["id"],
                    "title": it.get("title", ""),
                    "percent": 0,
                    "state": "queued",  # queued | downloading | converting | done | error
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
    """Marca el estado global del job."""
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["overall"] = status
