"""
Servidor Flask: punto de entrada de la app.

Mantiene las rutas finas — toda la lógica vive en el paquete `core`.
Endpoints:
    GET  /                  → la página (UI)
    GET  /search?q=...      → busca en YouTube, devuelve JSON de resultados
    POST /download          → arranca una tarea de descarga, devuelve job_id
    GET  /progress/<job_id> → estado actual de la tarea (para polling)
    POST /cancel/<job_id>   → cancela una tarea en curso
    GET  /version_check     → frescura de yt-dlp (best-effort, cacheado)
"""
import logging
import logging.handlers
import socket
import sys
import threading
import webbrowser

from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request

import config
from core import download as download_mod
from core import jobs as jobs_mod
from core import playlist as playlist_mod
from core import search as search_mod
from core import version_check

logger = logging.getLogger(__name__)

# Cuando corre desde un bundle PyInstaller los assets van a sys._MEIPASS
# (en onedir 6.x es la subcarpeta _internal, NO la carpeta del .exe).
if getattr(sys, 'frozen', False):
    _ROOT = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
else:
    _ROOT = Path(__file__).parent

app = Flask(
    __name__,
    template_folder=str(_ROOT / 'templates'),
    static_folder=str(_ROOT / 'static'),
)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # sin caché de static files en local

# La app escucha solo en loopback, pero eso no alcanza: cualquier página web
# que el usuario visite puede hacer fetch() a http://127.0.0.1:PORT (CSRF
# contra servidores locales) o apuntar un dominio propio a 127.0.0.1 (DNS
# rebinding, que además le permitiría LEER las respuestas). Validar Host y
# Origin corta ambos vectores.
_ALLOWED_HOSTNAMES = {"127.0.0.1", "localhost"}


@app.before_request
def _reject_external_requests():
    host = (request.host or "").rsplit(":", 1)[0]
    if host not in _ALLOWED_HOSTNAMES:
        logger.warning("Request rechazado por Host sospechoso: %r", request.host)
        return jsonify({"error": "Host no permitido"}), 403
    # La UI legítima siempre se sirve desde loopback: un Origin externo (o
    # "null", típico de iframes sandboxeados) nunca es tráfico nuestro.
    origin = request.headers.get("Origin")
    if origin and urlparse(origin).hostname not in _ALLOWED_HOSTNAMES:
        logger.warning("Request rechazado por Origin externo: %r", origin)
        return jsonify({"error": "Origen no permitido"}), 403


@app.route("/")
def index():
    return render_template("index.html", default_dir=str(config.DOWNLOAD_DIR))


def _annotate_downloaded(results: list[dict]) -> list[dict]:
    """Marca con `downloaded_at` los resultados que ya figuran en el historial."""
    index = jobs_mod.downloaded_index()
    for r in results:
        ts = index.get(r["id"])
        if ts:
            r["downloaded_at"] = ts
    return results


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": []})
    try:
        results = search_mod.search(query, config.MAX_SEARCH_RESULTS)
        return jsonify({"results": _annotate_downloaded(results)})
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error en búsqueda %r: %s", query, exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/download", methods=["POST"])
def download():
    # Sin force=True: exigir Content-Type application/json hace que un POST
    # cross-origin dispare preflight CORS (que acá nunca se autoriza), en vez
    # de colarse como text/plain. Complementa el chequeo de Origin de arriba.
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Se esperaba un body JSON (application/json)"}), 400
    items   = data.get("items", [])
    fmt     = data.get("format", "mp3")
    quality = data.get("quality", "high")
    naming  = data.get("naming", "youtube")

    raw_dir = (data.get("dest_dir") or "").strip()
    dest_dir = Path(raw_dir).expanduser() if raw_dir else config.DOWNLOAD_DIR

    if not isinstance(items, list) or not items:
        return jsonify({"error": "No se seleccionó ningún item"}), 400
    # Quedarnos solo con items bien formados (dict con id): evita un 500 más
    # adelante en create_job / run_job ante un POST malformado.
    items = [it for it in items if isinstance(it, dict) and it.get("id")]
    if not items:
        return jsonify({"error": "Ningún item tiene un id válido"}), 400
    if fmt not in config.SUPPORTED_FORMATS:
        return jsonify({"error": f"Formato no soportado: {fmt}"}), 400
    if quality not in config.AUDIO_QUALITY:
        quality = "high"
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


@app.route("/cancel/<job_id>", methods=["POST"])
def cancel(job_id):
    if not jobs_mod.cancel_job(job_id):
        return jsonify({"error": "Tarea no encontrada o ya terminada"}), 404
    logger.info("Job %s cancelado por el usuario", job_id)
    return jsonify({"ok": True})


@app.route("/version_check")
def version_check_route():
    return jsonify(version_check.check())


@app.route("/browse_dir")
def browse_dir():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return jsonify({"error": "tkinter no disponible en este sistema"}), 501

    # Tkinter puede fallar en runtime aunque importe (sin display en Linux,
    # o por correr fuera del main thread). Lo envolvemos para devolver un
    # error limpio en vez de un 500.
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(
            title="Elegí la carpeta de destino",
            initialdir=str(config.DOWNLOAD_DIR),
        )
        root.destroy()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"No se pudo abrir el selector: {exc}"}), 200
    return jsonify({"path": folder or None})


@app.route("/expand_playlist")
def expand_playlist():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL requerida"}), 400
    try:
        title, results = playlist_mod.expand(url)
        return jsonify({"title": title, "results": _annotate_downloaded(results)})
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error expandiendo playlist %r: %s", url, exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/history")
def history():
    return jsonify({"entries": jobs_mod.load_history()})


def _setup_logging():
    """Log a archivo con rotación: única forma de diagnosticar el .exe sin consola."""
    try:
        config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            config.LOG_FILE, maxBytes=512_000, backupCount=2, encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s",
        ))
        logging.basicConfig(level=logging.INFO, handlers=[handler])
    except Exception:  # noqa: BLE001 — sin log la app igual tiene que arrancar
        pass


def _pick_port() -> int:
    """Devuelve el primer puerto libre desde config.PORT (el 5000 es popular)."""
    for port in range(config.PORT, config.PORT + config.PORT_ATTEMPTS):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((config.HOST, port))
            except OSError:
                continue
        return port
    # Ninguno libre: devolver el preferido para que app.run() falle con el
    # error real y se muestre el diálogo de abajo.
    return config.PORT


def _open_browser(port: int):
    webbrowser.open(f"http://{config.HOST}:{port}")


if __name__ == "__main__":
    _setup_logging()
    port = _pick_port()
    try:
        from yt_dlp.version import __version__ as _ytdlp_ver
        logger.info(
            "Iniciando BajaMusica en %s:%s (yt-dlp %s, frozen=%s)",
            config.HOST, port, _ytdlp_ver, getattr(sys, 'frozen', False),
        )
        if config.OPEN_BROWSER:
            threading.Timer(1.2, _open_browser, args=(port,)).start()
        # threaded=True: permite que el polling de progreso responda mientras
        # una descarga corre en su propio thread.
        app.run(host=config.HOST, port=port, threaded=True)
    except Exception as exc:
        logger.exception("No se pudo iniciar la aplicación")
        if getattr(sys, 'frozen', False):
            # En el bundle no hay consola: mostrar el error en un diálogo.
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror(
                    "BajaMusica - Error al iniciar",
                    f"No se pudo iniciar la aplicación:\n\n{exc}\n\n"
                    f"Detalles en el log: {config.LOG_FILE}",
                )
                root.destroy()
            except Exception:
                pass
        raise
