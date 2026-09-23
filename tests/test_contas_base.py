import math

import pandas as pd

from pipeline import config, contas_base, limpar


def _filtrado(contas, cd=1, ano=2024, dt="2024-12-31"):
    return pd.DataFrame([
        {"cd_cvm": cd, "cnpj": "x", "nome": "X", "ano": ano, "dt_fim": pd.Timestamp(dt),
         "tipo_demonstrativo": "consolidado", "demonstrativo": "BP",
         "cd_conta": cod, "ds_conta": "d", "valor": v}
        for cod, v in contas.items()
    ])[limpar.COLUNAS_SAIDA]


def _todas(valor=1.0):
    return {cod: valor for cod in config.CONTAS.values()}


def test_uma_linha_por_empresa_ano_com_todas_as_colunas():
    cb, problemas = contas_base.montar_contas_base(_filtrado(_todas()))
    assert list(cb.columns) == ["cd_cvm", "ano", "tipo_demonstrativo", *config.CONTAS]
    assert len(cb) == 1
    assert cb.loc[0, "tipo_demonstrativo"] == "consolidado"
    assert problemas.empty


def test_mapeia_codigo_para_coluna():
    contas = _todas()
    contas["2.03"] = 40.0
    contas["3.05"] = 12.0
    cb, _ = contas_base.montar_contas_base(_filtrado(contas))
    assert cb.loc[0, "patrimonio_liquido"] == 40.0
    assert cb.loc[0, "ebit"] == 12.0


def test_opcional_ausente_vira_zero_sem_problema():
    contas = _todas()
    del contas["1.01.04"]  # estoques
    cb, problemas = contas_base.montar_contas_base(_filtrado(contas))
    assert cb.loc[0, "estoques"] == 0.0
    assert problemas.empty


def test_essencial_ausente_vira_nan_e_registra():
    contas = _todas()
    del contas["6.01"]  # fco
    cb, problemas = contas_base.montar_contas_base(_filtrado(contas))
    assert math.isnan(cb.loc[0, "fco"])
    assert problemas.to_dict("records") == [
        {"cd_cvm": 1, "ano": 2024, "etapa": "contas_base", "problema": "conta ausente: fco"}
    ]


def test_duplicata_no_mesmo_ano_fica_com_exercicio_mais_recente():
    antigo = _filtrado(_todas(1.0), dt="2024-03-31")
    novo = _filtrado(_todas(2.0), dt="2024-12-31")
    cb, _ = contas_base.montar_contas_base(pd.concat([novo, antigo], ignore_index=True))
    assert len(cb) == 1
    assert cb.loc[0, "ativo_total"] == 2.0
