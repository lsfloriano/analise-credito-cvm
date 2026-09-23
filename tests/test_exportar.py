import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

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


def test_parquet_usa_string_nao_large_string_ou_null(tmp_path):
    fato = pd.DataFrame({"cd_cvm": [1], "ano": [2024], "tipo_demonstrativo": ["consolidado"],
                         "z": [5.0]})
    cadastro = pd.DataFrame({"cd_cvm": [1], "cnpj": ["a"], "nome": ["A"], "setor": ["Alimentos"],
                             "situacao": ["ATIVO"]})
    problemas = pd.DataFrame(columns=["cd_cvm", "ano", "etapa", "problema"])  # vazia -> coluna null

    caminhos = exportar.exportar(fato, cadastro, problemas, tmp_path / "out")

    for caminho in caminhos.values():
        schema = pq.read_schema(caminho)
        for campo in schema:
            assert not pa.types.is_large_string(campo.type), f"{caminho.name}.{campo.name}"
            assert not pa.types.is_null(campo.type), f"{caminho.name}.{campo.name}"

    schema_qualidade = pq.read_schema(caminhos["qualidade"])
    assert schema_qualidade.field("problema").type == pa.string()


def test_reexecutar_sobrescreve(tmp_path):
    fato = pd.DataFrame({"cd_cvm": [1], "ano": [2024], "tipo_demonstrativo": ["consolidado"]})
    cad = pd.DataFrame({"cd_cvm": [1], "cnpj": ["a"], "nome": ["A"], "setor": ["X"], "situacao": ["ATIVO"]})
    vazio = pd.DataFrame(columns=["cd_cvm", "ano", "etapa", "problema"])
    exportar.exportar(fato, cad, vazio, tmp_path)
    c = exportar.exportar(fato, cad, vazio, tmp_path)
    assert len(pd.read_parquet(c["fato_indicadores"])) == 1
