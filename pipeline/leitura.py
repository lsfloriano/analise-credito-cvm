import zipfile

import pandas as pd

from pipeline import config

COLUNAS = ["CNPJ_CIA", "CD_CVM", "DENOM_CIA", "VERSAO", "ESCALA_MOEDA", "ORDEM_EXERC",
           "DT_FIM_EXERC", "CD_CONTA", "DS_CONTA", "VL_CONTA", "ST_CONTA_FIXA"]


def ler_dfp(zip_path, ano):
    partes = []
    with zipfile.ZipFile(zip_path) as z:
        nomes = set(z.namelist())
        for arquivo, grupo in config.DEMONSTRATIVOS.items():
            for tipo in ("con", "ind"):
                nome = f"dfp_cia_aberta_{arquivo}_{tipo}_{ano}.csv"
                if nome not in nomes:
                    continue
                with z.open(nome) as f:
                    df = pd.read_csv(f, sep=";", encoding="latin-1", dtype=str, usecols=COLUNAS)
                df["demonstrativo"] = grupo
                df["tipo"] = tipo
                partes.append(df)
    if not partes:
        raise ValueError(f"nenhum demonstrativo encontrado em {zip_path}")
    return pd.concat(partes, ignore_index=True)
