from datetime import date

from core import version_check
from core.version_check import _parse_version_date, is_outdated


def test_parsea_version_fecha():
    assert _parse_version_date("2025.06.09") == date(2025, 6, 9)


def test_version_no_fecha_devuelve_none():
    assert _parse_version_date("1.2") is None
    assert _parse_version_date("abc.def.ghi") is None


def test_version_vieja_es_outdated():
    assert is_outdated("2024.01.01", "2025.06.01") is True


def test_version_fresca_no_es_outdated():
    # Diferencia menor al margen de STALE_DAYS: no molestar
    assert is_outdated("2025.05.20", "2025.06.09") is False


def test_misma_version_no_es_outdated():
    assert is_outdated("2025.06.09", "2025.06.09") is False


def test_fallback_a_tuplas_si_no_son_fechas():
    assert is_outdated("1.0", "2.0") is True
    assert is_outdated("2.0", "1.0") is False


def test_check_sin_red_no_es_outdated(monkeypatch):
    monkeypatch.setattr(version_check, "_cache", None)
    monkeypatch.setattr(version_check, "_fetch_latest", lambda timeout: None)
    result = version_check.check()
    assert result["outdated"] is False
    assert result["latest"] is None


def test_check_cachea_el_resultado(monkeypatch):
    monkeypatch.setattr(version_check, "_cache", None)
    llamadas = []

    def fetch_contado(timeout):
        llamadas.append(1)
        return "2099.01.01"

    monkeypatch.setattr(version_check, "_fetch_latest", fetch_contado)
    primero = version_check.check()
    segundo = version_check.check()
    assert primero["outdated"] is True
    assert primero is segundo
    assert len(llamadas) == 1
