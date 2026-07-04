from core.util import format_duration, strip_ansi


def test_minutos_y_segundos():
    assert format_duration(75) == "1:15"


def test_con_horas():
    assert format_duration(3725) == "1:02:05"


def test_segundos_con_cero_a_la_izquierda():
    assert format_duration(61) == "1:01"


def test_vacios_y_invalidos():
    assert format_duration(None) == ""
    assert format_duration(0) == ""
    assert format_duration("no-numerico") == ""


def test_acepta_string_numerico():
    assert format_duration("90") == "1:30"


def test_strip_ansi_saca_colores():
    # El formato exacto que produce yt-dlp corriendo en una terminal.
    crudo = "\x1b[0;31mERROR:\x1b[0m [youtube] abc123: This video is not available"
    assert strip_ansi(crudo) == "ERROR: [youtube] abc123: This video is not available"


def test_strip_ansi_texto_limpio_queda_igual():
    assert strip_ansi("ERROR: sin colores") == "ERROR: sin colores"
    assert strip_ansi("") == ""
