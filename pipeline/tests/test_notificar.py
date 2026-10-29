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


def test_texto_externo_no_menciona_ni_enlaza_ni_mete_html():
    s = notificar.limpio("Hola @alguien <img src=x onerror=1> [clic](http://malo.example)\nsegunda línea")
    assert "@alguien" not in s and "@​alguien" in s
    assert "<" not in s and ">" not in s and "](" not in s and "\n" not in s


def test_texto_externo_largo_se_recorta():
    assert len(notificar.limpio("x" * 5000)) == 400


def test_la_issue_lleva_el_texto_limpio(tmp_path, monkeypatch):
    fallo = ["carga", "fact_x", "", "", "", "", "No actualizada: nota «avisar a @quien» <b>x</b>", "aviso"]
    fallos, _ = preparar(tmp_path, monkeypatch, [fallo], [])
    texto = fallos.read_text(encoding="utf-8")
    assert "@quien" not in texto and "<b>" not in texto
