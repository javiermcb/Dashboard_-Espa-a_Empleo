"""Aviso de carga publicada demasiado vieja."""
from datetime import datetime, timezone

import comprobar_frescura as cf

AHORA = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def test_carga_reciente():
    assert cf.revisar({"generado": "2026-10-26 06:30 UTC"}, ahora=AHORA) is None


def test_viernes_a_lunes_no_avisa():
    assert cf.revisar({"generado": "2026-10-23 11:48 UTC"}, ahora=AHORA) is None  # ~72 h


def test_carga_vieja_avisa():
    p = cf.revisar({"generado": "2026-10-20 06:30 UTC"}, ahora=AHORA)
    assert p and "2026-10-20 06:30 UTC" in p


def test_sin_fecha_o_ilegible():
    assert "no trae la fecha" in cf.revisar({}, ahora=AHORA)
    assert "ilegible" in cf.revisar({"generado": "ayer"}, ahora=AHORA)
