"""Helpers reutilizables."""


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
