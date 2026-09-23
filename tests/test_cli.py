import zipfile

import pandas as pd

from pipeline import cli, config

CAB = ("CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;"
       "ORDEM_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA\n")

DESCRICOES = {"2.03": "Patrimônio Líquido Consolidado",
              "3.05": "Resultado Antes do Resultado Financeiro e dos Tributos"}


def _zip(path, ano):
    arquivos = {"BPA": "1", "BPP": "2", "DRE": "3", "DFC_MI": "6"}
    with zipfile.ZipFile(path, "w") as z:
        for dem, prefixo in arquivos.items():
            linhas = [
                f"11;{ano}-12-31;1;EMPRESA A;000010;G;REAL;MIL;ÚLTIMO;{ano}-12-31;"
                f"{cod};{DESCRICOES.get(cod, 'Conta')};100.0;S\n"
                for cod in config.CONTAS.values()
                if cod.split(".")[0] == prefixo
            ]
            z.writestr(f"dfp_cia_aberta_{dem}_con_{ano}.csv", (CAB + "".join(linhas)).encode("latin-1"))


def test_run_ponta_a_ponta(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    for ano in (2023, 2024):
        _zip(raw / f"dfp_cia_aberta_{ano}.zip", ano)
    (raw / "cad_cia_aberta.csv").write_bytes(
        ("CNPJ_CIA;DENOM_SOCIAL;SIT;DT_INI_SIT;CD_CVM;SETOR_ATIV\n"
         "11;EMPRESA A SA;ATIVO;2010-01-01;10;Alimentos\n").encode("latin-1"))

    def get(url, timeout):
        raise AssertionError("não deveria baixar: arquivos estão em cache")

    caminhos = cli.run([2023, 2024], raw_dir=raw, out_dir=tmp_path / "out", get=get)

    fato = pd.read_parquet(caminhos["fato_indicadores"])
    assert fato[["cd_cvm", "ano"]].values.tolist() == [[10, 2023], [10, 2024]]
    assert (fato["ativo_total"] == 100_000.0).all()
    assert set(fato["zona"]) <= {"segura", "cinzenta", "risco", "indeterminada"}


def test_parse_anos():
    assert list(cli._parse_anos("2015-2017")) == [2015, 2016, 2017]
    assert list(cli._parse_anos("2020")) == [2020]
