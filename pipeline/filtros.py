import numpy as np
import pandas as pd

from pipeline import config

COLUNAS_PROBLEMAS = ["cd_cvm", "ano", "etapa", "problema"]


def filtrar(limpo, cadastro):
    chaves = limpo[["cd_cvm", "ano"]].drop_duplicates().reset_index(drop=True)
    setor = chaves["cd_cvm"].map(cadastro.set_index("cd_cvm")["setor"])

    indice = pd.MultiIndex.from_frame(chaves)
    layout_ok = np.ones(len(chaves), dtype=bool)
    for cod, trecho in config.LAYOUT_ESPERADO.items():
        certas = limpo[(limpo["cd_conta"] == cod)
                       & limpo["ds_conta"].str.contains(trecho, regex=False, na=False)]
        tuplas = list(certas[["cd_cvm", "ano"]].itertuples(index=False, name=None))
        layout_ok &= indice.isin(tuplas)

    at = (limpo[limpo["cd_conta"] == "1"].groupby(["cd_cvm", "ano"])["valor"].first()
          .reindex(indice))
    at_invalido = (at.isna() | (at == 0)).to_numpy()

    motivo = np.select(
        [setor.isna().to_numpy(),
         setor.isin(config.SETORES_FINANCEIROS).to_numpy(),
         ~layout_ok,
         at_invalido],
        ["sem cadastro", "setor financeiro", "layout não padrão", "ativo total nulo ou zero"],
        default="",
    )

    excluidas = chaves[motivo != ""].assign(etapa="filtro", problema=motivo[motivo != ""])
    validas = chaves[motivo == ""]
    filtrado = limpo.merge(validas, on=["cd_cvm", "ano"], how="inner")
    return filtrado.reset_index(drop=True), excluidas[COLUNAS_PROBLEMAS].reset_index(drop=True)
