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

from pathlib import Path

from flask import Flask, jsonify, render_template, request

import config
from core import download as download_mod
from core import jobs as jobs_mod
from core import playlist as playlist_mod
from core import search as search_mod

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # sin caché de static files en local


@app.route("/")
def index():
    return render_template("index.html", default_dir=str(config.DOWNLOAD_DIR))


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
    items   = data.get("items", [])
    fmt     = data.get("format", "mp3")
    quality = data.get("quality", "high")
    naming  = data.get("naming", "youtube")

    raw_dir = data.get("dest_dir", "").strip()
    dest_dir = Path(raw_dir).expanduser() if raw_dir else config.DOWNLOAD_DIR

    if not items:
        return jsonify({"error": "No se seleccionó ningún item"}), 400
    if fmt not in config.SUPPORTED_FORMATS:
        return jsonify({"error": f"Formato no soportado: {fmt}"}), 400
    if naming not in config.NAMING_SCHEMES:
        naming = "youtube"

    job_id = jobs_mod.create_job(items, fmt=fmt, dest_dir=str(dest_dir), naming=naming)
    thread = threading.Thread(
        target=download_mod.run_job,
        args=(
            job_id, items, fmt, quality,
            dest_dir, config.AUDIO_QUALITY, config.VIDEO_QUALITY, naming,
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


@app.route("/browse_dir")
def browse_dir():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return jsonify({"error": "tkinter no disponible en este sistema"}), 501

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder = filedialog.askdirectory(
        title="Elegí la carpeta de destino",
        initialdir=str(config.DOWNLOAD_DIR),
    )
    root.destroy()
    return jsonify({"path": folder or None})


@app.route("/expand_playlist")
def expand_playlist():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL requerida"}), 400
    try:
        title, results = playlist_mod.expand(url)
        return jsonify({"title": title, "results": results})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500


@app.route("/history")
def history():
    return jsonify({"entries": jobs_mod.load_history()})


def _open_browser():
    webbrowser.open(f"http://{config.HOST}:{config.PORT}")


if __name__ == "__main__":
    if config.OPEN_BROWSER:
        threading.Timer(1.2, _open_browser).start()
    # threaded=True: permite que el polling de progreso responda mientras
    # una descarga corre en su propio thread.
    app.run(host=config.HOST, port=config.PORT, threaded=True)
