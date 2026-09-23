import pandas as pd

from pipeline import config
from pipeline.filtros import COLUNAS_PROBLEMAS


def montar_contas_base(filtrado):
    coluna_por_codigo = {cod: col for col, cod in config.CONTAS.items()}
    chaves = pd.MultiIndex.from_frame(filtrado[["cd_cvm", "ano"]].drop_duplicates())

    x = filtrado[filtrado["cd_conta"].isin(coluna_por_codigo)].copy()
    x["coluna"] = x["cd_conta"].map(coluna_por_codigo)

    problemas = []
    n_distintos = x.groupby(["cd_cvm", "ano", "dt_fim", "coluna"])["valor"].transform("nunique")
    divergentes = (x[n_distintos > 1][["cd_cvm", "ano", "coluna"]]
                    .drop_duplicates())
    for cd_cvm, ano, coluna in divergentes.itertuples(index=False):
        problemas.append({"cd_cvm": cd_cvm, "ano": ano, "etapa": "contas_base",
                          "problema": f"duplicata com valores divergentes: {coluna}"})

    # se a empresa tiver dois exercícios no mesmo ano civil, vale o de fim mais recente
    x = x.sort_values("dt_fim", kind="stable").drop_duplicates(["cd_cvm", "ano", "coluna"], keep="last")

    cb = (x.pivot(index=["cd_cvm", "ano"], columns="coluna", values="valor")
            .reindex(index=chaves, columns=list(config.CONTAS)))
    cb.columns.name = None

    essenciais = [c for c in config.CONTAS if c not in config.CONTAS_OPCIONAIS]
    for col in essenciais:
        for cd_cvm, ano in cb.index[cb[col].isna()]:
            problemas.append({"cd_cvm": cd_cvm, "ano": ano, "etapa": "contas_base",
                              "problema": f"conta ausente: {col}"})

    opcionais = list(config.CONTAS_OPCIONAIS)
    cb[opcionais] = cb[opcionais].fillna(0.0)

    tipo = (filtrado.sort_values("dt_fim", kind="stable")
                    .groupby(["cd_cvm", "ano"])["tipo_demonstrativo"].last())
    cb.insert(0, "tipo_demonstrativo", tipo.reindex(cb.index))
    cb = cb.reset_index()
    return cb, pd.DataFrame(problemas, columns=COLUNAS_PROBLEMAS)
