import json

import pytest

import config
from core import jobs

ITEMS = [
    {"id": "vid1", "title": "Tema Uno"},
    {"id": "vid2", "title": "Tema Dos"},
]


@pytest.fixture(autouse=True)
def aislar_estado(tmp_path, monkeypatch):
    """Cada test arranca sin jobs en memoria y con un historial propio en tmp."""
    monkeypatch.setattr(jobs, "_jobs", {})
    monkeypatch.setattr(config, "HISTORY_FILE", tmp_path / "history.json")


# ── Ciclo de vida básico ─────────────────────────────────────────────────
def test_create_y_get():
    job_id = jobs.create_job(ITEMS, fmt="mp3", dest_dir="/tmp/x", naming="youtube")
    job = jobs.get_job(job_id)
    assert job["overall"] == "running"
    assert job["cancelled"] is False
    assert [it["id"] for it in job["items"]] == ["vid1", "vid2"]
    assert all(it["state"] == "queued" for it in job["items"])


def test_get_devuelve_copia():
    job_id = jobs.create_job(ITEMS)
    jobs.get_job(job_id)["items"][0]["state"] = "pisado"
    assert jobs.get_job(job_id)["items"][0]["state"] == "queued"


def test_update_item():
    job_id = jobs.create_job(ITEMS)
    jobs.update_item(job_id, "vid1", state="downloading", percent=42)
    item = jobs.get_job(job_id)["items"][0]
    assert (item["state"], item["percent"]) == ("downloading", 42)


def test_job_inexistente():
    assert jobs.get_job("nope") is None


# ── Cancelación ──────────────────────────────────────────────────────────
def test_cancel_marca_el_flag():
    job_id = jobs.create_job(ITEMS)
    assert jobs.cancel_job(job_id) is True
    assert jobs.is_cancelled(job_id) is True


def test_cancel_de_job_terminado_falla():
    job_id = jobs.create_job(ITEMS)
    jobs.set_overall(job_id, "done")
    assert jobs.cancel_job(job_id) is False


def test_cancel_de_job_inexistente_falla():
    assert jobs.cancel_job("nope") is False
    assert jobs.is_cancelled("nope") is False


# ── Purga de jobs viejos ─────────────────────────────────────────────────
def test_purga_jobs_terminados_viejos(monkeypatch):
    # Retención negativa: todo job terminado es inmediatamente purgable
    monkeypatch.setattr(config, "JOB_RETENTION_SECONDS", -1)
    viejo = jobs.create_job(ITEMS)
    jobs.set_overall(viejo, "done")
    nuevo = jobs.create_job(ITEMS)  # create_job dispara la purga
    assert jobs.get_job(viejo) is None
    assert jobs.get_job(nuevo) is not None


def test_no_purga_jobs_corriendo(monkeypatch):
    monkeypatch.setattr(config, "JOB_RETENTION_SECONDS", -1)
    corriendo = jobs.create_job(ITEMS)
    jobs.create_job(ITEMS)
    assert jobs.get_job(corriendo) is not None


def test_no_purga_jobs_recientes():
    # Retención por defecto: un job recién terminado tiene que sobrevivir
    reciente = jobs.create_job(ITEMS)
    jobs.set_overall(reciente, "done")
    jobs.create_job(ITEMS)
    assert jobs.get_job(reciente) is not None


# ── Historial e índice de descargados ────────────────────────────────────
def _completar_job(job_id, estados=("done", "done")):
    for item, estado in zip(jobs.get_job(job_id)["items"], estados):
        jobs.update_item(job_id, item["id"], state=estado)
    jobs.set_overall(job_id, "done")


def test_set_overall_persiste_historial():
    job_id = jobs.create_job(ITEMS)
    _completar_job(job_id)
    entradas = jobs.load_history()
    assert len(entradas) == 1
    assert entradas[0]["id"] == job_id


def test_historial_corrupto_devuelve_lista_vacia():
    config.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.HISTORY_FILE.write_text("{esto no es json", encoding="utf-8")
    assert jobs.load_history() == []


def test_historial_no_lista_devuelve_lista_vacia():
    config.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.HISTORY_FILE.write_text(json.dumps({"k": "v"}), encoding="utf-8")
    assert jobs.load_history() == []


def test_downloaded_index_solo_items_done():
    job_id = jobs.create_job(ITEMS)
    _completar_job(job_id, estados=("done", "error"))
    index = jobs.downloaded_index()
    assert "vid1" in index
    assert "vid2" not in index


def test_downloaded_index_usa_la_descarga_mas_reciente():
    primero = jobs.create_job([ITEMS[0]])
    _completar_job(primero, estados=("done",))
    segundo = jobs.create_job([ITEMS[0]])
    _completar_job(segundo, estados=("done",))
    entradas = jobs.load_history()
    # El historial inserta al principio: entradas[0] es la más reciente
    assert jobs.downloaded_index()["vid1"] == entradas[0]["created"]
