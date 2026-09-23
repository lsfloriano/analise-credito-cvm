import numpy as np
import pandas as pd

COLUNAS_SAIDA = ["cd_cvm", "cnpj", "nome", "ano", "dt_fim", "tipo_demonstrativo",
                 "demonstrativo", "cd_conta", "ds_conta", "valor"]

ESCALAS = {"MIL": 1000.0, "UNIDADE": 1.0}


def limpar(bruto):
    df = bruto[(bruto["ORDEM_EXERC"] == "ÚLTIMO") & (bruto["ST_CONTA_FIXA"] == "S")].copy()

    df["cd_cvm"] = df["CD_CVM"].astype(int)
    df["dt_fim"] = pd.to_datetime(df["DT_FIM_EXERC"])
    df["ano"] = df["dt_fim"].dt.year.astype(int)
    df["versao"] = df["VERSAO"].astype(int)

    # reapresentação: só a maior versão de cada demonstrativo
    maior = df.groupby(["cd_cvm", "ano", "dt_fim", "tipo", "demonstrativo"])["versao"].transform("max")
    df = df[df["versao"] == maior].copy()

    escala = df["ESCALA_MOEDA"].map(ESCALAS)
    if escala.isna().any():
        invalidas = sorted(df.loc[escala.isna(), "ESCALA_MOEDA"].unique())
        raise ValueError(f"ESCALA_MOEDA desconhecida: {invalidas}")
    df["valor"] = df["VL_CONTA"].astype(float) * escala

    # consolidado quando existe com Ativo Total diferente de zero; senão individual
    com_con = df[(df["tipo"] == "con") & (df["CD_CONTA"] == "1") & (df["valor"] != 0)]
    chaves_con = com_con[["cd_cvm", "ano"]].drop_duplicates().assign(_tem_con=True)
    df = df.merge(chaves_con, on=["cd_cvm", "ano"], how="left")
    usar = np.where(df["_tem_con"].eq(True), "con", "ind")
    df = df[df["tipo"] == usar].copy()
    df["tipo_demonstrativo"] = df["tipo"].map({"con": "consolidado", "ind": "individual"})

    df = df.rename(columns={"CNPJ_CIA": "cnpj", "DENOM_CIA": "nome",
                            "CD_CONTA": "cd_conta", "DS_CONTA": "ds_conta"})
    return df[COLUNAS_SAIDA].reset_index(drop=True)
