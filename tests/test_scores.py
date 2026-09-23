import math

import pandas as pd
import pytest

from pipeline import scores


def _base(**kw):
    """Empresa-ano com contas base neutras; sobrescreva o que o teste precisa."""
    linha = {
        "cd_cvm": 1, "ano": 2024, "tipo_demonstrativo": "consolidado",
        "ativo_total": 100.0, "ativo_circulante": 50.0, "passivo_circulante": 30.0,
        "passivo_nao_circulante": 20.0, "ativo_nao_circulante": 50.0,
        "patrimonio_liquido": 50.0, "reservas_lucros": 10.0, "lucros_acumulados": 0.0,
        "ebit": 10.0, "caixa": 5.0, "aplicacoes_financeiras": 5.0, "emprestimos_cp": 4.0,
    }
    linha.update(kw)
    return linha


def test_formula_do_z():
    r = scores.calcular_z(pd.DataFrame([_base()])).iloc[0]
    assert r["x1"] == pytest.approx(0.20)   # (50-30)/100
    assert r["x2"] == pytest.approx(0.10)   # (10+0)/100
    assert r["x3"] == pytest.approx(0.10)   # 10/100
    assert r["x4"] == pytest.approx(1.00)   # 50/(30+20)
    assert r["z"] == pytest.approx(3.25 + 6.56 * 0.2 + 3.26 * 0.1 + 6.72 * 0.1 + 1.05 * 1.0)


def test_tres_zonas():
    df = scores.calcular_z(pd.DataFrame([
        _base(),                                     # z = 6.61 → segura
        _base(ativo_circulante=30.0),                # x1=0 → z = 5.298 → cinzenta
        _base(ativo_circulante=10.0, ebit=-30.0),    # z negativo → risco
    ]))
    assert df["zona"].tolist() == ["segura", "cinzenta", "risco"]


def test_limites_exatos_das_zonas():
    z = pd.Series([5.85, 4.15, 5.8500001, 4.1499999])
    assert scores._zona(z).tolist() == ["cinzenta", "cinzenta", "segura", "risco"]


def test_z_indeterminado_quando_exigivel_zero_ou_componente_nan():
    df = scores.calcular_z(pd.DataFrame([
        _base(passivo_circulante=0.0, passivo_nao_circulante=0.0),
        _base(ebit=float("nan")),
    ]))
    assert math.isnan(df.loc[0, "z"])
    assert df["zona"].tolist() == ["indeterminada", "indeterminada"]


def _fleuriet(cdg, t):
    """Monta contas que produzem exatamente o CDG e o T pedidos (NCG = CDG - T)."""
    # CDG = PL + PNC - ANC  com PNC=0, ANC=100  → PL = CDG + 100
    # T = caixa + aplic - emp_cp  com aplic=0, emp_cp=100 → caixa = T + 100
    return _base(patrimonio_liquido=cdg + 100.0, passivo_nao_circulante=0.0,
                 ativo_nao_circulante=100.0, caixa=t + 100.0,
                 aplicacoes_financeiras=0.0, emprestimos_cp=100.0)


@pytest.mark.parametrize("cdg, t, tipo, situacao", [
    (10.0, 30.0, 1, "Excelente"),        # ncg = -20 → (+,-,+)
    (30.0, 10.0, 2, "Sólida"),           # ncg = 20  → (+,+,+)
    (10.0, -5.0, 3, "Insatisfatória"),   # ncg = 15  → (+,+,-)
    (-10.0, -30.0, 4, "Péssima"),        # ncg = 20  → (-,+,-)
    (-30.0, -10.0, 5, "Muito ruim"),     # ncg = -20 → (-,-,-)
    (-10.0, 5.0, 6, "Alto risco"),       # ncg = -15 → (-,-,+)
    (0.0, 0.0, 2, "Sólida"),             # zero conta como positivo
])
def test_seis_tipos_fleuriet(cdg, t, tipo, situacao):
    r = scores.classificar_fleuriet(pd.DataFrame([_fleuriet(cdg, t)])).iloc[0]
    assert r["cdg"] == pytest.approx(cdg)
    assert r["t"] == pytest.approx(t)
    assert r["ncg"] == pytest.approx(cdg - t)
    assert r["tipo_fleuriet"] == tipo
    assert r["situacao_fleuriet"] == situacao


def test_fleuriet_indeterminado_com_nan():
    r = scores.classificar_fleuriet(pd.DataFrame([_base(patrimonio_liquido=float("nan"))])).iloc[0]
    assert pd.isna(r["tipo_fleuriet"])
    assert pd.isna(r["situacao_fleuriet"])


def _serie(pares, cd=1, ano0=2020, tipos=None):
    """pares = [(cdg, ncg), ...] em anos consecutivos a partir de ano0."""
    if tipos is None:
        tipos = ["consolidado"] * len(pares)
    return pd.DataFrame([{"cd_cvm": cd, "ano": ano0 + i, "cdg": c, "ncg": n, "tipo_demonstrativo": t}
                         for i, ((c, n), t) in enumerate(zip(pares, tipos))])


def test_tesoura_exige_dois_anos_seguidos():
    # 2021: ΔNCG=10 > ΔCDG=0 ; 2022: ΔNCG=10 > ΔCDG=0 → tesoura em 2022
    df = scores.marcar_tesoura(_serie([(100, 50), (100, 60), (100, 70)]))
    assert df["efeito_tesoura"].tolist() == [pd.NA, pd.NA, True]


def test_tesoura_nao_marca_com_um_ano_so():
    df = scores.marcar_tesoura(_serie([(100, 50), (100, 60), (120, 60)]))
    assert df["efeito_tesoura"].tolist() == [pd.NA, pd.NA, False]


def test_tesoura_respeita_buraco_na_serie_e_empresas_diferentes():
    a = _serie([(100, 50), (100, 60)], cd=1, ano0=2020)          # 2020, 2021
    b = _serie([(100, 70)], cd=1, ano0=2023)                     # 2023 (2022 falta)
    c = _serie([(100, 50), (100, 60), (100, 70)], cd=2)          # outra empresa
    df = scores.marcar_tesoura(pd.concat([a, b, c], ignore_index=True))
    assert df["efeito_tesoura"].tolist() == [pd.NA, pd.NA, pd.NA, pd.NA, pd.NA, True]


def test_tesoura_nula_quando_troca_consolidado_individual():
    # mesma série de test_tesoura_exige_dois_anos_seguidos, mas o ano do meio é individual
    df = scores.marcar_tesoura(_serie([(100, 50), (100, 60), (100, 70)],
                                       tipos=["consolidado", "individual", "consolidado"]))
    assert df["efeito_tesoura"].tolist() == [pd.NA, pd.NA, pd.NA]


def test_tesoura_dtype_boolean_nullable():
    df = scores.marcar_tesoura(_serie([(100, 50), (100, 60), (100, 70)]))
    assert df["efeito_tesoura"].dtype == "boolean"


def test_calcular_scores_junta_tudo():
    df = scores.calcular_scores(pd.DataFrame([_base()]))
    for col in ["z", "zona", "cdg", "ncg", "t", "tipo_fleuriet", "situacao_fleuriet", "efeito_tesoura"]:
        assert col in df.columns
