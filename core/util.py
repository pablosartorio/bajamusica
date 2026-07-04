"""Helpers reutilizables."""
import re

# Secuencias de escape ANSI (colores de terminal), p. ej. "\x1b[0;31m".
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def strip_ansi(text: str) -> str:
    """Saca códigos de escape ANSI de un texto que va a mostrarse en la UI."""
    return _ANSI_RE.sub("", text)


def format_duration(seconds) -> str:
    """Convierte segundos en un string legible: 75 → '1:15', 3725 → '1:02:05'."""
    if not seconds:
        return ""
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return ""

    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
