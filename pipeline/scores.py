import numpy as np
import pandas as pd

LIMITE_SEGURA = 5.85
LIMITE_RISCO = 4.15

SITUACAO_FLEURIET = {1: "Excelente", 2: "Sólida", 3: "Insatisfatória",
                     4: "Péssima", 5: "Muito ruim", 6: "Alto risco"}

# (cdg >= 0, ncg >= 0, t >= 0) -> tipo
_TIPOS = {(True, False, True): 1, (True, True, True): 2, (True, True, False): 3,
          (False, True, False): 4, (False, False, False): 5, (False, False, True): 6}


def _zona(z):
    return pd.Series(
        np.select([z.isna(), z > LIMITE_SEGURA, z >= LIMITE_RISCO],
                  ["indeterminada", "segura", "cinzenta"], default="risco"),
        index=z.index,
    )


def calcular_z(df):
    df = df.copy()
    at = df["ativo_total"].where(df["ativo_total"] != 0)
    exigivel = df["passivo_circulante"] + df["passivo_nao_circulante"]
    df["x1"] = (df["ativo_circulante"] - df["passivo_circulante"]) / at
    df["x2"] = (df["reservas_lucros"] + df["lucros_acumulados"]) / at
    df["x3"] = df["ebit"] / at
    df["x4"] = df["patrimonio_liquido"] / exigivel.where(exigivel != 0)
    df["z"] = 3.25 + 6.56 * df["x1"] + 3.26 * df["x2"] + 6.72 * df["x3"] + 1.05 * df["x4"]
    df["zona"] = _zona(df["z"])
    return df


def classificar_fleuriet(df):
    df = df.copy()
    df["cdg"] = (df["patrimonio_liquido"] + df["passivo_nao_circulante"]) - df["ativo_nao_circulante"]
    df["t"] = (df["caixa"] + df["aplicacoes_financeiras"]) - df["emprestimos_cp"]
    df["ncg"] = df["cdg"] - df["t"]
    tipos = [
        pd.NA if pd.isna(cdg) or pd.isna(t) else _TIPOS.get((cdg >= 0, ncg >= 0, t >= 0), pd.NA)
        for cdg, ncg, t in zip(df["cdg"], df["ncg"], df["t"])
    ]
    df["tipo_fleuriet"] = pd.array(tipos, dtype="Int64")
    df["situacao_fleuriet"] = df["tipo_fleuriet"].map(SITUACAO_FLEURIET)
    return df


def marcar_tesoura(df):
    df = df.copy()
    base = df[["cd_cvm", "ano", "cdg", "ncg", "tipo_demonstrativo"]].reset_index(drop=True)
    ant1 = (base.assign(ano=base["ano"] + 1)
                .rename(columns={"cdg": "cdg_1", "ncg": "ncg_1", "tipo_demonstrativo": "tipo_1"}))
    ant2 = (base.assign(ano=base["ano"] + 2)
                .rename(columns={"cdg": "cdg_2", "ncg": "ncg_2", "tipo_demonstrativo": "tipo_2"}))
    m = base.merge(ant1, on=["cd_cvm", "ano"], how="left").merge(ant2, on=["cd_cvm", "ano"], how="left")

    elegivel = (
        (m["tipo_demonstrativo"] == m["tipo_1"]) & (m["tipo_demonstrativo"] == m["tipo_2"])
        & m["cdg"].notna() & m["ncg"].notna()
        & m["cdg_1"].notna() & m["ncg_1"].notna()
        & m["cdg_2"].notna() & m["ncg_2"].notna()
    )
    piorou_t = (m["ncg"] - m["ncg_1"]) > (m["cdg"] - m["cdg_1"])
    piorou_t1 = (m["ncg_1"] - m["ncg_2"]) > (m["cdg_1"] - m["cdg_2"])
    marcado = elegivel & piorou_t & piorou_t1

    df["efeito_tesoura"] = pd.array(
        np.where(elegivel.to_numpy(), marcado.to_numpy(), pd.NA), dtype="boolean"
    )
    return df


def calcular_scores(df):
    return marcar_tesoura(classificar_fleuriet(calcular_z(df)))
