import numpy as np
import pandas as pd

from pipeline.indices import INDICES, calcular_indices

COLUNAS_BENCHMARK = [*INDICES, "z"]


def ler_resultado_dax(caminho):
    df = pd.read_csv(caminho, encoding="utf-8-sig")
    df.columns = [c.rsplit("[", 1)[-1].rstrip("]") for c in df.columns]
    return df


def comparar(dax, ref, chaves, colunas, tol=1e-6):
    m = dax.merge(ref, on=chaves, how="outer", suffixes=("_dax", "_ref"), indicator=True)
    saida = [{**{k: r[k] for k in chaves}, "coluna": "(linha)", "dax": r["_merge"], "ref": None}
             for _, r in m[m["_merge"] != "both"].iterrows()]
    m = m[m["_merge"] == "both"]
    for col in colunas:
        a, b = m[f"{col}_dax"], m[f"{col}_ref"]
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            a, b = a.astype(float), b.astype(float)
            iguais = (a.isna() & b.isna()) | np.isclose(a, b, rtol=tol, atol=tol)
        else:
            iguais = (a.isna() & b.isna()) | (a.astype(str) == b.astype(str))
        for _, r in m[~iguais].iterrows():
            saida.append({**{k: r[k] for k in chaves}, "coluna": col,
                          "dax": r[f"{col}_dax"], "ref": r[f"{col}_ref"]})
    return pd.DataFrame(saida, columns=[*chaves, "coluna", "dax", "ref"])


def referencia_indices(fato):
    return calcular_indices(fato).merge(
        fato[["cd_cvm", "ano", "z", "zona", "tipo_fleuriet"]], on=["cd_cvm", "ano"])


def _indices_com_setor(fato, empresas):
    ind = calcular_indices(fato).merge(fato[["cd_cvm", "ano", "z"]], on=["cd_cvm", "ano"])
    return ind.merge(empresas[["cd_cvm", "setor"]], on="cd_cvm")


def referencia_benchmark(fato, empresas):
    g = _indices_com_setor(fato, empresas).groupby(["setor", "ano"])[COLUNAS_BENCHMARK]
    partes = [g.median().add_suffix("_mediana"),
              g.quantile(0.25).add_suffix("_q1"),
              g.quantile(0.75).add_suffix("_q3")]
    return pd.concat(partes, axis=1).reset_index()


def referencia_percentil(fato, empresas, ano):
    ind = _indices_com_setor(fato[fato["ano"] == ano], empresas)
    out = ind[["cd_cvm", "ano"]].copy()
    for col in COLUNAS_BENCHMARK:
        # fração de empresas do setor com valor <= o da empresa (empates contam a favor)
        out[f"{col}_pct"] = ind.groupby("setor")[col].rank(pct=True, method="max")
    return out


def referencia_migracao(fato, ano_base, ano):
    base = fato.loc[fato["ano"] == ano_base, ["cd_cvm", "zona"]].rename(columns={"zona": "zona_origem"})
    atual = fato.loc[fato["ano"] == ano, ["cd_cvm", "zona"]]
    par = atual.merge(base, on="cd_cvm")
    return par.groupby(["zona", "zona_origem"]).size().rename("n").reset_index()
