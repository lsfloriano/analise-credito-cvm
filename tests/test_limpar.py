import pandas as pd
import pytest

from pipeline import limpar


def _df(linhas):
    return pd.DataFrame(linhas)


def test_colunas_e_tipos(linha_cvm):
    out = limpar.limpar(_df([linha_cvm("1", "100.0")]))
    assert list(out.columns) == limpar.COLUNAS_SAIDA
    r = out.iloc[0]
    assert r["cd_cvm"] == 1023
    assert r["ano"] == 2024
    assert r["tipo_demonstrativo"] == "consolidado"


def test_escala_mil_vira_reais_e_unidade_mantem(linha_cvm):
    out = limpar.limpar(_df([
        linha_cvm("1", "100.0", escala="MIL"),
        linha_cvm("1", "100.0", cd_cvm="000002", escala="UNIDADE"),
    ]))
    assert out.set_index("cd_cvm")["valor"].to_dict() == {1023: 100_000.0, 2: 100.0}


def test_escala_desconhecida_da_erro(linha_cvm):
    with pytest.raises(ValueError, match="ESCALA_MOEDA"):
        limpar.limpar(_df([linha_cvm("1", "1.0", escala="MILHAO")]))


def test_mantem_so_ultimo_exercicio_e_contas_fixas(linha_cvm):
    out = limpar.limpar(_df([
        linha_cvm("1", "100.0"),
        linha_cvm("1", "90.0", ordem="PENÚLTIMO", dt_fim="2023-12-31"),
        linha_cvm("1.01.99", "5.0", fixa="N"),
    ]))
    assert out["cd_conta"].tolist() == ["1"]
    assert out["valor"].tolist() == [100_000.0]


def test_reapresentacao_fica_com_maior_versao(linha_cvm):
    out = limpar.limpar(_df([
        linha_cvm("1", "100.0", versao="1"),
        linha_cvm("1", "120.0", versao="2"),
    ]))
    assert out["valor"].tolist() == [120_000.0]


def test_prefere_consolidado_quando_existe(linha_cvm):
    out = limpar.limpar(_df([
        linha_cvm("1", "100.0", tipo="con"),
        linha_cvm("1", "80.0", tipo="ind"),
    ]))
    assert out["tipo_demonstrativo"].tolist() == ["consolidado"]
    assert out["valor"].tolist() == [100_000.0]


def test_usa_individual_quando_consolidado_nao_existe_ou_zerado(linha_cvm):
    out = limpar.limpar(_df([
        linha_cvm("1", "80.0", tipo="ind", cd_cvm="000001"),
        linha_cvm("1", "0.0", tipo="con", cd_cvm="000002"),
        linha_cvm("1", "70.0", tipo="ind", cd_cvm="000002"),
    ]))
    res = out.set_index("cd_cvm")
    assert res.loc[1, "tipo_demonstrativo"] == "individual"
    assert res.loc[2, "tipo_demonstrativo"] == "individual"
    assert res.loc[2, "valor"] == 70_000.0


def test_ano_vem_do_fim_do_exercicio(linha_cvm):
    out = limpar.limpar(_df([linha_cvm("1", "1.0", dt_fim="2024-03-31")]))
    assert out["ano"].item() == 2024
