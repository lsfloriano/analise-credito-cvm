import pandas as pd

from pipeline import exportar


def test_grava_quatro_parquets(tmp_path):
    fato = pd.DataFrame({"cd_cvm": [1, 1, 2], "ano": [2023, 2024, 2024],
                         "tipo_demonstrativo": ["individual", "consolidado", "consolidado"],
                         "z": [5.0, 6.0, 3.0]})
    cadastro = pd.DataFrame({"cd_cvm": [1, 2, 3], "cnpj": ["a", "b", "c"], "nome": ["A", "B", "C"],
                             "setor": ["Alimentos", "Energia Elétrica", "Bancos"],
                             "situacao": ["ATIVO"] * 3})
    problemas = pd.DataFrame({"cd_cvm": [3], "ano": [2024], "etapa": ["filtro"],
                              "problema": ["setor financeiro"]})

    caminhos = exportar.exportar(fato, cadastro, problemas, tmp_path / "out")

    assert sorted(caminhos) == ["dim_empresa", "dim_setor", "fato_indicadores", "qualidade"]
    dim = pd.read_parquet(caminhos["dim_empresa"]).set_index("cd_cvm")
    assert sorted(dim.index) == [1, 2]                       # só quem está na fato
    assert dim.loc[1, "tipo_demonstrativo"] == "consolidado"  # o do ano mais recente
    assert pd.read_parquet(caminhos["dim_setor"])["setor"].tolist() == ["Alimentos", "Energia Elétrica"]
    assert len(pd.read_parquet(caminhos["fato_indicadores"])) == 3
    assert pd.read_parquet(caminhos["qualidade"])["problema"].tolist() == ["setor financeiro"]


def test_reexecutar_sobrescreve(tmp_path):
    fato = pd.DataFrame({"cd_cvm": [1], "ano": [2024], "tipo_demonstrativo": ["consolidado"]})
    cad = pd.DataFrame({"cd_cvm": [1], "cnpj": ["a"], "nome": ["A"], "setor": ["X"], "situacao": ["ATIVO"]})
    vazio = pd.DataFrame(columns=["cd_cvm", "ano", "etapa", "problema"])
    exportar.exportar(fato, cad, vazio, tmp_path)
    c = exportar.exportar(fato, cad, vazio, tmp_path)
    assert len(pd.read_parquet(c["fato_indicadores"])) == 1
