"""Control de calidad antes de publicar los datos de la app."""
import control_publicacion as cp


def meta(**filas):
    return {"ficheros": {k.replace("__", "/"): {"filas": v} for k, v in filas.items()}}


def test_lee_la_lista_de_tablas_de_la_app():
    t = cp.tablas_app()
    assert "fact_ine" in t and "dim_territorio" in t
    assert any(x.startswith("marts/") for x in t)


def test_carga_correcta():
    assert cp.revisar(meta(a=100, marts__m=10), meta(a=90, marts__m=10), ["a", "marts/m"]) == []


def test_sin_carga_previa_solo_mira_las_requeridas():
    assert cp.revisar(meta(a=1), None, ["a"]) == []
    assert cp.revisar(meta(), None, ["a"]) == ["`a`: falta (la app la necesita)"]


def test_tabla_vacia():
    assert cp.revisar(meta(a=0), meta(a=10), ["a"]) == ["`a`: sin filas"]


def test_tabla_desaparecida():
    assert cp.revisar(meta(a=1), meta(a=1, b=5), ["a"]) == ["`b`: estaba publicada y ha desaparecido"]


def test_caida_de_filas():
    problemas = cp.revisar(meta(a=4000), meta(a=10000), ["a"])
    assert len(problemas) == 1 and "10.000" in problemas[0] and "4.000" in problemas[0]
    assert cp.revisar(meta(a=6000), meta(a=10000), ["a"]) == []  # una caída menor del 50 % se publica


def test_tabla_mensual_sepe_cortada_aunque_no_llegue_al_50():
    problemas = cp.revisar(meta(fact_sepe_paro_municipio=900), meta(fact_sepe_paro_municipio=1000), [])
    assert len(problemas) == 1 and "SEPE" in problemas[0]
    assert cp.revisar(meta(fact_sepe_paro_municipio=960), meta(fact_sepe_paro_municipio=1000), []) == []
    assert cp.revisar(meta(a=900), meta(a=1000), []) == []  # otra tabla: solo aplica el 50 %


def test_el_ultimo_periodo_no_retrocede():
    def m(p):
        return {"ficheros": {"fact_x": {"filas": 10, "ultimo_periodo": p}}}
    assert cp.revisar(m("2026-01-01"), m("2026-09-01"), []) == ["`fact_x`: el último periodo retrocede de 2026-09-01 a 2026-01-01"]
    assert cp.revisar(m("2026-09-01"), m("2026-09-01"), []) == []
    assert cp.revisar(m("2026-09-01"), meta(fact_x=10), []) == []  # la carga previa aún no registraba periodos


def _ejecutar(monkeypatch, tmp_path, avisos):
    (tmp_path / "metadatos.json").write_text('{"ficheros": {}}', encoding="utf-8")
    monkeypatch.setattr(cp, "NUEVO", tmp_path / "metadatos.json")
    monkeypatch.setattr(cp, "PREVIO", tmp_path / "no_existe.json")
    monkeypatch.setattr(cp, "SALIDA", tmp_path / "control.md")
    monkeypatch.setattr(cp, "SALIDA_CIFRAS", tmp_path / "cifras.md")
    monkeypatch.setattr(cp, "tablas_app", lambda: [])
    monkeypatch.setattr(cp, "revisar_modelo", lambda carpeta: [])
    monkeypatch.setattr(cp, "revisar_referencias", lambda carpeta: avisos)
    monkeypatch.setattr("sys.argv", ["control_publicacion.py"])
    return cp.main()


def test_cifras_que_no_cuadran_generan_el_texto_de_la_issue_sin_bloquear(monkeypatch, tmp_path):
    assert _ejecutar(monkeypatch, tmp_path, ["D3-01: 5 frente a 6"]) == 0
    assert "D3-01: 5 frente a 6" in (tmp_path / "cifras.md").read_text(encoding="utf-8")


def test_sin_avisos_no_queda_texto_de_cifras(monkeypatch, tmp_path):
    (tmp_path / "cifras.md").write_text("viejo", encoding="utf-8")
    assert _ejecutar(monkeypatch, tmp_path, []) == 0
    assert not (tmp_path / "cifras.md").exists()
