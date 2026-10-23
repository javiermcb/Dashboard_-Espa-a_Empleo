"""Avisos: solo lo nuevo frente a la carga anterior."""
import csv

import notificar

CAMPOS = ["tipo", "indicador", "territorio", "periodo", "valor", "referencia", "mensaje", "nivel"]


def escribir(ruta, filas):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(CAMPOS); w.writerows(filas)


def preparar(tmp_path, monkeypatch, actual, previa):
    monkeypatch.setattr(notificar, "ACTUAL", tmp_path / "qa" / "alertas.csv")
    monkeypatch.setattr(notificar, "PREVIA", tmp_path / "previa" / "alertas.csv")
    monkeypatch.setattr(notificar, "SALIDA", tmp_path / "qa")
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    escribir(notificar.ACTUAL, actual)
    escribir(notificar.PREVIA, previa)
    notificar.main()
    return tmp_path / "qa" / "notificacion_fallos.md", tmp_path / "qa" / "notificacion_alertas.md"


FALLO = ["carga", "fact_x", "", "", "", "", "No actualizada en esta carga: timeout", "aviso"]


def test_fallo_nuevo_se_avisa(tmp_path, monkeypatch):
    fallos, _ = preparar(tmp_path, monkeypatch, [FALLO], [])
    assert fallos.exists() and "fact_x" in fallos.read_text(encoding="utf-8")


def test_fallo_ya_avisado_no_se_repite(tmp_path, monkeypatch):
    fallos, alertas = preparar(tmp_path, monkeypatch, [FALLO], [FALLO])
    assert not fallos.exists() and not alertas.exists()


def test_dato_nuevo_va_a_alertas(tmp_path, monkeypatch):
    nov = ["novedad", "ine:6042", "", "2026T2", "", "", "Nuevo periodo", "novedad"]
    fallos, alertas = preparar(tmp_path, monkeypatch, [nov], [])
    assert not fallos.exists() and "ine:6042" in alertas.read_text(encoding="utf-8")
