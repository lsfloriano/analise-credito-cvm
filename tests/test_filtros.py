import pandas as pd

from pipeline import filtros, limpar


def _limpo(linhas):
    base = {"cnpj": "x", "nome": "X", "dt_fim": pd.Timestamp("2024-12-31"),
            "tipo_demonstrativo": "consolidado", "demonstrativo": "BP"}
    return pd.DataFrame([{**base, **l} for l in linhas])[limpar.COLUNAS_SAIDA]


def _empresa(cd, ano=2024, at=100.0, ds_pl="Patrimônio Líquido Consolidado",
             ds_ebit="Resultado Antes do Resultado Financeiro e dos Tributos"):
    return [
        {"cd_cvm": cd, "ano": ano, "cd_conta": "1", "ds_conta": "Ativo Total", "valor": at},
        {"cd_cvm": cd, "ano": ano, "cd_conta": "2.03", "ds_conta": ds_pl, "valor": 40.0},
        {"cd_cvm": cd, "ano": ano, "cd_conta": "3.05", "ds_conta": ds_ebit, "valor": 10.0},
    ]


CAD = pd.DataFrame({
    "cd_cvm": [1, 2, 3, 4],
    "cnpj": ["a", "b", "c", "d"],
    "nome": ["A", "B", "C", "D"],
    "setor": ["Energia Elétrica", "Bancos", "Alimentos", "Alimentos"],
    "situacao": ["ATIVO"] * 4,
})


def test_mantem_empresa_valida():
    filtrado, problemas = filtros.filtrar(_limpo(_empresa(1)), CAD)
    assert set(filtrado["cd_cvm"]) == {1}
    assert len(filtrado) == 3
    assert problemas.empty
    assert list(problemas.columns) == filtros.COLUNAS_PROBLEMAS


def test_exclui_e_registra_cada_motivo():
    linhas = (_empresa(1)
              + _empresa(2)                                                    # banco
              + _empresa(3, ds_pl="Passivos Financeiros ao Custo Amortizado")  # layout
              + _empresa(4, at=0.0)                                            # AT zero
              + _empresa(99))                                                  # sem cadastro
    filtrado, problemas = filtros.filtrar(_limpo(linhas), CAD)

    assert set(filtrado["cd_cvm"]) == {1}
    motivos = problemas.set_index("cd_cvm")["problema"].to_dict()
    assert motivos == {
        2: "setor financeiro",
        3: "layout não padrão",
        4: "ativo total nulo ou zero",
        99: "sem cadastro",
    }
    assert set(problemas["etapa"]) == {"filtro"}
    assert set(problemas["ano"]) == {2024}


def test_layout_exige_as_duas_contas():
    linhas = [l for l in _empresa(1) if l["cd_conta"] != "3.05"]
    filtrado, problemas = filtros.filtrar(_limpo(linhas), CAD)
    assert filtrado.empty
    assert problemas["problema"].tolist() == ["layout não padrão"]


def test_filtra_por_empresa_ano():
    linhas = _empresa(1, ano=2023, at=0.0) + _empresa(1, ano=2024)
    filtrado, problemas = filtros.filtrar(_limpo(linhas), CAD)
    assert set(filtrado["ano"]) == {2024}
    assert problemas[["cd_cvm", "ano"]].values.tolist() == [[1, 2023]]
