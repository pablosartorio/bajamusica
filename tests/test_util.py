from core.util import format_duration


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
