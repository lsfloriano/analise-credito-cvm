from pathlib import Path

import pandas as pd


def exportar(fato, cadastro, problemas, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tipo_recente = fato.sort_values("ano").groupby("cd_cvm")["tipo_demonstrativo"].last()
    dim_empresa = cadastro[cadastro["cd_cvm"].isin(fato["cd_cvm"].unique())].copy()
    dim_empresa["tipo_demonstrativo"] = dim_empresa["cd_cvm"].map(tipo_recente)
    dim_setor = pd.DataFrame({"setor": sorted(dim_empresa["setor"].unique())})

    tabelas = {
        "fato_indicadores": fato,
        "dim_empresa": dim_empresa,
        "dim_setor": dim_setor,
        "qualidade": problemas,
    }
    caminhos = {}
    for nome, df in tabelas.items():
        caminho = out_dir / f"{nome}.parquet"
        df.reset_index(drop=True).to_parquet(caminho, index=False)
        caminhos[nome] = caminho
    return caminhos
