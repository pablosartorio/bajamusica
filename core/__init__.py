"""
Paquete core: lógica de negocio desacoplada de Flask.

- search.py    → búsqueda en YouTube (sin descargar)
- download.py  → descarga + conversión con yt-dlp + ffmpeg
- jobs.py      → registro en memoria del estado de cada tarea
- util.py      → helpers (formateo de duración, etc.)

Mantener esta capa independiente de Flask permite reutilizarla luego desde
una CLI, una API distinta, o tests, sin tocar nada del servidor web.
"""
