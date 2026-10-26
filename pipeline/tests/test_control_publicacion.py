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
