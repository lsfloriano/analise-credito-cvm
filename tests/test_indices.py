import math

import pandas as pd
import pytest

from pipeline import indices


def _fato(**kw):
    linha = {
        "cd_cvm": 1, "ano": 2024,
        "ativo_total": 200.0, "ativo_circulante": 80.0, "estoques": 20.0,
        "passivo_circulante": 40.0, "passivo_nao_circulante": 60.0,
        "patrimonio_liquido": 100.0, "caixa": 10.0, "aplicacoes_financeiras": 5.0,
        "emprestimos_cp": 15.0, "emprestimos_lp": 30.0,
        "receita_liquida": 400.0, "ebit": 50.0, "despesas_financeiras": -25.0,
        "lucro_liquido": 20.0,
    }
    linha.update(kw)
    return pd.DataFrame([linha])


def test_formulas():
    r = indices.calcular_indices(_fato()).iloc[0]
    assert r["liquidez_corrente"] == pytest.approx(2.0)       # 80/40
    assert r["liquidez_seca"] == pytest.approx(1.5)           # (80-20)/40
    assert r["endividamento_geral"] == pytest.approx(0.5)     # (40+60)/200
    assert r["divida_liquida_pl"] == pytest.approx(0.3)       # (15+30-10-5)/100
    assert r["cobertura_juros"] == pytest.approx(2.0)         # 50/|−25|
    assert r["margem_ebit"] == pytest.approx(0.125)           # 50/400
    assert r["margem_liquida"] == pytest.approx(0.05)         # 20/400
    assert r["roa"] == pytest.approx(0.1)                     # 20/200
    assert r["roe"] == pytest.approx(0.2)                     # 20/100


def test_colunas():
    assert list(indices.calcular_indices(_fato()).columns) == ["cd_cvm", "ano", *indices.INDICES]


def test_denominador_zero_vira_nan():
    r = indices.calcular_indices(_fato(passivo_circulante=0.0, receita_liquida=0.0,
                                       despesas_financeiras=0.0)).iloc[0]
    for col in ["liquidez_corrente", "liquidez_seca", "margem_ebit", "margem_liquida", "cobertura_juros"]:
        assert math.isnan(r[col]), col


def test_pl_nao_positivo_anula_indices_sobre_pl():
    r = indices.calcular_indices(_fato(patrimonio_liquido=-10.0)).iloc[0]
    assert math.isnan(r["roe"])
    assert math.isnan(r["divida_liquida_pl"])
    assert not math.isnan(r["roa"])
