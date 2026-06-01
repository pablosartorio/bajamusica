"""
Servidor Flask: punto de entrada de la app.

Mantiene las rutas finas — toda la lógica vive en el paquete `core`.
Endpoints:
    GET  /                  → la página (UI)
    GET  /search?q=...      → busca en YouTube, devuelve JSON de resultados
    POST /download          → arranca una tarea de descarga, devuelve job_id
    GET  /progress/<job_id> → estado actual de la tarea (para polling)
"""
import threading
import webbrowser

from flask import Flask, jsonify, render_template, request

import config
from core import download as download_mod
from core import jobs as jobs_mod
from core import search as search_mod

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": []})
    try:
        results = search_mod.search(query, config.MAX_SEARCH_RESULTS)
        return jsonify({"results": results})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500


@app.route("/download", methods=["POST"])
def download():
    data = request.get_json(force=True, silent=True) or {}
    items = data.get("items", [])
    fmt = data.get("format", "mp3")
    quality = data.get("quality", "high")

    if not items:
        return jsonify({"error": "No se seleccionó ningún item"}), 400
    if fmt not in config.SUPPORTED_FORMATS:
        return jsonify({"error": f"Formato no soportado: {fmt}"}), 400

    job_id = jobs_mod.create_job(items)
    thread = threading.Thread(
        target=download_mod.run_job,
        args=(
            job_id, items, fmt, quality,
            config.DOWNLOAD_DIR, config.AUDIO_QUALITY, config.VIDEO_QUALITY,
        ),
        daemon=True,
    )
    thread.start()
    return jsonify({"job_id": job_id})


@app.route("/progress/<job_id>")
def progress(job_id):
    job = jobs_mod.get_job(job_id)
    if not job:
        return jsonify({"error": "Tarea no encontrada"}), 404
    return jsonify(job)


def _open_browser():
    webbrowser.open(f"http://{config.HOST}:{config.PORT}")


if __name__ == "__main__":
    if config.OPEN_BROWSER:
        threading.Timer(1.2, _open_browser).start()
    # threaded=True: permite que el polling de progreso responda mientras
    # una descarga corre en su propio thread.
    app.run(host=config.HOST, port=config.PORT, threaded=True)
