import json

import pytest

import app as app_mod
import config
from core import jobs

VALID_BODY = {
    "items": [{"id": "vid1", "title": "Tema Uno"}],
    "format": "mp3",
    "quality": "high",
    "naming": "youtube",
}


@pytest.fixture(autouse=True)
def aislar_estado(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "_jobs", {})
    monkeypatch.setattr(config, "HISTORY_FILE", tmp_path / "history.json")
    # Nunca descargar de verdad en los tests
    monkeypatch.setattr(app_mod.download_mod, "run_job", lambda *a, **kw: None)


@pytest.fixture()
def client():
    app_mod.app.config["TESTING"] = True
    return app_mod.app.test_client()


def _post_download(client, body=None, **kwargs):
    return client.post(
        "/download",
        data=json.dumps(body if body is not None else VALID_BODY),
        content_type="application/json",
        **kwargs,
    )


# ── Seguridad: Host y Origin ─────────────────────────────────────────────
def test_host_externo_rechazado():
    # DNS rebinding: el atacante apunta su dominio a 127.0.0.1
    client = app_mod.app.test_client()
    res = client.get("/history", headers={"Host": "atacante.com"})
    assert res.status_code == 403


def test_origin_externo_rechazado(client):
    res = _post_download(client, headers={"Origin": "https://atacante.com"})
    assert res.status_code == 403


def test_origin_null_rechazado(client):
    res = _post_download(client, headers={"Origin": "null"})
    assert res.status_code == 403


def test_origin_local_aceptado(client):
    res = _post_download(client, headers={"Origin": "http://localhost:5000"})
    assert res.status_code == 200
    assert "job_id" in res.get_json()


def test_post_sin_json_rechazado(client):
    # Sin Content-Type JSON no hay preflight CORS: tiene que rebotar
    res = client.post("/download", data=json.dumps(VALID_BODY),
                      content_type="text/plain")
    assert res.status_code == 400


# ── /download: validación ────────────────────────────────────────────────
def test_download_ok_devuelve_job_id(client):
    res = _post_download(client)
    assert res.status_code == 200
    job_id = res.get_json()["job_id"]
    assert jobs.get_job(job_id) is not None


def test_download_sin_items(client):
    res = _post_download(client, body=dict(VALID_BODY, items=[]))
    assert res.status_code == 400


def test_download_items_malformados(client):
    res = _post_download(client, body=dict(VALID_BODY, items=["no-dict", {"sin": "id"}]))
    assert res.status_code == 400


def test_download_formato_invalido(client):
    res = _post_download(client, body=dict(VALID_BODY, format="ogg"))
    assert res.status_code == 400


def test_download_calidad_invalida_cae_a_high(client):
    res = _post_download(client, body=dict(VALID_BODY, quality="ultra"))
    assert res.status_code == 200


# ── /progress y /cancel ──────────────────────────────────────────────────
def test_progress_inexistente(client):
    assert client.get("/progress/nope").status_code == 404


def test_progress_de_job_creado(client):
    job_id = _post_download(client).get_json()["job_id"]
    res = client.get(f"/progress/{job_id}")
    assert res.status_code == 200
    assert res.get_json()["overall"] == "running"


def test_cancel_job_corriendo(client):
    job_id = _post_download(client).get_json()["job_id"]
    res = client.post(f"/cancel/{job_id}")
    assert res.status_code == 200
    assert jobs.is_cancelled(job_id) is True


def test_cancel_inexistente(client):
    assert client.post("/cancel/nope").status_code == 404


# ── /version_check ───────────────────────────────────────────────────────
def test_version_check_responde(client, monkeypatch):
    from core import version_check
    monkeypatch.setattr(version_check, "_cache", None)
    monkeypatch.setattr(version_check, "_fetch_latest", lambda timeout: None)
    res = client.get("/version_check")
    assert res.status_code == 200
    data = res.get_json()
    assert {"current", "latest", "outdated"} <= set(data)


# ── Anotación de "ya bajado" ─────────────────────────────────────────────
def test_annotate_downloaded_marca_resultados():
    job_id = jobs.create_job([{"id": "vid1", "title": "Tema"}])
    jobs.update_item(job_id, "vid1", state="done")
    jobs.set_overall(job_id, "done")

    results = [{"id": "vid1"}, {"id": "vid2"}]
    app_mod._annotate_downloaded(results)
    assert "downloaded_at" in results[0]
    assert "downloaded_at" not in results[1]
